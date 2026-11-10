using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Runtime.InteropServices;
using Timberborn.AssetSystem;
using Timberborn.BlueprintSystem;
using Timberborn.SingletonSystem;
using Timberborn.TerrainSystem;
using Timberborn.TerrainSystemRendering;
using Timberborn.TickSystem;
using Timberborn.TimbermeshMaterials;
using ModdableFluids.Rendering.Prototype;
using UnityEngine;

namespace ModdableFluids.Runtime.Prototype {
  /// <summary>
  /// The shared terrain overlay (GPU half; capability <c>ModdableFluids.Rendering.TerrainOverlays</c>). It never modifies
  /// the game's own materials (native-safety audit C2): it makes per-scene copies of the native terrain materials (every
  /// <c>MaterialCollection.Common</c> material on <c>Shader Graphs/TerrainURP</c>) on the Moddable Fluids variant
  /// <c>ModdableFluids/FluidTerrainURP</c> (tools/moddable_fluids_shader_variants.mjs) and assigns them only to the
  /// scene's terrain tile renderers (native <c>TerrainMeshManager._tiles</c>). The native mesh assigns its materials when
  /// a tile's material count changes, so every frame each active tile slot that holds a native terrain material gets
  /// that material's copy, and the copies are refreshed from the native materials. Any other material on an active tile
  /// fails visibly. The overlays' levels and colours (<see cref="FluidTerrainOverlayField"/>) are published once per
  /// frame in which ticks ran (before the first tick, at once and settled), and only changed rows are uploaded, into an
  /// RG16 level array laid out like the native <c>TerrainMaterialMap</c> soil-contamination map and an RGBAHalf colour
  /// array. Every native member used is checked before anything is created (<see cref="CheckContract"/> at scene
  /// configuration, the rest in <see cref="PostLoad"/>); <see cref="Unload"/> puts the native materials back on every
  /// tile that still exists and destroys everything it created.
  /// </summary>
  public sealed class FluidTerrainRendering : ILoadableSingleton, IPostLoadableSingleton, ITickableSingleton, ILateUpdatableSingleton, IUnloadableSingleton {
    public const string Variant = "Shaders/ModdableFluids/FluidTerrainURP";
    public const string VariantName = "ModdableFluids/FluidTerrainURP";
    public const string NativeShader = "Shader Graphs/TerrainURP";
    public const string Keyword = "_MODDABLE_FLUIDS_TERRAIN_OVERLAY";
    public const string LevelsTexture = "_MFTerrainOverlayMap";
    public const string ColorsTexture = "_MFTerrainOverlayColors";
    /// <summary>The native material collection the terrain materials come from (native MaterialRepository).</summary>
    public const string MaterialCollection = "Common";
    private const string TerrainMeshManagerType = "Timberborn.TerrainSystemRendering.TerrainMeshManager";
    // Native shader-feature keywords the variant compiles as multi_compile (the bundle holds no material that would keep them).
    private static readonly string[] CompiledKeywords = { "_USE_TRIPLANAR_SPLATMAP", "_SAMPLE_SPLATMAP", "_USELAYERTOOL" };
    private const BindingFlags Fields = BindingFlags.Instance | BindingFlags.NonPublic;

    private readonly ISingletonRepository _singletons;
    private readonly ITerrainService _terrain;
    private readonly TerrainMaterialMap _materialMap;
    private readonly IAssetLoader _assets;
    private readonly ISpecService _specs;
    private readonly List<Material> _slots = new List<Material>();
    private readonly Dictionary<Material, Material> _copyOf = new Dictionary<Material, Material>();
    private readonly Dictionary<Material, Material> _nativeOf = new Dictionary<Material, Material>();
    private readonly Dictionary<int, Texture2D> _levelStaging = new Dictionary<int, Texture2D>(), _colorStaging = new Dictionary<int, Texture2D>();
    private ModdableFluidsHost _host;
    private FluidTerrainOverlayField _field;
    private ICollection _tiles;
    private MeshRenderer[] _renderers;
    private Texture2DArray _levels, _colors;
    private int _ticks, _publishedTicks;
    private bool _keyword;

    /// <summary>The scene's overlay surface (CPU half).</summary>
    public FluidTerrainOverlayField Field => _field;
    /// <summary>Active tiles drawn with an overlay copy in the last frame.</summary>
    public int TilesWithOverlayMaterial { get; private set; }
    public IReadOnlyCollection<Material> NativeMaterials => _copyOf.Keys;

