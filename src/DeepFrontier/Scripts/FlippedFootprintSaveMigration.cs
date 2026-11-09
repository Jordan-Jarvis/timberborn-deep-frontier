#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Bindito.Core;
using HarmonyLib;
using Timberborn.BlockSystem;
using Timberborn.Coordinates;
using Timberborn.GameSaveRepositorySystem;
using Timberborn.GameSceneLoading;
using Timberborn.SaveMetadataSystem;
using Timberborn.SceneLoading;
using Timberborn.SingletonSystem;
using Timberborn.TemplateSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Flipped buildings in saves made before a footprint change.
  //
  // Every smaller Deep Frontier footprint kept its origin: the unflipped
  // building keeps local (0, 0) where it was and its new blocks lie on ground
  // the old building covered. A flipped building mirrors its local x across
  // its width, so with the same origin it mirrors across the new, narrower
  // width: its blocks land on the old building's far side, over the free
  // strips and doorsteps the player built paths on, and its door, pipe ports
  // and (for the Reinforced Hydro Turbine) its water conduit move sideways by
  // the difference in width. On build 239 a 0.6.0 save's flipped Fishery
  // Works (11 -> 6 wide) loaded on a path the old building's free strip held,
  // and the game deleted it.
  //
  // A flipped placement from a save whose Deep Frontier version had another
  // width for that building is moved by (old width - new width) along its
  // local x, rotated by its orientation, through BlockObject's own private
  // UpdateValues(Placement) (decompiled 1.1.2.8; the method Load and
  // Reposition call), before it is validated and added. The flipped building
  // then covers exactly the ground its unflipped self would: the mirror image
  // of the old building's local x 0 .. new width - 1, so the door, the ports
  // and the conduit stay where they were; a building whose own block rules
  // reject that ground keeps its saved origin if it is valid there. The save's Deep Frontier version is
  // the one the native save metadata records (SaveMetadata.Mods), read
  // through the native GameSaveDeserializer. The widths below are the
  // BlockObjectSpec size x of each published version (Workshop uploads
  // 0.5.0 .. 0.8.1; git: the "Version x" commits, 0.5.0 = ad71e80). A save
  // made with a later version has the current footprints. The Deep Mine and
  // the quarries are not listed: MineFootprintSaveMigration.cs moves them
  // onto their deposit, flipped or not.
  [HarmonyPatch(typeof(BlockObject), nameof(BlockObject.AddToServiceAfterLoad))]
  internal static class FlippedFootprintSaveMigration {
    internal static readonly Version[] Versions = {
      new(0, 5, 0), new(0, 6, 0), new(0, 7, 0), new(0, 7, 1), new(0, 8, 0), new(0, 8, 1) };
    // Size x in each version of Versions, in order.
    internal static readonly Dictionary<string, int[]> Widths = new(StringComparer.Ordinal) {
      { "ArchiveExcavation.IronTeeth", new[] { 10, 10, 7, 7, 7, 7 } },
      { "Bathhouse.IronTeeth", new[] { 9, 9, 7, 7, 7, 7 } },
      { "CementKiln.IronTeeth", new[] { 7, 7, 5, 5, 5, 5 } },
      { "ChemicalWorks.IronTeeth", new[] { 10, 10, 5, 5, 5, 5 } },
      { "CoalPowerPlant.IronTeeth", new[] { 5, 5, 4, 4, 4, 4 } },
      { "ConcreteMixer.IronTeeth", new[] { 7, 7, 4, 4, 4, 4 } },
      { "CryogenicLiquefactionPlant.IronTeeth", new[] { 12, 12, 8, 8, 8, 8 } },
      { "CryogenicTankFarm.IronTeeth", new[] { 11, 11, 7, 7, 7, 7 } },
      { "DeepDrill.IronTeeth", new[] { 11, 11, 7, 7, 7, 7 } },
      { "DeepProcessor.IronTeeth", new[] { 11, 11, 7, 7, 7, 7 } },
      { "ElectrolysisPlant.IronTeeth", new[] { 12, 12, 8, 8, 8, 8 } },
      { "FertilizerWorks.IronTeeth", new[] { 9, 9, 7, 7, 7, 7 } },
      { "FishHatchery.IronTeeth", new[] { 7, 7, 7, 7, 7, 7 } },
      { "FisheryWorks.IronTeeth", new[] { 11, 11, 11, 11, 11, 11 } },
      { "FoodPackagingWorks.IronTeeth", new[] { 10, 10, 7, 7, 7, 7 } },
      { "Greenhouse.IronTeeth", new[] { 9, 9, 9, 9, 9, 9 } },
      { "GroceryStore.IronTeeth", new[] { 9, 9, 9, 9, 9, 9 } },
      { "Hospital.IronTeeth", new[] { 12, 12, 4, 4, 4, 4 } },
      { "LaunchPad.IronTeeth", new[] { 12, 12, 10, 10, 10, 10 } },
      { "LimestonePit.IronTeeth", new[] { 5, 5, 5, 5, 5, 5 } },
      { "MaterialsLaboratory.IronTeeth", new[] { 10, 10, 10, 10, 10, 10 } },
      { "MissionControl.IronTeeth", new[] { 12, 12, 8, 8, 8, 8 } },
      { "NuclearReactor.IronTeeth", new[] { 20, 20, 14, 14, 14, 14 } },
      { "ObservationDeck.IronTeeth", new[] { 6, 6, 6, 6, 6, 6 } },
      { "OilPowerPlant.IronTeeth", new[] { 6, 6, 5, 5, 5, 5 } },
      { "PrecisionMachineWorks.IronTeeth", new[] { 11, 11, 9, 9, 9, 9 } },
      { "PublicHealthLab.IronTeeth", new[] { 8, 8, 6, 6, 6, 6 } },
      { "RadioactiveWasteExport.IronTeeth", new[] { 6, 6, 6, 6, 6, 6 } },
      { "RadioactiveWasteRefinery.IronTeeth", new[] { 12, 12, 9, 9, 9, 9 } },
      { "RadioactiveWasteVault.IronTeeth", new[] { 9, 9, 8, 8, 8, 8 } },
      { "ReinforcedHydroTurbine.IronTeeth", new[] { 8, 8, 8, 8, 8, 8 } },
      { "Restaurant.IronTeeth", new[] { 9, 9, 9, 9, 9, 9 } },
      { "RocketAssemblyHangar.IronTeeth", new[] { 8, 8, 7, 7, 7, 7 } },
      { "SandstonePit.IronTeeth", new[] { 5, 5, 5, 5, 5, 5 } },
      { "SteelMill.IronTeeth", new[] { 12, 12, 8, 8, 8, 8 } },
      { "StoneCrusher.IronTeeth", new[] { 4, 4, 4, 4, 4, 4 } },
      { "TechnicalSchool.IronTeeth", new[] { 11, 11, 8, 8, 8, 8 } },
      { "TownPlaza.IronTeeth", new[] { 9, 9, 7, 7, 7, 7 } },
      { "UraniumProcessingPlant.IronTeeth", new[] { 12, 12, 8, 8, 8, 8 } },
      { "WaterTreatmentPlant.IronTeeth", new[] { 12, 12, 9, 9, 9, 9 } },
    };
    private static MethodInfo _updateValues;

    // Called once per process from DeepFrontierModStarter.
    internal static void Apply() => NativePatches.Install("DeepFrontier.FlippedFootprintSaveMigration",
      () => _updateValues = FootprintSaveMigrationNative.Verify("Flipped footprint save migration"), typeof(FlippedFootprintSaveMigration));

    private static void Prefix(BlockObject __instance) {
      if (__instance.AddedToService || __instance.IsPreview) return;
      var original = __instance.Placement;
      if (!original.FlipMode.IsFlipped) return;
      var template = __instance.GetComponent<TemplateSpec>()?.TemplateName;
      if (template == null || !Widths.TryGetValue(template, out var widths)) return;
      var save = SavedFootprintVersion.Current
        ?? throw new InvalidOperationException($"Flipped {template} loaded outside a game scene; its saved Deep Frontier version is unknown");
      int index = save.WidthIndex();
      if (index < 0) return;
      int oldWidth = widths[index], newWidth = __instance.Blocks.Size.x;
      if (oldWidth == newWidth) return;
      var shift = original.Orientation.Transform(new Vector2Int(oldWidth - newWidth, 0));
      var moved = new Placement(original.Coordinates + new Vector3Int(shift.x, shift.y, 0), original.Orientation, original.FlipMode);
      _updateValues.Invoke(__instance, new object[] { moved });
      if (__instance.IsValid()) {
        Debug.Log($"[DeepFrontier] Flipped {template} from a Deep Frontier {save.Version} save at {original.Coordinates} ({original.Orientation}) moved to {moved.Coordinates}: width {oldWidth} -> {newWidth}, the same ground as before.");
        return;
      }
      // The new blueprint's own rules can reject the mirrored ground where its layout is not a mirror of
      // the old one (Fishery Works: the water wing changed sides, so a "Ground" cell lands where the old
      // building overhung a dip). It then stays at its saved origin when that is valid; otherwise the
      // native loader deletes it with its loading issue, as before.
      _updateValues.Invoke(__instance, new object[] { original });
      Debug.LogWarning($"[DeepFrontier] Flipped {template} from a Deep Frontier {save.Version} save at {original.Coordinates} ({original.Orientation}): its blocks are not valid at {moved.Coordinates} (width {oldWidth} -> {newWidth}); it keeps its saved origin{(__instance.IsValid() ? "" : ", where it is not valid either: the game will remove it")}.");
    }
  }

  // The native members both footprint save migrations rely on (Timberborn
  // 1.1.2.8): their prefixes run before native AddToServiceAfterLoad, which
  // validates the (possibly moved) placement with IsValid and deletes the
  // object with a loading issue when it fails; the move goes through the
  // private UpdateValues(Placement) that Load and Reposition call. No native
  // save-migration hook exists for block object placement.
  internal static class FootprintSaveMigrationNative {
    internal static MethodInfo Verify(string feature) {
      var type = typeof(BlockObject);
      var add = NativeMember.Method(feature, type, nameof(BlockObject.AddToServiceAfterLoad), typeof(void));
      var isValid = NativeMember.Method(feature, type, nameof(BlockObject.IsValid), typeof(bool));
      if (!NativeIl.Calls(add, isValid)) throw NativePatches.Changed(feature, "BlockObject.AddToServiceAfterLoad validates with IsValid()");
      var update = NativeMember.Method(feature, type, "UpdateValues", typeof(void), typeof(Placement));
      if (update.IsPublic) throw NativePatches.Changed(feature, "private BlockObject.UpdateValues(Placement)");
      return update;
    }
  }

  // The Deep Frontier version recorded in the loaded save's native metadata.
  [Context("Game")]
  public sealed class SavedFootprintVersionConfigurator : Configurator {
    protected override void Configure() => Bind<SavedFootprintVersion>().AsSingleton();
  }

  // The Game scene's instance, for the load-time prefix above: set when the
  // scene's container constructs it (before any singleton or entity loads)
  // and cleared on unload, so a later scene never reads a finished game's save.
  internal sealed class SavedFootprintVersion : IUnloadableSingleton {
    internal const string ModId = "DeepFrontier";
    internal static SavedFootprintVersion Current { get; private set; }
    private readonly ISceneLoader _sceneLoader;
    private readonly GameSaveDeserializer _deserializer;
    private readonly SaveMetadataSerializer _metadata;
    private bool _read;
    private Version _version;

    public SavedFootprintVersion(ISceneLoader sceneLoader, GameSaveDeserializer deserializer, SaveMetadataSerializer metadata) {
      _sceneLoader = sceneLoader; _deserializer = deserializer; _metadata = metadata;
      if (Current != null) throw new InvalidOperationException("A saved footprint version is already active; the previous Game scene was not unloaded");
      Current = this;
    }

    public void Unload() {
      if (Current == this) Current = null;
    }

    // Null for a new game or a save without Deep Frontier.
    internal Version Version { get { Read(); return _version; } }

    // Index into FlippedFootprintSaveMigration.Versions of the footprints this save holds;
    // -1 when it holds the current ones (a new game, or a save made after the last listed version).
    internal int WidthIndex() {
      var version = Version;
      var versions = FlippedFootprintSaveMigration.Versions;
      if (version == null) throw new InvalidOperationException("A flipped Deep Frontier building in a save whose metadata lists no Deep Frontier version");
      var plain = new Version(version.Major, version.Minor, Math.Max(version.Build, 0));
      if (plain > versions[versions.Length - 1]) return -1;
      if (plain < versions[0]) throw new InvalidOperationException($"Save made with Deep Frontier {version}, before the first published version {versions[0]}: its footprints are unknown");
      return Array.FindLastIndex(versions, v => v <= plain);
    }

    private void Read() {
      if (_read) return;
      _read = true;
      var parameters = _sceneLoader.GetSceneParameters<GameSceneParameters>();
      if (parameters.NewGame) return;
      var mods = _deserializer.ReadFromSaveFileUnsafe(parameters.SaveReference, _metadata).Mods;
      var entry = mods.Where(m => m.Id == ModId).ToList();
      if (entry.Count > 1) throw new InvalidOperationException($"Save metadata lists {ModId} {entry.Count} times");
      if (entry.Count == 1) _version = Version.Parse(entry[0].Version);
    }
  }
}
#endif
