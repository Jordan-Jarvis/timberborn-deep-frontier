"""Our shader variants in built asset bundles, against the installed game's own shaders.

Deep Frontier and Moddable Fluids bundle variants of three native Timberborn shader graphs
(tools/native_shader_variants.mjs, tools/moddable_fluids_shader_variants.mjs). The builds strip
their variants with tools/unity/ModShaderVariantStripping.cs (rules and evidence:
docs/unity-build-performance.md). For every shader of ours (name DeepFrontier/... or
ModdableFluids/...) in each given bundle this requires, pass by pass and stage by stage, exactly
the keyword sets of its native counterpart in the installed game (resources.assets) that the
stripping keeps, each with and without the shader's own keyword: nothing the game can draw is
stripped, nothing the stripping removes is left. --expect lists our shaders the bundles must hold;
any other DeepFrontier/ or ModdableFluids/ shader fails (so it also proves a shader's absence).

It re-checks, in the installed game, the evidence the stripping relies on:
  - the game's only render pipeline asset uses only UniversalRendererData (no Renderer2DData), so
    passes tagged LightMode=Universal2D are never drawn;
  - every game material on a native water shader enables _CALCULATE_OUTFLOWS;
  - no game material on the native terrain shader enables _USE_TRIPLANAR_SPLATMAP without
    _SAMPLE_SPLATMAP;
  - no game assembly names those material keywords, so the game never toggles them at runtime.

  python tools/asset-pipeline/check_bundle_shaders.py --win <name>_win --mac <name>_mac --expect <shader> ...
Exit code 1 with FAIL lines on any difference; otherwise one JSON summary line.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import dev_environment as dev  # noqa: E402
sys.path.insert(0, str(ROOT / 'tools/asset-pipeline/unitypy'))
import UnityPy  # noqa: E402

OUR_PREFIXES = ('DeepFrontier/', 'ModdableFluids/')
STRIPPED_LIGHT_MODES = {'Universal2D'}
WATER_NATIVE = ('Shader Graphs/PhysicalWaterURP_Opaque', 'Shader Graphs/PhysicalWaterURP_Transparent')
TERRAIN_NATIVE = 'Shader Graphs/TerrainURP'
OUTFLOWS = '_CALCULATE_OUTFLOWS'
TRIPLANAR, SPLATMAP = '_USE_TRIPLANAR_SPLATMAP', '_SAMPLE_SPLATMAP'


def keep_water(keywords, declared):
    return OUTFLOWS not in declared or OUTFLOWS in keywords


def keep_terrain(keywords, declared):
    return not (TRIPLANAR in keywords and SPLATMAP not in keywords)


# Mirrors ModShaderVariantStripping.Rules: our shader -> (native counterpart, own keyword, kept material keywords).
SHADERS = {
    'DeepFrontier/IrradiatedTerrainURP': (TERRAIN_NATIVE, '_DEEP_FRONTIER_IRRADIATED_SOIL', keep_terrain),
    'DeepFrontier/RadioactiveWaterURP_Opaque': (WATER_NATIVE[0], '_DEEP_FRONTIER_RADIOACTIVE_WATER', keep_water),
    'DeepFrontier/RadioactiveWaterURP_Transparent': (WATER_NATIVE[1], '_DEEP_FRONTIER_RADIOACTIVE_WATER', keep_water),
    'ModdableFluids/FluidWaterURP_Opaque': (WATER_NATIVE[0], '_MODDABLE_FLUIDS_APPEARANCE', keep_water),
    'ModdableFluids/FluidWaterURP_Transparent': (WATER_NATIVE[1], '_MODDABLE_FLUIDS_APPEARANCE', keep_water),
}


def variants(shader):
    """(pass name, LightMode, stage) -> set of keyword frozensets, from the serialized player sub-programs."""
    parsed = shader['m_ParsedForm']
    names = parsed['m_KeywordNames']
    out = {}
    for subshader in parsed['m_SubShaders']:
        for pass_ in subshader['m_Passes']:
            tags = {key.upper(): value for key, value in pass_['m_State']['m_Tags']['tags']}
            for stage in ('progVertex', 'progFragment', 'progGeometry', 'progHull', 'progDomain'):
                sets = {frozenset(names[i] for i in program['m_KeywordIndices'])
                        for tier in pass_[stage]['m_PlayerSubPrograms'] for program in tier}
                if sets:
                    out[(pass_['m_State']['m_Name'], tags.get('LIGHTMODE', ''), stage)] = sets
    return out


def describe(key):
    return f'pass {key[0]} ({key[1]}) {key[2]}'


def game_evidence(failures):
    """The game data the stripping rules rest on; returns the native shaders' variants and a summary."""
    data = dev.game_data()
    env = UnityPy.load(str(data / 'globalgamemanagers.assets'), str(data / 'resources.assets'),
                       *[str(p) for p in sorted(data.glob('sharedassets*.assets'))])
    shaders, native = {}, {}
    for obj in env.objects:
        if obj.type.name == 'Shader':
            parsed = obj.parse_as_dict()
            name = parsed['m_ParsedForm']['m_Name']
            shaders[(obj.assets_file.name, obj.path_id)] = name
            if name in (TERRAIN_NATIVE, *WATER_NATIVE):
                if name in native:
                    failures.append(f'game data holds {name} twice')
                native[name] = variants(parsed)
    for name in (TERRAIN_NATIVE, *WATER_NATIVE):
        if name not in native:
            failures.append(f'the installed game has no {name}')
    renderers, materials = [], {}
    for obj in env.objects:
        if obj.type.name == 'MonoBehaviour':
            behaviour = obj.read(check_read=False)
            try:
                script = behaviour.m_Script.read()
            except Exception as error:
                failures.append(f'cannot resolve the script of MonoBehaviour {obj.assets_file.name}:{obj.path_id} ({error})')
                continue
            if script.m_ClassName.endswith('RendererData') or script.m_ClassName.endswith('RenderPipelineAsset'):
                renderers.append(script.m_ClassName)
        elif obj.type.name == 'Material':
            material = obj.parse_as_dict()
            pointer = material['m_Shader']
            if pointer['m_FileID'] != 0:
                continue
            shader = shaders.get((obj.assets_file.name, pointer['m_PathID']))
            if shader in (TERRAIN_NATIVE, *WATER_NATIVE):
                materials[f"{material['m_Name']} ({shader})"] = sorted(material.get('m_ValidKeywords') or [])
    if sorted(renderers) != ['UniversalRenderPipelineAsset', 'UniversalRendererData']:
        failures.append(f'game render pipeline objects changed: {sorted(renderers)} (Universal2D stripping assumes one '
                        'UniversalRenderPipelineAsset with one UniversalRendererData)')
    for material, keywords in materials.items():
        if any(material.endswith(f'({water})') for water in WATER_NATIVE) and OUTFLOWS not in keywords:
            failures.append(f'game material {material} does not enable {OUTFLOWS}')
        if material.endswith(f'({TERRAIN_NATIVE})') and not keep_terrain(set(keywords), set(keywords)):
            failures.append(f'game material {material} enables {TRIPLANAR} without {SPLATMAP}')
    if not any(m.endswith(f'({TERRAIN_NATIVE})') for m in materials) or not any(m.endswith(f'({WATER_NATIVE[0]})') for m in materials):
        failures.append('no native terrain or water material found in the game data')
    toggled = {}
    for assembly in sorted(dev.managed().glob('*.dll')):
        content = assembly.read_bytes()
        for keyword in (OUTFLOWS, TRIPLANAR, SPLATMAP):
            if keyword.encode('utf-16-le') in content or keyword.encode() in content:
                toggled.setdefault(keyword, []).append(assembly.name)
    for keyword, assemblies in toggled.items():
        failures.append(f'game assemblies name {keyword} (the game may toggle it at runtime): {", ".join(assemblies)}')
    return native, {'renderers': sorted(renderers), 'materials': materials}


