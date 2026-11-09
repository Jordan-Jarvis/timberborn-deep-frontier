using System;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.EntitySystem;
using Timberborn.MechanicalSystem;
using Timberborn.WaterSourceSystem;

namespace MoreFluids {
  /// <summary>Marks the buildable Healing Spring (<c>MoreFluidsHealingWell.&lt;Faction&gt;</c>), a building holding a native water source.</summary>
  internal record MoreFluidsHealingWellSpec : ComponentSpec { }

  /// <summary>
  /// Powers the buildable Healing Spring's native water source the way the vanilla Aquifer Drill
  /// (<c>UndergroundWaterSourceDrill</c>) powers an aquifer: strength × the mechanical node's power efficiency, and
  /// nothing while the building is unfinished, paused or unpowered. The native drought modifier stays, so the spring
  /// stops in droughts. Moddable Fluids makes its water healing water (source types <c>MoreFluids.HealingWell*</c>).
  /// </summary>
  internal sealed class HealingWellPump : BaseComponent, IAwakableComponent, IInitializableEntity, IFinishedStateListener, IWaterStrengthModifier {
    private WaterSource _source;
    private MechanicalNode _node;
    private bool _finished;

    public void Awake() {
      _source = GetComponent<WaterSource>();
      _node = GetComponent<MechanicalNode>();
      if (_source == null || _node == null) throw new InvalidOperationException("MoreFluidsHealingWellSpec requires the native WaterSource and MechanicalNode");
    }

    // Added at initialization, before the source's first strength update, so a construction site emits nothing.
    public void InitializeEntity() => _source.AddWaterStrengthModifier(this);

    public void OnEnterFinishedState() => _finished = true;

    public void OnExitFinishedState() => _finished = false;

    public float GetStrengthModifier() => _finished && _node.ActiveAndPowered ? _node.PowerEfficiency : 0f;
  }
}
