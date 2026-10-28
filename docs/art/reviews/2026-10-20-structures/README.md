# Concrete, masonry and reinforced structures

Original modular designs using the established Iron Teeth native material palette. These are grid construction pieces rather than reconstructions of a concept-sheet plan. No top-down reference was used. Passive structures have no animation.

| Model | Size | Purpose |
| --- | --- | --- |
| SandstoneMasonryBlock | 1×1×1 | Mortared retaining block |
| LimestoneMasonryBlock | 1×1×1 | Pale retaining block |
| ConcreteBlock | 1×1×1 | Concrete levee and foundation |
| ReinforcedDamBlock | 1×1×1 | Exposed steel cage with concrete infill |
| ConcreteOverflowDam | 1×1×1 | 0.65-layer sill under a supported top |
| ConcreteOverhang8x1 | 1×8×1 | One anchor and seven cantilever cells |
| ConcreteScaffold3x3 | 3×3×4 | Tall deck with an open central cross |
| ConcreteScaffold{3x3,4x4,5x5}H{1,2,3} | n×n×(H+1) | Concrete platform variants: same deck/column design, legs 1–3 layers; 4×4/5×5 add deck joists |

Each has front and opposite isometric renders in this folder. `structure-ivory-icons.png` shows the original transparent UI art at 128px and 32px.

Saved-source inspection checked all seven modules' actual bounds, 550 support-surface samples, 66 open-passage samples and native-atlas UVs. The first overflow revision had a bolt 0.0055 above the support plane; its authored position was lowered and the final scene rerendered. The first reinforced-block render hid its cage inside the concrete; the infill was recessed at source and rerendered. Final checks passed. The official Timbermesh export has three static nodes per model and matching construction-stage geometry. Source/export reports are in `outputs/structural-integration`.

The renders show Blender shading. Native build 90 separately passed all seven templates in four rotations, unsupported placement rejection, twelve-layer masonry stacking, native stairs and platform stacks, shafts/tubeways below open decks, sealed-water retention, native 0.65 crest registration, vanilla spill parity and six actual walking destinations.

Fresh-process reload 91 restored all 136 expected identities/positions and the actual native save's water depths, then repeated the six walking destinations and saved again. The concrete and native control pools both retained 0.3843088. [Main screenshot](Structures-native-build90.jpg) and [reload screenshot](Structures-native-reload91.jpg) show the installed models. The original failed pre-save checkpoint expectation was corrected at its source; no game water behavior was changed. See `tools/STATUS.md` for archive hashes and the test history.

The controlled dam turbine remains a separate model and gameplay task. These fixtures do not establish economic cost balance.

## Concrete platform variants (2026-10-21)

The eight variants (`ConcreteScaffold3x3H1`, `3x3H2`, `4x4H1`–`H3`, `5x5H1`–`H3`) come from `structural_geometry.scaffold_for(n, legs)`, which also reproduces the original 3×3 three-high scaffold exactly. The original's template is unchanged; only its display text is now "Concrete platform 3×3 (3 high)". Cost: k = n² + H, k × (3 Concrete, 2 Metal Block, 1 Gear), 500k science. Front and front-right renders are `outputs/reference-studies/<ident>-front.png` and `-front-right.png`; the icon sheet above includes all eight variant icons from `tools/create_scaffold_icon_svgs.mjs`. They have strict overlap and export checks only. No native placement test has been run.
