"""Explicit one-time split of a pit apron; never rebuilds any building."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from blender_components import object_digest,separate_components,surface_digest
from pit_apron_components import legacy,BOUNDS


def uv_digest(mesh):
    uv=mesh.uv_layers['UVMap']
    return hashlib.sha256(b''.join(struct.pack('<2f',*uv.data[i].uv)
        for polygon in mesh.polygons for i in polygon.loop_indices)).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--model',required=True,choices=tuple(BOUNDS))
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    path=ROOT/'src/DeepFrontier/Art/Source'/(args.model+'-ReferenceStudy.blend')
    before_sha=hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(path))
    arch=bpy.data.objects[args.model+'.Architecture']
    name=args.model+'.Apron'
    if name in bpy.data.objects:
        raise ValueError('Apron already separated; use the ordinary selected-component rebuild')
    old=legacy(args.model)
    # The mineral_pit source begins with exactly this deck; no coordinate or
    # provenance search is permitted to silently adopt a different surface.
    indices=list(range(len(old.faces)))
    locations=json.loads(arch['df_source_locations'])
    attribute=arch.data.attributes['df_source']
    for index,face,mat in zip(indices,old.faces,old.materials,strict=True):
        poly=arch.data.polygons[index]
        provenance=locations[attribute.data[index].value]
        if ':deck > pit_isometric_geometry.py:' not in provenance or ':mineral_pit' not in provenance:
            raise ValueError('First source faces are not the explicitly authored pit apron')
        if len(poly.vertices)!=len(face) or poly.material_index!=mat:
            raise ValueError('Legacy apron face topology/material changed')
        actual=[arch.data.vertices[v].co for v in poly.vertices]
        expected=[Vector(old.vertices[v]) for v in face]
        if any((a-b).length>2e-6 for a,b in zip(actual,expected,strict=True)):
            raise ValueError('Legacy apron coordinates or winding changed')
    untouched={obj.name:object_digest(obj) for obj in bpy.data.objects if obj!=arch}
    previous=json.loads(arch['df_components'])
    migration=separate_components(arch,[{'name':name,'faceRange':[0,len(old.faces)]}])
    arch['df_components']=json.dumps(previous+[name])
    part=bpy.data.objects[name]
    changed=[key for key,digest in untouched.items() if object_digest(bpy.data.objects[key])!=digest]
    if changed:
        raise RuntimeError('Apron extraction changed unselected objects: '+str(changed))
    if hashlib.sha256(path.read_bytes()).hexdigest()!=before_sha:
        raise RuntimeError('Source changed externally while open')
    # This is the exact split source, before the separate authored-height edit.
    report=dict(model=args.model,beforeSha256=before_sha,migration=migration,
                apronUvSha256=uv_digest(part.data),
                apronFaceUvCorners=[[[float(v) for v in part.data.uv_layers['UVMap'].data[i].uv]
                                    for i in poly.loop_indices] for poly in part.data.polygons],
                apronSurfaceSha256=surface_digest(part),
                untouchedObjectsVerified=len(untouched),unchangedObjectDigests=untouched,
                wholeBuildingGeneratorCalled=False,renderedFrames=0)
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    report['afterSha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('unchangedObjectDigests','apronFaceUvCorners')}),flush=True)


if __name__=='__main__':main()
