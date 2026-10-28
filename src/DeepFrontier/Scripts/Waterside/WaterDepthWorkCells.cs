using System;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.Linq;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockingSystem;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.Common;
using Timberborn.EntitySystem;
using Timberborn.Localization;
using Timberborn.StatusSystem;
using Timberborn.TickSystem;
using Timberborn.WaterBuildings;
using UnityEngine;

namespace DeepFrontier.Scripts {
  internal record WaterDepthWorkCellsSpec : ComponentSpec {
    // Local block coordinates (same frame as BlockObjectSpec.Blocks; BaseZ is
    // not added) inside the footprint. Each cell is sampled through the open
    // native water column containing it. WorkCells[0] also supplies the
    // contamination sample for the native ContaminationBlockableBuilding.
    [Serialize] public ImmutableArray<Vector3Int> WorkCells { get; init; }
    // The water surface must stand at least this far above the working
    // cell's own floor (native TickableWaterBuilding MinWaterHeight rule).
    [Serialize] public float MinDepth { get; init; }
    // Most water the cell's open column may hold, riverbed/floor to surface.
    [Serialize] public float MaxDepth { get; init; }
    // Band around each limit, as native TickableWaterBuildingSpec.ChangeRange.
    [Serialize] public float Hysteresis { get; init; }
  }

  // Replaces TickableWaterBuilding for buildings whose working cells need a
  // water depth range. As the only IWaterNeedingBuilding on the entity it also
  // receives native NeedsWaterBuildingStatus, WaterBuildingDescriber and
  // ContaminationBlockableBuilding through their interface decorators.
  internal sealed class WaterDepthWorkCells : TickableComponent, IAwakableComponent, IInitializableEntity,
      IPostLoadableEntity, IFinishedStateListener, IWaterNeedingBuilding {
    private readonly WatersideSurvey _survey;
    private readonly ILoc _loc;
    private BlockObject _block;
    private BlockableObject _blockable;
    private StatusToggle _tooDeepStatus;
    private WaterRangeState[] _states;
    private bool _needsWater,_tooDeep,_blocked;
    public WaterDepthWorkCellsSpec Spec { get; private set; }
    public IReadOnlyList<WaterRangeState> States=>_states;
    public bool IsBlockedByDepth=>_blocked;

    public Vector3Int WaterCoordinatesTransformed=>
      _survey.ContaminationSampleCell(_block.TransformCoordinates(Spec.WorkCells[0]));
    public event EventHandler StartedNeedingWater;
    public event EventHandler StoppedNeedingWater;

    public WaterDepthWorkCells(WatersideSurvey survey,ILoc loc) {_survey=survey;_loc=loc;}

    public void Awake() {
      Spec=GetComponent<WaterDepthWorkCellsSpec>();_block=GetComponent<BlockObject>();
      _blockable=GetComponent<BlockableObject>();
      Validate(Spec,GetComponent<BlockObjectSpec>().Size);
      var needers=new List<IWaterNeedingBuilding>();GetComponents(needers);
      if(needers.Count!=1)
        throw new InvalidOperationException("WaterDepthWorkCellsSpec replaces TickableWaterBuildingSpec/WaterNeederSpec; only one IWaterNeedingBuilding is allowed per entity");
      if(_blockable==null)throw new InvalidOperationException("WaterDepthWorkCells requires native BlockableObject");
      _states=Enumerable.Repeat(WaterRangeState.InRange,Spec.WorkCells.Length).ToArray();
      _tooDeepStatus=StatusToggle.CreateNormalStatusWithAlertAndFloatingIcon("FloodedBuilding",
        _loc.T(WatersideLoc.StatusWaterTooDeep),_loc.T(WatersideLoc.StatusWaterTooDeepShort));
      DisableComponent();
    }

    internal static void Validate(WaterDepthWorkCellsSpec spec,Vector3Int size) {
      if(spec.WorkCells.IsDefaultOrEmpty||spec.WorkCells.Distinct().Count()!=spec.WorkCells.Length)
        throw new InvalidOperationException("Water depth work cells must be a non-empty set of distinct cells");
      foreach(var c in spec.WorkCells)
        if(c.x<0||c.y<0||c.x>=size.x||c.y>=size.y||c.z>=size.z)
          throw new InvalidOperationException($"Water depth work cell {c} lies outside the building footprint");
      if(!float.IsFinite(spec.MinDepth)||!float.IsFinite(spec.MaxDepth)||!float.IsFinite(spec.Hysteresis)
        ||spec.Hysteresis<0||spec.MinDepth-spec.Hysteresis<=0||spec.MinDepth+spec.Hysteresis>=spec.MaxDepth-spec.Hysteresis)
        throw new InvalidOperationException("Water depth range needs 0 < MinDepth-Hysteresis and MinDepth+Hysteresis < MaxDepth-Hysteresis");
    }

    public void InitializeEntity()=>GetComponent<StatusSubject>().RegisterStatus(_tooDeepStatus);

    public void OnEnterFinishedState() {EnableComponent();Evaluate();}
    public void OnExitFinishedState()=>DisableComponent();
    public void PostLoadEntity() {if(Enabled)Evaluate();}
    public override void Tick()=>Evaluate();

    private void Evaluate() {
      bool shallow=false,deep=false;
      for(int i=0;i<_states.Length;i++) {
        var reading=_survey.ReadWorkCell(_block.TransformCoordinates(Spec.WorkCells[i]));
        _states[i]=WatersideSurvey.Next(_states[i],reading,Spec.MinDepth,Spec.MaxDepth,Spec.Hysteresis);
        shallow|=_states[i]==WaterRangeState.Shallow;deep|=_states[i]==WaterRangeState.Deep;
      }
      bool blocked=shallow||deep;
      if(blocked!=_blocked) {
        if(blocked)_blockable.Block(this);else _blockable.Unblock(this);
        _blocked=blocked;
      }
      if(shallow!=_needsWater) {
        _needsWater=shallow;
        (shallow?StartedNeedingWater:StoppedNeedingWater)?.Invoke(this,EventArgs.Empty);
      }
      if(deep!=_tooDeep) {
        _tooDeep=deep;
        if(deep)_tooDeepStatus.Activate();else _tooDeepStatus.Deactivate();
      }
    }
  }

