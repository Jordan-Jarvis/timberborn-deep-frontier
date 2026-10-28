# Restaurant exterior shell repair

Source review, 2026-10-21. This is not an installed-game appearance or traversal result.

The reported see-through areas were reproducible missing geometry. A zero overlap report did not detect them, because overlap detection asks a different question.

Repairs in the producing sources:

- `grid_structure.room` reserved 20 cm for corner posts even where joined rooms intentionally had no perpendicular wall or post. The hall/kitchen side seam is now continuous. Its upper fascia now uses the actual surface intersection rather than the shorter beam butt-joint span.
- Full-width stairhead doors remove lower corner posts. The adjacent side wall now reaches the doorway return instead of stopping at the missing post.
- `framed_room` cladding now reaches its floor, ceiling and matching exterior corners. The projecting rounded frame no longer has to act as an opaque seal; door-overlapping posts resume above the lintel.
- Gabled roofs retain separate roof sheets and gable boards, with physical sheathing closing their 12 mm and 8 mm through-joints. An outward soffit closes their eaves. Dormer, roof-lantern and terrace stairhead curbs join the authored room and roof heights.
- Decks use a continuous 106 mm structural layer under 4 mm board relief, retaining the original 110 mm total thickness. Structural plate boundaries remain hard edges so adjoining tiles meet. Only the decorative finish is softened.
- The exposed rear-left cell of the entrance vestibule was open from above. `EntranceVestibuleCap` supplies a flush 1×1 roof at layer 2, carried by the existing room with no additional posts. Picking geometry now contains 115 boxes. The white roof terrace dimensions and its clear 3×3 construction area are unchanged.

`test_restaurant_shell.py` checks the evaluated Blender scene, including modifiers. It rejects inward-facing triangles and limits each ray to the nearby surface, so a distant wall cannot hide a hole. The final run passed **118,893 wall, oblique corner/joint, roof, gable and deck-joint probes with zero uncovered samples**. Exact failure coordinates from the initial and intermediate runs are retained in `outputs/restaurant-shell-before.json` and `outputs/restaurant-shell-intermediate.json`; the final report is `outputs/restaurant-shell-after.json`. The initial test included some below-terrain oblique rays; those invalid camera positions were removed from the final test. Outer-edge deck probes sit 0.5 mm inside the edge because a ray exactly tangent to a polygon boundary has no defined area coverage. Corner rays start 5 mm from the nominal facade end and finish inside the room, requiring the adjacent wall/frame to close the corner instead of demanding a surface outside a recessed frame. The independent 6,000-probe full-width doorway test remains unchanged and passes.

The user's close-up also identified floating windows. Old native-frame anchors sat 4–6 cm off the actual plaster. The native pane assemblies now use exact authored wall-plane anchors and an explicit 40 mm physical mounting reveal, preserving their native meshes and UVs. The reveal follows each native pane boundary and reaches back to the opaque wall; it provides real support while keeping panes ahead of projecting timber posts. Two ground factory windows were slightly resized and centered to fit the actual available wall span. One lower window hidden inside the vestibule was removed. All **43 window mounts passed 1,240 rear-perimeter wall-contact probes**, with every tested window and reveal excluded from the backing tree. Original native geometry/UV and physical reveal checks pass for all four styles in four orientations.

The strict evaluated overlap check also passed with zero sampled visible candidates. Source UV contracts, gallery clearance, terrace clearance and animation checks passed during the scene build. These checks do not prove native shader behavior, player-placed rail adaptation or save/reload behavior. The independent official export/build and game acceptance results belong in the project status record.

The review keeps both chimneys, all four door positions, the rear balcony, metalwork, native window varieties, fourteen seats and the unobstructed original white terrace. No interior furniture or room floors were added to hide gaps, and no coordinate cleanup, UV repair, depth bias or fallback was introduced.
