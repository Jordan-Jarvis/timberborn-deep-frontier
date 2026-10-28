"""Verify and archive a native late-game acceptance run without modifying its save.

Usage: capture_lategame_acceptance.py --build N [--reload]
Exit code 0 only when the harness completed, saved, and recorded zero FAIL checks.
Individual FAIL records are printed and kept in the report either way.
"""
import argparse
import collections
import hashlib
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--build", type=int, required=True)
parser.add_argument("--reload", action="store_true")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
kind = "reload" if args.reload else "main"
log_path = root / f"outputs/lategame-{kind}{args.build}.log"
log = log_path.read_text(encoding="utf-8", errors="replace")
tag = "[DeepFrontier Lategame]"

harness_error = [line for line in log.splitlines() if f"{tag} FAILED:" in line]
assert not harness_error, "Harness failed: " + harness_error[0]
assert not any(line.startswith(("- No Build Restriction (", "- All Buildings Transfer Power ("))
               for line in log.splitlines()), "A placement-cheat mod was active"
done = re.search(rf"{re.escape(tag)} COMPLETE {kind.upper()} passed=(\d+) failed=(\d+) skipped=(\d+) AND SAVED", log)
assert done, f"No completed and saved {kind} run in {log_path}"
passed, failed, skipped = map(int, done.groups())

results = json.loads((root / f"outputs/lategame-acceptance-{kind}.json").read_text(encoding="utf-8"))
counts = collections.Counter(r["Status"] for r in results["results"])
assert (counts["PASS"], counts["FAIL"], counts["SKIP"]) == (passed, failed, skipped), "Results file differs from the log"

save_name = "Lategame acceptance - reload" if args.reload else "Lategame acceptance - main"
source = Path("C:/Users/Jordan/Documents/Timberborn/ExperimentalSaves/Industrial Acceptance") / f"{save_name}.timber"
with zipfile.ZipFile(source) as archive:
    world = json.loads(archive.read("world.json"))
entities = {e["Id"]: e for e in world["Entities"]}
assert any(e["Components"].get("NamedEntity", {}).get("EntityName") == "Deep Frontier Acceptance Fixture"
           for e in entities.values()), "Saved settlement lost its fixture marker"
expected = json.loads((root / "outputs/lategame-reload-expectations.json").read_text(encoding="utf-8"))
missing = []
for record in expected["Entities"]:
    entity = entities.get(record["Id"])
    if entity is None or entity["Template"] != record["Template"]:
        missing.append(record)
        continue
    c = entity["Components"]["BlockObject"]["Coordinates"]
    if c != {axis.upper(): record["Coordinates"][axis] for axis in ("x", "y", "z")}:
        missing.append(record)
assert not missing, f"{len(missing)} recorded entities missing or moved in the native save, e.g. {missing[0]}"

stem = f"lategame-{kind}-build{args.build}"
preserved = root / f"outputs/{stem}.timber"
shutil.copyfile(source, preserved)
sha256 = hashlib.sha256(preserved.read_bytes()).hexdigest()
if not args.reload:
    (root / "outputs/lategame-save-checkpoint.json").write_text(json.dumps(
        {"SourceSha256": sha256, "SourceBuild": args.build}, indent=2) + "\n")

failures = [r for r in results["results"] if r["Status"] == "FAIL"]
by_building = collections.defaultdict(list)
for r in failures:
    by_building[r["Building"]].append(f'{r["Check"]}: {r["Detail"]}')
report = {
    "build": args.build, "mode": kind, "save": str(preserved), "sha256": sha256,
    "entitiesVerifiedInSave": len(expected["Entities"]),
    "passed": passed, "failed": failed, "skipped": skipped,
    "subjects": results["subjects"],
    "failuresByBuilding": by_building,
    "skips": [f'{r["Building"]} {r["Check"]}: {r["Detail"]}' for r in results["results"] if r["Status"] == "SKIP"],
}
(root / f"outputs/{stem}-report.json").write_text(json.dumps(report, indent=2) + "\n")
print(f"{kind}: passed={passed} failed={failed} skipped={skipped}; {len(expected['Entities'])} entities verified in {source.name}")
for building, items in sorted(by_building.items()):
    print(f"FAIL {building}")
    for item in items:
        print(f"    {item}")
sys.exit(1 if failed else 0)
