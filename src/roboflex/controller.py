"""10 ms style cyclic sequence, simulated I/O and latched alarm recovery."""

from dataclasses import asdict
from enum import Enum
import time

import numpy as np

from .motion import HOME, TRAYS, Pose, Robot, plan
from .vision import default_calibration, detect, synthetic_frame


class State(str, Enum):
    IDLE = "IDLE"
    WAIT_PART = "WAIT_PART"
    VISION = "VISION"
    PICK = "ROBOT_PICK"
    GRIP = "GRIPPER_CLOSE"
    PLACE = "ROBOT_PLACE"
    RELEASE = "GRIPPER_OPEN"
    CHECK = "QUALITY_CHECK"
    HOME = "RETURN_HOME"
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"


FAULTS = {
    "camera_offline": ("ALM-001", "相机断线：检查相机连接后复位"),
    "vision_fail": ("ALM-002", "视觉目标不唯一或识别失败：检查光照和工件"),
    "robot_not_ready": ("ALM-003", "机器人未就绪：检查运行模式和握手"),
    "robot_timeout": ("ALM-004", "机器人运动超时：检查任务与驱动反馈"),
    "gripper_fail": ("ALM-005", "夹爪闭合反馈超时：检查气压与夹爪"),
    "part_dropped": ("ALM-006", "放置检测失败：清理工件后复位"),
    "communication_loss": ("ALM-007", "通信心跳丢失：恢复连接后复位"),
    "sensor_stuck": ("ALM-008", "来料传感器超时：检查传感器与输送线"),
    "conveyor_jam": ("ALM-009", "输送带堵塞：清理输送线后复位"),
    "estop": ("ALM-010", "急停输入断开：解除急停并人工复位"),
    "door_open": ("ALM-011", "安全门打开：关闭安全门并人工复位"),
    "planning_fail": ("ALM-012", "路径被拒绝：检查工作范围与夹具位置"),
}


