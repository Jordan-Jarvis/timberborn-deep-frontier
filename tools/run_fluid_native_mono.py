"""Run an isolated Fluids API probe inside the installed game's Mono, outside its process.

    run_fluid_native_mono.py <FluidsApi.NativeMonoProbe.dll> <reflection consumer.dll> <compiled consumer.dll>
    run_fluid_native_mono.py --absent <FluidsApi.AbsenceProbe.dll> <reflection consumer.dll> <compiled consumer.dll>

The absent mode searches only the game's Managed folder and the absence probe's own folder,
which holds no FluidsApi.dll, so the API is genuinely missing as in an install without it.
"""
import ctypes
import hashlib
import json
import sys
from pathlib import Path

import dev_environment as dev


def main():
    arguments = sys.argv[1:]
    absent = arguments[:1] == ['--absent']
    if absent:
        arguments = arguments[1:]
    if len(arguments) != 3:
        raise SystemExit(__doc__)
    probe, reflection, compiled = (Path(a).resolve(strict=True) for a in arguments)
    if absent and (probe.parent / 'FluidsApi.dll').exists():
        raise SystemExit('The absence probe folder must not contain FluidsApi.dll')
    consumers = str(reflection) + ';' + str(compiled)
    managed = dev.managed()
    runtime = dev.game_root() / 'MonoBleedingEdge' / 'EmbedRuntime' / 'mono-2.0-bdwgc.dll'
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

    # This is a separate worker process. The game process and its loaded mods are untouched.
    set_path((str(managed) + ';' + str(probe.parent)).encode('utf-8'))
    domain = initialize(b'FluidsApiNativeProbe', b'v4.0.30319')
    if not domain:
        raise RuntimeError('Installed Mono did not initialize')
    harmony = Path(dev.get('timberbornDocuments')) / 'ModsBuild' / 'TimberbornModExamples_Data' / 'Managed' / '0Harmony.dll'
    if not absent and not open_assembly(domain, str(harmony.resolve(strict=True)).encode('utf-8')):
        raise RuntimeError('Installed Harmony dependency did not load in the isolated Mono host')
    assembly = open_assembly(domain, str(probe).encode('utf-8'))
    if not assembly:
        raise RuntimeError('Installed Mono did not load the probe assembly')
    namespace, name, count = (b'FluidsApi.Absence', b'AbsenceProbe', 1) if absent else (b'FluidsApi.Native.Acceptance', b'MonoProbe', 2)
    klass = get_class(get_image(assembly), namespace, name)
    method = get_method(klass, b'Run', count) if klass else None
    if not method:
        raise RuntimeError('Mono probe Run was not found')
    values = [consumers] if absent else [str(managed), consumers]
    arguments = (pointer * count)(*[new_string(domain, v.encode('utf-8')) for v in values])
    exception = pointer()
    result = invoke(method, None, arguments, ctypes.byref(exception))
    if exception.value:
        formatting_error = pointer()
        description = to_string(exception, ctypes.byref(formatting_error))
        if formatting_error.value or not description:
            raise RuntimeError('Mono probe raised an exception whose description could not be formatted')
        raise RuntimeError(decode(description))
    if not result:
        raise RuntimeError('Mono probe returned no result')
    message = decode(result)
    if not message.startswith('PASS '):
        raise RuntimeError(message)
    report = dev.ROOT / 'outputs' / 'fluids-api-prototype' / ('mono-absence-report.json' if absent else 'mono-report.json')
    report.parent.mkdir(parents=True, exist_ok=True)
    consumer_hashes = [{'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in (reflection, compiled)]
    if absent:
        report.write_text(json.dumps({
            'status': 'passed', 'runtime': str(runtime), 'probe': str(probe), 'message': message, 'consumers': consumer_hashes,
            'scope': 'Embedded installed Mono in a separate process whose search path has no FluidsApi.dll; consumers byte-loaded like ModCodeStarter'
        }, indent=2) + '\n', encoding='utf-8')
        print(message)
        return
    report.write_text(json.dumps({
        'status': 'passed', 'runtime': str(runtime), 'probe': str(probe), 'message': message,
        'runtimeSha256': hashlib.sha256(runtime.read_bytes()).hexdigest(),
        'harmonyAssembly': str(harmony), 'harmonySha256': hashlib.sha256(harmony.read_bytes()).hexdigest(),
        'apiAssemblies': [{ 'path': str(probe.parent / name),
                            'sha256': hashlib.sha256((probe.parent / name).read_bytes()).hexdigest() }
                          for name in ['FluidsApi.dll', 'FluidsApi.TransportPrototype.dll', 'FluidsApi.GamePrototype.dll']],
        'consumers': consumer_hashes,
        'scope': 'Embedded installed Mono in a separate process; actual native scheduler patched with immediate fixture execution; live worker barriers and settlement acceptance remain pending'
    }, indent=2) + '\n', encoding='utf-8')
    print(message)


if __name__ == '__main__':
    main()
