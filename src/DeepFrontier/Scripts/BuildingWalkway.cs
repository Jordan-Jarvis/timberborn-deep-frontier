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
using Timberborn.Coordinates;
using Timberborn.Navigation;
using Timberborn.PathSystem;
using Timberborn.TemplateInstantiation;
using UnityEngine;

namespace DeepFrontier.Scripts {
  internal record WalkwayOpeningSpec {
    [Serialize] public string Id { get; init; }
    [Serialize] public Vector3Int Inside { get; init; }
    [Serialize] public Vector3Int Outside { get; init; }
    [Serialize] public Vector3 ApproachPosition { get; init; }
    [Serialize] public ImmutableArray<string> HiddenNodes { get; init; }
    [Serialize] public ImmutableArray<string> ShownNodes { get; init; }
  }

  internal record WalkwayWaypointSpec {
    [Serialize] public Vector3Int Cell { get; init; }
    [Serialize] public Vector3 Position { get; init; }
  }

  // Native navmesh specs author movement; this component gates boundary edges
  // and switches the corresponding rail meshes after native graph updates.
  internal record BuildingWalkwaySpec : ComponentSpec {
    [Serialize] public ImmutableArray<WalkwayOpeningSpec> Openings { get; init; }
    [Serialize] public ImmutableArray<WalkwayWaypointSpec> Waypoints { get; init; }
  }

