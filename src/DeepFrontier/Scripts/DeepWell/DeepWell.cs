using System;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.Linq;
using System.Reflection;
using Bindito.Core;
using DeepFrontier.Scripts.RadioactiveTide;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockingSystem;
using Timberborn.BlockObjectModelSystem;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.Common;
using Timberborn.Buildings;
using Timberborn.DuplicationSystem;
using Timberborn.EntitySystem;
using Timberborn.GameWaterSourceSystem;
using Timberborn.GoodConsumingBuildingSystem;
using Timberborn.HazardousWeatherSystem;
using Timberborn.Localization;
using Timberborn.MechanicalSystem;
using Timberborn.Persistence;
using Timberborn.SingletonSystem;
using Timberborn.StatusSystem;
using Timberborn.TemplateInstantiation;
using Timberborn.TickSystem;
using Timberborn.TimbermeshAnimations;
using Timberborn.TimeSystem;
using Timberborn.WaterSourceSystem;
using Timberborn.WeatherSystem;
using Timberborn.WorldPersistence;
using UnityEngine;

namespace DeepFrontier.Scripts.DeepWell {
  // Deep Well (tools/deep_well_content.mjs, docs in the generator header): a
  // powered, worker-free building whose DRILL cell hangs over a native map
  // water source (1x1 Water/Badwater Source cell, a Water/Badwater Seep cell or
  // a 3x3 Badwater Source cell). The drill block is MatterBelow Any /
  // Occupations None, so it never conflicts with the source's own block, and
  // the anchor cell stands on ground. Timberborn 1.1.2.8 cannot bind a source
  // through such a block (UnderstructureFinder reads Top/Corners foundation
  // blocks only), so DeepWellPlacementValidator (native IBlockObjectValidator)
  // requires the source and DeepWell links it.
  //
  // While running (finished, unblocked, linked, the source activated, drill
  // bits in stock, powered, not shut off for the tide) it is an
  // IWaterStrengthModifier of the source returning 1 + (Boost - 1) x the
  // network's power efficiency; the native WaterSource multiplies it into
  // CurrentStrength and caps it at MaxWaterSourceStrength (8) per source cell.
  // While running it also removes the seep's WaterDepthStrengthModifier (the
  // seep pours like a normal source) and disables the native
  // DroughtWaterStrengthModifier (the source keeps flowing in drought; under
  // Moddable Weathers its replacement Disable sets IgnoreDrought).
  //
  // Drought (user 2026-10-30: the well was too strong in droughts). While the
  // weather is hazardous and the cycle's IHazardousWeather has the native
  // DroughtWeather id ("DroughtWeather": native DroughtWeather and Moddable
  // Weathers' GameDroughtWeather, the same test as the tide below), the
  // power demand is DroughtPowerInput at any boost (input multiplier
  // DroughtPowerInput / PowerInput), the well runs only on full power (native
  // PowerEfficiency 1: supply covers every demand on the network), and the
  // boost is min(Boost, DroughtMaxBoost); drill bits follow that boost.
  // Short of full power it does not run, so the drought modifier stays on
  // and the source dries up like any other. The slider keeps its setting.
  //
  // With the
  // tide checkbox on and the Radioactive Tide current (the cycle's
  // IHazardousWeather has id RadioactiveTideWeather while the weather is
  // hazardous: the vanilla and Moddable Weathers paths), the modifier is 0:
  // the source pours nothing. Otherwise it is 1 (native behaviour).
  //
  // Power draw: MechanicalNodeSpec.PowerInput x Boost / MaxBoost through the
  // native MechanicalNode.SetInputMultiplier, 0 while it cannot run.
  // Drill bits: the native GoodConsumingBuilding (no workplace; haulers fill
  // it) at DrillBitsPerBoostStepPerHour x Boost. Its spec field has no
  // setter, so the rate is written as SpecialistSchool writes it; the
  // blueprint's own rate is the full-boost rate, which sizes the inventory.
  internal record DeepWellSpec : ComponentSpec {
    [Serialize] public Vector3Int DrillCell { get; init; }
    [Serialize] public int MaxBoost { get; init; }
    [Serialize] public int DefaultBoost { get; init; }
    [Serialize] public bool DefaultShutOffDuringTide { get; init; }
    [Serialize] public string DrillBitGoodId { get; init; }
    [Serialize] public float DrillBitsPerBoostStepPerHour { get; init; }
    [Serialize] public int DroughtMaxBoost { get; init; }
    [Serialize] public int DroughtPowerInput { get; init; }
  }

