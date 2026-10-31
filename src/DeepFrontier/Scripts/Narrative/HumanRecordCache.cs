using System;
using System.Collections.Generic;
using System.Linq;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockSystem;
using Timberborn.EntitySystem;
using Timberborn.Goods;
using Timberborn.Persistence;
using Timberborn.TickSystem;
using Timberborn.TimeSystem;
using Timberborn.Workshops;
using Timberborn.WorldPersistence;
using UnityEngine;

namespace DeepFrontier.Scripts.Narrative {
  internal enum HumanRecordCacheState { NoSurveyor, Idle, Surveying, WaitingForStorage, Surveyed }

  // Optional map evidence: a sealed human records box (map-editor object cloned
  // from the vanilla MediumRelic). The nearest finished workshop that runs the
  // survey recipe (the Archive Excavation's RecoveredArtifact) with an occupied cell
  // within SurveyRadius tiles horizontally and SurveyRadius layers vertically
  // surveys it while its workers work (native Workshop.CurrentlyWorking). After
  // SurveyHours of working time the cache gives RewardAmount RewardGoodId to
  // that workshop's native output inventory as unreserved capacity allows, then
  // reports the survey; the journal adds the next cache record. The native
  // relic demolition (and its science reward) is unchanged; demolishing before
  // the survey loses the records.
  internal sealed class HumanRecordCache : TickableComponent, IAwakableComponent, IFinishedStateListener, IPersistentEntity {
    private static readonly ComponentKey Key=new("DeepFrontier.HumanRecordCache");
    private static readonly PropertyKey<float> ProgressKey=new("SurveyHours");
    private static readonly PropertyKey<int> DeliveredKey=new("Delivered");
    private static readonly PropertyKey<bool> SurveyedKey=new("Surveyed");

    private readonly NarrativeObjectiveService _narrative;
    private readonly EntityComponentRegistry _registry;
    private readonly IDayNightCycle _cycle;
    private readonly RecipeSpecService _recipes;
    private BlockObject _block;
    private Vector3Int[] _cells=Array.Empty<Vector3Int>();
    private Manufactory _surveyor;
    private int _rescanTicks;

    public HumanRecordCacheSpec Spec { get; private set; }
    public float ProgressHours { get; private set; }
    public int Delivered { get; private set; }
    public bool Surveyed { get; private set; }
    public HumanRecordCacheState State { get; private set; }=HumanRecordCacheState.NoSurveyor;
    public float SurveyFraction=>ProgressHours/Spec.SurveyHours;

    public HumanRecordCache(NarrativeObjectiveService narrative,EntityComponentRegistry registry,IDayNightCycle cycle,RecipeSpecService recipes) {
      _narrative=narrative;_registry=registry;_cycle=cycle;_recipes=recipes;
    }

    public void Awake() {
      Spec=GetComponent<HumanRecordCacheSpec>();
      _block=GetComponent<BlockObject>();
      if(Spec.SurveyRadius<1||!(Spec.SurveyHours>0f)||Spec.RewardAmount<1||string.IsNullOrEmpty(Spec.RewardGoodId))
        throw new InvalidOperationException("Human Record Cache needs a positive radius, survey time and reward");
      var recipe=_recipes.GetRecipe(Spec.SurveyRecipeId);
      if(!recipe.Products.Any(p=>p.Id==Spec.RewardGoodId))
        throw new InvalidOperationException($"Human Record Cache reward {Spec.RewardGoodId} is not a product of survey recipe {Spec.SurveyRecipeId}");
      DisableComponent();
    }

    public void OnEnterFinishedState() {
      _cells=_block.PositionedBlocks.GetAllCoordinates().ToArray();
      _surveyor=null;_rescanTicks=0;
      State=Surveyed?HumanRecordCacheState.Surveyed:HumanRecordCacheState.NoSurveyor;
      if(!Surveyed)EnableComponent();
    }

    public void OnExitFinishedState() {
      _surveyor=null;
      DisableComponent();
    }

    public void Save(IEntitySaver saver) {
      var data=saver.GetComponent(Key);
      data.Set(ProgressKey,ProgressHours);data.Set(DeliveredKey,Delivered);data.Set(SurveyedKey,Surveyed);
    }

    public void Load(IEntityLoader loader) {
      // Map objects placed in the editor have no survey state yet.
      if(!loader.TryGetComponent(Key,out var data))return;
      ProgressHours=data.Get(ProgressKey);Delivered=data.Get(DeliveredKey);Surveyed=data.Get(SurveyedKey);
      if(ProgressHours<0f||ProgressHours>Spec.SurveyHours||Delivered<0||Delivered>Spec.RewardAmount
        ||(Delivered>0&&ProgressHours<Spec.SurveyHours)||Surveyed!=(Delivered==Spec.RewardAmount))
        throw new InvalidOperationException("Saved Human Record Cache survey state is inconsistent");
    }

    public override void Tick() {
      if(_surveyor!=null&&!_surveyor.Enabled)_surveyor=null;
      if(_surveyor==null||--_rescanTicks<=0) {
        _surveyor=FindSurveyor();
        _rescanTicks=_cycle.HoursToTicks(1f);
      }
      if(_surveyor==null) {State=HumanRecordCacheState.NoSurveyor;return;}
      if(ProgressHours<Spec.SurveyHours) {
        if(!_surveyor.GetComponent<Workshop>().CurrentlyWorking) {State=HumanRecordCacheState.Idle;return;}
        ProgressHours=Mathf.Min(Spec.SurveyHours,ProgressHours+_cycle.FixedDeltaTimeInHours);
        State=HumanRecordCacheState.Surveying;
        if(ProgressHours<Spec.SurveyHours)return;
      }
      int give=Mathf.Min(Spec.RewardAmount-Delivered,_surveyor.Inventory.UnreservedCapacity(Spec.RewardGoodId));
      if(give>0) {
        _surveyor.Inventory.GiveProduced(new GoodAmount(Spec.RewardGoodId,give));
        Delivered+=give;
        _narrative.ReportBonusGoods(Spec.RewardGoodId,give,_surveyor);
      }
      if(Delivered<Spec.RewardAmount) {State=HumanRecordCacheState.WaitingForStorage;return;}
      Surveyed=true;
      State=HumanRecordCacheState.Surveyed;
      _surveyor=null;
      _narrative.ReportCacheSurveyed(this);
      DisableComponent();
    }

    private Manufactory FindSurveyor() {
      Manufactory best=null;int bestDistance=int.MaxValue;
      foreach(var manufactory in _registry.GetEnabled<Manufactory>()) {
        if(!manufactory.ProductionRecipes.Any(r=>r.Id==Spec.SurveyRecipeId)||manufactory.GetComponent<Workshop>()==null)continue;
        int distance=Distance(manufactory.GetComponent<BlockObject>().PositionedBlocks.GetOccupiedCoordinates());
        if(distance<=Spec.SurveyRadius&&distance<bestDistance) {best=manufactory;bestDistance=distance;}
      }
      return best;
    }

    // Horizontal tile distance between footprints, counting only cells within
    // SurveyRadius layers of each other.
    private int Distance(IEnumerable<Vector3Int> others) {
      int best=int.MaxValue;
      foreach(var other in others)
        foreach(var cell in _cells) {
          if(Math.Abs(other.z-cell.z)>Spec.SurveyRadius)continue;
          best=Math.Min(best,Math.Max(Math.Abs(other.x-cell.x),Math.Abs(other.y-cell.y)));
        }
      return best;
    }
  }
}
