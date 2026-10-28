"""Preserve verified native pit saves; never alter their world data."""
import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--build", type=int, required=True)
parser.add_argument("--reload", action="store_true")
parser.add_argument("--native-rules", action="store_true",
                    help="Require effective native support checks and absence of both global rule overrides.")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
kind = "reload" if args.reload else "run"
log = (root / f"outputs/mineral-pits-{kind}{args.build}.log").read_text(encoding="utf-8")
marker = ("ALL RELOAD, GATHERING AND FINITE DEPLETION CHECKS PASSED AND SAVED" if args.reload
          else "ALL PLACEMENT, GATHERING, ANIMATION AND PAUSE CHECKS PASSED AND SAVED")
assert marker in log and "[DeepFrontier Mineral Pits] FAILED:" not in log
if args.native_rules:
    assert "PASS unmodified ground-only foundations, non-supporting roofs, rejected roof paths/platforms and no power nodes" in log
    assert not any(line.startswith(("- No Build Restriction (", "- All Buildings Transfer Power ("))
                   for line in log.splitlines())
name = "Mineral pits continuity - verified" if args.reload else "Mineral pits - verified"
source = Path("C:/Users/Jordan/Documents/Timberborn/ExperimentalSaves/Industrial Acceptance") / f"{name}.timber"
with zipfile.ZipFile(source) as archive:
    world = json.loads(archive.read("world.json"))
entities = {entity["Id"]: entity for entity in world["Entities"]}
assert any(entity["Components"]["NamedEntity"]["EntityName"] == "Deep Frontier Acceptance Fixture"
           for entity in entities.values() if "NamedEntity" in entity["Components"])
expected = json.loads((root / "outputs/mineral-pit-reload-expectations.json").read_text())
reports = []
for index, (good, record) in enumerate(zip(("Sandstone", "Limestone"), expected, strict=True)):
    pit = entities[record["BuildingId"]]
    assert pit["Template"] == good + "Pit.IronTeeth"
    components = pit["Components"]
    assert components["PausableBuilding"]["Paused"] is True
    assert components["BlockObject"]["Coordinates"] == {"X": 159 + 7 * index, "Y": 160, "Z": 3}
    stock = components["Inventory:SimpleOutputInventory"]["Storage"]["Goods"]
    assert all(entry["Good"] == good for entry in stock)
    amount = sum(entry["Amount"] for entry in stock)
    if args.reload:
        assert record["DepositId"] not in entities
        assert amount == 24
        remaining = 0
    else:
        deposit = entities[record["DepositId"]]
        assert deposit["Template"] == good + "Outcrop"
        saved_yield = deposit["Components"]["Yielder:Mineral"]["Yield"]
        assert saved_yield["Good"] == good
        remaining = saved_yield["Amount"]
        assert 0 < remaining == record["Remaining"] < 24
        assert 0 < amount == record["Stock"] < 24
    assert amount + remaining == 24
    reports.append({"good": good, "buildingId": pit["Id"], "stock": amount, "remaining": remaining})
stem = "mineral-pits-continuity" if args.reload else "mineral-pits-verified"
preserved = root / f"outputs/{stem}-build{args.build}.timber"
shutil.copyfile(source, preserved)
report = {"build": args.build, "reload": args.reload,
          "nativeRulesVerified": args.native_rules,
          "sha256": hashlib.sha256(preserved.read_bytes()).hexdigest(),
          "preserved": str(preserved), "pits": reports,
          "scope": "Native harvesting of explicitly shortened 24-unit test deposits; normal authored yield is 600."}
(root / f"outputs/{stem}{args.build}.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
