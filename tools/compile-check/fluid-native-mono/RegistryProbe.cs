using System;
using System.IO;
using System.Linq;
using System.Reflection;
using ModdableFluids.Native.Prototype;
using ModdableFluids.Persistence.Prototype;
using ModdableFluids.Transport.Prototype;

namespace ModdableFluids.Native.Acceptance {
  /// <summary>
  /// Public registry, consumer routes and save round trip under the installed Mono. Consumers are
  /// loaded from bytes like Timberborn's ModCodeStarter, so their Moddable Fluids reference binds the
  /// same way it does in game.
  /// </summary>
  internal static class RegistryProbe {
    internal static string Note = "";
    internal static FluidSaveDocument Document;

    internal static int Run(string consumers, NativeWaterArrayAdapter backend, NativeFluidTransportSession session) {
      int checks = 0;
      void Check(bool condition, string name) { checks++; if (!condition) throw new InvalidOperationException(name); }
      var paths = consumers.Split(';');
      if (paths.Length != 2) throw new ArgumentException("Expected reflection;compiled consumer paths");
      var reflection = Assembly.Load(File.ReadAllBytes(paths[0]));
      var compiled = Assembly.Load(File.ReadAllBytes(paths[1]));
      Check(!reflection.GetReferencedAssemblies().Any(a => a.Name == "ModdableFluids"), "Mono reflection consumer has no compiled API reference");
      Check(reflection.GetTypes().Length >= 3 && compiled.GetTypes().Length >= 2, "Mono type enumeration of both consumers with the API present");
      Check(AppDomain.CurrentDomain.GetAssemblies().Count(a => a.GetName().Name == "ModdableFluids") == 1, "Mono has one ModdableFluids assembly");

      var juice = Activator.CreateInstance(reflection.GetType("ModdableFluidsSyntheticReflection.JuiceProvider", true));
      var register = reflection.GetType("ModdableFluidsSyntheticReflection.SyntheticReflectionDiscovery", true).GetMethod("Register");
      string result = (string)register.Invoke(null, new object[] { AppDomain.CurrentDomain.GetAssemblies(), juice });
      Check(result == "registered ModdableFluidsSyntheticReflection.Juice with Moddable Fluids 0.1.3", "Mono reflection discovery: " + result);
      // The cast succeeds only if the byte-loaded consumer bound to this same API assembly.
      var tracer = (IFluidProvider)Activator.CreateInstance(compiled.GetType("ModdableFluidsSyntheticCompiled.TracerProvider", true));
      ModdableFluidsEntry.RegisterProvider(tracer);
      var host = ModdableFluidsEntry.Host;
      var registry = host.Freeze();
      Check(registry.Definitions.Select(d => d.Id).SequenceEqual(new[] { FluidIds.Water, FluidIds.Badwater, "ModdableFluidsSyntheticCompiled.Tracer", "ModdableFluidsSyntheticReflection.Juice" }),
        "Mono registry order");
      Check(registry.Get(registry.GetHandle("ModdableFluidsSyntheticReflection.Juice")).Metadata["ModdableFluidsSyntheticReflection.Sweetness"] == "7", "Mono reflected metadata");

      var scene = host.ActivateScene();
      host.LoadProviderStates(scene, null);
      juice.GetType().GetProperty("Pressings").SetValue(juice, 5);
      tracer.GetType().GetProperty("Releases").SetValue(tracer, 3);
      tracer.GetType().GetProperty("LastTag").SetValue(tracer, "mono");
      var states = host.SaveProviderStates(scene);
      host.UnloadScene(scene);
      Check(session.Phase == "Ready" && session.ComponentCount == registry.Count, "Mono session matches the registry layout");
      var document = FluidWorldPersistence.Capture(registry, session, 5, states);
      Document = document;
      var restoredSession = new NativeFluidTransportSession(backend, registry.Count, FluidRegistry.BadwaterIndex);
      var layout = Enumerable.Range(0, restoredSession.ColumnCount).Select(restoredSession.GetGeometry).ToArray();
      var restored = FluidWorldPersistence.Restore(document, registry, layout, 5, 3);
      FluidWorldPersistence.Apply(restoredSession, registry, restored, 5);
      for (int slot = 0; slot < session.ColumnCount; slot++) {
        int native = session.GetGeometry(slot).NativeIndex;
        for (int c = 0; c < registry.Count; c++)
          Check(BitConverter.DoubleToInt64Bits(restoredSession.Sample(native).GetVolume(c)) == BitConverter.DoubleToInt64Bits(session.Sample(native).GetVolume(c)),
            "Mono bitwise save round trip at " + native + " component " + c);
      }
      juice.GetType().GetProperty("Pressings").SetValue(juice, 0);
      tracer.GetType().GetProperty("Releases").SetValue(tracer, 0);
      var second = host.ActivateScene();
      host.LoadProviderStates(second, document.GetProviderStates());
      host.UnloadScene(second);
      Check((int)juice.GetType().GetProperty("Pressings").GetValue(juice) == 5 && (int)tracer.GetType().GetProperty("Releases").GetValue(tracer) == 3 &&
        (string)tracer.GetType().GetProperty("LastTag").GetValue(tracer) == "mono", "Mono provider state round trip");
      Check((int)juice.GetType().GetProperty("Activations").GetValue(juice) == 2 && (int)juice.GetType().GetProperty("Unloads").GetValue(juice) == 2, "Mono scene re-entry");

      var random = new Random(1105);
      for (int i = 0; i < 1000; i++) {
        double value = Math.Exp(random.NextDouble() * 60 - 40) * random.NextDouble();
        Check(BitConverter.DoubleToInt64Bits(FluidSaveDocument.DecodeQuantity(FluidSaveDocument.EncodeQuantity(value), "mono")) == BitConverter.DoubleToInt64Bits(value), "Mono exact quantity");
      }

      // Last: a second byte load of the API, as an enabled local and Workshop copy would produce.
      var copy = Assembly.Load(File.ReadAllBytes(typeof(ModdableFluidsEntry).Assembly.Location));
      int copies = AppDomain.CurrentDomain.GetAssemblies().Count(a => a.GetName().Name == "ModdableFluids");
      bool rejected = false;
      try { ModdableFluidsEntry.RequireSingleLoadedCopy(AppDomain.CurrentDomain.GetAssemblies()); } catch (InvalidOperationException) { rejected = true; }
      Check(copies == 1 ? !rejected && ReferenceEquals(copy, typeof(ModdableFluidsEntry).Assembly) : rejected, "Mono duplicate-copy detection agrees with the loaded copies");
      Note = copies == 1 ? "Mono returned the loaded ModdableFluids for a second byte load" : "Mono loaded a second ModdableFluids copy from bytes and the API refused it";
      return checks;
    }
  }
}
