"""Conservative Cartesian TCP routing around rectangular obstacles.

This planner checks the tool envelope only, not a robot's links, IK or dynamics.
It deliberately routes all XY motion at travel Z above the fixtures.
"""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Pose:
    x: float
    y: float
    z: float
    yaw: float = 0.0


@dataclass(frozen=True)
class Obstacle:
    xmin: float
    xmax: float
    ymin: float
    ymax: float
    top: float


HOME = Pose(200, -100, 160)
TRAYS = {"circle": Pose(540, -100, 25), "square": Pose(540, 0, 25), "ring": Pose(540, 100, 25)}
FIXTURES = (Obstacle(360, 420, -80, -30, 80),)
TOOL_RADIUS = 20.0
TRAVEL_Z = 160.0


def in_workspace(p):
    return all(math.isfinite(v) for v in (p.x, p.y, p.z, p.yaw)) and 180 <= p.x <= 600 and -150 <= p.y <= 250 and 15 <= p.z <= 250


def segment_clear(a, b, obstacles=FIXTURES):
    """Slab intersection test with radius-inflated boxes (units: millimetres)."""
    if not in_workspace(a) or not in_workspace(b):
        return False
    for box in obstacles:
        lower = (box.xmin - TOOL_RADIUS, box.ymin - TOOL_RADIUS, 0)
        upper = (box.xmax + TOOL_RADIUS, box.ymax + TOOL_RADIUS, box.top + TOOL_RADIUS)
        tmin, tmax = 0.0, 1.0
        for start, end, lo, hi in zip((a.x, a.y, a.z), (b.x, b.y, b.z), lower, upper):
            delta = end - start
            if abs(delta) < 1e-12:
                if start < lo or start > hi:
                    tmin, tmax = 1.0, 0.0
                    break
            else:
                first, last = sorted(((lo - start) / delta, (hi - start) / delta))
                tmin, tmax = max(tmin, first), min(tmax, last)
        if tmin <= tmax:
            return False
    return True


def plan(current, target, obstacles=FIXTURES):
    if not in_workspace(current) or not in_workspace(target):
        raise ValueError("Pose outside Cartesian workspace")
    route = [current, Pose(current.x, current.y, TRAVEL_Z, current.yaw),
             Pose(target.x, target.y, TRAVEL_Z, target.yaw), target]
    if not all(segment_clear(a, b, obstacles) for a, b in zip(route, route[1:])):
        raise ValueError("Tool path collides with fixture; no route accepted")
    return route


def path_length(route):
    return sum(math.dist((a.x, a.y, a.z), (b.x, b.y, b.z)) for a, b in zip(route, route[1:]))


class Robot:
    """Level handshake: start -> running -> drop start -> complete -> ack."""
    def __init__(self):
        self.pose = HOME
        self.ready = True
        self.running = self.complete = self.error = False
        self.route = []
        self.index = 1
        self.speed_mm_s = 250.0
        self.length_mm = 0.0

    def command(self, route):
        if not self.ready or self.running or self.complete:
            raise RuntimeError("Robot not ready for a new handshake")
        self.route, self.index = route, 1
        self.length_mm = path_length(route)
        self.running, self.ready = True, False

    def tick(self, dt, start=False, ack=False, fault=None):
        if ack and self.complete:
            self.complete, self.ready = False, True
        if not self.running or fault == "robot_timeout":
            return
        budget = self.speed_mm_s * dt
        while self.index < len(self.route):
            target = self.route[self.index]
            distance = math.dist((self.pose.x, self.pose.y, self.pose.z), (target.x, target.y, target.z))
            if distance <= budget:
                self.pose = target
                budget -= distance
                self.index += 1
            else:
                ratio = budget / distance
                self.pose = Pose(self.pose.x + ratio * (target.x - self.pose.x),
                                 self.pose.y + ratio * (target.y - self.pose.y),
                                 self.pose.z + ratio * (target.z - self.pose.z), target.yaw)
                break
        if self.index == len(self.route) and not start:
            self.running, self.complete = False, True

    def stop(self):
        self.running = self.complete = False
        self.ready = False

    def reset(self):
        # Retain the physical position; recovery never teleports to HOME.
        self.running = self.complete = self.error = False
        self.ready = True
        self.route = []
