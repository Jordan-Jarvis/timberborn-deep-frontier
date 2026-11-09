using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Timberborn.AssetSystem;
using Timberborn.BlueprintSystem;
using Timberborn.SingletonSystem;
using Timberborn.WaterSystemRendering;
using ModdableFluids.Rendering.Prototype;
using UnityEngine;

namespace ModdableFluids.Runtime.Prototype {
  /// <summary>
  /// The shared water renderer (GPU half). It never modifies the game's own materials (native-safety
  /// audit C2): it makes per-scene copies of the native Opaque/Transparent water materials on the
  /// Moddable Fluids shader variants (tools/moddable_fluids_shader_variants.mjs) and assigns them only
  /// to the scene's water tile renderers. The native mesh assigns its materials when it creates a tile
  /// and when the opacity toggle changes, so every frame each tile that holds a native material gets the
  /// matching copy, and the copies are refreshed from the native materials. Any other material on a tile
  /// fails visibly. Appearance comes from <see cref="FluidAppearanceField"/> at completed ticks, encoded per
  /// channel through the inverse of the native visibility curve into old/new R8 texture arrays with the
  /// native layout and update order. Every native member used is checked before anything is created.
  /// </summary>
  public sealed class FluidWaterRendering : IPostLoadableSingleton, IUpdatableSingleton, IUnloadableSingleton {
    public const string OpaqueVariant = "Shaders/ModdableFluids/FluidWaterURP_Opaque";
    public const string TransparentVariant = "Shaders/ModdableFluids/FluidWaterURP_Transparent";
    public const string Keyword = "_MODDABLE_FLUIDS_APPEARANCE";
    private static readonly string[] Channels = { "Red", "Green", "Blue", "Strength" };
    private static readonly string[] CompiledKeywords = { "_CALCULATE_OUTFLOWS" };
    private const int CurveSteps = 1024;
    private readonly ModdableFluidsSceneOwner _owner;
    private readonly IWaterMesh _waterMesh;
    private readonly IAssetLoader _assets;
    private readonly ISpecService _specs;
    private readonly byte[] _curve = new byte[CurveSteps + 1];
    private Material _nativeOpaque, _nativeTransparent, _opaque, _transparent;
    private IDictionary _tiles;
    private FluidAppearanceField _field;
    private FluidAppearanceResolver _resolver;
    private Texture2DArray[] _oldArrays = new Texture2DArray[4], _newArrays = new Texture2DArray[4];
    private byte[][] _old = new byte[4][], _new = new byte[4][];
    private int _lastTick = -1, _layers;
    public int TintedTexels { get; private set; }
    public int TilesWithFluidMaterial { get; private set; }

    public FluidWaterRendering(ModdableFluidsSceneOwner owner, IWaterMesh waterMesh, IAssetLoader assets, ISpecService specs) {
      _owner = owner; _waterMesh = waterMesh; _assets = assets; _specs = specs;
    }

