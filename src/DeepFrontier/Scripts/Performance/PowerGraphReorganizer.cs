#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using HarmonyLib;
using Timberborn.MechanicalSystem;
using Timberborn.ModManagerScene;
using UnityEngine;

namespace DeepFrontier.Scripts.Performance {
  // Why Harmony (Timberborn 1.1.2.8, decompiled): when a node leaves a power
  // network (a building or shaft is deleted, paused, blocked, flooded or
  // switched off by automation), native MechanicalGraphManager.RemoveNode
  // calls MechanicalGraphReorganizer.Reorganize, which splits the network by
  // visiting every remaining node. For each node, VisitConnectedNodes runs
  //   node.Transputs.Select(t => t.ConnectedNode).Intersect(_oldGraphNodes)
  // and LINQ Intersect copies its whole second argument, the set of every
  // node not yet visited, into a new set. One reorganization therefore costs
  // the square of the network's size: Deep Frontier networks (and towns where
  // a mod makes every building a shaft) reach thousands of nodes, and each
  // removal froze the game. The replacement asks _oldGraphNodes directly:
  // exactly the nodes Intersect yields (distinct connected nodes that are not
  // yet visited; a transput without a connection has a null ConnectedNode,
  // which the set never contains) go into _currentGraphNodes, in linear time.
  // The type's IL is verified first; a changed game throws at mod start.
  internal sealed class PowerGraphReorganizerModStarter : IModStarter {
    public void StartMod(IModEnvironment modEnvironment) {
      PowerGraphReorganizer.Patch();
      Debug.Log("[DeepFrontier] Power network split patch applied (MechanicalGraphReorganizer.VisitConnectedNodes, linear).");
    }
  }

  internal static class PowerGraphReorganizer {
    // 1.1.2.8: every method of MechanicalGraphReorganizer (PreviewAccessCache.TypeDigest).
    private const string TypeIl = "30a67fda9e63b34077aa177efc457c15a6263252a0df0e5bf1656988a52d6e9b";

    internal static void Patch() {
      var type = typeof(MechanicalGraphReorganizer);
      var digest = PreviewNavMesh.PreviewAccessCache.TypeDigest(type);
      if (digest != TypeIl) throw new InvalidOperationException($"[DeepFrontier PowerGraphReorganizer] MechanicalGraphReorganizer differs from 1.1.2.8 (IL digest {digest})");
      foreach (var name in new[] { "_oldGraphNodes", "_currentGraphNodes" })
        if (AccessTools.Field(type, name)?.FieldType != typeof(HashSet<MechanicalNode>))
          throw new InvalidOperationException($"[DeepFrontier PowerGraphReorganizer] MechanicalGraphReorganizer.{name} : HashSet<MechanicalNode> changed");
      var visit = AccessTools.Method(type, "VisitConnectedNodes", new[] { typeof(MechanicalNode) });
      if (visit == null || NativeIl.Inlinable(visit))
        throw new InvalidOperationException("[DeepFrontier PowerGraphReorganizer] MechanicalGraphReorganizer.VisitConnectedNodes(MechanicalNode) is missing or inlinable");
      new Harmony("DeepFrontier.PowerGraphReorganizer").Patch(visit,
        prefix: new HarmonyMethod(typeof(PowerGraphReorganizer), nameof(VisitConnectedNodesPrefix)));
    }

    private static bool VisitConnectedNodesPrefix(MechanicalNode node, HashSet<MechanicalNode> ____oldGraphNodes,
        HashSet<MechanicalNode> ____currentGraphNodes) {
      var transputs = node.Transputs;
      for (int i = 0; i < transputs.Length; i++) {
        var connected = transputs[i].ConnectedNode;
        if (connected != null && ____oldGraphNodes.Contains(connected)) ____currentGraphNodes.Add(connected);
      }
      return false;
    }
  }
}
#endif
