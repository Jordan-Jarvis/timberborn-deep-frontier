"""Read-only provenance inventory of the explicitly opened Hospital source.

No geometry builder, component migration, save, rendering or export is called.
The caller must supply the exact expected hash, including for a .blend1 file.
"""
import argparse,hashlib,json,sys
from collections import Counter
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from hospital_structure import DOORS,ROOMS

parser=argparse.ArgumentParser()
parser.add_argument('--expected-sha256',required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
path=Path(bpy.data.filepath)
digest=hashlib.sha256(path.read_bytes()).hexdigest()
if digest!=args.expected_sha256:raise ValueError('Opened Hospital source differs from the requested revision')
if not args.output.is_absolute():raise ValueError('Diagnostic output path must be absolute')
architecture=bpy.data.objects['Hospital.Architecture']
sources=json.loads(architecture['df_source_locations'])
source_attribute=architecture.data.attributes['df_source']
matches={name:[] for name in DOORS}
for polygon in architecture.data.polygons:
    source=sources[source_attribute.data[polygon.index].value]
    if ':building_portal' not in source:continue
    points=[architecture.matrix_world@architecture.data.vertices[i].co for i in polygon.vertices]
    center=[sum((-p[a] if a<2 else p[a]) for p in points)/len(points) for a in range(3)]
    name=min(DOORS,key=lambda name:sum((center[a]-DOORS[name]['position'][a])**2 for a in range(3)))
    if sum((center[a]-DOORS[name]['position'][a])**2 for a in range(3))>1.5:
        raise ValueError('Portal provenance exists outside a canonical Hospital door')
    matches[name].append({'index':polygon.index,'source':source,
        'material':architecture.data.materials[polygon.material_index].name,
        'vertices':[[-p.x,-p.y,p.z] for p in points]})
result={'scope':__doc__,'source':str(path),'sourceSha256':digest,
        'architectureFaces':len(architecture.data.polygons),'doors':[]}
rooms={'GroundDoor':'CentralLower','WestWardDoor':'WestWardUpper',
       'RearWardDoor':'CentralUpper','RoofTerraceDoor':'RoofStairhead'}
for name,door in DOORS.items():
    rows=matches[name]
    if len(rows)!=41:raise ValueError('Expected the known 41-face recessed legacy insert: '+name)
    ids=[row['index'] for row in rows]
    if ids!=list(range(ids[0],ids[-1]+1)):raise ValueError('Legacy door faces are not contiguous: '+name)
    x,y,z=door['position'];nx,ny=door['outward'];tx,ty=-ny,nx
    local=[((p[0]-x)*tx+(p[1]-y)*ty,-(p[0]-x)*nx-(p[1]-y)*ny,p[2]-z)
           for row in rows for p in row['vertices']]
    result['doors'].append({'id':name,'room':rooms[name],'roomBounds':ROOMS[rooms[name]],
        'position':door['position'],'outward':door['outward'],'faceRangeExclusive':[ids[0],ids[-1]+1],
        'faceCount':len(rows),'materials':dict(Counter(row['material'] for row in rows)),
        'sourceFaceCounts':dict(Counter(row['source'] for row in rows)),
        'localBoundsMin':[min(p[a] for p in local) for a in range(3)],
        'localBoundsMax':[max(p[a] for p in local) for a in range(3)],
        'legacyCavityCaps':rows[-4:],
        'requiredFacade':'grid','gridPanelDepth':.04,'legacyPanelDepth':.12})
if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Source changed externally during the read-only audit')
args.output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='doors'}))
for door in result['doors']:
    print(door['id'],door['position'],door['outward'],door['faceRangeExclusive'],door['faceCount'])
