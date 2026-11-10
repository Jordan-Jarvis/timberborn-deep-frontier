using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text.RegularExpressions;
using Bindito.Core;
using Timberborn.HazardousWeatherSystem;
using Timberborn.SingletonSystem;

namespace ModdableFluids.Tides.ModdableWeathersAdapter {
  /// <summary>
  /// Every Moddable Weathers member the adapter uses, and the behaviour it relies on, checked by name before anything is
  /// bound (Moddable Weathers 11.0.0, source-confirmed with ilspycmd; docs/fluids-tides.md, "Moddable Weathers"). Moddable
  /// Weathers' public API is unversioned (its assembly version stays 1.0.0.0), so an update that changes one of these stops
  /// the Game scene here, naming every changed member and the installed version, instead of failing mid-game.
  /// <para>
  /// Everything is looked up by name: this class references no Moddable Weathers type, so a renamed type cannot fail the
  /// JIT before the check runs. A type the adapter's weathers derive from that disappears entirely fails earlier, when
  /// the game enumerates this assembly's types; the game's log then names this assembly.
  /// </para>
  /// </summary>
  public static class FluidTideModdableWeathersContract {
    public const string WrittenFor = "11.0.0";
    public const string AssemblyName = "ModdableWeathers";
    private const BindingFlags Instance = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly;
    private const BindingFlags Static = BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly;

    /// <summary>Throws one InvalidOperationException listing every changed member, or returns the checked assembly.</summary>
    public static Assembly Verify() {
      var assemblies = AppDomain.CurrentDomain.GetAssemblies().Where(a => a.GetName().Name == AssemblyName).ToArray();
      if (assemblies.Length != 1)
        throw new InvalidOperationException("Moddable Fluids' Moddable Weathers adapter needs exactly one loaded " + AssemblyName + " assembly; found " + assemblies.Length);
      var mw = assemblies[0];
      var problems = new List<string>();
      Check(mw, problems);
      if (problems.Count > 0)
        throw new InvalidOperationException("Moddable Fluids tides cannot run with this Moddable Weathers (installed: " + InstalledVersion(mw) + "): their adapter was written for Moddable Weathers "
          + WrittenFor + ", and these members changed:\n- " + string.Join("\n- ", problems)
          + "\nUpdate Moddable Fluids, or disable Moddable Weathers or the mods that register tides for this game.");
      return mw;
    }

    /// <summary>The installed Moddable Weathers version, from the manifest beside its assembly (diagnostic text only).</summary>
    public static string InstalledVersion(Assembly mw) {
      string location = mw.Location;
      if (string.IsNullOrEmpty(location)) return "version unknown: the assembly was loaded without a file path";
      string manifest = Path.Combine(Path.GetDirectoryName(location), "manifest.json");
      if (!File.Exists(manifest)) return "version unknown: no manifest.json beside " + location;
      var match = Regex.Match(File.ReadAllText(manifest), "\"Version\"\\s*:\\s*\"([^\"]+)\"");
      return match.Success ? match.Groups[1].Value + " at " + Path.GetDirectoryName(location) : "version unknown: " + manifest + " has no Version";
    }

