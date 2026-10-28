using System;
using System.IO;
using System.Linq;
using Bindito.Core;
using Timberborn.BlockSystem;
using Timberborn.Buildings;
using Timberborn.CameraSystem;
using Timberborn.EntityNaming;
using Timberborn.EntitySystem;
using Timberborn.GameSaveRepositorySystem;
using Timberborn.GameSaveRuntimeSystem;
using Timberborn.Goods;
using Timberborn.SingletonSystem;
using Timberborn.TemplateSystem;
using Timberborn.TimeSystem;
using Timberborn.Workshops;
using UnityEngine;

namespace DeepFrontier.Scripts {
  [Context("Game")]
  public sealed class ReservoirAcceptanceConfigurator : Configurator {
    protected override void Configure() {
      if (Environment.GetCommandLineArgs().Contains("-deepFrontierReservoirAcceptance")
          || Environment.GetCommandLineArgs().Contains("-deepFrontierReservoirReload"))
        Bind<ReservoirAcceptance>().AsSingleton();
    }
  }

  // Public native inventories in the explicitly marked disposable fixture only.
  public sealed class ReservoirAcceptance : IPostLoadableSingleton, IUpdatableSingleton {
    private readonly EntityRegistry _registry;
    private readonly SpeedManager _speed;
    private readonly CameraService _camera;
    private readonly GameSaver _saver;
    private readonly GameLoader _loader;
    private BlockObject[] _quarries;
    private int _frame;
    private bool _failed;
    private bool _reload;
    public ReservoirAcceptance(EntityRegistry registry, SpeedManager speed, CameraService camera, GameSaver saver, GameLoader loader) {
      _registry=registry; _speed=speed; _camera=camera; _saver=saver; _loader=loader;
    }
    public void PostLoad() {
      if (!_registry.Entities.Any(e=>e.HasComponent<NamedEntity>() && e.GetComponent<NamedEntity>().EntityName=="Deep Frontier Acceptance Fixture"))
        throw new InvalidOperationException("Reservoir acceptance requires the marked disposable fixture.");
      _quarries=_registry.Entities.Where(e=>e.HasComponent<WorkshopReservoirSpec>()).Select(e=>e.GetComponent<BlockObject>()).ToArray();
      if (_quarries.Length!=2)throw new InvalidOperationException("Expected the two native quarry workshops.");
      _reload=Environment.GetCommandLineArgs().Contains("-deepFrontierReservoirReload");
      foreach (var quarry in _quarries) {
        var pausable=quarry.GetComponent<PausableBuilding>();
        if (_reload && !pausable.Paused)
          throw new InvalidOperationException("Reservoir persistence fixture must retain its saved production pause.");
        if (!_reload) pausable.Pause();
      }
    }
    public void UpdateSingleton() {
      if (_failed) return;
      ++_frame;
      try {
        if (_frame==260) {
          _speed.ChangeSpeed(0);
          _camera.MoveTargetTo(new Vector3(176.94f,4.75f,146.80f));
          _camera.SetZoomLevel(12,0); _camera.HorizontalAngle=0; _camera.VerticalAngle=50;
          if (_reload) {
            foreach(var quarry in _quarries)Verify(quarry,8,"save/reload");
            Debug.Log("[DeepFrontier Reservoir] RELOAD PASSED");
          } else SetStock(0,"empty");
        }
        if(_reload)return;
        if(_frame==290)Capture("quarry-water-empty");
        if(_frame==320)SetStock(8,"half-full");
        if(_frame==350)Capture("quarry-water-half");
        if(_frame==380)SetStock(16,"full");
        if(_frame==410)Capture("quarry-water-full");
        if(_frame==440)SetStock(0,"drained");
        if(_frame==470)Capture("quarry-water-drained");
        if(_frame==500)SetStock(8,"refilled");
        if(_frame==530)Capture("quarry-water-refilled");
        if(_frame==560)_saver.QueueSave(new SaveReference("Reservoir acceptance - verified",_loader.LoadedSave.SettlementReference),
          ()=>Debug.Log("[DeepFrontier Reservoir] SAVED VERIFIED WATER FIXTURE"));
      } catch(Exception e) { _failed=true; Debug.LogError("[DeepFrontier Reservoir] FAILED: "+e); }
    }
    private void SetStock(int amount,string label) {
      foreach(var quarry in _quarries) {
        var inventory=quarry.GetComponent<Manufactory>().Inventory;
        var old=inventory.AmountInStock("Water");
        if(old>0)inventory.TakeExisting(new GoodAmount("Water",old));
        if(amount>0)inventory.GiveExisting(new GoodAmount("Water",amount));
        Verify(quarry,amount,label);
      }
    }
    private static void Verify(BlockObject quarry,int amount,string label) {
      var spec=quarry.GetComponent<WorkshopReservoirSpec>();
      var visual=quarry.GetComponent<WorkshopReservoir>();
      var actualStock=quarry.GetComponent<Manufactory>().Inventory.AmountInStock("Water");
      if(spec.Capacity!=16 || visual.StoredAmount!=amount || visual.SurfacesVisible!=(amount>0))
        throw new InvalidOperationException($"Reservoir {quarry.GetComponent<TemplateSpec>().TemplateName} {label}: capacity={spec.Capacity}, actualStock={actualStock}, visualStock={visual.StoredAmount}, visible={visual.SurfacesVisible}, surfaceCount={visual.SurfaceHeights.Count}, expected={amount}");
      for(int i=0;i<spec.Surfaces.Length;i++) {
        var surface=spec.Surfaces[i];
        var expected=surface.EmptyHeight+(surface.FullHeight-surface.EmptyHeight)*amount/16f;
        if(Math.Abs(visual.SurfaceHeights[i]-expected)>.00001f)throw new InvalidOperationException("Reservoir height mismatch: "+label);
      }
      Debug.Log($"[DeepFrontier Reservoir] PASS {quarry.GetComponent<TemplateSpec>().TemplateName} {label}: water={amount}/16, visible={visual.SurfacesVisible}, localY={string.Join(",",visual.SurfaceHeights)}");
    }
    private static void Capture(string name) {
      var folder=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),"TimberbornModding/docs/art/reviews/2026-10-19-native-water");
      Directory.CreateDirectory(folder); ScreenCapture.CaptureScreenshot(Path.Combine(folder,name+".png"));
    }
  }
}
