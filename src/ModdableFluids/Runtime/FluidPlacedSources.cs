using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using Timberborn.BaseComponentSystem;
using Timberborn.EntitySystem;
using Timberborn.TemplateInstantiation;
using Timberborn.TemplateSystem;
using Timberborn.TimeSystem;
using Timberborn.WaterSourceSystem;
using Timberborn.WaterSystem;
using ModdableFluids;
using ModdableFluids.Sources.Prototype;

namespace ModdableFluids.Runtime.Prototype {
  /// <summary>
  /// The source type of every placed native water source, for the fluid source stage on the worker threads. Each source
  /// is classified once on the main thread, when its entity wakes, and kept by object identity (a weak table, so a
  /// deleted source's entry goes with it). A source the stage meets without a type fails visibly.
  /// </summary>
  public sealed class FluidPlacedSources {
    private readonly ConditionalWeakTable<object, FluidSourceTypeDefinition> _types = new ConditionalWeakTable<object, FluidSourceTypeDefinition>();
    public int Classified { get; private set; }
    internal void Register(IWaterSource source, FluidSourceTypeDefinition type) {
      _types.Remove(source);
      _types.Add(source, type);
      Classified++;
    }
    /// <summary>The type of a native source (the <c>ThreadSafeWaterSource._waterSource</c> object); any thread.</summary>
    public FluidSourceTypeDefinition TypeOf(object source) {
      if (source != null && _types.TryGetValue(source, out var type)) return type;
      throw new InvalidOperationException("A native water source (" + source?.GetType().FullName + ") reached the fluid source stage without a source type; "
        + "every placed source is classified by its blueprint when it wakes");
    }
  }

  /// <summary>
  /// Decorated onto every native <c>WaterSource</c>: finds its registered source type by its blueprint (template name and
  /// native specs, checked by <see cref="NativeSourceClassifier"/>, which fails visibly when the blueprint no longer matches
  /// its type), records it for the source stage, and applies the type's native behaviour the game's own way. A schedule
  /// (a geyser) is an <c>IWaterStrengthModifier</c> on the source, like the native drought and depth modifiers; a type that
  /// does not follow droughts removes the native drought modifier from its source, as the native
  /// <c>UnderlyingWaterSource.DisableDroughtInfluence</c> (the Badwater Pressurizer) does. Badtide behaviour comes from the
  /// blueprint's own native controller spec, which the classification checks against the type.
  /// </summary>
  public sealed class FluidPlacedSource : BaseComponent, IAwakableComponent, IPostInitializableEntity, IWaterStrengthModifier {
    private const BindingFlags Members = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;
    private const string Specs = "Timberborn.WaterSourceSystem.";
    private readonly FluidPlacedSources _sources;
    private readonly IDayNightCycle _time;
    private WaterSource _source;
    private Guid _entity;
    public FluidSourceTypeDefinition SourceType { get; private set; }
    public bool DroughtRemoved { get; private set; }

    public FluidPlacedSource(FluidPlacedSources sources, IDayNightCycle time) { _sources = sources; _time = time; }

    public void Awake() {
      _source = GetComponent<WaterSource>();
      string template = GetComponent<TemplateSpec>()?.TemplateName
        ?? throw new InvalidOperationException("Moddable Fluids: water source " + Name + " has no TemplateSpec, so its source type cannot be found");
      var registry = ModdableFluidsEntry.Host.Registry;
      if (!NativeSourceClassifier.TryClassify(registry, Signature(template), out var type, out string reason))
        throw new InvalidOperationException("Moddable Fluids: " + reason + " (placed water source " + Name + "). The mod that adds this blueprint must register its source type (FluidRegistration.AddSourceType).");
      SourceType = type;
      _sources.Register(_source, type);
    }

    public void PostInitializeEntity() {
      _entity = GetComponent<EntityComponent>().EntityId;
      if (SourceType.Schedule != null) _source.AddWaterStrengthModifier(this);
      if (!SourceType.FollowsDrought) {
        var drought = AllComponents.Where(c => c.GetType().FullName == Specs + "DroughtWaterStrengthModifier").ToArray();
        if (drought.Length != 1) throw new InvalidOperationException("Moddable Fluids: water source " + Name + " has " + drought.Length + " native drought modifiers, expected 1 (Timberborn 1.1.2.8)");
        _source.RemoveWaterStrengthModifier((IWaterStrengthModifier)drought[0]);
        DroughtRemoved = true;
      }
    }