    public void PostLoad() {
      // WaterMeshSpec is internal in 1.1.2.8: read it through a checked reflection contract.
      const BindingFlags members = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;
      var specType = typeof(IWaterMesh).Assembly.GetType("Timberborn.WaterSystemRendering.WaterMeshSpec")
        ?? throw new InvalidOperationException("Native Timberborn.WaterSystemRendering.WaterMeshSpec is missing (expected Timberborn 1.1.2.8)");
      var getSpec = typeof(ISpecService).GetMethods().SingleOrDefault(m => m.Name == "GetSingleSpec" && m.IsGenericMethodDefinition && m.GetParameters().Length == 0)
        ?? throw new MissingMethodException("ISpecService.GetSingleSpec<T>()");
      object spec = getSpec.MakeGenericMethod(specType).Invoke(_specs, null);
      Material Read(string name) {
        var property = specType.GetProperty(name, members) ?? throw new MissingMemberException(specType.FullName, name);
        object assetRef = property.GetValue(spec);
        var asset = assetRef?.GetType().GetProperty("Asset", members) ?? throw new MissingMemberException(property.PropertyType.FullName, "Asset");
        return asset.GetValue(assetRef) as Material ?? throw new InvalidOperationException("WaterMeshSpec." + name + " holds no Material");
      }
      _nativeOpaque = Read("OpaqueMaterial"); _nativeTransparent = Read("TransparentMaterial");
      var tiles = _waterMesh.GetType().GetField("_createdTiles", BindingFlags.Instance | BindingFlags.NonPublic)
        ?? throw new MissingFieldException(_waterMesh.GetType().FullName, "_createdTiles");
      if (!typeof(IDictionary).IsAssignableFrom(tiles.FieldType) || tiles.FieldType.GetGenericArguments().LastOrDefault() != typeof(MeshRenderer))
        throw new InvalidOperationException("Native WaterMesh._createdTiles is no longer a dictionary of MeshRenderer (expected Timberborn 1.1.2.8)");
      _tiles = (IDictionary)tiles.GetValue(_waterMesh);
      _opaque = Copy(_nativeOpaque, "Shader Graphs/PhysicalWaterURP_Opaque", _assets.Load<Shader>(OpaqueVariant), "ModdableFluids/FluidWaterURP_Opaque");
      _transparent = Copy(_nativeTransparent, "Shader Graphs/PhysicalWaterURP_Transparent", _assets.Load<Shader>(TransparentVariant), "ModdableFluids/FluidWaterURP_Transparent");
      float min = NativeFloat("_MinContaminationThreshold"), max = NativeFloat("_MaxContaminationThreshold"), nonlinearity = NativeFloat("_ContaminationNonlinearity");
      if (!(max > min) || !(min >= 0f) || !(max <= 1f) || !(nonlinearity > 0f))
        throw new InvalidOperationException("Native water contamination curve changed: thresholds " + min + ".." + max + ", nonlinearity " + nonlinearity);
      // Inverse of the native visual weight smoothstep((c - min) / (max - min)) ^ nonlinearity.
      for (int k = 0; k <= CurveSteps; k++) {
        float s = Mathf.Pow(k / (float)CurveSteps, 1f / nonlinearity);
        float t = 0.5f - Mathf.Sin(Mathf.Asin(1f - 2f * s) / 3f);
        _curve[k] = (byte)Mathf.RoundToInt(255f * (min + t * (max - min)));
      }
      _curve[0] = 0;
      _resolver = new FluidAppearanceResolver(_owner.Registry);
      _field = new FluidAppearanceField(_owner.Stride - 2, _owner.Height);
      Shader.DisableKeyword(Keyword);
    }

    private static Material Copy(Material native, string nativeShader, Shader variant, string variantName) {
      if (native == null || native.shader == null || native.shader.name != nativeShader)
        throw new InvalidOperationException("Expected the native water material on " + nativeShader + ", found " + (native?.shader == null ? "none" : native.shader.name));
      if (variant == null || variant.name != variantName) throw new InvalidOperationException("Shader variant " + variantName + " is missing from the Moddable Fluids bundle");
      if (!variant.isSupported) throw new InvalidOperationException("Shader variant " + variantName + " is not supported on this GPU");
      for (int i = 0; i < native.shader.GetPropertyCount(); i++) {
        int index = variant.FindPropertyIndex(native.shader.GetPropertyName(i));
        if (index < 0 || variant.GetPropertyType(index) != native.shader.GetPropertyType(i))
          throw new InvalidOperationException(variantName + " lacks native property " + native.shader.GetPropertyName(i) + "; regenerate it from the installed game's graph");
      }
      foreach (var keyword in native.enabledKeywords)
        if (Array.IndexOf(CompiledKeywords, keyword.name) < 0) throw new InvalidOperationException(native.name + " enables " + keyword.name + ", which " + variantName + " does not compile");
      var copy = new Material(variant) { name = native.name + " (Moddable Fluids, scene copy)" };
      Refresh(copy, native);
      return copy;
    }

    private static void Refresh(Material copy, Material native) {
      copy.CopyPropertiesFromMaterial(native);
      copy.renderQueue = native.renderQueue;
      foreach (var keyword in native.enabledKeywords) copy.EnableKeyword(keyword.name);
      if (copy.renderQueue != native.renderQueue) throw new InvalidOperationException(copy.name + ": render queue " + copy.renderQueue + ", native " + native.renderQueue);
    }

    private float NativeFloat(string name) {
      if (!_nativeOpaque.HasFloat(name) || !_nativeTransparent.HasFloat(name)) throw new InvalidOperationException("Native water materials lost " + name);
      float value = _nativeOpaque.GetFloat(name);
      if (_nativeTransparent.GetFloat(name) != value) throw new InvalidOperationException("Native water materials disagree on " + name);
      return value;
    }

