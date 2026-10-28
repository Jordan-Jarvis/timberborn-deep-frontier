#if !UNITY_EDITOR
using System;
using Bindito.Core;
using DeepFrontier.Scripts.Radiation;
using DeepFrontier.Scripts.Sensors;
using SluiceIsBack.Components;
using Timberborn.BaseComponentSystem;
using Timberborn.Persistence;
using Timberborn.TemplateInstantiation;
using Timberborn.WorldPersistence;
using UnityEngine;

namespace DeepFrontier.SluiceIsBackContamination {
  // What the Sluice of "Sluice is Back!" 11.0.0 measures for its contamination
  // automation ("Close above x% / below x% contamination", SluiceState
  // AutoCloseOnAbove/AutoCloseOnBelow with OnAboveLimit/OnBelowLimit). The
  // same choice as the Contamination Sensor (SensedSubstance):
  //   Badwater  native Sluice.GetContamination(), unchanged (the default, so
  //             existing sluices and saves behave as before)
  //   Radiation radioactive share r of the source column (IRadiationService.Sample)
  //   Any       badwater + radioactive share (one fluid: b + r <= 1)
  // each rounded as the native Sluice.GetContamination rounds
  // (Math.Round(share, 2)) and compared by the native automation with the
  // native limits (SluiceContaminationPatches.cs, a postfix on the private
  // GetContamination()).
  //
  // Synchronized sluices (SluiceState.IsSynchronized, the mod's neighbour
  // synchronizer) share the choice like their other settings: the native
  // SluiceState.SetState(neighbor, minLimit), which the synchronizer, the
  // copy-settings tool (Sluice.DuplicateFrom) and a newly placed neighbour
  // use, copies it (SluiceStateSynchronizationPatch).
  //
  // Unlike the Contamination Sensor, no saved radioactive share is needed:
  // the sluice measures only in its Tick, and a save's radiation is applied
  // before the first tick (RadiationSimulation.UpdateSingleton throws otherwise).
  public sealed class SluiceContaminationSubstance : BaseComponent, IAwakableComponent, IPersistentEntity, IContaminationSubstanceChoice {
    private static readonly ComponentKey Key = new("DeepFrontier.SluiceContaminationSubstance");
    private static readonly PropertyKey<SensedSubstance> SubstanceKey = new("Substance");

    private readonly IRadiationService _radiation;
    private Sluice _sluice;
    private SluiceState _state;

    public SensedSubstance Substance { get; private set; }
    public Sluice Sluice => _sluice;

    public SluiceContaminationSubstance(IRadiationService radiation) {
      _radiation = radiation;
    }

    public void Awake() {
      _sluice = GetComponent<Sluice>();
      _state = GetComponent<SluiceState>();
      if (!_state) throw new InvalidOperationException("Sluice is Back! sluice without its SluiceState decorator");
    }

    public void SetSubstance(SensedSubstance substance) {
      RequireDefined(substance);
      if (Substance == substance) return;
      Substance = substance;
      // The mod's own synchronization: SetStateAndSynchronize(this) keeps every
      // setting (it applies the same outflow clamp as Sluice.Tick) and passes
      // the state to the synchronized neighbours through SetState.
      if (_state.IsSynchronized) _state.SetStateAndSynchronize(_state, _sluice.MinHeight - _sluice.MaxHeight);
    }

    // SluiceState.SetState postfix: the neighbour's choice, without a further
    // synchronization (the mod's synchronizer walks the chain itself).
    internal void CopyFrom(SluiceContaminationSubstance neighbor) {
      RequireDefined(neighbor.Substance);
      Substance = neighbor.Substance;
    }

    // The value the native automation compares, for the source column at
    // `sourceCell`, given the native rounded badwater share.
    internal float Measure(Vector3Int sourceCell, float nativeBadwater) {
      if (Substance == SensedSubstance.Badwater) return nativeBadwater;
      return (float)Math.Round(Share(Read(sourceCell)), 2);
    }

    // Unrounded shares of the source column, for the panel.
    internal RadiationSample Read(Vector3Int sourceCell) => _radiation.Sample(sourceCell);

    internal float Share(RadiationSample sample) => Substance switch {
      SensedSubstance.Badwater => sample.BadwaterShare,
      SensedSubstance.Radiation => sample.WaterRadiation,
      SensedSubstance.Any => sample.BadwaterShare + sample.WaterRadiation,
      _ => throw new ArgumentOutOfRangeException(nameof(Substance), Substance, "Unknown sluice contamination substance"),
    };

    public void Save(IEntitySaver entitySaver) {
      entitySaver.GetComponent(Key).Set(SubstanceKey, Substance);
    }

    public void Load(IEntityLoader entityLoader) {
      // Saved before the option existed (or without Deep Frontier): the native badwater sluice.
      if (!entityLoader.TryGetComponent(Key, out var loader)) return;
      var substance = loader.Get(SubstanceKey);
      RequireDefined(substance);
      Substance = substance;
    }

    private static void RequireDefined(SensedSubstance substance) {
      if (!Enum.IsDefined(typeof(SensedSubstance), substance))
        throw new ArgumentOutOfRangeException(nameof(substance), substance, "Unknown sluice contamination substance");
    }
  }

  // Sluice is Back!'s own configurator (SluiceIsBack.MGameConfig) is
  // [Context("Game")], as is this.
  [Context("Game")]
  public sealed class SluiceContaminationConfigurator : Configurator {
    protected override void Configure() {
      Bind<SluiceContaminationSubstance>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }

    private static TemplateModule Provide() {
      var builder = new TemplateModule.Builder();
      builder.AddDecorator<Sluice, SluiceContaminationSubstance>();
      return builder.Build();
    }
  }
}
#endif
