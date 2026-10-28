#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;
using DeepFrontier.Scripts.Radiation;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockingSystem;
using Timberborn.BlockSystem;
using Timberborn.Coordinates;
using Timberborn.EntitySystem;
using Timberborn.MechanicalSystem;
using Timberborn.TemplateSystem;
using Timberborn.WaterBuildings;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Sites batch of the all-buildings acceptance. The buildings a flat pad cannot hold run last, on the
  // sites of tools/all_buildings_sites.json, which tools/create_all_buildings_sites_map.py authors into
  // the test map 'Deep Frontier - All Buildings Sites Test' (terrain and map-authored understructures; no
  // water). The batch fills the water through the native water services with known volumes, builds the
  // side-platform anchors and the river reach's divider dam, places each building at its contract
  // placement and then runs the same generic checks as the pad batches, plus per site:
  //   Deep Mine / quarries   placed over the map-authored DeepOreVein / seams; a production cycle completes;
  //   Fish Hatchery          nursery work cells wet; a cycle completes; player paths built on its deck
  //                          slabs, ranked after the hatchery by the native loader, still standing at the end;
  //   side platforms         native preview accepts the anchored deck (and rejects one cleated onto a
  //                          plain platform); paths and a platform are built on top of the placed deck;
  //   sludge recovery pump   radioactive pool intake; sludge produced; the world's water radiation falls by
  //                          the recovered volume (radioactive volume per good x goods, plus progress and
  //                          the intake buffer), drift measured on an identical pool without a pump;
  //   hydro turbine          sealed reach filled above the divider; with the gate opened, flow through the
  //                          turbine into the lower reach and measured shaft output;
  //   vanilla pump / shower / pool   intake pipe or pool cell in water; the pump completes a cycle; the
  //                          shower and the pool are visited (generic attraction check).
  // On a map without these sites, the site buildings run on the pad as before and report SITE.
  internal sealed partial class AllBuildingsAcceptance {
    private static readonly string SitesPath=Path.Combine(Root,"tools","all_buildings_sites.json");
    private const float SiteFillDelayHours=.2f,TopUpIntervalHours=.25f;
    private JObject _sites;
    private bool _sitesAvailable,_siteBatch,_siteDone,_siteFilled;
    private RectInt _siteZone;
    private readonly List<Subject> _siteSubjects=new();
    private readonly JObject _siteReport=new();
    private float _lastTopUp;
    private double _toppedUp;
    // Hydro
    private HydroTurbine _turbine;
    private RectInt _basin;
    private int _divider;
    private bool _turbineOpen;
    private float _peakFlow,_peakHp,_peakSupply,_peakNodeOutput,_peakHead;
    private string _peakState="";
    private (double Upper,double Lower) _reachAtOpen;
    // Sludge
    private bool _sludgeBaseline;
    private float _w0,_c0,_p0,_buffer0,_progress0;
    private int _produced0;
    private float _sludgeStart;
    // Hatchery deck
    private readonly List<BlockObject> _deckPaths=new();
    private Subject _hatchery;

    // ---------- contract and map ----------
    private static Vector3Int Xyz(JToken t)=>new((int)t["x"],(int)t["y"],(int)t["z"]);
    private static IEnumerable<Vector2Int> RectCells(JToken rect) {
      var r=rect.ToObject<int[]>();
      for(int x=r[0];x<r[0]+r[2];x++)for(int y=r[1];y<r[1]+r[3];y++)yield return new Vector2Int(x,y);
    }
    private JToken Pit(string id)=>_sites["pits"].Single(p=>(string)p["id"]==id);
    private IEnumerable<Vector3Int> PitCells(string id) {
      var pit=Pit(id);int floor=(int)pit["floor"];
      return pit["rects"].SelectMany(RectCells).Select(c=>new Vector3Int(c.x,c.y,floor));
    }

    // The sites are used only when the loaded map carries them: every map-authored understructure at its
    // contract cell and the planned terrain of every pit and wall.
    private void LoadSites() {
      _siteReport["contract"]=SitesPath;
      if(!File.Exists(SitesPath)){_siteReport["available"]=false;_siteReport["reason"]="no site contract";return;}
      _sites=JObject.Parse(File.ReadAllText(SitesPath));
      var zone=_sites["zone"].ToObject<int[]>();
      _siteZone=new RectInt(zone[0],zone[1],zone[2],zone[3]);
      var problems=new List<string>();
      foreach(var u in _sites["understructures"]) {
        var at=Xyz(u);string template=(string)u["template"];
        bool found=_entities.Entities.Any(e=>e.GetComponent<TemplateSpec>()?.TemplateName==template&&
          e.GetComponent<BlockObject>() is var b&&b&&b.Coordinates==at);
        if(!found)problems.Add(template+" missing at "+at);
      }
      foreach(var pit in _sites["pits"]) {
        int floor=(int)pit["floor"];
        int wrong=pit["rects"].SelectMany(RectCells).Count(c=>_terrain.GetTerrainHeight(new Vector3Int(c.x,c.y,0))!=floor);
        if(wrong>0)problems.Add("pit "+pit["id"]+": "+wrong+" cells not at floor "+floor);
      }
      foreach(var wall in _sites["walls"]) {
        var r=wall["ring"].ToObject<int[]>();int height=(int)wall["height"];int wrong=0;
        foreach(var c in RectCells(wall["ring"]))
          if((c.x==r[0]||c.x==r[0]+r[2]-1||c.y==r[1]||c.y==r[1]+r[3]-1)&&_terrain.GetTerrainHeight(new Vector3Int(c.x,c.y,0))!=height)wrong++;
        if(wrong>0)problems.Add("wall "+wall["id"]+": "+wrong+" ring cells not at height "+height);
      }
      _sitesAvailable=problems.Count==0;
      _siteReport["available"]=_sitesAvailable;
      _siteReport["map"]=(string)_sites["map"];
      _siteReport["zone"]=_siteZone.ToString();
      if(problems.Count>0)_siteReport["reason"]=new JArray(problems);
      Debug.Log(Tag+" sites "+(_sitesAvailable?"available on this map: zone "+_siteZone:"not on this map ("+string.Join("; ",problems.Take(4))+
        "); site buildings run on the pad"));
    }
    private void AssignSites() {
      if(!_sitesAvailable)return;
      foreach(var entry in _sites["buildings"]) {
        var s=_subjects.SingleOrDefault(x=>x.Template==(string)entry["template"]);
        if(s==null){_harness.Add("site contract names "+entry["template"]+", which is not a subject");continue;}
        if(s.Spec==null)continue;
        s.Site=(JObject)entry;s.Anchor=Xyz(entry);
        s.Orientation=(Orientation)Enum.Parse(typeof(Orientation),(string)entry["orientation"]);
        _siteSubjects.Add(s);
      }
    }

    // ---------- batch ----------
    private void StartSiteBatch() {
      _siteDone=true;_siteBatch=true;
      _batch.Clear();_batchObjects.Clear();_network.Clear();_batchNumber++;
      var dc=_district.GetComponent<BlockObject>();
      var dcBounds=Bounds(dc.GetComponent<BlockObjectSpec>(),dc.Placement);
      int x0=Math.Min(_siteZone.xMin,dcBounds.xMin-3),x1=Math.Max(_siteZone.xMax,dcBounds.xMax+3);
      int y0=Math.Min(_siteZone.yMin,dcBounds.yMin-3),y1=Math.Max(_siteZone.yMax,dcBounds.yMax+3);
      _routeArea=new RectInt(x0,y0,x1-x0,y1-y0);
      foreach(var s in _siteSubjects){s.Batch="sites";_batch.Add(s);}
      Debug.Log(Tag+" BATCH "+_batchNumber+" (sites): "+string.Join(", ",_batch.Select(s=>s.Id))+"; route area "+_routeArea);
      // Side-platform anchors, then the native preview of each deck against them.
      foreach(var a in _sites["anchors"]) {
        var deck=_batch.FirstOrDefault(s=>s.Template==(string)a["deck"]);
        if(deck==null)continue;
        Guard(deck,"site: anchor",()=>{Create(Spec((string)a["template"]),At(Xyz(a)));
          Add(deck,"site: anchor","INFO",a["template"]+" at "+Xyz(a));});
      }
      // The build tool's view of each site first: a native preview at the contract placement.
      foreach(var s in _batch) {
        string check=s.Blueprint.HasSpec<AnchoredDeckSpec>()?"site: native preview accepts the anchored deck":"site: native preview accepts the site";
        Guard(s,check,()=>SitePreview(s,At(s.Anchor,s.Orientation),true,check));
      }
      // The player's way to that placement: the cursor on the water building's bank cell, through the
      // native picker, gives the bank height and a valid preview.
      foreach(var s in _batch.Where(x=>x.Blueprint.HasSpec<WaterDepthWorkCellsSpec>()))
        Guard(s,"site: cursor on the door cell picks the bank height",()=>CursorPreview(s,At(s.Anchor,s.Orientation)));
      var negative=_sites["negativeAnchor"];
      var negativeDeck=_batch.FirstOrDefault(s=>s.Template==(string)negative["deck"]);
      if(negativeDeck!=null)Guard(negativeDeck,"site: native preview rejects a deck cleated onto a plain platform",()=>{
        Create(Spec((string)negative["template"]),At(Xyz(negative)));
        var d=negative["deckAt"].ToObject<int[]>();
        SitePreview(negativeDeck,At(new Vector3Int(d[0],d[1],d[2])),false,"site: native preview rejects a deck cleated onto a plain platform");
      });
      foreach(var s in _batch)Guard(s,"placement",()=>Place(s));
      foreach(var s in Placed().Where(s=>s.Building.HasComponent<HydroTurbine>()))Guard(s,"site: river reach",()=>PrepareReach(s));
      foreach(var s in Placed())Guard(s,"entrance path",()=>PlaceEntrancePath(s));
      RouteAll();
      foreach(var s in Placed().Where(s=>s.Manufactory)) {
        Guard(s,"recipe",()=>ChooseRecipe(s));
        var subject=s;s.Manufactory.ProductionFinished+=(sender,args)=>subject.Produced++;
      }
      _hatchery=Placed().FirstOrDefault(s=>s.Building.HasComponent<WaterDepthWorkCells>());
      _camera.MoveTargetTo(new Vector3(_siteZone.center.x,_ground,_siteZone.center.y));_camera.SetZoomLevel(38,0);
      _speed.ChangeSpeed(3);
      Phase(10,"sites placed; water fill after the native placement updates");
    }
    // A rejected site placement is a failure: the map was made for it.
    private void PlaceOnSite(Subject s,Placement p) {
      if(!_validator.BlocksValid(s.Spec,p)){Record(s,"placement",false,"native BlockValidator rejected the prepared site at "+p.Coordinates+" "+p.Orientation);return;}
      try {s.Building=Create(s.Spec,p);}
      catch(Exception error){Record(s,"placement",false,error.Message+" (prepared site)");return;}
      s.Placed=true;
      var expected=s.Spec.GetBlocks(s.Building.Placement).Where(k=>k.IsOccupied).Select(k=>k.Coordinates).ToList();
      Record(s,"placement",Occupied(s.Building).SetEquals(expected)&&expected.All(c=>_blocks.GetObjectsAt(c).Contains(s.Building)),
        "finished on its site at "+s.Building.Coordinates+" "+p.Orientation+"; "+expected.Count+" occupied cells registered");
    }

    // ---------- water ----------
    // A failed fill is recorded for the harness; the site checks that need the water then fail on their own.
    private void FillSites() {
      try {FillSiteWater();}
      catch(Exception error){_harness.Add("site water fill failed: "+error);Debug.LogWarning(Tag+" site water fill failed: "+error);}
      _siteFilled=true;_lastTopUp=_clock.PartialDayNumber;
    }
    private void FillSiteWater() {
      var fill=new JObject();
      foreach(var pit in _sites["pits"]) {
        float clean=(float?)pit["clean"]??0f,radioactive=(float?)pit["radioactive"]??0f;
        if(clean<=0f&&radioactive<=0f)continue;
        int cells=0;
        foreach(var c in PitCells((string)pit["id"])) {
          if(clean>0f)_waterService.AddCleanWater(c,clean);
          if(radioactive>0f)_radiation.AddRadioactiveWater(c,radioactive);
          cells++;
        }
        fill[(string)pit["id"]]=new JObject{["cells"]=cells,["clean"]=clean*cells,["radioactive"]=radioactive*cells};
      }
      if(_turbine) {
        float surface=(float)_sites["hydro"]["upperSurface"];double added=0;
        foreach(var (cell,index) in ReachColumns()) {
          if(cell.y>=_divider)continue;
          var column=_water.WaterColumns[index];
          float depth=Mathf.Min(surface,column.Ceiling)-column.Floor;
          if(depth<=0f)continue;
          _waterService.AddCleanWater(cell,depth);added+=depth;
        }
        fill["upperReach"]=Math.Round(added,1);
      }
      _siteReport["fill"]=fill;
      Debug.Log(Tag+" site water added through the native water services: "+fill.ToString(Newtonsoft.Json.Formatting.None));
    }
    // The pond keeps its depth (evaporation, the pump, the shower); the radioactive pools are not topped up.
    private void SiteTick() {
      if(_siteFilled&&(_clock.PartialDayNumber-_lastTopUp)*24f>TopUpIntervalHours) {
        _lastTopUp=_clock.PartialDayNumber;
        foreach(var pit in _sites["pits"].Where(p=>p["topUpBelow"]!=null)) {
          float below=(float)pit["topUpBelow"],clean=(float)pit["clean"];
          foreach(var c in PitCells((string)pit["id"])) {
            float depth=_water.WaterDepth(c);
            if(depth<below){_waterService.AddCleanWater(c,clean-depth);_toppedUp+=clean-depth;}
          }
        }
      }
      if(_turbineOpen&&_turbine) {
        var node=_turbine.GetComponent<MechanicalNode>();
        if(_turbine.OutputHp>_peakHp){_peakHp=_turbine.OutputHp;_peakState=_turbine.State+" head "+_turbine.AvailableHead.ToString("0.00")+
          " upstream "+_turbine.UpstreamHeight.ToString("0.00")+" downstream "+_turbine.DownstreamHeight.ToString("0.00");}
        _peakFlow=Math.Max(_peakFlow,_turbine.ActualFlow);_peakHead=Math.Max(_peakHead,_turbine.AvailableHead);
        _peakNodeOutput=Math.Max(_peakNodeOutput,node.Actuals.PowerOutput);
        if(node.Graph!=null)_peakSupply=Math.Max(_peakSupply,node.Graph.PowerSupply);
      }
    }
    private float PoolRadiation(string pit)=>PitCells(pit).Sum(c=>_radiation.Sample(c).WaterRadiation*_water.WaterDepth(c));
    private float PoolWater(string pit)=>PitCells(pit).Sum(c=>_water.WaterDepth(c));

    // ---------- river reach (HydroBasinAcceptance geometry, one turbine) ----------
    private IEnumerable<(Vector3Int Cell,int Index)> ReachColumns() {
      for(int x=_basin.xMin+1;x<_basin.xMax-1;x++)for(int y=_basin.yMin+1;y<_basin.yMax-1;y++) {
        int index=_indices.CellToIndex(new Vector2Int(x,y));
        for(int ordinal=0;ordinal<_water.ColumnCount(index);ordinal++) {
          int index3D=index+ordinal*_indices.VerticalStride;
          yield return (new Vector3Int(x,y,_water.WaterColumns[index3D].Floor),index3D);
        }
      }
    }
    private (double Upper,double Lower) ReadReach() {
      double upper=0,lower=0;
      foreach(var (cell,index) in ReachColumns()) {
        var c=_water.WaterColumns[index];double volume=c.WaterDepth+c.Overflow;
        if(cell.y<_divider)upper+=volume;else if(cell.y>_divider)lower+=volume;
      }
      return (upper,lower);
    }
    private void PrepareReach(Subject s) {
      var hydro=_sites["hydro"];
      var basin=hydro["basin"].ToObject<int[]>();
      _basin=new RectInt(basin[0],basin[1],basin[2],basin[3]);
      _divider=(int)hydro["divider"];
      _turbine=s.Building.GetComponent<HydroTurbine>();
      _turbine.SetClosed(true);_turbine.SetDischargeLimit((float)hydro["dischargeLimit"]);
      var raised=hydro["damRaisedColumns"].ToObject<int[]>();
      int top=(int)hydro["damTop"],raisedBottom=(int)hydro["damRaisedBottom"],blocks=0;
      var dam=Spec((string)hydro["dam"]);
      for(int x=_basin.xMin+1;x<_basin.xMax-1;x++) {
        int bottom=x>=raised[0]&&x<=raised[1]?raisedBottom:_ground;
        for(int z=bottom;z<=top;z++){Create(dam,At(new Vector3Int(x,_divider,z)));blocks++;}
      }
      Record(s,"site: river reach dammed",true,blocks+" "+hydro["dam"]+" across row y="+_divider+" of the walled reach "+_basin+
        "; gate closed, discharge limit "+_turbine.DischargeLimit);
    }
    private void OpenTurbine() {
      if(!_turbine)return;
      _reachAtOpen=ReadReach();_turbine.SetClosed(false);_turbineOpen=true;
      Debug.Log(Tag+" site: turbine gate opened; reach upper "+_reachAtOpen.Upper.ToString("0.0")+" lower "+_reachAtOpen.Lower.ToString("0.0"));
    }
    private void HydroVerdict(Subject s) {
      var reach=ReadReach();
      double delivered=reach.Lower-_reachAtOpen.Lower,drawn=_reachAtOpen.Upper-reach.Upper;
      bool ok=_turbineOpen&&_peakHp>100f&&_peakFlow>.1f&&delivered>1&&_peakSupply>0f;
      Record(s,"site: power from flow",ok,"peak flow "+_peakFlow.ToString("0.000")+" (limit "+_turbine.DischargeLimit+"), peak turbine output "+
        _peakHp.ToString("0")+" hp ("+_peakState+"), peak native node output "+_peakNodeOutput.ToString("0")+" hp, peak graph supply "+
        _peakSupply.ToString("0")+" hp; upper reach "+_reachAtOpen.Upper.ToString("0.0")+" -> "+reach.Upper.ToString("0.0")+
        ", lower reach "+_reachAtOpen.Lower.ToString("0.0")+" -> "+reach.Lower.ToString("0.0")+" (delivered "+delivered.ToString("0.0")+
        ", drawn "+drawn.ToString("0.0")+")");
      _siteReport["hydro"]=new JObject{["peakFlow"]=_peakFlow,["peakHp"]=_peakHp,["peakNodeOutput"]=_peakNodeOutput,["peakSupply"]=_peakSupply,
        ["peakHead"]=_peakHead,["upperAtOpen"]=_reachAtOpen.Upper,["lowerAtOpen"]=_reachAtOpen.Lower,["upperEnd"]=reach.Upper,["lowerEnd"]=reach.Lower};
      _turbine.SetClosed(true);_turbineOpen=false;
    }

    // ---------- side platforms ----------
    // Native preview (PreviewFactory, as the build tool) repositioned to the placement, then the native
    // block rules and every IBlockObjectValidator (AnchoredDeckValidator and AdaptiveSupportsPlacementValidator
    // check previews only). A rejected deck must fail on the anchor rule alone.
    private void SitePreview(Subject s,Placement p,bool expectValid,string check) {
      var preview=_previews.Create(s.Blueprint.GetSpec<PlaceableBlockObjectSpec>());
      try {
        var block=preview.BlockObject;
        block.Reposition(p);
        bool blocks=_validator.BlocksValid(block.PositionedBlocks);
        bool validators=_validation.AreValid(new BaseComponent[]{block},out var message);
        string anchorMessage=_loc.T(AnchoredDeckLoc.RequiresAnchor);
        string detail="preview at "+p.Coordinates+": native blocks "+(blocks?"valid":"invalid")+", validators "+
          (validators?"valid":"rejected: "+message);
        if(expectValid)Record(s,check,blocks&&validators,detail);
        else Record(s,check,blocks&&!validators&&message==anchorMessage,
          detail+" (expected native blocks valid and the anchor rule '"+anchorMessage+"')");
      } finally {
        UnityEngine.Object.Destroy(preview.GameObject);
      }
    }
    // Native build-tool path (PreviewPlacer -> BlockObjectPreviewPicker.CenteredPreviewCoordinates): a ray
    // straight down onto the cell the CustomPivot sits in (the door cell on the bank at the contract
    // placement). The picker takes the first terrain or stackable top face along the ray and subtracts
    // BaseZ, so the picked placement must be the contract placement: the bank height, not the riverbed
    // under the pens. That placement then passes the same native preview validation as the build tool.
    private void CursorPreview(Subject s,Placement contract) {
      const string Check="site: cursor on the door cell picks the bank height";
      var placeable=s.Blueprint.GetSpec<PlaceableBlockObjectSpec>();
      var pivot=placeable.CustomPivot;
      if(!pivot.HasCustomPivot){Record(s,Check,false,"no CustomPivot: the cursor sits over the footprint centre");return;}
      var local=new Vector3Int(Mathf.FloorToInt(pivot.Coordinates.x),Mathf.FloorToInt(pivot.Coordinates.y),s.Spec.BaseZ);
      var cell=Blocks.From(s.Spec).Transform(local,contract);
      // The native tools pass a grid-space ray (CameraService.ScreenPointToRayInGridSpace; GridTraversal
      // .TraverseRay steps grid x, y and height z): straight down from 20 above the door cell.
      var ray=new Ray(new Vector3(cell.x+.5f,cell.y+.5f,cell.z+20f),new Vector3(0f,0f,-1f));
      var picked=_picker.CenteredPreviewCoordinates(placeable,contract.Orientation,ray);
      if(!picked.HasValue){Record(s,Check,false,"the native picker found no top face under the cursor at "+cell);return;}
      var at=picked.Value.Coordinates;
      if(at!=contract.Coordinates){Record(s,Check,false,"cursor at "+cell+" picked "+at+", contract placement "+contract.Coordinates);return;}
      Record(s,Check,true,"cursor on the door cell "+cell+" (terrain height "+_terrain.GetTerrainHeight(cell)+") picked "+at+" = contract placement");
      SitePreview(s,new Placement(at,contract.Orientation,FlipMode.Unflipped),true,"site: native preview from the cursor is valid");
    }
    private void BuildOnDeck(Subject s) {
      var slabs=s.Building.PositionedBlocks.GetAllBlocks().Where(b=>b.IsOccupied&&b.Stackable==BlockStackable.BlockObject)
        .Select(b=>b.Coordinates+new Vector3Int(0,0,1)).OrderBy(c=>c.y).ThenBy(c=>c.x).ToList();
      var rejected=new List<string>();int paths=0;bool platform=false;
      foreach(var c in slabs) {
        try {
          if(!platform){Create(_platform,At(c));Create(_path,At(c+new Vector3Int(0,0,1)));platform=true;continue;}
          Create(_path,At(c));paths++;
        } catch(Exception error){rejected.Add(c+": "+error.Message);}
      }
      Record(s,"site: building on the deck",rejected.Count==0&&platform&&paths==slabs.Count-1,
        slabs.Count+" slab cells: Platform.IronTeeth with a Path on top at "+(slabs.Count>0?slabs[0].ToString():"-")+", "+paths+" Paths on the others"+
        (rejected.Count>0?"; rejected: "+string.Join("; ",rejected.Take(4)):""));
    }

    // ---------- snapshots and verdicts ----------
    private void SiteSnapshot(Subject s) {
      var b=s.Building;var site=s.Site;
      if(site==null)return;
      var under=(string)site["understructure"];
      if(under!=null) {
        var u=_sites["understructures"].Single(x=>(string)x["template"]==under);
        bool below=_blocks.GetObjectsAt(Xyz(u)).Any(o=>o.GetComponent<TemplateSpec>()?.TemplateName==under);
        Record(s,"site: on the map-authored "+under,below,"native UnderstructureConstraint accepted the placement; "+under+" registered at "+Xyz(u)+"="+below);
      }
      var cells=b.GetComponent<WaterDepthWorkCells>();
      if(cells) {
        var depths=cells.Spec.WorkCells.Select(c=>b.TransformCoordinates(c)).Select(c=>c+" "+_water.WaterDepth(c).ToString("0.00"));
        var blockable=b.GetComponent<BlockableObject>();
        Record(s,"site: nursery pens wet",!cells.IsBlockedByDepth&&blockable.IsUnblocked,"work cells ["+string.Join("; ",depths)+"] blockedByDepth="+
          cells.IsBlockedByDepth+" unblocked="+blockable.IsUnblocked);
      }
      var pipe=b.GetComponent<WaterInputPipeCoordinates>();
      if(pipe) {
        float depth=_water.WaterDepth(pipe.Coordinates);
        Record(s,"site: intake pipe reaches water",pipe.Depth>0&&depth>0f,"pipe depth "+pipe.Depth+" to "+pipe.Coordinates+", water "+depth.ToString("0.00")+
          " underwater="+b.GetComponent<WaterInput>()?.IsUnderwater);
        if(b.GetComponent<RadioactiveSludgeIntake>()!=null) {
          var sample=_radiation.Sample(pipe.Coordinates);
          Record(s,"site: intake column radioactive",_radiation.IsColumnContaminated(pipe.Coordinates),"radioactive share "+sample.WaterRadiation.ToString("0.000")+
            " badwater "+sample.BadwaterShare.ToString("0.000")+"; pool "+site["pit"]+" radioactive volume "+PoolRadiation((string)site["pit"]).ToString("0.00")+
            ", control "+site["control"]+" "+PoolRadiation((string)site["control"]).ToString("0.00"));
        }
      }
      var pool=b.GetComponent<TickableWaterBuilding>();
      if(pool) {
        float depth=_water.WaterDepth(pool.WaterCoordinatesTransformed);
        var blockable=b.GetComponent<BlockableObject>();
        Record(s,"site: pool cell in water",depth>0f&&(!blockable||blockable.IsUnblocked),"water cell "+pool.WaterCoordinatesTransformed+" depth "+
          depth.ToString("0.00")+" unblocked="+(!blockable||blockable.IsUnblocked));
      }
      if(b.HasComponent<HydroTurbine>()) {
        var reach=ReadReach();
        Record(s,"site: upper reach filled, gate closed",reach.Upper>1000&&reach.Lower<.5,"upper "+reach.Upper.ToString("0.0")+" lower "+reach.Lower.ToString("0.0")+
          " state "+_turbine.State+" closed="+_turbine.GateIsClosed);
      }
    }
    private void SiteWaveStarted() {
      var sludge=_wave.FirstOrDefault(s=>s.Building&&s.Building.GetComponent<RadioactiveSludgeIntake>()!=null);
      if(sludge==null)return;
      var site=sludge.Site;
      _w0=_radiation.TotalWaterRadiation;_c0=PoolRadiation((string)site["control"]);_p0=PoolRadiation((string)site["pit"]);
      _produced0=sludge.Produced;_progress0=sludge.Manufactory.ProductionProgress;
      _buffer0=sludge.Building.GetComponent<RadioactiveSludgeIntake>().BufferedVolume;
      _sludgeStart=_clock.PartialDayNumber;_sludgeBaseline=true;
      Debug.Log(Tag+" site: radiation baseline world "+_w0.ToString("0.000")+" pool "+_p0.ToString("0.000")+" control "+_c0.ToString("0.000"));
    }
    private void SiteWaveVerdict(Subject s) {
      var site=s.Site;var b=s.Building;
      if(!b)return;
      var produces=(string)site["produces"];
      if(produces!=null) {
        var m=s.Manufactory;
        Record(s,"site: produces "+produces,s.Produced>0,s.Produced+" native production cycles finished; stock ["+
          string.Join(",",m.Inventory.Stock.Select(g=>g.GoodId+" "+g.Amount))+"]");
      }
      var intake=b.GetComponent<RadioactiveSludgeIntake>();
      if(intake!=null&&_sludgeBaseline)SludgeBalance(s,intake);
      if(s==_hatchery)PlaceDeckPaths(s);
    }
    // World water radiation W, the pumped pool P and the control pool C at the start of the wave and now.
    // Recovered R = volume per cycle x (cycles finished + progress gained) + intake buffer gained.
    // The only radioactive water in the world is in the two pools, and the identical control pool shows
    // the natural drift D (evaporation into the soil, soil exchange, decay; b165: 13% in 8 h). So the
    // pumped pool must fall by R + D, and the world by R + 2D. The tolerance allows 5% of R and 5% of the
    // drift (the pumped pool holds less water than the control while drifting).
    private void SludgeBalance(Subject s,RadioactiveSludgeIntake intake) {
      var site=s.Site;var m=s.Manufactory;
      var spec=s.Building.GetComponent<RadioactiveSludgeIntakeSpec>();
      float w1=_radiation.TotalWaterRadiation,c1=PoolRadiation((string)site["control"]),p1=PoolRadiation((string)site["pit"]);
      int cycles=s.Produced-_produced0;
      float recovered=spec.RadioactiveVolumePerCycle*(cycles+m.ProductionProgress-_progress0)+intake.BufferedVolume-_buffer0;
      float worldDrop=_w0-w1,controlDrift=_c0-c1,poolDrop=_p0-p1;
      float poolError=poolDrop-controlDrift-recovered,error=worldDrop-2f*controlDrift-recovered;
      // Water radiation outside both pool measures at the baseline (b165: 0.126 of 20.77; it was gone by the
      // end, consistent with the native 0.005 share cutoff on thin water) may leave the world total as well.
      float outside=Math.Abs(_w0-_p0-_c0);
      float poolTolerance=.03f+.05f*recovered+.05f*controlDrift,tolerance=.03f+.05f*recovered+.05f*2f*controlDrift+outside;
      float hours=(_clock.PartialDayNumber-_sludgeStart)*24f;
      Record(s,"site: radioactive water becomes sludge",cycles>0&&recovered>0f,cycles+" RadioactiveSludge in "+hours.ToString("0.0")+" h; recovered "+
        recovered.ToString("0.000")+" radioactive volume ("+spec.RadioactiveVolumePerCycle+" per good, buffer "+intake.BufferedVolume.ToString("0.000")+")");
      string water="; water pumped pool "+PoolWater((string)site["pit"]).ToString("0.00")+" vs control "+PoolWater((string)site["control"]).ToString("0.00");
      Record(s,"site: pumped pool falls by the recovered amount",cycles>0&&Math.Abs(poolError)<=poolTolerance,
        "pumped pool "+_p0.ToString("0.000")+" -> "+p1.ToString("0.000")+" (fell "+poolDrop.ToString("0.000")+") = recovered "+recovered.ToString("0.000")+
        " + control drift "+controlDrift.ToString("0.000")+" (control "+_c0.ToString("0.000")+" -> "+c1.ToString("0.000")+"); difference "+
        poolError.ToString("0.0000")+" (tolerance "+poolTolerance.ToString("0.000")+")"+water);
      Record(s,"site: world radioactivity falls by the recovered amount",cycles>0&&Math.Abs(error)<=tolerance,
        "world water radiation "+_w0.ToString("0.000")+" -> "+w1.ToString("0.000")+" (fell "+worldDrop.ToString("0.000")+") = recovered "+recovered.ToString("0.000")+
        " + drift of both pools 2 x "+controlDrift.ToString("0.000")+"; difference "+error.ToString("0.0000")+" (tolerance "+tolerance.ToString("0.000")+
        ", of which "+outside.ToString("0.000")+" was outside both pools at the start)"+water);
      _siteReport["sludge"]=new JObject{["hours"]=hours,["cycles"]=cycles,["recovered"]=recovered,["world0"]=_w0,["world1"]=w1,
        ["pool0"]=_p0,["pool1"]=p1,["control0"]=_c0,["control1"]=c1,["poolError"]=poolError,["poolTolerance"]=poolTolerance,["worldError"]=error,["worldTolerance"]=tolerance};
    }
    // Player paths on the hatchery deck (FisheryAcceptance.HatcheryPathCells, the verified fixture layout),
    // built after the hatchery has worked; cells taken by this harness's power or pipe objects are skipped.
    private void PlaceDeckPaths(Subject s) {
      var b=s.Building;var placed=new List<string>();var harness=new List<string>();var rejected=new List<string>();
      foreach(var local in FisheryAcceptance.HatcheryPathCells().OrderBy(c=>c.y).ThenBy(c=>c.x)) {
        var world=b.TransformCoordinates(local);
        if(IsRoad(world)){_deckPaths.Add(_blocks.GetObjectsAt(world).First(o=>o.GetComponent<TemplateSpec>()?.TemplateName=="Path"));placed.Add(local.ToString());continue;}
        var occupant=_blocks.GetObjectsAt(world).FirstOrDefault(o=>o!=b);
        if(occupant&&s.Attached.Contains(occupant)){harness.Add(local+" "+occupant.GetComponent<TemplateSpec>()?.TemplateName);continue;}
        try {_deckPaths.Add(Create(_path,At(world)));placed.Add(local.ToString());}
        catch(Exception error){rejected.Add(local+": "+error.Message);}
      }
      Record(s,"site: player paths on the deck",rejected.Count==0&&placed.Count>0,placed.Count+" native Paths on the deck and bank cells"+
        (harness.Count>0?"; "+harness.Count+" cells hold this test's power/pipe objects ("+string.Join(", ",harness)+")":"")+
        (rejected.Count>0?"; rejected: "+string.Join("; ",rejected.Take(4)):""));
      // Native BlockObjectBatchLoader adds saved objects ordered by (CoordinatesAtBaseZ.z, GetHighestOccupation)
      // and deletes any whose support is not there yet (Waterside/StackableBaseLoadOrder.cs).
      int z=b.CoordinatesAtBaseZ.z,rank=BlockObjectBatchLoader.GetHighestOccupation(b);
      var early=new List<string>();int onDeck=0;
      foreach(var other in _entities.Entities.Select(e=>e.GetComponent<BlockObject>()).Where(o=>o&&o!=b)) {
        bool standsOnSlab=other.PositionedBlocks.GetFoundationBlocks().Any(f=>
          b.PositionedBlocks.TryGetBlock(f.Coordinates-new Vector3Int(0,0,1),out var slab)&&slab.Stackable.IsStackable());
        if(!standsOnSlab)continue;
        onDeck++;
        int oz=other.CoordinatesAtBaseZ.z,orank=BlockObjectBatchLoader.GetHighestOccupation(other);
        if(oz<z||oz==z&&orank<=rank)early.Add(other.Name+" at "+other.Coordinates+" ("+oz+","+orank+")");
      }
      Record(s,"site: deck paths load after the hatchery",rank==StackableBaseLoadOrder.SupportFirst&&early.Count==0&&onDeck>0,
        "hatchery load key ("+z+","+rank+"); "+onDeck+" objects stand on its deck slabs"+(early.Count>0?"; loaded before it: "+string.Join("; ",early.Take(4)):""));
    }
    private void SiteEndChecks() {
      if(_hatchery!=null&&_deckPaths.Count>0) {
        int standing=_deckPaths.Count(p=>p&&_blocks.GetObjectsAt(p.Coordinates).Contains(p));
        var blockable=_hatchery.Building.GetComponent<BlockableObject>();
        Record(_hatchery,"site: deck paths survive",standing==_deckPaths.Count,standing+" of "+_deckPaths.Count+" deck paths still standing and registered at the end of the batch;"+
          " hatchery unblocked="+blockable.IsUnblocked+", nursery blockedByDepth="+_hatchery.Building.GetComponent<WaterDepthWorkCells>().IsBlockedByDepth);
      }
      _siteReport["pondTopUp"]=Math.Round(_toppedUp,2);
    }
  }
}
#endif