def expected_variants(native, own, keep):
    expected = {}
    for key, sets in native.items():
        if key[1] in STRIPPED_LIGHT_MODES:
            continue
        declared = frozenset().union(*sets)
        expected[key] = {kept | extra for kept in sets if keep(kept, declared) for extra in (frozenset(), frozenset([own]))}
    return expected


def check_bundle(path, platform, native, expect, failures):
    env = UnityPy.load(str(path))
    target = {'win': 19, 'mac': 2}[platform]  # Unity BuildTarget values
    platforms = {int(obj.assets_file.target_platform) for obj in env.objects}
    if platforms != {target}:
        failures.append(f'{path}: expected {platform} build target {target}, got {sorted(platforms)}')
    found, report = set(), {}
    for obj in env.objects:
        if obj.type.name != 'Shader':
            continue
        parsed = obj.parse_as_dict()
        name = parsed['m_ParsedForm']['m_Name']
        if not name.startswith(OUR_PREFIXES):
            continue
        found.add(name)
        if name not in SHADERS:
            failures.append(f'{path.name}: {name} has no stripping rule (add it to ModShaderVariantStripping and this check)')
            continue
        native_name, own, keep = SHADERS[name]
        ours = variants(parsed)
        expected = expected_variants(native[native_name], own, keep)
        for key in sorted(set(ours) | set(expected)):
            if key[1] in STRIPPED_LIGHT_MODES:
                failures.append(f'{path.name}: {name} {describe(key)} is drawn only by the 2D renderer and must be stripped')
                continue
            missing, extra = expected.get(key, set()) - ours.get(key, set()), ours.get(key, set()) - expected.get(key, set())
            for label, sets in (('lacks', missing), ('holds stripped', extra)):
                for keywords in sorted(sets, key=sorted)[:4]:
                    failures.append(f'{path.name}: {name} {describe(key)} {label} variant [{" ".join(sorted(keywords))}]'
                                    + (f' (+{len(sets) - 4} more)' if len(sets) > 4 else ''))
        report[name] = {describe(key): len(sets) for key, sets in sorted(ours.items())}
    for name in sorted(set(expect) - found):
        failures.append(f'{path.name}: {name} is missing')
    for name in sorted(found - set(expect)):
        failures.append(f'{path.name}: {name} must not be in this bundle')
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--win', required=True, help='built <mod>_win asset bundle')
    parser.add_argument('--mac', required=True, help='built <mod>_mac asset bundle')
    parser.add_argument('--expect', nargs='+', required=True, help='every DeepFrontier/ or ModdableFluids/ shader the bundles hold')
    cli = parser.parse_args()
    unknown = [name for name in cli.expect if name not in SHADERS]
    if unknown:
        raise SystemExit(f'No stripping rule for {unknown}')
    failures = []
    native, evidence = game_evidence(failures)
    reports = {}
    if len(native) == 3:
        for platform in ('win', 'mac'):
            path = Path(getattr(cli, platform))
            if not path.is_file():
                failures.append(f'{path} does not exist')
                continue
            reports[platform] = check_bundle(path, platform, native, cli.expect, failures)
    if failures:
        print('\n'.join('FAIL ' + failure for failure in failures))
        raise SystemExit(f'Bundle shader check failed ({len(failures)})')
    print(json.dumps({'status': 'bundle-shaders-match-native', 'shaders': reports, 'evidence': evidence}))


if __name__ == '__main__':
    main()
