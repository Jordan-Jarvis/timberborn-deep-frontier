"""Prepare deterministic Unity asset-bundle inputs for Deep Frontier materials.

The Timbermesh exporter stores material names, while Unity materials and their
texture references live in the mod AssetBundle. This script copies the authored
texture source maps into the bundle input tree. The Unity editor build step
creates the serialized .mat assets and the platform bundle.
"""

import os
import shutil


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SOURCE_TEXTURES = os.path.join(ROOT, "src", "DeepFrontier", "Art", "Textures")
BUNDLE_TEXTURES = os.path.join(
    ROOT,
    "src",
    "DeepFrontier",
    "AssetBundles",
    "Resources",
    "Materials",
    "DeepFrontier",
)


def main():
    os.makedirs(BUNDLE_TEXTURES, exist_ok=True)
    mappings = {
        "DeepFrontierMetal.png": "DeepFrontierMetal.BaseColor.png",
        "DeepFrontierOre.png": "DeepFrontierPainted.BaseColor.png",
        "DeepFrontierHazard.png": "DeepFrontierRock.BaseColor.png",
    }
    for source_name, destination_name in mappings.items():
        source = os.path.join(SOURCE_TEXTURES, source_name)
        destination = os.path.join(BUNDLE_TEXTURES, destination_name)
        if not os.path.isfile(source):
            raise FileNotFoundError(source)
        shutil.copyfile(source, destination)
        print(f"Prepared {destination}")


if __name__ == "__main__":
    main()