class Cell:
    def __init__(self, seed=42):
        self.rng = np.random.default_rng(seed)
        self.calibration = default_calibration()
        self.robot = Robot()
        self.state = State.IDLE
        self.clock = self.elapsed = 0.0
        self.cycle_started = 0.0
        self.enabled = False
        self.conveyor = self.gripper = self.robot_start = False
        self.fault = None
        self.alarm = None
        self.events = []
        self.records = []
        self.image = None
        self.truth = self.target = None
        self.part_kind = None
        self.holding = False
        self.cycle_length = 0.0
        self.heartbeat_age = 0.0
        self.total = self.ok = self.ng = self.aborted = 0

    def transition(self, state):
        self.events.append({"sim_time_s": round(self.clock, 3), "from": self.state.value, "to": state.value})
        self.state, self.elapsed = state, 0.0

    def start(self):
        if self.state != State.IDLE or self.fault is not None or self.holding:
            return False
        self.enabled = True
        self.cycle_started = self.clock
        self.transition(State.WAIT_PART)
        return True

    def stop(self):
        """Controlled simulation stop. A partial cycle needs explicit reset/clear."""
        if self.state not in (State.IDLE, State.ERROR):
            self.trip("ALM-013", "操作员停止：清理未完成工件并复位")

    def inject(self, fault):
        if fault not in FAULTS:
            raise ValueError("Unknown fault scenario")
        self.fault = fault

    def trip(self, code, message):
        if self.state == State.ERROR:
            return
        self.alarm = {"code": code, "message": message, "state": self.state.value,
                      "sim_time_s": round(self.clock, 3)}
        self.aborted += int(self.state != State.IDLE)
        self.enabled = self.conveyor = self.robot_start = False
        self.robot.stop()
        self.transition(State.ERROR)
        # A held part remains held on stop; opening the gripper could drop it.

    def reset(self, clear_part=False):
        if self.fault is not None or self.state != State.ERROR:
            return False
        if self.holding and not clear_part:
            return False
        self.holding = self.gripper = False
        self.robot.reset()
        self.alarm = None
        self.target = self.truth = None
        self.heartbeat_age = 0.0
        self.transition(State.IDLE)
        return True

    def move(self, target):
        try:
            route = plan(self.robot.pose, target)
            self.robot.command(route)
            self.cycle_length += self.robot.length_mm
            self.robot_start = True
        except (ValueError, RuntimeError):
            self.trip(*FAULTS["planning_fail"])

    def tick(self, dt=0.01):
        if not 0 < dt <= 0.1:
            raise ValueError("Scan dt must be in (0, 0.1] seconds")
        self.clock += dt
        self.elapsed += dt
        if self.fault in ("estop", "door_open"):
            self.trip(*FAULTS[self.fault])
        if self.state == State.ERROR:
            return
        self.heartbeat_age = self.heartbeat_age + dt if self.fault == "communication_loss" else 0.0
        if self.enabled and self.heartbeat_age >= 0.5:
            self.trip(*FAULTS["communication_loss"])
            return
        self.robot.tick(dt, start=self.robot_start, fault=self.fault)
        if self.robot_start and self.robot.running:
            self.robot_start = False
        if self.state == State.IDLE:
            return
        if self.state == State.WAIT_PART:
            self.conveyor = True
            if self.fault in ("sensor_stuck", "conveyor_jam"):
                if self.elapsed >= 2.0:
                    self.trip(*FAULTS[self.fault])
            elif self.elapsed >= 0.3:
                self.conveyor = False
                self.cycle_length = 0.0
                self.image, self.truth = synthetic_frame(self.rng, self.part_kind)
                self.transition(State.VISION)
        elif self.state == State.VISION:
            if self.elapsed < 0.05:
                return
            if self.fault in ("camera_offline", "vision_fail"):
                self.trip(*FAULTS[self.fault])
                return
            detections = detect(self.image)
            if len(detections) != 1:
                self.trip(*FAULTS["vision_fail"])
                return
            item = detections[0]
            try:
                x, y = self.calibration.map(item.pixel)
                yaw = self.calibration.angle(item.pixel, item.angle_deg) if item.kind == "square" else 0.0
                self.target = {"kind": item.kind, "pixel": list(item.pixel), "x": x, "y": y, "yaw": yaw}
            except ValueError:
                self.trip(*FAULTS["planning_fail"])
                return
            if self.fault == "robot_not_ready":
                self.trip(*FAULTS[self.fault])
                return
            self.transition(State.PICK)
            self.move(Pose(400, -55, 25) if self.fault == "planning_fail" else Pose(x, y, 25, yaw))
        elif self.state in (State.PICK, State.PLACE, State.HOME):
            if self.elapsed >= 6.0:
                self.trip(*FAULTS["robot_timeout"])
            elif self.robot.complete:
                self.robot.tick(0, ack=True)
                if self.state == State.PICK:
                    self.transition(State.GRIP)
                elif self.state == State.PLACE:
                    self.transition(State.RELEASE)
                else:
                    self.transition(State.COMPLETE)
        elif self.state == State.GRIP:
            self.gripper = True
            if self.fault == "gripper_fail":
                if self.elapsed >= 0.5:
                    self.trip(*FAULTS[self.fault])
            elif self.elapsed >= 0.15:
                self.holding = True
                self.transition(State.PLACE)
                self.move(TRAYS[self.target["kind"]])
        elif self.state == State.RELEASE:
            self.gripper = False
            if self.elapsed >= 0.15:
                self.holding = False
                self.transition(State.CHECK)
        elif self.state == State.CHECK:
            if self.elapsed >= 0.1:
                if self.fault == "part_dropped":
                    self.total += 1
                    self.ng += 1
                    self.trip(*FAULTS[self.fault])
                else:
                    self.transition(State.HOME)
                    self.move(HOME)
        elif self.state == State.COMPLETE:
            self.total += 1
            self.ok += 1
            error = float(np.linalg.norm(np.asarray([self.target["x"], self.target["y"]]) - self.truth["xy_mm"]))
            self.records.append({"cycle": self.total, "kind": self.target["kind"],
                                 "cycle_time_s": round(self.clock - self.cycle_started, 3),
                                 "localization_error_mm": error, "path_length_mm": self.cycle_length,
                                 "truth": self.truth, "detected": self.target})
            self.cycle_started = self.clock
            self.transition(State.WAIT_PART if self.enabled else State.IDLE)

    def snapshot(self):
        return {"state": self.state.value, "sim_time_s": round(self.clock, 3),
                "enabled": self.enabled, "conveyor": self.conveyor, "gripper": self.gripper,
                "holding": self.holding, "robot_start": self.robot_start,
                "robot": {"ready": self.robot.ready, "running": self.robot.running,
                          "complete": self.robot.complete, "pose": asdict(self.robot.pose)},
                "fault": self.fault, "alarm": self.alarm, "target": self.target,
                "total": self.total, "ok": self.ok, "ng": self.ng, "aborted": self.aborted,
                "last_cycle": self.records[-1] if self.records else None, "events": self.events[-12:]}


def run_cycles(count=100, seed=42):
    if count < 1:
        raise ValueError("Cycle count must be positive")
    cell = Cell(seed)
    cell.start()
    started = time.perf_counter()
    for _ in range(count * 2500):
        cell.tick()
        if cell.state == State.ERROR:
            raise RuntimeError(f"Unexpected simulation alarm: {cell.alarm}")
        if cell.ok >= count:
            break
    if cell.ok != count:
        raise RuntimeError("Simulation scan budget exceeded")
    duration = time.perf_counter() - started
    errors = [r["localization_error_mm"] for r in cell.records]
    cycles = [r["cycle_time_s"] for r in cell.records]
    return {"seed": seed, "cycles": count, "ok": cell.ok, "ng": cell.ng,
            "scope": "synthetic vision + Cartesian TCP software-in-the-loop; no hardware",
            "dt_s": 0.01, "mean_localization_error_mm": float(np.mean(errors)),
            "max_localization_error_mm": float(np.max(errors)),
            "mean_simulated_cycle_time_s": float(np.mean(cycles)),
            "p95_simulated_cycle_time_s": float(np.percentile(cycles, 95)),
            "benchmark_wall_time_s": duration, "records": cell.records}
