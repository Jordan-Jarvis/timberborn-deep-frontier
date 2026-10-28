#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using HarmonyLib;
using Timberborn.AssetSystem;
using Timberborn.ModManagerScene;
using Timberborn.Timbermesh;
using Timberborn.PrefabOptimization;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Releases the intermediate meshes the native prefab optimization chain leaves behind
  // (Timberborn 1.1.2.8, decompiled Timberborn.PrefabOptimization):
  //
  // PrefabOptimizationChain.ProcessPrefab(GameObject) runs once per blueprint (cached in
  // _blueprintCache; every instance, preview or building, shares the result). It clones the
  // input under an inactive root and runs, in order:
  //   TimbermeshPrefabOptimizer          imports each .timbermesh (a new Mesh per node)
  //   AutoAtlasingPrefabOptimizer        Object.Instantiate(sharedMesh), atlas UVs, replaces it
  //   VertexColorPrefabOptimizer         Object.Instantiate(sharedMesh), colours, replaces it
  //   MergeMeshesByMaterialPrefabOptimizer  MeshBuilder.Build() -> a new Mesh, replaces it
  //   DestroyEmptyChildrenPrefabOptimizer
  // No step destroys the Mesh it replaces, so every renderer leaves three unreferenced copies
  // of its full vertex data until the next Resources.UnloadUnusedAssets (the next scene
  // change). BottomBarPanel.Load creates a preview of every placeable blueprint during the
  // game-scene load, so all of them are processed in one frame. Vanilla models are small;
  // Deep Frontier's are 0.1-1.7 M vertices each, with the same model imported twice (finished
  // and ConstructionStage0), and the orphans alone reached several GB (outputs/memory-load-*).
  //
  // A postfix of each optimizer records the meshes it replaced; a postfix of ProcessPrefab
  // destroys those created during this run that the finished prefab no longer references.
  // Meshes the input prefab already referenced (shared prefab assets) are never touched, and
  // the finished prefab draws exactly what it drew before (ShareIdenticalModels below only
  // swaps a mesh for an identical one).
  internal sealed class PrefabMeshReleaseModStarter : IModStarter {
    public void StartMod(IModEnvironment modEnvironment) {
      // Test-only switch for before/after memory runs (tools/start_memory_load.ps1 -KeepPrefabMeshes).
      var args = Environment.GetCommandLineArgs();
      if (args.Contains(PrefabMeshRelease.KeepFlag)) {
        if (!args.Contains("-deepFrontierLoadAcceptance")) throw new InvalidOperationException($"{PrefabMeshRelease.KeepFlag} requires -deepFrontierLoadAcceptance");
        Debug.Log("[DeepFrontier] Prefab mesh release NOT applied (test switch " + PrefabMeshRelease.KeepFlag + ").");
        return;
      }
      PrefabMeshRelease.Apply();
      Debug.Log("[DeepFrontier] Prefab mesh release applied (orphaned optimization meshes, byte-identical models).");
    }
  }

  internal static class PrefabMeshRelease {
    internal const string HarmonyId = "DeepFrontier.PrefabMeshRelease";
    internal const string KeepFlag = "-deepFrontierKeepPrefabMeshes";
    private static readonly Stack<Run> Runs = new Stack<Run>();
    // Meshes the finished prefabs of earlier runs use (the chain caches them for the scene).
    private static readonly HashSet<Mesh> KeptByPrefabs = new HashSet<Mesh>();
    private static Mesh[] _before;
    internal static long ReleasedMeshes { get; private set; }
    internal static long ReleasedVertices { get; private set; }
    internal static int Collections { get; private set; }
    private const long HeavyModelVertices = 100_000;
    private const long VeryLargeModelVertices = 200_000;

    private sealed class Run {
      public readonly HashSet<Mesh> Protected = new HashSet<Mesh>();
      public readonly List<Mesh> Replaced = new List<Mesh>();
      // Per model root (TimbermeshDescription transform): the objects the importer created, in node order.
      public readonly Dictionary<Transform, GameObject[]> Imported = new Dictionary<Transform, GameObject[]>();
    }

    internal static void Apply() {
      var harmony = new Harmony(HarmonyId);
      harmony.Patch(ProcessPrefab(), prefix: new HarmonyMethod(Method(nameof(ProcessPrefix))), finalizer: new HarmonyMethod(Method(nameof(ProcessFinalizer))));
      foreach (var optimize in Optimizers())
        harmony.Patch(optimize, new HarmonyMethod(Method(nameof(OptimizePrefix))), new HarmonyMethod(Method(nameof(OptimizePostfix))));
      var processModel = typeof(TimbermeshImporter).GetMethod(nameof(TimbermeshImporter.ProcessModel), BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic,
        null, new[] { typeof(Timberborn.TimbermeshDTO.Model), typeof(HideFlags), typeof(ImportDetails) }, null)
        ?? throw new InvalidOperationException("Prefab mesh release: TimbermeshImporter.ProcessModel(Model, HideFlags, ImportDetails) not found (Timberborn 1.1.2.8)");
      harmony.Patch(processModel, postfix: new HarmonyMethod(Method(nameof(ImportPostfix))));
    }

    // TimbermeshImporter.ProcessModel: CreateMeshes made one GameObject per model node under details.Root.
    private static void ImportPostfix(Timberborn.TimbermeshDTO.Model model, ImportDetails details) {
      if (Runs.Count == 0) return;   // an import outside the chain
      var objects = new GameObject[model.Nodes.Length];
      for (int i = 0; i < objects.Length; i++) objects[i] = details.CreatedObjectsMap[model.Nodes[i]];
      var imported = Runs.Peek().Imported;
      if (imported.ContainsKey(details.Root)) throw new InvalidOperationException($"Prefab mesh release: {details.Root.name} imported two models");
      imported.Add(details.Root, objects);
    }

    private static MethodInfo Method(string name) => typeof(PrefabMeshRelease).GetMethod(name, BindingFlags.Static | BindingFlags.NonPublic);

    // The chain's step for one prefab, and the five optimizers the native provider puts in it.
    private static MethodInfo ProcessPrefab() {
      var method = typeof(PrefabOptimizationChain).GetMethod("ProcessPrefab", BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic,
        null, new[] { typeof(GameObject) }, null);
      if (method == null || method.ReturnType != typeof(GameObject))
        throw new InvalidOperationException("Prefab mesh release: PrefabOptimizationChain.ProcessPrefab(GameObject) : GameObject not found (Timberborn 1.1.2.8)");
      return method;
    }

    private static IEnumerable<MethodInfo> Optimizers() {
      var expected = new[] { typeof(TimbermeshPrefabOptimizer), typeof(AutoAtlasingPrefabOptimizer), typeof(VertexColorPrefabOptimizer),
        typeof(MergeMeshesByMaterialPrefabOptimizer), typeof(DestroyEmptyChildrenPrefabOptimizer) };
      var found = typeof(IPrefabOptimizer).Assembly.GetTypes()
        .Where(t => !t.IsInterface && !t.IsAbstract && typeof(IPrefabOptimizer).IsAssignableFrom(t)).ToList();
      if (found.Count != expected.Length || expected.Any(t => !found.Contains(t)))
        throw new InvalidOperationException("Prefab mesh release: the native prefab optimizers changed (expected " +
          string.Join(", ", expected.Select(t => t.Name)) + "; found " + string.Join(", ", found.Select(t => t.Name)) + ")");
      foreach (var type in expected) {
        var method = type.GetMethod(nameof(IPrefabOptimizer.Optimize), BindingFlags.Instance | BindingFlags.Public | BindingFlags.DeclaredOnly,
          null, new[] { typeof(GameObject) }, null);
        if (method == null) throw new InvalidOperationException($"Prefab mesh release: {type.Name}.Optimize(GameObject) not found");
        yield return method;
      }
    }

    private static void ProcessPrefix(GameObject inputPrefab) {
      var run = new Run();
      if (inputPrefab) Collect(inputPrefab, run.Protected);
      Runs.Push(run);
    }

    private static void OptimizePrefix(GameObject prefab) {
      if (Runs.Count == 0) return;   // an optimizer called outside the chain
      var meshes = new HashSet<Mesh>();
      Collect(prefab, meshes);
      _before = meshes.ToArray();
    }

    private static void OptimizePostfix(GameObject prefab) {
      if (Runs.Count == 0) return;
      var after = new HashSet<Mesh>();
      Collect(prefab, after);
      var run = Runs.Peek();
      foreach (var mesh in _before)
        if (mesh && !after.Contains(mesh) && !run.Protected.Contains(mesh)) run.Replaced.Add(mesh);
      _before = null;
      // Each step on a very large model leaves its own garbage (import buffers, uv/colour/index
      // copies, MeshBuilder arrays); collecting between steps keeps one model's steps from
      // stacking up into a heap expansion (see ProcessFinalizer).
      long vertices = 0;
      foreach (var mesh in after) vertices += mesh.vertexCount;
      if (vertices >= VeryLargeModelVertices) { GC.Collect(); Collections++; }
    }

    // Finalizer, so a failed run (the native chain rethrows) still leaves the stack balanced;
    // the native exception is rethrown unchanged.
    private static void ProcessFinalizer(PrefabOptimizationChain __instance, Exception __exception, GameObject __result) {
      var run = Runs.Pop();
      if (__exception != null || !__result) return;
      ShareIdenticalModels(__instance, __result, run);
      var kept = new HashSet<Mesh>();
      Collect(__result, kept);
      long released = 0;
      foreach (var mesh in run.Replaced.Distinct()) {
        if (!mesh || kept.Contains(mesh)) continue;
        // A mesh created in this run cannot belong to an earlier finished prefab; if it does,
        // the native chain shares meshes in a way this release does not know.
        if (KeptByPrefabs.Contains(mesh))
          throw new InvalidOperationException($"Prefab mesh release: {mesh.name} replaced while processing {__result.name} is used by an earlier optimized prefab");
        released += mesh.vertexCount;
        ReleasedVertices += mesh.vertexCount;
        ReleasedMeshes++;
        UnityEngine.Object.DestroyImmediate(mesh);
      }
      KeptByPrefabs.UnionWith(kept);
      // The import and optimization of a large model leave hundreds of MB of managed garbage
      // (protobuf vertex data, uv/colour/index copies, MeshBuilder lists). Boehm grows the
      // Mono heap rather than collect while recent allocation is below a share of the heap,
      // and never returns it, so back-to-back large models ratcheted the heap up by ~0.8 GB at
      // a time during BottomBarPanel.Load. A full collection after each large model lets the
      // next one reuse that space. Semantically transparent; costs one collection per model.
      if (released >= HeavyModelVertices) { GC.Collect(); Collections++; }
      // Guard: the finished prefab must still draw every mesh it references.
      foreach (var filter in __result.GetComponentsInChildren<MeshFilter>(true))
        if (filter.sharedMesh is var mesh && !ReferenceEquals(mesh, null) && !mesh)
          throw new InvalidOperationException($"Prefab mesh release destroyed a mesh that {__result.name}/{filter.name} still uses");
    }

    // Two timbermesh models of one prefab whose files are byte-identical (every Deep Frontier
    // building's ConstructionStage0 model is a copy of its finished model; vanilla blueprints
    // repeat models such as barrels and bridge sections) went through the same deterministic
    // import and optimization, so the second takes the first's finished meshes and its own
    // copies are released. Objects are matched by model node index (recorded at import); a
    // byte-identical model that came out different is a broken assumption and throws.
    private static readonly Dictionary<string, (int Length, ulong Hash)> ModelIdentity = new Dictionary<string, (int, ulong)>();

    private static void ShareIdenticalModels(PrefabOptimizationChain chain, GameObject prefab, Run run) {
      var descriptions = prefab.GetComponentsInChildren<TimbermeshDescription>(true);
      if (descriptions.Length < 2) return;
      var loader = chain._prefabProcessors.OfType<TimbermeshPrefabOptimizer>().Single()._assetLoader;
      var firstByIdentity = new Dictionary<(int, ulong), TimbermeshDescription>();
      foreach (var description in descriptions) {
        if (!run.Imported.TryGetValue(description.transform, out var nodes))
          throw new InvalidOperationException($"{prefab.name}: model {description.ModelName} was not imported by this run");
        var identity = Identity(loader, description.ModelName);
        if (!firstByIdentity.TryGetValue(identity, out var first)) { firstByIdentity.Add(identity, description); continue; }
        var originals = run.Imported[first.transform];
        if (originals.Length != nodes.Length)
          throw new InvalidOperationException($"{prefab.name}: byte-identical models {first.ModelName} and {description.ModelName} have {originals.Length} and {nodes.Length} nodes");
        for (int n = 0; n < nodes.Length; n++) {
          // DestroyEmptyChildren removes the same empty nodes from both.
          bool a = originals[n], b = nodes[n];
          if (a != b) throw new InvalidOperationException($"{prefab.name}: node {n} of byte-identical models {first.ModelName} and {description.ModelName} survived in only one");
          if (!a) continue;
          var original = originals[n].GetComponent<MeshFilter>();
          var filter = nodes[n].GetComponent<MeshFilter>();
          if ((bool)original != (bool)filter || (original && (bool)original.sharedMesh != (bool)filter.sharedMesh))
            throw new InvalidOperationException($"{prefab.name}: node {nodes[n].name} of byte-identical models has a mesh in only one");
          if (!original || !original.sharedMesh || filter.sharedMesh == original.sharedMesh) continue;
          RequireSame(prefab, original, filter);
          run.Replaced.Add(filter.sharedMesh);
          filter.sharedMesh = original.sharedMesh;
          SharedMeshes++;
        }
      }
    }

    internal static long SharedMeshes { get; private set; }

    private static (int, ulong) Identity(IAssetLoader loader, string model) {
      if (ModelIdentity.TryGetValue(model, out var known)) return known;
      var bytes = loader.Load<BinaryData>(model).Bytes;
      ulong hash = 14695981039346656037UL;                      // FNV-1a 64
      for (int i = 0; i < bytes.Length; i++) { hash ^= bytes[i]; hash *= 1099511628211UL; }
      var identity = (bytes.Length, hash);
      ModelIdentity.Add(model, identity);
      return identity;
    }

    private static void RequireSame(GameObject prefab, MeshFilter a, MeshFilter b) {
      Mesh x = a.sharedMesh, y = b.sharedMesh;
      bool same = x.vertexCount == y.vertexCount && x.subMeshCount == y.subMeshCount && x.bounds == y.bounds
        && a.transform.localPosition == b.transform.localPosition && a.transform.localRotation == b.transform.localRotation
        && a.transform.localScale == b.transform.localScale
        && a.GetComponent<MeshRenderer>() is var ra && b.GetComponent<MeshRenderer>() is var rb && ra && rb
        && ra.sharedMaterials.SequenceEqual(rb.sharedMaterials);
      for (int i = 0; same && i < x.subMeshCount; i++) same = x.GetSubMesh(i).indexCount == y.GetSubMesh(i).indexCount;
      if (!same) throw new InvalidOperationException($"{prefab.name}: byte-identical models produced different meshes at {a.name} ({x.vertexCount} vs {y.vertexCount} vertices)");
    }

    // Every mesh a prefab hierarchy references through a renderer or collider.
    private static void Collect(GameObject root, HashSet<Mesh> meshes) {
      foreach (var filter in root.GetComponentsInChildren<MeshFilter>(true)) if (filter.sharedMesh) meshes.Add(filter.sharedMesh);
      foreach (var skinned in root.GetComponentsInChildren<SkinnedMeshRenderer>(true)) if (skinned.sharedMesh) meshes.Add(skinned.sharedMesh);
      foreach (var collider in root.GetComponentsInChildren<MeshCollider>(true)) if (collider.sharedMesh) meshes.Add(collider.sharedMesh);
    }
  }
}
#endif
