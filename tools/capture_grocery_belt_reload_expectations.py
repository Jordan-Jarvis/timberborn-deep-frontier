"""Read and preserve the completed native grocery conveyor fixture."""
import argparse
import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--build", required=True, type=int)
parser.add_argument("--continuity", action="store_true")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
save_name = "Grocery belt continuity - verified" if args.continuity else "Grocery belts - verified"
source = Path("C:/Users/Jordan/Documents/Timberborn/ExperimentalSaves/Industrial Acceptance") / f"{save_name}.timber"
log_name = f"grocery-belts-reload{args.build}.log" if args.continuity else f"grocery-belts{args.build}.log"
log = (root / "outputs" / log_name).read_text(encoding="utf-8")
success = ("ALL RELOAD, QUEUE AND RESUMED DELIVERY CHECKS PASSED AND SAVED" if args.continuity
           else "ALL DELIVERY, CAPACITY, POWER AND STOCK CUSTODY CHECKS PASSED AND SAVED")
assert success in log
with zipfile.ZipFile(source) as archive:
    world = json.loads(archive.read("world.json"))
assert any(e["Components"]["NamedEntity"]["EntityName"] == "Deep Frontier Acceptance Fixture"
           for e in world["Entities"] if "NamedEntity" in e["Components"])

def entity_at(template, x, y, z):
    matches = [e for e in world["Entities"] if e["Template"] == template
               and e["Components"]["BlockObject"]["Coordinates"] == {"X": x, "Y": y, "Z": z}]
    assert len(matches) == 1, (template, x, y, z)
    return matches[0]

def stock_record(entity, component):
    goods = entity["Components"][component]["Storage"]["Goods"]
    assert goods and all(g["Amount"] > 0 for g in goods)
    return {"EntityId": entity["Id"], "Stocks": [
        {"Name": g["Good"], "Amount": g["Amount"]} for g in goods]}

if args.continuity:
    expected = json.loads((root / "outputs/grocery-belt-reload-expectations.json").read_text())
    shop = entity_at("GroceryStore.IronTeeth", 159, 160, 3)
    assert shop["Id"] == expected["Shop"]["EntityId"]
    assert shop["Components"]["PausableBuilding"]["Paused"]
    shop_record = stock_record(shop, "Inventory:GroceryStore")
    eaten = -sum(int(n) for n in re.findall(r"RELOAD STOCK Consumed corn=(-\d+)", log))
    delivered = sum(int(n) for n in re.findall(r"RELOAD STOCK None corn=(\d+)", log))
    supply = sum(g["Amount"] for g in expected["Donor"]["Stocks"] if g["Name"] == "CornRation")
    supply += sum(len(b["Items"]) for b in expected["Incoming"])
    assert delivered == supply
    corn = next(g["Amount"] for g in shop_record["Stocks"] if g["Name"] == "CornRation")
    assert corn + eaten == expected["CornTotal"] - 30
    by_id = {e["Id"]: e for e in world["Entities"]}
    for key in ("Donor", "Receiver"):
        assert "Inventory:Stockpile" not in by_id[expected[key]["EntityId"]]["Components"]
    for belt in expected["Incoming"] + expected["Outgoing"]:
        assert by_id[belt["EntityId"]]["Components"]["BeltInventory"] == {}
    preserved = root / f"outputs/grocery-belt-continuity-build{args.build}.timber"
    shutil.copyfile(source, preserved)
    report = {"build": args.build, "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "savedCorn": corn, "nativeConsumed": eaten, "delivered": delivered,
              "explicitFixtureWithdrawal": 30, "initialTotal": expected["CornTotal"],
              "incomingAndOutgoingBeltsEmpty": True, "donorAndReceiverEmpty": True}
    (root / f"outputs/grocery-belt-continuity{args.build}.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    raise SystemExit(0)

shop = entity_at("GroceryStore.IronTeeth", 159, 160, 3)
assert shop["Components"]["PausableBuilding"]["Paused"]
donor = entity_at("SmallWarehouse.IronTeeth", 164, 170, 3)
receiver = entity_at("SmallWarehouse.IronTeeth", 165, 170, 3)
assert "Inventory:Stockpile" not in receiver["Components"], "Native empty inventory must be omitted"
record = {
    "Shop": stock_record(shop, "Inventory:GroceryStore"),
    "Donor": stock_record(donor, "Inventory:Stockpile"),
    "Receiver": {"EntityId": receiver["Id"], "Stocks": []},
    "GeneratorId": entity_at("DevPowerGenerator", 163, 168, 3)["Id"],
    "Incoming": [], "Outgoing": [],
}
for y in (168, 169):
    incoming = entity_at("ConveyorBeltSp1.IronTeeth", 164, y, 3)
    items = incoming["Components"]["BeltInventory"]["Items"]
    assert items and all(item.startswith("CornRation;") for item in items)
    record["Incoming"].append({"EntityId": incoming["Id"], "Items": items})
    outgoing = entity_at("ConveyorBeltSp1.IronTeeth", 165, y, 3)
    assert outgoing["Components"]["BeltInventory"] == {}, "Outgoing lane must remain empty"
    record["Outgoing"].append({"EntityId": outgoing["Id"], "Items": []})
record["CornTotal"] = sum(g["Amount"] for key in ("Shop", "Donor") for g in record[key]["Stocks"]
                          if g["Name"] == "CornRation") + sum(len(b["Items"]) for b in record["Incoming"])
assert record["CornTotal"] == 117
assert next(g["Amount"] for g in record["Shop"]["Stocks"] if g["Name"] == "CornRation") == 100
preserved = root / f"outputs/grocery-belts-build{args.build}.timber"
shutil.copyfile(source, preserved)
(root / "outputs/grocery-belt-reload-expectations.json").write_text(json.dumps(record, indent=2) + "\n")
evidence = {
    "build": args.build, "nativeSave": str(source), "preserved": str(preserved),
    "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "cornTotal": record["CornTotal"], "queued": sum(len(b["Items"]) for b in record["Incoming"]),
    "donorStock": record["Donor"]["Stocks"], "shopStock": record["Shop"]["Stocks"],
}
(root / f"outputs/grocery-belt-source{args.build}.json").write_text(json.dumps(evidence, indent=2) + "\n")
print(json.dumps(evidence, indent=2))
