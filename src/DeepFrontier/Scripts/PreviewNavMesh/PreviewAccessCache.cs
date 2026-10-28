#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Security.Cryptography;
using System.Text;
using HarmonyLib;
using Timberborn.BlockObjectAccesses;
using Timberborn.BlockSystem;
using Timberborn.BuildingsNavigation;
using Timberborn.Coordinates;
using Timberborn.Navigation;
using Timberborn.SingletonSystem;
using Timberborn.TerrainSystem;
using UnityEngine;

namespace DeepFrontier.Scripts.PreviewNavMesh {
  // Measured (PreviewCostAcceptance, build 143): after the navmesh cache the
  // Nuclear Reactor preview still cost ~1,030 ms per frame, 1,045 ms of it in
  // native ConstructionSiteAccessible.OnPreviewSelect. Preview.Show calls it
  // every frame, and for a single preview it runs UpdateAccesses ->
  // BlockObjectAccessGenerator.GenerateAccesses(MinZ, MaxZ): every column round
  // and under the footprint, at every level up to the map top, against terrain,
  // the regular navmesh and the block service.
  //
  // GenerateAccesses (1.1.2.8, every method and iterator IL-verified) reads only:
  // - the preview's own placement-derived blocks, BaseZ and entrance (key);
  // - ITerrainService.TryGetDistanceToTerrainAbove (terrain);
  // - INavMeshService.IsOnNavMesh: the regular TerrainNavMeshGraph;
  // - IBlockService.GetBottomObjectAt / GetBottomObjectComponentAt<IPathHeightProvider>
  //   and, on those objects, BlockObjectAccesses (their placement), Entrance,
  //   IsUnfinished and the stairs height providers' IsFinished.
  // So the result is recomputed when the placement changes or after any of:
  // terrain height or field/cutout change, a regular navmesh update, a block
  // object set/unset, or any object entering/leaving the finished or
  // unfinished state. Otherwise the previous list is handed to
  // Accessible.SetAccesses again, exactly what the native call would compute.
  // Previews with an IConstructionSiteAccessProvider and non-single previews
  // keep the native path.
  internal static class PreviewAccessCache {
    private sealed class State {
      public bool Valid;
      public int Version;
      public int Epoch=-1;
      public Placement Placement;
      public readonly List<Vector3> Accesses=new();
    }

    private static readonly ConditionalWeakTable<ConstructionSiteAccessible,State> States=new();
    private static AccessTools.FieldRef<ConstructionSiteAccessible,Preview> _preview;
    private static AccessTools.FieldRef<ConstructionSiteAccessible,BlockObject> _block;
    private static AccessTools.FieldRef<ConstructionSiteAccessible,BlockObjectAccessGenerator> _generator;
    private static FieldInfo _provider;
    private static MethodInfo _minZ,_maxZ;
    private static bool _loaded,_enabled=true;
    private static int _version,_epoch;
    public static long Generated,Reused,WorldChanges;

    private static readonly (Type Type,string Method,string Sha256)[] NativeIl={
      (typeof(ConstructionSiteAccessible),"OnPreviewSelect","0d743e6b483977d1af542a2fb3c89958e4186d100cdcc4d5bd2d3f5fcfdbb02f"),
      (typeof(ConstructionSiteAccessible),"UpdateAccesses","15fae515d5572e056d38e99015a23fa1a1b038ba238b124e41e27f584a5f9926"),
      (typeof(ConstructionSiteAccessible),"get_MinZ","4711002a01397d91447802a78bf79843026ef33743ca1468be2bad69a6443fd1"),
      (typeof(ConstructionSiteAccessible),"get_MaxZ","c92883cacc031d075a6c2577d44407014eab46fa6963b0927872c5fe882ee021"),
      (typeof(Accessible),"SetAccesses","5d196d4ca2b5602784c4591a0139c41b59ae5df2b790cba8ab2d08ea2ba55207"),
    };
    // SHA-256 over the sorted "<nested>::<method> <IL sha256>" lines of every
    // method of the type and its nested (iterator, lambda) types.
    private static readonly (Type Type,string Sha256)[] TypeIl={
      (typeof(BlockObjectAccessGenerator),"c6589196c70f6cd8c21f53f970691c87dfa9866fd232404bf1e2a2feb37e34a9"),
      (typeof(ParentedNeighborCalculator),"f474b79135dcaeb5a93719c43fd6cb25d1c8237b4c4364051f12b4b2bbdf3fba"),
      (typeof(NeighborCalculator),"2b7c38fe3c44222f1916f72eb782815effa4f193345ffb1d2ff058a929307cac"),
    };

