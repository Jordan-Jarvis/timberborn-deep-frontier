#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Security.Cryptography;
using Bindito.Core;
using HarmonyLib;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockObjectTools;
using Timberborn.BlockSystem;
using Timberborn.Coordinates;
using Timberborn.ModManagerScene;
using Timberborn.Navigation;
using Timberborn.SingletonSystem;
using Timberborn.TemplateInstantiation;
using UnityEngine;

namespace DeepFrontier.Scripts.PreviewNavMesh {
  // Extension gap (Timberborn 1.1.2.8, decompiled): while a building tool is
  // active, AreaSelectionController calls PreviewPlacer.ShowPreviews every
  // frame. Its PopulateBuildablePreviewsAndAddToBlockServices removes every
  // preview from the preview services and adds the valid ones back, and
  // BlockObjectPreviewNavMesh.AddToPreviewService answers each add with
  //   RemoveFromPreviewService(); RecalculateNavMeshObject(); AddToPreviewNavMesh();
  // so a preview that has not moved still rebuilds its whole NavMeshObject
  // (NavMeshObjectUpdater.Update: blocked wall edges for every bottom-occupied
  // block, times every nav group) and applies its removing and adding change
  // lists to the preview navmesh twice, notifying every preview navmesh
  // listener. The Nuclear Reactor has 2,543 occupied blocks (8,065 wall edges
  // per group, 4 groups); vanilla Smelter 24. Placed buildings build theirs once.
  //
  // 1. Cache (exactly equivalent). NavMeshObjectUpdater.Update reads only the
  //    preview's own BlockObject (PositionedBlocks, Entrance, PositionedEntrance:
  //    functions of its Placement and its template), its
  //    BlockObjectNavMeshSettingsSpec (template) and NavMeshGroupService group
  //    ids (append-only). It reads no terrain, no other block object, no path
  //    and no preview state. The lists are rebuilt only when the placement or
  //    the group count differs from the last rebuild of that preview.
  // 2. Kept application. Inside PopulateBuildablePreviewsAndAddToBlockServices of
  //    a single-preview placer, the native remove of an applied preview is held
  //    as pending. The following add of the same preview at the same cached
  //    placement cancels it: the identical lists stay applied once. A pending
  //    removal is applied for real before a different list is added, and for
  //    every still-pending preview when Populate returns or throws (Finalizer).
  //    Outside Populate nothing is held, so every caller that
  //    removes previews before placing or hiding them (GetBuildableCoordinates,
  //    HideAllPreviews, HideAndRemoveFromServices, tool exit) gets the native
  //    immediate removal. Previews with any other IPreviewServiceMember
  //    (district centres and obstacles) are never held.
  // 3. Deferred while moving (measured: moving the Reactor rebuilt and
  //    re-applied 8,065 x 4 edges every frame). A held preview whose placement
  //    differs from its applied list keeps that list applied (or, if none is
  //    applied, stays without one) until it has rested RestSeconds at one
  //    placement; then the old list is removed, the new one built and added.
  //    Only the preview navmesh lags; its readers are the preview's own
  //    unreachable/range feedback (ReachabilityPreviewValidator is an
  //    IPreviewValidator: warning colour and text only), BoundsNavRangeDrawing,
  //    district preview maps (district previews are never held) and
  //    BuildingModelUpdater model refreshes. Placement never reads it:
  //    BlockObjectTool.Place -> PreviewPlacer.GetBuildableCoordinates ->
  //    PreviewsAreValid -> BlockObjectValidationService (IBlockObjectValidators,
  //    none of which reads the preview navmesh), then RemovePreviewsFromServices
  //    outside Populate removes whatever list is applied before the building
  //    is created; the placed building builds its own regular navmesh object.
  //    PreviewPlacer (whole type, iterators included) is IL-verified for this.
  // Balance: every application goes through ApplyAdd/ApplyRemove, which require
  // the native _addedToPreviewNavMesh flag to flip and a per-preview counter to
  // stay equal to it (0 or 1); a kept list must still have the length it had
  // when added. Any mismatch throws.
  //
  // The IL of every native method this relies on is hashed at mod start and
  // compared with 1.1.2.8; a changed method throws instead of patching.
  internal static class PreviewNavMeshCache {
    private sealed class State {
      public BaseComponent Owner;
      public NavMeshObject Nav;
      public object BlockNavMesh;
      public BlockObject Block;
      public bool Deferrable;
      public int Epoch=-1;
      public bool HasKey;
      public Placement Key;
      public int Groups;
      public int AddingCount;
      public bool Pending;
      public int Balance;
      public bool HasDesired;
      public Placement Desired;
      public float DesiredSince;
    }

