using System;
using System.Collections.Generic;
using System.Reflection;
using System.Runtime.InteropServices;
using Timberborn.BlueprintSystem;
using Timberborn.Common;
using Timberborn.TerrainSystemRendering;
using Timberborn.WaterSystem;
using Timberborn.WaterSystemRendering;
using UnityEngine;
using Object = UnityEngine.Object;

namespace DeepFrontier.Scripts.Radiation {
  // Radioactive water and irradiated ground drawn by the native surfaces.
  //
  // Native path (Timberborn 1.1.2.8, decompiled Timberborn.WaterSystemRendering
  // and Timberborn.TerrainSystemRendering):
  // - Water: UpdateWaterTexturesTask writes byte(255 * WaterColumn.Contamination)
  //   into WaterRenderer._contaminations, a DataTextureArray<byte> (R8, layer =
  //   column index, pixel x + y * width, old and new arrays). The
  //   WaterColumnPostprocessor publishes it as _OldContaminations and
  //   _NewContaminations, and the native WaterContamination subgraph of
  //   PhysicalWaterURP_Opaque/_Transparent samples it and colours the surface.
  //   The single R8 channel holds b and nothing else.
  // - Soil: TerrainMaterialMap keeps _contaminationMapTexture, an RG16
  //   Texture2DArray of PixelData (R old, G new; layer = terrain z, pixel
  //   x + y * width), published as _ContaminationMap, which the
  //   SoilContaminationVisualization subgraph of TerrainURP blends in.
  //
  // tools/native_shader_variants.mjs builds variants of those three native
  // graphs (bundled from AssetBundles/Resources/Shaders/DeepFrontier): the native
  // graph plus a second instance of its own contamination subgraph, fed from
  // the texture arrays below in the same layout, lerped over the native result
  // behind a global keyword. RadiationRenderer puts the variants on the native
  // materials while a game is loaded and restores the native shaders on unload.
  //
  // The native materials outlive the scene (their shaders are what the next
  // scene starts from), but the variants do not reach Unload intact: native
  // SceneLoader.LoadSceneCoroutine calls IAssetLoader.Reset (ModAssetBundleProvider
  // -> ModAssetBundleLoader.Reload: AssetBundle.Unload(true) on every mod bundle,
  // then a fresh load) before SceneManager.LoadScene, whose teardown runs
  // SingletonLifecycleUnityAdapter.OnDestroy -> IUnloadableSingleton.Unload. A
  // material whose shader was destroyed reports Hidden/InternalErrorShader
  // (Unity 6000.5.11f1, checked with a bundle-loaded shader and Unload(true)), so
  // ShaderSwap.Restore accepts exactly that shader once its variant is destroyed.
  internal static class RadiationShading {
    internal const string WaterOpaqueVariant = "Shaders/DeepFrontier/RadioactiveWaterURP_Opaque";
    internal const string WaterTransparentVariant = "Shaders/DeepFrontier/RadioactiveWaterURP_Transparent";
    internal const string TerrainVariant = "Shaders/DeepFrontier/IrradiatedTerrainURP";
    internal const string WaterOpaqueNative = "Shader Graphs/PhysicalWaterURP_Opaque";
    internal const string WaterTransparentNative = "Shader Graphs/PhysicalWaterURP_Transparent";
    internal const string TerrainNative = "Shader Graphs/TerrainURP";
    internal const string WaterOpaqueVariantName = "DeepFrontier/RadioactiveWaterURP_Opaque";
    internal const string WaterTransparentVariantName = "DeepFrontier/RadioactiveWaterURP_Transparent";
    internal const string TerrainVariantName = "DeepFrontier/IrradiatedTerrainURP";

