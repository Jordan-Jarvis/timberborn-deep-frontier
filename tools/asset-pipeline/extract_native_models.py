"""Cache exact shipped Timbermesh models by name for local previews.

Reads the installed Timberborn resources.assets (read-only), finds the
GameObject named '<name>.Model', takes its BinaryData component (the
Timbermesh payload, script PathID 4746 as in inspect_native_rail_reference.py)
and writes outputs/native-civic-assets/<name>.timbermesh plus a node summary.
The cached copies are review inputs, never mod payload: blueprints reference
the original resources.

Run: python extract_native_models.py BeaverBust.IronTeeth BeaverStatue.IronTeeth
"""
import json
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/asset-pipeline/unitypy'))
sys.path.insert(0, str(ROOT / 'tools/asset-pipeline/timbermesh-plugin/timbermesh_blender_plugin'))
import UnityPy  # noqa: E402
import model_pb2  # noqa: E402

BINARY_DATA_SCRIPT = {'m_FileID': 1, 'm_PathID': 4746}
OUT = ROOT / 'outputs/native-civic-assets'


def main(names):
    env = UnityPy.load('C:/Program Files (x86)/Steam/steamapps/common/Timberborn/Timberborn_Data/resources.assets')
    objects = {o.path_id: o for o in env.objects}
    wanted = {n + '.Model': n for n in names}
    found = {}
    for o in env.objects:
        if o.type.name != 'GameObject':
            continue
        root = o.parse_as_dict()
        if root.get('m_Name') in wanted:
            if root['m_Name'] in found:
                raise SystemExit(f'{root["m_Name"]}: more than one GameObject')
            found[root['m_Name']] = root
    missing = sorted(set(wanted) - set(found))
    if missing:
        raise SystemExit(f'Not in resources.assets: {missing}')
    for model_name, root in found.items():
        name = wanted[model_name]
        binary = []
        for c in root['m_Component']:
            target = objects[c['component']['m_PathID']]
            if target.type.name != 'MonoBehaviour':
                continue
            if target.read_typetree(check_read=False)['m_Script'] == BINARY_DATA_SCRIPT:
                binary.append(target.get_raw_data())
        if len(binary) != 1:
            raise SystemExit(f'{model_name}: expected one BinaryData component, found {len(binary)}')
        data = binary[0]
        length = struct.unpack_from('<I', data, 32)[0]
        if len(data) != 36 + length + (4 - length % 4) % 4:
            raise SystemExit(f'{model_name}: BinaryData length does not match the Unity byte-array layout')
        payload = data[36:36 + length]
        model = model_pb2.Model()
        model.ParseFromString(zlib.decompress(payload))
        (OUT / (name + '.timbermesh')).write_bytes(payload)
        summary = [{'name': n.name, 'vertices': n.vertexCount,
                    'meshes': [{'material': m.material, 'triangles': len(m.indices) // 3} for m in n.meshes]}
                   for n in model.nodes]
        (OUT / (name + '-model.json')).write_text(json.dumps(summary, indent=2) + '\n')
        print(name, json.dumps(summary), flush=True)


if __name__ == '__main__':
    main(sys.argv[1:])