    private static readonly ConditionalWeakTable<BaseComponent,State> States=new();
    private static readonly List<State> PendingStates=new();
    private static Type _previewNavMeshType;
    private static FieldInfo _blockObjectNavMesh;
    private static PropertyInfo _navMeshObject;
    private static MethodInfo _recalculate;
    private static AccessTools.FieldRef<NavMeshObject,bool> _added;
    private static AccessTools.FieldRef<NavMeshObject,List<NavMeshChangeSpecification>> _addingChanges;
    private static AccessTools.FieldRef<PreviewPlacer,Lazy<Preview[]>> _placerPreviews;
    private static NavMeshGroupService _groups;
    private static bool _deferring;
    private static int _epoch;
    private static bool _enabled=true;

    public static long Rebuilds,CachedLists,KeptApplied,DeferredMoves,AppliedAdds,AppliedRemoves;
    // A held preview whose placement changed keeps its previous list applied
    // until it has rested this long at one placement (see the header, part 3).
    internal const float RestSeconds=0.2f;

    // 1.1.2.8 IL (System.Reflection.Metadata MethodBodyBlock.GetILBytes, SHA-256).
    private static readonly (string Type,string Method,string Sha256)[] NativeIl={
      ("Timberborn.BlockSystemNavigation.BlockObjectPreviewNavMesh","AddToPreviewService","8862c9c1b1d8bf9453aac1910cc2d0afab6b1f29c6a55183589614783992515d"),
      ("Timberborn.BlockSystemNavigation.BlockObjectPreviewNavMesh","RemoveFromPreviewService","1c263418cb63099b1e6aef56704889445d7d075d99c984cc997d0ea7fac2696d"),
      ("Timberborn.BlockSystemNavigation.BlockObjectNavMesh","RecalculateNavMeshObject","7d0e98c31e397190152fc15737b53285d34b247f68c592a3d41a6ad174b01152"),
      ("Timberborn.BlockObjectTools.PreviewPlacer","PopulateBuildablePreviewsAndAddToBlockServices","4720e9a4d154eb72d0ed32e3a4ae5e5016c50bd707e3b1697b36f1bc61e2d031"),
      ("Timberborn.BlockObjectTools.PreviewPlacer","RemovePreviewsFromServices","18c81eb7bb2d3ff5e8d47800ecb60e4ae78602d19b882b622d2ef163b1cd8a7e"),
      ("Timberborn.BlockSystem.Preview","RemoveFromPreviewServices","8de16a706551578325285afad5d91e79594488b877ee5ddb249c8535794a9fb2"),
      ("Timberborn.BlockSystem.Preview","AddToPreviewServices","270cdb92665a393b1ac6f1004f44385641266582d1140c5666c1b6f0ff03303f"),
      ("Timberborn.Navigation.NavMeshObject","AddToPreviewNavMesh","23be39e11bffe1e8ecd0a617e97931feb2e0349a1190a90e2f32183d9c227506"),
      ("Timberborn.Navigation.NavMeshObject","RemoveFromPreviewNavMesh","928191e8d49049e62e40ebdc6a09b3008c1b66b186eef80e83af78c3586bed17"),
    };
    // Every method of NavMeshObjectUpdater: the purity of Update is what makes
    // the cache equivalent, so any change to any of them disables the patch.
    private static readonly string[] UpdaterIl={
      "Update 4a8de9bdcdec27b92db342e72d84eecf8ff97136a3c8309107e9e85263121b03",
      "AddManuallySetEdges 484d0b880a23a0580b6b0fdf79425035f6e0cdeef9f7eccf1de4fd186c7f8a55",
      "GetManuallySetEdge ba437ab702dc5714dee8ee9b0b1621fcfceb03fc48752422221e2984d878fee1",
      "AddEdgesAddedByStackable d93443b790c9772ef695e21f0d9b41482bc8d201fb2c3b47fe3ec23a5d85c146",
      "AddUnblockedEdges 4d575aae752052411f5cb0ce01d37582eb2ddd0106f08de1021696f069adb88b",
      "AddBlockedEdges 8ff0494f92d87bbcd086e85dfa3576a9afd4bba8237914abbacc628cf2dd1565",
      "AddBlockedEdges 2919f032ef08be46462064818c536ef3da363ca61a1c47727f90f43f3dcdf136",
      "AddEdgesBlockedByElevatedEntrance bfed41573500693b6b400a0e3b1fdaba29d1667d5526d3d1beb5a5c1fef0b5b0",
      "AddEdgesBlockedByCoordinates 2b9f601f25f60cc53524c34a1abbf15f54967bf9339b515c893f2cbe252787a2",
      "AddBlockedEdgesToNeighbors d92574cd624a307a66c0de124dc91a1165cd672bc31c927b1a5b0c31f5624942",
      "AddEdgesBlockedByWalls d157284efc04c04f60b52cefe52b3a72c116a0772c88980ddded2c88119edc48",
      "GetEntranceEdge 24d8ef9ba9b8552008bd120dcbf63d047d92b05e34ab25a0be491a6bba330698",
      "AddEdgesBlockedByWall 69612b03428954a36d8065a841ba36beefcb1a590da30be06878e025badccd46",
      "AddEdgesBlockedByWall 406c04d3d83dc14511c80b4f75b8c145f09cbacf4baefe58ea61fd6c06a3a591",
      "CanAddBlockingEdge dc3e2fa202b8ab8d0b2d333e203cf47966818be442f2e1876613996358dce643",
    };