  internal sealed class BuildingWalkway : BaseComponent, IAwakableComponent,
      IModelUpdater, IFinishedStateListener, IInstantNavMeshListener,
      IPrePlacementChangeListener, IPostPlacementChangeListener, IPathConnectionEnforcer {
    private readonly IBlockService _blocks;
    private readonly PreviewBlockService _previews;
    private readonly INavMeshService _navigation;
    private readonly INavMeshListenerEntityRegistry _listeners;
    private readonly INavMeshObjectFactory _meshFactory;
    private BlockObject _blockObject;
    private BuildingWalkwaySpec _spec;
    private readonly Dictionary<string, GameObject> _nodes = new Dictionary<string, GameObject>();
    private readonly HashSet<string> _hidden = new HashSet<string>();
    private bool _finished;
    private NavMeshObject _closedEdges;
    private readonly HashSet<string> _closed = new HashSet<string>();
    private readonly HashSet<string> _nowClosed = new HashSet<string>();
    private readonly HashSet<string> _shown = new HashSet<string>();
    private bool _gatesInstalled;
    private string[] _shownNames;
    private readonly HashSet<string> _appliedHidden = new HashSet<string>();
    private readonly HashSet<string> _appliedShown = new HashSet<string>();
    private bool _anyApplied;

    public BuildingWalkway(IBlockService blocks, PreviewBlockService previews,
        INavMeshService navigation,
        INavMeshListenerEntityRegistry listeners, INavMeshObjectFactory meshFactory) {
      _blocks = blocks;
      _previews = previews;
      _navigation = navigation;
      _listeners = listeners;
      _meshFactory = meshFactory;
    }

    public void Awake() {
      _blockObject = GetComponent<BlockObject>();
      _spec = GetComponent<BuildingWalkwaySpec>();
      _closedEdges = _meshFactory.Create();
      ValidateSpec();
      var transforms = GameObject.FindChildIfNameNotEmpty(GetComponent<BuildingModelSpec>().FinishedModelName)
          .GetComponentsInChildren<Transform>(true);
      foreach (var name in _spec.Openings.SelectMany(o => o.HiddenNodes.Concat(o.ShownNodes)).Distinct()) {
        var matches = transforms.Where(t => t.name == name).ToArray();
        if (matches.Length != 1)
          throw new InvalidOperationException($"Walkway requires exactly one finished-model node '{name}'; found {matches.Length}.");
        _nodes.Add(name, matches[0].gameObject);
      }
      _shownNames = _spec.Openings.SelectMany(o => o.ShownNodes).Distinct().ToArray();
    }

    public void OnEnterFinishedState() {
      if (_finished) throw new InvalidOperationException("Walkway entered finished state twice.");
      _finished = true;
      _listeners.RegisterInstantNavMeshListener(this);
      UpdateModel();
    }

    public void OnExitFinishedState() {
      if (!_finished) throw new InvalidOperationException("Walkway exited finished state without entering it.");
      _listeners.UnregisterInstantNavMeshListener(this);
      _finished = false;
      if (_gatesInstalled) {
        _closedEdges.EnqueueRemoveFromRegularNavMesh();
        _gatesInstalled = false;
        _closed.Clear();
      }
      UpdateModel();
    }

    public void OnPrePlacementChanged() {
      if (_gatesInstalled) {
        _closedEdges.EnqueueRemoveFromRegularNavMesh();
        _gatesInstalled = false;
        _closed.Clear();
      }
    }
    public void OnPostPlacementChanged() { UpdateModel(); }

    public void OnInstantNavMeshUpdated(NavMeshUpdate update) {
      // State comparisons prevent repeated mutations when our queued gate change
      // produces a second native graph notification. No per-frame scanning.
      UpdateModel();
    }

    public void UpdateModel() {
      _hidden.Clear();
      _shown.Clear();
      if (_finished && _blockObject.Positioned) {
        var closed = _nowClosed;
        closed.Clear();
        foreach (var opening in _spec.Openings) {
          var inside = _blockObject.TransformCoordinates(opening.Inside);
          var outside = _blockObject.TransformCoordinates(opening.Outside);
          bool neighbor = HasFinishedNeighbor(inside, outside);
          if (!neighbor) closed.Add(opening.Id);
          if (neighbor
              && _navigation.AreConnectedInstant(inside, outside)
              && _navigation.AreConnectedInstant(outside, inside)) {
            _hidden.UnionWith(opening.HiddenNodes);
            _shown.UnionWith(opening.ShownNodes);
          }
        }
        if (!_gatesInstalled || !_closed.SetEquals(closed)) {
          if (_gatesInstalled) _closedEdges.EnqueueRemoveFromRegularNavMesh();
          _closedEdges.Reset();
          foreach (var opening in _spec.Openings) {
            if (!closed.Contains(opening.Id)) continue;
            var a = _blockObject.TransformCoordinates(opening.Inside);
            var b = _blockObject.TransformCoordinates(opening.Outside);
            _closedEdges.BlockEdge(NavMeshEdge.CreateBlocking(a, b, 0));
            _closedEdges.BlockEdge(NavMeshEdge.CreateBlocking(b, a, 0));
          }
          _closed.Clear(); _closed.UnionWith(closed);
          _closedEdges.EnqueueAddToRegularNavMesh();
          _gatesInstalled = true;
        }
      }
      // Native PreviewPlacer calls UpdateModel every frame while placing;
      // node states are rewritten only when they change.
      if (_anyApplied && _appliedHidden.SetEquals(_hidden) && _appliedShown.SetEquals(_shown)) return;
      foreach (var node in _nodes) node.Value.SetActive(!_hidden.Contains(node.Key));
      foreach (var name in _shownNames) _nodes[name].SetActive(_shown.Contains(name));
      _appliedHidden.Clear(); _appliedHidden.UnionWith(_hidden);
      _appliedShown.Clear(); _appliedShown.UnionWith(_shown);
      _anyApplied = true;
    }

    public bool CanConnectPath(Vector3Int origin, Vector3Int target) {
      // The native path modeller queries both orientations. Preview orientation
      // may change, but real rail openings require completed neighbors above.
      if (!_blockObject.Positioned) return false;
      foreach (var opening in _spec.Openings) {
        var inside = _blockObject.TransformCoordinates(opening.Inside);
        var outside = _blockObject.TransformCoordinates(opening.Outside);
        if ((origin == inside && target == outside) || (origin == outside && target == inside)) {
          return HasPathEdge(_blocks.GetPathObjectAt(outside), outside, inside, false)
              || HasPathEdge(_previews.GetPathObjectAt(outside), outside, inside, false)
              || HasMatchingWalkway(inside, outside, false);
        }
      }
      return false;
    }

    private bool HasFinishedNeighbor(Vector3Int inside, Vector3Int outside) {
      return HasPathEdge(_blocks.GetPathObjectAt(outside), outside, inside, true)
          || HasMatchingWalkway(inside, outside, true);
    }

    private static bool HasPathEdge(BlockObject path, Vector3Int from, Vector3Int to, bool finishedOnly) {
      if (!path || (finishedOnly && !path.IsFinished) || !path.HasComponent<PathSpec>()) return false;
      // Native instant changes also affect the preview graph. Inspect the
      // neighbor's authored edge instead of querying a graph our gate blocks.
      // TransformCoordinates includes the neighbor's actual rotation/flip.
      var settings = path.GetComponent<BlockObjectNavMeshSettingsSpec>();
      foreach (var group in settings.EdgeGroups) {
        if (!group.IsPath || group.UseGroup) continue;
        foreach (var edge in group.AddedEdges) {
          var start = path.TransformCoordinates(edge.Start);
          var end = path.TransformCoordinates(edge.End);
          if ((start == from && end == to) || (edge.IsTwoWay && start == to && end == from)) return true;
        }
      }
      return false;
    }

    public bool TryGetWaypoint(Vector3Int worldCell, out Vector3 point) {
      if (_finished) foreach (var waypoint in _spec.Waypoints) {
        if (_blockObject.TransformCoordinates(waypoint.Cell) == worldCell) {
          point = Transform.TransformPoint(waypoint.Position);
          return true;
        }
      }
      point = default;
      return false;
    }

    public bool TryGetApproach(Vector3Int inside, Vector3Int outside, out Vector3 point) {
      foreach(var opening in _spec.Openings) {
        if(_blockObject.TransformCoordinates(opening.Inside)==inside && _blockObject.TransformCoordinates(opening.Outside)==outside) {
          point=Transform.TransformPoint(opening.ApproachPosition);
          return true;
        }
      }
      point=default;
      return false;
    }

    private bool HasMatchingWalkway(Vector3Int inside, Vector3Int outside, bool finishedOnly) {
      foreach (var other in _blocks.GetObjectsWithComponentAt<BuildingWalkway>(outside)) {
        if (other != this && (!finishedOnly || other._blockObject.IsFinished)
            && other.HasPort(outside, inside)) return true;
      }
      if (!finishedOnly) {
        foreach (var other in _previews.GetObjectsWithComponentAt<BuildingWalkway>(outside)) {
          if (other != this && other.HasPort(outside, inside)) return true;
        }
      }
      return false;
    }

    private bool HasPort(Vector3Int inside, Vector3Int outside) {
      return _spec.Openings.Any(o => _blockObject.TransformCoordinates(o.Inside) == inside
          && _blockObject.TransformCoordinates(o.Outside) == outside);
    }

    private void ValidateSpec() {
      if (_spec.Openings.IsDefaultOrEmpty)
        throw new InvalidOperationException("BuildingWalkwaySpec requires explicit openings.");
      var ids = new HashSet<string>();
      var edges = new HashSet<(Vector3Int, Vector3Int)>();
      var size = GetComponent<BlockObjectSpec>().Size;
      foreach (var o in _spec.Openings) {
        var delta = o.Outside - o.Inside;
        if (string.IsNullOrWhiteSpace(o.Id) || !ids.Add(o.Id)
            || !edges.Add((o.Inside, o.Outside)))
          throw new InvalidOperationException("Walkway opening IDs and edges must be unique.");
        if (delta.z != 0 || Math.Abs(delta.x) + Math.Abs(delta.y) != 1)
          throw new InvalidOperationException($"Walkway '{o.Id}' must connect adjacent cells at the same elevation.");
        if (o.Inside.x < 0 || o.Inside.y < 0 || o.Inside.z < 0
            || o.Inside.x >= size.x || o.Inside.y >= size.y || o.Inside.z >= size.z)
          throw new InvalidOperationException($"Walkway '{o.Id}' starts outside its building volume.");
        if (o.HiddenNodes.IsDefaultOrEmpty || o.HiddenNodes.Any(string.IsNullOrWhiteSpace)
            || o.HiddenNodes.Distinct().Count() != o.HiddenNodes.Length)
          throw new InvalidOperationException($"Walkway '{o.Id}' requires explicit, unique panel and post nodes.");
      }
      if (_spec.Waypoints.IsDefaultOrEmpty || _spec.Waypoints.Select(w => w.Cell).Distinct().Count() != _spec.Waypoints.Length)
        throw new InvalidOperationException("Walkways require unique, explicitly authored waypoint cells.");
    }
  }

