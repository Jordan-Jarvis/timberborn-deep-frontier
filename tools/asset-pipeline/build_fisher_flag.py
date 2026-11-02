"""Build, check, save and export the Fisher Flag model (2026-11-02).

Authors fisher_flag_geometry.py into a fresh scene, checks it against the
contract in tools/aquaculture.json fisherFlag.model (1x1 footprint, height,
triangle ceiling, Iron Teeth and Common materials only, every UV inside 0..1,
the '#Slot#Seat0' idle seat and the swinging banner node), saves
src/DeepFrontier/Art/Source/FisherFlag-ReferenceStudy.blend (collection
FisherFlag.ReferenceStudy, export child FisherFlag.Model) and exports it with
the official Timbermesh exporter to the tracked candidate
outputs/civic-integration/Data/Buildings/Food/FisherFlag/, with its
construction stage (collection FisherFlag.ConstructionStage0, the landing,
post stumps and the pole lying on the boards). Canonical generation
(fishery_building_content.mjs) copies both exports into Data.

The banner swings about its bar in a 60-frame loop (the exporter's single
"Default" clip, played by AmbientAnimation while the flag is finished).

Run (real repository only; the scene and the export are written there):
  blender -b --factory-startup --python-exit-code 1 --python build_fisher_flag.py
  ... -- --no-save --export-root <dir>      scratch preview, no scene save
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Quaternion, Vector

sys.path.insert(0, str(Path(__file__).parent))
import build_map_objects as kit  # noqa: E402  (reset_scene, measure, export, sha)
import fisher_flag_geometry as geometry  # noqa: E402
import map_object_preview as preview  # noqa: E402

ROOT = kit.ROOT
CONTRACT = json.loads((ROOT / 'tools/aquaculture.json').read_text(encoding='utf-8'))['fisherFlag']['model']
VANILLA = ROOT / 'vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources/MaterialCollections'
FRAMES = 61
SEAT = '#Slot#Seat0'
BANNER = '#FisherFlag.Banner'


def allowed_materials():
    names = set()
    for collection in ('MaterialCollection.Common', 'MaterialCollection.IronTeeth'):
        spec = json.loads((VANILLA / f'{collection}.blueprint.json').read_text(encoding='utf-8-sig'))['MaterialCollectionSpec']
        names |= {path.rsplit('/', 1)[1] for path in spec['Materials']}
    return names


def animate_banner(obj):
    # A pendulum swing about the bar (the tile x axis), sine-eased, one loop.
    obj.rotation_mode = 'QUATERNION'
    for frame in range(1, FRAMES + 1):
        angle = geometry.SWING * math.sin(math.tau * (frame - 1) / (FRAMES - 1))
        obj.rotation_quaternion = Quaternion((1, 0, 0), angle)
        obj.keyframe_insert(data_path='rotation_quaternion', frame=frame)
    for curve in obj.animation_data.action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation = 'LINEAR'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-save', action='store_true')
    parser.add_argument('--export-root', help='write the export and report here instead (scratch previews)')
    cli = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    ident = geometry.IDENT
    scene = kit.reset_scene()
    scene.frame_start, scene.frame_end = 1, FRAMES
    study, model = kit.study_collections(scene, ident)
    materials = [preview.material(name) for name in geometry.MATERIALS]
    static, swing, seat = geometry.build()
    objects = [static.build(model, materials, bevel=0, uv_profile='civic-native'),
               swing.build(model, materials, bevel=0, uv_profile='civic-native')]
    report = kit.measure(objects)
    banner = objects[1]
    banner.name = BANNER
    animate_banner(banner)
    empty = bpy.data.objects.new(SEAT, None)
    model.objects.link(empty)
    x, y, z = seat
    empty.location = (-x, -y, z)
    # Facing the entrance side (-y in tile units), as the vanilla seat.
    empty.rotation_euler = (0, 0, math.atan2(0, -1))
    report['objects'] = [o.name for o in model.objects]
    stage = bpy.data.collections.new(f'{ident}.ConstructionStage0')
    study.children.link(stage)
    stage_object = geometry.build_stage().build(stage, materials, bevel=0, uv_profile='civic-native')
    stage_report = kit.measure([stage_object])

    problems = []
    w, d, _ = geometry.SIZE
    lo, hi = report['boundsMin'], report['boundsMax']
    if lo[0] < -1e-4 or lo[1] < -1e-4 or hi[0] > w + 1e-4 or hi[1] > d + 1e-4:
        problems.append(f'bounds {lo}..{hi} leave the {w}x{d} footprint')
    if lo[2] < -1e-4 or hi[2] > CONTRACT['maxHeight'] + 1e-4:
        problems.append(f'height {lo[2]}..{hi[2]} outside 0..{CONTRACT["maxHeight"]}')
    if report['triangles'] > CONTRACT['triangles']:
        problems.append(f'{report["triangles"]} triangles exceed the ceiling {CONTRACT["triangles"]}')
    extra = sorted(set(report['materials']) - allowed_materials())
    if extra:
        problems.append(f'materials outside MaterialCollection.IronTeeth and Common: {extra}')
    if sorted(report['materials']) != sorted(geometry.MATERIALS):
        problems.append(f'materials {sorted(report["materials"])} differ from the authored set {geometry.MATERIALS}')
    if report['uvErrorCount'] or stage_report['uvErrorCount']:
        problems.append(f'atlas UVs outside 0..1, e.g. {(report["uvErrors"] + stage_report["uvErrors"])[:3]}')
    slo, shi = stage_report['boundsMin'], stage_report['boundsMax']
    if slo[0] < -1e-4 or slo[1] < -1e-4 or shi[0] > w + 1e-4 or shi[1] > d + 1e-4 or slo[2] < -1e-4 or shi[2] > 1:
        problems.append(f'construction stage bounds {slo}..{shi} leave the footprint or its first layer')
    if stage_report['triangles'] > CONTRACT['stageTriangles']:
        problems.append(f'construction stage {stage_report["triangles"]} triangles exceed {CONTRACT["stageTriangles"]}')
    for name in (SEAT, BANNER):
        if name not in report['objects']:
            problems.append(f'{name} missing')
    if problems:
        print('\n'.join('FAIL ' + p for p in problems))
        raise SystemExit(f'Fisher Flag build failed ({len(problems)})')

    root = Path(cli.export_root) if cli.export_root else ROOT / 'outputs/civic-integration'
    if not cli.no_save:
        scene_path = ROOT / CONTRACT['sourceScene']
        bpy.ops.wm.save_as_mainfile(filepath=str(scene_path))
        report['sourceScene'] = CONTRACT['sourceScene']
        report['sourceSha256'] = kit.sha(scene_path)
    path = root / 'Data' / (CONTRACT['resource'] + '.timbermesh')
    kit.export(model, path, merge=True)
    report['export'] = path.relative_to(root).as_posix()
    report['exportSha256'] = kit.sha(path)
    report['frames'] = FRAMES
    stage_path = root / 'Data' / (CONTRACT['stageResource'] + '.timbermesh')
    kit.export(stage, stage_path, merge=True)
    report['constructionStage'] = {'triangles': stage_report['triangles'], 'boundsMin': slo, 'boundsMax': shi,
                                   'export': stage_path.relative_to(root).as_posix(), 'exportSha256': kit.sha(stage_path)}
    (root / f'{ident}-export.json').write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8')
    print('FISHER FLAG', json.dumps({k: report[k] for k in ('triangles', 'materials', 'boundsMin', 'boundsMax')}), flush=True)


if __name__ == '__main__':
    main()