    public static void Patch() {
      Require(Type.GetType("Timberborn.Navigation.NavMeshObject, Timberborn.Navigation")==typeof(NavMeshObject),"NavMeshObject moved");
      foreach(var (type,method,sha) in NativeIl) {
        var actual=Il(Method(Resolve(type),method));
        Require(actual==sha,$"{type}.{method} differs from 1.1.2.8 (IL {actual}); the preview navmesh patch must be re-verified");
      }
      // Part 3 relies on the whole placer (placing path included).
      var placer=PreviewAccessCache.TypeDigest(typeof(PreviewPlacer));
      Require(placer=="7985147405c2e08fc9357108fee823750a9f1242a30c75a222318fc4fd344a21","PreviewPlacer differs from 1.1.2.8 (IL digest "+placer+")");
      var updater=Resolve("Timberborn.BlockSystemNavigation.NavMeshObjectUpdater");
      var methods=updater.GetMethods(BindingFlags.Instance|BindingFlags.Static|BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.DeclaredOnly)
        .Where(m=>m.GetMethodBody()!=null).Select(m=>m.Name+" "+Il(m)).OrderBy(s=>s,StringComparer.Ordinal).ToArray();
      Require(methods.SequenceEqual(UpdaterIl.OrderBy(s=>s,StringComparer.Ordinal)),"NavMeshObjectUpdater differs from 1.1.2.8: "+string.Join(", ",methods));

      _previewNavMeshType=Resolve("Timberborn.BlockSystemNavigation.BlockObjectPreviewNavMesh");
      var blockNavMeshType=Resolve("Timberborn.BlockSystemNavigation.BlockObjectNavMesh");
      _blockObjectNavMesh=AccessTools.Field(_previewNavMeshType,"_blockObjectNavMesh");
      Require(_blockObjectNavMesh!=null&&_blockObjectNavMesh.FieldType==blockNavMeshType,"BlockObjectPreviewNavMesh._blockObjectNavMesh changed");
      _navMeshObject=AccessTools.Property(blockNavMeshType,"NavMeshObject");
      Require(_navMeshObject!=null&&_navMeshObject.PropertyType==typeof(NavMeshObject),"BlockObjectNavMesh.NavMeshObject changed");
      _recalculate=Method(blockNavMeshType,"RecalculateNavMeshObject");
      _added=AccessTools.FieldRefAccess<NavMeshObject,bool>("_addedToPreviewNavMesh");
      _addingChanges=AccessTools.FieldRefAccess<NavMeshObject,List<NavMeshChangeSpecification>>("_addingChanges");
      _placerPreviews=AccessTools.FieldRefAccess<PreviewPlacer,Lazy<Preview[]>>("_previews");

      var harmony=new Harmony("DeepFrontier.PreviewNavMesh");
      harmony.Patch(Method(_previewNavMeshType,"AddToPreviewService"),prefix:new HarmonyMethod(typeof(PreviewNavMeshCache),nameof(AddPrefix)));
      harmony.Patch(Method(_previewNavMeshType,"RemoveFromPreviewService"),prefix:new HarmonyMethod(typeof(PreviewNavMeshCache),nameof(RemovePrefix)));
      harmony.Patch(Method(typeof(PreviewPlacer),"PopulateBuildablePreviewsAndAddToBlockServices"),
        prefix:new HarmonyMethod(typeof(PreviewNavMeshCache),nameof(PopulatePrefix)),
        finalizer:new HarmonyMethod(typeof(PreviewNavMeshCache),nameof(PopulateFinalizer)));
    }

