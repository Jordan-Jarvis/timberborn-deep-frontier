"""Read installed 1.1 assets for native civic props and liquid rendering."""
from pathlib import Path
import collections,json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/asset-pipeline/unitypy'))
import UnityPy
if UnityPy.__version__!='1.25.4':raise RuntimeError('Use the inspected UnityPy 1.25.4 API')
game=Path('C:/Program Files (x86)/Steam/steamapps/common/Timberborn/Timberborn_Data')
out=ROOT/'outputs/native-civic-assets';out.mkdir(parents=True,exist_ok=True)
env=UnityPy.load(str(game/'resources.assets'))
types=collections.Counter(o.type.name for o in env.objects);selected=[];containers=[]
keys=('waterwheel','barrel','smalltank','hydroponic','water','basewood','irregularplanks','paintedmetal')
for obj in env.objects:
    if obj.type.name=='ResourceManager':
        data=obj.parse_as_dict()
        (out/'resource-paths.json').write_text(json.dumps(data,indent=2))
    if obj.type.name not in ('GameObject','Mesh','TextAsset','Material','Texture2D'):continue
    data=obj.parse_as_object();name=data.m_Name
    if not any(k in name.lower() for k in keys):continue
    record={'id':obj.path_id,'type':obj.type.name,'name':name}
    if obj.type.name=='Texture2D':record.update(width=data.m_Width,height=data.m_Height)
    selected.append(record)
    if obj.type.name=='Material':
        (out/(str(obj.path_id)+'-material.json')).write_text(json.dumps(obj.parse_as_dict(),indent=2))
(out/'index.json').write_text(json.dumps({'UnityPy':UnityPy.__version__,'types':dict(types),'selected':selected},indent=2))
print(json.dumps({'types':dict(types),'selected':selected}),flush=True)
