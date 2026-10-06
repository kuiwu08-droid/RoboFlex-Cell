import pytest

from roboflex.motion import HOME, Pose, Robot, plan, segment_clear


def test_direct_collision_is_avoided_by_travel_height():
    a, b = Pose(300, -55, 25), Pose(480, -55, 25)
    assert not segment_clear(a, b)
    route = plan(a, b)
    assert all(segment_clear(x, y) for x, y in zip(route, route[1:]))
    assert route[1].z == route[2].z == 160


@pytest.mark.parametrize("target", [Pose(400, -55, 25), Pose(900, 0, 25), Pose(300, 0, -5), Pose(float("nan"), 0, 25)])
def test_bad_target_rejected(target):
    with pytest.raises(ValueError):
        plan(HOME, target)


def test_latched_handshake_no_early_complete_or_retrigger():
    robot = Robot()
    route = plan(HOME, Pose(220, -100, 25))
    robot.command(route)
    for _ in range(1000):
        robot.tick(.01, start=True)
    assert robot.running and not robot.complete
    robot.tick(.01, start=False)
    assert robot.complete and not robot.running and not robot.ready
    with pytest.raises(RuntimeError):
        robot.command(route)
    robot.tick(0, ack=True)
    assert robot.ready and not robot.complete


def test_speed_limit_and_stop_position_retained():
    robot = Robot()
    robot.command(plan(HOME, Pose(540, 100, 25)))
    robot.tick(.01)
    assert robot.pose.x - HOME.x <= robot.speed_mm_s * .01 + 1e-6
    pose = robot.pose
    robot.stop()
    robot.tick(1)
    assert robot.pose == pose
    robot.reset()
    assert robot.pose == pose