    /// <summary>The type's schedule multiplier at the current game time, phased by the entity's saved ID.</summary>
    public float GetStrengthModifier() =>
      (float)FluidSourceEmission.StrengthMultiplier(SourceType, (double)_time.DayNumber * 24 + _time.HoursPassedToday, _entity);

    private NativeSourceSignature Signature(string template) {
      object Spec(string name) => AllComponents.SingleOrDefault(c => c.GetType().FullName == Specs + name);
      object Get(object spec, string property) => spec.GetType().GetProperty(property, Members).GetValue(spec);
      var source = Spec("WaterSourceSpec") ?? throw new InvalidOperationException("Moddable Fluids: water source " + Name + " has no WaterSourceSpec");
      var contamination = Spec("WaterSourceContaminationSpec");
      var depth = Spec("WaterDepthStrengthModifierSpec");
      var weathers = Spec("HazardousWeatherWaterSourceSpec");
      return new NativeSourceSignature(template, (int)Get(Get(source, "Coordinates"), "Length"), (float)Get(source, "DefaultStrength"),
        // Without the native contamination spec no native type matches (NaN equals nothing); custom types do not compare it.
        contamination != null ? (float)Get(contamination, "DefaultContamination") : float.NaN,
        Spec("BadtideWaterSourceContaminationControllerSpec") != null, depth != null ? (double?)(float)Get(depth, "DepthLimit") : null,
        Spec("UndergroundWaterSourceSpec") != null, weathers != null ? ((IEnumerable<string>)Get(weathers, "ActiveInHazardousWeather")).ToArray() : new string[0],
        Spec("DirectionalWaterSourceSpec") != null);
    }

    public static TemplateModule Module() {
      var builder = new TemplateModule.Builder();
      builder.AddDecorator<WaterSource, FluidPlacedSource>();
      return builder.Build();
    }

    /// <summary>The native members placed-source classification reads; empty when the installed game matches 1.1.2.8.</summary>
    public static IReadOnlyList<string> CheckContract() {
      var problems = new List<string>();
      var assembly = typeof(WaterSource).Assembly;
      void Property(string type, string name, Func<Type, bool> expected) {
        var t = assembly.GetType(Specs + type);
        var p = t?.GetProperty(name, Members);
        if (p == null || !expected(p.PropertyType)) problems.Add(type + "." + name);
      }
      Property("WaterSourceSpec", "Coordinates", t => t.GetProperty("Length")?.PropertyType == typeof(int));
      Property("WaterSourceSpec", "DefaultStrength", t => t == typeof(float));
      Property("WaterSourceContaminationSpec", "DefaultContamination", t => t == typeof(float));
      Property("WaterDepthStrengthModifierSpec", "DepthLimit", t => t == typeof(float));
      Property("HazardousWeatherWaterSourceSpec", "ActiveInHazardousWeather", t => typeof(IEnumerable<string>).IsAssignableFrom(t));
      foreach (string marker in new[] { "BadtideWaterSourceContaminationControllerSpec", "UndergroundWaterSourceSpec", "DirectionalWaterSourceSpec" })
        if (assembly.GetType(Specs + marker) == null) problems.Add(marker);
      var drought = assembly.GetType(Specs + "DroughtWaterStrengthModifier");
      if (drought == null || !typeof(IWaterStrengthModifier).IsAssignableFrom(drought)) problems.Add("DroughtWaterStrengthModifier : IWaterStrengthModifier");
      if (typeof(WaterSource).GetMethod("AddWaterStrengthModifier", new[] { typeof(IWaterStrengthModifier) }) == null
          || typeof(WaterSource).GetMethod("RemoveWaterStrengthModifier", new[] { typeof(IWaterStrengthModifier) }) == null)
        problems.Add("WaterSource.AddWaterStrengthModifier/RemoveWaterStrengthModifier(IWaterStrengthModifier)");
      if (typeof(TemplateSpec).GetProperty("TemplateName")?.PropertyType != typeof(string)) problems.Add("TemplateSpec.TemplateName : string");
      if (typeof(EntityComponent).GetProperty("EntityId")?.PropertyType != typeof(Guid)) problems.Add("EntityComponent.EntityId : Guid");
      if (typeof(BaseComponent).GetProperty("AllComponents") == null) problems.Add("BaseComponent.AllComponents");
      return problems;
    }
  }
}
