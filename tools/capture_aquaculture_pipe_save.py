"""Preserve a completed native pipe fixture and capture exact reload expectations."""
import argparse
import hashlib
import json
import math
import re
import shutil
import zipfile
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--build", required=True, type=int)
parser.add_argument("--continuity", action="store_true")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
log_name = f"aquaculture-pipes-reload{args.build}.log" if args.continuity else f"aquaculture-pipes{args.build}.log"
log = (root / "outputs" / log_name).read_text(encoding="utf-8")
success = ("ALL RELOAD, VOLUME AND PIPE-FED PRODUCTION CHECKS PASSED AND SAVED" if args.continuity
           else "ALL DELIVERY, CAPACITY, VALVE AND RESERVOIR CHECKS PASSED AND SAVED")
assert success in log
save_name = "Aquaculture pipe continuity - verified" if args.continuity else "Aquaculture pipes - verified"
source = Path("C:/Users/Jordan/Documents/Timberborn/ExperimentalSaves/Industrial Acceptance") / f"{save_name}.timber"
with zipfile.ZipFile(source) as archive:
    world = json.loads(archive.read("world.json"))
assert any(e["Components"]["NamedEntity"]["EntityName"] == "Deep Frontier Acceptance Fixture"
           for e in world["Entities"] if "NamedEntity" in e["Components"])


def entity_at(template, coordinate):
    matches = [e for e in world["Entities"] if e["Template"] == template
               and e["Components"]["BlockObject"]["Coordinates"] == dict(zip(("X", "Y", "Z"), coordinate))]
    assert len(matches) == 1, (template, coordinate)
    return matches[0]


records = []
totals = {}
for template, coordinate, capacity, pipe_positions, tank_position in [
    ("FisheryWorks.IronTeeth", (159, 160, 3), 90,
     [(164, 170, 3), (164, 171, 3), (164, 172, 3)], (164, 173, 3)),
    # Compact 7x7 hatchery (2026-10-26): intake (6,2,1), line one cell west.
    ("FishHatchery.IronTeeth", (187, 156, 3), 60,
     [(194, 158, 3), (195, 158, 3), (196, 158, 3)], (197, 158, 3)),
]:
    workshop = entity_at(template, coordinate)
    assert workshop["Components"]["PausableBuilding"]["Paused"]
    goods = workshop["Components"]["Inventory:Manufactory"]["Storage"]["Goods"]
    assert next(g["Amount"] for g in goods if g["Good"] == "Water") == capacity
    tank = entity_at("MediumTank.IronTeeth", tank_position)
    tank_goods = tank["Components"]["Inventory:Stockpile"]["Storage"]["Goods"]
    assert len(tank_goods) == 1 and tank_goods[0]["Good"] == "Water"
    pending = tank["Components"]["PipeTank"]["PendingVolume"]
    assert math.isfinite(pending)
    tank_volume = tank_goods[0]["Amount"] * 0.2 + pending
    pipe_records = []
    for pipe_name, position in zip(
        ("HorizontalPipeValve.IronTeeth", "HorizontalPipe.IronTeeth", "HorizontalPipePump.IronTeeth"),
        pipe_positions,
    ):
        pipe = entity_at(pipe_name, position)
        state = pipe["Components"]["BuildingPipe"]
        assert state["FluidGoodId"] == "Water"
        assert state["MixGoodA"] == "" and state["MixGoodB"] == ""
        volume = state["FluidHeight"]
        assert math.isfinite(volume) and 0 <= volume <= 1
        pipe_records.append({"EntityId": pipe["Id"], "GoodId": "Water", "Volume": volume})
        if pipe_name == "HorizontalPipeValve.IronTeeth":
            valve = pipe["Components"]["ValvePipe"]
            assert valve["InletEnabled"] is True and valve["OutletEnabled"] is False
            assert valve["ExtractBuffer"] == 0 and valve["ExtractBufferGoodId"] == ""
    assert sum(p["Volume"] for p in pipe_records) > 0
    total = capacity + 5 * (tank_volume + sum(p["Volume"] for p in pipe_records))
    expected_total = 290
    if args.continuity:
        matches = re.findall(re.escape(template) + r" completed (\d+) native batches using (\d+) pipe-fed Water", log)
        assert len(matches) == 1, (template, matches)
        batches, consumed = map(int, matches[0])
        assert batches >= (2 if template == "FisheryWorks.IronTeeth" else 1)
        assert consumed > 0
        expected_total = 270 - consumed
        totals[template] = {"batches": batches, "recipeWaterConsumed": consumed,
                            "explicitReloadWithdrawals": 20, "savedWaterEquivalent": total}
    assert abs(total - expected_total) < 0.02, (template, total, expected_total)
    records.append({
        "WorkshopId": workshop["Id"], "TankId": tank["Id"],
        "Stocks": [{"Name": g["Good"], "Amount": g["Amount"]} for g in goods],
        "TankWater": tank_goods[0]["Amount"], "TankVolume": tank_volume, "Pipes": pipe_records,
    })

stem = "aquaculture-pipe-continuity" if args.continuity else "aquaculture-pipes"
preserved = root / f"outputs/{stem}-build{args.build}.timber"
shutil.copyfile(source, preserved)
if not args.continuity:
    (root / "outputs/aquaculture-pipe-reload-expectations.json").write_text(json.dumps(records, indent=2) + "\n")
report = {"build": args.build, "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
          "preserved": str(preserved), "lines": records, "recipeChecks": totals}
report_name = f"aquaculture-pipe-continuity{args.build}.json" if args.continuity else f"aquaculture-pipe-source{args.build}.json"
(root / "outputs" / report_name).write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