    internal const string WaterKeyword = "_DEEP_FRONTIER_RADIOACTIVE_WATER";
    internal const string SoilKeyword = "_DEEP_FRONTIER_IRRADIATED_SOIL";
    internal static readonly int OldRadioactivity = Shader.PropertyToID("_DFOldRadioactivity");
    internal static readonly int NewRadioactivity = Shader.PropertyToID("_DFNewRadioactivity");
    internal static readonly int RadioactiveBaseColorA = Shader.PropertyToID("_DFRadioactiveBaseColorA");
    internal static readonly int RadioactiveBaseColorB = Shader.PropertyToID("_DFRadioactiveBaseColorB");
    internal static readonly int RadioactiveDetailColorA = Shader.PropertyToID("_DFRadioactiveDetailColorA");
    internal static readonly int RadioactiveDetailColorB = Shader.PropertyToID("_DFRadioactiveDetailColorB");
    internal static readonly int IrradiatedSoilMap = Shader.PropertyToID("_DFIrradiatedSoilMap");
    internal static readonly int IrradiatedSoilColor = Shader.PropertyToID("_DFIrradiatedSoilColor");

    // Native shader-feature keywords the variants compile as multi_compile
    // (the bundle holds no material that would keep their variants).
    internal static readonly string[] WaterCompiledKeywords = { "_CALCULATE_OUTFLOWS" };
    internal static readonly string[] TerrainCompiledKeywords = { "_USE_TRIPLANAR_SPLATMAP", "_SAMPLE_SPLATMAP", "_USELAYERTOOL" };
    // Native TerrainURP materials (MaterialCollection.Common), by repository name.
    internal static readonly string[] TerrainMaterials = { "Grass", "Cliff", "CliffEdge", "SlopeCliff", "SlopeCliffEdge" };

    private const BindingFlags Fields = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;

    // Every native member the variants mirror or the renderer reads; throws
    // when a game update changed one.
    internal static void Verify() {
      var failures = new List<string>();
      void Require(bool condition, string what) { if (!condition) failures.Add(what); }
      void RequireField(Type type, string name, Type fieldType) =>
        Require(type.GetField(name, Fields)?.FieldType == fieldType, $"{type.Name}.{name} : {fieldType.Name}");
      var spec = typeof(WaterMeshSpec);
      foreach (var name in new[] { nameof(WaterMeshSpec.OpaqueMaterial), nameof(WaterMeshSpec.TransparentMaterial) })
        Require(spec.GetProperty(name)?.PropertyType == typeof(AssetRef<Material>), $"WaterMeshSpec.{name} : AssetRef<Material>");
      RequireField(typeof(WaterRenderer), "_contaminations", typeof(DataTextureArray<byte>));
      RequireField(typeof(UpdateWaterTexturesTask), "_contaminations", typeof(DataTextureArray<byte>));
      RequireField(typeof(UpdateWaterTexturesTask), "_waterColumns", typeof(ReadOnlyArray<ReadOnlyWaterColumn>));
      Require(WaterTextureNames.OldContaminations == "_OldContaminations" && WaterTextureNames.NewContaminations == "_NewContaminations",
        "WaterTextureNames.Old/NewContaminations are _OldContaminations/_NewContaminations");
      RequireField(typeof(TerrainMaterialMap), "_contaminationMapTexture", typeof(Texture2DArray));
      RequireField(typeof(TerrainMaterialMap), "_contaminations", typeof(PixelData[][]));
      RequireField(typeof(TerrainMaterialMap), "_textureSize", typeof(Vector3Int));
      Require(typeof(TerrainMaterialMap).GetMethod(nameof(TerrainMaterialMap.SetSoilContamination), new[] { typeof(Vector3Int), typeof(float) }) != null,
        "TerrainMaterialMap.SetSoilContamination(Vector3Int, float)");
      Require(Marshal.SizeOf(typeof(PixelData)) == 2, "PixelData is two bytes (R old, G new)");
      if (failures.Count > 0)
        throw new InvalidOperationException("Native water or terrain rendering changed; regenerate the Deep Frontier shader variants: " + string.Join("; ", failures));
    }

    // A native material drawn with a variant while a game is loaded. The
    // variant must declare every native property with the same type, and
    // every keyword the native material enables must be compiled for all
    // combinations.
    internal sealed class ShaderSwap {
      private const string ErrorShaderName = "Hidden/InternalErrorShader";
      private readonly Material _material;
      private readonly Shader _native, _variant, _errorShader;
      private readonly string[] _keywords;
      private readonly string _materialName, _nativeName, _variantName;
      private bool _applied;

