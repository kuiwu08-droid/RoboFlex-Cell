import cv2
import numpy as np
import pytest

from roboflex.vision import Calibration, default_calibration, detect, synthetic_frame


@pytest.mark.parametrize("kind", ["circle", "square", "ring"])
def test_noisy_part_position_and_class(kind):
    rng = np.random.default_rng(91)
    calibration = default_calibration()
    for _ in range(20):
        frame, truth = synthetic_frame(rng, kind)
        parts = detect(frame)
        assert len(parts) == 1
        assert parts[0].kind == kind
        assert np.linalg.norm(np.asarray(calibration.map(parts[0].pixel)) - truth["xy_mm"]) < 0.5
        if kind == "square":
            difference = abs((parts[0].angle_deg - truth["angle_deg"] + 45) % 90 - 45)
            assert difference < 2


def test_empty_scene():
    assert detect(np.zeros((480, 640, 3), np.uint8)) == []
    with pytest.raises(ValueError):
        detect(None)


def test_multiple_parts_returned_for_controller_rejection():
    image = np.zeros((480, 640, 3), np.uint8)
    cv2.circle(image, (100, 200), 28, (220, 220, 220), -1)
    cv2.circle(image, (400, 200), 28, (220, 220, 220), -1)
    assert len(detect(image)) == 2


def test_calibration_on_independent_holdout_points():
    pixels = [(20, 20), (620, 20), (620, 460), (20, 460), (320, 240)]
    truth_matrix = np.array([[0.5, 0.02, 190], [0.03, -0.5, 210], [0.00005, 0.0001, 1.]])
    robot = cv2.perspectiveTransform(np.array([pixels], dtype=float), truth_matrix)[0]
    calibration = Calibration(pixels, robot)
    for pixel in [(100, 100), (320, 180), (480, 360)]:
        expected = cv2.perspectiveTransform(np.array([[pixel]], dtype=float), truth_matrix)[0, 0]
        assert np.allclose(calibration.map(pixel), expected, atol=1e-4)


def test_angle_is_transformed_to_robot_base():
    calibration = default_calibration()
    assert calibration.angle((320, 240), 30) == pytest.approx(150)


@pytest.mark.parametrize("pixel", [(0, 0), (640, 480), (float("nan"), 100)])
def test_outside_calibration_or_invalid_point_rejected(pixel):
    with pytest.raises(ValueError):
        default_calibration().map(pixel)


def test_degenerate_calibration_rejected():
    with pytest.raises(ValueError):
        Calibration([(0, 0), (1, 1), (2, 2), (3, 3)], [(0, 0), (1, 1), (2, 2), (3, 3)])
