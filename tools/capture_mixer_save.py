"""Preserve native mixer acceptance evidence, without modifying the save."""
import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--build", required=True, type=int)
parser.add_argument("--reload", action="store_true")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
kind = "reload" if args.reload else "run"
log = (root / f"outputs/mixer-{kind}{args.build}.log").read_text(encoding="utf-8")
success = ("ALL RELOAD AND PRODUCTION CHECKS PASSED AND SAVED" if args.reload
           else "ALL PLACEMENT, WALKING, ANIMATION AND PRODUCTION CHECKS PASSED AND SAVED")
assert success in log and "[DeepFrontier Mixer] FAILED:" not in log
save_name = "Mixer continuity - verified" if args.reload else "Mixer acceptance - verified"
source = Path("C:/Users/Jordan/Documents/Timberborn/ExperimentalSaves/Industrial Acceptance") / f"{save_name}.timber"
with zipfile.ZipFile(source) as archive:
    world = json.loads(archive.read("world.json"))
assert any(e["Components"]["NamedEntity"]["EntityName"] == "Deep Frontier Acceptance Fixture"
           for e in world["Entities"] if "NamedEntity" in e["Components"])
matches = [e for e in world["Entities"] if e["Template"] == "ConcreteMixer.IronTeeth"]
assert len(matches) == 1
mixer = matches[0]
assert mixer["Components"]["PausableBuilding"]["Paused"] is True
assert mixer["Components"]["BlockObject"]["Coordinates"] == {"X": 159, "Y": 160, "Z": 3}
expected = json.loads((root / "outputs/mixer-reload-expectations.json").read_text())
assert mixer["Id"] == expected["EntityId"]
stock = mixer["Components"]["Inventory:Manufactory"]["Storage"]["Goods"]
if not args.reload:
    for good, amount in expected["Stock"].items():
        assert sum(g["Amount"] for g in stock if g["Good"] == good) == amount, good
assert any(e["Template"] == "Path"
           and e["Components"]["BlockObject"]["Coordinates"] == {"X": 160, "Y": 160, "Z": 3}
           for e in world["Entities"])
stem = "mixer-continuity" if args.reload else "mixer-verified"
preserved = root / f"outputs/{stem}-build{args.build}.timber"
shutil.copyfile(source, preserved)
report = {"build": args.build, "reload": args.reload,
          "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
          "preserved": str(preserved), "mixer": mixer}
(root / f"outputs/{stem}{args.build}.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({k: v for k, v in report.items() if k != "mixer"}, indent=2))