    public FluidTerrainRendering(ISingletonRepository singletons, ITerrainService terrain, TerrainMaterialMap materialMap, IAssetLoader assets, ISpecService specs) {
      _singletons = singletons; _terrain = terrain; _materialMap = materialMap; _assets = assets; _specs = specs;
    }

    /// <summary>
    /// The native members the terrain overlay reads, checked when the scene is configured, before it is bound, so a
    /// changed game fails with one message instead of a missing member in the first frame.
    /// </summary>
    public static IReadOnlyList<string> CheckContract() {
      var problems = new List<string>();
      void Require(bool ok, string member) { if (!ok) problems.Add(member); }
      var manager = typeof(TerrainMaterialMap).Assembly.GetType(TerrainMeshManagerType);
      Require(manager != null, TerrainMeshManagerType);
      if (manager != null) {
        Require(typeof(ILateUpdatableSingleton).IsAssignableFrom(manager), "TerrainMeshManager : ILateUpdatableSingleton (found through ISingletonRepository)");
        var tile = manager.GetNestedType("TileComponents", BindingFlags.NonPublic);
        Require(tile != null && tile.IsValueType, "TerrainMeshManager.TileComponents (struct)");
        if (tile != null) {
          Require(tile.GetField("_meshRenderer", Fields)?.FieldType == typeof(MeshRenderer), "TerrainMeshManager.TileComponents._meshRenderer : MeshRenderer");
          Require(manager.GetField("_tiles", Fields)?.FieldType == typeof(Dictionary<,>).MakeGenericType(typeof(Vector3Int), tile),
            "TerrainMeshManager._tiles : Dictionary<Vector3Int, TileComponents>");
        }
      }
      // The overlay level map mirrors the native soil-contamination map: RG16 PixelData (R old, G new), layer = terrain z.
      Require(typeof(TerrainMaterialMap).GetField("_textureSize", Fields)?.FieldType == typeof(Vector3Int), "TerrainMaterialMap._textureSize : Vector3Int");
      Require(typeof(TerrainMaterialMap).GetField("_contaminationMapTexture", Fields)?.FieldType == typeof(Texture2DArray), "TerrainMaterialMap._contaminationMapTexture : Texture2DArray");
      Require(typeof(TerrainMaterialMap).GetField("_contaminations", Fields)?.FieldType == typeof(PixelData[][]), "TerrainMaterialMap._contaminations : PixelData[][]");
      Require(Marshal.SizeOf(typeof(PixelData)) == FluidTerrainOverlayField.LevelBytesPerTexel, "PixelData is two bytes (R old, G new)");
      Require(typeof(ITerrainService).GetProperty("Size")?.PropertyType == typeof(Vector3Int), "ITerrainService.Size : Vector3Int");
      Require(typeof(MaterialCollectionSpec).GetProperty("CollectionId")?.PropertyType == typeof(string), "MaterialCollectionSpec.CollectionId : string");
      Require(typeof(MaterialCollectionSpec).GetProperty("Materials")?.PropertyType == typeof(System.Collections.Immutable.ImmutableArray<AssetRef<Material>>),
        "MaterialCollectionSpec.Materials : ImmutableArray<AssetRef<Material>>");
      Require(typeof(ISingletonRepository).GetMethod("GetSingletons") != null, "ISingletonRepository.GetSingletons<T>()");
      return problems;
    }

    /// <summary>
    /// The renderers of the native terrain tiles: <c>TerrainMeshManager._tiles</c>, created once while the manager loads.
    /// A tile without its renderer is refused.
    /// </summary>
    public static MeshRenderer[] ReadTiles(object manager, out ICollection tiles) {
      if (manager == null || manager.GetType().FullName != TerrainMeshManagerType) throw new ArgumentException("Expected the native " + TerrainMeshManagerType);
      tiles = manager.GetType().GetField("_tiles", Fields)?.GetValue(manager) as IDictionary
        ?? throw new InvalidOperationException("Native TerrainMeshManager._tiles is not a dictionary (expected Timberborn 1.1.2.8)");
      var renderer = manager.GetType().GetNestedType("TileComponents", BindingFlags.NonPublic)?.GetField("_meshRenderer", Fields)
        ?? throw new MissingFieldException(TerrainMeshManagerType + "+TileComponents", "_meshRenderer");
      var result = new List<MeshRenderer>();
      foreach (DictionaryEntry entry in (IDictionary)tiles) {
        if (!(renderer.GetValue(entry.Value) is MeshRenderer meshRenderer) || meshRenderer == null)
          throw new InvalidOperationException("Native terrain tile " + entry.Key + " has no MeshRenderer");
        result.Add(meshRenderer);
      }
      return result.ToArray();
    }

