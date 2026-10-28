"""Inspect the official example scene's actual material and UV contracts."""
import bpy,json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
out=root/'outputs/native-material-inspection';out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(root/'vendor/timberborn-modding/Assets/Tools/ImportedAssets/TimberbornExampleModels.blend'))
materials=[]
for m in bpy.data.materials:
    materials.append({'name':m.name,'nodes':[{'name':n.name,'type':n.type,'image':n.image.name if n.type=='TEX_IMAGE' and n.image else None,'inputs':{i.name:list(i.default_value) if hasattr(i.default_value,'__len__') else i.default_value for i in n.inputs if hasattr(i,'default_value') and not i.is_linked}} for n in m.node_tree.nodes] if m.use_nodes else []})
objects=[]
for o in bpy.data.objects:
    if o.type!='MESH' or not o.data.uv_layers.active:continue
    bymat={}
    for p in o.data.polygons:
        m=o.data.materials[p.material_index].name
        bymat.setdefault(m,[]).extend(list(o.data.uv_layers.active.data[i].uv) for i in p.loop_indices)
    objects.append({'name':o.name,'materials':{m:{'min':[min(v[i] for v in u) for i in range(2)],'max':[max(v[i] for v in u) for i in range(2)],'samples':u[:12]} for m,u in bymat.items()}})
images=[]
for i in bpy.data.images:
    images.append({'name':i.name,'size':list(i.size),'filepath':i.filepath,'packed':bool(i.packed_file)})
    if i.packed_file:
        i.filepath_raw=str(out/(i.name+'.png'));i.file_format='PNG';i.save()
(out/'official-example.json').write_text(json.dumps({'materials':materials,'objects':objects,'images':images},indent=2))
print(json.dumps({'materials':[m['name'] for m in materials],'objects':len(objects),'images':images}))
