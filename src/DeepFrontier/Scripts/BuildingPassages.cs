#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Bindito.Core;
using HarmonyLib;
using Timberborn.Attractions;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockSystem;
using Timberborn.BuildingRange;
using Timberborn.Buildings;
using Timberborn.Coordinates;
using Timberborn.CoreUI;
using Timberborn.DistributionSystem;
using Timberborn.DwellingSystem;
using Timberborn.EntitySystem;
using Timberborn.GameDistricts;
using Timberborn.Navigation;
using Timberborn.SingletonSystem;
using Timberborn.Stockpiles;
using Timberborn.UILayoutSystem;
using Timberborn.WorkSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Buildings that touch share their insides: beavers walk in one building's
  // door, through both buildings' cells, and out of the other's door, so a
  // building is reachable through any building it touches, stacked or side by
  // side (this replaces the Hooman Stairs mod, which links stacked buildings
  // only; BuildingPassagesHoomanStairs turns this off while it is enabled).
  //
  // A passage between two finished buildings (homes, workplaces, storage and
  // attractions; not district centres or crossings) of one district joins
  // their doorsteps by a unit-step path found breadth-first through the cells
  // both occupy, plus each building's own entrance <-> doorstep step. Its
  // steps are native nav-mesh edges in their own group ("DeepFrontierPassages"),
  // which the NavMeshSource.Block/UnblockEdge prefixes never let a building's
  // native blocking close, and its nodes are not district obstacles
  // (DistrictObstacleService.IsSetObstacle postfix). A building with a passage
  // is reached at its doorstep (Accessible.SetAccesses prefix) and its doorstep
  // flow fields are cached, as native entrances are; with none left it gets
  // its native access back. Nav-mesh edges are a list, so a step two passages
  // share is added and removed once per passage.
  internal sealed class Passage {
    public BlockObject A, B;
    public List<Vector3Int> Path;
    public readonly List<NavMeshEdge> Edges = new();
    public bool Joins(BlockObject building) => A == building || B == building;
    public BlockObject Other(BlockObject building) => A == building ? B : A;
  }

  internal sealed class BuildingPassages : IPostLoadableSingleton {
    private const string GroupName = "DeepFrontierPassages";
    private static readonly Vector3Int[] Steps = {
      Vector3Int.up, Vector3Int.down, Vector3Int.left, Vector3Int.right, new(0, 0, 1), new(0, 0, -1) };
    // Read by the Harmony patches below and by SaveInspectionProbe.
    internal static int GroupId = -1;
    internal static readonly Dictionary<int, int> Nodes = new();
    internal static readonly Dictionary<BlockObject, int> Linked = new();
    internal static readonly List<Passage> Passages = new();
    private static Func<Vector3Int, int> _nodeId;
    private static Func<Vector3Int, bool> _inNavMesh;
    private static readonly Action<BuildingAccessible> EnableNativeAccesses = AccessTools.MethodDelegate<Action<BuildingAccessible>>(
      AccessTools.Method(typeof(BuildingAccessible), "EnableAccesses") ?? throw new InvalidOperationException("BuildingAccessible.EnableAccesses changed"));

    private readonly IBlockService _blocks;
    private readonly EventBus _events;
    private readonly EntityComponentRegistry _registry;
    private readonly INavMeshService _navMesh;
    private readonly INavigationCachingService _caching;
    private readonly NavMeshGroupService _groups;
    private bool _ready;

    public BuildingPassages(IBlockService blocks, EventBus events, EntityComponentRegistry registry, INavMeshService navMesh,
        INavigationCachingService caching, NavMeshGroupService groups) {
      _blocks = blocks; _events = events; _registry = registry; _navMesh = navMesh; _caching = caching; _groups = groups;
    }

    public void PostLoad() {
      Passages.Clear(); Nodes.Clear(); Linked.Clear();
      GroupId = _groups.GetOrAddGroupId(GroupName);
      // Native node ids (internal NodeIdService, held by NavMeshService).
      var service = _navMesh.GetType().GetField("_nodeIdService", BindingFlags.Instance | BindingFlags.NonPublic)?.GetValue(_navMesh)
        ?? throw new InvalidOperationException("NavMeshService._nodeIdService changed");
      _nodeId = (Func<Vector3Int, int>)Delegate.CreateDelegate(typeof(Func<Vector3Int, int>), service,
        service.GetType().GetMethod("GridToId", new[] { typeof(Vector3Int) }) ?? throw new InvalidOperationException("NodeIdService.GridToId changed"));
      _inNavMesh = (Func<Vector3Int, bool>)Delegate.CreateDelegate(typeof(Func<Vector3Int, bool>), service,
        service.GetType().GetMethod("Contains", new[] { typeof(Vector3Int) }) ?? throw new InvalidOperationException("NodeIdService.Contains changed"));
      _events.Register(this);
    }

    // Every building is in place once the game shows its UI; from then on each
    // finished or removed building updates its own passages.
    [OnEvent]
    public void OnShowPrimaryUI(ShowPrimaryUIEvent _) {
      _ready = true;
      foreach (var building in _registry.GetEnabled<Building>().Select(b => b.GetComponent<BlockObject>()).Where(b => b && b.IsFinished).ToList())
        Link(building);
    }
    [OnEvent]
    public void OnFinished(EnteredFinishedStateEvent e) { if (_ready) Link(e.BlockObject); }
    [OnEvent]
    public void OnUnfinished(ExitedFinishedStateEvent e) => Unlink(e.BlockObject);

    private static bool Linkable(BlockObject b) =>
      b && b.IsFinished && b.PositionedEntrance != null && !b.HasComponent<DistrictCenter>() && !b.HasComponent<DistrictCrossing>()
      && (b.HasComponent<Dwelling>() || b.HasComponent<Workplace>() || b.HasComponent<Stockpile>() || b.HasComponent<Attraction>());

    private static bool SameDistrict(BlockObject a, BlockObject b) {
      var da = a.GetComponent<DistrictBuilding>()?.District;
      var db = b.GetComponent<DistrictBuilding>()?.District;
      return da == null || db == null || da == db;
    }

    private void Link(BlockObject building) {
      if (!Linkable(building)) return;
      var cells = building.PositionedBlocks.GetOccupiedCoordinates().ToHashSet();
      var touching = new HashSet<BlockObject>();
      foreach (var cell in cells)
        foreach (var step in Steps) {
          var next = cell + step;
          if (cells.Contains(next)) continue;
          foreach (var other in _blocks.GetObjectsAt(next))
            if (other != building && Linkable(other) && SameDistrict(building, other)) touching.Add(other);
        }
      foreach (var other in touching)
        if (!Passages.Any(p => p.Joins(building) && p.Joins(other))) Connect(building, other, cells);
    }

    private void Connect(BlockObject a, BlockObject b, HashSet<Vector3Int> aCells) {
      var area = new HashSet<Vector3Int>(aCells);
      area.UnionWith(b.PositionedBlocks.GetOccupiedCoordinates());
      var start = a.PositionedEntrance.DoorstepCoordinates;
      var target = b.PositionedEntrance.DoorstepCoordinates;
      var path = Route(start, target, area);
      if (path == null) return;
      var passage = new Passage { A = a, B = b, Path = path };
      for (int i = 0; i < path.Count - 1; i++) Edge(passage, path[i], path[i + 1]);
      Edge(passage, a.PositionedEntrance.Coordinates, start);
      Edge(passage, b.PositionedEntrance.Coordinates, target);
      foreach (var node in path.Append(a.PositionedEntrance.Coordinates).Append(b.PositionedEntrance.Coordinates))
        if (_inNavMesh(node)) { int id = _nodeId(node); Nodes[id] = Nodes.GetValueOrDefault(id) + 1; }
      Passages.Add(passage);
      Enter(a); Enter(b);
    }

    // Cheaper than a native step (1): NavMeshSourceNode.IsConnectedTo keeps only the
    // cheapest unblocked edge between two nodes, and a tie with a native non-road edge
    // dropped the road link (54 of 86 doorsteps unreachable at cost 1, build 201).
    // Hooman Stairs' costs: 0.6 one way, 0.8 back.
    private void Edge(Passage passage, Vector3Int from, Vector3Int to) {
      foreach (var edge in new[] { NavMeshEdge.CreateGrouped(from, to, GroupId, true, 0.6f), NavMeshEdge.CreateGrouped(to, from, GroupId, true, 0.8f) }) {
        _navMesh.AddEdge(edge); passage.Edges.Add(edge);
      }
    }

    // A building's first passage moves its access to its doorstep.
    private void Enter(BlockObject building) {
      int count = Linked.GetValueOrDefault(building);
      Linked[building] = count + 1;
      if (count > 0) return;
      var doorstep = building.PositionedEntrance.DoorstepCoordinates;
      building.GetComponent<BuildingAccessible>().Accessible.SetAccesses(new[] { CoordinateSystem.GridToWorldCentered(doorstep) });
      _caching.StartCachingRoadFlowField(doorstep);
      if (building.HasComponent<BuildingWithTerrainRange>()) _caching.StartCachingTerrainFlowField(doorstep);
    }

    private void Unlink(BlockObject building) {
      foreach (var passage in Passages.Where(p => p.Joins(building)).ToList()) {
        foreach (var edge in passage.Edges) _navMesh.RemoveEdge(edge);
        foreach (var node in passage.Path.Append(passage.A.PositionedEntrance.Coordinates).Append(passage.B.PositionedEntrance.Coordinates))
          if (_inNavMesh(node)) {
            int id = _nodeId(node);
            if (--Nodes[id] == 0) Nodes.Remove(id);
          }
        Passages.Remove(passage);
        Leave(passage.A); Leave(passage.B);
      }
    }

    // With its last passage gone a building gets its native access back.
    private void Leave(BlockObject building) {
      if (--Linked[building] > 0) return;
      Linked.Remove(building);
      var doorstep = building.PositionedEntrance.DoorstepCoordinates;
      _caching.StopCachingRoadFlowField(doorstep);
      if (building.HasComponent<BuildingWithTerrainRange>()) _caching.StopCachingTerrainFlowField(doorstep);
      if (building.IsFinished) EnableNativeAccesses(building.GetComponent<BuildingAccessible>());
    }

    // Breadth-first, unit steps (6 directions), through the cells of both buildings.
    private static List<Vector3Int> Route(Vector3Int start, Vector3Int target, HashSet<Vector3Int> area) {
      area.Add(start); area.Add(target);
      var came = new Dictionary<Vector3Int, Vector3Int> { [start] = start };
      var queue = new Queue<Vector3Int>(); queue.Enqueue(start);
      while (queue.Count > 0) {
        var cell = queue.Dequeue();
        if (cell == target) break;
        foreach (var step in Steps) {
          var next = cell + step;
          if (area.Contains(next) && !came.ContainsKey(next)) { came[next] = cell; queue.Enqueue(next); }
        }
      }
      if (!came.ContainsKey(target)) return null;
      var route = new List<Vector3Int>();
      for (var c = target; c != start; c = came[c]) route.Add(c);
      route.Add(start); route.Reverse();
      return route;
    }
  }

  // Passage steps are never blocked by a building's native nav-mesh blocking.
  [HarmonyPatch]
  internal static class PassageEdgeBlocking {
    private static IEnumerable<MethodBase> TargetMethods() {
      var source = AccessTools.TypeByName("Timberborn.Navigation.NavMeshSource") ?? throw new InvalidOperationException("NavMeshSource changed");
      yield return AccessTools.Method(source, "BlockEdge", new[] { typeof(int), typeof(int), typeof(int) }) ?? throw new InvalidOperationException("NavMeshSource.BlockEdge changed");
      yield return AccessTools.Method(source, "UnblockEdge", new[] { typeof(int), typeof(int), typeof(int) }) ?? throw new InvalidOperationException("NavMeshSource.UnblockEdge changed");
    }
    private static bool Prefix(int groupId) => groupId != BuildingPassages.GroupId || BuildingPassages.GroupId < 0;
  }

  // Passage nodes are inside buildings, which are district obstacles.
  [HarmonyPatch]
  internal static class PassageObstacles {
    private static MethodBase TargetMethod() {
      var service = AccessTools.TypeByName("Timberborn.Navigation.DistrictObstacleService") ?? throw new InvalidOperationException("DistrictObstacleService changed");
      return AccessTools.Method(service, "IsSetObstacle", new[] { typeof(int) }) ?? throw new InvalidOperationException("DistrictObstacleService.IsSetObstacle changed");
    }
    private static void Postfix(int nodeId, ref bool __result) { if (__result && BuildingPassages.Nodes.ContainsKey(nodeId)) __result = false; }
  }

  // A linked building is reached at its doorstep, through its passages.
  [HarmonyPatch(typeof(Accessible), nameof(Accessible.SetAccesses))]
  internal static class PassageAccess {
    private static void Prefix(Accessible __instance, ref IEnumerable<Vector3> accesses) {
      var building = __instance.GetComponent<BlockObject>();
      if (building && BuildingPassages.Linked.ContainsKey(building))
        accesses = new[] { CoordinateSystem.GridToWorldCentered(building.PositionedEntrance.DoorstepCoordinates) };
    }
  }

  // Hooman Stairs (Calloatti.HoomanStairs) links stacked buildings its own way;
  // the two would link the same buildings twice. While it is enabled Deep
  // Frontier's passages stay off and the main menu says so.
  internal static class BuildingPassagesHoomanStairs {
    internal static bool Enabled => AppDomain.CurrentDomain.GetAssemblies().Any(a => a.GetName().Name == "hoomanstairs");
    internal const string Message =
      "Deep Frontier is incompatible with Hooman Stairs.\n\nDeep Frontier now links touching buildings itself, stacked and side by side, so beavers walk through one building to reach the next. With Hooman Stairs enabled the two would link the same buildings twice, so Deep Frontier's building links are off.\n\nDisable Hooman Stairs in the Mods screen to use Deep Frontier's building links.";
  }

  internal static class BuildingPassagesPatches {
    // Called once per process from DeepFrontierModStarter.
    internal static void Apply() {
      var harmony = new Harmony("DeepFrontier.BuildingPassages");
      harmony.CreateClassProcessor(typeof(PassageEdgeBlocking)).Patch();
      harmony.CreateClassProcessor(typeof(PassageObstacles)).Patch();
      harmony.CreateClassProcessor(typeof(PassageAccess)).Patch();
    }
  }

  [Context("Game")]
  public sealed class BuildingPassagesConfigurator : Configurator {
    protected override void Configure() {
      if (BuildingPassagesHoomanStairs.Enabled) {
        Debug.LogWarning("[DeepFrontier] Hooman Stairs is enabled: Deep Frontier's building links are off (incompatible).");
        return;
      }
      Bind<BuildingPassages>().AsSingleton();
    }
  }

  internal sealed class HoomanStairsNotice : IPostLoadableSingleton {
    private readonly DialogBoxShower _dialogs;
    public HoomanStairsNotice(DialogBoxShower dialogs) { _dialogs = dialogs; }
    public void PostLoad() => _dialogs.Create().SetMessage(BuildingPassagesHoomanStairs.Message).Show();
  }

  [Context("MainMenu")]
  public sealed class HoomanStairsNoticeConfigurator : Configurator {
    protected override void Configure() {
      if (BuildingPassagesHoomanStairs.Enabled) Bind<HoomanStairsNotice>().AsSingleton();
    }
  }
}
#endif
