"""Monte Carlo planar calibration with noisy correspondences and holdout points."""

import json
from pathlib import Path

import cv2
import numpy as np

from roboflex.vision import Calibration


def main():
    rng = np.random.default_rng(42)
    true_h = np.array([[.5, .02, 190], [.03, -.5, 210], [.00005, .0001, 1.]])
    grid = np.array([(u, v) for v in (30, 170, 310, 450) for u in (30, 180, 330, 480, 610)], dtype=float)
    robot_ref = cv2.perspectiveTransform(grid[None], true_h)[0]
    records = []
    for trial in range(20):
        measured = grid + rng.normal(0, .6, grid.shape)
        calibration = Calibration(measured, robot_ref)
        actual = rng.uniform((80, 80), (560, 400), (50, 2))
        detected = actual + rng.normal(0, .6, actual.shape)
        truth = cv2.perspectiveTransform(actual[None], true_h)[0]
        estimates = np.array([calibration.map(p) for p in detected])
        errors = np.linalg.norm(estimates - truth, axis=1)
        records.append({"trial": trial, "fit_rmse_mm": calibration.fit_rmse_mm,
                        "holdout_errors_mm": errors.tolist()})
    errors = np.array([v for record in records for v in record["holdout_errors_mm"]])
    result = {"scope": "synthetic planar projective geometry; noisy calibration and detections",
              "seed": 42, "trials": 20, "points_per_calibration": 20, "holdout_points_per_trial": 50,
              "pixel_noise_sigma": .6, "true_h": true_h.tolist(),
              "mean_holdout_error_mm": float(errors.mean()), "p95_holdout_error_mm": float(np.percentile(errors, 95)),
              "max_holdout_error_mm": float(errors.max()), "records": records}
    target = Path(__file__).resolve().parents[1] / "docs/evidence/calibration.json"
    target.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "records"}, indent=2))


if __name__ == "__main__":
    main()
