using System;
using Timberborn.AssetSystem;
using Timberborn.BlueprintSystem;
using Timberborn.SingletonSystem;
using Timberborn.TerrainSystem;
using Timberborn.TickSystem;
using Timberborn.Timbermesh;
using Timberborn.WaterSystem;
using Timberborn.WaterSystemRendering;
using UnityEngine;

namespace DeepFrontier.Scripts.Radiation {
  // Radioactive water and irradiated ground through the native surfaces (see
  // RadiationShading): every water tile is drawn once, by the native water
  // mesh, whose colour blends clean, badwater and radioactive water by share;
  // irradiated soil is drawn by the native terrain material like badwater-
  // contaminated soil. No overlay meshes.
  //
  // Load verifies the native members (RadiationShading.Verify). PostLoad, when
  // every native singleton (material repository, terrain, specs) has loaded,
  // puts the Deep Frontier shader variants on the native water and terrain
  // materials; Unload restores the native shaders. The textures are updated in the late tick, after
  // RadiationSimulation.Tick (TickableSingletonService keeps the singleton
  // repository order, and the simulation is bound and created first), for the
  // rows that hold radiation plus rows still settling to zero; only changed
  // layers are uploaded, and nothing runs per frame. A loaded game starts
  // paused, so until the first tick a new simulation state (the applied save)
  // is also drawn from UpdateSingleton.
  public sealed class RadiationRenderer : ILoadableSingleton, IPostLoadableSingleton, ITickableSingleton, ILateTickable,
      IUnloadableSingleton, IUpdatableSingleton {
    private readonly RadiationSimulation _simulation;
    private readonly WaterSimulator _waterSimulator;
    private readonly ISpecService _specService;
    private readonly IAssetLoader _assetLoader;
    private readonly IMaterialRepository _materialRepository;
    private readonly ITerrainService _terrainService;
    private RadioactiveWaterSurface _water;
    private IrradiatedSoilSurface _soil;
    private int _lastVersion = -1;

    public RadiationRenderer(RadiationSimulation simulation, WaterSimulator waterSimulator, ISpecService specService,
        IAssetLoader assetLoader, IMaterialRepository materialRepository, ITerrainService terrainService) {
      _simulation = simulation; _waterSimulator = waterSimulator; _specService = specService;
      _assetLoader = assetLoader; _materialRepository = materialRepository; _terrainService = terrainService;
    }

    public void Load() => RadiationShading.Verify();

    public void PostLoad() {
      var spec = _specService.GetSingleSpec<WaterMeshSpec>();
      var opaqueVariant = _assetLoader.Load<Shader>(RadiationShading.WaterOpaqueVariant);
      var transparentVariant = _assetLoader.Load<Shader>(RadiationShading.WaterTransparentVariant);
      var terrainVariant = _assetLoader.Load<Shader>(RadiationShading.TerrainVariant);
      var terrain = Array.ConvertAll(RadiationShading.TerrainMaterials, _materialRepository.GetMaterial);
      _water = new RadioactiveWaterSurface(spec.OpaqueMaterial.Asset, spec.TransparentMaterial.Asset, opaqueVariant, transparentVariant);
      _soil = new IrradiatedSoilSurface(terrain, terrainVariant, _terrainService.Size);
    }

    public void Unload() {
      _water?.Unload();
      _soil?.Unload();
      _water = null; _soil = null;
    }

    public void Tick() => Refresh(settle: true);

    public void UpdateSingleton() {
      if (!_simulation.HasTicked) Refresh(settle: false);
    }

    // settle: also update while texture rows are still moving to their values
    // (old/new pairs are interpolated over one tick, so they settle per tick).
    private void Refresh(bool settle) {
      if (_water == null) throw new InvalidOperationException("Radiation renderer refreshed before PostLoad");
      if (_simulation.Layers == 0) return;
      if (_simulation.StateVersion == _lastVersion && !(settle && (_water.Pending || _soil.Pending))) return;
      _lastVersion = _simulation.StateVersion;
      _water.Update(_simulation, _waterSimulator.ColumnCounts, _waterSimulator.WaterColumns);
      _soil.Update(_simulation);
    }
  }
}
