#if !UNITY_EDITOR
using System;
using Bindito.Core;
using HarmonyLib;
using Timberborn.BlueprintSystem;
using Timberborn.GameScene;
using Timberborn.GameSceneLoading;
using Timberborn.MapStateSystem;
using Timberborn.Persistence;
using Timberborn.SceneLoading;
using Timberborn.SingletonSystem;
using Timberborn.WorldPersistence;
using Timberborn.WorldSerialization;
using UnityEngine;

namespace DeepFrontier.Scripts.MapSetup {
  // Total build height of a new game on a built-in map (docs/maps.md "Built-in maps: new-game setup",
  // docs/map-height.md). Built-in maps store 23 terrain layers and no MapHeight key, so the global
  // MapSizeSpec applies (23 / 33). Deep Frontier never changes that spec. For a NEW game on a
  // built-in map that has a setup entry, it writes the key Map Transformer reads,
  // MapHeight {X: stored terrain layers, Y: the entry's TotalHeight}, into the map's MapSize
  // singleton before MapSize.Load runs:
  //   1. GameSceneSerializedWorldSupplier.Load (Timberborn.GameScene, 1.1.2.8) deserializes the map
  //      of GameSceneParameters.NewGameConfiguration; the postfix below keeps that world and the map
  //      name for step 2. Loaded saves are not touched.
  //   2. MapSize.Load (Timberborn.MapStateSystem) reads the MapSize singleton from that world; it is
  //      loaded after the supplier because it depends on it (ISingletonLoader -> WorldSingletonLoader
  //      -> ISerializedWorldSupplier). The prefix writes MapHeight with the native ObjectSaver, the
  //      writer Map Transformer's own MapSize.Save postfix uses; Map Transformer 11.0.0's MapSize.Load
  //      postfix then applies it (MaxGameTerrainHeight = X - 1 unchanged, MaxHeightAboveTerrain =
  //      Y - X), and its Save postfix keeps the key in every save, so reloads keep the height.
  // TerrainMap.Load still reads the stored 23 layers (TerrainSize.z is unchanged). BuiltinMapSetup
  // checks the resulting MapSize and reports any difference.
  internal static class BuiltinMapHeight {
    // The MapSize singleton (MapSize.MapSizeKey) and Map Transformer's key (MapSizePatches.MapSizeHeightKey).
    internal const string MapSizeSingleton = "MapSize";
    internal static readonly PropertyKey<Vector2Int> MapHeightKey = new("MapHeight");

    internal sealed class PendingNewGame {
      public string MapName;
      public SerializedWorld World;
    }

    // Called once per process from DeepFrontierModStarter.
    internal static void Apply() =>
      NativePatches.Install("DeepFrontier.BuiltinMapHeight", Verify, typeof(CaptureNewGameWorld), typeof(WriteMapHeight));

    // The two patches hand the new game's world from one native Load to the
    // next. Native order puts the supplier's Load first: MapSize's constructor
    // takes ISingletonLoader, bound to WorldSingletonLoader, whose constructor
    // takes ISerializedWorldSupplier, so the supplier is constructed, and
    // loaded, before MapSize (SingletonLifecycleService loads in construction
    // order). Checked here with every field the patches read.
    private static void Verify() {
      const string feature = "Built-in map height";
      var supplier = typeof(GameSceneSerializedWorldSupplier);
      NativeMember.Method(feature, supplier, nameof(GameSceneSerializedWorldSupplier.Load), typeof(void));
      NativeMember.Field(feature, supplier, "_sceneLoader", typeof(ISceneLoader));
      NativeMember.Field(feature, supplier, "_serializedWorld", typeof(SerializedWorld));
      NativeMember.Method(feature, typeof(MapSize), nameof(MapSize.Load), typeof(void));
      NativeMember.Field(feature, typeof(MapSize), "_specService", typeof(ISpecService));
      if (typeof(MapSize).GetConstructor(new[] { typeof(ISingletonLoader), typeof(ISpecService) }) == null)
        throw NativePatches.Changed(feature, "MapSize(ISingletonLoader, ISpecService)");
      var worldLoader = NativeMember.Type(feature, typeof(ISingletonSaver), "Timberborn.WorldPersistence.WorldSingletonLoader");
      if (worldLoader.GetConstructor(new[] { typeof(ISerializedWorldSupplier) }) == null || !typeof(ISingletonLoader).IsAssignableFrom(worldLoader))
        throw NativePatches.Changed(feature, "WorldSingletonLoader(ISerializedWorldSupplier) : ISingletonLoader");
      if (!typeof(ISerializedWorldSupplier).IsAssignableFrom(supplier)) throw NativePatches.Changed(feature, "GameSceneSerializedWorldSupplier : ISerializedWorldSupplier");
    }