  internal static class DeepWellLoc {
    public const string NoSource = "DeepFrontier.DeepWell.Placement.NoSource";
    public const string SourceTaken = "DeepFrontier.DeepWell.Placement.SourceTaken";
    public const string SourceControlled = "DeepFrontier.DeepWell.Placement.SourceControlled";
    public const string StatusNoDrillBits = "DeepFrontier.DeepWell.Status.NoDrillBits";
    public const string StatusNoDrillBitsShort = "DeepFrontier.DeepWell.Status.NoDrillBits.Short";
    public const string StatusNoSource = "DeepFrontier.DeepWell.Status.NoSource";
    public const string StatusNoSourceShort = "DeepFrontier.DeepWell.Status.NoSource.Short";
    public const string PanelTitle = "DeepFrontier.DeepWell.Panel.Title";
    public const string PanelBoost = "DeepFrontier.DeepWell.Panel.Boost";
    public const string PanelBoostValue = "DeepFrontier.DeepWell.Panel.BoostValue";
    public const string PanelTide = "DeepFrontier.DeepWell.Panel.ShutOffDuringTide";
    public const string PanelDemand = "DeepFrontier.DeepWell.Panel.Demand";
    public const string PanelDrillBits = "DeepFrontier.DeepWell.Panel.DrillBits";
    public const string PanelSource = "DeepFrontier.DeepWell.Panel.Source";
    public const string PanelSeep = "DeepFrontier.DeepWell.Panel.Seep";
    public const string PanelDrought = "DeepFrontier.DeepWell.Panel.Drought";
    public const string PanelCapped = "DeepFrontier.DeepWell.Panel.Capped";
    public const string State = "DeepFrontier.DeepWell.State.";
  }

  internal enum DeepWellState { UnderConstruction, NoSource, Paused, TideShutOff, SourceDormant, NoDrillBits, NoPower, DroughtNoPower, Boosting, DroughtBoosting }

  // One Deep Well per water source: two would multiply their boosts.
  internal sealed class DeepWellRegistry {
    private readonly Dictionary<WaterSource, DeepWell> _wells = new();
    public bool TryGet(WaterSource source, out DeepWell well) => _wells.TryGetValue(source, out well);
    public void Add(WaterSource source, DeepWell well) {
      if (_wells.TryGetValue(source, out var other) && other != well)
        throw new InvalidOperationException($"{well.Name}: water source {source.Name} is already boosted by {other.Name}");
      _wells[source] = well;
    }
    public void Remove(WaterSource source, DeepWell well) {
      if (_wells.TryGetValue(source, out var other) && other == well) _wells.Remove(source);
    }
  }

  internal static class DeepWellSources {
    // The native water source whose cell is the drill cell, or null.
    public static WaterSource At(IBlockService blocks, Vector3Int cell) {
      foreach (var blockObject in blocks.GetObjectsAt(cell)) {
        var source = blockObject.GetComponent<WaterSource>();
        if (source && source.Coordinates.Contains(cell)) return source;
      }
      return null;
    }

    // True when a native building already controls the source from above
    // (Badwater Pressurizer, Badwater Dome or Rig, Aquifer Drill: they bind
    // it through UnderlyingWaterSource and change its drought modifier).
    public static bool ControlledByNativeBuilding(IBlockService blocks, WaterSource source) {
      foreach (var cell in source.Coordinates)
        foreach (var blockObject in blocks.GetObjectsAt(cell))
          if (blockObject.GetComponent<UnderlyingWaterSource>()) return true;
      return false;
    }
  }

