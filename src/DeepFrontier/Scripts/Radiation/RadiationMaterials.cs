using System;
using Timberborn.AssetSystem;
using Timberborn.SingletonSystem;
using UnityEngine;
using Object = UnityEngine.Object;

namespace DeepFrontier.Scripts.Radiation {
  // The radiation colours. The Radioactive Spring marker is a runtime copy of
  // the mod's bundled URP Lit material DFIndustrial18 (authored with the
  // _EMISSION variant), so it keeps a faint glow at night. Radioactive water
  // and irradiated ground have no material of their own: the native water and
  // terrain materials draw them (RadiationShading) with the colours below.
  // Bound in Game and MapEditor.
  public sealed class RadiationMaterials : ILoadableSingleton, IUnloadableSingleton {
    private const string BaseMaterialPath = "Materials/DeepFrontierIndustrial/DFIndustrial18";
    // The radiation yellow (zombie tint; the bright radioactive water colour).
    internal static readonly Color WaterTintColor = new Color(0.86f, 0.92f, 0.08f, 1f);
    internal static readonly Color SpringColor = new Color(0.80f, 0.87f, 0.10f, 1f);
    internal static readonly Color SpringEmission = new Color(0.42f, 0.52f, 0.02f, 1f);
    // Radioactive water, in place of the native badwater colours of the native
    // WaterContamination subgraph (native: base A 0.02 grey, B rust 0.5/0.12/0.04;
    // detail A/B orange 0.85/0.56/0.33): base colours are the albedo pattern,
    // detail colours the emissive glow, at about the native glow luminance.
    internal static readonly Color WaterBaseColorA = new Color(0.50f, 0.56f, 0.04f, 0f);
    internal static readonly Color WaterBaseColorB = new Color(WaterTintColor.r, WaterTintColor.g, WaterTintColor.b, 0f);
    internal static readonly Color WaterDetailColorA = new Color(0.55f, 0.68f, 0.12f, 0f);
    internal static readonly Color WaterDetailColorB = new Color(0.62f, 0.72f, 0.16f, 0f);
    // Irradiated ground: the native soil contamination texture
    // (Environment/Land/Materials/SoilContamination, 1.1.2.8; its opaque veins
    // average NativeSoilVeinColor in sRGB) tinted so the veins show SoilVeinColor.
    internal static readonly Color SoilVeinColor = new Color(0.66f, 0.74f, 0.12f, 1f);
    internal static readonly Color NativeSoilVeinColor = new Color(0.306f, 0.130f, 0.020f, 1f);

    private readonly IAssetLoader _assetLoader;
    private Material _spring;
    // Created on first use: block-object previews and templates can Awake
    // before this singleton's Load (build 125 left the Radioactive Spring
    // preview with null materials, which the native highlighter dereferenced).
    public Material Spring { get { EnsureCreated(); return _spring; } }

    public RadiationMaterials(IAssetLoader assetLoader) { _assetLoader = assetLoader; }

    public void Load() => EnsureCreated();

    private void EnsureCreated() {
      if (_spring != null) return;
      var baseMaterial = _assetLoader.Load<Material>(BaseMaterialPath);
      if (baseMaterial == null) throw new InvalidOperationException($"Radiation base material is missing: {BaseMaterialPath}");
      _spring = Create(baseMaterial, "DeepFrontierRadioactiveSpring", SpringColor, SpringEmission, 0.75f);
    }

    public void Unload() {
      if (_spring != null) Object.Destroy(_spring);
      _spring = null;
    }

    private static Material Create(Material source, string name, Color color, Color emission, float smoothness) {
      var material = new Material(source) { name = name };
      material.SetTexture("_BaseMap", Texture2D.whiteTexture);
      material.SetColor("_BaseColor", color);
      material.SetFloat("_Metallic", 0f);
      material.SetFloat("_Smoothness", smoothness);
      material.EnableKeyword("_EMISSION");
      material.SetTexture("_EmissionMap", Texture2D.whiteTexture);
      material.SetColor("_EmissionColor", emission);
      return material;
    }
  }
}