    public static void Patch() {
      foreach(var (type,method,sha) in NativeIl) {
        var actual=Il(Single(type,method));
        Require(actual==sha,$"{type.FullName}.{method} differs from 1.1.2.8 (IL {actual})");
      }
      foreach(var (type,sha) in TypeIl) {
        var actual=TypeDigest(type);
        Require(actual==sha,$"{type.FullName} differs from 1.1.2.8 (IL digest {actual})");
      }
      _preview=AccessTools.FieldRefAccess<ConstructionSiteAccessible,Preview>("_preview");
      _block=AccessTools.FieldRefAccess<ConstructionSiteAccessible,BlockObject>("_blockObject");
      _generator=AccessTools.FieldRefAccess<ConstructionSiteAccessible,BlockObjectAccessGenerator>("_blockObjectAccessGenerator");
      _provider=AccessTools.Field(typeof(ConstructionSiteAccessible),"_constructionSiteAccessProvider");
      Require(_provider!=null&&_provider.FieldType==typeof(IConstructionSiteAccessProvider),"ConstructionSiteAccessible._constructionSiteAccessProvider changed");
      _minZ=Single(typeof(ConstructionSiteAccessible),"get_MinZ");
      _maxZ=Single(typeof(ConstructionSiteAccessible),"get_MaxZ");
      new Harmony("DeepFrontier.PreviewAccess").Patch(Single(typeof(ConstructionSiteAccessible),"OnPreviewSelect"),
        prefix:new HarmonyMethod(typeof(PreviewAccessCache),nameof(OnPreviewSelectPrefix)));
    }

    internal static void Load() {_loaded=true;_version++;}
    internal static void Unload() {_loaded=false;_version++;}
    internal static void WorldChanged() {_version++;WorldChanges++;}
    internal static void SetEnabledForMeasurement(bool enabled) {_enabled=enabled;_epoch++;PositionedBlocksIndex.SetEnabledForMeasurement(enabled);}

    private static bool OnPreviewSelectPrefix(ConstructionSiteAccessible __instance) {
      if(!_enabled)return true;
      if(!_preview(__instance).PreviewState.IsSingle)return true; // native: DisableAccesses
      if(_provider.GetValue(__instance)!=null)return true;        // custom provider: native
      Require(_loaded,"World change listener not loaded in this scene");
      var block=_block(__instance);
      var state=States.GetValue(__instance,_=>new State());
      if(state.Epoch!=_epoch) {state.Epoch=_epoch;state.Valid=false;}
      if(!(state.Valid&&state.Version==_version&&state.Placement.Equals(block.Placement))) {
        int version=_version;
        state.Accesses.Clear();
        state.Accesses.AddRange(_generator(__instance).GenerateAccesses((int)_minZ.Invoke(__instance,null),(int)_maxZ.Invoke(__instance,null)));
        Require(version==_version,"World changed while generating construction accesses");
        state.Version=version;state.Placement=block.Placement;state.Valid=block.Positioned;
        Generated++;
      } else {
        Reused++;
      }
      __instance.Accessible.SetAccesses(state.Accesses);
      return false;
    }

    private static MethodInfo Single(Type type,string name) {
      var methods=type.GetMethods(BindingFlags.Instance|BindingFlags.Static|BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.DeclaredOnly)
        .Where(m=>m.Name==name).ToArray();
      Require(methods.Length==1,$"Expected exactly one {type.FullName}.{name}, found {methods.Length}");
      return methods[0];
    }

