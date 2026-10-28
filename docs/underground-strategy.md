# Underground strategy for Timberborn 1.1

## Decision

The first implementation should simulate an underground industrial frontier with normal Timberborn buildings, authored lower terrain, shafts, and transport networks. It should not attempt to raise the height of an existing save or carve a fully dynamic cave network at runtime. Use [Map Transformer](https://steamcommunity.com/sharedfiles/filedetails/?id=3798650616) once while authoring a copied map; it is marked for Update 1.1 and can resize height or add bottom dirt, but the transformed session may crash and custom terrain height remains a map/mod compatibility requirement.

The official modding tools support building blueprints, assets, JSON data, DLL code, and runtime configuration. The current ModdableTimberborn foundation exposes spec/template modifiers, building settings, entity tracking, areas, game stats, extra hauler targets, and mechanical-system changes. Its documented game stats expose map dimensions, including terrain and total height, as values to read; they do not provide a supported terrain-expansion subsystem. That makes runtime map growth a high-risk engine modification rather than a normal building mod. See the [official tools](https://github.com/mechanistry/timberborn-modding), [ModdableTimberborn API overview](https://github.com/datvm/TimberbornMods/blob/master/ModdableTimberborn/Docs/README.MD), and [map dimension stats](https://github.com/datvm/TimberbornMods/blob/master/ModdableTimberborn/Docs/GameStats.MD).

## What the player sees

- New maps can be authored with tall stepped terrain, deep basins, shafts, and sealed lower districts from the start.
- Existing compatible maps use naturally low valleys, cliff faces, water-cut basins, and stacked solid structures as the first frontier sites.
- A Survey Station reveals dormant lower sectors that already exist in the map. The unlock changes access, recipes, and objectives; it does not create new terrain inside a save.
- Deep Drill, hoist, belt lift, pipe riser, and power-line buildings connect the lower sector to the surface.
- Underground settlements are placed in authored cavities or lower terraces and behave like ordinary buildings with specialized visuals and requirements.

This still feels like expansion because the player gains access in stages and must build the vertical logistics chain. It avoids the fragile assumption that a save can be resized safely after the game has already serialized its terrain, navigation, fluids, and building positions.

The first authoring target is a modest extra Z budget, roughly eight added terrain layers and a total height near forty. Resize the copied map, reload the generated save, save it again, then place and test lower-sector objects. Do not make Map Transformer a gameplay action in the first release.

## Optional gas and fumes branch

Gas and scrubbers are not part of the first factory progression. Keep them as an optional late hazard module after deep extraction, surface automation, and transport adapters are stable.

Use a two-tier model:

1. **Network fluid:** define methane, sulfur gas, toxic fumes, and radon as liquid-engine goods for pipes, tanks, scrubbers, and sealed machine buffers. The workbook labels these as `Fluid (gas proxy)` so recipes can use the existing liquid logistics contract. New goods and recipes are a normal JSON content-mod task; the terrain field is the unsupported part. See the [community JSON specification reference](https://github.com/KnatteAnka/Timberborn-Modding_KA_U6/blob/main/README.md).
2. **Local pocket:** represent accumulation in a low area with a Fume Basin, Gas Pocket, or sealed chamber inventory attached to an authored zone. A machine emits a quantity into the nearest compatible pocket; a gas detector reads the pocket level and raises a warning or triggers a shutoff. A scrubber, vent, flare, or pipe outlet removes the pocket contents.

If this optional branch is enabled, it gives the player the desired behavior—fumes collect in holes and low areas, then must be cleared—without requiring buoyancy, diffusion, or a new world-fluid solver. The pocket can be displayed as a low fog or colored overlay and can affect nearby beavers through an area effect. Its prototype should use a small number of explicit pockets rather than scanning every terrain cell.

The fluid proxy must be tested against Timber Pipes, tanks, the existing [Pump to Tank mod](https://steamcommunity.com/workshop/filedetails/?id=3681283725), and fluid dumps before it becomes a hard dependency. Deep Frontier should detect and use Pump to Tank's tank-to-tank behavior rather than reimplement it. If the vanilla fluid system rejects custom gas goods in world terrain, keep them in pocket and tank inventories while retaining the same pipe ports and recipes. That preserves the logistics gameplay without pretending the engine supports real gas physics.

## Power and machine contract

Every building and recipe now carries three explicit fields:

- **Power demand (hp):** mechanical power consumed while operating.
- **Power output (hp):** maximum mechanical power supplied to the network.
- **Power role:** Consumer, Generator, Passive / transport, or Review if both demand and output are nonzero.

The same machine load can appear on both a building row and its recipe row. Those are two views of one load, not two loads to add together. Colony power totals should use the building instance's demand once; the recipe field is there to make line balancing readable.

Standard machines should have one nonzero side at most. A generator such as Northforge Solar Panel has output and zero demand. A drill, scrubber, lift, or factory has demand and zero output. A flywheel is a storage consumer/producer only if the dependency's runtime behavior explicitly exposes both sides; it should be marked Review until its package profile is confirmed.

## Implementation phases

### Phase 1: safe vertical slice

- Authored test map with one lower basin and one shaft.
- Deep Drill produces Deep Ore and sends it through a vertical material route.
- A surface processor consumes the extracted ore.
- Pipe, conveyor, and power adapters connect the lower sector to the surface.
- Save/reload preserves source, drill, transport, and processor state.

### Phase 2: industrial frontier

- Multiple authored sectors with different resource profiles.
- Oil and contaminated wastewater chains; gas is optional.
- Underground housing, hospital, grocery, and recreation supplied by the same surface logistics systems.
- Optional low-area pocket rules, isolation gates, vent stacks, and emergency purge.

### Phase 3: optional engine research

Only after the normal building version is stable should we investigate runtime terrain edits, dynamic map-sector loading, or a custom gas field. These would require decompilation, save compatibility work, pathing and fluid tests, and likely patches to private game systems. They are an experimental branch, not a prerequisite for the mod's main progression.

## Map height recommendation

Do not make every existing world taller. Ship a purpose-built Deep Frontier map family derived from a copied vanilla map with more vertical room, and make the mod work on ordinary maps through low valleys and surface-first buildings. A taller map helps authored sectors, but it does not solve dynamic excavation by itself. The robust design is pre-authored space plus staged access, not runtime resizing.
