# Native building mirroring

Target: Timberborn 1.1.2.8. Every Deep Frontier building must expose the game's F mirroring action. The producing blueprint must explicitly set `BlockObjectSpec.Flippable` to `true`; mirrored replacement meshes and custom input handlers are unnecessary.

The installed `Timberborn.BlockObjectToolsUI.BlockObjectPlacementPanel.OnToolEntered` reads that exact spec property, binds the native `Flip` shortcut, calls `PreviewPlacement.EnableFlipping`, and shows the Flip button only when it is true. This is the source-confirmed cause of the missing F action. The inspection is archived in `outputs/Timberborn.BlockObjectToolsUI-mirroring.cs`.

The installed game's `Timberborn.BlockSystem.BlockObject` applies the placement's `FlipMode` to occupied cells, entrances and direction transforms. Its visual root gets the corresponding negative X scale and width offset. Custom world points must use that same root's `TransformPoint`, or `BlockObject.TransformCoordinates` for grid points. This includes worker positions, restaurant seats, deck openings, reservoir props and machinery ports. A manual rotation without the flip is insufficient for an asymmetric direction.

Native saving records `BlockObject.Flipped`; native loading honors it when the current blueprint permits flipping. Turning the flag off later would change the interpretation of saved mirrored buildings, so it is part of the authored placement contract.

`tools/building_asset_catalog.json` enumerates all 41 active templates and their source owners. Run `tools/audit_building_assets.py --require-mirroring` after canonical content generation. It rejects an unregistered template or any generated building that disables mirroring. The audit records source and exported mesh hashes; these are provenance, not runtime proof.

`tools/start_mirroring_acceptance.ps1 -Build <number>` launches an explicitly marked disposable settlement with the native preview test. `MirroringAcceptance.cs` creates every template at four rotations, with and without flipping. It checks every cell center, fractional boundary points and native entrance coordinates against the visual root transform. It destroys only its own preview objects. Success is the `ALL NATIVE PREVIEW CHECKS PASSED` marker in `outputs/mirroring<number>.log`.

Build114 completed this native test: all 41 buildings, 328 preview placements and 76,800 point probes passed (`outputs/mirroring114.log`). The official installed package matched 474 authored data/manifest/DLL hashes before launch. This verifies native root, cell and entrance transforms in all four rotations and both flip states.

The restaurant's native duplication/placement UI was also inspected after the build114 reload: its F mirror button is visible next to R and Shift+R. Screenshot: `reviews/2026-10-21-exterior-repair-runtime/restaurant-native-F-option.png`. This verifies the previously missing UI option. An automated keyboard press had no visually established result, so it is not recorded as a keyboard pass.

The preview and UI checks do not establish every production, hydraulic, seating, adjacent-path or save/reload scenario for finished mirrored buildings. Record additional interaction checks separately in `tools/STATUS.md`.
