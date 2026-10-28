# Hospital: ward wings and central pavilion

The hospital now has two substantial seven-tile-long ward wings flanking a taller administration pavilion. Its two long ward roofs run front to back, while the central roof runs across them. Pale native plaster distinguishes the ward walls from the warmer central entrance. There is no copied restaurant roof lantern or side terrace tower.

The rear connector carries a clear 4 × 3 roof garden. A one-cell stairhead, with a native arch and attic window, opens directly onto it. The whole ground floor, ward gallery, upper rear gallery and roof door are connected internally. Exterior decks use player-placed paths. The 60 decorative rail openings follow individual adjacent path cells.

Source contracts are `hospital_structure.py`, `hospital_layout.py` and `hospital_geometry.py` under `tools/asset-pipeline`. The explicitly authored registration is 14 × 11 × 9, with door levels 0, 2, 4 and 6. Fifteen short posts support the outer galleries; the central building carries the roof garden. Room faces accept power on their exposed levels. Picking volumes follow the actual room and platform parts. Native mirroring is enabled in the building specification; runtime mirror acceptance is tracked separately.

The care behavior is unchanged: 30 patient places, six workers, 600 hp demand, injury recovery at 1.8 times the Medical Bed rate, native chipped-tooth and badwater treatment, and neighborhood wellbeing.

## Verification

The checked official export completed with zero visible overlap candidates across 214,762 evaluated triangles. Source tests sampled 345,600 authored exterior wall positions, 342,352 evaluated exterior wall positions, 140,800 roof positions and 280 beaver-body positions on suggested deck roads. A continuous route check also covers the spaces between grid-cell centers, including the shoulder clearance next to the ward roof eaves.

All 72 native window assemblies now sit on their actual wall skins through physical timber reveals. The gable windows have solid timber seats spanning the gaps between individual gable planks. A separate audit removed every window face from its backing tree and passed 2,290 contact probes around the mounting perimeters. This prevents the window's own reveal from incorrectly proving that it touches the wall. The native window meshes and atlas UVs remain intact.

These are source and export checks. The new care/placement fixture in `HospitalAcceptance.cs` uses actual player paths, a native stair flight, an external platform seam and a full roof-platform stack. Native placement, care operation and save/reload still need a new game run; earlier hospital runs do not prove this new geometry.

Review images are actual Blender renders from the source scene, with source and image hashes recorded in `review.json` in this folder. Only isometric panels of `docs/art/concepts/Hospital.png` informed this redesign; its top view and printed footprint were not used.
