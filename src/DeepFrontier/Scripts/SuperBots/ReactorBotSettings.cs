using System;
using System.Collections.Immutable;
using System.Linq;
using Timberborn.BlueprintSystem;
using Timberborn.GameFactionSystem;
using Timberborn.Illumination;
using Timberborn.SingletonSystem;
using UnityEngine;

namespace DeepFrontier.Scripts.SuperBots {
  // Reactor Bots: an in-place upgrade of the ordinary bot (tools/super_bots.json,
  // written by tools/super_bot_content.mjs as the singleton
  // Data/Configurations/DeepFrontierReactorBots.blueprint.json). No defaults:
  // every value comes from the catalog.
  internal record FrontierReactorBotSettingsSpec : ComponentSpec {
    // Enabled only while a retrofit is queued; each is filled by one part's
    // ConsumptionEffects (taken from storage). All full completes the upgrade.
    [Serialize] public ImmutableArray<string> RetrofitNeedIds { get; init; }
    // Charged at the Reactor Charging Bay (its only AttractionSpec effect).
    [Serialize] public string ChargeNeedId { get; init; }
    // At its minimum the bot wears UnplatedWearMultiplier times faster.
    [Serialize] public string PlatingNeedId { get; init; }
    // Enabled only on Reactor Bots.
    [Serialize] public ImmutableArray<string> ReactorNeedIds { get; init; }
    // Vanilla bot needs a Reactor Bot loses (Energy: it never uses the vanilla Charging Station).
    [Serialize] public ImmutableArray<string> ReplacedNeedIds { get; init; }
    // Animator bool the vanilla bot template drives from Energy (CriticalNeedStateAnimationSpec).
    [Serialize] public string NoChargeAnimation { get; init; }
    // Native BonusManager delta on CarryingCapacity (bonus type clamps 0.1..10).
    [Serialize] public float CarryingCapacityBonus { get; init; }
    // Multiplies WalkerSpeedManager's base speed (the native MovementSpeed bonus clamps at 2.0).
    [Serialize] public float SpeedMultiplier { get; init; }
    // Divides every deterioration tick (native, workplace and unplated wear).
    [Serialize] public float LifespanMultiplier { get; init; }
    [Serialize] public float UnplatedWearMultiplier { get; init; }
    [Serialize] public string IlluminationColorId { get; init; }
    [Serialize] public Color Tint { get; init; }
  }

  internal sealed class ReactorBotSettings : ILoadableSingleton, IPostLoadableSingleton {
    private readonly ISpecService _specs;
    private readonly FactionNeedService _needs;
    private readonly IlluminationService _illumination;

    public FrontierReactorBotSettingsSpec Spec { get; private set; }
    public Color IlluminationColor { get; private set; }

    public ReactorBotSettings(ISpecService specs, FactionNeedService needs, IlluminationService illumination) {
      _specs=specs;_needs=needs;_illumination=illumination;
    }

    public void Load() {
      Spec=_specs.GetSingleSpec<FrontierReactorBotSettingsSpec>();
      if(Spec.ReactorNeedIds.IsDefaultOrEmpty||Spec.ReplacedNeedIds.IsDefaultOrEmpty||Spec.RetrofitNeedIds.IsDefaultOrEmpty)
        throw new InvalidOperationException("Reactor bots: settings list no retrofit, reactor or replaced needs; regenerate tools/super_bot_content.mjs");
      if(!Spec.ReactorNeedIds.Contains(Spec.ChargeNeedId)||!Spec.ReactorNeedIds.Contains(Spec.PlatingNeedId))
        throw new InvalidOperationException("Reactor bots: the charge and plating needs must be reactor needs");
      if(!(Spec.CarryingCapacityBonus>0f&&Spec.SpeedMultiplier>1f&&Spec.LifespanMultiplier>1f&&Spec.UnplatedWearMultiplier>1f))
        throw new InvalidOperationException("Reactor bots: invalid buff values in the settings");
      // Native FindColorById only warns on an unknown id; require the generated colour.
      if(!_specs.GetSpecs<IlluminationColorSpec>().Any(c=>c.Id==Spec.IlluminationColorId))
        throw new InvalidOperationException($"Reactor bots: illumination colour {Spec.IlluminationColorId} is not generated");
      // Injected services load first (native BotColors reads IlluminationService the same way).
      IlluminationColor=_illumination.FindColorById(Spec.IlluminationColorId);
    }

    // Faction needs are loaded by FactionNeedService.Load; check them after
    // (as WorkforceSettings does). Every switched need must be a current-faction
    // Bot need (Iron Teeth NeedCollection).
    public void PostLoad() {
      var botNeeds=_needs.GetBotNeeds().Select(n=>n.Id).ToImmutableHashSet();
      foreach(var id in Spec.ReactorNeedIds.Concat(Spec.ReplacedNeedIds).Concat(Spec.RetrofitNeedIds))
        if(!botNeeds.Contains(id))throw new InvalidOperationException($"Reactor bots: {id} is not a Bot need of the current faction");
    }
  }
}
