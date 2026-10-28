#!/usr/bin/env bash
# Run the pinned Blender at below-normal CPU priority so renders and audits
# don't make the desktop crawl. Arguments pass straight through; the exit
# status is Blender's.
B="$(cd "$(dirname "$0")" && pwd)/blender-4.5.3/blender.exe"
"$B" "$@" &
pid=$!
winpid=$(cat /proc/$pid/winpid 2>/dev/null)
if [ -n "$winpid" ]; then
  powershell.exe -NoProfile -Command "try { (Get-Process -Id $winpid).PriorityClass = 'BelowNormal' } catch {}" >/dev/null 2>&1
fi
wait $pid
