"""Inspect explicit native prefab roots and their serialized model components."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import dev_environment as dev
sys.path.insert(0,str(ROOT/'tools/asset-pipeline/unitypy'))
import UnityPy
env=UnityPy.load(str(dev.resources_assets()))
objects={o.path_id:o for o in env.objects}
out=ROOT/'outputs/native-civic-assets'
for ident in (4227,4293,4390,4151,4677,4421,3742,4370,4516,4393):
    obj=objects[ident];root=obj.parse_as_dict();result={'root':root,'components':[]}
    for c in root['m_Component']:
        target=objects[c['component']['m_PathID']]
        if target.type.name=='MonoBehaviour':
            # Read only Unity's base header to identify the managed component.
            # Its payload is saved intact; this is not a successful full parse.
            data=target.read_typetree(check_read=False)
            pointer=data['m_Script'];script=target.assets_file.externals[pointer['m_FileID']-1]
            (out/(str(target.path_id)+'-component.bin')).write_bytes(target.get_raw_data())
            result['components'].append({'id':target.path_id,'type':target.type.name,'baseHeader':data,
                'scriptFile':script.path,'bytes':target.byte_size})
        else:result['components'].append({'id':target.path_id,'type':target.type.name,'data':target.parse_as_dict()})
    (out/(str(ident)+'-prefab.json')).write_text(json.dumps(result,indent=2))
    print(ident,root['m_Name'],[(r['id'],r['type']) for r in result['components']],flush=True)