    public void UpdateSingleton() {
      if (_opaque == null) return;
      Refresh(_opaque, _nativeOpaque); Refresh(_transparent, _nativeTransparent);
      int count = 0;
      foreach (MeshRenderer tile in _tiles.Values) {
        if (tile == null) continue;
        var material = tile.sharedMaterial;
        if (material == _nativeOpaque) tile.sharedMaterial = _opaque;
        else if (material == _nativeTransparent) tile.sharedMaterial = _transparent;
        else if (material != _opaque && material != _transparent)
          throw new InvalidOperationException("Water tile " + tile.name + " holds " + (material == null ? "no material" : material.name) + ", not a native or Moddable Fluids water material");
        count++;
      }
      TilesWithFluidMaterial = count;
      var session = _owner.Hooks?.Session;
      if (session == null || session.Phase != "Ready" || session.CompletedTicks == _lastTick) return;
      _lastTick = session.CompletedTicks;
      _field.Update(session, _resolver, _owner.Stride);
      Upload();
    }

    private void Upload() {
      int size = _field.Width * _field.Height;
      if (_field.Layers != _layers) Resize(_field.Layers, size);
      var texels = _field.CopyTexels();
      int tinted = 0;
      for (int channel = 0; channel < 4; channel++) {
        // Native order (UpdateWaterTexturesTask): old takes the previous new.
        Buffer.BlockCopy(_new[channel], 0, _old[channel], 0, _new[channel].Length);
        for (int i = 0; i < _layers * size; i++) {
          byte value = texels[i * 4 + channel];
          _new[channel][i] = _curve[(value * CurveSteps + 127) / 255];
          if (channel == 3 && value != 0) tinted++;
        }
        for (int layer = 0; layer < _layers; layer++) {
          _oldArrays[channel].SetPixelData(_old[channel], 0, layer, layer * size);
          _newArrays[channel].SetPixelData(_new[channel], 0, layer, layer * size);
        }
        _oldArrays[channel].Apply(false); _newArrays[channel].Apply(false);
      }
      TintedTexels = tinted;
      if (tinted > 0) Shader.EnableKeyword(Keyword); else Shader.DisableKeyword(Keyword);
    }

    private void Resize(int layers, int size) {
      for (int channel = 0; channel < 4; channel++) {
        var oldBytes = new byte[layers * size]; var newBytes = new byte[layers * size];
        if (_old[channel] != null) { Buffer.BlockCopy(_old[channel], 0, oldBytes, 0, _old[channel].Length); Buffer.BlockCopy(_new[channel], 0, newBytes, 0, _new[channel].Length); }
        _old[channel] = oldBytes; _new[channel] = newBytes;
        if (_oldArrays[channel] != null) { UnityEngine.Object.Destroy(_oldArrays[channel]); UnityEngine.Object.Destroy(_newArrays[channel]); }
        _oldArrays[channel] = NewArray("_MFOldTint" + Channels[channel], layers); _newArrays[channel] = NewArray("_MFNewTint" + Channels[channel], layers);
        Shader.SetGlobalTexture("_MFOldTint" + Channels[channel], _oldArrays[channel]);
        Shader.SetGlobalTexture("_MFNewTint" + Channels[channel], _newArrays[channel]);
      }
      _layers = layers;
    }

    private Texture2DArray NewArray(string name, int layers) =>
      new Texture2DArray(_field.Width, _field.Height, layers, TextureFormat.R8, false) { name = name, filterMode = FilterMode.Point, wrapMode = TextureWrapMode.Clamp };

    public void Unload() {
      Shader.DisableKeyword(Keyword);
      if (_tiles != null)
        foreach (MeshRenderer tile in _tiles.Values) {
          if (tile == null) continue;
          if (tile.sharedMaterial == _opaque) tile.sharedMaterial = _nativeOpaque;
          else if (tile.sharedMaterial == _transparent) tile.sharedMaterial = _nativeTransparent;
        }
      foreach (var texture in _oldArrays.Concat(_newArrays)) if (texture != null) UnityEngine.Object.Destroy(texture);
      if (_opaque != null) UnityEngine.Object.Destroy(_opaque);
      if (_transparent != null) UnityEngine.Object.Destroy(_transparent);
      _opaque = _transparent = null;
    }
  }
}