  internal sealed class DeepWellPlacementValidator : IBlockObjectValidator {
    private readonly IBlockService _blocks;
    private readonly DeepWellRegistry _registry;
    private readonly ILoc _loc;

    public DeepWellPlacementValidator(IBlockService blocks, DeepWellRegistry registry, ILoc loc) {
      _blocks = blocks; _registry = registry; _loc = loc;
    }

    // Placement only: a placed or loaded Deep Well is not re-validated
    // (BlockObjectBatchLoader adds objects of one layer in an order that can
    // put the well before its source); DeepWell idles without a source.
    public bool IsValid(BlockObject blockObject, out string errorMessage) {
      errorMessage = null;
      var spec = blockObject.GetComponent<DeepWellSpec>();
      if (spec == null || !blockObject.IsPreview) return true;
      var source = DeepWellSources.At(_blocks, blockObject.TransformCoordinates(spec.DrillCell));
      if (!source) errorMessage = _loc.T(DeepWellLoc.NoSource);
      else if (_registry.TryGet(source, out _)) errorMessage = _loc.T(DeepWellLoc.SourceTaken);
      else if (DeepWellSources.ControlledByNativeBuilding(_blocks, source)) errorMessage = _loc.T(DeepWellLoc.SourceControlled);
      return errorMessage == null;
    }
  }

