import argparse
import csv
import json
from pathlib import Path
import platform
import sys

import cv2
import numpy as np

from .controller import run_cycles
from .server import serve


def main():
    parser = argparse.ArgumentParser(description="RoboFlex Cell software-in-the-loop workstation")
    commands = parser.add_subparsers(dest="command", required=True)
    hmi = commands.add_parser("serve", help="Run local HMI")
    hmi.add_argument("--port", type=int, default=8080)
    hmi.add_argument("--seed", type=int, default=42)
    benchmark = commands.add_parser("benchmark", help="Run deterministic synthetic cycles")
    benchmark.add_argument("--cycles", type=int, default=100)
    benchmark.add_argument("--seed", type=int, default=42)
    benchmark.add_argument("--output", type=Path, default=Path("artifacts/benchmark"))
    args = parser.parse_args()
    if args.command == "serve":
        serve(args.port, args.seed)
    else:
        result = run_cycles(args.cycles, args.seed)
        result["environment"] = {"python": sys.version.split()[0], "opencv": cv2.__version__,
                                 "numpy": np.__version__, "platform": platform.platform()}
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        with (args.output / "cycles.csv").open("w", newline="", encoding="utf-8") as stream:
            fields = ["cycle", "kind", "cycle_time_s", "localization_error_mm", "path_length_mm"]
            writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(result["records"])
        print(json.dumps({k: v for k, v in result.items() if k != "records"}, indent=2))


if __name__ == "__main__":
    main()