      internal ShaderSwap(Material material, string nativeShader, Shader variant, string variantName, string[] compiledKeywords) {
        if (material == null) throw new InvalidOperationException($"Native material for {nativeShader} is missing");
        _material = material;
        _native = material.shader;
        if (_native == null || _native.name != nativeShader)
          throw new InvalidOperationException($"{material.name}: expected native shader {nativeShader}, found {(_native == null ? "none" : _native.name)}");
        if (variant == null || variant.name != variantName) throw new InvalidOperationException($"Shader variant {variantName} is missing from the Deep Frontier bundle");
        if (!variant.isSupported) throw new InvalidOperationException($"Shader variant {variantName} is not supported on this GPU");
        _variant = variant;
        _errorShader = Shader.Find(ErrorShaderName);
        if (_errorShader == null) throw new InvalidOperationException($"Unity's {ErrorShaderName} is missing");
        _materialName = material.name; _nativeName = nativeShader; _variantName = variantName;
        for (int i = 0; i < _native.GetPropertyCount(); i++) {
          string name = _native.GetPropertyName(i);
          int index = variant.FindPropertyIndex(name);
          if (index < 0 || variant.GetPropertyType(index) != _native.GetPropertyType(i))
            throw new InvalidOperationException($"{variantName} lacks native property {name} ({_native.GetPropertyType(i)}); regenerate it from the installed game's graph");
        }
        var enabled = material.enabledKeywords;
        _keywords = new string[enabled.Length];
        for (int i = 0; i < enabled.Length; i++) {
          _keywords[i] = enabled[i].name;
          if (Array.IndexOf(compiledKeywords, _keywords[i]) < 0)
            throw new InvalidOperationException($"{material.name} enables {_keywords[i]}, which {variantName} does not compile for every combination");
        }
      }

      internal Material Material => _material;

      internal void Apply() {
        _applied = true;
        Use(_variant);
      }

      // Puts the native shader and keywords back after Apply, always. Returns
      // null when the material held what Apply left (the variant, or the error
      // shader once the asset loader reset destroyed the variant), otherwise
      // what it held instead.
      internal string Restore() {
        if (!_applied) return null;
        if (_material == null) return $"{_materialName} was destroyed while it held {_variantName}";
        if (_native == null) return $"{_materialName}: {_nativeName} was destroyed while the material held {_variantName}";
        var current = _material.shader;
        bool expected = _variant != null ? current == _variant : current == _errorShader;
        string problem = expected ? null
          : $"{_materialName}: expected {(_variant != null ? _variantName : ErrorShaderName + " (" + _variantName + " unloaded)")} before restoring {_nativeName}, found {(current == null ? "none" : current.name)}";
        Use(_native);
        _applied = false;
        return problem;
      }

      // Restores every applied swap, then throws for any that failed or held
      // something else.
      internal static void RestoreAll(List<ShaderSwap> swaps) {
        var problems = new List<string>();
        foreach (var swap in swaps) {
          try {
            if (swap.Restore() is string problem) problems.Add(problem);
          } catch (Exception exception) {
            problems.Add(exception.Message);
          }
        }
        swaps.Clear();
        if (problems.Count > 0)
          throw new InvalidOperationException("Native water or terrain material changed while Deep Frontier's shader variant was on it (native shader restored): " + string.Join("; ", problems));
      }

      private void Use(Shader shader) {
        _material.shader = shader;
        foreach (var keyword in _keywords) {
          _material.EnableKeyword(keyword);
          if (!_material.IsKeywordEnabled(keyword)) throw new InvalidOperationException($"{_material.name}: keyword {keyword} did not survive the shader change");
        }
      }
    }

    // Uploads changed layers the way the native renderer does (buffer
    // texture, then Graphics.CopyTexture into the array layer).
    internal static void UploadLayer(Texture2D buffer, byte[] data, Texture2DArray array, int layer) {
      buffer.SetPixelData(data, 0);
      buffer.Apply(false, false);
      Graphics.CopyTexture(buffer, 0, 0, array, layer, 0);
    }

    internal static Texture2DArray CreateArray(int width, int height, int depth, TextureFormat format, string name) =>
      new Texture2DArray(width, height, depth, format, false) { name = name, filterMode = FilterMode.Point, wrapMode = TextureWrapMode.Clamp };