    // The overlay surface exists from Load on, so providers can write from their PostLoad.
    public void Load() {
      _host = ModdableFluidsEntry.Host;
      var overlays = _host.TerrainOverlays;
      if (overlays.Count == 0) throw new InvalidOperationException("Moddable Fluids' terrain renderer is bound only when a mod registered a terrain overlay");
      var size = _terrain.Size;
      bool linear = QualitySettings.activeColorSpace == ColorSpace.Linear;
      // Material colours, as Material.SetColor passes them to the shader.
      var colors = overlays.Select(o => linear ? new FluidTerrainOverlayColor(Mathf.GammaToLinearSpace(o.Color.Red), Mathf.GammaToLinearSpace(o.Color.Green),
        Mathf.GammaToLinearSpace(o.Color.Blue)) : o.Color).ToArray();
      _field = new FluidTerrainOverlayField(size.x, size.y, size.z, colors, Environment.CurrentManagedThreadId);
      _host.AttachTerrainOverlays(_field);
    }

    public void PostLoad() {
      // Everything that can refuse, before anything is created or assigned.
      var size = (Vector3Int)typeof(TerrainMaterialMap).GetField("_textureSize", Fields).GetValue(_materialMap);
      if (size != new Vector3Int(_field.Width, _field.Height, _field.Depth))
        throw new InvalidOperationException("The native soil-contamination map is " + size + ", the terrain " + new Vector3Int(_field.Width, _field.Height, _field.Depth) + "; the overlay map mirrors it");
      var managerType = typeof(TerrainMaterialMap).Assembly.GetType(TerrainMeshManagerType);
      var managers = _singletons.GetSingletons<ILateUpdatableSingleton>().Where(s => s.GetType() == managerType).ToArray();
      if (managers.Length != 1) throw new InvalidOperationException("Expected one native TerrainMeshManager in the scene, found " + managers.Length);
      _renderers = ReadTiles(managers[0], out _tiles);
      var natives = _specs.GetSpecs<MaterialCollectionSpec>().Where(s => s.CollectionId == MaterialCollection).SelectMany(s => s.Materials).Select(m => m.Asset)
        .Where(m => m != null && m.shader != null && m.shader.name == NativeShader).Distinct().ToArray();
      if (natives.Length == 0) throw new InvalidOperationException("MaterialCollection " + MaterialCollection + " holds no material on " + NativeShader);
      var variant = _assets.Load<Shader>(Variant);
      if (variant == null || variant.name != VariantName) throw new InvalidOperationException("Shader variant " + VariantName + " is missing from the Moddable Fluids bundle");
      if (!variant.isSupported) throw new InvalidOperationException("Shader variant " + VariantName + " is not supported on this GPU");
      foreach (var native in natives) Check(native, variant);
      foreach (var format in new[] { TextureFormat.RG16, TextureFormat.RGBAHalf })
        if (!SystemInfo.SupportsTextureFormat(format)) throw new InvalidOperationException("This GPU has no " + format + " textures, which the terrain overlay maps need");
      if ((SystemInfo.copyTextureSupport & UnityEngine.Rendering.CopyTextureSupport.Basic) == 0)
        throw new InvalidOperationException("This GPU has no Graphics.CopyTexture, which uploads the terrain overlay maps (and the native terrain maps)");
      var known = new HashSet<Material>(natives);
      foreach (var renderer in _renderers) {
        if (!renderer.gameObject.activeSelf) continue;
        renderer.GetSharedMaterials(_slots);
        foreach (var material in _slots)
          if (material == null || !known.Contains(material))
            throw new InvalidOperationException("Terrain tile " + renderer.name + " draws with " + (material == null ? "no material" : material.name + " (" + material.shader?.name + ")")
              + ", not a native " + MaterialCollection + " terrain material on " + NativeShader);
      }

      foreach (var native in natives) {
        var copy = new Material(variant) { name = native.name + " (Moddable Fluids terrain overlay, scene copy)" };
        Refresh(copy, native);
        _copyOf.Add(native, copy); _nativeOf.Add(copy, native);
      }
      _levels = NewArray(TextureFormat.RG16, "ModdableFluids.TerrainOverlayLevels");
      _colors = NewArray(TextureFormat.RGBAHalf, "ModdableFluids.TerrainOverlayColors");
      // New GPU textures are undefined (as natively): every layer starts at zero.
      var zeroLevels = new byte[FluidTerrainOverlayField.LevelBytesPerTexel * _field.Width * _field.Height];
      var zeroColors = new ushort[FluidTerrainOverlayField.ColorHalvesPerTexel * _field.Width * _field.Height];
      for (int z = 0; z < _field.Depth; z++) {
        Upload(_levels, _levelStaging, TextureFormat.RG16, zeroLevels, FluidTerrainOverlayField.LevelBytesPerTexel, z, 0, _field.Height - 1);
        Upload(_colors, _colorStaging, TextureFormat.RGBAHalf, zeroColors, FluidTerrainOverlayField.ColorHalvesPerTexel, z, 0, _field.Height - 1);
      }
      Shader.SetGlobalTexture(LevelsTexture, _levels);
      Shader.SetGlobalTexture(ColorsTexture, _colors);
      Shader.DisableKeyword(Keyword); _keyword = false;
      Debug.Log("[ModdableFluids] Terrain overlays drawn on scene copies of " + string.Join(", ", natives.Select(m => m.name)) + " on " + _renderers.Length
        + " native terrain tiles (" + _field.Width + " x " + _field.Height + " x " + _field.Depth + "): " + string.Join("; ", _host.TerrainOverlays));
    }

