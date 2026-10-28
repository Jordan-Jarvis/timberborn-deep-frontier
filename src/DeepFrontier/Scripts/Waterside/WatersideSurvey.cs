using System;
using System.Collections.Generic;
using Timberborn.BlockSystem;
using Timberborn.TerrainSystem;
using Timberborn.WaterBuildings;
using Timberborn.WaterSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Result of probing one support column downward from its authored top cell.
  // Depth counts one-cell post segments from Top down to the bed (exclusive).
  // When ReachesBed is false, nothing solid exists within MaxDepth cells, or
  // (InMap false) an unbuildable preview has the column outside the map.
  internal readonly struct SupportProbe {
    public Vector3Int Top { get; }
    public int Depth { get; }
    public bool ReachesBed { get; }
    public bool InMap { get; }
    public SupportProbe(Vector3Int top,int depth,bool reachesBed,bool inMap) {Top=top;Depth=depth;ReachesBed=reachesBed;InMap=inMap;}
    // Grid cell whose floor is the top surface of the bed (the foot stands here).
    public Vector3Int FootCell=>Top-new Vector3Int(0,0,Depth-1);
  }

  // Water in the open native water column that contains a working cell.
  // A cell embedded in terrain or a full obstacle has no open column (dry).
  // Depth is the column's water depth (riverbed/floor to surface); Submersion
  // is how far the surface rises above the working cell's own floor (cell.z),
  // as native TickableWaterBuilding's WaterHeightOrFloor - z. It is negative
  // when the surface lies below the cell.
  internal readonly struct WorkCellReading {
    public Vector3Int Cell { get; }
    public bool HasOpenColumn { get; }
    public int Floor { get; }
    public float Depth { get; }
    public float Surface=>Floor+Depth;
    public float Submersion=>HasOpenColumn?Surface-Cell.z:0f;
    public WorkCellReading(Vector3Int cell,bool hasOpenColumn,int floor,float depth) {
      Cell=cell;HasOpenColumn=hasOpenColumn;Floor=floor;Depth=depth;
    }
  }

  internal enum WaterRangeState { InRange, Shallow, Deep }

  // Shared, stateless placement/runtime survey. The validators, preview markers
  // and gameplay components all read the same native sources through this class.
  internal sealed class WatersideSurvey {
    private readonly ITerrainService _terrain;
    private readonly IBlockService _blocks;
    private readonly IThreadSafeWaterMap _water;
    private readonly List<BlockObject> _objects=new();
    public WatersideSurvey(ITerrainService terrain,IBlockService blocks,IThreadSafeWaterMap water) {
      _terrain=terrain;_blocks=blocks;_water=water;
    }

    // Same stopping rule as native WaterInputPipeCoordinates: terrain, or any
    // non-overridable object other than the owner occupying more than
    // Floor/Corners of the cell. The bottom of the map is solid.
    public SupportProbe ProbeSupport(BlockObject owner,Vector3Int top,int maxDepth) {
      if(maxDepth<1)throw new ArgumentOutOfRangeException(nameof(maxDepth),"Support depth limit must be at least one cell");
      if(!_blocks.Contains(new Vector2Int(top.x,top.y))||top.z>=_blocks.Size.z)return new SupportProbe(top,0,false,false);
      for(int depth=0;depth<=maxDepth;depth++) {
        if(IsBed(owner,top-new Vector3Int(0,0,depth)))return new SupportProbe(top,depth,true,true);
      }
      return new SupportProbe(top,maxDepth,false,true);
    }

    private bool IsBed(BlockObject owner,Vector3Int cell) {
      if(cell.z<0||_terrain.Underground(cell))return true;
      _blocks.GetIntersectingObjectsAt(cell,WaterInputPipeCoordinates.InvalidOccupations,_objects);
      bool occupied=false;
      foreach(var item in _objects)
        if(!item.Overridable&&item!=owner) {occupied=true;break;}
      _objects.Clear();
      return occupied;
    }

    public WorkCellReading ReadWorkCell(Vector3Int cell) {
      if(!_water.TryGetColumnFloor(cell,out int floor))return new WorkCellReading(cell,false,0,0);
      return new WorkCellReading(cell,true,floor,_water.WaterDepth(cell));
    }

    // Native ContaminationBlockableBuilding reports zero contamination for a
    // coordinate above the surface. Sample at the open column's floor instead,
    // which is underwater whenever that column holds any water.
    public Vector3Int ContaminationSampleCell(Vector3Int cell) {
      var reading=ReadWorkCell(cell);
      return reading.HasOpenColumn?new Vector3Int(cell.x,cell.y,reading.Floor):cell;
    }

    // Shallow: the surface does not reach MinDepth above the working cell's
    // floor (dry and embedded cells included). Deep: the open column holds
    // more than MaxDepth of water from its riverbed/floor.
    public static WaterRangeState Classify(in WorkCellReading reading,float minDepth,float maxDepth) {
      if(reading.Submersion<minDepth)return WaterRangeState.Shallow;
      return reading.Depth>maxDepth?WaterRangeState.Deep:WaterRangeState.InRange;
    }

    // Hysteresis mirrors native TickableWaterBuilding: leave the range at
    // (limit -/+ band) inclusive, re-enter strictly inside (limit +/- band).
    // The minimum applies to submersion, the maximum to column depth.
    // Shallow has priority in every state, as in Classify: depth minus
    // submersion is the whole number of layers from the column floor to the
    // cell, so a dry cell above a deep pit trips both limits at once. Shallow
    // is left only once the surface rises past MinDepth+band, and Deep can
    // only fall back to Shallow below MinDepth-band, so for an unchanged
    // reading every state settles after at most one transition.
    public static WaterRangeState Next(WaterRangeState state,in WorkCellReading reading,float minDepth,float maxDepth,float band) {
      float submersion=reading.Submersion,depth=reading.Depth;
      switch(state) {
        case WaterRangeState.InRange:
          if(submersion<=minDepth-band)return WaterRangeState.Shallow;
          return depth>=maxDepth+band?WaterRangeState.Deep:WaterRangeState.InRange;
        case WaterRangeState.Shallow:
          if(submersion<=minDepth+band)return WaterRangeState.Shallow;
          return depth>=maxDepth+band?WaterRangeState.Deep:WaterRangeState.InRange;
        case WaterRangeState.Deep:
          if(submersion<=minDepth-band)return WaterRangeState.Shallow;
          return depth<maxDepth-band?WaterRangeState.InRange:WaterRangeState.Deep;
        default:throw new ArgumentOutOfRangeException(nameof(state),state,null);
      }
    }
  }
}
