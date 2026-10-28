"""Verify and archive a native rocket-program run (main sequence or one checkpoint reload).

Usage: capture_lategame_rocket.py --build N [--checkpoint main|preparing|flight|refurbishing]
The main capture archives the three checkpoint saves and records their hashes for the reloads.
Exit code 0 only when the run completed with zero FAIL checks.
"""
import argparse
import collections
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--build", type=int, required=True)
parser.add_argument("--checkpoint", default="main", choices=["main", "preparing", "flight", "refurbishing"])
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
mode = args.checkpoint
log = (root / f"outputs/lategame-rocket-{mode}{args.build}.log").read_text(encoding="utf-8", errors="replace")
tag = "[DeepFrontier Rocket]"
errors = [line for line in log.splitlines() if f"{tag} FAILED:" in line]
assert not errors, "Harness failed: " + errors[0]
assert not any(line.startswith(("- No Build Restriction (", "- All Buildings Transfer Power ("))
               for line in log.splitlines()), "A placement-cheat mod was active"
done = re.search(rf"{re.escape(tag)} (COMPLETE|INCOMPLETE) {mode.upper()} passed=(\d+) failed=(\d+) skipped=(\d+)", log)
assert done, f"No finished rocket {mode} run in the log"
complete = done.group(1) == "COMPLETE"
passed, failed, skipped = map(int, done.groups()[1:])
results = json.loads((root / f"outputs/lategame-rocket-{mode}-results.json").read_text(encoding="utf-8"))
counts = collections.Counter(r["Status"] for r in results["results"])
assert (counts["PASS"], counts["FAIL"], counts["SKIP"]) == (passed, failed, skipped), "Results file differs from the log"

saves = Path("C:/Users/Jordan/Documents/Timberborn/ExperimentalSaves/Industrial Acceptance")
archived = {}
if mode == "main":
    for checkpoint in ("preparing", "flight", "refurbishing"):
        if f"{tag} CHECKPOINT {checkpoint} SAVED" not in log:
            continue
        source = saves / f"Lategame rocket - {checkpoint}.timber"
        target = root / f"outputs/lategame-rocket-{checkpoint}-build{args.build}.timber"
        shutil.copyfile(source, target)
        archived[checkpoint] = hashlib.sha256(target.read_bytes()).hexdigest()
    (root / "outputs/lategame-rocket-checkpoints.json").write_text(
        json.dumps({k.lower(): v.upper() for k, v in archived.items()} | {"build": args.build}, indent=2) + "\n")

failures = [f'{r["Check"]}: {r["Detail"]}' for r in results["results"] if r["Status"] == "FAIL"]
report = {"build": args.build, "mode": mode, "complete": complete, "passed": passed, "failed": failed,
          "skipped": skipped, "checkpointSaves": archived, "failures": failures,
          "skips": [f'{r["Check"]}: {r["Detail"]}' for r in results["results"] if r["Status"] == "SKIP"]}
(root / f"outputs/lategame-rocket-{mode}-build{args.build}-report.json").write_text(json.dumps(report, indent=2) + "\n")
print(f"rocket {mode}: {'complete' if complete else 'INCOMPLETE'} passed={passed} failed={failed} skipped={skipped}"
      + (f"; checkpoints archived: {', '.join(archived)}" if archived else ""))
for failure in failures:
    print("FAIL " + failure)
sys.exit(0 if complete and not failed else 1)