    private static void Check(Material native, Shader variant) {
      for (int i = 0; i < native.shader.GetPropertyCount(); i++) {
        int index = variant.FindPropertyIndex(native.shader.GetPropertyName(i));
        if (index < 0 || variant.GetPropertyType(index) != native.shader.GetPropertyType(i))
          throw new InvalidOperationException(VariantName + " lacks native property " + native.shader.GetPropertyName(i) + "; regenerate it from the installed game's graph");
      }
      foreach (var keyword in native.enabledKeywords)
        if (Array.IndexOf(CompiledKeywords, keyword.name) < 0) throw new InvalidOperationException(native.name + " enables " + keyword.name + ", which " + VariantName + " does not compile");
    }

    private static void Refresh(Material copy, Material native) {
      copy.CopyPropertiesFromMaterial(native);
      copy.renderQueue = native.renderQueue;
      foreach (var keyword in native.enabledKeywords) copy.EnableKeyword(keyword.name);
      if (copy.renderQueue != native.renderQueue) throw new InvalidOperationException(copy.name + ": render queue " + copy.renderQueue + ", native " + native.renderQueue);
    }

    private Texture2DArray NewArray(TextureFormat format, string name) =>
      new Texture2DArray(_field.Width, _field.Height, _field.Depth, format, false) { name = name, filterMode = FilterMode.Point, wrapMode = TextureWrapMode.Clamp };

    public void Tick() => _ticks++;

    // Late update: after the frame's ticks (providers write in theirs) and, in native order or not, the native mesh's
    // tile rebuilds; a tile rebuilt after this pass draws with the native material for that one frame.
    public void LateUpdateSingleton() {
      if (_levels == null) return;
      foreach (var pair in _copyOf) Refresh(pair.Value, pair.Key);
      AssignTiles();
      if (_ticks == 0) { if (_field.HasPendingWork) _field.Publish(interpolate: false); }
      else if (_ticks != _publishedTicks) { _field.Publish(interpolate: true); _publishedTicks = _ticks; }
      for (int z = 0; z < _field.Depth; z++) {
        if (_field.TakeLevelUpload(z, out int lo, out int hi))
          Upload(_levels, _levelStaging, TextureFormat.RG16, _field.LevelLayer(z), FluidTerrainOverlayField.LevelBytesPerTexel, z, lo, hi);
        if (_field.TakeColorUpload(z, out lo, out hi))
          Upload(_colors, _colorStaging, TextureFormat.RGBAHalf, _field.ColorLayer(z), FluidTerrainOverlayField.ColorHalvesPerTexel, z, lo, hi);
      }
      bool keyword = _field.NonZeroTexels > 0;
      if (keyword != _keyword) { if (keyword) Shader.EnableKeyword(Keyword); else Shader.DisableKeyword(Keyword); _keyword = keyword; }
    }