  // Public native extension point: the game's pathfinder chooses the route;
  // this maps its corners onto the existing stair treads and deck corridors.
  internal sealed class BuildingWalkwayPathTransformer : IPathTransformer {
    private readonly IBlockService _blocks;
    public BuildingWalkwayPathTransformer(IBlockService blocks) { _blocks = blocks; }
    public bool Transform(ref int index, ReadOnlyList<FlowFieldPathNode> path, List<PathCorner> corners) {
      var node = path[index];
      var cell = NavigationCoordinateSystem.WorldToGridInt(node.Position);
      foreach (var walkway in _blocks.GetObjectsWithComponentAt<BuildingWalkway>(cell)) {
        if (walkway.TryGetWaypoint(cell, out var point)) {
          if(index>0 && walkway.TryGetApproach(cell,NavigationCoordinateSystem.WorldToGridInt(path[index-1].Position),out var incoming) && incoming!=point)
            corners.Add(new PathCorner(incoming,node.NormalizedSpeed,node.GroupId));
          corners.Add(new PathCorner(point, node.NormalizedSpeed, node.GroupId));
          if(index+1<path.Count && walkway.TryGetApproach(cell,NavigationCoordinateSystem.WorldToGridInt(path[index+1].Position),out var outgoing) && outgoing!=point)
            corners.Add(new PathCorner(outgoing,node.NormalizedSpeed,node.GroupId));
          ++index;
          return true;
        }
      }
      return false;
    }
  }

  [Context("Game")]
  public sealed class BuildingWalkwayConfigurator : Configurator {
    protected override void Configure() {
      Bind<BuildingWalkway>().AsTransient();
      MultiBind<IPathTransformer>().To<BuildingWalkwayPathTransformer>().AsSingleton();
      MultiBind<TemplateModule>().ToProvider(ProvideTemplateModule).AsSingleton();
    }

    private static TemplateModule ProvideTemplateModule() {
      var builder = new TemplateModule.Builder();
      builder.AddDecorator<BuildingWalkwaySpec, BuildingWalkway>();
      return builder.Build();
    }
  }
}
