#if !UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using Bindito.Core;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockingSystem;
using Timberborn.BlockObjectTools;
using Timberborn.BlockSystem;
using Timberborn.Buildings;
using Timberborn.BuildingsReachability;
using Timberborn.CameraSystem;
using Timberborn.ConstructionSites;
using Timberborn.Coordinates;
using Timberborn.CoreUI;
using Timberborn.Effects;
using Timberborn.EnterableSystem;
using Timberborn.EntitySystem;
using Timberborn.GameDistricts;
using Timberborn.Localization;
using Timberborn.MechanicalSystem;
using Timberborn.NaturalResources;
using Timberborn.Navigation;
using Timberborn.NeedSystem;
using Timberborn.PathSystem;
using Timberborn.SingletonSystem;
using Timberborn.StatusSystem;
using Timberborn.TemplateSystem;
using Timberborn.TerrainSystem;
using Timberborn.TimeSystem;
using Timberborn.WaterSystem;
using Timberborn.WorkSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Explicit disposable test only: -deepFrontierLoadAcceptance -deepFrontierNewGame "user:<map>"
  // -deepFrontierFlipProbe [-deepFrontierFlipProbeLabel <label>] (tools/start_flip_probe.ps1).
  [Context("Game")]
  public sealed class FlipPlacementProbeConfigurator : Configurator {
    protected override void Configure() {
      var args=Environment.GetCommandLineArgs();
      if(!args.Contains(FlipPlacementProbe.Flag))return;
      if(!args.Contains("-deepFrontierLoadAcceptance")||MemoryLoadProbe.NewGameMap()==null)
        throw new InvalidOperationException(FlipPlacementProbe.Flag+" requires -deepFrontierLoadAcceptance with -deepFrontierNewGame");
      if(args.Contains(AllBuildingsAcceptance.Flag))throw new InvalidOperationException(FlipPlacementProbe.Flag+" and "+AllBuildingsAcceptance.Flag+" are separate runs");
      Bind<FlipPlacementProbe>().AsSingleton();
    }
  }

  // Build 176 user reports on flipped FishHatchery, FisheryWorks and Greenhouse placements: entrances
  // "don't work" and walls "don't take power". Every placement a player can make (4 rotations x
  // unflipped/flipped) of each, one at a time on a levelled pad next to the district centre; the
  // hatchery on a carved bank (bank at the pad level, a river one layer lower with water in it).
  // Per placement:
  //   hatchery: the native build-tool picker (BlockObjectPreviewPicker.CenteredPreviewCoordinates) with
  //     the cursor on the unflipped pivot cell (the door cell, or its mirror when flipped), with player
  //     Paths along the bank and a SolarPanel beside it, picks the bank level (layer BaseZ on the bank);
  //   the native preview at that placement is valid; the finished building registers its blocks;
  //   entrance: a plain player Path on the native Entrance, a road from it to the district centre; the
  //     native path connection service connects the entrance Path toward the doorstep (what
  //     DynamicPathModel draws), the building gets the native district, no Unconnected status, the
  //     entrance is neither blocked nor inaccessible, the single access is the Entrance centre;
  //   power: for every horizontal and Top transput of the building, platforms where the target cell
  //     needs support, a native PowerShaft preview valid in the target cell, the finished shaft joins
  //     the building's graph through that transput, and the native connector socket on the building
  //     (MechanicalConnectorTargetSpec) is shown;
  //   a beaver employed there reaches the building (inside it, or within 1.5 of its entrance access).
  // Results: outputs/flip-probe-<label>.json and "[DeepFrontier FlipProbe]" log lines.
  internal sealed class FlipPlacementProbe : IPostLoadableSingleton,IUpdatableSingleton {
    internal const string Flag="-deepFrontierFlipProbe";
    private const string LabelFlag="-deepFrontierFlipProbeLabel";
    private const string Tag="[DeepFrontier FlipProbe]";
    private static readonly string Outputs=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),"TimberbornModding","outputs");
    private static readonly string[] Templates={"FishHatchery.IronTeeth","FisheryWorks.IronTeeth","Greenhouse.IronTeeth"};
    private static readonly Orientation[] Rotations={Orientation.Cw0,Orientation.Cw90,Orientation.Cw180,Orientation.Cw270};
    private static readonly string[] BasicNeeds={"Hunger","Thirst","Sleep"};
    private const int SlotSize=26,SearchRadius=70,SettleFrames=90,WaterFrames=240;
    private const float WalkHours=6f,RiverDepth=.8f;

    private sealed class Case {
      public string Template;public Orientation Orientation;public FlipMode Flip;
      public BlockObjectSpec Spec;public PlaceableBlockObjectSpec Placeable;
      public Placement Placement;public BlockObject Building;
      public readonly List<BlockObject> Objects=new();
      public readonly List<Vector3Int> Carved=new();
      public readonly JArray Checks=new();
      public readonly JArray Faces=new();
      public List<Transput> Transputs;public int Face;
      public Worker Worker;public float WalkStart;public float Closest=float.MaxValue;
      public string Id=>Template.Replace(".IronTeeth","")+" "+Orientation+(Flip.IsFlipped?" flipped":"");
    }

    private readonly EntityRegistry _entities;
    private readonly EntityService _entityService;
    private readonly TemplateService _templates;
    private readonly BlockObjectFactory _factory;
    private readonly BlockValidator _validator;
    private readonly BlockObjectValidationService _validation;
    private readonly IBlockService _blocks;
    private readonly StackableBlockService _stackable;
    private readonly ITerrainService _terrain;
    private readonly IThreadSafeWaterMap _water;
    private readonly IWaterService _waterService;
    private readonly SpeedManager _speed;
    private readonly IDayNightCycle _clock;
    private readonly CameraService _camera;
    private readonly ILoc _loc;
    private readonly PanelStack _panels;
    private readonly PreviewFactory _previews;
    private readonly Timberborn.BlockObjectPickingSystem.BlockObjectPreviewPicker _picker;
    private readonly IConnectionService _connections;
    private readonly INavMeshService _nav;
    private readonly string _label;
    private readonly List<Case> _cases=new();
    private readonly List<string> _harness=new();
    private readonly List<Worker> _workers=new();
    private BlockObjectSpec _path,_shaft,_platform,_solar;
    private DistrictCenter _district;
    private Vector3Int _dcEntrance;
    private RectInt _slot,_routeArea;
    private int _ground,_frame,_index=-1,_wait;
    private string _step="setup",_unconnected;
    private bool _finished;
    private IPanelController _lastPanel;private int _panelFrames;
    private float _lastRefresh;

    public FlipPlacementProbe(EntityRegistry entities,EntityService entityService,TemplateService templates,BlockObjectFactory factory,
        BlockValidator validator,BlockObjectValidationService validation,IBlockService blocks,StackableBlockService stackable,
        ITerrainService terrain,IThreadSafeWaterMap water,IWaterService waterService,SpeedManager speed,IDayNightCycle clock,
        CameraService camera,ILoc loc,PanelStack panels,PreviewFactory previews,
        Timberborn.BlockObjectPickingSystem.BlockObjectPreviewPicker picker,IConnectionService connections,INavMeshService nav) {
      _entities=entities;_entityService=entityService;_templates=templates;_factory=factory;_validator=validator;_validation=validation;
      _blocks=blocks;_stackable=stackable;_terrain=terrain;_water=water;_waterService=waterService;_speed=speed;_clock=clock;
      _camera=camera;_loc=loc;_panels=panels;_previews=previews;_picker=picker;_connections=connections;_nav=nav;
      var args=Environment.GetCommandLineArgs();
      int i=Array.IndexOf(args,LabelFlag);
      _label=i>=0&&i+1<args.Length?args[i+1].Trim('"'):"run";
      if(_label.IndexOfAny(Path.GetInvalidFileNameChars())>=0)throw new InvalidOperationException(LabelFlag+" is not a valid file name part: "+_label);
    }

    // ---------- recording ----------
    private static void Require(bool value,string message) {if(!value)throw new InvalidOperationException(message);}
    private void Record(Case c,string check,bool ok,string detail)=>Add(c,check,ok?"PASS":"FAIL",detail);
    private void Add(Case c,string check,string status,string detail) {
      c.Checks.Add(new JObject{["check"]=check,["status"]=status,["detail"]=detail});
      var line=Tag+" "+status+" "+c.Id+" "+check+": "+detail;
      if(status=="FAIL")Debug.LogWarning(line);else Debug.Log(line);
    }

    // ---------- helpers ----------
    private BlockObjectSpec Spec(string name) {
      var t=_templates.GetAll<TemplateSpec>().SingleOrDefault(x=>x.TemplateName==name);
      Require(t!=null,"Template not loaded: "+name);
      return t.Blueprint.GetSpec<BlockObjectSpec>();
    }
    private static Placement At(Vector3Int c,Orientation o=Orientation.Cw0)=>new(c,o,FlipMode.Unflipped);
    private bool Free(BlockObjectSpec spec,Vector3Int c)=>_validator.BlocksValid(spec,At(c));
    private BlockObject Create(Case c,BlockObjectSpec spec,Placement p) {
      Require(_validator.BlocksValid(spec,p),"native placement rejected "+spec.Blueprint.Name+" at "+p.Coordinates+" "+p.Orientation+(p.FlipMode.IsFlipped?" flipped":""));
      var b=_factory.CreateFinished(new EntitySetup.Builder(spec.Blueprint).AddInitComponent(new FinishedConstructionSiteInit()),p);
      if(!_validation.IsValid(b)) {
        _entityService.Delete(b.GetComponent<EntityComponent>());
        throw new InvalidOperationException("native object requirements rejected "+spec.Blueprint.Name+" at "+p.Coordinates);
      }
      c?.Objects.Add(b);
      return b;
    }
    private void Delete(BlockObject b) {if(b){var e=b.GetComponent<EntityComponent>();if(e)_entityService.Delete(e);}}
    private bool IsRoad(Vector3Int c)=>_blocks.GetObjectsAt(c).Any(b=>b.GetComponent<TemplateSpec>()?.TemplateName=="Path");
    private static RectInt Bounds(BlockObjectSpec spec,Placement p) {
      var blocks=spec.GetBlocks(p).ToArray();
      int x0=blocks.Min(b=>b.Coordinates.x),y0=blocks.Min(b=>b.Coordinates.y);
      return new RectInt(x0,y0,blocks.Max(b=>b.Coordinates.x)-x0+1,blocks.Max(b=>b.Coordinates.y)-y0+1);
    }
    private List<string> VisibleStatuses(BaseComponent b) {
      var subject=b.GetComponent<StatusSubject>();
      if(!subject)return new List<string>();
      return subject.ActiveStatuses.Where(s=>s.IsVisible()).Select(s=>s.StatusDescription).ToList();
    }
    private static string Xyz(Vector3Int c)=>"("+c.x+","+c.y+","+c.z+")";

    // ---------- lifecycle ----------
    public void PostLoad() {_speed.ChangeSpeed(0);_unconnected=_loc.T("Status.Buildings.Unconnected");}

    public void UpdateSingleton() {
      if(_finished)return;
      try {
        if(++_frame<90)return;
        DismissPanels();
        if((_clock.PartialDayNumber-_lastRefresh)*24f>3f){RefreshBeavers();_lastRefresh=_clock.PartialDayNumber;}
        if(_wait>0){_wait--;return;}
        switch(_step) {
          // Native deletions take effect at the end of the frame, so cells are reused a few frames later.
          case "setup": Setup();_step="start";_wait=5;break;
          case "start": if(!IsRoad(_dcEntrance))Create(null,_path,At(_dcEntrance));_step="next";break;
          case "next": NextCase();break;
          case "pick": if(Current.Placeable.CustomPivot.HasCustomPivot)CursorPick(Current);_step="place";_wait=5;break;
          case "place": Place(Current);break;
          case "settle": EntranceChecks(Current);Current.Face=0;_step="face";break;
          case "face": FaceStep(Current);break;
          case "faceCleanup": FaceCleanup(Current);break;
          case "walk": WalkStep(Current);break;
          case "cleanup": Cleanup(Current);break;
        }
      } catch(Exception error) {
        _finished=true;_speed.ChangeSpeed(0);
        _harness.Add("FAILED: "+error);
        Write(false);
        Debug.LogError(Tag+" FAILED: "+error);
      }
    }
    private Case Current=>_cases[_index];

    private void DismissPanels() {
      var stacked=AcceptancePanels.Stacked(_panels);
      if(stacked.Count==0){_lastPanel=null;_panelFrames=0;return;}
      var top=stacked[0];
      if(ReferenceEquals(top,_lastPanel)) {
        if(++_panelFrames>120)throw new InvalidOperationException("Panel did not close on Escape: "+AcceptancePanels.Describe(top));
        return;
      }
      _lastPanel=top;_panelFrames=0;
      _harness.Add("dismissed panel: "+AcceptancePanels.Describe(top));
      top.OnUICancelled();
    }
    private void RefreshBeavers() {
      foreach(var e in _entities.Entities.Where(e=>e.HasComponent<NeedManager>()&&e.HasComponent<Enterer>()).ToList()) {
        var needs=e.GetComponent<NeedManager>();
        foreach(var id in BasicNeeds)if(needs.HasNeed(id))
          needs.ApplyEffect(new InstantEffect(id,needs.GetNeedSpec(id).MaximumValue-needs.GetNeedPoints(id),1));
        foreach(var spec in needs.NeedSpecs)if(spec.HasSpec<NeedPreventingWorkSpec>()&&needs.GetNeedPoints(spec.Id)<spec.MaximumValue)
          needs.ApplyEffect(new InstantEffect(spec.Id,spec.MaximumValue-needs.GetNeedPoints(spec.Id),1));
      }
    }

    // ---------- setup ----------
    private void Setup() {
      _path=Spec("Path");_shaft=Spec("PowerShaft.IronTeeth");_platform=Spec("Platform.IronTeeth");
      // Northforge Solar Panel (installed with the user's mod set): the generator the user put beside the hatchery.
      var solar=_templates.GetAll<TemplateSpec>().SingleOrDefault(x=>x.TemplateName=="SolarPanel.IronTeeth");
      _solar=solar?.Blueprint.GetSpec<BlockObjectSpec>();
      var centres=_entities.Entities.Select(e=>e.GetComponent<DistrictCenter>()).Where(d=>d).ToList();
      Require(centres.Count==1,"A new game must have exactly one district centre, found "+centres.Count);
      _district=centres[0];
      var dc=_district.GetComponent<BlockObject>();
      _ground=dc.Coordinates.z;_dcEntrance=dc.PositionedEntrance.Coordinates;
      var adults=_entities.Entities.Select(e=>e.GetComponent<Worker>()).Where(w=>w&&w.WorkerType=="Beaver"&&!w.GetComponent<Timberborn.Beavers.Child>()).ToList();
      _workers.AddRange(adults);
      Require(_workers.Count>0,"The new game has no adult beaver worker");
      ChooseSlot(dc);
      PrepareArea();
      foreach(var template in Templates) {
        var spec=Spec(template);
        foreach(var o in Rotations)foreach(var flip in new[]{FlipMode.Unflipped,FlipMode.Flipped})
          _cases.Add(new Case{Template=template,Orientation=o,Flip=flip,Spec=spec,Placeable=spec.Blueprint.GetSpec<PlaceableBlockObjectSpec>()});
      }
      Debug.Log(Tag+" START label="+_label+" cases="+_cases.Count+" slot="+_slot+" ground="+_ground+" workers="+_workers.Count+
        " solar="+(_solar!=null));
      _camera.MoveTargetTo(new Vector3(_slot.center.x,_ground,_slot.center.y));_camera.SetZoomLevel(30,0);
    }
    private void ChooseSlot(BlockObject dc) {
      var dcBounds=Bounds(dc.GetComponent<BlockObjectSpec>(),dc.Placement);
      var size=_terrain.Size;
      var candidates=new List<RectInt>();
      for(int dx=-SearchRadius;dx<=SearchRadius;dx+=2)for(int dy=-SearchRadius;dy<=SearchRadius;dy+=2)
        candidates.Add(new RectInt(dcBounds.center.x.Round()+dx-SlotSize/2,dcBounds.center.y.Round()+dy-SlotSize/2,SlotSize,SlotSize));
      foreach(var r in candidates.OrderBy(r=>(r.center-dcBounds.center).sqrMagnitude)) {
        if(r.xMin<4||r.yMin<4||r.xMax>size.x-4||r.yMax>size.y-4)continue;
        if(r.Overlaps(new RectInt(dcBounds.xMin-4,dcBounds.yMin-4,dcBounds.width+8,dcBounds.height+8)))continue;
        if(!Usable(r))continue;
        int x0=Math.Min(r.xMin,dcBounds.xMin)-3,y0=Math.Min(r.yMin,dcBounds.yMin)-3;
        int x1=Math.Max(r.xMax,dcBounds.xMax)+3,y1=Math.Max(r.yMax,dcBounds.yMax)+3;
        _slot=r;_routeArea=new RectInt(x0,y0,x1-x0,y1-y0);
        return;
      }
      throw new InvalidOperationException("No dry "+SlotSize+"x"+SlotSize+" slot within "+SearchRadius+" cells of the district centre");
    }
    private bool Usable(RectInt r) {
      for(int x=r.xMin;x<r.xMax;x++)for(int y=r.yMin;y<r.yMax;y++) {
        int h=_terrain.GetTerrainHeight(new Vector3Int(x,y,0));
        if(Math.Abs(h-_ground)>1||_water.WaterDepth(new Vector3Int(x,y,h))>0)return false;
        foreach(var b in _blocks.GetObjectsAt(new Vector3Int(x,y,h)).Concat(_blocks.GetObjectsAt(new Vector3Int(x,y,h-1))))
          if(!Clearable(b.GetComponent<EntityComponent>()))return false;
      }
      return true;
    }
    private static bool Clearable(EntityComponent e) {
      if(e.HasComponent<NaturalResource>())return true;
      var t=e.GetComponent<TemplateSpec>()?.TemplateName??"";
      return t=="Blockage"||t.StartsWith("Ruin",StringComparison.Ordinal);
    }
    private void PrepareArea() {
      foreach(var e in _entities.Entities.ToList()) {
        var b=e.GetComponent<BlockObject>();
        if(!b||!b.Positioned||!Clearable(e))continue;
        if(b.PositionedBlocks.GetAllBlocks().Any(k=>_routeArea.Contains(new Vector2Int(k.Coordinates.x,k.Coordinates.y))))_entityService.Delete(e);
      }
      for(int x=_routeArea.xMin;x<_routeArea.xMax;x++)for(int y=_routeArea.yMin;y<_routeArea.yMax;y++) {
        var cell=new Vector2Int(x,y);
        int h=_terrain.GetTerrainHeight(new Vector3Int(x,y,0));
        if(_blocks.GetObjectsAt(new Vector3Int(x,y,h)).Concat(_blocks.GetObjectsAt(new Vector3Int(x,y,_ground))).Any(b=>!Clearable(b.GetComponent<EntityComponent>())))continue;
        if(_water.WaterDepth(new Vector3Int(x,y,h))>0)continue;
        foreach(var top in _terrain.GetAllHeightsInCell(cell).Where(c=>c.z>_ground).OrderByDescending(c=>c.z).ToArray())
          _terrain.UnsetTerrain(new Vector3Int(x,y,top.z-1),top.z-_ground);
        h=_terrain.GetTerrainHeight(new Vector3Int(x,y,0));
        if(h<_ground)_terrain.SetTerrain(new Vector3Int(x,y,h),_ground-h);
        if(_slot.Contains(cell))Require(_terrain.GetTerrainHeight(new Vector3Int(x,y,0))==_ground,"Slot not level at "+cell);
      }
    }

    // ---------- one placement ----------
    private void NextCase() {
      if(++_index>=_cases.Count){Finish();return;}
      var c=Current;
      var probe=Bounds(c.Spec,new Placement(Vector3Int.zero,c.Orientation,c.Flip));
      var origin=new Vector3Int(_slot.center.x.Round()-probe.width/2-probe.xMin,_slot.center.y.Round()-probe.height/2-probe.yMin,_ground-c.Spec.BaseZ);
      c.Placement=new Placement(origin,c.Orientation,c.Flip);
      Debug.Log(Tag+" CASE "+(_index+1)+"/"+_cases.Count+" "+c.Id+" at "+origin);
      _step="pick";
      if(_speed.CurrentSpeed<=0f)_speed.ChangeSpeed(1);
      // The river's water settles before the cursor pick and the native preview read it.
      if(c.Spec.BaseZ>0){CarveBank(c);_wait=WaterFrames;}
    }
    private void Place(Case c) {
      PreviewCheck(c);
      try {c.Building=Create(c,c.Spec,c.Placement);}
      catch(Exception error){Record(c,"placement",false,error.Message);_step="cleanup";return;}
      var expected=c.Spec.GetBlocks(c.Placement).Where(k=>k.IsOccupied).Select(k=>k.Coordinates).ToList();
      var occupied=new HashSet<Vector3Int>(c.Building.PositionedBlocks.GetOccupiedBlocks().Select(k=>k.Coordinates));
      Record(c,"placement",occupied.SetEquals(expected)&&expected.All(k=>_blocks.GetObjectsAt(k).Contains(c.Building)),
        "finished at "+c.Building.Coordinates+" (layer BaseZ "+c.Spec.BaseZ+" at z="+(c.Building.Coordinates.z+c.Spec.BaseZ)+"); "+expected.Count+" occupied cells registered");
      EntrancePath(c);
      _step="settle";_wait=SettleFrames;
      if(_speed.CurrentSpeed<=0f)_speed.ChangeSpeed(1);
    }
    // The bank: the building's rows y >= 1 (in its own frame), and a ring around them except on the
    // bank side, lowered one layer and filled with clean water; the bank row and the entrance row stay
    // at the pad level (the user's site: bank top 3, river top 2).
    private void CarveBank(Case c) {
      var blocks=Blocks.From(c.Spec);int w=c.Spec.Size.x,h=c.Spec.Size.y;
      var cells=new HashSet<Vector2Int>();
      for(int x=-1;x<=w;x++)for(int y=1;y<=h;y++){var p=blocks.Transform(new Vector3Int(x,y,0),c.Placement);cells.Add(new Vector2Int(p.x,p.y));}
      foreach(var cell in cells) {
        var v=new Vector3Int(cell.x,cell.y,_ground-1);
        Require(_terrain.GetTerrainHeight(v)==_ground,"Bank cell not at pad level: "+cell);
        _terrain.UnsetTerrain(v,1);c.Carved.Add(v);
      }
      foreach(var v in c.Carved)_waterService.AddCleanWater(v,RiverDepth);
      Add(c,"bank site","INFO",c.Carved.Count+" river cells at terrain height "+(_ground-1)+" with "+RiverDepth+" water; bank and entrance row at "+_ground);
    }
    // Native build-tool path (AreaPicker -> BlockObjectPreviewPicker.CenteredPreviewCoordinates): the
    // pivot is rotated, never flipped, so the cursor cell is the pivot's cell of the unflipped placement
    // (the door cell, or its mirror on the bank row when flipped). A ray straight down onto it, as
    // AllBuildingsSites.CursorPreview, with player Paths along the bank and a SolarPanel beside it.
    private void CursorPick(Case c) {
      const string Check="cursor on the pivot cell picks the bank level";
      var blocks=Blocks.From(c.Spec);int w=c.Spec.Size.x;var pivot=c.Placeable.CustomPivot.Coordinates;
      var local=new Vector3Int(Mathf.FloorToInt(pivot.x),Mathf.FloorToInt(pivot.y),c.Spec.BaseZ);
      var cell=blocks.Transform(local,new Placement(c.Placement.Coordinates,c.Orientation,FlipMode.Unflipped));
      var fixtures=new List<BlockObject>();var placed=new List<string>();
      for(int x=-1;x<=w;x++) {
        var p=blocks.Transform(new Vector3Int(x,-1,c.Spec.BaseZ),c.Placement);
        if(Free(_path,p)){fixtures.Add(Create(null,_path,At(p)));placed.Add("Path "+Xyz(p));}
      }
      if(_solar!=null)foreach(var x in new[]{-1,w}) {
        var p=blocks.Transform(new Vector3Int(x,0,c.Spec.BaseZ),c.Placement);
        if(_validator.BlocksValid(_solar,At(p))){fixtures.Add(Create(null,_solar,At(p)));placed.Add("SolarPanel "+Xyz(p));}
      }
      var ray=new Ray(new Vector3(cell.x+.5f,cell.y+.5f,cell.z+20f),new Vector3(0f,0f,-1f));
      var picked=_picker.CenteredPreviewCoordinates(c.Placeable,c.Orientation,ray);
      string near="fixtures ["+string.Join(", ",placed)+"]"+(_solar==null?" (no SolarPanel.IronTeeth template loaded)":"");
      if(!picked.HasValue)Record(c,Check,false,"no top face under the cursor at "+Xyz(cell)+"; "+near);
      else Record(c,Check,picked.Value.Coordinates==c.Placement.Coordinates,"cursor at "+Xyz(cell)+" (terrain height "+_terrain.GetTerrainHeight(cell)+
        ") picked "+Xyz(picked.Value.Coordinates)+", bank placement "+Xyz(c.Placement.Coordinates)+"; "+near);
      foreach(var f in fixtures)Delete(f);
    }
    private void PreviewCheck(Case c) {
      var preview=_previews.Create(c.Placeable);
      try {
        var block=preview.BlockObject;block.Reposition(c.Placement);
        bool blocks=_validator.BlocksValid(block.PositionedBlocks);
        bool validators=_validation.AreValid(new BaseComponent[]{block},out var message);
        Record(c,"native preview valid",blocks&&validators,"blocks "+(blocks?"valid":"invalid")+", validators "+(validators?"valid":"rejected: "+message));
      } finally {UnityEngine.Object.Destroy(preview.GameObject);}
    }
    private void EntrancePath(Case c) {
      var e=c.Building.PositionedEntrance;
      if(_blocks.GetObjectsAt(e.Coordinates).Contains(c.Building)){Record(c,"entrance takes a plain player Path",false,"entrance "+Xyz(e.Coordinates)+" is the building's own block");return;}
      if(!Free(_path,e.Coordinates)){Record(c,"entrance takes a plain player Path",false,"native Path rejected at entrance "+Xyz(e.Coordinates));return;}
      Create(c,_path,At(e.Coordinates));
      Record(c,"entrance takes a plain player Path",true,"Path on the entrance "+Xyz(e.Coordinates)+", doorstep "+Xyz(e.DoorstepCoordinates)+", direction "+e.Direction2D);
      // The road keeps every transput's target cell free for the power sweep.
      var targets=new HashSet<Vector3Int>(c.Building.GetComponent<MechanicalNode>().Transputs.Select(t=>t.Target));
      var route=Route(e.Coordinates,targets);
      if(route==null){Record(c,"road to the district centre",false,"no native Path route from "+Xyz(e.Coordinates));return;}
      foreach(var p in route)if(!IsRoad(p))Create(c,_path,At(p));
      Add(c,"road to the district centre","INFO",route.Count+" cells");
    }
    private List<Vector3Int> Route(Vector3Int from,HashSet<Vector3Int> avoid) {
      var parent=new Dictionary<Vector3Int,Vector3Int>{[from]=from};
      var queue=new Queue<Vector3Int>();queue.Enqueue(from);
      while(queue.Count>0) {
        var c=queue.Dequeue();
        if(c==_dcEntrance) {
          var route=new List<Vector3Int>();
          for(var p=c;p!=from;p=parent[p])route.Add(p);
          return route;
        }
        foreach(var d in new[]{Vector3Int.left,Vector3Int.right,Vector3Int.up,Vector3Int.down}) {
          var n=c+d;
          if(parent.ContainsKey(n)||avoid.Contains(n)||!_routeArea.Contains(new Vector2Int(n.x,n.y)))continue;
          if(!(IsRoad(n)||Free(_path,n)))continue;
          parent[n]=c;queue.Enqueue(n);
        }
      }
      return null;
    }

    // ---------- entrance ----------
    private void EntranceChecks(Case c) {
      if(!c.Building)return;
      var b=c.Building;var e=b.PositionedEntrance;
      var toDoorstep=new[]{Direction2D.Down,Direction2D.Left,Direction2D.Up,Direction2D.Right}
        .Single(d=>d.ToOffset()==new Vector3Int(e.DoorstepCoordinates.x-e.Coordinates.x,e.DoorstepCoordinates.y-e.Coordinates.y,0));
      bool drawn=_connections.CanConnectInDirection(e.Coordinates,toDoorstep);
      Record(c,"entrance Path connects toward the door",drawn,"native IConnectionService.CanConnectInDirection("+Xyz(e.Coordinates)+", "+toDoorstep+
        ") (DynamicPathModel draws this side); path model "+PathModelName(e.Coordinates));
      var district=b.GetComponent<DistrictBuilding>();
      Record(c,"district connection",district&&district.InstantDistrict==_district,"instant district "+(district&&district.InstantDistrict?district.InstantDistrict.Name:"none")+
        "; road to the district centre entrance "+_nav.AreConnectedRoadInstant(e.Coordinates,_dcEntrance));
      var statuses=VisibleStatuses(b);
      Record(c,"no Unconnected status",!statuses.Any(s=>s.StartsWith(_unconnected,StringComparison.Ordinal)),"visible ["+string.Join("; ",statuses)+"]");
      var blockable=b.GetComponent<BlockableEntranceBuilding>();
      bool blocked=blockable.IsEntranceBlocked(),inaccessible=blockable.IsEntranceInaccessible();
      Record(c,"entrance not blocked",!blocked&&!inaccessible,"blocked="+blocked+" inaccessible="+inaccessible);
      var access=b.GetComponent<BuildingAccessible>().Accessible.UnblockedSingleAccess;
      var centre=CoordinateSystem.GridToWorldCentered(e.Coordinates);
      Record(c,"access on the entrance",access.HasValue&&Vector3.Distance(access.Value,centre)<.01f,"access "+(access.HasValue?access.Value.ToString("0.00"):"none")+
        ", entrance centre "+centre.ToString("0.00"));
      var node=b.GetComponent<MechanicalNode>();
      c.Transputs=node.Transputs.Where(t=>t.Direction!=Direction3D.Bottom).ToList();
      Add(c,"transputs","INFO",node.Transputs.Length+" transputs, "+c.Transputs.Count+" horizontal or Top; connector target "+(ConnectorsOf(b)!=null));
    }
    private string PathModelName(Vector3Int cell) {
      var path=_blocks.GetObjectsAt(cell).FirstOrDefault(o=>o.GetComponent<TemplateSpec>()?.TemplateName=="Path");
      if(!path)return "no path";
      var model=path.AllComponents.FirstOrDefault(x=>x.GetType().FullName=="Timberborn.PathSystem.DynamicPathModel");
      var field=model?.GetType().GetField("_currentModel",BindingFlags.Instance|BindingFlags.NonPublic);
      var orientation=model?.GetType().GetField("_currentModelOrientation",BindingFlags.Instance|BindingFlags.NonPublic);
      if(field==null||orientation==null)return "DynamicPathModel not readable";
      var go=field.GetValue(model) as GameObject;
      return (go?go.name:"none")+" "+orientation.GetValue(model);
    }

    // ---------- power ----------
    private static object ConnectorsOf(BlockObject b)=>b.AllComponents.FirstOrDefault(x=>x.GetType().FullName=="Timberborn.MechanicalConnectorSystem.MechanicalConnectors");
    internal static bool ConnectorShown(BlockObject b,Transput t,out string detail) {
      var connectors=ConnectorsOf(b);
      if(connectors==null){detail="no native MechanicalConnectors (blueprint lacks MechanicalConnectorTargetSpec)";return false;}
      var field=connectors.GetType().GetField("_connectors",BindingFlags.Instance|BindingFlags.NonPublic);
      Require(field!=null,"MechanicalConnectors._connectors not found; recheck the 1.1.2.8 contract");
      var map=(IDictionary)field.GetValue(connectors);
      if(!map.Contains(t)){detail="no connector for this transput";return false;}
      bool shown=((GameObject)map[t]).activeSelf;
      detail="connector "+(shown?"shown":"hidden");
      return shown;
    }
    private List<BlockObject> _faceObjects=new();
    private void FaceStep(Case c) {
      if(!c.Building||c.Transputs==null||c.Face>=c.Transputs.Count){SummarisePower(c);StartWalk(c);return;}
      var t=c.Transputs[c.Face];
      var target=t.Target;
      var face=new JObject{["cell"]=Xyz(t.Coordinates),["direction"]=t.Direction.ToString(),["target"]=Xyz(target)};
      c.Faces.Add(face);
      _faceObjects=new List<BlockObject>();
      try {
        var supports=new List<Vector3Int>();
        for(int z=target.z-1;;z--) {
          var below=new Vector3Int(target.x,target.y,z);
          if(_terrain.Underground(below)||_stackable.IsStackableBlockAt(below))break;
          supports.Add(below);
          if(supports.Count>6)throw new InvalidOperationException("more than 6 platforms under "+Xyz(target));
        }
        supports.Reverse();
        foreach(var s in supports) {
          if(!Free(_platform,s))throw new InvalidOperationException("native Platform rejected at "+Xyz(s)+" (support under "+Xyz(target)+")");
          _faceObjects.Add(Create(null,_platform,At(s)));
        }
        face["platforms"]=supports.Count;
        var preview=_previews.Create(_shaft.Blueprint.GetSpec<PlaceableBlockObjectSpec>());
        bool valid;string message;
        try {
          preview.BlockObject.Reposition(At(target));
          valid=_validator.BlocksValid(preview.BlockObject.PositionedBlocks)&_validation.AreValid(new BaseComponent[]{preview.BlockObject},out message);
        } finally {UnityEngine.Object.Destroy(preview.GameObject);}
        face["preview"]=valid;
        if(!valid)throw new InvalidOperationException("native PowerShaft preview invalid at "+Xyz(target)+(message!=null?": "+message:""));
        var shaft=Create(null,_shaft,At(target));_faceObjects.Add(shaft);
        var shaftNode=shaft.GetComponent<MechanicalNode>();
        bool linked=t.Connected&&t.ConnectedNode==shaftNode,graph=shaftNode.Graph==c.Building.GetComponent<MechanicalNode>().Graph;
        bool socket=ConnectorShown(c.Building,t,out var socketDetail);
        face["linked"]=linked;face["sameGraph"]=graph;face["socket"]=socket;face["socketDetail"]=socketDetail;
        face["ok"]=linked&&graph&&socket;
      } catch(InvalidOperationException error) when(!error.Message.Contains("contract")) {
        face["ok"]=false;face["error"]=error.Message;
      }
      _step="faceCleanup";
    }
    private void FaceCleanup(Case c) {
      foreach(var b in _faceObjects)Delete(b);
      _faceObjects.Clear();
      c.Face++;_step="face";_wait=1;
    }
    private void SummarisePower(Case c) {
      if(!c.Building||c.Transputs==null)return;
      var bad=c.Faces.Where(f=>!(bool)f["ok"]).ToList();
      string Describe(JToken f)=>f["cell"]+" "+f["direction"]+" -> "+f["target"]+": "+(f["error"]??("linked="+f["linked"]+" graph="+f["sameGraph"]+" "+f["socketDetail"]));
      Record(c,"every face takes a native PowerShaft, joins the graph and shows its socket",bad.Count==0&&c.Faces.Count>0,
        (c.Faces.Count-bad.Count)+"/"+c.Faces.Count+" faces ("+c.Faces.Count(f=>(int?)f["platforms"]>0)+" on platforms)"+
        (bad.Count>0?"; failing: "+string.Join("; ",bad.Take(12).Select(Describe))+(bad.Count>12?"; ...":""):""));
    }

    // ---------- beaver ----------
    private void StartWalk(Case c) {
      _step="walk";
      var workplace=c.Building?c.Building.GetComponent<Workplace>():null;
      if(!workplace||!c.Building.GetComponent<DistrictBuilding>().InstantDistrict){Add(c,"a beaver reached the building","SKIP",workplace?"no district":"no workplace");_step="cleanup";return;}
      RefreshBeavers();
      // The native district may already have staffed the workplace (b177 run 1: "this workplace isn't
      // understaffed"); then the first native assignee is the beaver followed.
      var worker=workplace.AssignedWorkers.FirstOrDefault();
      if(!worker) {
        worker=_workers.FirstOrDefault(w=>w&&!w.Workplace&&!w.GetComponent<SpecialistTrait>().IsSpecialist)??_workers.FirstOrDefault(w=>w&&!w.Workplace)??_workers.First(w=>w);
        var discipline=c.Building.GetComponent<FrontierSpecialistWorkplaceSpec>()?.Discipline;
        if(discipline!=null&&worker.GetComponent<SpecialistTrait>().Discipline!=discipline) {
          var trained=_workers.FirstOrDefault(w=>w&&w.GetComponent<SpecialistTrait>().Discipline==discipline);
          if(trained)worker=trained;else worker.GetComponent<SpecialistTrait>().Graduate(discipline);
        }
        while(workplace.DesiredWorkers<1)workplace.IncreaseDesiredWorkers();
        worker.Unemploy();
        if(workplace.AssignedWorkers.Any())worker=workplace.AssignedWorkers.First();else worker.EmployAt(workplace);
      }
      c.Worker=worker;c.WalkStart=_clock.PartialDayNumber;
      _speed.ChangeSpeed(3);
      var blockable=c.Building.GetComponent<BlockableObject>();
      Add(c,"worker employed","INFO",worker.Name+" assigned="+workplace.AssignedWorkers.Contains(worker)+" building unblocked="+(!blockable||blockable.IsUnblocked));
    }
    private void WalkStep(Case c) {
      var b=c.Building;var w=c.Worker;
      var enterable=b.GetComponent<Enterable>();
      var access=b.GetComponent<BuildingAccessible>().Accessible.UnblockedSingleAccess;
      if(access.HasValue)c.Closest=Math.Min(c.Closest,Vector3.Distance(w.Transform.position,access.Value));
      bool inside=enterable&&w.GetComponent<Enterer>().CurrentBuilding==enterable;
      float hours=(_clock.PartialDayNumber-c.WalkStart)*24f;
      var workplace=b.GetComponent<Workplace>();
      if(w.Workplace!=workplace&&hours>.1f) {
        RefreshBeavers();
        if(workplace.AssignedWorkers.Any()){w=c.Worker=workplace.AssignedWorkers.First();}
        else{w.Unemploy();w.EmployAt(workplace);}
      }
      if(inside||c.Closest<=1.5f||hours>WalkHours) {
        Record(c,"a beaver reached the building",inside||c.Closest<=1.5f,(inside?"worker inside the building":"worker never inside")+"; closest to the access "+
          (c.Closest<float.MaxValue?c.Closest.ToString("0.0"):"-")+" after "+hours.ToString("0.0")+" h");
        foreach(var assigned in b.GetComponent<Workplace>().AssignedWorkers.ToList())assigned.Unemploy();
        _speed.ChangeSpeed(1);
        _step="cleanup";
      }
    }

    // ---------- cleanup and results ----------
    private void Cleanup(Case c) {
      foreach(var b in c.Objects.AsEnumerable().Reverse())Delete(b);
      c.Objects.Clear();
      foreach(var v in c.Carved) {
        float depth=_water.WaterDepth(v);
        if(depth>0f)_waterService.RemoveCleanWater(v,depth);
        _terrain.SetTerrain(v,1);
      }
      c.Carved.Clear();
      Write(false);
      _step="next";_wait=30;
    }
    private void Finish() {
      _finished=true;_speed.ChangeSpeed(0);
      Write(true);
      int fails=_cases.Sum(c=>c.Checks.Count(k=>(string)k["status"]=="FAIL"));
      Debug.Log(Tag+" COMPLETE label="+_label+" cases="+_cases.Count+" failed checks="+fails);
    }
    private void Write(bool complete) {
      var result=new JObject{["label"]=_label,["complete"]=complete,["slot"]=_slot.ToString(),["ground"]=_ground,["harness"]=new JArray(_harness),
        ["cases"]=new JArray(_cases.Where(c=>c.Checks.Count>0).Select(c=>new JObject{["case"]=c.Id,["template"]=c.Template,["orientation"]=c.Orientation.ToString(),
          ["flipped"]=c.Flip.IsFlipped,["coordinates"]=Xyz(c.Placement.Coordinates),
          ["verdict"]=c.Checks.Any(k=>(string)k["status"]=="FAIL")?"FAIL":"PASS",["checks"]=c.Checks,["faces"]=c.Faces}))};
      Directory.CreateDirectory(Outputs);
      File.WriteAllText(Path.Combine(Outputs,"flip-probe-"+_label+".json"),result.ToString(Formatting.Indented));
    }
  }
}
#endif
