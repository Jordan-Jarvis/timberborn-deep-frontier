# Quarry reservoir runtime check

Official build 23 uses the original native Iron Teeth Small Tank model/materials and a native liquid plane for the existing quarry water barrel. The surface displays the actual Manufactory Water stock; it is not a separate inventory.

`outputs/native-water-run23.log` passed both sandstone and limestone quarries through empty (0), half (8), full (16), drained (0) and refilled (8). Capacity is 16. Surface local heights are 1.36852, 1.63946 and 1.9104 respectively. Empty surfaces are inactive. The fixture was saved using the native game saver as `Industrial Acceptance / Reservoir acceptance - verified`.

The automatic state captures were obscured by a Weather Settings dialog from another installed mod, so they are not visual acceptance evidence. [The inspected half-full barrel](quarry-water-refilled-visible.jpg) was captured after closing that dialog. The original user's settlement was not edited; these tests used the explicitly marked disposable acceptance fixture.

Fresh-process persistence **passed** in `outputs/native-water-reload23.log`: both quarries restored 8/16 water, visible surfaces and local Y 1.63946. [The inspected build-23 reload](quarry-water-reloaded-build23.jpg) shows the half-full native barrel. Existing walkway reload checks passed too. Build 23 pauses the test workplaces before saving so they cannot consume the test stock before the reload assertion; their saved paused state is also asserted. The fishery's larger basins, inventory-driven cascades and wheel gating remain civic integration work.

Build evidence: `outputs/native-water-build23.log`; the exact official player DLL and all 415 authored data files match the installed package in `outputs/native-water-package-verification23.json`. Earlier build-22 records remain historical evidence.
