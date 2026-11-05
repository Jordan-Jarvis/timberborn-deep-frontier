#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Bindito.Core;
using Timberborn.BlockSystem;
using Timberborn.Buildings;
using Timberborn.ConstructionSites;
using Timberborn.Coordinates;
using Timberborn.EntitySystem;
using Timberborn.GameDistricts;
using Timberborn.Navigation;
using Timberborn.SingletonSystem;
using Timberborn.TemplateSystem;
using Timberborn.TimeSystem;
using Timberborn.TubeSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  [Context("Game")]
  public sealed class BuildingPassagesAcceptanceConfigurator : Configurator {
    protected override void Configure() {
      if (Environment.GetCommandLineArgs().Contains("-deepFrontierPassageAcceptance"))
        Bind<BuildingPassagesAcceptance>().AsSingleton();
    }
  }

  // Explicit disposable copy only. Uses native deletion, construction, road
  // searches and district assignment. Never saves the modified fixture.
  internal sealed class BuildingPassagesAcceptance : IPostLoadableSingleton, IUpdatableSingleton {
    private const string Tag = "[DeepFrontier Passages] ";
    private readonly EntityRegistry _entities;
    private readonly EntityService _entityService;
    private readonly BlockObjectFactory _factory;
    private readonly TemplateService _templates;
    private readonly BlockValidator _validator;
    private readonly INavigationService _navigation;
    private readonly INavMeshService _navMesh;
    private readonly SpeedManager _speed;
    private readonly List<Passage> _surviving = new();
    private BlockObject _plant;
    private int _frame, _count;
    private Dictionary<BlockObject, int> _linked;
    private Dictionary<int, int> _unlinkedNodes;
    private Placement _placement;

    public BuildingPassagesAcceptance(EntityRegistry entities, EntityService entityService, BlockObjectFactory factory,
        TemplateService templates, BlockValidator validator, INavigationService navigation, INavMeshService navMesh, SpeedManager speed) {
      _entities=entities; _entityService=entityService; _factory=factory; _templates=templates;
      _validator=validator; _navigation=navigation; _navMesh=navMesh; _speed=speed;
    }

    public void PostLoad() {
      Require(Path.GetFileName(MemoryLoadProbe.SavePath()) == "passage-reconnect-repro-copy.timber",
        "Passage acceptance requires the explicitly named disposable save copy");
      Require(!Environment.GetCommandLineArgs().Contains(MemoryLoadProbe.SaveAsFlag), "Passage acceptance never saves its mutations");
    }
    private static void Require(bool condition, string message) {
      if (!condition) throw new InvalidOperationException(Tag + message);
    }
    private BlockObject Find(string id, Vector3Int position) => _entities.Entities
      .Where(e=>e.GetComponent<TemplateSpec>()?.TemplateName==id)
      .Select(e=>e.GetComponent<BlockObject>()).Single(b=>b.Coordinates==position);
    private bool Road(Vector3Int from, Vector3Int to) => _navigation.FindInstantRoadPath(
      NavigationCoordinateSystem.GridToWorld(from), NavigationCoordinateSystem.GridToWorld(to), out _);
    private void CheckSurvivors(string phase) {
      // FindInstantRoadPath is limited to the starting node's district. Deleting
      // the only connecting building correctly isolates the chain; its local
      // road edges must survive even while no district can reach those nodes.
      var broken=_surviving.Where(p=>!BuildingPassages.Passages.Contains(p)||
        p.Edges.Any(e=>!_navMesh.AreConnectedRoadInstant(e.Start,e.End))).ToList();
      foreach (var p in broken) {
        Debug.Log(Tag+phase+": broken "+p.A.Name+" at "+p.A.Coordinates+" -> "+p.B.Name+" at "+p.B.Coordinates+
          "; registered="+BuildingPassages.Passages.Contains(p));
        foreach (var edge in p.Edges.Where(e=>!_navMesh.AreConnectedRoadInstant(e.Start,e.End)))
          Debug.Log(Tag+"missing road edge "+edge.Start+" -> "+edge.End+"; terrain="+_navMesh.AreConnectedInstant(edge.Start,edge.End));
      }
      Require(broken.Count==0,phase+" broke "+broken.Count+" surviving passages");
    }

    private void CheckChain(string phase) {
      var drill=Find("DeepDrill.IronTeeth",new Vector3Int(82,96,5));
      var lab=Find("MaterialsLaboratory.IronTeeth",new Vector3Int(90,99,5));
      foreach(var b in new[]{_plant,drill,lab}) {
        Require(BuildingPassages.Linked.ContainsKey(b), phase+": missing passage for "+b.Name);
        var district=b.GetComponent<DistrictBuilding>();
        Require(district.District && district.InstantDistrict,phase+": no district for "+b.Name);
        var centre=district.District.GetComponent<BlockObject>().PositionedEntrance.Coordinates;
        Require(Road(centre,b.PositionedEntrance.DoorstepCoordinates),phase+": no road from district to "+b.Name);
        Require(b.GetComponent<BuildingAccessible>().Accessible.UnblockedSingleAccess.HasValue,
          phase+": blocked access for "+b.Name);
      }
      Require(BuildingPassages.Passages.Any(p=>p.Joins(_plant)&&p.Joins(drill)),phase+": missing plant-to-drill link");
      Debug.Log(Tag+"PASS "+phase+": workerless plant, drill and laboratory linked, unblocked and assigned to district");
    }

    public void UpdateSingleton() {
      ++_frame;
      if (_frame==300) {
        Require(!BuildingPassages.Linked.Keys.Any(b=>b.HasComponent<TubeStationSpec>()),
          "Tubeway station ports must retain their native transport routes");
        _plant=Find("CoalPowerPlant.IronTeeth",new Vector3Int(80,92,5));
        CheckChain("loaded replacement layout");
        _count=BuildingPassages.Passages.Count;
        _linked=new Dictionary<BlockObject,int>(BuildingPassages.Linked);
        _surviving.AddRange(BuildingPassages.Passages.Where(p=>!p.Joins(_plant)));
        CheckSurvivors("Loaded layout");
        _placement=new Placement(_plant.Coordinates,_plant.Orientation,_plant.FlipMode);
        _entityService.Delete(_plant.GetComponent<EntityComponent>());
      }
      if (_frame==420) {
        Require(!BuildingPassages.Linked.ContainsKey(_plant),"Deleted plant still registered");
        Require(!BuildingPassages.Passages.Any(p=>p.Joins(_plant)),"Deleted plant still has passages");
        CheckSurvivors("Deletion");
        Debug.Log(Tag+"PASS deletion removed plant links and retained "+_surviving.Count+" walkable surviving passages");
        _unlinkedNodes=new Dictionary<int,int>(BuildingPassages.Nodes);
        var template=_templates.GetAll<TemplateSpec>().Single(t=>t.TemplateName=="CoalPowerPlant.IronTeeth");
        Require(_validator.BlocksValid(template.Blueprint.GetSpec<BlockObjectSpec>(),_placement),"Replacement placement invalid");
        _linked.Remove(_plant);
        _plant=_factory.CreateFinished(new EntitySetup.Builder(template.Blueprint).AddInitComponent(new FinishedConstructionSiteInit()),_placement);
      }
      if (_frame==600) {
        CheckChain("rebuilt without reload");
        Require(BuildingPassages.Passages.Count==_count,"Rebuild changed total passage count");
        Require(_linked.All(p=>BuildingPassages.Linked.TryGetValue(p.Key,out var n)&&n==p.Value),"Rebuild changed surviving link counts");
        CheckSurvivors("Rebuild");
        _entityService.Delete(_plant.GetComponent<EntityComponent>());
      }
      if (_frame==720) {
        // Rebuilding can choose another valid shortest route. Its deletion must
        // still return every shared node to the state before that rebuild.
        Require(BuildingPassages.Nodes.Count==_unlinkedNodes.Count &&
          _unlinkedNodes.All(p=>BuildingPassages.Nodes.TryGetValue(p.Key,out var n)&&n==p.Value),
          "Second deletion leaked or over-released passage node references");
        CheckSurvivors("Second deletion");
        var template=_templates.GetAll<TemplateSpec>().Single(t=>t.TemplateName=="CoalPowerPlant.IronTeeth");
        Require(_validator.BlocksValid(template.Blueprint.GetSpec<BlockObjectSpec>(),_placement),"Second replacement placement invalid");
        _plant=_factory.CreateFinished(new EntitySetup.Builder(template.Blueprint).AddInitComponent(new FinishedConstructionSiteInit()),_placement);
      }
      if (_frame==900) {
        CheckChain("second rebuild without reload");
        Require(BuildingPassages.Passages.Count==_count,"Second rebuild leaked passages");
        Debug.Log(Tag+"COMPLETE native removal/rebuild and district reconnection passed; original save untouched");
        _speed.ChangeSpeed(0);
      }
    }
  }
}
#endif
