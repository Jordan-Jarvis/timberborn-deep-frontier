using System.Collections.Generic;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockSystem;
using Timberborn.CoreUI;
using Timberborn.EntityPanelSystem;
using Timberborn.EntitySystem;
using Timberborn.Forestry;
using Timberborn.Growing;
using Timberborn.Localization;
using Timberborn.NaturalResourcesLifecycle;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Every Growable (crops, trees, bushes): smog slows its growth, and living
  // trees and bushes clean the smog around them.
  //
  // Slowdown: once per GrowthIntervalHours the service hands each plant the
  // slowdown s of its cell. The native TimeTrigger advances only while in
  // progress (DaysLeft subtracts DaysSinceStart only when InProgress), so the
  // progress gained since the last charge is exactly the growth this plant
  // made at full speed, however much of the interval it was paused, dying or
  // newly planted. Setting it back by s times that growth leaves an effective
  // rate of (1 - s) for the time it actually grew. Nothing else lowers a
  // Growable's progress (its trigger is private; only this class passes a
  // negative IncreaseGrowthProgress), so the set-back never exceeds the
  // progress made. Progress itself is saved natively by Growable; the charge
  // baseline restarts at the loaded progress.
  internal sealed class SmogGrowth : BaseComponent, IAwakableComponent, IInitializableEntity, IDeletableEntity, IEntityDescriber {
    private readonly SmogService _smog;
    private readonly ILoc _loc;
    private BlockObject _blockObject;
    private LivingNaturalResource _living;
    private bool _tree, _bush, _registered;
    // Growable.GrowthProgress right after the last charge (or at registration).
    private float _chargedProgress;
    public Growable Growable { get; private set; }

    public SmogGrowth(SmogService smog,ILoc loc) {_smog=smog;_loc=loc;}

    public void Awake() {
      Growable=GetComponent<Growable>();
      _blockObject=GetComponent<BlockObject>();
      _living=GetComponent<LivingNaturalResource>();
      _tree=HasComponent<TreeComponentSpec>();
      _bush=HasComponent<BushSpec>();
    }

    public Vector2Int Cell=>new Vector2Int(_blockObject.Coordinates.x,_blockObject.Coordinates.y);

    // Greenery: grown trees/bushes at full value, saplings by growth, dead
    // (cut stumps, withered) none. Crops do not clean the air.
    public float GreeneryReduction {
      get {
        if(!(_tree||_bush)||_living.IsDead)return 0f;
        float full=_tree?_smog.Settings.TreeReduction:_smog.Settings.BushReduction;
        return full*(Growable.IsGrown?1f:Growable.GrowthProgress);
      }
    }

    // Every real plant counts; placement previews (BlockObject.MarkAsPreview-
    // AndInitialize) do not.
    public void InitializeEntity() {
      if(_blockObject.IsPreview)return;
      // Growable.Load (EntitiesLoader.Load) runs before every InitializeEntity,
      // so this is the loaded or freshly planted progress.
      _chargedProgress=Growable.GrowthProgress;
      _smog.AddGrowth(this);_registered=true;
    }

    public void DeleteEntity() {
      if(_registered){_smog.RemoveGrowth(this);_registered=false;}
    }

    // Charges only the growth made since the last charge. A paused (dying,
    // dead) plant is charged for what it grew before pausing;
    // TimeTrigger.FastForwardProgress resumes only a trigger that was in
    // progress, so this never restarts it. A grown plant (Finished) cannot be
    // set back and is skipped.
    public void ApplySlowdown(float slowdown) {
      float grown=Growable.GrowthProgress-_chargedProgress;
      if(slowdown>0f&&grown>0f&&!Growable.IsGrown)Growable.IncreaseGrowthProgress(-slowdown*grown);
      _chargedProgress=Growable.GrowthProgress;
    }

    public IEnumerable<EntityDescription> DescribeEntity() {
      if(!_registered)yield break;
      float intensity=_smog.IntensityAt(Cell);
      if(_smog.IsLight(intensity))
        yield return EntityDescription.CreateTextSection(SpecialStrings.RowStarter+_loc.T("DeepFrontier.Smog.Growth",
          Mathf.RoundToInt(intensity*100f),Mathf.RoundToInt(_smog.GrowthSlowdown(intensity)*100f)),2200);
      float greenery=GreeneryReduction;
      if(greenery>0f)
        yield return EntityDescription.CreateTextSection(SpecialStrings.RowStarter+_loc.T("DeepFrontier.Smog.Greenery",
          Mathf.RoundToInt(greenery*100f),Mathf.CeilToInt(_smog.Settings.GreeneryRadius)),2210);
    }
  }
}