    private void AssignTiles() {
      if (_tiles.Count != _renderers.Length) throw new InvalidOperationException("The native terrain tiles changed from " + _renderers.Length + " to " + _tiles.Count + " after the scene loaded");
      int count = 0;
      foreach (var renderer in _renderers) {
        if (renderer == null) throw new InvalidOperationException("A native terrain tile was destroyed while the scene is loaded");
        if (!renderer.gameObject.activeSelf) continue;
        renderer.GetSharedMaterials(_slots);
        bool changed = false;
        for (int i = 0; i < _slots.Count; i++) {
          var material = _slots[i];
          if (material != null && _copyOf.TryGetValue(material, out var copy)) { _slots[i] = copy; changed = true; }
          else if (material == null || !_nativeOf.ContainsKey(material))
            throw new InvalidOperationException("Terrain tile " + renderer.name + " holds " + (material == null ? "no material" : material.name)
              + ", not a native terrain material or its Moddable Fluids copy");
        }
        if (changed) renderer.sharedMaterials = _slots.ToArray();
        count++;
      }
      TilesWithOverlayMaterial = count;
    }

    // Rows lo..hi of layer z, through a staging texture of the next power-of-two height (the native uploads whole layers
    // through one buffer texture and Graphics.CopyTexture; this copies the changed band).
    private void Upload<T>(Texture2DArray array, Dictionary<int, Texture2D> staging, TextureFormat format, T[] data, int elementsPerTexel, int z, int lo, int hi) where T : struct {
      int rows = hi - lo + 1, height = 1, width = _field.Width;
      while (height < rows) height <<= 1;
      if (height > _field.Height) height = _field.Height;
      int start = Math.Min(lo, _field.Height - height);
      if (!staging.TryGetValue(height, out var buffer))
        staging.Add(height, buffer = new Texture2D(width, height, format, false) { name = array.name + ".Staging" + height, filterMode = FilterMode.Point, wrapMode = TextureWrapMode.Clamp });
      buffer.SetPixelData(data, 0, start * width * elementsPerTexel);
      buffer.Apply(false, false);
      Graphics.CopyTexture(buffer, 0, 0, 0, 0, width, height, array, z, 0, 0, start);
    }

    public void Unload() {
      if (_keyword || _levels != null) Shader.DisableKeyword(Keyword);
      _keyword = false;
      var problems = new List<string>();
      if (_field != null && _host != null && _host.TerrainOverlaysAttached) {
        try { _host.DetachTerrainOverlays(_field); } catch (Exception e) { problems.Add(e.Message); }
      }
      if (_renderers != null)
        foreach (var renderer in _renderers) {
          if (renderer == null) continue;
          renderer.GetSharedMaterials(_slots);
          bool changed = false;
          for (int i = 0; i < _slots.Count; i++) {
            var material = _slots[i];
            if (material != null && _nativeOf.TryGetValue(material, out var native)) { _slots[i] = native; changed = true; }
            else if (material == null || !_copyOf.ContainsKey(material)) problems.Add(renderer.name + " holds " + (material == null ? "no material" : material.name));
          }
          if (changed) renderer.sharedMaterials = _slots.ToArray();
        }
      foreach (var copy in _nativeOf.Keys) if (copy != null) UnityEngine.Object.Destroy(copy);
      _copyOf.Clear(); _nativeOf.Clear();
      foreach (var texture in _levelStaging.Values.Concat(_colorStaging.Values)) if (texture != null) UnityEngine.Object.Destroy(texture);
      _levelStaging.Clear(); _colorStaging.Clear();
      if (_levels != null) UnityEngine.Object.Destroy(_levels);
      if (_colors != null) UnityEngine.Object.Destroy(_colors);
      _levels = _colors = null; _renderers = null; _field = null;
      if (problems.Count > 0)
        throw new InvalidOperationException("Native terrain tiles held unexpected materials while Moddable Fluids' terrain overlay was loaded (native materials restored): " + string.Join("; ", problems));
    }
  }
}
