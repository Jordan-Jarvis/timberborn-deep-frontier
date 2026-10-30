using System;
using System.Linq;
using Bindito.Core;
using Timberborn.BlueprintSystem;
using Timberborn.GameSaveRepositorySystem;
using Timberborn.GameSceneLoading;
using Timberborn.MapRepositorySystem;
using Timberborn.SingletonSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Explicit test launch only. Uses the same native save loader as the menu.
  [Context("MainMenu")]
  public sealed class IndustrialAcceptanceLoaderConfigurator : Configurator {
    protected override void Configure() {
      if(Environment.GetCommandLineArgs().Contains("-deepFrontierLoadAcceptance"))
        Bind<IndustrialAcceptanceLoader>().AsSingleton();
    }
  }
  public sealed class IndustrialAcceptanceLoader : IUpdatableSingleton {
    private readonly GameSaveRepository _saves;
    private readonly GameSceneLoader _loader;
    private readonly MapRepository _maps;
    private readonly ISpecService _specs;
    private int _frame;
    public IndustrialAcceptanceLoader(GameSaveRepository saves,GameSceneLoader loader,MapRepository maps,ISpecService specs) {
      _saves=saves;_loader=loader;_maps=maps;_specs=specs;
    }
    public void UpdateSingleton() {
      if(++_frame!=30)return;
      var args=Environment.GetCommandLineArgs();
      if(SceneCycleAcceptance.Active) {
        SceneCycleAcceptance.MainMenu(_specs,_saves,_loader,_maps);
        return;
      }
      if(MemoryLoadProbe.SavePath()is string path) {
        var named=MemoryLoadProbe.Find(_saves,path);
        Debug.Log("[DeepFrontier Acceptance] Loading named save through native GameSceneLoader: "+named);
        _loader.StartSaveGame(named);
        return;
      }
      if(MemoryLoadProbe.NewGameMap()is string map) {
        var reference=MemoryLoadProbe.Map(_maps,map);
        Debug.Log("[DeepFrontier Acceptance] Starting an Iron Teeth new game through native GameSceneLoader on "+reference);
        _loader.StartNewGameInstantly("IronTeeth",reference,MemoryLoadProbe.TestSettlement);
        return;
      }
      var saveName=args.Contains("-deepFrontierLategameRocketPreparing")?"Lategame rocket - preparing":
        args.Contains("-deepFrontierLategameRocketFlight")?"Lategame rocket - flight":
        args.Contains("-deepFrontierLategameRocketRefurbishing")?"Lategame rocket - refurbishing":
        args.Contains("-deepFrontierLategameRocket")?"Lategame acceptance - main":
        args.Contains("-deepFrontierLategameReload")?"Lategame acceptance - main":
        args.Contains("-deepFrontierLategame")?"Reservoir acceptance - verified":
        args.Contains("-deepFrontierStructuresReload")?"Structures - verified":
        args.Contains("-deepFrontierResearchReload")?"Research acceptance - verified":
        args.Contains("-deepFrontierResearch")?"Reservoir acceptance - verified":
        args.Contains("-deepFrontierHydroBasins")?"Mineral pits continuity - verified":
        args.Contains("-deepFrontierHydroReload")?"Hydro turbine - verified":
        args.Contains("-deepFrontierHydro")?"Mineral pits continuity - verified":
        args.Contains("-deepFrontierHydroProbe")?"Mineral pits continuity - verified":
        args.Contains("-deepFrontierStructures")?"Mineral pits continuity - verified":
        args.Contains("-deepFrontierMineralReload")?"Mineral pits - verified":
        args.Contains("-deepFrontierMineralAcceptance")?"Reservoir acceptance - verified":
        args.Contains("-deepFrontierFactoryPowerLinesReload")?"Factory power lines - verified":
        args.Contains("-deepFrontierFactoryPowerLines")?"Factory transport - verified":
        args.Contains("-deepFrontierFactoryTransportReload")?"Factory transport - verified":
        args.Contains("-deepFrontierFactoryTransport")?"Mixer acceptance - verified":
        args.Contains("-deepFrontierMixerReload")?"Mixer acceptance - verified":
        args.Contains("-deepFrontierMixerAcceptance")?"Reservoir acceptance - verified":
        args.Contains("-deepFrontierAquaculturePipesReload")?"Aquaculture pipes - verified":
        args.Contains("-deepFrontierAquaculturePipes")?"Hatchery acceptance - verified":
        args.Contains("-deepFrontierGroceryBeltsReload")?"Grocery belts - verified":
        args.Contains("-deepFrontierGroceryBelts")?"Grocery acceptance - verified":
        args.Contains("-deepFrontierGroceryReload")?"Grocery acceptance - verified":
        args.Contains("-deepFrontierGroceryAcceptance")?"Reservoir acceptance - verified":
        args.Contains("-deepFrontierHospitalReload")?"Hospital acceptance - verified":
        args.Contains("-deepFrontierHospitalAcceptance")?"Reservoir acceptance - verified":
        args.Contains("-deepFrontierAquacultureContinuity")?"Hatchery acceptance - verified":
        args.Contains("-deepFrontierAquacultureBootstrap")?"Reservoir acceptance - verified":
        args.Contains("-deepFrontierHatcheryAcceptance")?"Fishery acceptance - verified":
        args.Contains("-deepFrontierFisheryReload")?"Fishery acceptance - verified":
        args.Contains("-deepFrontierFisheryAcceptance")?"Reservoir acceptance - verified":
        args.Contains("-deepFrontierRestaurantReload")?"Restaurant acceptance - verified":
        args.Contains("-deepFrontierRestaurantAcceptance")?"Reservoir acceptance - verified":
        args.Contains("-deepFrontierReservoirReload")?"Reservoir acceptance - verified":
        args.Contains("-deepFrontierWalkwayReload")?"Industrial acceptance - verified":"Industrial acceptance - initial";
      var save=_saves.GetAllSaves().Single(s=>s.SettlementReference.SettlementName=="Industrial Acceptance"&&s.SaveName==saveName);
      Debug.Log("[DeepFrontier Acceptance] Loading exact fixture through native GameSceneLoader: "+save);
      _loader.StartSaveGame(save);
    }
  }
}
