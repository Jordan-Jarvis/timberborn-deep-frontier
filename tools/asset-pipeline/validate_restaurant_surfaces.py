"""Inspect authored mesh faces for coincident plaster/wood wall rectangles."""
import json
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'src/DeepFrontier/Art/Source/Restaurant-ReferenceStudy.blend'))
obj=bpy.data.objects['Restaurant.Architecture']
planes={}
count=0
for polygon in obj.data.polygons:
    if polygon.material_index not in (0,1,28) or len(polygon.vertices)!=4:continue
    points=[obj.matrix_world@obj.data.vertices[i].co for i in polygon.vertices]
    lo=[min(p[a] for p in points) for a in range(3)]
    hi=[max(p[a] for p in points) for a in range(3)]
    axes=[a for a in (0,1) if hi[a]-lo[a]<1e-6]
    if len(axes)!=1:continue
    axis=axes[0];other=[a for a in range(3) if a!=axis]
    # Only true rectangular faces; angled arch and roof triangles are not walls.
    if any(not all(abs(p[a]-lo[a])<1e-6 or abs(p[a]-hi[a])<1e-6 for a in other) for p in points):continue
    # Thin end caps inside perpendicular wall/frame joints are intentional
    # intersections, not the exposed broad plaster facade being inspected.
    if polygon.material_index==28 and hi[1-axis]-lo[1-axis]<.3:continue
    planes.setdefault(axis,[]).append((lo[axis],polygon.index,polygon.material_index,lo,hi))
    count+=1
overlaps=[]
for axis,faces in planes.items():
    wood=[f for f in faces if f[2] in (0,1)]
    for depth,index,material,lo,hi in (f for f in faces if f[2]==28):
        for wd,wi,wm,wl,wh in wood:
            if abs(wd-depth)>1e-6:continue
            lengths=[min(hi[a],wh[a])-max(lo[a],wl[a]) for a in range(3) if a!=axis]
            if min(lengths)>1e-5:overlaps.append({'plasterFace':index,'woodFace':wi,'area':lengths[0]*lengths[1]})
report={'scope':'Authored broad plaster facade rectangles versus wood faces; thin interior panel end caps excluded. Source evidence, not a native visual test.',
        'checkedFaces':count,'coplanarPlasterWoodOverlaps':overlaps}
(ROOT/'outputs/restaurant-wall-surface-checks108.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
if overlaps:raise ValueError('Coplanar wood/plaster wall faces: '+str(overlaps[:12]))
print(json.dumps(report))
