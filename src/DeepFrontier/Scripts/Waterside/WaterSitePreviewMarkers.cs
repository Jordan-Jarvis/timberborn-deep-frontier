using System;
using System.Collections.Generic;
using System.Linq;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockSystem;
using Timberborn.Rendering;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Per-cell placement guidance drawn while the building is a selected preview
  // (native WaterDirectionPreviewMarker / TimberPipes PipeFacingPortMarkerDrawer
  // pattern). Support depth itself is shown by AdaptiveSupports' stacked posts.
  internal sealed class WaterSitePreviewMarkers : BaseComponent, IAwakableComponent, IUpdatableComponent,
      IPreviewSelectionListener, IPostPlacementChangeListener {
    // Cells whose blocks need ground/stackable matter below (door/land row).
    private static readonly Color FoundationColor=new(0.86f,0.70f,0.36f,0.75f);
    // Where each support foot meets the terrain or an existing object.
    private static readonly Color SupportFootColor=new(0.62f,0.66f,0.74f,0.8f);
    // Lowest permitted segment of a support that finds no bed within MaxDepth.
    private static readonly Color SupportTooDeepColor=new(0.92f,0.18f,0.14f,0.85f);
    // Working cells by water state, drawn at the water surface (or the cell
    // itself when it is embedded in terrain / a full obstacle).
    private static readonly Color WaterInRangeColor=new(0.18f,0.82f,0.52f,0.8f);
    private static readonly Color WaterShallowColor=new(1f,0.58f,0.1f,0.85f);
    private static readonly Color WaterTooDeepColor=new(0.38f,0.36f,1f,0.85f);
    private const float Lift=0.02f;
    private readonly MarkerDrawerFactory _drawers;
    private readonly WatersideSurvey _survey;
    private readonly List<Vector3Int> _foundation=new();
    private BlockObject _block;
    private AdaptiveSupports _supports;
    private WaterDepthWorkCellsSpec _work;
    private MeshDrawer _foundationTile,_footTile,_tooDeepSupportTile,_inRangeTile,_shallowTile,_deepTile;

    public WaterSitePreviewMarkers(MarkerDrawerFactory drawers,WatersideSurvey survey) {_drawers=drawers;_survey=survey;}

    public void Awake() {
      _block=GetComponent<BlockObject>();_supports=GetComponent<AdaptiveSupports>();
      _work=GetComponent<WaterDepthWorkCellsSpec>();
      if(_supports==null&&_work==null)
        throw new InvalidOperationException("Waterside preview markers need AdaptiveSupportsSpec or WaterDepthWorkCellsSpec");
      _foundationTile=_drawers.CreateTileDrawer(FoundationColor);
      _footTile=_drawers.CreateTileDrawer(SupportFootColor);
      _tooDeepSupportTile=_drawers.CreateTileDrawer(SupportTooDeepColor);
      _inRangeTile=_drawers.CreateTileDrawer(WaterInRangeColor);
      _shallowTile=_drawers.CreateTileDrawer(WaterShallowColor);
      _deepTile=_drawers.CreateTileDrawer(WaterTooDeepColor);
      DisableComponent();
    }

    // Native Preview.Show calls this every frame while the preview is shown;
    // the foundation is re-read only on selection and on placement change.
    public void OnPreviewSelect() {if(Enabled)return;CacheFoundation();EnableComponent();}
    public void OnPreviewUnselect() {DisableComponent();_foundation.Clear();}
    public void OnPostPlacementChanged() {if(Enabled)CacheFoundation();}

    private void CacheFoundation() {
      _foundation.Clear();
      if(_block.Positioned)_foundation.AddRange(_block.PositionedBlocks.GetFoundationCoordinates().Distinct());
    }

    public void Update() {
      if(!_block.IsPreview||!_block.Positioned)return;
      foreach(var cell in _foundation)_foundationTile.DrawAtCoordinates(cell,Lift);
      if(_supports!=null&&_supports.HasProbes) {
        foreach(var probe in _supports.Probes) {
          if(!probe.InMap)continue;
          // Depth 0: the column top is already ground (a level bank under a
          // bank post), so no post or foot is built there.
          if(probe.ReachesBed) {if(probe.Depth>0)_footTile.DrawAtCoordinates(probe.FootCell,Lift);}
          else _tooDeepSupportTile.DrawAtCoordinates(probe.Top-new Vector3Int(0,0,probe.Depth-1),Lift);
        }
      }
      if(_work!=null) {
        foreach(var local in _work.WorkCells) {
          var reading=_survey.ReadWorkCell(_block.TransformCoordinates(local));
          var state=WatersideSurvey.Classify(reading,_work.MinDepth,_work.MaxDepth);
          var tile=state switch {
            WaterRangeState.InRange=>_inRangeTile,
            WaterRangeState.Shallow=>_shallowTile,
            WaterRangeState.Deep=>_deepTile,
            _=>throw new ArgumentOutOfRangeException(nameof(state),state,null),
          };
          // In range / too deep: at the actual water surface. Too shallow: at
          // the level the surface must reach (cell floor + MinDepth), so the
          // player sees how far short the water is.
          if(state==WaterRangeState.Shallow)tile.DrawAtCoordinates(reading.Cell,_work.MinDepth+Lift);
          else tile.DrawAtCoordinates(new Vector3Int(reading.Cell.x,reading.Cell.y,reading.Floor),reading.Depth+Lift);
        }
      }
    }
  }
}
