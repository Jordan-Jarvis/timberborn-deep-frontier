using System;
using System.Collections.Generic;
using System.Linq;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.GameFactionSystem;
using Timberborn.NeedSpecs;
using Timberborn.SingletonSystem;
using Timberborn.TerrainSystem;
using Timberborn.TickSystem;
using Timberborn.TimeSystem;
using Timberborn.WindSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // The smog field: one intensity (0..1) per map column (x, y), like the
  // native RangedEffectService grid, recomputed every FieldIntervalHours.
  //
  // raw    = 1 - prod(1 - c_i) over every polluting flue i (stacks combine
  //          but never exceed 1), c_i from SmogSettingsSpec Core/Edge falloff
  //          around the flue drifted downwind.
  // green  = sum of tree/bush reductions within GreeneryRadius (capped).
  // scrub  = 1 - prod(1 - k_j) over active scrubbers in range (capped).
  // I      = raw * (1 - green) * (1 - scrub).
  //
  // Native contracts used (Timberborn 1.1 decompiled):
  // - NeedManager.ApplyEffect(ContinuousEffect, hours) as RangedEffectSubject
  //   does (SmogExposure).
  // - Growable.IncreaseGrowthProgress(p) -> TimeTrigger.FastForwardProgress,
  //   which subtracts full*p from the remaining delay; a negative p sets the
  //   trigger back (SmogGrowth slowdown).
  // - WindService.WindDirection/WindStrength; WindParticleController bends
  //   the plume by world (x * s, -y * s), i.e. grid (x, -y).
  internal sealed class SmogService : ILoadableSingleton, IPostLoadableSingleton, ITickableSingleton {
    private readonly ITerrainService _terrain;
    private readonly IDayNightCycle _cycle;
    private readonly WindService _wind;
    private readonly ISpecService _specs;
    private readonly FactionNeedService _needs;
    private readonly List<SmogEmitter> _emitters = new List<SmogEmitter>();
    private readonly List<SmogScrubber> _scrubbers = new List<SmogScrubber>();
    private readonly List<SmogGrowth> _growths = new List<SmogGrowth>();
    private readonly Dictionary<BlockObject, float> _buildingCache = new Dictionary<BlockObject, float>();
    private float[] _clean, _green, _scrubClean, _intensity;
    private int _width, _height;
    // Cell offsets within GreeneryRadius of a plant's cell centre (see Load).
    private int[] _greenDx, _greenDy;
    private float _nextFieldHour = float.NegativeInfinity, _lastGrowthHour = float.NaN;
    private int _lightPenalty, _heavyPenalty;

    public SmogSettingsSpec Settings { get; private set; }
    public IReadOnlyList<SmogGrowth> Growths => _growths;

    public SmogService(ITerrainService terrain, IDayNightCycle cycle, WindService wind, ISpecService specs,
      FactionNeedService needs) {
      _terrain=terrain;_cycle=cycle;_wind=wind;_specs=specs;_needs=needs;
    }

    public void Load() {
      Settings=_specs.GetSingleSpec<SmogSettingsSpec>();
      Validate(Settings);
      _width=_terrain.Size.x;_height=_terrain.Size.y;
      _clean=new float[_width*_height];_green=new float[_width*_height];
      _scrubClean=new float[_width*_height];_intensity=new float[_width*_height];
      GreeneryOffsets();
    }

    // A plant's disc is centred on its cell centre (Cell + 0.5), so which
    // cells it covers depends only on the integer offset. Precompute them once
    // in ForCells order (y, then x) with ForCells' own float distance test:
    // (x+.5f)-(cx+.5f) is exact for map coordinates, so the test is the same
    // as Vector2.Distance(offset+.5, .5) and the summed field is identical.
    private void GreeneryOffsets() {
      float radius=Settings.GreeneryRadius;
      int reach=Mathf.CeilToInt(radius);
      var dx=new List<int>();var dy=new List<int>();
      for(int y=-reach;y<=reach;y++)for(int x=-reach;x<=reach;x++)
        if(Vector2.Distance(new Vector2(x+.5f,y+.5f),new Vector2(.5f,.5f))<=radius){dx.Add(x);dy.Add(y);}
      _greenDx=dx.ToArray();_greenDy=dy.ToArray();
    }

    // Faction needs are loaded by FactionNeedService.Load; read them after.
    public void PostLoad() {
      _lightPenalty=Penalty(Settings.LightNeedId);
      _heavyPenalty=Penalty(Settings.HeavyNeedId);
    }

    private int Penalty(string needId) {
      NeedSpec need=_needs.GetBeaverOrBotNeedById(needId);
      if(need.CharacterType!="Beaver"||need.UnfavorableWellbeing>=0||need.FavorableWellbeing!=0||need.MaximumValue!=0f||need.MinimumValue>=0f)
        throw new InvalidOperationException($"Smog need {needId} must be a never-positive beaver need with negative unfavorable wellbeing");
      return -need.UnfavorableWellbeing;
    }

    private static void Validate(SmogSettingsSpec s) {
      bool Fraction(float v)=>v>0f&&v<=1f;
      if(!Fraction(s.LightThreshold)||!Fraction(s.HeavyThreshold)||s.HeavyThreshold<=s.LightThreshold
        ||string.IsNullOrEmpty(s.LightNeedId)||string.IsNullOrEmpty(s.HeavyNeedId)||s.LightNeedId==s.HeavyNeedId
        ||!(s.ExposurePointsPerHour>0f)||!Fraction(s.GrowthSlowdownAtThreshold)||!(s.GrowthSlowdownPerIntensity>=0f)
        ||!Fraction(s.GrowthSlowdownMax)||s.GrowthSlowdownMax<s.GrowthSlowdownAtThreshold
        ||!Fraction(s.TreeReduction)||!Fraction(s.BushReduction)||!(s.GreeneryRadius>0f)||!Fraction(s.GreeneryMaxReduction)
        ||!Fraction(s.ScrubberMaxReduction)||!(s.WindDriftCells>=0f)||!Fraction(s.CoreFraction)||s.CoreFraction>=1f
        ||!Fraction(s.EdgeFactor)||!(s.FieldIntervalHours>0f)||!(s.GrowthIntervalHours>0f))
        throw new InvalidOperationException("SmogSettingsSpec values must be explicitly valid: "+s);
    }

    public void AddEmitter(SmogEmitter e) {if(_emitters.Contains(e))throw new InvalidOperationException("Smog emitter registered twice");_emitters.Add(e);MarkDirty();}
    public void RemoveEmitter(SmogEmitter e) {if(!_emitters.Remove(e))throw new InvalidOperationException("Smog emitter was not registered");MarkDirty();}
    public void AddScrubber(SmogScrubber s) {if(_scrubbers.Contains(s))throw new InvalidOperationException("Smog scrubber registered twice");_scrubbers.Add(s);MarkDirty();}
    public void RemoveScrubber(SmogScrubber s) {if(!_scrubbers.Remove(s))throw new InvalidOperationException("Smog scrubber was not registered");MarkDirty();}
    public void AddGrowth(SmogGrowth g) {_growths.Add(g);}
    public void RemoveGrowth(SmogGrowth g) {if(!_growths.Remove(g))throw new InvalidOperationException("Smog growth was not registered");}
    public void MarkDirty() {_nextFieldHour=float.NegativeInfinity;}

    public void Tick() {
      float now=_cycle.PartialDayNumber*24f;
      if(now>=_nextFieldHour) {RecomputeField();_nextFieldHour=now+Settings.FieldIntervalHours;}
      if(float.IsNaN(_lastGrowthHour))_lastGrowthHour=now;
      else if(now-_lastGrowthHour>=Settings.GrowthIntervalHours) {ApplyGrowthSlowdown();_lastGrowthHour=now;}
    }

    // Plume offset (grid cells) the same way the smoke particles bend.
    public Vector2 WindDrift() {
      Vector2 d=_wind.WindDirection;
      return new Vector2(d.x,-d.y)*(_wind.WindStrength*Settings.WindDriftCells);
    }

    public float Contribution(float distance,float radius,float strength) {
      if(distance>radius)return 0f;
      float core=radius*Settings.CoreFraction;
      if(distance<=core)return strength;
      return strength*(1f-(1f-Settings.EdgeFactor)*(distance-core)/(radius-core));
    }

    private void RecomputeField() {
      Array.Fill(_clean,1f);Array.Clear(_green,0,_green.Length);Array.Fill(_scrubClean,1f);
      Vector2 drift=WindDrift();
      foreach(SmogEmitter emitter in _emitters) {
        if(!emitter.IsPolluting)continue;
        foreach(SmogEmitter.Source source in emitter.Sources) {
          Vector2 c=source.Center+drift;
          ForCells(c,source.Radius,(i,d)=>_clean[i]*=1f-Contribution(d,source.Radius,source.Strength));
        }
      }
      // Every plant, every recompute: no closure or delegate per plant, no
      // distance test (precomputed offsets); off-map cells skipped as
      // ForCells' clamped box does.
      foreach(SmogGrowth growth in _growths) {
        float w=growth.GreeneryReduction;
        if(w<=0f)continue;
        Vector2Int cell=growth.Cell;
        for(int k=0;k<_greenDx.Length;k++) {
          int x=cell.x+_greenDx[k],y=cell.y+_greenDy[k];
          if(x>=0&&x<_width&&y>=0&&y<_height)_green[y*_width+x]+=w;
        }
      }
      foreach(SmogScrubber scrubber in _scrubbers) {
        if(!scrubber.IsCleaning)continue;
        float k=scrubber.Reduction;
        ForCells(scrubber.Center,scrubber.Radius,(i,d)=>_scrubClean[i]*=1f-k);
      }
      for(int i=0;i<_intensity.Length;i++) {
        float raw=1f-_clean[i];
        _intensity[i]=raw<=0f?0f:raw*(1f-Mathf.Min(_green[i],Settings.GreeneryMaxReduction))
          *(1f-Mathf.Min(1f-_scrubClean[i],Settings.ScrubberMaxReduction));
      }
      _buildingCache.Clear();
    }

    // Cells whose centre lies within radius of centre (grid units).
    private void ForCells(Vector2 centre,float radius,Action<int,float> visit) {
      int x0=Mathf.Max(0,Mathf.FloorToInt(centre.x-radius)),x1=Mathf.Min(_width-1,Mathf.CeilToInt(centre.x+radius));
      int y0=Mathf.Max(0,Mathf.FloorToInt(centre.y-radius)),y1=Mathf.Min(_height-1,Mathf.CeilToInt(centre.y+radius));
      for(int y=y0;y<=y1;y++)for(int x=x0;x<=x1;x++) {
        float d=Vector2.Distance(new Vector2(x+.5f,y+.5f),centre);
        if(d<=radius)visit(y*_width+x,d);
      }
    }

    public static IEnumerable<Vector2Int> CellsWithin(Vector2 centre,float radius) {
      int x0=Mathf.FloorToInt(centre.x-radius),x1=Mathf.CeilToInt(centre.x+radius);
      int y0=Mathf.FloorToInt(centre.y-radius),y1=Mathf.CeilToInt(centre.y+radius);
      for(int y=y0;y<=y1;y++)for(int x=x0;x<=x1;x++)
        if(Vector2.Distance(new Vector2(x+.5f,y+.5f),centre)<=radius)yield return new Vector2Int(x,y);
    }

    public bool Contains(Vector2Int c)=>_terrain.Contains(c);

    private int Index(Vector2Int c) {
      if(!_terrain.Contains(c))throw new InvalidOperationException($"Smog lookup outside the map at {c}");
      return c.y*_width+c.x;
    }

    public float IntensityAt(Vector2Int c)=>_intensity[Index(c)];
    public float RawAt(Vector2Int c)=>1f-_clean[Index(c)];
    public float GreeneryAt(Vector2Int c)=>Mathf.Min(_green[Index(c)],Settings.GreeneryMaxReduction);
    public float ScrubbingAt(Vector2Int c)=>Mathf.Min(1f-_scrubClean[Index(c)],Settings.ScrubberMaxReduction);

    // Average intensity over the building's footprint columns.
    public float BuildingIntensity(BlockObject building) {
      if(_buildingCache.TryGetValue(building,out float cached))return cached;
      List<Vector2Int> cells=FootprintCells(building);
      float value=cells.Average(IntensityAt);
      _buildingCache[building]=value;
      return value;
    }

    public (float raw,float green,float scrub) BuildingBreakdown(BlockObject building) {
      List<Vector2Int> cells=FootprintCells(building);
      return (cells.Average(RawAt),cells.Average(GreeneryAt),cells.Average(ScrubbingAt));
    }

    // Map columns the building actually occupies. Unoccupied blocks are not
    // part of it and may lie off the map: BlockValidator.FitsInMap only checks
    // occupied blocks (XY in both branches), so a building may hang an empty
    // edge row over the map edge. Occupied blocks are always on the map, the
    // same footprint the native RangedEffectService and TerrainLevelValidator
    // use; Index still fails explicitly if that contract is ever broken.
    public static List<Vector2Int> FootprintCells(BlockObject building)=>
      building.PositionedBlocks.GetOccupiedCoordinates().Select(c=>new Vector2Int(c.x,c.y)).Distinct().ToList();

    public bool IsLight(float intensity)=>intensity>=Settings.LightThreshold;
    public bool IsHeavy(float intensity)=>intensity>=Settings.HeavyThreshold;

    // Wellbeing lost by a beaver at this intensity (positive number).
    public int WellbeingPenalty(float intensity)=>IsHeavy(intensity)?_lightPenalty+_heavyPenalty:IsLight(intensity)?_lightPenalty:0;
    public int LightPenalty=>_lightPenalty;
    public int MaxPenalty=>_lightPenalty+_heavyPenalty;

    public float GrowthSlowdown(float intensity) {
      if(!IsLight(intensity))return 0f;
      return Mathf.Min(Settings.GrowthSlowdownMax,
        Settings.GrowthSlowdownAtThreshold+Settings.GrowthSlowdownPerIntensity*(intensity-Settings.LightThreshold));
    }

    private void ApplyGrowthSlowdown() {
      foreach(SmogGrowth growth in _growths)growth.ApplySlowdown(GrowthSlowdown(IntensityAt(growth.Cell)));
    }
  }
}
