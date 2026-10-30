"""Persistent GPU visibility service: one warm Blender takes visibility jobs
from every agent.

Initialising the GPU in a background Blender costs about 1 CPU-s per process
(gpu_visibility.init_gpu), more than a whole small audit. The service pays it
once: a long-lived `blender -b` keeps the GPU context and runs the jobs that
clients send it over 127.0.0.1:PORT, one at a time in arrival order.

Clients (audit_hidden_geometry.py's main) keep their command line: they send
their own script path, entry function, arguments and working directory, wait,
print the job's output and exit with its status. When no service is
listening, the client starts one (detached, log in LOG) and waits for it;
there is no CPU path to fall back to.

Each job runs the client's own copy of the script (so mirrors and the real
repository each use their own code and ROOT) with sys.path, sys.argv and the
working directory set as the client had them. Afterwards the job's modules
(everything loaded from outside Blender's installation) are dropped and the
scene is reset to factory settings, so nothing carries over between jobs.
A Python exception or SystemExit in a job is returned to its client as a
failure; the service keeps running. A native crash ends the service: that
client reports it, and the next submission starts a fresh service.

The service stops on request (`python gpu_visibility_service.py stop`) or
after IDLE_EXIT seconds without a job.

    python gpu_visibility_service.py status|stop        (no Blender needed)
"""
import contextlib
import importlib.util
import io
import json
import os
import socket
import struct
import subprocess
import sys
import time
import traceback
from pathlib import Path

HOST, PORT = '127.0.0.1', 47613
PROTOCOL = 'deep-frontier-gpu-visibility/1'
IDLE_EXIT = 3600
START_TIMEOUT = 180          # seconds a freshly started service may take to accept
LOG = Path(os.environ['USERPROFILE']) / 'dfs' / 'gpu-visibility-service.log'
HERE = Path(__file__).resolve().parent


def _send(sock, obj):
    data = json.dumps(obj).encode('utf-8')
    sock.sendall(struct.pack('>I', len(data)) + data)


def _exact(sock, n):
    buf = b''
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError('connection closed')
        buf += chunk
    return buf


def _recv(sock):
    return json.loads(_exact(sock, struct.unpack('>I', _exact(sock, 4))[0]).decode('utf-8'))


def _connect():
    """A connection to the running service (its greeting checked), or None
    when nothing listens on the port."""
    try:
        sock = socket.create_connection((HOST, PORT), timeout=5)
    except (ConnectionRefusedError, TimeoutError, socket.timeout):
        return None
    sock.settimeout(None)            # a queued client waits for its turn
    hello = _recv(sock)
    if hello.get('protocol') != PROTOCOL:
        sock.close()
        raise RuntimeError(f'{HOST}:{PORT} answers {hello!r}, not {PROTOCOL}; stop that process '
                           f'(an older service: python {HERE / "gpu_visibility_service.py"} stop)')
    return sock


def _start(blender):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    print(f'GPU VISIBILITY SERVICE: starting {blender} (log {LOG})', flush=True)
    with open(LOG, 'ab') as log:
        subprocess.Popen([str(blender), '-b', '--factory-startup', '--python-exit-code', '1',
                          '--python', str(HERE / 'gpu_visibility_service.py'), '--', '--serve'],
                         stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, close_fds=True,
                         creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)


def _request(obj, blender=None):
    sock = _connect()
    if sock is None:
        if blender is None:
            raise RuntimeError('the GPU visibility service is not running')
        _start(blender)
        deadline = time.monotonic() + START_TIMEOUT
        while sock is None:
            if time.monotonic() > deadline:
                raise RuntimeError(f'the GPU visibility service did not start within {START_TIMEOUT} s; see {LOG}')
            time.sleep(.5)
            sock = _connect()
    with sock:
        _send(sock, obj)
        try:
            return _recv(sock)
        except ConnectionError:
            raise RuntimeError(f'the GPU visibility service ended during this job (native crash?); see {LOG}. '
                               'The next submission starts a fresh service.') from None


def submit(script, entry, argv):
    """Run `entry()` of `script` in the service with these arguments; print its
    output and exit as the job did (SystemExit with its message on failure)."""
    import bpy
    reply = _request({'op': 'run', 'script': str(Path(script).resolve()), 'entry': entry,
                      'argv': list(argv), 'cwd': os.getcwd()}, blender=bpy.app.binary_path)
    sys.stdout.write(reply['output'])
    sys.stdout.flush()
    if reply['code']:
        raise SystemExit(reply['message'] or f'{Path(script).name} failed in the GPU visibility service')


