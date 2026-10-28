# Restaurant native build114 review

Captured in Timberborn 1.1.2.8 after installing the repaired source through the official Mod Builder. Matching Blender close-ups and geometry evidence are in `../2026-10-21-exterior-repair/`; in particular, `Restaurant-wall-junction.png` shows the user's selected junction after its window mounts and shell seams were repaired.

`restaurant-serving.png` shows the main dining run. `restaurant-in-game.png` is the initial load capture and may contain the old fixture's loading dialog. Test platform stacks, shafts, stairs and paths surrounding the building are native placed entities, not parts of its mesh.

The main run passed:

- Four door connections, two native stairs in both directions and five actual walking destinations.
- Shafts supplying the building at three heights, under-deck path/shaft/tubeway placement, platform stacking and solid-room rejection.
- Selective decorative railing opening on both sides through path creation, deletion and recreation; adjacent unsupported panels remain visible.
- Workers serving real foods at tables, native production of four sweet berry cakes, coffee and thirst-dependent water service with stock accounting.
- Saved identities and coordinates for all 90 recorded placements, including 69 native paths and a native Rooftop Terrace on the unchanged white deck.

Main evidence: `outputs/restaurant-run114.log`, `outputs/restaurant-grid-run114.json`. Main archive SHA256: `78a0bcdb1038441f25a85093f02b59c163852c96132e1bd2b394766fc6092f8f`.

Fresh-process reload completed saved service without duplicate servings and passed Pause/Resume, power loss/restoration and staff off-duty/on-duty transitions. All 90 entity identities/positions survived; see `outputs/restaurant-reload114.log` and `outputs/restaurant-grid-reload114.json`. Reload archive SHA256: `6e4789ee5937df8bc193f1fb2c6b90b741ef93dd0988365d3f223220f5a56aef`. `restaurant-reload-verified.png` is the final paused game capture.

`restaurant-native-F-option.png` records the native duplication/placement panel with the F mirror option visibly available. No new building was placed during that UI inspection.

This fixture covers one authored orientation; the separate native mirror-preview check does not establish all finished mirrored seating, power or neighboring-building combinations.
