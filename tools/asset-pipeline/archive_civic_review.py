"""Archive the accepted civic Blender review; this does not export game assets."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "outputs/reference-studies"
DEST = ROOT / "docs/art/reviews/2026-10-19-civic"
MODELS = ("Hospital", "Restaurant", "GroceryStore", "FisheryWorks")
REFERENCES = ("Hospital.png", "Resturaunt.png", "Grocery Store.png", "Fishery.png")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


files = []
models = []
for model, reference in zip(MODELS, REFERENCES, strict=True):
    motion = json.loads((SOURCE / f"{model}-motion-check.json").read_text())
    video = json.loads((SOURCE / f"{model}-video-check.json").read_text())
    heights = json.loads((SOURCE / f"{model}-height-manifest.json").read_text())
    if video["frames"] != motion["previewFrames"] or video["fps"] != motion["previewFps"]:
        raise ValueError(f"Video/report mismatch: {model}")
    if heights["entranceLayers"] != [0, 2, 4, 6]:
        raise ValueError(f"Incorrect source doorway layers: {model}")
    for part in motion["parts"]:
        if part["loopMatrixError"] > 0.0001 or part["sampleMatrixDifference"] <= 0:
            raise ValueError(f"Invalid animation evidence: {model}/{part['name']}")
    files.extend(f"{model}-{angle}.png" for angle in ("front", "front-right", "rear"))
    files.append(f"{model}-motion.mp4")
    files.extend(f"{model}-{name}.json" for name in (
        "motion-check", "video-check", "clearance-check", "access-manifest",
        "height-manifest", "native-assembly", "rail-manifest", "study",
        "terrace-manifest", "visitor-manifest"))
    files.extend(f"{model}-video-frame-{frame:03d}.png" for frame in video["decodedReviewFrames"])
    scene = ROOT / f"src/DeepFrontier/Art/Source/{model}-ReferenceStudy.blend"
    concept = ROOT / "docs/art/concepts" / reference
    models.append({
        "model": model, "scene": scene.relative_to(ROOT).as_posix(), "sceneSha256": sha256(scene),
        "concept": concept.relative_to(ROOT).as_posix(), "conceptSha256": sha256(concept),
        "animatedParts": len(motion["parts"]), "vertices": motion["sourceVertices"],
        "polygons": motion["sourcePolygons"], "railNodes": motion["separateRailNodes"],
        "previewSeconds": video["frames"] / video["fps"],
    })
files.extend(("Hospital-planter-detail.png", "Hospital-terrace-detail.png",
              "NativePlants-original.png", "FisheryWorks-water-full.png",
              "FisheryWorks-water-half.png", "FisheryWorks-water-empty.png",
              "FisheryWorks-water-preview.json"))
if len(set(files)) != len(files):
    raise ValueError("Duplicate review filenames")
for name in files:
    if not (SOURCE / name).is_file():
        raise FileNotFoundError(SOURCE / name)

DEST.mkdir(parents=True, exist_ok=True)
copied = []
for name in files:
    shutil.copy2(SOURCE / name, DEST / name)
    digest = sha256(SOURCE / name)
    if sha256(DEST / name) != digest:
        raise ValueError(f"Archive copy differs: {name}")
    copied.append({"path": name, "sha256": digest})
manifest = {
    "date": "2026-10-19", "scope": "Blender source and previews; civic game integration pending",
    "foliageStatus": "User accepted; no further plant design change in this archive pass",
    "models": models, "files": copied,
    "geometryEvidence": "Current motion-check reports include geometry, material and clearance checks; older standalone geometry-check reports are excluded.",
}
(DEST / "review-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps({"archivedFiles": len(copied), "models": models}, indent=2))
