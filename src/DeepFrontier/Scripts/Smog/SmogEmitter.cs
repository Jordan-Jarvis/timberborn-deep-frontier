using System;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.Linq;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockSystem;
using Timberborn.BuildingRange;
using Timberborn.ConstructionMode;
using Timberborn.CoreUI;
using Timberborn.EnterableSystem;
using Timberborn.EntityPanelSystem;
using Timberborn.Localization;
using Timberborn.MechanicalSystem;
using Timberborn.Workshops;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // A polluting building. Pollutes only while finished and running the same
  // condition as its smoke particles (SmogEmitterSpec.Activity).
  //
  // IBuildingWithRange gives the native range preview: while placing or
  // selecting any polluter, the native RangeTileMarkerService tints the union
  // of every polluter's envelope (shared RangeName), RangeEnterableHighlighter
  // outlines enterable buildings inside it, and RangeObjectHighlighterService
  // shades the crops/trees returned by GetObjectsInRange. The envelope is the
  // flue radius plus the maximum wind drift, so homes outside it never smog.
  internal sealed class SmogEmitter : BaseComponent, IAwakableComponent, IFinishedStateListener, IBuildingWithRange, IEntityDescriber {
    public const string Range="DeepFrontier.Smog";
    internal readonly struct Source {
      public readonly Vector2 Center;public readonly float Radius;public readonly float Strength;
      public Source(Vector2 center,float radius,float strength) {Center=center;Radius=radius;Strength=strength;}
    }
    private readonly SmogService _smog;
    private readonly StackableBlockService _stackable;
    private readonly ConstructionModeService _constructionMode;
    private readonly ILoc _loc;
    private SmogEmitterSpec _spec;
    private BlockObject _blockObject;
    private Workshop _workshop;
    private MechanicalNode _generator;
    private Enterable _enterable;
    private bool _finished;
    public ImmutableArray<Source> Sources { get; private set; }

    public SmogEmitter(SmogService smog,StackableBlockService stackable,ConstructionModeService constructionMode,ILoc loc) {
      _smog=smog;_stackable=stackable;_constructionMode=constructionMode;_loc=loc;
    }

    public void Awake() {
      _spec=GetComponent<SmogEmitterSpec>();
      _blockObject=GetComponent<BlockObject>();
      if(_spec.Sources.IsDefaultOrEmpty||_spec.Sources.Any(s=>!(s.Radius>0f)||!(s.Strength>0f)||s.Strength>1f))
        throw new InvalidOperationException("SmogEmitterSpec needs flue sources with positive radius and strength in (0, 1]");
      if(_spec.Activity=="Workshop") {
        _workshop=GetComponent<Workshop>();
        if(!_workshop)throw new InvalidOperationException("Workshop smog emitter has no Workshop");
      } else if(_spec.Activity=="Generator") {
        // The native PowerGeneratorParticleController condition (Steam Engine pattern).
        _generator=GetComponent<MechanicalNode>();
        if(!_generator)throw new InvalidOperationException("Generator smog emitter has no MechanicalNode");
      } else if(_spec.Activity=="Occupied") {
        _enterable=GetComponent<Enterable>();
        if(!_enterable)throw new InvalidOperationException("Occupied smog emitter has no Enterable");
      } else throw new InvalidOperationException($"Unknown smog emitter activity {_spec.Activity}");
    }

    public bool IsPolluting=>_finished&&(_workshop?_workshop.CurrentlyWorking
      :_generator?_generator.ActiveAndPowered&&_generator.OutputMultiplier>0f
      :_enterable.NumberOfEnterersInside>0);
    public string RangeName=>Range;
    public float MaxRadius=>_spec.Sources.Max(s=>s.Radius);

    public void OnEnterFinishedState() {
      Sources=PlacedSources().ToImmutableArray();
      _finished=true;_smog.AddEmitter(this);
    }

    public void OnExitFinishedState() {
      _finished=false;_smog.RemoveEmitter(this);
    }

    // Flue mouths in world grid coordinates for the current placement (also
    // valid for previews: Blocks.Transform uses the preview's placement).
    private IEnumerable<Source> PlacedSources()=>_spec.Sources.Select(s=>{
      Vector3 world=_blockObject.TransformCoordinates(s.Position);
      return new Source(new Vector2(world.x,world.y),s.Radius,s.Strength);
    });

    public HashSet<Vector2Int> EnvelopeCells() {
      var cells=new HashSet<Vector2Int>();
      foreach(Source s in PlacedSources())cells.UnionWith(SmogService.CellsWithin(s.Center,s.Radius+_smog.Settings.WindDriftCells));
      return cells;
    }

    public IEnumerable<Vector3Int> GetBlocksInRange()=>
      _stackable.GetGroundOrStackableBlocks(EnvelopeCells().Where(_smog.Contains),!_constructionMode.InConstructionMode);

    // Placed: crops/trees in its envelope that smog slows now. Preview: every
    // crop/tree it would reach, so players see what they are about to smog.
    public IEnumerable<BaseComponent> GetObjectsInRange() {
      HashSet<Vector2Int> cells=EnvelopeCells();
      bool preview=_blockObject.IsPreview;
      return _smog.Growths.Where(g=>cells.Contains(g.Cell)&&(preview||_smog.IsLight(_smog.IntensityAt(g.Cell))))
        .Select(g=>(BaseComponent)g.Growable).ToList();
    }

    // "Smog: -X wellbeing nearby": X from the worst cell it reaches now.
    public IEnumerable<EntityDescription> DescribeEntity() {
      string text;
      if(!_finished) text=_loc.T("DeepFrontier.Smog.Emitter.Planned",_spec.Sources.Length,Mathf.CeilToInt(MaxRadius),_smog.MaxPenalty);
      else if(!IsPolluting) text=_loc.T("DeepFrontier.Smog.Emitter.Idle",_spec.Sources.Length,Mathf.CeilToInt(MaxRadius));
      else {
        float worst=EnvelopeCells().Where(_smog.Contains).Select(_smog.IntensityAt).DefaultIfEmpty(0f).Max();
        text=_loc.T("DeepFrontier.Smog.Emitter.Active",_smog.WellbeingPenalty(worst),Mathf.CeilToInt(MaxRadius),
          Mathf.RoundToInt(_smog.GrowthSlowdown(worst)*100f));
      }
      yield return EntityDescription.CreateTextSection(SpecialStrings.RowStarter+text+"\n"+SpecialStrings.RowStarter
        +_loc.T("DeepFrontier.Smog.Emitter.Mitigation"),1030);
    }
  }
}
