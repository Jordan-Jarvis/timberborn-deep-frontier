using System;
using System.IO;
using System.Linq;
using Timberborn.ModdingTools.Common;
using UnityEngine;

namespace Timberborn.ModdingTools.ModBuilding {
  public static class FluidsApiBatchBuild {
    public static void Build() {
      var mod = new ModFinder().GetAllMods().Single(value => value.Name == "FluidsApi");
      var settings = new ModBuilderSettings(buildCode: true, buildWindowsAssetBundle: false,
        buildMacAssetBundle: false, deleteFiles: true, buildZipArchive: false, compatibilityVersion: "1.1");
      if (!new ModBuilder(new[] { mod }, settings).Build()) throw new InvalidOperationException("Official Fluids API prototype build failed");
      var directory = Path.Combine(ModDirectories.ModsDirectory, "FluidsApi", "version-1.1", "Scripts");
      foreach (string assembly in new[] { "FluidsApi.TransportPrototype", "FluidsApi.GamePrototype", "FluidsApi.RuntimePrototype" })
        if (!File.Exists(Path.Combine(directory, assembly + ".dll"))) throw new InvalidOperationException("Official package lacks " + assembly);
      Debug.Log("[FluidsApi] Official Mod Builder completed the flagged development package.");
    }
  }
}
