"""Read-only boundary audit of all twenty unreplaced building prototypes.

Closed component meshes establish no missing faces in those components. They
do not establish a detailed building design, sensible hitboxes, native style,
or watertight joins between independently positioned components.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[2]
SOURCES={
    'DeepFrontierModels.blend':[
        'DeepDrill','DeepMine','DeepProcessor','FertilizerWorks','FoodPackagingWorks',
        'PublicHealthLab','Greenhouse','ChemicalWorks','PrecisionMachineWorks',
        'WaterTreatmentPlant','TechnicalSchool','UraniumProcessingPlant',
        'RadioactiveWasteRefinery','ElectrolysisPlant','RocketAssemblyHangar',
        'MissionControl','LaunchPad','RadioactiveWasteVault'],
    'ApprovedBuildings.blend':['NuclearReactor','CryogenicLiquefactionPlant'],
}
results=[]
for source,names in SOURCES.items():
    path=ROOT/'src/DeepFrontier/Art/Source'/source
    before=hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(path))
    bpy.context.scene.frame_set(1)
    depsgraph=bpy.context.evaluated_depsgraph_get()
    for name in names:
        collection=bpy.data.collections[name+'.IronTeeth.Model']
        defects=[];meshes=0;faces=0
        for obj in collection.all_objects:
            if obj.type!='MESH':continue
            meshes+=1
            evaluated=obj.evaluated_get(depsgraph);mesh=evaluated.to_mesh()
            try:
                faces+=len(mesh.polygons)
                incidence=Counter();direction=Counter()
                for poly in mesh.polygons:
                    for i,a in enumerate(poly.vertices):
                        b=poly.vertices[(i+1)%len(poly.vertices)]
                        incidence[tuple(sorted((a,b)))]+=1
                        direction[(a,b)]+=1
                boundary=sum(n==1 for n in incidence.values())
                nonmanifold=sum(n>2 for n in incidence.values())
                winding=sum(direction[(a,b)]!=direction[(b,a)] for a,b in incidence)
                if boundary or nonmanifold or winding:
                    defects.append({'object':obj.name,'boundaryEdges':boundary,
                        'nonmanifoldEdges':nonmanifold,'inconsistentWindingEdges':winding})
            finally:evaluated.to_mesh_clear()
        results.append({'model':name,'source':str(path.relative_to(ROOT)),
            'sha256':before,'meshes':meshes,'polygons':faces,'componentDefects':defects,
            'artStatus':'Older prototype; detailed source-grid/native-style migration pending'})
        print(name,meshes,'meshes',len(defects),'defective components',flush=True)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==before,'Audit modified source'
out=ROOT/'outputs/prototype-shell-audit.json'
out.write_text(json.dumps({'scope':__doc__,'models':results},indent=2)+'\n')
assert len(results)==20
assert all(not r['componentDefects'] for r in results),f'Component defects: inspect {out}'
print('PASS 20 prototype component-boundary audits; no claim of art/grid readiness')