    internal static Texture2D CreateBuffer(int width, int height, TextureFormat format, string name) =>
      new Texture2D(width, height, format, false) { name = name, filterMode = FilterMode.Point, wrapMode = TextureWrapMode.Clamp };

    internal static void SetKeyword(string keyword, bool enabled) {
      if (enabled) Shader.EnableKeyword(keyword); else Shader.DisableKeyword(keyword);
    }

    internal static void Destroy(Object obj) { if (obj != null) Object.Destroy(obj); }
  }

  // Radioactive water: the second native WaterContamination pass. Its R8 value
  // runs through the native smoothstep(MinContaminationThreshold,
  // MaxContaminationThreshold) ^ ContaminationNonlinearity, so the stored value
  // is the inverse of that curve applied to the wanted lerp weight
  // w = visibility(r) * r / (b + r): mixed with badwater by share, and visible
  // from the pump detection limit (0.12 there, 1 at r = 1, log-scaled like the
  // overlay it replaces).
  internal sealed class RadioactiveWaterSurface {
    private const int WeightSteps = 1024;
    private readonly RadiationShading.ShaderSwap[] _swaps;
    private readonly byte[] _weightToByte = new byte[WeightSteps + 1];
    private int _width, _height, _layers;
    private byte[][] _old = Array.Empty<byte[]>(), _new = Array.Empty<byte[]>();
    private bool[][] _wet = Array.Empty<bool[]>();
    private bool[] _dirty = Array.Empty<bool>();
    private Texture2DArray _oldArray, _newArray;
    private Texture2D _buffer;
    private int _nonZero;
    private bool _keyword;
    private RadiationSimulation.RowRange _rowsWithData = RadiationSimulation.RowRange.None;

    // Each swap joins `applied` before it is applied; the renderer restores them.
    internal RadioactiveWaterSurface(Material opaque, Material transparent, Shader opaqueVariant, Shader transparentVariant,
        List<RadiationShading.ShaderSwap> applied) {
      _swaps = new[] {
        new RadiationShading.ShaderSwap(opaque, RadiationShading.WaterOpaqueNative, opaqueVariant, RadiationShading.WaterOpaqueVariantName, RadiationShading.WaterCompiledKeywords),
        new RadiationShading.ShaderSwap(transparent, RadiationShading.WaterTransparentNative, transparentVariant, RadiationShading.WaterTransparentVariantName, RadiationShading.WaterCompiledKeywords),
      };
      float min = NativeFloat(opaque, transparent, "_MinContaminationThreshold");
      float max = NativeFloat(opaque, transparent, "_MaxContaminationThreshold");
      float nonlinearity = NativeFloat(opaque, transparent, "_ContaminationNonlinearity");
      if (!(max > min) || !(min >= 0f) || !(max <= 1f) || !(nonlinearity > 0f))
        throw new InvalidOperationException($"Native water contamination curve changed: thresholds {min}..{max}, nonlinearity {nonlinearity}");
      for (int k = 0; k <= WeightSteps; k++) {
        float s = Mathf.Pow(k / (float)WeightSteps, 1f / nonlinearity);
        float t = 0.5f - Mathf.Sin(Mathf.Asin(1f - 2f * s) / 3f);      // inverse smoothstep
        _weightToByte[k] = (byte)Mathf.RoundToInt(255f * (min + t * (max - min)));
      }
      foreach (var swap in _swaps) {
        applied.Add(swap);
        swap.Apply();
        swap.Material.SetColor(RadiationShading.RadioactiveBaseColorA, RadiationMaterials.WaterBaseColorA);
        swap.Material.SetColor(RadiationShading.RadioactiveBaseColorB, RadiationMaterials.WaterBaseColorB);
        swap.Material.SetColor(RadiationShading.RadioactiveDetailColorA, RadiationMaterials.WaterDetailColorA);
        swap.Material.SetColor(RadiationShading.RadioactiveDetailColorB, RadiationMaterials.WaterDetailColorB);
      }
      RadiationShading.SetKeyword(RadiationShading.WaterKeyword, false);
    }

