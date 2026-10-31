#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using Bindito.Core;
using Timberborn.AssetSystem;
using Timberborn.BlueprintSystem;
using Timberborn.SerializationSystem;
using UnityEngine;

namespace DeepFrontier.PowerLineIntegration {
  // Power Lines cable attachment points on Deep Frontier buildings, present
  // only while the Power Lines mod is enabled.
  //
  // This is the optional assembly DeepFrontier.PowerLines. The build packages
  // it as Scripts/DeepFrontier.PowerLines.dll.PowerLines.optional
  // (tools/unity/DeepFrontierBatchBuild.cs), so only Moddable Timberborn's
  // OptionalModsLoader loads it, and only when the mod with Id PowerLines is
  // enabled. The main DeepFrontier assembly holds no Power Lines reference.
  //
  // PowerLineSpec cannot stay in the building blueprints: the game's
  // SpecService deserializes templates with BlueprintDeserializer.DeserializeUnsafe,
  // which throws "No type found for key PowerLineSpec" when Power Lines is
  // absent (Timberborn.BlueprintSystem 1.1.2.8). The spec is instead authored in
  // Data/Integrations/PowerLines/<Template>.json ({Blueprint, Modifier}, written
  // by tools/create_construction_material_content.mjs) and added here through
  // the game's own IBlueprintModifierProvider, the interface the faction
  // blueprint modifiers use: SpecService appends each provider's modifier JSON
  // to the blueprint's files before deserializing it. Power Lines reads the
  // result with GetComponent<PowerLineSpec>() on the entity.
  [Context("MainMenu")]
  [Context("Game")]
  [Context("MapEditor")]
  public sealed class PowerLineIntegrationConfigurator : Configurator {
    protected override void Configure() {
      MultiBind<IBlueprintModifierProvider>().To<PowerLineConnectionPoints>().AsSingleton();
    }
  }

  internal sealed class PowerLineConnectionPoints : IBlueprintModifierProvider {
    // Data/Integrations/PowerLines in the source; the package root holds Data's contents.
    internal const string Folder = "Integrations/PowerLines";
    private readonly IAssetLoader _assetLoader;
    private readonly SerializedObjectReaderWriter _json;
    private Dictionary<string, string> _modifiers;

    public PowerLineConnectionPoints(IAssetLoader assetLoader, SerializedObjectReaderWriter json) {
      _assetLoader = assetLoader;
      _json = json;
    }

    public string ModifierName => "Deep Frontier Power Lines connection points";

    public IEnumerable<string> GetModifiers(string blueprintPath) {
      // Read on first use: SpecService only deserializes after every asset provider has loaded.
      _modifiers ??= Load();
      if (_modifiers.TryGetValue(blueprintPath, out var modifier)) yield return modifier;
    }

    private Dictionary<string, string> Load() {
      var modifiers = new Dictionary<string, string>();
      foreach (var loaded in _assetLoader.LoadAll<TextAsset>(Folder)) {
        var entry = _json.ReadJson(loaded.Asset.text);
        // Load throws for a missing blueprint; its Path is the normalized key SpecService passes in.
        var blueprint = _assetLoader.Load<BlueprintAsset>(entry.Get<string>("Blueprint"));
        if (!modifiers.TryAdd(blueprint.Path, _json.WriteJson(entry.Get<SerializedObject>("Modifier"))))
          throw new InvalidOperationException($"Two Power Lines connection files target {blueprint.Path} ({Folder}/{loaded.Asset.name})");
      }
      if (modifiers.Count == 0)
        throw new InvalidOperationException($"No Power Lines connection points under {Folder}: the Deep Frontier package is incomplete");
      Debug.Log($"[DeepFrontier] Power Lines connection points added to {modifiers.Count} buildings ({string.Join(", ", modifiers.Keys)}).");
      return modifiers;
    }
  }
}
#endif