    [HarmonyPatch(typeof(GameSceneSerializedWorldSupplier), nameof(GameSceneSerializedWorldSupplier.Load))]
    private static class CaptureNewGameWorld {
      private static void Postfix(ISceneLoader ____sceneLoader, SerializedWorld ____serializedWorld) {
        var capture = BuiltinMapHeightCapture.Current
          ?? throw new InvalidOperationException("[DeepFrontier MapSetup] the Game scene has no BuiltinMapHeightCapture");
        var parameters = ____sceneLoader.GetSceneParameters<GameSceneParameters>();
        capture.Pending = parameters.NewGame && parameters.NewGameConfiguration.MapFileReference.Resource
          ? new PendingNewGame { MapName = parameters.NewGameConfiguration.MapFileReference.Name, World = ____serializedWorld }
          : null;
      }
    }

    [HarmonyPatch(typeof(MapSize), nameof(MapSize.Load))]
    private static class WriteMapHeight {
      private static void Prefix(ISpecService ____specService) {
        // MapSize also loads in the main menu and the map editor, which have no capture.
        var capture = BuiltinMapHeightCapture.Current;
        if (capture == null) return;
        var pending = capture.Pending;
        capture.Pending = null;
        if (pending == null) return;
        // A built-in map without an entry gets no height; BuiltinMapSetup reports it.
        var map = ____specService.GetSingleSpec<BuiltinMapSetupSpec>().Find(pending.MapName);
        if (map == null) return;
        var mapSize = pending.World.GetSingleton(MapSizeSingleton);
        if (new ObjectLoader(mapSize).Has(MapHeightKey))
          throw new InvalidOperationException("[DeepFrontier MapSetup] built-in map " + pending.MapName + " already carries MapHeight; the setup expects a vanilla map");
        var spec = ____specService.GetSingleSpec<MapSizeSpec>();
        int terrainLayers = spec.MaxGameTerrainHeight + 1;
        if (map.TotalHeight < terrainLayers + spec.MaxHeightAboveTerrain)
          throw new InvalidOperationException("[DeepFrontier MapSetup] " + pending.MapName + " TotalHeight " + map.TotalHeight + " is below the vanilla total height");
        new ObjectSaver(mapSize).Set(MapHeightKey, new Vector2Int(terrainLayers, map.TotalHeight));
        Debug.Log("[DeepFrontier MapSetup] new game on built-in " + pending.MapName + ": MapHeight {" + terrainLayers + ", " + map.TotalHeight + "} written for Map Transformer");
      }
    }
  }

  // The new game's world, handed from the supplier's Load to MapSize.Load
  // within one Game scene. Owned by that scene: constructed with its
  // container (before any Load) and cleared on unload, so a capture from a
  // game whose load failed can never reach another scene's MapSize.Load.
  internal sealed class BuiltinMapHeightCapture : IUnloadableSingleton {
    internal static BuiltinMapHeightCapture Current { get; private set; }
    internal BuiltinMapHeight.PendingNewGame Pending;

    public BuiltinMapHeightCapture() {
      if (Current != null) throw new InvalidOperationException("[DeepFrontier MapSetup] a map height capture is already active; the previous Game scene was not unloaded");
      Current = this;
    }

    public void Unload() {
      if (Current == this) Current = null;
    }
  }

  [Context("Game")]
  public sealed class BuiltinMapHeightConfigurator : Configurator {
    protected override void Configure() => Bind<BuiltinMapHeightCapture>().AsSingleton();
  }
}
#endif