    private static float NativeFloat(Material opaque, Material transparent, string name) {
      if (!opaque.HasFloat(name) || !transparent.HasFloat(name)) throw new InvalidOperationException($"Native water materials lost {name}");
      float value = opaque.GetFloat(name);
      if (transparent.GetFloat(name) != value) throw new InvalidOperationException($"Native water materials disagree on {name}");
      return value;
    }

    internal bool Pending => !_rowsWithData.Empty;

    internal byte Encode(float radiation, float contamination) {
      if (radiation < RadiationTuning.DetectionLimit) return 0;
      // 0.12 at the detection limit to 1 at r = 1, log-scaled over the decades
      // between them (0.38 per decade at 0.5%; the former four-decade range had 0.22).
      float visibility = Mathf.Min(1f, 0.12f + 0.88f * Mathf.Log10(radiation / RadiationTuning.DetectionLimit) / -Mathf.Log10(RadiationTuning.DetectionLimit));
      float weight = visibility * radiation / (contamination + radiation);
      return _weightToByte[Mathf.RoundToInt(Mathf.Clamp01(weight) * WeightSteps)];
    }

    // Native order (UpdateWaterTexturesTask): old = the previous new; a column
    // that just got water shows its value at once (old = new); a column that
    // just dried keeps its last value.
    internal void Update(RadiationSimulation simulation, ReadOnlySpan<byte> counts, ReadOnlySpan<WaterColumn> columns) {
      if (_buffer == null) {
        _width = simulation.XSize; _height = simulation.YSize;
        _buffer = RadiationShading.CreateBuffer(_width, _height, TextureFormat.R8, "DeepFrontier.RadioactivityBuffer");
      }
      if (simulation.Layers > _layers) Resize(simulation.Layers);
      var rows = RadiationSimulation.RowRange.Union(simulation.VisibleRows, _rowsWithData).Clamp(0, _height - 1);
      var withData = RadiationSimulation.RowRange.None;
      var radiation = simulation.WaterRadiation;
      int stride = simulation.Stride, vs = simulation.VerticalStride;
      for (int y = rows.Lo; y <= rows.Hi; y++) {
        bool rowData = false;
        int rowStart = (y + 1) * stride + 1;
        for (int x = 0; x < _width; x++) {
          int i = rowStart + x, p = x + y * _width, count = counts[i];
          for (int j = 0; j < _layers; j++) {
            byte previousOld = _old[j][p], previousNew = _new[j][p];
            bool previousWet = _wet[j][p], wet = false;
            byte next = 0;
            if (j < count) {
              int idx = j * vs + i;
              wet = columns[idx].WaterDepth > 0f;
              next = wet ? Encode(radiation[idx], columns[idx].Contamination) : previousWet ? previousNew : (byte)0;
            }
            byte old = wet && !previousWet ? next : previousNew;
            _wet[j][p] = wet;
            if (old != previousOld || next != previousNew) {
              _nonZero += (old != 0 ? 1 : 0) - (previousOld != 0 ? 1 : 0) + (next != 0 ? 1 : 0) - (previousNew != 0 ? 1 : 0);
              _old[j][p] = old; _new[j][p] = next;
              _dirty[j] = true;
            }
            rowData |= old != 0 || next != 0;
          }
        }
        if (rowData) withData.Include(y);
      }
      _rowsWithData = withData;
      for (int j = 0; j < _layers; j++) {
        if (!_dirty[j]) continue;
        RadiationShading.UploadLayer(_buffer, _old[j], _oldArray, j);
        RadiationShading.UploadLayer(_buffer, _new[j], _newArray, j);
        _dirty[j] = false;
      }
      bool keyword = _nonZero > 0;
      if (keyword != _keyword) { RadiationShading.SetKeyword(RadiationShading.WaterKeyword, keyword); _keyword = keyword; }
    }

