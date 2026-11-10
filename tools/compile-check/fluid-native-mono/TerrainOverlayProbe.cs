using System;
using System.Collections;
using System.Reflection;
using System.Runtime.Serialization;
using Timberborn.TerrainSystemRendering;
using UnityEngine;
using ModdableFluids.Rendering.Prototype;
using ModdableFluids.Runtime.Prototype;

namespace ModdableFluids.Native.Acceptance {
  /// <summary>
  /// Moddable Fluids' terrain overlay under the installed Mono: its native contract (TerrainMeshManager and its tile
  /// dictionary, TerrainMaterialMap's soil-contamination layout, MaterialCollectionSpec) passes against the installed
  /// assemblies; the native tile dictionary is read through its private nested struct, and a tile without its renderer
  /// is refused; the overlay field publishes in the native order; the half floats and the curve bytes it uploads are
  /// what the .NET harness checks, under Mono's JIT (the curve against IrradiatedSoilSurface.Encode's expression).
  /// </summary>
  internal static class TerrainOverlayProbe {
    private const BindingFlags Fields = BindingFlags.Instance | BindingFlags.NonPublic;

    internal static int Run() {
      int checks = 0;
      void Check(bool condition, string name) { checks++; if (!condition) throw new InvalidOperationException(name); }
      var contract = FluidTerrainRendering.CheckContract();
      Check(contract.Count == 0, "Installed terrain overlay contract reported: " + string.Join("; ", contract));

      var managerType = typeof(TerrainMaterialMap).Assembly.GetType("Timberborn.TerrainSystemRendering.TerrainMeshManager", true);
      object manager = FormatterServices.GetUninitializedObject(managerType);
      var tilesField = managerType.GetField("_tiles", Fields);
      var tiles = (IDictionary)Activator.CreateInstance(tilesField.FieldType);
      tilesField.SetValue(manager, tiles);
      var none = FluidTerrainRendering.ReadTiles(manager, out var read);
      Check(none.Length == 0 && ReferenceEquals(read, tiles), "The native tile dictionary is read from TerrainMeshManager._tiles");
      tiles.Add(new Vector3Int(1, 2, 0), Activator.CreateInstance(managerType.GetNestedType("TileComponents", BindingFlags.NonPublic)));
      bool refused = false;
      try { FluidTerrainRendering.ReadTiles(manager, out _); }
      catch (InvalidOperationException e) { refused = e.Message.Contains("(1, 2, 0)") && e.Message.Contains("no MeshRenderer"); }
      Check(refused, "A native tile without its renderer (read through the boxed TileComponents) was not refused");
      bool wrongOwner = false;
      try { FluidTerrainRendering.ReadTiles(new object(), out _); } catch (ArgumentException) { wrongOwner = true; }
      Check(wrongOwner, "Tiles were read from an object that is not the native TerrainMeshManager");

      // The CPU half: settled load, a tick's change from G to R, the settling tick.
      var field = new FluidTerrainOverlayField(3, 2, 2, new[] { new FluidTerrainOverlayColor(2.156863f, 5.692307f, 6f) }, Environment.CurrentManagedThreadId);
      field.SetLevel(0, 2, 1, 1, 200);
      field.Publish(interpolate: false);
      Check(field.Texel(2, 1, 1) == ((byte)200, (byte)200) && field.NonZeroTexels == 1, "Mono: settled publish");
      Check(field.TakeLevelUpload(1, out int lo, out int hi) && lo == 1 && hi == 1 && !field.TakeLevelUpload(0, out _, out _), "Mono: only the written row uploads");
      field.SetLevel(0, 2, 1, 1, 0);
      field.Publish(interpolate: true);
      Check(field.Texel(2, 1, 1) == ((byte)200, (byte)0) && Math.Abs(field.ColorTexel(2, 1, 1).Blue - 200 / 255f * 6) < 1e-2, "Mono: the fading texel keeps its colour");
      field.Publish(interpolate: true);
      Check(field.Texel(2, 1, 1) == ((byte)0, (byte)0) && field.NonZeroTexels == 0 && field.ColorTexel(2, 1, 1).LevelSum == 0, "Mono: settled at 0, colour cleared");
      Check(FluidHalf.FromFloat(65520f) == 0x7C00 && FluidHalf.FromFloat(65519f) == 0x7BFF && FluidHalf.FromFloat(2.9802322E-08f) == 0
        && FluidHalf.FromFloat(1f / 3) == 0x3555 && FluidHalf.ToFloat(0x3555) == 0.333251953125f && FluidHalf.FromFloat(-6f) == 0xC600, "Mono: half-float rounding");

      // IrradiatedSoilSurface.Encode's expression (constants folded as there) against the overlay curve, under Mono's JIT.
      var curve = new FluidTerrainOverlayCurve(.05f, .5f, .1f);
      int differences = 0;
      for (int k = 0; k <= 600000; k++) {
        float soil = k / 500000f;
        if (curve.Encode(soil) != Encode(soil)) differences++;
      }
      Check(differences == 0, "Mono: the overlay curve differs from IrradiatedSoilSurface.Encode for " + differences + " soil values");
      return checks;
    }

    private const float MinRenderedSoil = 0.05f, FullSoil = 0.5f, MinMapValue = 0.1f;

    private static byte Encode(float soil) {
      if (soil < MinRenderedSoil) return 0;
      float value = 1f - (1f - MinMapValue) * (1f - Mathf.Min(soil, FullSoil) / FullSoil);
      return (byte)(255f * value);
    }
  }
}
