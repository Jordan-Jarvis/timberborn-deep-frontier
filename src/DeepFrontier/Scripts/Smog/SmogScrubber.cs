using System;
using System.Collections.Generic;
using System.Linq;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockingSystem;
using Timberborn.BlockSystem;
using Timberborn.BuildingRange;
using Timberborn.ConstructionMode;
using Timberborn.CoreUI;
using Timberborn.EntityPanelSystem;
using Timberborn.Localization;
using Timberborn.MechanicalSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Smog Scrubber: cleans while finished, unblocked (not paused) and powered,
  // the same Active condition as the native RangedEffectBuilding. Its own
  // RangeName previews every scrubber's coverage together.
  internal sealed class SmogScrubber : BaseComponent, IAwakableComponent, IFinishedStateListener, IBuildingWithRange, IEntityDescriber {
    public const string Range="DeepFrontier.SmogScrubber";
    private readonly SmogService _smog;
    private readonly StackableBlockService _stackable;
    private readonly ConstructionModeService _constructionMode;
    private readonly ILoc _loc;
    private SmogScrubberSpec _spec;
    private BlockObjectCenter _center;
    private BlockableObject _blockable;
    private MechanicalBuilding _power;
    private bool _finished;

    public SmogScrubber(SmogService smog,StackableBlockService stackable,ConstructionModeService constructionMode,ILoc loc) {
      _smog=smog;_stackable=stackable;_constructionMode=constructionMode;_loc=loc;
    }

    public void Awake() {
      _spec=GetComponent<SmogScrubberSpec>();
      _center=GetComponent<BlockObjectCenter>();
      _blockable=GetComponent<BlockableObject>();
      _power=GetComponent<MechanicalBuilding>();
      if(!(_spec.Radius>0f)||!(_spec.Reduction>0f)||_spec.Reduction>1f)
        throw new InvalidOperationException("SmogScrubberSpec needs a positive radius and a reduction in (0, 1]");
      if(!_blockable||!_power)throw new InvalidOperationException("Smog scrubber needs BlockableObject and MechanicalBuilding (power)");
    }

    public float Radius=>_spec.Radius;
    public float Reduction=>_spec.Reduction;
    public Vector2 Center=>new Vector2(_center.GridCenter.x,_center.GridCenter.y);
    public bool IsCleaning=>_finished&&_blockable.IsUnblocked&&_power.ActiveAndPowered;
    public string RangeName=>Range;

    public void OnEnterFinishedState() {_finished=true;_smog.AddScrubber(this);}
    public void OnExitFinishedState() {_finished=false;_smog.RemoveScrubber(this);}

    public IEnumerable<Vector3Int> GetBlocksInRange()=>
      _stackable.GetGroundOrStackableBlocks(SmogService.CellsWithin(Center,_spec.Radius).Where(_smog.Contains),!_constructionMode.InConstructionMode);

    public IEnumerable<BaseComponent> GetObjectsInRange()=>Enumerable.Empty<BaseComponent>();

    public IEnumerable<EntityDescription> DescribeEntity() {
      string key=!_finished?"DeepFrontier.Smog.Scrubber.Planned":IsCleaning?"DeepFrontier.Smog.Scrubber.Active":"DeepFrontier.Smog.Scrubber.Idle";
      yield return EntityDescription.CreateTextSection(SpecialStrings.RowStarter
        +_loc.T(key,Mathf.RoundToInt(_spec.Reduction*100f),Mathf.CeilToInt(_spec.Radius)),1030);
    }
  }
}