    internal static void Load(NavMeshGroupService groups) {_groups=groups;}
    internal static void Unload() {
      Require(PendingStates.Count==0&&!_deferring,"Preview navmesh removals still pending at unload");
      _groups=null;
    }

    // Measurement only (PreviewCostAcceptance): run the native path instead.
    // Allowed only while nothing is pending; cached lists are forgotten.
    internal static void SetEnabledForMeasurement(bool enabled) {
      Require(PendingStates.Count==0&&!_deferring,"Cannot switch the preview navmesh cache while removals are pending");
      _enabled=enabled;_epoch++;
      PreviewAccessCache.SetEnabledForMeasurement(enabled);
    }

    private static bool AddPrefix(BaseComponent __instance) {
      if(!_enabled)return true;
      var state=StateOf(__instance);
      if(state.Nav==null)return true; // before Awake: native null-tolerant path
      var placement=state.Block.Placement;
      bool sameList=state.HasKey&&state.Block.Positioned&&state.Key.Equals(placement)&&state.Groups==GroupCount();
      if(state.Pending) {
        Unpend(state);
        if(sameList) {
          Require(Added(state)&&state.Balance==1,"Held preview list is no longer applied");
          Require(_addingChanges(state.Nav).Count==state.AddingCount,"Held preview list changed while applied");
          state.HasDesired=false;
          KeptApplied++;CachedLists++;
          return false;
        }
        if(Moving(state,placement)) {
          // Part 3: the previous list stays applied, unchanged, while moving.
          Require(Added(state)&&state.Balance==1,"Held preview list is no longer applied");
          Require(_addingChanges(state.Nav).Count==state.AddingCount,"Held preview list changed while applied");
          DeferredMoves++;
          return false;
        }
        ApplyRemove(state);
      } else if(Added(state)) {
        ApplyRemove(state); // native: RemoveFromPreviewService() first
      } else if(!sameList&&_deferring&&state.Deferrable&&Moving(state,placement)) {
        DeferredMoves++; // nothing applied yet; the list is added once at rest
        return false;
      }
      state.HasDesired=false;
      if(sameList) {
        Require(_addingChanges(state.Nav).Count==state.AddingCount,"Cached preview list changed outside the cache");
        CachedLists++;
      } else {
        Require(!Added(state),"Rebuilding a preview list while it is applied");
        _recalculate.Invoke(state.BlockNavMesh,null);
        state.HasKey=state.Block.Positioned;state.Key=placement;state.Groups=GroupCount();
        state.AddingCount=_addingChanges(state.Nav).Count;
        Rebuilds++;
      }
      ApplyAdd(state);
      return false;
    }

    // True while the held preview has not yet rested RestSeconds at placement.
    private static bool Moving(State state,Placement placement) {
      float now=Time.unscaledTime;
      if(!state.HasDesired||!state.Desired.Equals(placement)) {
        state.HasDesired=true;state.Desired=placement;state.DesiredSince=now;
      }
      return now-state.DesiredSince<RestSeconds;
    }

    private static bool RemovePrefix(BaseComponent __instance) {
      if(!_enabled)return true;
      var state=StateOf(__instance);
      if(state.Nav==null)return true;
      if(state.Pending)return false; // already held in this Populate
      if(_deferring&&state.Deferrable&&Added(state)) {
        state.Pending=true;PendingStates.Add(state);
        return false;
      }
      if(Added(state))ApplyRemove(state);
      return false;
    }

    private static void PopulatePrefix(PreviewPlacer __instance) {
      Require(!_deferring&&PendingStates.Count==0,"Nested preview population");
      _deferring=_enabled&&_placerPreviews(__instance).Value.Length==1;
    }

    private static Exception PopulateFinalizer(Exception __exception) {
      _deferring=false;
      while(PendingStates.Count>0) {
        var state=PendingStates[PendingStates.Count-1];
        Unpend(state);ApplyRemove(state);
      }
      return __exception;
    }

