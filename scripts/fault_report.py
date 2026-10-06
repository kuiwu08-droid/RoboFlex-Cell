"""Record each executable injected fault, output stop and one-cycle recovery."""

import json
from pathlib import Path

from roboflex.controller import Cell, FAULTS, State


def main():
    results = []
    for fault, (code, _) in FAULTS.items():
        cell = Cell(42)
        cell.start()
        cell.inject(fault)
        for _ in range(4000):
            cell.tick()
            if cell.state == State.ERROR:
                break
        assert cell.state == State.ERROR and cell.alarm["code"] == code
        assert not cell.robot.running and not cell.robot_start and not cell.conveyor
        record = {"fault": fault, "alarm": cell.alarm.copy(), "scan_time_s": cell.clock,
                  "outputs_stopped": True, "reset_with_cause_present_rejected": not cell.reset(clear_part=True)}
        cell.fault = None
        assert cell.reset(clear_part=True)
        record["reset_state"] = cell.state.value
        assert cell.start()
        for _ in range(4000):
            cell.tick()
            if cell.ok == 1:
                break
        assert cell.ok == 1
        record["recovered_ok_cycles"] = cell.ok
        results.append(record)
    target = Path(__file__).resolve().parents[1] / "docs/evidence/faults.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Verified and recorded {len(results)} fault/recovery scenarios")


if __name__ == "__main__":
    main()