    // Layers follow the native column count; data is kept and re-uploaded.
    private void Resize(int layers) {
      int cells = _width * _height;
      Array.Resize(ref _old, layers); Array.Resize(ref _new, layers); Array.Resize(ref _wet, layers);
      for (int j = _layers; j < layers; j++) { _old[j] = new byte[cells]; _new[j] = new byte[cells]; _wet[j] = new bool[cells]; }
      _dirty = new bool[layers];
      for (int j = 0; j < layers; j++) _dirty[j] = true;
      RadiationShading.Destroy(_oldArray); RadiationShading.Destroy(_newArray);
      _oldArray = RadiationShading.CreateArray(_width, _height, layers, TextureFormat.R8, "DeepFrontier.OldRadioactivity");
      _newArray = RadiationShading.CreateArray(_width, _height, layers, TextureFormat.R8, "DeepFrontier.NewRadioactivity");
      Shader.SetGlobalTexture(RadiationShading.OldRadioactivity, _oldArray);
      Shader.SetGlobalTexture(RadiationShading.NewRadioactivity, _newArray);
      _layers = layers;
    }

    internal void Unload() {
      RadiationShading.SetKeyword(RadiationShading.WaterKeyword, false);
      RadiationShading.Destroy(_oldArray); RadiationShading.Destroy(_newArray); RadiationShading.Destroy(_buffer);
    }
  }

  // Irradiated ground: the second native SoilContaminationVisualization pass,
  // with Deep Frontier's soil map in the native TerrainMaterialMap layout and
  // update rule (a changed value moves G to R and writes the new G; the next
  // update settles R = G). Values map like native soil contamination
  // (SoilContaminationService.GetMapSoilContamination: 0.1 at the first visible
  // level, 1 at full), from MinRenderedSoil to FullSoil.
  internal sealed class IrradiatedSoilSurface {
    // The tint appears where plants die (one threshold: RadiationTuning.IrradiatedGroundThreshold).
    private const float MinRenderedSoil = RadiationTuning.IrradiatedGroundThreshold;
    private const float FullSoil = 0.5f;
    private const float MinMapValue = 0.1f;
    private readonly RadiationShading.ShaderSwap[] _swaps;
    private readonly int _width, _height, _depth;
    private readonly byte[][] _pixels;          // per terrain z: (R old, G new) per cell
    private readonly bool[] _dirty, _hasData;   // per layer; per cell
    private readonly byte[] _target;            // per terrain z, scratch
    private readonly Texture2DArray _array;
    private readonly Texture2D _buffer;
    private int _nonZero;
    private bool _keyword, _primed;
    private RadiationSimulation.RowRange _rowsWithData = RadiationSimulation.RowRange.None;

    // Each swap joins `applied` before it is applied; the renderer restores them.
    internal IrradiatedSoilSurface(IReadOnlyList<Material> materials, Shader variant, Vector3Int terrainSize, List<RadiationShading.ShaderSwap> applied) {
      _swaps = new RadiationShading.ShaderSwap[materials.Count];
      for (int i = 0; i < materials.Count; i++)
        _swaps[i] = new RadiationShading.ShaderSwap(materials[i], RadiationShading.TerrainNative, variant, RadiationShading.TerrainVariantName,
          RadiationShading.TerrainCompiledKeywords);
      _width = terrainSize.x; _height = terrainSize.y; _depth = terrainSize.z;
      int cells = _width * _height;
      _pixels = new byte[_depth][];
      for (int z = 0; z < _depth; z++) _pixels[z] = new byte[2 * cells];
      _dirty = new bool[_depth];
      for (int z = 0; z < _depth; z++) _dirty[z] = true;    // new GPU textures are undefined, as natively
      _hasData = new bool[cells];
      _target = new byte[_depth];
      _array = RadiationShading.CreateArray(_width, _height, _depth, TextureFormat.RG16, "DeepFrontier.IrradiatedSoilMap");
      _buffer = RadiationShading.CreateBuffer(_width, _height, TextureFormat.RG16, "DeepFrontier.IrradiatedSoilBuffer");
      Shader.SetGlobalTexture(RadiationShading.IrradiatedSoilMap, _array);
      var color = SoilColor();
      foreach (var swap in _swaps) {
        applied.Add(swap);
        swap.Apply();
        swap.Material.SetColor(RadiationShading.IrradiatedSoilColor, color);
      }
      RadiationShading.SetKeyword(RadiationShading.SoilKeyword, false);
    }

