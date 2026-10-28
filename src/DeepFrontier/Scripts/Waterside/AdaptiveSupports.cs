using System;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.Linq;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockObjectModelSystem;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.Buildings;
using Timberborn.Common;
using Timberborn.Coordinates;
using Timberborn.EntitySystem;
using Timberborn.Localization;
using Timberborn.Rendering;
using Timberborn.SelectionSystem;
using Timberborn.SingletonSystem;
using Timberborn.TerrainSystem;
using UnityEngine;
using Object = UnityEngine.Object;

namespace DeepFrontier.Scripts {
  internal record AdaptiveSupportsSpec : ComponentSpec {
    // Local block coordinates, the same frame as BlockObjectSpec.Blocks and
    // TickableWaterBuildingSpec.WaterCoordinates (BaseZ is not added). X/Y
    // select the support column inside the footprint; Z is the authored top
    // cell of the post, i.e. its highest one-cell segment. Z may be negative
    // for a post hanging below the building's lowest layer.
    [Serialize] public ImmutableArray<Vector3Int> Columns { get; init; }
    // Most one-cell segments a column may use, including its foot.
    [Serialize] public int MaxDepth { get; init; }
    // Nodes in the finished model that are cloned once per cell. Each is
    // modelled one cell tall, origin at the bottom centre of its cell. The foot
    // is the lowest piece and carries the footing; the segment is a plain post.
    [Serialize] public string SegmentNodeName { get; init; }
    [Serialize] public string FootNodeName { get; init; }
  }

  // Stacks post segments from each authored column top down to the terrain or
  // an existing object's top, like native WaterInputPipe stacks PipeSegments.
  // The posts are visual: they register no blocks, water obstacles or paths.
  internal sealed class AdaptiveSupports : BaseComponent, IAwakableComponent, IInitializableEntity,
      IDeletableEntity, IPostPlacementChangeListener, IModelUpdater {
    private readonly WatersideSurvey _survey;
    private readonly ITerrainService _terrain;
    private readonly EventBus _events;
    private readonly MaterialColorer _colorer;
    private readonly List<GameObject> _segments=new();
    private readonly List<GameObject> _feet=new();
    private BlockObject _block;
    private EntityMaterials _materials;
    private HighlightableObject _highlight;
    private GameObject _segmentTemplate,_footTemplate;
    private SupportProbe[] _probes,_scratch;
    private bool _registered;
    public AdaptiveSupportsSpec Spec { get; private set; }
    public bool HasProbes { get; private set; }
    public IReadOnlyList<SupportProbe> Probes=>_probes;
    public bool AllColumnsSupported=>HasProbes&&_probes.All(p=>p.InMap&&p.ReachesBed);

    public AdaptiveSupports(WatersideSurvey survey,ITerrainService terrain,EventBus events,MaterialColorer colorer) {
      _survey=survey;_terrain=terrain;_events=events;_colorer=colorer;
    }

    public void Awake() {
      Spec=GetComponent<AdaptiveSupportsSpec>();_block=GetComponent<BlockObject>();
      _materials=GetComponent<EntityMaterials>();_highlight=GetComponent<HighlightableObject>();
      if(_materials==null||_highlight==null)
        throw new InvalidOperationException("Adaptive supports require native EntityMaterials and HighlightableObject");
      var size=GetComponent<BlockObjectSpec>().Size;
      if(Spec.Columns.IsDefaultOrEmpty)throw new InvalidOperationException("Adaptive supports need at least one authored column");
      if(Spec.MaxDepth<1)throw new InvalidOperationException("Adaptive support MaxDepth must be at least one cell");
      if(Spec.Columns.Select(c=>new Vector2Int(c.x,c.y)).Distinct().Count()!=Spec.Columns.Length)
        throw new InvalidOperationException("Adaptive support columns must have distinct X/Y cells");
      foreach(var c in Spec.Columns)
        if(c.x<0||c.y<0||c.x>=size.x||c.y>=size.y||c.z>=size.z)
          throw new InvalidOperationException($"Adaptive support column {c} lies outside the building footprint");
      if(string.IsNullOrEmpty(Spec.SegmentNodeName)||string.IsNullOrEmpty(Spec.FootNodeName)||Spec.SegmentNodeName==Spec.FootNodeName)
        throw new InvalidOperationException("Adaptive supports need distinct segment and foot node names");
      var finished=GameObject.FindChildIfNameNotEmpty(GetComponent<BuildingModelSpec>().FinishedModelName);
      if(finished==null)throw new InvalidOperationException("Adaptive supports require a finished model");
      // Under the finished model, native ConstructionModeModel removes the
      // grayscale applied to segments created while unfinished.
      _segmentTemplate=FindNode(finished,Spec.SegmentNodeName);
      _footTemplate=FindNode(finished,Spec.FootNodeName);
      _segmentTemplate.SetActive(false);_footTemplate.SetActive(false);
      _probes=new SupportProbe[Spec.Columns.Length];
      _scratch=new SupportProbe[Spec.Columns.Length];
    }

    private static GameObject FindNode(GameObject root,string name) {
      var matches=root.GetComponentsInChildren<Transform>(true).Where(t=>t.name==name).ToArray();
      if(matches.Length!=1)throw new InvalidOperationException("Adaptive support model node must exist exactly once: "+name);
      return matches[0].gameObject;
    }

    // Previews are not entity-initialized; they refresh through placement
    // changes and BlockObjectModelController.UpdateModel instead.
    public void InitializeEntity() {
      _terrain.TerrainHeightChanged+=OnTerrainHeightChanged;_events.Register(this);_registered=true;
      Refresh();
    }

    public void DeleteEntity() {
      if(!_registered)return;
      _terrain.TerrainHeightChanged-=OnTerrainHeightChanged;_events.Unregister(this);_registered=false;
    }

    public void OnPostPlacementChanged()=>Refresh();
    public void UpdateModel()=>Refresh();

    [OnEvent]
    public void OnBlockObjectSet(BlockObjectSetEvent e) {if(AffectsColumns(e.BlockObject))Refresh();}
    [OnEvent]
    public void OnBlockObjectUnset(BlockObjectUnsetEvent e) {if(AffectsColumns(e.BlockObject))Refresh();}

    // Event filters use the column tops cached by the last Refresh, which runs
    // on every placement change before the entity can receive these events.
    private void OnTerrainHeightChanged(object sender,TerrainHeightChangeEventArgs args) {
      if(!HasProbes)return;
      var xy=args.Change.Coordinates;
      foreach(var probe in _probes)
        if(probe.Top.x==xy.x&&probe.Top.y==xy.y) {Refresh();return;}
    }

    private bool AffectsColumns(BlockObject other) {
      if(other==_block||!HasProbes||!other.Positioned)return false;
      foreach(var cell in other.PositionedBlocks.GetAllCoordinates())
        foreach(var probe in _probes)
          if(cell.x==probe.Top.x&&cell.y==probe.Top.y&&cell.z<=probe.Top.z)return true;
      return false;
    }

    // Native PreviewPlacer calls UpdateModel every frame while placing. The
    // probes are cheap; posts are rebuilt only when a probe result changes
    // (the post layout is a function of the probes alone).
    private void Refresh() {
      if(!_block.Positioned)return;
      bool changed=!HasProbes;
      for(int i=0;i<Spec.Columns.Length;i++) {
        _scratch[i]=_survey.ProbeSupport(_block,_block.TransformCoordinates(Spec.Columns[i]),Spec.MaxDepth);
        changed|=!Same(_scratch[i],_probes[i]);
      }
      if(!changed)return;
      int segmentsUsed=0,feetUsed=0;bool created=false;
      for(int i=0;i<Spec.Columns.Length;i++) {
        var probe=_scratch[i];
        _probes[i]=probe;
        // An unsupported column shows every allowed segment and no foot: it
        // visibly hangs, and the placement validator rejects the preview.
        // A column outside the map (unbuildable preview only) shows nothing.
        if(!probe.InMap)continue;
        int plain=probe.ReachesBed?Math.Max(probe.Depth-1,0):Spec.MaxDepth;
        for(int k=0;k<plain;k++)
          Show(_segments,segmentsUsed++,_segmentTemplate,probe.Top-new Vector3Int(0,0,k),ref created);
        if(probe.ReachesBed&&probe.Depth>0)
          Show(_feet,feetUsed++,_footTemplate,probe.Top-new Vector3Int(0,0,probe.Depth-1),ref created);
      }
      for(int i=segmentsUsed;i<_segments.Count;i++)_segments[i].SetActive(false);
      for(int i=feetUsed;i<_feet.Count;i++)_feet[i].SetActive(false);
      HasProbes=true;
      if(created)_highlight.RefreshHighlight();
    }

    private static bool Same(in SupportProbe a,in SupportProbe b)=>
      a.Top==b.Top&&a.Depth==b.Depth&&a.ReachesBed==b.ReachesBed&&a.InMap==b.InMap;

    private void Show(List<GameObject> pool,int index,GameObject template,Vector3Int cell,ref bool created) {
      if(index==pool.Count) {
        var clone=Object.Instantiate(template,template.transform.parent);
        clone.name=template.name+"#"+index;
        _materials.AddMaterials(clone);
        // As native WaterInputPipeSegmentCreator.CreateUnfinished: segments
        // created during construction start gray like the finished model.
        if(_block.IsUnfinished)_colorer.EnableGrayscale(clone);
        pool.Add(clone);created=true;
      }
      var instance=pool[index];
      instance.transform.position=CoordinateSystem.GridToWorldCentered(cell);
      instance.SetActive(true);
    }
  }

