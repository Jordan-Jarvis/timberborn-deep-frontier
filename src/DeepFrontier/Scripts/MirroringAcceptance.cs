using System;
using System.Linq;
using Bindito.Core;
using Timberborn.BlockSystem;
using Timberborn.Common;
using Timberborn.Coordinates;
using Timberborn.EntityNaming;
using Timberborn.EntitySystem;
using Timberborn.SingletonSystem;
using Timberborn.TemplateSystem;
using Timberborn.TimeSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  [Context("Game")]
  public sealed class MirroringAcceptanceConfigurator : Configurator {
    protected override void Configure() {
      if(Environment.GetCommandLineArgs().Contains("-deepFrontierMirrorAcceptance"))
        Bind<MirroringAcceptance>().AsSingleton();
    }
  }
  // Explicit disposable-fixture launch. These are native previews: no placed
  // entities or saved settlement objects are created or removed by this test.
  internal sealed class MirroringAcceptance : IPostLoadableSingleton,IUpdatableSingleton {
    private static readonly string[] Names={
      "CementKiln","ChemicalWorks","ConcreteBlock","ConcreteMixer","ConcreteOverhang8x1",
      "ConcreteOverflowDam","ConcreteScaffold3x3","CryogenicLiquefactionPlant","DeepDrill",
      "DeepMine","DeepProcessor","ElectrolysisPlant","FertilizerWorks","FishHatchery",
      "FisheryWorks","FoodPackagingWorks","Greenhouse","GroceryStore","Hospital","LaunchPad",
      "LimestoneMasonryBlock","LimestonePit","LimestoneQuarry","MaterialsLaboratory",
      "MissionControl","NuclearReactor","PrecisionMachineWorks","PublicHealthLab",
      "RadioactiveWasteRefinery","RadioactiveWasteVault","ReinforcedDamBlock",
      "ReinforcedHydroTurbine","Restaurant","RocketAssemblyHangar","SandstoneMasonryBlock",
      "SandstonePit","SandstoneQuarry","StoneCrusher","TechnicalSchool",
      "UraniumProcessingPlant","WaterTreatmentPlant",
      "SteelCantilever10x1","SteelCantilever12x1","SteelCantilever15x1","SteelBridge8x1",
      "SteelBridge15x1","SteelColumnH1","SteelColumnH6","SteelDeck3x3","SteelDeck5x5"
    };
    private static readonly Orientation[] Rotations={Orientation.Cw0,Orientation.Cw90,Orientation.Cw180,Orientation.Cw270};
    private readonly TemplateService _templates;
    private readonly BlockObjectFactory _factory;
    private readonly EntityRegistry _registry;
    private readonly SpeedManager _speed;
    private BlockObject _preview;
    private GameObject _root;
    private int _frame,_test,_probes;
    private bool _ready,_finished;
    public MirroringAcceptance(TemplateService templates,BlockObjectFactory factory,EntityRegistry registry,SpeedManager speed) {
      _templates=templates;_factory=factory;_registry=registry;_speed=speed;
    }
    public void PostLoad() {
      if(!_registry.Entities.Any(e=>e.HasComponent<NamedEntity>()&&e.GetComponent<NamedEntity>().EntityName=="Deep Frontier Acceptance Fixture"))
        throw new InvalidOperationException("Mirroring test requires the marked disposable settlement");
      _speed.ChangeSpeed(0);
      _root=new GameObject("DeepFrontier mirror preview acceptance");_ready=true;
    }
    public void UpdateSingleton() {
      if(!_ready||_finished)return;
      try {
        ++_frame;
        if(_frame%4==1) {
          string name=Names[_test/8]+".IronTeeth";
          var template=_templates.GetAll<TemplateSpec>().Single(t=>t.TemplateName==name);
          var spec=_templates.GetAll<BlockObjectSpec>().Single(s=>s.Blueprint==template.Blueprint);
          Require(spec.Flippable,"F mirroring disabled: "+name);
          var placement=new Placement(new Vector3Int(64,64,20),Rotations[(_test%8)/2],new FlipMode((_test%2)==1));
          _preview=_factory.CreateAsPreview(spec,_root.transform,placement);
        } else if(_frame%4==3) {
          var spec=_preview.GetComponent<BlockObjectSpec>();
          // Test each local cell center plus non-centered face/door-like points.
          foreach(var cell in _preview.Blocks.GetAllCoordinates()) {
            CheckPoint(new Vector3(cell.x+.5f,cell.y+.5f,cell.z+.5f),spec.BaseZ);
          }
          foreach(var point in new[]{new Vector3(0,.5f,0),new Vector3(spec.Size.x,.5f,0),
                    new Vector3(.5f,0,0),new Vector3(.5f,spec.Size.y,0),
                    new Vector3(.23f,.71f,spec.Size.z-.1f)})CheckPoint(point,spec.BaseZ);
          if(_preview.HasEntrance) {
            var expected=_preview.TransformCoordinates(spec.Entrance.Coordinates);
            Require(_preview.PositionedEntrance.Coordinates==expected,"Mirrored native entrance differs");
          }
          if((_test%8)==7)Debug.Log("[DeepFrontier Mirror] PASS "+Names[_test/8]+": native previews at four rotations, both flip states, all cell transforms and entrance");
          UnityEngine.Object.Destroy(_preview.GameObject);_preview=null;++_test;
          if(_test==Names.Length*8) {
            _finished=true;_speed.ChangeSpeed(0);UnityEngine.Object.Destroy(_root);
            Debug.Log("[DeepFrontier Mirror] ALL NATIVE PREVIEW CHECKS PASSED buildings="+Names.Length+", placements="+_test+", pointProbes="+_probes);
          }
        }
      } catch(Exception error) {
        _finished=true;_speed.ChangeSpeed(0);
        if(_root)UnityEngine.Object.Destroy(_root);
        Debug.LogError("[DeepFrontier Mirror] FAILED test="+_test+": "+error);
      }
    }
    private void CheckPoint(Vector3 localGrid,int baseZ) {
      var expected=CoordinateSystem.GridToWorld(_preview.TransformCoordinates(localGrid));
      var actual=_preview.Transform.TransformPoint(CoordinateSystem.GridToWorld(localGrid-new Vector3(0,0,baseZ)));
      Require(Vector3.Distance(expected,actual)<.0002f,"Visual/native grid mirror mismatch at "+localGrid+" expected "+expected+" got "+actual);
      ++_probes;
    }
    private static void Require(bool condition,string message) {if(!condition)throw new InvalidOperationException(message);}
  }
}
