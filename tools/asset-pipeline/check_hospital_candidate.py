"""Check proposed public Hospital routes against the approved saved mesh."""
import json,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from hospital_layout import HOSPITAL as d
from civic_isometric_geometry import CIVIC_ACCESS,CIVIC_TERRACES
from civic_validation import validate_civic_walks

source=ROOT/'src/DeepFrontier/Art/Source/Hospital-ReferenceStudy.blend'
if Path(bpy.data.filepath)!=source:raise ValueError('Open the canonical Hospital study')
points={tuple(n['cell']):n['point'] for n in d['nodes']}
interior={tuple(c) for c in d['interiorCells']}
reports={}
for z in (2,4,6):
    routes=[]
    for a,b in d['edges']:
        a,b=tuple(a),tuple(b)
        if a[2]==z and b[2]==z and a not in interior and b not in interior:
            routes.append([points[a][:2],points[b][:2]])
    if not routes:raise ValueError('No public Hospital routes on layer '+str(z))
    CIVIC_ACCESS['Hospital']['routes']=routes
    CIVIC_ACCESS['Hospital']['balconyLayers']=[z]
    reports[str(z)]=validate_civic_walks('Hospital',bpy.data.collections['Hospital.ReferenceStudy'],bpy.context.scene)
if {tuple(c) for c in d['buildableCells']}!={(x,y,6) for x in range(5,9) for y in range(7,10)}:
    raise ValueError('Hospital must preserve the explicit central four-by-three roof garden')
report={'status':'Candidate source clearance only; native integration pending','publicLayers':reports,
        'routeCells':len(d['nodes']),'railOpenings':len(d['ports']),'buildableCells':d['buildableCells']}
(ROOT/'outputs/civic-integration/Hospital-candidate-clearance.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('Hospital candidate public routes and full terrace cells passed')