    internal static string TypeDigest(Type root) {
      var lines=new List<string>();
      void Add(Type type,string prefix) {
        const BindingFlags all=BindingFlags.Instance|BindingFlags.Static|BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.DeclaredOnly;
        foreach(var method in type.GetMethods(all).Cast<MethodBase>().Concat(type.GetConstructors(all)))
          if(method.GetMethodBody() is MethodBody body)lines.Add(prefix+method.Name+" "+Il(method));
        foreach(var nested in type.GetNestedTypes(BindingFlags.Public|BindingFlags.NonPublic))
          Add(nested,(prefix.Length==0?"":prefix.Substring(0,prefix.Length-2)+"+")+nested.Name+"::");
      }
      Add(root,"");
      lines.Sort(StringComparer.Ordinal);
      return Hex(Encoding.UTF8.GetBytes(string.Join("\n",lines)));
    }

    private static string Il(MethodBase method)=>Hex(method.GetMethodBody().GetILAsByteArray());

    private static string Hex(byte[] data) {
      using var sha=SHA256.Create();
      return string.Concat(sha.ComputeHash(data).Select(b=>b.ToString("x2")));
    }

    private static void Require(bool condition,string message) {
      if(!condition)throw new InvalidOperationException("[DeepFrontier PreviewAccess] "+message);
    }
  }

  // Every source GenerateAccesses reads, as change notifications.
  internal sealed class PreviewAccessWorldListener : ILoadableSingleton, IUnloadableSingleton, INavMeshListener {
    private readonly EventBus _events;
    private readonly ITerrainService _terrain;
    private readonly INavMeshListenerEntityRegistry _navMeshListeners;
    public PreviewAccessWorldListener(EventBus events,ITerrainService terrain,INavMeshListenerEntityRegistry navMeshListeners) {
      _events=events;_terrain=terrain;_navMeshListeners=navMeshListeners;
    }
    public void Load() {
      _events.Register(this);
      _terrain.TerrainHeightChanged+=OnTerrainHeightChanged;
      _terrain.FieldOrCutoutChanged+=OnFieldOrCutoutChanged;
      _navMeshListeners.RegisterNavMeshListener(this);
      PreviewAccessCache.Load();
    }
    public void Unload() {
      _events.Unregister(this);
      _terrain.TerrainHeightChanged-=OnTerrainHeightChanged;
      _terrain.FieldOrCutoutChanged-=OnFieldOrCutoutChanged;
      _navMeshListeners.UnregisterNavMeshListener(this);
      PreviewAccessCache.Unload();
    }
    private void OnTerrainHeightChanged(object sender,TerrainHeightChangeEventArgs e)=>PreviewAccessCache.WorldChanged();
    private void OnFieldOrCutoutChanged(object sender,Vector3Int e)=>PreviewAccessCache.WorldChanged();
    public void OnNavMeshUpdated(NavMeshUpdate navMeshUpdate)=>PreviewAccessCache.WorldChanged();
    [OnEvent] public void OnBlockObjectSet(BlockObjectSetEvent e)=>PreviewAccessCache.WorldChanged();
    [OnEvent] public void OnBlockObjectUnset(BlockObjectUnsetEvent e)=>PreviewAccessCache.WorldChanged();
    [OnEvent] public void OnEnteredFinishedState(EnteredFinishedStateEvent e)=>PreviewAccessCache.WorldChanged();
    [OnEvent] public void OnExitedFinishedState(ExitedFinishedStateEvent e)=>PreviewAccessCache.WorldChanged();
    [OnEvent] public void OnEnteredUnfinishedState(EnteredUnfinishedStateEvent e)=>PreviewAccessCache.WorldChanged();
    [OnEvent] public void OnExitedUnfinishedState(ExitedUnfinishedStateEvent e)=>PreviewAccessCache.WorldChanged();
  }
}
#endif