  // Soft preview warning (native WaterInputPipeValidator pattern): placement
  // stays allowed, the preview turns the warning colour and shows the text.
  internal sealed class WaterDepthPreviewValidator : BaseComponent, IAwakableComponent, IPreviewValidator {
    private static readonly ReadOnlyHashSet<BaseComponent> NoObjects=new HashSet<BaseComponent>().AsReadOnlyHashSet();
    private readonly WatersideSurvey _survey;
    private readonly ILoc _loc;
    private BlockObject _block;
    private WaterDepthWorkCellsSpec _spec;
    public WaterDepthPreviewValidator(WatersideSurvey survey,ILoc loc) {_survey=survey;_loc=loc;}
    public void Awake() {_block=GetComponent<BlockObject>();_spec=GetComponent<WaterDepthWorkCellsSpec>();}

    public bool IsValid(out string warningMessage) {
      warningMessage=string.Empty;
      if(!_block.Positioned)return true;
      int shallow=0,deep=0;
      foreach(var cell in _spec.WorkCells) {
        var reading=_survey.ReadWorkCell(_block.TransformCoordinates(cell));
        switch(WatersideSurvey.Classify(reading,_spec.MinDepth,_spec.MaxDepth)) {
          case WaterRangeState.Shallow:shallow++;break;
          case WaterRangeState.Deep:deep++;break;
        }
      }
      if(shallow==0&&deep==0)return true;
      // Native PreviewShower asks every frame; the text changes only with the counts.
      if(_message==null||shallow!=_shallow||deep!=_deep) {
        string shallowText=shallow>0?_loc.T(WatersideLoc.WorkCellsTooShallow,shallow,WatersideLoc.Meters(_spec.MinDepth)):null;
        string deepText=deep>0?_loc.T(WatersideLoc.WorkCellsTooDeep,deep,WatersideLoc.Meters(_spec.MaxDepth)):null;
        _message=shallowText!=null&&deepText!=null?shallowText+"\n"+deepText:shallowText??deepText;
        _shallow=shallow;_deep=deep;
      }
      warningMessage=_message;
      return false;
    }
    private string _message;
    private int _shallow,_deep;

    public ReadOnlyHashSet<BaseComponent> InvalidatedObjects(out string warningMessage) {
      warningMessage=string.Empty;
      return NoObjects;
    }
  }
}
