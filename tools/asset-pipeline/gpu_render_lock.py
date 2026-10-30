"""One GPU render at a time across every Blender process on this machine.

A Cycles render on the RTX 2060 keeps one CPU core busy for as long as it
holds the GPU (the host thread waiting on OptiX), so concurrent renders from
several agents time-slice the GPU and each spins a core. Every renderer calls
render() instead of bpy.ops.render.render(): it waits, without a timeout, for
the named Windows mutex Local\\DeepFrontierGpuRender, renders, and releases it.

The mutex is a kernel object owned by the waiting thread: if a process dies
while rendering, Windows releases it (the next waiter gets WAIT_ABANDONED and
renders normally), so a crash never leaves a stale lock behind.
"""
import ctypes
import time
from contextlib import contextmanager
from ctypes import wintypes

import bpy

NAME = 'Local\\DeepFrontierGpuRender'
INFINITE = 0xFFFFFFFF
WAIT_OBJECT_0, WAIT_ABANDONED, WAIT_TIMEOUT = 0x0, 0x80, 0x102

_kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
_kernel32.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
_kernel32.CreateMutexW.restype = wintypes.HANDLE
_kernel32.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
_kernel32.WaitForSingleObject.restype = wintypes.DWORD
_kernel32.ReleaseMutex.argtypes = (wintypes.HANDLE,)
_kernel32.ReleaseMutex.restype = wintypes.BOOL
_kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
_kernel32.CloseHandle.restype = wintypes.BOOL


def _wait(handle, milliseconds):
    result = _kernel32.WaitForSingleObject(handle, milliseconds)
    if result not in (WAIT_OBJECT_0, WAIT_ABANDONED, WAIT_TIMEOUT):
        raise ctypes.WinError(ctypes.get_last_error())
    return result != WAIT_TIMEOUT


@contextmanager
def held():
    handle = _kernel32.CreateMutexW(None, False, NAME)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        if not _wait(handle, 0):
            print('GPU RENDER LOCK: waiting for another process to finish rendering', flush=True)
            started = time.monotonic()
            _wait(handle, INFINITE)
            print(f'GPU RENDER LOCK: acquired after {time.monotonic() - started:.1f} s', flush=True)
        try:
            yield
        finally:
            if not _kernel32.ReleaseMutex(handle):
                raise ctypes.WinError(ctypes.get_last_error())
    finally:
        _kernel32.CloseHandle(handle)


def render(**kwargs):
    """bpy.ops.render.render(**kwargs) under the machine-wide GPU render lock."""
    with held():
        return bpy.ops.render.render(**kwargs)
