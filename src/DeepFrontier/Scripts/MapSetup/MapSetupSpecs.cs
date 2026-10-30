#if !UNITY_EDITOR
using System.Collections.Immutable;
using System.Linq;
using Timberborn.BlueprintSystem;

namespace DeepFrontier.Scripts.MapSetup {
  // Built-in new-game setup (docs/maps.md "Built-in maps: new-game setup"). Exactly one blueprint,
  // Configurations/DeepFrontierMapSetup, carries it; tools/map_setup_content.mjs generates it from
  // tools/map_variants/*.json (every default variant whose source is builtin:<Name>) and
  // tools/map_setup.json, and tools/prepare_deep_frontier_map.py builtin validates every entry
  // against the unmodified built-in map. Every value is required; nothing is defaulted.
  internal record BuiltinMapSetupSpec : ComponentSpec {
    // A map whose area (width x height) is below this is small (tools/map_setup.json smallMap).
    [Serialize] public int SmallMapMaxArea { get; init; }
    // Cells the full-loop sites claim with their margins on the largest reference map.
    [Serialize] public int ReferenceSiteArea { get; init; }
    // The game's developer test maps (IsDev): no setup, reported as such.
    [Serialize] public ImmutableArray<string> DevMaps { get; init; }
    [Serialize] public ImmutableArray<BuiltinMapSpec> Maps { get; init; }

    public BuiltinMapSpec Find(string mapName) => Maps.SingleOrDefault(m => m.MapName == mapName);
  }

  internal record BuiltinMapSpec {
    // The built-in map's asset name (MapFileReference.Name of a resource map; MapNameService.Name).
    [Serialize] public string MapName { get; init; }
    // Source variant id (tools/map_variants/<id>.json), for the log.
    [Serialize] public string VariantId { get; init; }
    [Serialize] public int Width { get; init; }
    [Serialize] public int Height { get; init; }
    // Total build height (layers) of a new game on this map; the terrain keeps its stored layers.
    [Serialize] public int TotalHeight { get; init; }
    [Serialize] public bool Small { get; init; }
    // One localized line per loop-coverage item the map cannot provide (the variant's "unmet").
    [Serialize] public ImmutableArray<string> UnmetLocKeys { get; init; }
    [Serialize] public ImmutableArray<MapPlacementSpec> Placements { get; init; }
  }

  internal record MapPlacementSpec {
    [Serialize] public string Template { get; init; }
    [Serialize] public string Label { get; init; }
    [Serialize] public int X { get; init; }
    [Serialize] public int Y { get; init; }
    [Serialize] public int Z { get; init; }
    // Timberborn.Coordinates.Orientation name (Cw0, Cw90, Cw180, Cw270).
    [Serialize] public string Orientation { get; init; }
    // Stockpile map objects (DeepOreSource) only: the fixed good and its amount; "" and 0 otherwise.
    [Serialize] public string Good { get; init; }
    [Serialize] public int Amount { get; init; }
  }
}
#endif
