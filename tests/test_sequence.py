import numpy as np
import pytest

from roboflex.controller import Cell, FAULTS, State, run_cycles


def advance(cell, until, scans=4000):
    for _ in range(scans):
        cell.tick()
        if until(cell):
            return
    pytest.fail(f"Expected condition was not reached: {cell.snapshot()}")


@pytest.mark.parametrize("kind", ["circle", "square", "ring"])
def test_complete_cycle_and_handshake_order(kind):
    cell = Cell()
    cell.part_kind = kind
    assert cell.start()
    advance(cell, lambda c: c.ok == 1)
    assert cell.total == 1 and cell.ng == 0
    assert cell.records[0]["kind"] == kind
    visited = [e["to"] for e in cell.events]
    assert visited == ["WAIT_PART", "VISION", "ROBOT_PICK", "GRIPPER_CLOSE", "ROBOT_PLACE",
                       "GRIPPER_OPEN", "QUALITY_CHECK", "RETURN_HOME", "COMPLETE", "WAIT_PART"]
    assert cell.robot.ready and not cell.robot.complete and not cell.holding


@pytest.mark.parametrize("fault", list(FAULTS))
def test_fault_latches_stops_outputs_and_recovers(fault):
    cell = Cell()
    cell.inject(fault)
    # Start interlock rejects a known fault. Inject during operation instead.
    assert not cell.start()
    cell.fault = None
    assert cell.start()
    cell.inject(fault)
    advance(cell, lambda c: c.state == State.ERROR)
    assert cell.alarm["code"] == FAULTS[fault][0]
    assert not cell.conveyor and not cell.robot.running and not cell.robot_start
    alarm = cell.alarm.copy()
    for _ in range(20):
        cell.tick()
    assert cell.alarm == alarm and not cell.start() and not cell.reset(clear_part=True)
    cell.fault = None
    assert cell.reset(clear_part=True)
    assert cell.state == State.IDLE and cell.ok == 0
    for _ in range(100):
        cell.tick()
    assert cell.state == State.IDLE  # No automatic restart after reset.
    assert cell.start()
    advance(cell, lambda c: c.ok == 1)


def test_safety_stop_preserves_held_part_until_operator_clearance():
    cell = Cell()
    cell.start()
    advance(cell, lambda c: c.holding)
    pose = cell.robot.pose
    cell.inject("door_open")
    cell.tick()
    assert cell.state == State.ERROR and cell.holding and cell.gripper
    assert cell.robot.pose == pose
    cell.fault = None
    assert not cell.reset()
    assert cell.reset(clear_part=True)
    assert cell.robot.pose == pose


def test_planning_failure_from_calibration_target_outside_workspace():
    cell = Cell()
    cell.start()
    advance(cell, lambda c: c.state == State.VISION)
    cell.calibration.matrix[0, 2] += 1000
    advance(cell, lambda c: c.state == State.ERROR)
    assert cell.alarm["code"] == "ALM-012"
    assert not cell.robot.running


def test_ambiguous_or_missing_part_rejected():
    cell = Cell()
    cell.start()
    advance(cell, lambda c: c.state == State.VISION)
    cell.image = np.zeros_like(cell.image)
    advance(cell, lambda c: c.state == State.ERROR)
    assert cell.alarm["code"] == "ALM-002"


def test_operator_stop_requires_reset():
    cell = Cell()
    cell.start()
    cell.stop()
    assert cell.state == State.ERROR and cell.alarm["code"] == "ALM-013"
    assert not cell.start()
    assert cell.reset()
    assert not cell.enabled


def test_seeded_batch_is_reproducible():
    a, b = run_cycles(10, 7), run_cycles(10, 7)
    assert a["records"] == b["records"]
    assert a["ok"] == 10
    assert a["max_localization_error_mm"] < .5
