"""Validate that finished Deep Frontier models carry a playable Timbermesh clip."""

import sys
import json
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "tools" / "asset-pipeline" / "timbermesh-plugin" / "timbermesh_blender_plugin"
sys.path.insert(0, str(PLUGIN))
import model_pb2  # noqa: E402


def read_model(path: Path):
    model = model_pb2.Model()
    model.ParseFromString(zlib.decompress(path.read_bytes()))
    return model


finished = sorted((ROOT / "src" / "DeepFrontier" / "Data" / "Buildings").rglob("*.IronTeeth.Model.timbermesh"))
if not finished:
    raise SystemExit("No finished Timbermesh models were found.")

missing = []
summary = []
passive = {b['id'] for b in json.loads((ROOT/'tools/structural_content.json').read_text())['buildings']}
static_models = []
for path in finished:
    model = read_model(path)
    clips = [animation for node in model.nodes for animation in node.nodeAnimations]
    ident=path.name.removesuffix('.IronTeeth.Model.timbermesh')
    if ident in passive:
        if clips:
            raise SystemExit(f'Passive structure unexpectedly animates: {path}')
        static_models.append(ident)
    elif not clips or max(len(animation.frames) for animation in clips) < 2:
        missing.append(str(path.relative_to(ROOT)))
    else:
        summary.append({"path": str(path.relative_to(ROOT)), "nodes": len(model.nodes), "clips": len(clips), "frames": max(len(animation.frames) for animation in clips)})

if missing:
    raise SystemExit(f"Finished models without a playable animation: {missing}")

print({"status": "ok", "finishedModels": len(finished), "animatedModels": len(summary), "staticStructures": static_models, "sample": summary[:3]})
