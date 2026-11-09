using System;
using System.IO;
using System.Linq;
using System.Reflection;

namespace FluidsApi.Absence {
  /// <summary>
  /// Installed-Mono check with Fluids API absent. Consumers are loaded from bytes like Timberborn's
  /// ModCodeStarter, which then calls GetTypes() on every mod assembly without a guard.
  /// </summary>
  public static class AbsenceProbe {
    public static string Run(string consumers) {
      int checks = 0;
      void Check(bool condition, string name) { checks++; if (!condition) throw new InvalidOperationException(name); }
      var paths = consumers.Split(';');
      if (paths.Length != 2) throw new ArgumentException("Expected reflection;compiled consumer paths");
      var reflection = Assembly.Load(File.ReadAllBytes(paths[0]));
      Check(reflection.GetTypes().Length >= 3, "Reflection consumer enumerates without the API");
      var discovery = reflection.GetType("FluidsApiSyntheticReflection.SyntheticReflectionDiscovery", true);
      var provider = Activator.CreateInstance(reflection.GetType("FluidsApiSyntheticReflection.JuiceProvider", true));
      string result = (string)discovery.GetMethod("Register").Invoke(null, new object[] { AppDomain.CurrentDomain.GetAssemblies(), provider });
      Check(result == (string)discovery.GetField("Absent").GetValue(null), "Absent API outcome: " + result);
      Check(!AppDomain.CurrentDomain.GetAssemblies().Any(a => a.GetName().Name == "FluidsApi"), "FluidsApi was loadable in the absence probe");
      var compiled = Assembly.Load(File.ReadAllBytes(paths[1]));
      ReflectionTypeLoadException failure = null;
      try { compiled.GetTypes(); } catch (ReflectionTypeLoadException e) { failure = e; }
      Check(failure != null, "A compiled consumer enumerated without the API; its package must require Fluids API");
      string cause = string.Join(" | ", failure.LoaderExceptions.Where(e => e != null).Select(e => e.Message).Distinct());
      Check(cause.Contains("FluidsApi"), "Loader exceptions do not name FluidsApi: " + cause);
      return "PASS " + checks + " absence checks; compiled consumer GetTypes failed as documented: " + cause;
    }
  }
}
