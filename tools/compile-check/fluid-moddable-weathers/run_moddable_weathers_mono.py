"""Run the Moddable Weathers adapter probe inside the installed game's Mono, in a separate process.

    run_moddable_weathers_mono.py <ModdableFluids.ModdableWeathersMonoProbe.dll> [report.json]

Embeds the game's own Mono runtime (MonoBleedingEdge). The assembly path is the game's Managed folder, the probe's
folder and the installed Workshop copies of Moddable Weathers 11.0.0 (3630523180), Moddable Timberborn (3578009707) and
TimberUi (3430626620), version-1.1, as the game loads them. It loads the Harmony the official mod builder ships and
calls ModdableFluids.Tides.ModdableWeathersAdapter.Acceptance.ModdableWeathersMonoProbe.Run(managed). The game process
is never started.
"""
import ctypes
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import dev_environment as dev  # noqa: E402

WORKSHOP = {'ModdableWeathers': '3630523180', 'ModdableTimberborn': '3578009707', 'TimberUi': '3430626620'}


def main():
    if len(sys.argv) not in (2, 3):
        raise SystemExit(__doc__)
    probe = Path(sys.argv[1]).resolve(strict=True)
    report = Path(sys.argv[2]).resolve() if len(sys.argv) == 3 else None
    managed = dev.managed()
    runtime = dev.game_root() / 'MonoBleedingEdge' / 'EmbedRuntime' / 'mono-2.0-bdwgc.dll'
    workshop = dev.workshop()
    folders = {name: workshop / item / 'version-1.1' for name, item in WORKSHOP.items()}
    for name, folder in folders.items():
        (folder / (name + '.dll')).resolve(strict=True)
    mono = ctypes.CDLL(str(runtime.resolve(strict=True)))

    def bind(name, result, *arguments):
        function = getattr(mono, name)
        function.restype = result
        function.argtypes = list(arguments)
        return function

    pointer = ctypes.c_void_p
    text = ctypes.c_char_p
    set_path = bind('mono_set_assemblies_path', None, text)
    initialize = bind('mono_jit_init_version', pointer, text, text)
    open_assembly = bind('mono_domain_assembly_open', pointer, pointer, text)
    get_image = bind('mono_assembly_get_image', pointer, pointer)
    get_class = bind('mono_class_from_name', pointer, pointer, text, text)
    get_method = bind('mono_class_get_method_from_name', pointer, pointer, text, ctypes.c_int)
    new_string = bind('mono_string_new', pointer, pointer, text)
    invoke = bind('mono_runtime_invoke', pointer, pointer, pointer, ctypes.POINTER(pointer), ctypes.POINTER(pointer))
    to_string = bind('mono_object_to_string', pointer, pointer, ctypes.POINTER(pointer))
    to_utf8 = bind('mono_string_to_utf8', pointer, pointer)
    free = bind('mono_free', None, pointer)

    def decode(value):
        encoded = to_utf8(value)
        if not encoded:
            raise RuntimeError('Mono could not encode the probe result')
        try:
            return ctypes.string_at(encoded).decode('utf-8')
        finally:
            free(encoded)

    search = [str(managed), str(probe.parent)] + [str(folder) for folder in folders.values()]
    set_path(';'.join(search).encode('utf-8'))
    domain = initialize(b'ModdableFluidsModdableWeathersProbe', b'v4.0.30319')
    if not domain:
        raise RuntimeError('Installed Mono did not initialize')
    harmony = Path(dev.get('timberbornDocuments')) / 'ModsBuild' / 'TimberbornModExamples_Data' / 'Managed' / '0Harmony.dll'
    if not open_assembly(domain, str(harmony.resolve(strict=True)).encode('utf-8')):
        raise RuntimeError('Installed Harmony did not load in the isolated Mono host')
    assembly = open_assembly(domain, str(probe).encode('utf-8'))
    if not assembly:
        raise RuntimeError('Installed Mono did not load the Moddable Weathers probe')
    klass = get_class(get_image(assembly), b'ModdableFluids.Tides.ModdableWeathersAdapter.Acceptance', b'ModdableWeathersMonoProbe')
    method = get_method(klass, b'Run', 1) if klass else None
    if not method:
        raise RuntimeError('ModdableWeathersMonoProbe.Run was not found')
    arguments = (pointer * 1)(new_string(domain, str(managed).encode('utf-8')))
    exception = pointer()
    result = invoke(method, None, arguments, ctypes.byref(exception))
    if exception.value:
        formatting_error = pointer()
        description = to_string(exception, ctypes.byref(formatting_error))
        if formatting_error.value or not description:
            raise RuntimeError('The Moddable Weathers probe raised an exception whose description could not be formatted')
        raise RuntimeError(decode(description))
    if not result:
        raise RuntimeError('The Moddable Weathers probe returned no result')
    message = decode(result)
    if not message.startswith('PASS '):
        raise RuntimeError(message)
    if report:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps({
            'status': 'passed', 'message': message, 'runtime': str(runtime), 'probe': str(probe),
            'runtimeSha256': hashlib.sha256(runtime.read_bytes()).hexdigest(),
            'harmonySha256': hashlib.sha256(harmony.read_bytes()).hexdigest(),
            'adapterAssemblySha256': hashlib.sha256((probe.parent / 'ModdableFluids.ModdableWeathers.dll').read_bytes()).hexdigest(),
            'workshopSha256': {name: hashlib.sha256((folder / (name + '.dll')).read_bytes()).hexdigest() for name, folder in folders.items()},
            'scope': 'Installed Mono in a separate process; real Moddable Weathers 11.0.0 weathers, registry and history and real native '
                     'weather types; WeatherGenerator mirrored (it draws with UnityEngine.Random); no game process, scene or engine call',
        }, indent=2) + '\n', encoding='utf-8')
    print(message)


if __name__ == '__main__':
    main()
