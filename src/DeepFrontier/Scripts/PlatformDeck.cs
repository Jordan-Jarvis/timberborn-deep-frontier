using System;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.Linq;
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockObjectModelSystem;
using Timberborn.BlockSystem;
using Timberborn.BlockSystemNavigation;
using Timberborn.BlueprintSystem;
using Timberborn.Buildings;
using Timberborn.Common;
using Timberborn.Navigation;
using Timberborn.PathSystem;
using Timberborn.TemplateInstantiation;
using UnityEngine;

namespace DeepFrontier.Scripts {
  internal record DeckDoorSpec {
    [Serialize] public Vector3Int Interior { get; init; }
    [Serialize] public Vector3Int Exterior { get; init; }
  }
  internal record PlatformDeckSpec : ComponentSpec {
    [Serialize] public ImmutableArray<WalkwayOpeningSpec> Openings { get; init; }
    [Serialize] public ImmutableArray<DeckDoorSpec> Doors { get; init; }
  }

  // The native platform supplies floor/support; native player Path entities own
  // all outdoor road edges. Rails are decorative: this component changes only
  // their visibility, never adding blockers or modifying outdoor navigation.
  internal sealed class PlatformDeck : BaseComponent, IAwakableComponent,
      IModelUpdater, IFinishedStateListener, IInstantNavMeshListener,
      IPrePlacementChangeListener, IPostPlacementChangeListener, IPathConnectionEnforcer {
    private readonly IBlockService _blocks;
    private readonly PreviewBlockService _previews;
    private readonly INavMeshService _nav;
    private readonly INavMeshListenerEntityRegistry _listeners;
    private BlockObject _building;
    private PlatformDeckSpec _spec;
    private bool _finished;
    private readonly Dictionary<string,GameObject> _nodes=new();
    public PlatformDeck(IBlockService blocks,PreviewBlockService previews,INavMeshService nav,
        INavMeshListenerEntityRegistry listeners) {
      _blocks=blocks;_previews=previews;_nav=nav;_listeners=listeners;
    }
    public void Awake() {
      _building=GetComponent<BlockObject>();_spec=GetComponent<PlatformDeckSpec>();
      if(_spec.Openings.IsDefaultOrEmpty||_spec.Doors.IsDefaultOrEmpty)
        throw new InvalidOperationException("Platform deck requires explicit rails and interior doors.");
      if(_spec.Openings.Select(o=>o.Id).Distinct().Count()!=_spec.Openings.Length)
        throw new InvalidOperationException("Duplicate platform rail IDs.");
      foreach(var o in _spec.Openings) {
        var delta=o.Outside-o.Inside;
        if(delta.z!=0||Math.Abs(delta.x)+Math.Abs(delta.y)!=1||o.HiddenNodes.IsDefaultOrEmpty||!o.ShownNodes.IsEmpty)
          throw new InvalidOperationException("Platform rails require adjacent cells and existing deck geometry: "+o.Id);
      }
      var transforms=GameObject.FindChildIfNameNotEmpty(GetComponent<BuildingModelSpec>().FinishedModelName).GetComponentsInChildren<Transform>(true);
      foreach(var name in _spec.Openings.SelectMany(o=>o.HiddenNodes).Distinct()) {
        var matches=transforms.Where(t=>t.name==name).ToArray();
        if(matches.Length!=1)throw new InvalidOperationException("Platform railing node must exist exactly once: "+name);
        _nodes.Add(name,matches[0].gameObject);
      }
    }
    public void OnEnterFinishedState() {
      if(_finished)throw new InvalidOperationException("Duplicate platform finish.");
      _finished=true;_listeners.RegisterInstantNavMeshListener(this);UpdateModel();
    }
    public void OnExitFinishedState() {
      _listeners.UnregisterInstantNavMeshListener(this);_finished=false;UpdateModel();
    }
    public void OnPrePlacementChanged() { }
    public void OnPostPlacementChanged() {UpdateModel();}
    public void OnInstantNavMeshUpdated(NavMeshUpdate update) {UpdateModel();}
    // Native PreviewPlacer calls UpdateModel every frame while placing; the
    // node states are rewritten only when the hidden set actually changes.
    private readonly HashSet<string> _hidden=new();
    private readonly HashSet<string> _applied=new();
    private bool _anyApplied;
    public void UpdateModel() {
      var hidden=_hidden;hidden.Clear();
      if(_finished&&_building.Positioned) {
        foreach(var o in _spec.Openings) {
          var a=_building.TransformCoordinates(o.Inside);var b=_building.TransformCoordinates(o.Outside);
          bool paths=HasPathEdge(_blocks.GetPathObjectAt(a),a,b,true)&&HasPathEdge(_blocks.GetPathObjectAt(b),b,a,true);
          if(paths&&_nav.AreConnectedInstant(a,b)&&_nav.AreConnectedInstant(b,a))hidden.UnionWith(o.HiddenNodes);
        }
      }
      if(_anyApplied&&_applied.SetEquals(hidden))return;
      foreach(var pair in _nodes)pair.Value.SetActive(!hidden.Contains(pair.Key));
      _applied.Clear();_applied.UnionWith(hidden);_anyApplied=true;
    }
    // Only enclosed door cells need the native connection-enforcer extension.
    // Ordinary paths on a deck already connect to other native Path entities.
    public bool CanConnectPath(Vector3Int origin,Vector3Int target) {
      if(!_building.Positioned)return false;
      foreach(var door in _spec.Doors) {
        var inside=_building.TransformCoordinates(door.Interior);var outside=_building.TransformCoordinates(door.Exterior);
        if((origin==inside&&target==outside)||(origin==outside&&target==inside))
          return HasPathEdge(_blocks.GetPathObjectAt(outside),outside,inside,false)
              ||HasPathEdge(_previews.GetPathObjectAt(outside),outside,inside,false);
      }
      return false;
    }
    private static bool HasPathEdge(BlockObject path,Vector3Int from,Vector3Int to,bool finished) {
      if(!path||(finished&&!path.IsFinished)||!path.HasComponent<PathSpec>())return false;
      foreach(var group in path.GetComponent<BlockObjectNavMeshSettingsSpec>().EdgeGroups) {
        if(!group.IsPath||group.UseGroup)continue;
        foreach(var edge in group.AddedEdges) {
          var a=path.TransformCoordinates(edge.Start);var b=path.TransformCoordinates(edge.End);
          if((a==from&&b==to)||(edge.IsTwoWay&&a==to&&b==from))return true;
        }
      }
      return false;
    }
  }
  [Context("Game")]
  public sealed class PlatformDeckConfigurator : Configurator {
    protected override void Configure() {
      Bind<PlatformDeck>().AsTransient();MultiBind<TemplateModule>().ToProvider(Module).AsSingleton();
    }
    private static TemplateModule Module() {
      var builder=new TemplateModule.Builder();builder.AddDecorator<PlatformDeckSpec,PlatformDeck>();return builder.Build();
    }
  }
}