    // The native soil contamination texture (veins, sRGB mean
    // NativeSoilVeinColor) times this colour gives SoilVeinColor.
    private static Color SoilColor() {
      var target = RadiationMaterials.SoilVeinColor; var native = RadiationMaterials.NativeSoilVeinColor;
      if (QualitySettings.activeColorSpace == ColorSpace.Gamma)
        return new Color(target.r / native.r, target.g / native.g, target.b / native.b, 1f);
      var linear = new Color(Mathf.GammaToLinearSpace(target.r) / Mathf.GammaToLinearSpace(native.r),
        Mathf.GammaToLinearSpace(target.g) / Mathf.GammaToLinearSpace(native.g),
        Mathf.GammaToLinearSpace(target.b) / Mathf.GammaToLinearSpace(native.b), 1f);
      return linear.gamma;   // Material.SetColor linearises colours in a linear project
    }

    internal bool Pending => !_rowsWithData.Empty;

    private static byte Encode(float soil) {
      if (soil < MinRenderedSoil) return 0;
      float value = 1f - (1f - MinMapValue) * (1f - Mathf.Min(soil, FullSoil) / FullSoil);
      return (byte)(255f * value);
    }

    internal void Update(RadiationSimulation simulation) {
      if (simulation.XSize != _width || simulation.YSize != _height)
        throw new InvalidOperationException("Irradiated soil map and the radiation simulation disagree on the map size");
      var rows = RadiationSimulation.RowRange.Union(simulation.VisibleRows, _rowsWithData).Clamp(0, _height - 1);
      var withData = RadiationSimulation.RowRange.None;
      var counts = simulation.Counts; var columns = simulation.WaterSnapshot;
      int stride = simulation.Stride, vs = simulation.VerticalStride;
      for (int y = rows.Lo; y <= rows.Hi; y++) {
        bool rowData = false;
        int rowStart = (y + 1) * stride + 1;
        for (int x = 0; x < _width; x++) {
          int i = rowStart + x, p = x + y * _width, count = counts[i];
          bool any = false;
          for (int j = 0; j < count; j++) {
            int idx = j * vs + i;
            // Persistent soil or the bank layer (RadiationSimulation.SoilAt).
            byte value = Encode(simulation.SoilAt(idx));
            if (value == 0) continue;
            // Floors at or above the terrain height (MapSize.TerrainSize.z) are
            // building tops: no terrain surface draws them, and the native map
            // has no layer for them.
            int z = columns[idx].Floor;
            if (z >= _depth) continue;
            if (value > _target[z]) _target[z] = value;
            any = true;
          }
          if (!any && !_hasData[p]) continue;
          bool cellData = false;
          for (int z = 0; z < _depth; z++) {
            byte target = _target[z];
            _target[z] = 0;
            var pixels = _pixels[z];
            byte r = pixels[2 * p], g = pixels[2 * p + 1];
            byte nr = r, ng = g;
            if (!_primed) { nr = ng = target; }
            else if (g != target) { nr = g; ng = target; }
            else if (r != g) nr = g;
            if (nr != r || ng != g) {
              _nonZero += (nr != 0 ? 1 : 0) - (r != 0 ? 1 : 0) + (ng != 0 ? 1 : 0) - (g != 0 ? 1 : 0);
              pixels[2 * p] = nr; pixels[2 * p + 1] = ng;
              _dirty[z] = true;
            }
            cellData |= nr != 0 || ng != 0;
          }
          _hasData[p] = cellData;
          rowData |= cellData;
        }
        if (rowData) withData.Include(y);
      }
      _rowsWithData = withData;
      _primed = true;
      for (int z = 0; z < _depth; z++) {
        if (!_dirty[z]) continue;
        RadiationShading.UploadLayer(_buffer, _pixels[z], _array, z);
        _dirty[z] = false;
      }
      bool keyword = _nonZero > 0;
      if (keyword != _keyword) { RadiationShading.SetKeyword(RadiationShading.SoilKeyword, keyword); _keyword = keyword; }
    }

    internal void Unload() {
      RadiationShading.SetKeyword(RadiationShading.SoilKeyword, false);
      RadiationShading.Destroy(_array); RadiationShading.Destroy(_buffer);
    }
  }
}