  internal sealed class DeepWell : TickableComponent, IAwakableComponent, IInitializableEntity, IFinishedStateListener,
      IPersistentEntity, IDeletableEntity, IWaterStrengthModifier, IDuplicable<DeepWell> {
    private static readonly ComponentKey Key = new("DeepFrontier.DeepWell");
    private static readonly PropertyKey<int> BoostKey = new("Boost");
    private static readonly PropertyKey<bool> TideKey = new("ShutOffDuringTide");
    // Native member without a public writer (Timberborn 1.1.2.8); a missing one fails at load.
    private static readonly FieldInfo ConsumerSpecField = RequireField(typeof(GoodConsumingBuilding), "_goodConsumingBuildingSpec", typeof(GoodConsumingBuildingSpec));

    private readonly IBlockService _blocks;
    private readonly DeepWellRegistry _registry;
    private readonly EventBus _eventBus;
    private readonly WeatherService _weather;
    private readonly HazardousWeatherService _hazardousWeather;
    private readonly DroughtWeather _droughtWeather;
    private readonly NonlinearAnimationManager _animation;
    private readonly WaterStrengthService _strength;
    private readonly ILoc _loc;
    private DeepWellSpec _spec;
    private BlockObject _blockObject;
    private BlockableObject _blockable;
    private MechanicalNode _node;
    private GoodConsumingBuilding _consumer;
    private GoodConsumingBuildingSpec _consumerSpec;
    private GoodConsumingToggle _toggle;
    private IAnimator _animator;
    private StatusToggle _noDrillBits, _noSource;
    private bool _finished, _registeredEvents, _effectsApplied, _modifierAdded, _modelHidden;
    private IWaterStrengthModifier _removedSeepModifier;
    private DroughtWaterStrengthModifier _disabledDrought;
    private float _modifier = 1f;
    private int _rateBoost;

    public DeepWell(IBlockService blocks, DeepWellRegistry registry, EventBus eventBus, WeatherService weather,
        HazardousWeatherService hazardousWeather, DroughtWeather droughtWeather, NonlinearAnimationManager animation, WaterStrengthService strength, ILoc loc) {
      _blocks = blocks; _registry = registry; _eventBus = eventBus; _weather = weather;
      _hazardousWeather = hazardousWeather; _droughtWeather = droughtWeather; _animation = animation; _strength = strength; _loc = loc;
    }

    public int Boost { get; private set; }
    public int MaxBoost => _spec.MaxBoost;
    public int DroughtMaxBoost => _spec.DroughtMaxBoost;
    public int DroughtPowerInput => _spec.DroughtPowerInput;
    public bool ShutOffDuringTide { get; private set; }
    public WaterSource Source { get; private set; }
    public DeepWellState State { get; private set; }
    public float StrengthModifier => _modifier;
    public bool IsSeep => Source && Source.GetComponent<WaterDepthStrengthModifier>();
    // The boost the well drives now: the slider, capped during a drought.
    public int EffectiveBoost => DroughtActive ? Mathf.Min(Boost, _spec.DroughtMaxBoost) : Boost;
    public int PowerDemandAtBoost => Mathf.CeilToInt(PowerInput * DemandMultiplier);
    public float DrillBitsPerHour => _spec.DrillBitsPerBoostStepPerHour * EffectiveBoost;
    public float HoursOfDrillBits => _consumer.HoursUntilNoSupply();
    // The native per-cell maximum (WaterStrengthSpec.MaxWaterSourceStrength) cuts the boost.
    public bool IsCapped => State == DeepWellState.Boosting
      && Source.SpecifiedStrength * _modifier > _strength.MaxWaterSourceStrength * Source.Coordinates.Length;
    public bool TideActive => _weather.IsHazardousWeather && _hazardousWeather.CurrentCycleHazardousWeather?.Id == RadioactiveTideTuning.WeatherId;
    public bool DroughtActive => _weather.IsHazardousWeather && _hazardousWeather.CurrentCycleHazardousWeather?.Id == _droughtWeather.Id;
    private int PowerInput => _node.GetComponent<MechanicalNodeSpec>().PowerInput;
    // Native input multiplier while the well demands power.
    private float DemandMultiplier => DroughtActive ? (float)_spec.DroughtPowerInput / PowerInput : (float)Boost / _spec.MaxBoost;

    private static FieldInfo RequireField(Type type, string name, Type fieldType) {
      var field = type.GetField(name, BindingFlags.Instance | BindingFlags.NonPublic);
      if (field == null || field.FieldType != fieldType)
        throw new InvalidOperationException($"Deep Well: native {type.Name}.{name} : {fieldType.Name} was not found");
      return field;
    }

    public void Awake() {
      _spec = GetComponent<DeepWellSpec>();
      _blockObject = GetComponent<BlockObject>();
      _blockable = GetComponent<BlockableObject>();
      _node = GetComponent<MechanicalNode>();
      _consumer = GetComponent<GoodConsumingBuilding>();
      _consumerSpec = GetComponent<GoodConsumingBuildingSpec>();
      if (_spec.MaxBoost < 1 || _spec.DefaultBoost < 1 || _spec.DefaultBoost > _spec.MaxBoost || !(_spec.DrillBitsPerBoostStepPerHour > 0f))
        throw new InvalidOperationException($"{Name}: DeepWellSpec needs 1 <= DefaultBoost <= MaxBoost and a positive drill-bit rate");
      if (_spec.DroughtMaxBoost < 1 || _spec.DroughtMaxBoost >= _spec.MaxBoost)
        throw new InvalidOperationException($"{Name}: DeepWellSpec needs 1 <= DroughtMaxBoost < MaxBoost");
      if (!_blockObject || !_blockable || !_node || !_consumer || _consumerSpec == null)
        throw new InvalidOperationException($"{Name}: a Deep Well needs BlockObject, BlockableObject, MechanicalNode and GoodConsumingBuilding");
      if (_spec.DroughtPowerInput <= PowerInput)
        throw new InvalidOperationException($"{Name}: DeepWellSpec.DroughtPowerInput must exceed the full-boost MechanicalNodeSpec.PowerInput {PowerInput}");
      if (_consumerSpec.ConsumedGoods.Length != 1 || _consumerSpec.ConsumedGoods[0].GoodId != _spec.DrillBitGoodId
          || !Mathf.Approximately(_consumerSpec.ConsumedGoods[0].GoodPerHour, _spec.DrillBitsPerBoostStepPerHour * _spec.MaxBoost))
        throw new InvalidOperationException($"{Name}: GoodConsumingBuildingSpec must consume only {_spec.DrillBitGoodId} at the full-boost rate");
      var finished = GameObject.FindChildIfNameNotEmpty(GetComponent<BuildingModelSpec>().FinishedModelName);
      _animator = finished.GetComponentsInChildren<MonoBehaviour>(true).OfType<IAnimator>().Single();
      _animator.Enabled = false;
      _toggle = _consumer.GetGoodConsumingToggle();
      Boost = _spec.DefaultBoost;
      _rateBoost = Boost;
      ShutOffDuringTide = _spec.DefaultShutOffDuringTide;
      DisableComponent();
    }

    public void Save(IEntitySaver entitySaver) {
      var saver = entitySaver.GetComponent(Key);
      saver.Set(BoostKey, Boost);
      saver.Set(TideKey, ShutOffDuringTide);
    }

    public void Load(IEntityLoader entityLoader) {
      var loader = entityLoader.GetComponent(Key);
      SetBoost(loader.Get(BoostKey));
      ShutOffDuringTide = loader.Get(TideKey);
    }

    public void DuplicateFrom(DeepWell source) {
      SetBoost(source.Boost);
      SetShutOffDuringTide(source.ShutOffDuringTide);
    }

    public void InitializeEntity() {
      ApplyConsumptionRate(Boost);
      if (_blockObject.IsPreview) return;
      _noDrillBits = StatusToggle.CreateNormalStatusWithAlertAndFloatingIcon("LackOfResources",
        _loc.T(DeepWellLoc.StatusNoDrillBits), _loc.T(DeepWellLoc.StatusNoDrillBitsShort));
      _noSource = StatusToggle.CreateNormalStatusWithAlertAndFloatingIcon("NothingToDo",
        _loc.T(DeepWellLoc.StatusNoSource), _loc.T(DeepWellLoc.StatusNoSourceShort));
      var statuses = GetComponent<StatusSubject>();
      statuses.RegisterStatus(_noDrillBits);
      statuses.RegisterStatus(_noSource);
      Source = DeepWellSources.At(_blocks, _blockObject.TransformCoordinates(_spec.DrillCell));
      if (Source) _registry.Add(Source, this);
      _eventBus.Register(this);
      _registeredEvents = true;
    }

    public void OnEnterFinishedState() {
      _finished = true;
      if (Source) Link();
      EnableComponent();
      Tick();
    }

    public void OnExitFinishedState() {
      _finished = false;
      Unlink();
      _toggle.PauseConsumption();
      _node.SetInputMultiplier(0f);
      _noDrillBits?.Deactivate();
      _noSource?.Deactivate();
      State = DeepWellState.UnderConstruction;
      DisableComponent();
    }

    public void DeleteEntity() {
      Unlink();
      if (Source) _registry.Remove(Source, this);
      if (_registeredEvents) _eventBus.Unregister(this);
      _registeredEvents = false;
    }

    [OnEvent]
    public void OnEntityDeleted(EntityDeletedEvent deleted) {
      if (!Source || deleted.Entity.GetComponent<WaterSource>() != Source) return;
      Unlink();
      _registry.Remove(Source, this);
      Source = null;
      Tick();
    }

    public void SetBoost(int boost) {
      if (boost < 1 || boost > _spec.MaxBoost) throw new ArgumentOutOfRangeException(nameof(boost), boost, $"{Name}: boost must be 1..{_spec.MaxBoost}");
      if (boost == Boost) return;
      Boost = boost;
      ApplyConsumptionRate(EffectiveBoost);
    }

    public void SetShutOffDuringTide(bool value) => ShutOffDuringTide = value;

    public float GetStrengthModifier() => _modifier;

    public override void Tick() {
      _animator.Speed = _animation.SpeedMultiplier;
      bool linked = _finished && Source;
      bool tide = linked && ShutOffDuringTide && TideActive;
      bool drought = DroughtActive;
      int boost = EffectiveBoost;
      if (boost != _rateBoost) ApplyConsumptionRate(boost);
      bool dormant = linked && Source.GetComponent<WaterSourceActivator>().GetStrengthModifier() == 0f;
      bool drillBits = _consumer.CanUse;
      bool demand = linked && _blockable.IsUnblocked && !tide && !dormant && drillBits;
      _node.SetInputMultiplier(demand ? DemandMultiplier : 0f);
      // In a drought only full power runs the well (native efficiency is min(supply / demand, 1)).
      bool running = demand && _node.ActiveAndPowered && (drought ? _node.PowerEfficiency >= 1f : _node.PowerEfficiency > 0f);
      if (running) _toggle.ResumeConsumption(); else _toggle.PauseConsumption();
      State = !_finished ? DeepWellState.UnderConstruction
        : !Source ? DeepWellState.NoSource
        : tide ? DeepWellState.TideShutOff
        : !_blockable.IsUnblocked ? DeepWellState.Paused
        : dormant ? DeepWellState.SourceDormant
        : !drillBits ? DeepWellState.NoDrillBits
        : !running ? (drought ? DeepWellState.DroughtNoPower : DeepWellState.NoPower)
        : drought ? DeepWellState.DroughtBoosting
        : DeepWellState.Boosting;
      SetActive(_noSource, _finished && !Source);
      SetActive(_noDrillBits, linked && _blockable.IsUnblocked && !tide && !dormant && !drillBits);
      _modifier = tide ? 0f : running ? 1f + (boost - 1) * _node.PowerEfficiency : 1f;
      SetEffects(running);
    }

    private static void SetActive(StatusToggle status, bool active) {
      if (active) status.Activate(); else status.Deactivate();
    }

    private void ApplyConsumptionRate(int boost) {
      _rateBoost = boost;
      var good = new ConsumedGoodSpec { GoodId = _spec.DrillBitGoodId, GoodPerHour = _spec.DrillBitsPerBoostStepPerHour * boost };
      ConsumerSpecField.SetValue(_consumer, _consumerSpec with { ConsumedGoods = ImmutableArray.Create(good) });
    }

    private void Link() {
      if (!_modifierAdded) {
        Source.AddWaterStrengthModifier(this);
        _modifierAdded = true;
      }
      // A one-cell source's rock stands in the drill cell, under the wellhead.
      if (Source.Coordinates.Length == 1 && !_modelHidden) {
        Source.GetComponent<BlockObjectModel>().HideFullModelPermanently();
        _modelHidden = true;
      }
    }

    private void Unlink() {
      if (!Source) return;
      SetEffects(false);
      _modifier = 1f;
      if (_modifierAdded) Source.RemoveWaterStrengthModifier(this);
      _modifierAdded = false;
      if (_modelHidden) Source.GetComponent<BlockObjectModel>().UnhideFullModelPermanently();
      _modelHidden = false;
      _animator.Stop();
      _animator.Enabled = false;
    }

    // Seep depth limit and drought, removed only while running and restored
    // exactly as found.
    private void SetEffects(bool running) {
      if (running == _effectsApplied || !Source) return;
      _effectsApplied = running;
      if (running) {
        var seep = Source.GetComponent<WaterDepthStrengthModifier>();
        if (seep && Source.WaterStrengthModifiers.Contains(seep)) {
          Source.RemoveWaterStrengthModifier(seep);
          _removedSeepModifier = seep;
        }
        _disabledDrought = Source.GetComponent<DroughtWaterStrengthModifier>()
          ?? throw new InvalidOperationException($"{Name}: water source {Source.Name} has no native DroughtWaterStrengthModifier");
        _disabledDrought.Disable();
        _animator.Enabled = true;
        _animator.Play("Default");
      } else {
        if (_removedSeepModifier != null) Source.AddWaterStrengthModifier(_removedSeepModifier);
        _removedSeepModifier = null;
        _disabledDrought?.Enable();
        _disabledDrought = null;
        _animator.Stop();
        _animator.Enabled = false;
      }
    }
  }

  [Context("Game")]
  public sealed class DeepWellConfigurator : Configurator {
    protected override void Configure() {
      Bind<DeepWellRegistry>().AsSingleton();
      Bind<DeepWell>().AsTransient();
      MultiBind<IBlockObjectValidator>().To<DeepWellPlacementValidator>().AsSingleton();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }
    private static TemplateModule Provide() {
      var b = new TemplateModule.Builder();
      b.AddDecorator<DeepWellSpec, DeepWell>();
      return b.Build();
    }
  }
}
