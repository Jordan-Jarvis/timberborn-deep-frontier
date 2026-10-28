using Timberborn.BaseComponentSystem;
using Timberborn.Bots;
using Timberborn.Coordinates;
using Timberborn.Effects;
using Timberborn.EnterableSystem;
using Timberborn.NeedSystem;
using Timberborn.TickSystem;
using Timberborn.TimeSystem;
using Timberborn.BlockSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Breathing smog, modelled on the native RangedEffectSubject: inside a
  // building a beaver breathes that building's footprint average (homes and
  // workplaces); outside, its own map column. Exposure lowers the never-
  // positive Smog need (and HeavySmog in heavy smog) at
  // ExposurePointsPerHour * intensity; their native DailyDelta recovers them
  // once the beaver leaves. Each need costs its UnfavorableWellbeing while
  // below zero. Bots do not breathe and are left alone by design.
  internal sealed class SmogExposure : TickableComponent, IAwakableComponent {
    private readonly SmogService _smog;
    private readonly IDayNightCycle _cycle;
    private NeedManager _needs;
    private Enterer _enterer;

    public SmogExposure(SmogService smog,IDayNightCycle cycle) {_smog=smog;_cycle=cycle;}

    public void Awake() {
      _needs=GetComponent<NeedManager>();
      _enterer=GetComponent<Enterer>();
      if(HasComponent<BotSpec>()||!_needs)DisableComponent();
    }

    public float CurrentIntensity=>_enterer.IsInside
      ? _smog.BuildingIntensity(_enterer.CurrentBuilding.GetComponent<BlockObject>())
      : _smog.IntensityAt(Cell(Transform.position));

    private static Vector2Int Cell(Vector3 world) {
      Vector3Int g=CoordinateSystem.WorldToGridInt(world);
      return new Vector2Int(g.x,g.y);
    }

    public override void Tick() {
      float intensity=CurrentIntensity;
      if(!_smog.IsLight(intensity))return;
      SmogSettingsSpec s=_smog.Settings;
      float hours=_cycle.FixedDeltaTimeInHours,points=-s.ExposurePointsPerHour*intensity;
      _needs.ApplyEffect(new ContinuousEffect(s.LightNeedId,points),hours);
      if(_smog.IsHeavy(intensity))_needs.ApplyEffect(new ContinuousEffect(s.HeavyNeedId,points),hours);
    }
  }
}
