"""Read-only comparison of construction rows with current authored blueprints."""
import json
from pathlib import Path
from openpyxl import load_workbook

root = Path(__file__).resolve().parents[1]
catalog = json.loads((root / "tools/construction_materials.json").read_text())
workbook = load_workbook(root / "outputs/Timberborn_Deep_Frontier_Balance_Workbook.xlsx",
                         data_only=False)
sheet = workbook["Buildings"]
headers = [cell.value for cell in sheet[1]]
rows = {row[0]: dict(zip(headers, row)) for row in sheet.iter_rows(min_row=2, values_only=True)}
report = {}
for item in catalog["buildings"]:
    ident = item["id"]
    blueprint = json.loads((root / f"src/DeepFrontier/Data/Buildings/Metal/{ident}/{ident}.IronTeeth.blueprint.json").read_text())
    row = rows[ident]
    block = blueprint["BlockObjectSpec"]
    size = block["Size"]
    assert [row[h] for h in ("Width", "Length", "Height")] == [size[k] for k in ("X", "Y", "Z")], ident
    assert row["Workers"] == blueprint["WorkplaceSpec"]["MaxWorkers"], ident
    assert row["Power demand (hp)"] == item["hp"], ident
    assert row["Power output (hp)"] == 0, ident
    assert row["Science unlock"] == blueprint["BuildingSpec"]["ScienceCost"], ident
    support = sum(b["Stackable"] == "BlockObject" for b in block["Blocks"])
    empty = sum(b["Occupations"] == "None" for b in block["Blocks"])
    assert f"{support} support cells; {empty} empty cells" in row["Flags"], ident
    assert row["Stackable"] == ("Clear supported deck cells" if support else "No"), ident
    assert row["Status"] == row["Data status"], ident
    assert row["Status"] != "Prototype", ident
    if "BuildingWalkwaySpec" in blueprint:
        walkway = blueprint["BuildingWalkwaySpec"]
        assert f'{len(walkway["Waypoints"])} route cells' in row["Flags"], ident
        assert f'{len(walkway["Openings"])} adaptive rail openings' in row["Flags"], ident
        assert "no layer cap" in row["Stacking rule"], ident
    report[ident] = {"dimensions": item["size"], "hp": item["hp"],
                     "supportCells": support, "emptyCells": empty,
                     "status": row["Status"]}
(root / "outputs/construction-workbook-verification.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
