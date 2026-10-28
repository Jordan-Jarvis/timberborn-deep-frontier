"""Integration step: register the three concrete side platforms in
tools/building_asset_catalog.json AFTER canonical generation/promotion has put
their blueprints in src/DeepFrontier/Data (audit_building_assets.py requires the
catalog to equal the active templates). Idempotence is not attempted: it fails if
the entries already exist."""
from pathlib import Path
import json
p=Path(__file__).resolve().parents[2]/'tools/building_asset_catalog.json'
s=p.read_text(encoding='utf-8')
assert 'ConcreteSidePlatform' not in s,'Side platforms are already registered'
anchor='''      "building": "LimestoneMasonryBlock",'''
assert s.count(anchor)==1
entries=''
for n in (3,4,5):
    i=f'ConcreteSidePlatform{n}x{n}'
    entries+=f'''      "building": "{i}",
      "template": "{i}.IronTeeth",
      "blueprint": "src/DeepFrontier/Data/Buildings/Platforms/{i}/{i}.IronTeeth.blueprint.json",
      "model": "{i}",
      "sourceScene": "src/DeepFrontier/Art/Source/{i}-ReferenceStudy.blend",
      "collection": "{i}.ReferenceStudy",
      "geometry": "tools/asset-pipeline/structural_geometry.py",
      "generator": "tools/asset-pipeline/render_reference_studies.py",
      "exporter": "tools/asset-pipeline/export_industrial_models.py",
      "artStage": "detailed"
    }},
    {{
'''
s=s.replace(anchor,entries+anchor)
json.loads(s)
p.write_text(s,encoding='utf-8')
print('registered 3 side platforms')