# ---------------------------------------------------------------- service side

def _purge(install):
    """Drop every module loaded from outside Blender's installation."""
    for name, module in list(sys.modules.items()):
        path = getattr(module, '__file__', None)
        if name == '__main__' or not path:
            continue
        try:
            Path(path).resolve().relative_to(install)
        except ValueError:
            del sys.modules[name]


def _run_job(req, install):
    import bpy
    started, cpu = time.time(), time.process_time()
    out = io.StringIO()
    code, message = 0, None
    saved = (list(sys.path), list(sys.argv), os.getcwd())
    script = Path(req['script'])
    try:
        os.chdir(req['cwd'])
        sys.path.insert(0, str(script.parent))
        sys.argv = [bpy.app.binary_path, '--'] + req['argv']
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            spec = importlib.util.spec_from_file_location('gpu_visibility_job', script)
            module = importlib.util.module_from_spec(spec)
            sys.modules['gpu_visibility_job'] = module
            spec.loader.exec_module(module)
            getattr(module, req['entry'])()
    except SystemExit as exit_:
        if exit_.code not in (None, 0):
            code = 1
            message = exit_.code if isinstance(exit_.code, str) else None
    except BaseException:
        code = 1
        out.write(traceback.format_exc())
    finally:
        sys.path[:], sys.argv[:] = saved[0], saved[1]
        os.chdir(saved[2])
        _purge(install)
        bpy.ops.wm.read_factory_settings(use_empty=True)
    return {'code': code, 'message': message, 'output': out.getvalue(),
            'seconds': round(time.time() - started, 2), 'cpuSeconds': round(time.process_time() - cpu, 2)}


def serve():
    import bpy
    install = Path(bpy.app.binary_path).resolve().parent
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    try:
        server.bind((HOST, PORT))
    except OSError:
        print('GPU VISIBILITY SERVICE: port taken (another service is starting or running); exiting', flush=True)
        return
    server.listen(64)
    server.settimeout(30)
    sys.path.insert(0, str(HERE))
    import gpu_visibility
    gpu_visibility.init_gpu()          # the one-time cost the service exists to keep
    sys.path.remove(str(HERE))
    _purge(install)
    stats = {'pid': os.getpid(), 'jobs': 0, 'failed': 0, 'started': time.time()}
    print(f'GPU VISIBILITY SERVICE: ready on {HOST}:{PORT}, pid {os.getpid()}', flush=True)
    last = time.time()
    while True:
        try:
            conn, _ = server.accept()
        except socket.timeout:
            if time.time() - last > IDLE_EXIT:
                print('GPU VISIBILITY SERVICE: idle; exiting', flush=True)
                break
            continue
        with conn:
            conn.settimeout(None)
            try:
                _send(conn, {'protocol': PROTOCOL, 'pid': os.getpid()})
                req = _recv(conn)
                if req['op'] == 'stop':
                    _send(conn, {'stopped': True, **stats})
                    print('GPU VISIBILITY SERVICE: stop requested; exiting', flush=True)
                    break
                if req['op'] == 'status':
                    _send(conn, {**stats, 'cpuSeconds': round(time.process_time(), 2)})
                    continue
                if req['op'] != 'run':
                    _send(conn, {'code': 1, 'message': f"unknown operation {req['op']!r}", 'output': ''})
                    continue
                print(f"GPU VISIBILITY SERVICE: job {stats['jobs'] + 1}: {req['script']} {req['argv']}", flush=True)
                reply = _run_job(req, install)
                stats['jobs'] += 1
                stats['failed'] += bool(reply['code'])
                print(f"GPU VISIBILITY SERVICE: job {stats['jobs']} exit {reply['code']} "
                      f"{reply['seconds']} s, {reply['cpuSeconds']} CPU-s", flush=True)
                _send(conn, reply)
            except (ConnectionError, OSError, ValueError, KeyError) as error:
                print(f'GPU VISIBILITY SERVICE: dropped a connection: {error!r}', flush=True)
        last = time.time()
    server.close()


def main():
    if '--' in sys.argv and '--serve' in sys.argv[sys.argv.index('--') + 1:]:
        serve()
        return
    if len(sys.argv) != 2 or sys.argv[1] not in ('status', 'stop'):
        raise SystemExit('usage: python gpu_visibility_service.py status|stop')
    sock = _connect()
    if sock is None:
        print('GPU visibility service: not running')
        return
    with sock:
        _send(sock, {'op': sys.argv[1]})
        print(json.dumps(_recv(sock)))


if __name__ == '__main__':
    main()
