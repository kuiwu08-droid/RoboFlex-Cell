"""Planar eye-to-hand calibration and contour-based part detection.

All coordinates refer to a fixed, undistorted work plane. This is not a 3D
hand-eye calibration. A real lens must be calibrated/undistorted first.
"""

from dataclasses import dataclass
import math

import cv2
import numpy as np


@dataclass(frozen=True)
class Detection:
    kind: str
    pixel: tuple[float, float]
    angle_deg: float
    area_px: float


class Calibration:
    def __init__(self, pixel_points, robot_points):
        pixels = np.asarray(pixel_points, dtype=np.float64)
        robot = np.asarray(robot_points, dtype=np.float64)
        if pixels.shape != robot.shape or pixels.ndim != 2 or pixels.shape[1] != 2 or len(pixels) < 4:
            raise ValueError("Need at least four paired 2D calibration points")
        if not np.isfinite(pixels).all() or not np.isfinite(robot).all():
            raise ValueError("Calibration points must be finite")
        self.matrix, _ = cv2.findHomography(pixels, robot, method=0)
        if self.matrix is None or not np.isfinite(self.matrix).all() or np.linalg.matrix_rank(self.matrix) < 3:
            raise ValueError("Degenerate calibration geometry")
        self.hull = cv2.convexHull(pixels.astype(np.float32))
        fitted = cv2.perspectiveTransform(pixels[None], self.matrix)[0]
        self.fit_rmse_mm = float(np.sqrt(np.mean(np.sum((fitted - robot) ** 2, axis=1))))

    def map(self, point):
        point = np.asarray(point, dtype=np.float64)
        if point.shape != (2,) or not np.isfinite(point).all():
            raise ValueError("Expected finite (u, v)")
        if cv2.pointPolygonTest(self.hull, tuple(map(float, point)), False) < 0:
            raise ValueError("Target outside calibrated region")
        result = cv2.perspectiveTransform(point.reshape(1, 1, 2), self.matrix)[0, 0]
        if not np.isfinite(result).all():
            raise ValueError("Invalid projective mapping")
        return tuple(map(float, result))

    def angle(self, pixel, angle_deg):
        """Map a local image axis; do not reuse the image angle as a base angle."""
        theta = math.radians(angle_deg)
        p = np.asarray([pixel, (pixel[0] + math.cos(theta), pixel[1] + math.sin(theta))], dtype=np.float64)
        q = cv2.perspectiveTransform(p[None], self.matrix)[0]
        return math.degrees(math.atan2(q[1, 1] - q[0, 1], q[1, 0] - q[0, 0])) % 180


def detect(image):
    """Return all non-border foreground parts; holes distinguish rings.

    Circular parts have no meaningful yaw. Square yaw is modulo 90 degrees.
    """
    if image is None or image.size == 0:
        raise ValueError("Camera returned an empty image")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, mask = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is None:
        return []
    results = []
    height, width = gray.shape
    for i, contour in enumerate(contours):
        if hierarchy[0, i, 3] != -1:
            continue
        area = cv2.contourArea(contour)
        x, y, w, h = cv2.boundingRect(contour)
        if area < 600 or x <= 0 or y <= 0 or x + w >= width or y + h >= height:
            continue
        moments = cv2.moments(contour)
        pixel = (moments["m10"] / moments["m00"], moments["m01"] / moments["m00"])
        perimeter = cv2.arcLength(contour, True)
        circularity = 4 * math.pi * area / perimeter**2
        child = hierarchy[0, i, 2]
        has_hole = child != -1 and cv2.contourArea(contours[child]) / area > 0.1
        if has_hole:
            kind, angle = "ring", 0.0
        elif circularity > 0.83:
            kind, angle = "circle", 0.0
        else:
            polygon = cv2.approxPolyDP(contour, 0.03 * perimeter, True)
            if len(polygon) != 4:
                continue
            (_, _), (rw, rh), angle = cv2.minAreaRect(contour)
            if min(rw, rh) / max(rw, rh) < 0.85:
                continue
            kind, angle = "square", float(angle % 90)
        results.append(Detection(kind, pixel, angle, area))
    return sorted(results, key=lambda d: (d.pixel[0], d.pixel[1]))


def default_calibration():
    # Image x points right; image y points down. Base Y points up.
    return Calibration([(20, 20), (620, 20), (620, 460), (20, 460)],
                       [(200, 200), (500, 200), (500, -20), (200, -20)])


def synthetic_frame(rng, kind=None):
    """Create one known part with noise. Returns image and independent ground truth."""
    kind = kind or str(rng.choice(["circle", "square", "ring"]))
    u, v = int(rng.integers(100, 540)), int(rng.integers(100, 380))
    angle = float(rng.uniform(0, 90))
    image = np.full((480, 640), 24, np.uint8)
    if kind in ("circle", "ring"):
        cv2.circle(image, (u, v), 28, 220, -1)
        if kind == "ring":
            cv2.circle(image, (u, v), 13, 24, -1)
    elif kind == "square":
        box = cv2.boxPoints(((u, v), (50, 50), angle))
        cv2.fillConvexPoly(image, np.round(box).astype(np.int32), 220)
    else:
        raise ValueError(f"Unknown part kind: {kind}")
    noise = rng.normal(0, 5, image.shape)
    image = np.clip(image.astype(float) + noise, 0, 255).astype(np.uint8)
    truth = {"kind": kind, "pixel": [u, v], "xy_mm": [190 + u * 0.5, 210 - v * 0.5], "angle_deg": angle}
    return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR), truth
