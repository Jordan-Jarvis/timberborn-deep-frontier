# Dependency matrix (Timberborn 1.1)

Which of these are required and which are optional integrations, and why, is in [the dependency reference](dependency-reference.md#required-and-optional-mods-060-2026-10-30); the manifest's RequiredMods and OptionalMods are authoritative. Pump to Tank, Flywheels, Teleporter Stations, Solar Panel, Expanded Storage, Powered Tubeway and Power Lines are not required. These are the intended foundation mods. Version numbers are recorded when an installed package is available and must be rechecked after updates. Deep Frontier's design layer is Iron Teeth. See the [dependency reference](dependency-reference.md) for verified 1.1 mechanics, exact public costs and unlocks, recipes, declared requirements, package facts, and stacking rules.

The load profile also pins the 1.1 support stack required by the foundation set: Harmony 2.4.1, Moddable Timberborn 11.1.3, Moddable Tool Groups 11.0.0, Mod Settings 1.1.1.0, and TimberUi 11.0.1. They are recorded in `tools/installed_dependency_manifests_1_1.json` and are declared by the Deep Frontier shell so a missing support package fails early with a useful dependency message.

| Mod | Role in Deep Frontier | Integration boundary | Source |
|---|---|---|---|
| Pump to Tank | foundation water logistics | use the existing tank/pump behavior adapter; Deep Frontier does not reimplement it | https://steamcommunity.com/workshop/filedetails/?id=3681283725 |
| Flywheels | mechanical energy buffer | power network adapter; exact capacity/cost pending | https://steamcommunity.com/sharedfiles/filedetails/?id=3322428023 |
| Wormhole and Ring Teleporter Stations | long-distance logistics | transport endpoint API; station costs and Extract crossing rule recorded | https://steamcommunity.com/sharedfiles/filedetails/?id=3813842276 |
| Timber Pipes (Workshop 3801726769, 11.4.0) | liquid transport | installed Version-1.1 package; pipe connection/throughput adapter; current public costs and unlocks recorded | https://steamcommunity.com/sharedfiles/filedetails/?id=3801726769 |
| Northforge - Solar Panel (Workshop 3801036916, 1.0.2) | renewable power | Iron Teeth 1x1x1 producer, up to 100 hp, 250 science; optional Northforge.Core | https://steamcommunity.com/sharedfiles/filedetails/?id=3801036916 |
| Expanded Storage (Workshop 3795292508, 1.0.1) | bulk resource buffering | Iron Teeth grand stores and BlockObject stackable modules; exact capacities, dimensions, costs, and science captured | https://steamcommunity.com/sharedfiles/filedetails/?id=3795292508 |
| Conveyor Belts v2 (Workshop 3815376360, 11.4.0) | item logistics | installed Version-1.1 package; belt endpoint adapter; exact per-piece costs pending | https://steamcommunity.com/sharedfiles/filedetails/?id=3815376360 |
| Powered Tubeway (Workshop 3543155128, 11.0.0) | powered item transport | installed Version-1.1 behavior patch; tubeway endpoint adapter; no new recipe verified | https://steamcommunity.com/sharedfiles/filedetails/?id=3543155128 |
| Power Lines (Workshop 3766893705, 11.1.1) | electric distribution | installed Version-1.1 package; power network adapter; exact profile pending | https://steamcommunity.com/sharedfiles/filedetails/?id=3766893705 |
| Map Transformer (Workshop 3798650616, 11.0.0) | map authoring | one-time copied-map height/terrain authoring tool; not a runtime gameplay dependency | https://steamcommunity.com/sharedfiles/filedetails/?id=3798650616 |

Required shared infrastructure to evaluate first: the official pipeline, Moddable Timberborn, Moddable Tool Groups, Mod Settings, Harmony where runtime patches are needed, and the current 1.1 Mod Manager. The local manifest capture in `tools/installed_dependency_manifests_1_1.json` records the exact package IDs, versions, minimum game versions, and declared requirements for the installed foundation set. Confirm every package's declared 1.1 compatibility again after updates. The old community Mod Manager checkout is retained only as historical reference.

The local game exposes a native Mods folder at `C:\Users\Jordan\Documents\Timberborn\Mods`. Keep a clean profile and a development profile so failures are reversible.