  // Hard rule: every support column must lie inside the map and reach a bed
  // within MaxDepth. Gated on IsPreview because native
  // BlockObject.AddToServiceAfterLoad deletes any loaded object that fails an
  // IBlockObjectValidator; terrain may change after a building is placed.
  // Native PreviewPlacer shows this text for an almost-valid preview (some
  // foundation still inside the map), so an off-map column is reported as
  // such before any depth is judged.
  internal sealed class AdaptiveSupportsPlacementValidator : IBlockObjectValidator {
    private readonly WatersideSurvey _survey;
    private readonly ILoc _loc;
    public AdaptiveSupportsPlacementValidator(WatersideSurvey survey,ILoc loc) {_survey=survey;_loc=loc;}
    public bool IsValid(BlockObject blockObject,out string errorMessage) {
      errorMessage=null;
      if(!blockObject.IsPreview)return true;
      var supports=blockObject.GetComponent<AdaptiveSupports>();
      if(supports==null)return true;
      // Runs two or three times per preview frame: no allocation. An off-map
      // column is reported before any depth, as before.
      var spec=supports.Spec;
      bool tooDeep=false;
      foreach(var column in spec.Columns) {
        var probe=_survey.ProbeSupport(blockObject,blockObject.TransformCoordinates(column),spec.MaxDepth);
        if(!probe.InMap) {
          errorMessage=_loc.T(WatersideLoc.SupportOutsideMap);
          return false;
        }
        tooDeep|=!probe.ReachesBed;
      }
      if(tooDeep) {
        errorMessage=_loc.T(WatersideLoc.SupportTooDeep,spec.MaxDepth);
        return false;
      }
      return true;
    }
  }
}
