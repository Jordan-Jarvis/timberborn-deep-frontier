# Native materials and factory integration review

Timberborn 1.1.2.8, Iron Teeth. These are actual game captures from official build 15, installed through the official Mod Builder. Architecture and door layout are preserved. The tall plain platform towers and external stairs are vanilla objects placed for acceptance testing.

## Texture correction

The previous world-space repeating UVs sampled unrelated regions of native atlas materials. Beam, plank and roof faces now receive bounded UV islands at mesh creation, with grain along each face's long edge. No exported UV wrapping, clamping, missing-material substitution or runtime repair was added.

The actual Iron Teeth materials are `BaseWood_DarkBrown.IronTeeth`, `IrregularPlanks_DarkBrown.IronTeeth` and `PaintedMetal.IronTeeth`. Other machinery materials retain their authored identities. Export validation checked 600,485 native-material vertices across the four building variants. Source and installed DLL/data hashes agree in `outputs/industrial-integration/run15-build-hashes.json`.

| View | Capture |
| --- | --- |
| Previous atlas error | [Before](before-atlas-mapping.jpg) |
| Crusher, shared decks, native stairs and platform stacks | [Crusher](crusher-native-materials.png) |
| Roofed kiln and native stairs | [Kiln](kiln-native-materials.png) |
| Quarry, native stair, gallery ladders and platform stacks | [Quarry](quarry-native-materials.png) |
| Limestone quarry consuming 1,500 hp through a vanilla shaft | [Power panel](limestone-native-shaft-power.jpg) |

## Run 15 results

Evidence: `outputs/industrial-game-run15.log`.

- Four generator → vanilla shaft → factory connections passed, with 5,000 hp available from each developer generator. This is test supply, not a change to factory demand.
- Seven native stair upper exits opened their corresponding rail panels. The fixture includes every factory instance and the kiln's rear access.
- Five deck locations accepted a Double Platform, two additional Platforms and a top Path. Coverage includes a rotated crusher and the quarry's layer-7 gallery. Actual equipment and open ladder hatches remain unavailable for support.
- Twelve under-deck placements accepted native Paths, Power Shafts and Tubeways; three solid-room locations correctly rejected Paths.
- Thirty-five rail assertions passed, including shared decks, rotation, wrong-facing stairs, unfinished paths, individual segment removal and restoration.
- A real beaver reached eight movement targets through native control/pathfinding: crusher approach and deck, the neighboring crusher's shared deck, kiln approach and rear gallery, quarry approach, top ladder gallery and engine-room doorway approach. No teleport was used for this sequence.
- All four native workshops produced Aggregate, Cement, Sandstone and Limestone from recipe inputs. The limestone workplace was raised to highest priority through its normal UI after the colony reassigned its worker.
- The game's native save service wrote `Industrial Acceptance/Industrial acceptance - verified.timber` after production and walking passed. Run 17 subsequently reloaded that save in a fresh process: all 17 connection/rail assertions and all six ground-to-deck routes passed. All six factories retained valid native requirements. Evidence: `outputs/industrial-game-run17-reload.log` and `outputs/industrial-integration/run17-build-hashes.json`.

Run 16 preserved every expected route and connection, but exposed a stale fixture assertion: native builders had completed the deliberately unfinished path during production. The railing correctly opened. Build 17 explicitly requires that path to be completed before saving and checks its completed state and open railing on reload. The mesh and gameplay implementation are unchanged by this test correction.

The production fixture intentionally supplies inputs and developer power; this verifies operation, not colony-wide logistics or progression balance. The extra disconnected/unpowered crusher instances serve shared-deck and rotation tests, so their warning icons are expected. Tests cover the listed arrangements; they are not proof of every rotation, terrain shape or dependency combination.
