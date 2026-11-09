using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;

// Matches FluidsApiHost.ApiVersion so loaded-copy reports name the contract version.
[assembly: AssemblyVersion("0.1.0.0")]

namespace FluidsApi {
  /// <summary>
  /// Documented discovery entry. Compiled consumers call it directly. Reflection consumers find
  /// exactly one loaded assembly named <see cref="AssemblyName"/> in the AppDomain, get the type
  /// <see cref="EntryTypeName"/>, read <see cref="ApiVersion"/> and <see cref="Capabilities"/>, and
  /// pass a plain provider object to <see cref="RegisterReflectedProvider"/>. Timberborn loads every
  /// enabled mod's assemblies before any IModStarter runs, so registering from StartMod works in
  /// any mod order; the process-wide host is created on first use, not by this mod's own start.
  /// </summary>
  public static class FluidsApiEntry {
    public const string AssemblyName = "FluidsApi";
    public const string EntryTypeName = "FluidsApi.FluidsApiEntry";
    private static readonly object Gate = new object();
    private static FluidsApiHost _host;

    public static string ApiVersion => FluidsApiHost.ApiVersion;
    public static int ContractMajor => FluidsApiHost.ApiMajor;
    public static IReadOnlyList<string> Capabilities => FluidsApiHost.Capabilities;

    /// <summary>The process-wide host. Fails visibly when more than one Fluids API copy is loaded.</summary>
    public static FluidsApiHost Host {
      get {
        lock (Gate) {
          if (_host == null) {
            RequireSingleLoadedCopy(AppDomain.CurrentDomain.GetAssemblies());
            _host = new FluidsApiHost();
          }
          return _host;
        }
      }
    }

    public static void RegisterProvider(IFluidProvider provider) => Host.RegisterProvider(provider);
    public static void RegisterReflectedProvider(object provider) => Host.RegisterReflectedProvider(provider);
    public static string DescribeRuntime() => Host.DescribeRuntime();

    /// <summary>Every loaded assembly with this API's name, as "name version" strings.</summary>
    public static IReadOnlyList<string> DescribeLoadedCopies(IEnumerable<Assembly> assemblies) =>
      assemblies.Where(IsApiAssembly).Select(a => a.GetName().Name + " " + a.GetName().Version).ToArray();

    /// <summary>
    /// Two enabled copies (for example a local build and the Workshop item) load two assemblies
    /// with this name, each with its own static host. Refuse to start a second registry.
    /// </summary>
    public static void RequireSingleLoadedCopy(IEnumerable<Assembly> assemblies) {
      var copies = assemblies.Where(IsApiAssembly).ToArray();
      if (copies.Length > 1)
        throw new InvalidOperationException("Fluids API is loaded " + copies.Length + " times (" + string.Join(", ", DescribeLoadedCopies(copies))
          + "). Enable exactly one Fluids API mod; a local and a Workshop copy cannot run together.");
    }

    private static bool IsApiAssembly(Assembly assembly) => assembly.GetName().Name == AssemblyName;
  }
}