    private static void Check(Assembly mw, List<string> problems) {
      Type T(string name) {
        var type = mw.GetType(name);
        if (type == null) problems.Add("type " + name);
        return type;
      }
      var weatherInterface = T("ModdableWeathers.Weathers.IModdableWeather");
      var hazardous = T("ModdableWeathers.Weathers.IModdableHazardousWeather");
      var weatherBase = T("ModdableWeathers.Weathers.ModdableWeatherBase");
      var spec = T("ModdableWeathers.Weathers.ModdableWeatherSpec");
      var specService = T("ModdableWeathers.Weathers.ModdableWeatherSpecService");
      var registry = T("ModdableWeathers.Weathers.ModdableWeatherRegistry");
      var stageDecision = T("ModdableWeathers.Historical.WeatherCycleStageDecision");
      var cycleDecision = T("ModdableWeathers.Historical.WeatherCycleDecision");
      var historyService = T("ModdableWeathers.Historical.WeatherHistoryService");
      var historyRegistry = T("ModdableWeathers.Historical.WeatherHistoryRegistry");
      var weatherCycle = T("ModdableWeathers.Historical.WeatherCycle");
      var cycleStage = T("ModdableWeathers.Historical.WeatherCycleStage");
      var detailedCycle = T("ModdableWeathers.Historical.DetailedWeatherCycle");
      var detailedStage = T("ModdableWeathers.Historical.DetailedWeatherCycleStage");
      var stageReference = T("ModdableWeathers.Historical.DetailedWeatherStageReference");
      var generator = T("ModdableWeathers.Cycles.WeatherGenerator");
      var cycleService = T("ModdableWeathers.Cycles.WeatherCycleService");
      var binding = T("ModdableWeathers.Helpers.ModdableWeatherBindingExtensions");
      var replacedService = T("ModdableWeathers.Services.ModdableHazardousWeatherService");
      if (problems.Count > 0) return;

      string Name(Type type) => type.IsGenericType ? type.Name + "<" + string.Join(", ", type.GetGenericArguments().Select(Name)) + ">" : type.Name;
      void Property(Type type, string name, Type propertyType, bool setter = false, BindingFlags flags = Instance) {
        var property = type.GetProperty(name, flags);
        if (property?.PropertyType != propertyType || property.GetGetMethod(true) == null || (setter && property.GetSetMethod(true) == null))
          problems.Add(type.Name + "." + name + " : " + Name(propertyType) + (setter ? " { get; set; }" : " { get; }"));
      }
      MethodInfo Method(Type type, string name, Type returnType, Type[] parameters, BindingFlags flags = Instance) {
        var method = type.GetMethod(name, flags, null, parameters, null);
        if (method == null || method.ReturnType != returnType) {
          problems.Add(type.Name + "." + name + "(" + string.Join(", ", parameters.Select(Name)) + ") : " + Name(returnType));
          return null;
        }
        return method;
      }
      // FrozenDictionary and ImmutableArray both live in the game's System.Collections.Immutable.
      Type Generic(string definition, params Type[] arguments) {
        var type = typeof(System.Collections.Immutable.ImmutableArray<>).Assembly.GetType(definition);
        if (type == null) { problems.Add("type " + definition); return typeof(void); }
        return type.MakeGenericType(arguments);
      }
      var frozen = "System.Collections.Frozen.FrozenDictionary`2";
      var immutable = "System.Collections.Immutable.ImmutableArray`1";
      var weighParameters = new[] { stageDecision, cycleDecision, historyService };

      // The weather contract the adapter's weathers implement (FluidTideModdableWeather).
      if (!weatherInterface.IsInterface || !hazardous.IsInterface || !hazardous.GetInterfaces().Contains(weatherInterface) || !hazardous.GetInterfaces().Contains(typeof(IHazardousWeather)))
        problems.Add("IModdableHazardousWeather : IModdableWeather, IHazardousWeather");
      Property(weatherInterface, "Id", typeof(string));
      Property(weatherInterface, "Spec", spec);
      Property(weatherInterface, "Active", typeof(bool));
      Property(weatherInterface, "Enabled", typeof(bool));
      Method(weatherInterface, "Start", typeof(void), new[] { stageReference, typeof(bool) });
      Method(weatherInterface, "End", typeof(void), Type.EmptyTypes);
      var getChance = Method(weatherInterface, "GetChance", typeof(int), weighParameters);
      Method(weatherInterface, "GetDuration", typeof(int), weighParameters);
      if (!weatherBase.IsAbstract || !weatherInterface.IsAssignableFrom(weatherBase) || !typeof(ILoadableSingleton).IsAssignableFrom(weatherBase))
        problems.Add("abstract ModdableWeatherBase : IModdableWeather, ILoadableSingleton");
      if (weatherBase.GetConstructor(Instance, null, new[] { specService }, null) is var constructor && (constructor == null || constructor.IsPrivate))
        problems.Add("ModdableWeatherBase(ModdableWeatherSpecService)");
      var abstracts = weatherBase.GetMethods(Instance).Where(m => m.IsAbstract).Select(m => m.Name).OrderBy(n => n, StringComparer.Ordinal).ToArray();
      var expectedAbstracts = new[] { "get_Id", "GetChance", "GetDuration" }.OrderBy(n => n, StringComparer.Ordinal).ToArray();
      if (!abstracts.SequenceEqual(expectedAbstracts)) problems.Add("ModdableWeatherBase's abstract members { " + string.Join(", ", expectedAbstracts) + " }, found { " + string.Join(", ", abstracts) + " }");
      var load = Method(weatherBase, "Load", typeof(void), Type.EmptyTypes);
      if (load != null && (!load.IsVirtual || !Calls(load, specService.GetProperty("SpecsById")?.GetGetMethod())))
        problems.Add("virtual ModdableWeatherBase.Load() reading its Spec from ModdableWeatherSpecService.SpecsById");
      if (weatherBase.GetProperty("Enabled", Instance)?.GetGetMethod()?.IsVirtual != true) problems.Add("virtual ModdableWeatherBase.Enabled");
      var setActive = weatherBase.GetProperty("Active", Instance)?.GetSetMethod(true);
      var start = Method(weatherBase, "Start", typeof(void), new[] { stageReference, typeof(bool) });
      var end = Method(weatherBase, "End", typeof(void), Type.EmptyTypes);
      if (setActive == null || start == null || end == null || !Calls(start, setActive) || !Calls(end, setActive))
        problems.Add("ModdableWeatherBase.Start and End setting Active");

      // Specs: one ModdableWeatherSpec blueprint per tide, by weather ID.
      Property(specService, "SpecsById", Generic(frozen, typeof(string), spec));
      Property(spec, "Id", typeof(string));
      Property(spec, "DisplayLoc", typeof(string));

      // The registry lists every multi-bound weather and the generator weighs a stage's enabled weathers by GetChance.
      var registryConstructor = registry.GetConstructors().SingleOrDefault();
      if (registryConstructor == null || registryConstructor.GetParameters().FirstOrDefault()?.ParameterType != typeof(IEnumerable<>).MakeGenericType(weatherInterface))
        problems.Add("ModdableWeatherRegistry(IEnumerable<IModdableWeather>, ...): the multi-bound weathers");
      Property(registry, "HazardousWeathers", Generic(immutable, hazardous));
      Property(registry, "WeathersById", Generic(frozen, typeof(string), weatherInterface));
      // The order key is a compiler-generated lambda of the registry: q => q.Spec.Order.
      var registryLoad = Method(registry, "Load", typeof(void), Type.EmptyTypes);
      var specGetter = weatherInterface.GetProperty("Spec")?.GetGetMethod();
      if (registryLoad != null && (!CallsNamed(registryLoad, typeof(Enumerable), "OrderBy")
          || !registry.GetNestedTypes(BindingFlags.NonPublic).SelectMany(t => t.GetMethods(Instance)).Any(m => Calls(m, specGetter))))
        problems.Add("ModdableWeatherRegistry.Load ordering the weathers with OrderBy on IModdableWeather.Spec");
      var decide = Method(generator, "DecideWeather", weatherInterface, new[] { stageDecision, cycleDecision, typeof(System.Text.StringBuilder) });
      var enabled = weatherInterface.GetProperty("Enabled")?.GetGetMethod();
      if (decide != null && (getChance == null || enabled == null || !Calls(decide, getChance) || !Calls(decide, enabled)))
        problems.Add("WeatherGenerator.DecideWeather weighing the enabled weathers by IModdableWeather.GetChance");
      Method(generator, "EnsureWeatherGenerated", typeof(void), new[] { typeof(int) });
      Property(stageDecision, "Cycle", typeof(int));
      Property(stageDecision, "StageIndex", typeof(int));
      Property(stageDecision, "IsBenign", typeof(bool), setter: true);
      Property(stageDecision, "Weather", weatherInterface, setter: true);
      Property(stageDecision, "DaysMultiplier", typeof(int), setter: true);
      Property(cycleDecision, "Cycle", typeof(int));
      Property(cycleDecision, "Stages", Generic(immutable, stageDecision));

      // History: the saved stages per cycle, raw (weather IDs) and resolved.
      Property(historyRegistry, "CycleCount", typeof(int));
      if (historyRegistry.GetProperty("Item", Instance, null, weatherCycle, new[] { typeof(int) }, null)?.GetGetMethod() == null) problems.Add("WeatherHistoryRegistry[int] : WeatherCycle");
      Method(historyRegistry, "ClearFutureEntries", typeof(void), new[] { typeof(int) });
      Property(weatherCycle, "Cycle", typeof(int));
      Property(weatherCycle, "Stages", Generic(immutable, cycleStage));
      Property(cycleStage, "IsBenign", typeof(bool));
      Property(cycleStage, "WeatherId", typeof(string));
      Property(cycleStage, "Days", typeof(int));
      Method(historyService, "GetWeatherCycle", detailedCycle, new[] { typeof(int) });
      Method(historyService, "UpdateReferences", typeof(void), new[] { typeof(int), typeof(bool) });
      Property(detailedCycle, "Stages", Generic(immutable, detailedStage));
      Property(detailedStage, "Weather", weatherInterface);

      // Weathers start and end with their stage (Active), and the hazardous weather service reports the cycle's
      // current or next hazardous stage (the Weather Station samples it).
      var transition = cycleService.GetMethods(Instance).SingleOrDefault(m => m.Name == "TransitionWeather");
      if (transition == null || !Calls(transition, weatherInterface.GetMethod("Start")) || !Calls(transition, weatherInterface.GetMethod("End")))
        problems.Add("WeatherCycleService.TransitionWeather starting and ending the stage weathers");
      if (replacedService.BaseType != typeof(HazardousWeatherService) || !replacedService.GetCustomAttributes(false).Any(a => a.GetType().Name == "ReplaceSingletonAttribute"))
        problems.Add("[ReplaceSingleton] ModdableHazardousWeatherService : HazardousWeatherService");
      Property(replacedService, "MCurrentCycleHazardousWeather", typeof(IHazardousWeather));

      // Registration: BindWeather<T>(Configurator), Moddable Weathers' own binding of a weather type.
      var bind = binding.GetMethods(Static).SingleOrDefault(m => m.Name == "BindWeather" && m.IsGenericMethodDefinition && m.GetGenericArguments().Length == 1);
      if (bind == null || bind.ReturnType != typeof(Configurator) || bind.GetParameters().Length != 1 || bind.GetParameters()[0].ParameterType != typeof(Configurator)
          || !bind.GetGenericArguments()[0].GetGenericParameterConstraints().Contains(weatherInterface))
        problems.Add("ModdableWeatherBindingExtensions.BindWeather<T>(Configurator) where T : class, IModdableWeather");
    }

    // call, callvirt or newobj of the callee in the caller's IL.
    private static bool Calls(MethodBase caller, MethodBase callee) =>
      callee != null && Callees(caller).Any(method => method.Module == callee.Module && method.MetadataToken == callee.MetadataToken);

    private static bool CallsNamed(MethodBase caller, Type declaringType, string name) =>
      Callees(caller).Any(method => method.DeclaringType == declaringType && method.Name == name);

    private static IEnumerable<MethodBase> Callees(MethodBase caller) {
      var il = caller?.GetMethodBody()?.GetILAsByteArray();
      if (il == null) yield break;
      for (int i = 0; i + 4 < il.Length; i++) {
        if (il[i] != 0x28 && il[i] != 0x6F && il[i] != 0x73) continue;
        int token = BitConverter.ToInt32(il, i + 1);
        int table = token >> 24;
        if (table != 0x06 && table != 0x0A && table != 0x2B) continue;
        MethodBase method;
        try { method = caller.Module.ResolveMethod(token, caller.DeclaringType?.GetGenericArguments(), caller.IsGenericMethod ? caller.GetGenericArguments() : null); }
        catch (ArgumentException) { continue; }
        yield return method;
      }
    }
  }
}
