"""Preserve completed native transport saves and exact expectation evidence."""
import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--build", type=int, required=True)
parser.add_argument("--reload", action="store_true")
parser.add_argument("--power-lines", action="store_true")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
kind = "reload" if args.reload else "run"
test = "factory-power-lines" if args.power_lines else "factory-transport"
log = (root / f"outputs/{test}-{kind}{args.build}.log").read_text()
marker = "ALL " + ("RELOAD AND " if args.reload else "") + ("POWER LINES, " if args.power_lines else "") + "TRANSPORT AND PRODUCTION CHECKS PASSED AND SAVED"
assert marker in log and "[DeepFrontier Factory Transport] FAILED:" not in log
label = "Factory power lines" if args.power_lines else "Factory transport"
name = label + (" continuity - verified" if args.reload else " - verified")
source = Path("C:/Users/Jordan/Documents/Timberborn/ExperimentalSaves/Industrial Acceptance") / f"{name}.timber"
with zipfile.ZipFile(source) as archive:
    world = json.loads(archive.read("world.json"))
assert any(e["Components"]["NamedEntity"]["EntityName"] == "Deep Frontier Acceptance Fixture"
           for e in world["Entities"] if "NamedEntity" in e["Components"])
expected = json.loads((root / f"outputs/{test}-expectations.json").read_text())
entities = {e["Id"]: e for e in world["Entities"]}
mixer = entities[expected["MixerId"]]
assert mixer["Template"] == "ConcreteMixer.IronTeeth"
assert mixer["Components"]["PausableBuilding"]["Paused"]
assert len(expected["Belts"]) == 6 and len(expected["Pipes"]) == 3
for record in [*expected["Belts"], *expected["Pipes"], *expected["Stores"]]:
    assert record["EntityId"] in entities
assert expected["TankId"] in entities
if args.power_lines:
    assert entities[expected["RemoteSourceId"]]["Template"] == "DevPowerGenerator"
    connections = world["Singletons"]["PowerLineConnectionService"]["Connections"].split("|")
    assert len(connections) == 2
    assert set(connections) == {expected["RemoteSourceId"], expected["MixerId"]}
if not args.reload:
    stock = mixer["Components"]["Inventory:Manufactory"]["Storage"]["Goods"]
    assert sum(g["Amount"] for g in stock) == sum(g["Amount"] for g in expected["MixerStock"])
    for good in expected["MixerStock"]:
        assert sum(g["Amount"] for g in stock if g["Good"] == good["Name"]) == good["Amount"]
stem = test + ("-continuity" if args.reload else "")
preserved = root / f"outputs/{stem}-build{args.build}.timber"
shutil.copyfile(source, preserved)
report = {
    "build": args.build, "reload": args.reload,
    "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "preserved": str(preserved), "mixer": mixer,
    "stores": [entities[r["EntityId"]] for r in expected["Stores"]],
    "belts": [entities[r["EntityId"]] for r in expected["Belts"]],
    "pipes": [entities[r["EntityId"]] for r in expected["Pipes"]],
    "tank": entities[expected["TankId"]],
}
(root / f"outputs/{stem}{args.build}.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({k: report[k] for k in ("build", "reload", "sha256", "preserved")}, indent=2))
