"""Official export of the two remaining approved-generator prototypes.

The exact saved source hash must already have a clean strict surface report.
No geometry generation, render, icon update or unrelated resource export runs.
"""
import hashlib
import json
import sys
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[2]
PLUGIN=ROOT/'tools/asset-pipeline/timbermesh-plugin'
sys.path[:0]=[str(PLUGIN),str(PLUGIN/'timbermesh_blender_plugin')]
from timbermesh_blender_plugin import timbermesh_exporter

source=ROOT/'src/DeepFrontier/Art/Source/ApprovedBuildings.blend'
# Late-game studies own integrated models; this exporter must not overwrite them.
INTEGRATED=set(json.loads((ROOT/'tools/lategame_batches.json').read_text())['integrated'])
PROTOTYPES=[n for n in ('NuclearReactor','CryogenicLiquefactionPlant') if n not in INTEGRATED]
digest=hashlib.sha256(source.read_bytes()).hexdigest()
for name in PROTOTYPES:
    report=json.loads((ROOT/f'outputs/zfight/{name}-frame1.json').read_text())
    if report['visibleConflicts'] or report['sourceSha256']!=digest:
        raise ValueError('Export requires a fresh clean prototype surface audit: '+name)
bpy.ops.wm.open_mainfile(filepath=str(source))
settings=timbermesh_exporter.ExportSettings(bpy.context,False,True,False)
for name,group in [(n,g) for n,g in (('NuclearReactor','Power'),('CryogenicLiquefactionPlant','Metal')) if n in PROTOTYPES]:
    for suffix in ('Model','ConstructionStage0.Model'):
        collection=bpy.data.collections[f'{name}.IronTeeth.{suffix}']
        output=ROOT/f'src/DeepFrontier/Data/Buildings/{group}/{name}/{collection.name}.timbermesh'
        timbermesh_exporter.Exporter.export_collection(collection,str(output),settings)
        print('EXPORTED',output.relative_to(ROOT),flush=True)
