"""Archive a successful native structural fixture without modifying its save."""
import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--build", type=int, required=True)
parser.add_argument("--reload", action="store_true")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
kind = "reload" if args.reload else "run"
log = (root / f"outputs/structures-{kind}{args.build}.log").read_text(encoding="utf-8")
phase = "RELOAD" if args.reload else "PLACEMENT"
assert f"[DeepFrontier Structures] ALL {phase}, WATER AND WALKING CHECKS PASSED AND SAVED" in log
assert "[DeepFrontier Structures] FAILED:" not in log
assert not any(line.startswith(("- No Build Restriction (", "- All Buildings Transfer Power ("))
               for line in log.splitlines())
assert log.count("[DeepFrontier Structures] PASS actual beaver reached ") == 6
if args.reload:
    assert "exact structural identities, positions and retained basin water restored" in log
else:
    assert "concrete overflow matches the vanilla dam" in log
    assert "settled below-crest pool retains water with native dam parity" in log

name = "Structures continuity - verified" if args.reload else "Structures - verified"
source = Path("C:/Users/Jordan/Documents/Timberborn/ExperimentalSaves/Industrial Acceptance") / f"{name}.timber"
with zipfile.ZipFile(source) as archive:
    world = json.loads(archive.read("world.json"))
entities = {e["Id"]: e for e in world["Entities"]}
expected = json.loads((root / "outputs/structural-reload-expectations.json").read_text())
assert any(e["Components"]["NamedEntity"]["EntityName"] == "Deep Frontier Acceptance Fixture"
           for e in entities.values() if "NamedEntity" in e["Components"])
counts = {}
for record in expected["Entities"]:
    entity = entities[record["Id"]]
    assert entity["Template"] == record["Template"]
    coordinates = entity["Components"]["BlockObject"]["Coordinates"]
    assert coordinates == {axis.upper(): record["Coordinates"][axis] for axis in ("x", "y", "z")}
    counts[record["Template"]] = counts.get(record["Template"], 0) + 1
for ident in json.loads((root / "tools/structural_content.json").read_text())["buildings"]:
    assert counts[ident["id"] + ".IronTeeth"] > 0
# Native WaterColumnPackedListSerializer writes one colon-delimited token per
# column. MapIndexService.Pack removes the border and orders x, then y, then
# column ordinal. This fixture's two open pools occupy ordinal zero, floor 4.
size = world["Singletons"]["MapSize"]["Size"]
water = world["Singletons"]["WaterMapNew"]
columns = water["WaterColumns"]["Array"].split()
assert len(columns) == size["X"] * size["Y"] * water["Levels"]
saved_depths = {}
for x, label in ((143, "concrete"), (149, "native")):
    token = columns[170 * size["X"] + x]
    fields = token.split(":")
    assert len(fields) == 5 and int(fields[3]) == 4, (label, token)
    saved_depths[label] = float(fields[0])
assert .30 < saved_depths["concrete"] < .55
assert abs(saved_depths["concrete"] - saved_depths["native"]) < .025
stem = "structures-continuity" if args.reload else "structures-verified"
preserved = root / f"outputs/{stem}-build{args.build}.timber"
shutil.copyfile(source, preserved)
sha256 = hashlib.sha256(preserved.read_bytes()).hexdigest()
checkpoint = root / "outputs/structural-water-checkpoint.json"
if args.reload:
    original = json.loads(checkpoint.read_text())
    assert 0 <= original["WaterDepth"] - saved_depths["concrete"] < .02
else:
    # The authoritative reload expectation comes from the completed native
    # artifact, never a pre-save thread-safe simulation snapshot.
    checkpoint.write_text(json.dumps({
        "WaterDepth": saved_depths["concrete"], "ControlWaterDepth": saved_depths["native"],
        "SourceSha256": sha256, "SourceBuild": args.build,
    }, indent=2) + "\n")
report = {
    "build": args.build, "reload": args.reload,
    "sha256": sha256,
    "preserved": str(preserved), "entities": len(expected["Entities"]),
    "templates": counts, "savedBasinDepths": saved_depths,
    "actualWalkingDestinations": 6,
    "scope": "Native support, water behavior, traversal and identity continuity; seeded fixture, not economic balance.",
}
(root / f"outputs/{stem}{args.build}.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