    private static void ApplyAdd(State state) {
      Require(!Added(state)&&state.Balance==0,"Preview navmesh add while applied");
      state.Nav.AddToPreviewNavMesh();
      Require(Added(state),"Native AddToPreviewNavMesh did not apply");
      state.Balance=1;AppliedAdds++;
    }

    private static void ApplyRemove(State state) {
      Require(Added(state)&&state.Balance==1,"Preview navmesh remove without a matching add");
      state.Nav.RemoveFromPreviewNavMesh();
      Require(!Added(state),"Native RemoveFromPreviewNavMesh did not apply");
      state.Balance=0;AppliedRemoves++;
    }

    private static void Unpend(State state) {
      Require(state.Pending&&PendingStates.Remove(state),"Preview navmesh pending bookkeeping lost");
      state.Pending=false;
    }

    private static bool Added(State state)=>_added(state.Nav);

    private static int GroupCount() {
      Require(_groups!=null,"NavMeshGroupService not loaded");
      return _groups.GetAllGroupIds().Count;
    }

    private static State StateOf(BaseComponent owner) {
      var state=States.GetValue(owner,o=>new State{Owner=o});
      if(state.Nav==null) {
        state.BlockNavMesh=_blockObjectNavMesh.GetValue(owner);
        if(state.BlockNavMesh==null)return state;
        state.Nav=(NavMeshObject)_navMeshObject.GetValue(state.BlockNavMesh);
        if(state.Nav==null)return state;
        state.Block=owner.GetComponent<BlockObject>();
        var members=new List<IPreviewServiceMember>();
        owner.GetComponent<Preview>().GetComponents(members);
        state.Deferrable=members.Select(m=>m.GetType().FullName).OrderBy(n=>n,StringComparer.Ordinal)
          .SequenceEqual(new[]{"Timberborn.BlockSystem.PreviewBlockObject","Timberborn.BlockSystemNavigation.BlockObjectPreviewNavMesh"});
        state.Balance=_added(state.Nav)?1:0;
      }
      if(state.Epoch!=_epoch) {
        Require(!state.Pending,"Pending preview across a cache switch");
        state.Epoch=_epoch;state.HasKey=false;state.Balance=_added(state.Nav)?1:0;
      }
      Require(state.Balance==(_added(state.Nav)?1:0),"Preview navmesh applied outside the cache");
      return state;
    }

    private static Type Resolve(string name) {
      var type=AccessTools.TypeByName(name);
      Require(type!=null,"Native type missing: "+name);
      return type;
    }

    private static MethodInfo Method(Type type,string name) {
      var methods=type.GetMethods(BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.DeclaredOnly)
        .Where(m=>m.Name==name).ToArray();
      Require(methods.Length==1,$"Expected exactly one {type.FullName}.{name}, found {methods.Length}");
      return methods[0];
    }

    private static string Il(MethodBase method) {
      using var sha=SHA256.Create();
      return string.Concat(sha.ComputeHash(method.GetMethodBody().GetILAsByteArray()).Select(b=>b.ToString("x2")));
    }

    private static void Require(bool condition,string message) {
      if(!condition)throw new InvalidOperationException("[DeepFrontier PreviewNavMesh] "+message);
    }
  }

  internal sealed class PreviewNavMeshModStarter : IModStarter {
    public void StartMod(IModEnvironment modEnvironment) {
      PreviewNavMeshCache.Patch();
      PreviewAccessCache.Patch();
      PositionedBlocksIndex.Patch();
      Debug.Log("[DeepFrontier] Preview navmesh cache (kept, deferred while moving), construction-access cache and PositionedBlocks index patched (1.1.2.8 IL verified).");
    }
  }

  internal sealed class PreviewNavMeshGroups : ILoadableSingleton, IUnloadableSingleton {
    private readonly NavMeshGroupService _groups;
    public PreviewNavMeshGroups(NavMeshGroupService groups) {_groups=groups;}
    public void Load()=>PreviewNavMeshCache.Load(_groups);
    public void Unload()=>PreviewNavMeshCache.Unload();
  }

  [Context("Game")]
  public sealed class PreviewNavMeshConfigurator : Configurator {
    protected override void Configure() {
      Bind<PreviewNavMeshGroups>().AsSingleton();
      Bind<PreviewAccessWorldListener>().AsSingleton();
    }
  }
}
#endif
