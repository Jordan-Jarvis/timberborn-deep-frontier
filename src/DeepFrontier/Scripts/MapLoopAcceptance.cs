#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using Bindito.Core;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockObjectTools;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.ConstructionSites;
using Timberborn.Coordinates;
using Timberborn.CoreUI;
using Timberborn.EntitySystem;
using Timberborn.NaturalResources;
using Timberborn.SingletonSystem;
using Timberborn.Stockpiles;
using Timberborn.TemplateSystem;
using Timberborn.TerrainSystem;
using Timberborn.TimeSystem;
using Timberborn.WaterSystem;
using Timberborn.Yielding;
using UnityEngine;
using DeepFrontier.Scripts.Narrative;

namespace DeepFrontier.Scripts {
  // Explicit disposable test only: -deepFrontierLoadAcceptance -deepFrontierNewGame "user:Deep Frontier - <map>"
  // -deepFrontierMapLoop [-deepFrontierMapLoopLabel <label>] (tools/start_map_loop_test.ps1). Never saves.
  [Context("Game")]
  public sealed class MapLoopAcceptanceConfigurator : Configurator {
    protected override void Configure() {
      var args=Environment.GetCommandLineArgs();
      if(!args.Contains(MapLoopAcceptance.Flag))return;
      if(!args.Contains("-deepFrontierLoadAcceptance")||MemoryLoadProbe.NewGameMap()==null)
        throw new InvalidOperationException(MapLoopAcceptance.Flag+" requires -deepFrontierLoadAcceptance with -deepFrontierNewGame");
      Bind<MapLoopAcceptance>().AsSingleton();
    }
  }

  // Full-loop map proof on a new game of one Deep Frontier map variant. The contract is the static
  // validation evidence of tools/prepare_deep_frontier_map.py (outputs/maps/<id>-validation.json) whose
  // output file is the loaded map; the map file's SHA-256 must equal the evidence's outputSha256.
  //   1. Every placement survived loading (native BlockObject validation deletes invalid objects): the
  //      template is registered at its coordinates and orientation; Deep Ore Sources hold their DeepOre;
  //      outcrops yield their stone; Human Record Caches load without survey state.
  //   2. Every site: trees in the footprint are removed (as the player cuts them); cells the site lists
  //      under "dynamite" are lowered with ITerrainService.UnsetTerrain (as vanilla Dynamite does); the
  //      water settles; then a native preview (PreviewFactory, as the build tool) at the native placement
  //      must pass the native block rules and every IBlockObjectValidator (understructure, map edge,
  //      adaptive supports). Water-depth work cells and water intakes are read from the water map.
  //      Dam sites must hold water.
  //   3. Every pit is built finished; its native InRangeYielders must list the deposits the static check
  //      found in range.
  // Results: outputs/map-loop-<label>-<variant>.json and "[DeepFrontier MapLoop]" log lines.
  internal sealed class MapLoopAcceptance : IPostLoadableSingleton,IUpdatableSingleton {
    internal const string Flag="-deepFrontierMapLoop";
    private const string LabelFlag="-deepFrontierMapLoopLabel";
    private const string Tag="[DeepFrontier MapLoop]";
    private static readonly string Root=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),"TimberbornModding");
    private static readonly string Outputs=Path.Combine(Root,"outputs");
    private static readonly string Maps=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),"Timberborn","Maps");
    private const int SettleFrames=600,PitFrames=240;

    private sealed class Check {public string Subject,Name,Status,Detail;}

    private readonly EntityRegistry _entities;
    private readonly EntityService _entityService;
    private readonly TemplateService _templates;
    private readonly BlockObjectFactory _factory;
    private readonly BlockValidator _validator;
    private readonly BlockObjectValidationService _validation;
    private readonly IBlockService _blocks;
    private readonly ITerrainService _terrain;
    private readonly IThreadSafeWaterMap _water;
    private readonly SpeedManager _speed;
    private readonly PanelStack _panels;
    private readonly PreviewFactory _previews;
    private readonly string _label;
    private readonly List<Check> _checks=new();
    private readonly List<string> _harness=new();
    private readonly List<(JObject Site,BlockObject Pit)> _pits=new();
    private JObject _contract;
    private string _variant;
    private int _frame,_phase,_phaseFrame;
    private bool _finished;
    private IPanelController _lastPanel;
    private int _panelFrames;
    private DateTime _startedAt;

    public MapLoopAcceptance(EntityRegistry entities,EntityService entityService,TemplateService templates,BlockObjectFactory factory,
        BlockValidator validator,BlockObjectValidationService validation,IBlockService blocks,ITerrainService terrain,
        IThreadSafeWaterMap water,SpeedManager speed,PanelStack panels,PreviewFactory previews) {
      _entities=entities;_entityService=entityService;_templates=templates;_factory=factory;_validator=validator;
      _validation=validation;_blocks=blocks;_terrain=terrain;_water=water;_speed=speed;_panels=panels;_previews=previews;
      var args=Environment.GetCommandLineArgs();
      int i=Array.IndexOf(args,LabelFlag);
      _label=i>=0&&i+1<args.Length?args[i+1].Trim('"'):"run";
      if(_label.IndexOfAny(Path.GetInvalidFileNameChars())>=0)throw new InvalidOperationException(LabelFlag+" is not a valid file name part: "+_label);
    }

    // ---------- recording ----------
    private static void Require(bool value,string message) {if(!value)throw new InvalidOperationException(message);}
    private void Record(string subject,string check,bool ok,string detail)=>Add(subject,check,ok?"PASS":"FAIL",detail);
    private void Add(string subject,string check,string status,string detail) {
      _checks.Add(new Check{Subject=subject,Name=check,Status=status,Detail=detail});
      var line=Tag+" "+status+" "+subject+" | "+check+": "+detail;
      if(status=="FAIL")Debug.LogWarning(line);else Debug.Log(line);
    }

    // ---------- helpers ----------
    private static Vector3Int Xyz(JToken a)=>new((int)a[0],(int)a[1],(int)a[2]);
    private static Orientation Rotation(JToken o)=>o==null||o.Type==JTokenType.Null?Orientation.Cw0:(Orientation)Enum.Parse(typeof(Orientation),(string)o);
    private static Placement At(Vector3Int c,Orientation o)=>new(c,o,new FlipMode(false));
    private Blueprint Blueprint(string template) {
      var t=_templates.GetAll<TemplateSpec>().SingleOrDefault(x=>x.TemplateName==template);
      Require(t!=null,"Template not loaded: "+template);
      return t.Blueprint;
    }
    private static string Sha256(string path) {
      using var sha=SHA256.Create();
      using var stream=File.OpenRead(path);
      return string.Concat(sha.ComputeHash(stream).Select(b=>b.ToString("x2")));
    }
    private IEnumerable<BlockObject> ObjectsAt(Vector3Int c)=>_blocks.GetObjectsAt(c);
    private static string TemplateOf(BaseComponent c)=>c.GetComponent<TemplateSpec>()?.TemplateName;

    // ---------- lifecycle ----------
    public void PostLoad() {_speed.ChangeSpeed(0);_startedAt=DateTime.Now;}

    public void UpdateSingleton() {
      if(_finished)return;
      try {
        // Startup panels are dismissed before frame 60 (AcceptanceStartupPanels).
        if(++_frame<90)return;
        DismissPanels();
        if(_frame==90){LoadContract();CheckPlacements();PrepareSites();_speed.ChangeSpeed(3);Phase(1);return;}
        if(_phase==1&&_frame-_phaseFrame>=SettleFrames){_speed.ChangeSpeed(0);CheckSites();BuildPits();_speed.ChangeSpeed(1);Phase(2);return;}
        if(_phase==2&&_frame-_phaseFrame>=PitFrames){_speed.ChangeSpeed(0);CheckPits();Finish();}
      } catch(Exception error) {
        _finished=true;_speed.ChangeSpeed(0);
        _harness.Add("harness error: "+error);
        WriteResults(false);
        Debug.LogError(Tag+" FAILED: "+error);
      }
    }
    private void Phase(int phase) {_phase=phase;_phaseFrame=_frame;Debug.Log(Tag+" Phase "+phase);}

    private void DismissPanels() {
      var stacked=AcceptancePanels.Stacked(_panels);
      if(stacked.Count==0){_lastPanel=null;_panelFrames=0;return;}
      var top=stacked[0];
      if(ReferenceEquals(top,_lastPanel)) {
        if(++_panelFrames>120)throw new InvalidOperationException("Panel did not close on Escape: "+AcceptancePanels.Describe(top));
        return;
      }
      _lastPanel=top;_panelFrames=0;
      var description=AcceptancePanels.Describe(top);
      top.OnUICancelled();
      _harness.Add("dismissed panel: "+description);
    }

    // ---------- 0. contract ----------
    private void LoadContract() {
      var map=MemoryLoadProbe.NewGameMap();
      Require(map.StartsWith("user:",StringComparison.Ordinal),Flag+" needs a user map, got "+map);
      var name=map.Substring(5);
      var matches=Directory.GetFiles(Path.Combine(Outputs,"maps"),"*-validation.json")
        .Select(p=>JObject.Parse(File.ReadAllText(p)))
        .Where(r=>Path.GetFileNameWithoutExtension((string)r["output"])==name).ToList();
      Require(matches.Count==1,"Expected one outputs/maps/*-validation.json for "+name+", found "+matches.Count);
      _contract=matches[0];
      _variant=(string)_contract["variant"];
      Require(((JArray)_contract["errors"]).Count==0,"The static validation of "+_variant+" has errors; rebuild the map first");
      var file=Path.Combine(Maps,name+".timber");
      var hash=Sha256(file);
      Record(_variant,"contract matches the loaded map file",hash==(string)_contract["outputSha256"],file+" sha256 "+hash+" (evidence "+_contract["outputSha256"]+")");
    }

    // ---------- 1. placements ----------
    private void CheckPlacements() {
      foreach(JObject p in _contract["placements"]) {
        string template=(string)p["template"],label=(string)p["label"];
        var at=Xyz(p["at"]);
        var o=Rotation(p["orientation"]);
        var found=ObjectsAt(at).Where(b=>TemplateOf(b)==template&&b.Coordinates==at).ToList();
        string subject=template+" "+label;
        if(found.Count!=1){Record(subject,"placement loaded",false,found.Count+" "+template+" registered at "+at);continue;}
        var block=found[0];
        Record(subject,"placement loaded",block.Orientation==o,template+" at "+at+" orientation "+block.Orientation+" (expected "+o+")");
        if(p["good"]!=null&&block.GetComponent<Stockpile>() is Stockpile stockpile) {
          int amount=stockpile.Inventory.AmountInStock((string)p["good"]);
          Record(subject,"stock",amount==(int)p["amount"],amount+" "+p["good"]+" (map "+p["amount"]+")");
        } else if(p["good"]!=null&&block.GetComponent<MineralDeposit>() is MineralDeposit deposit) {
          var y=deposit.Yielder.Yield;
          Record(subject,"yield",y.GoodId==(string)p["good"]&&y.Amount==(int)p["amount"],y.Amount+" "+y.GoodId+" (blueprint "+p["amount"]+" "+p["good"]+")");
        }
        if(block.GetComponent<HumanRecordCache>() is HumanRecordCache cache)
          Record(subject,"cache unsurveyed",!cache.Surveyed,"state "+cache.State+", surveyed "+cache.Surveyed);
      }
    }

    // ---------- 2. sites ----------
    private void PrepareSites() {
      int removed=0,blasted=0;
      foreach(JObject site in _contract["sites"]) {
        if((string)site["rule"]=="hydro")continue;
        var spec=Blueprint((string)site["template"]).GetSpec<BlockObjectSpec>();
        var placement=At(Xyz(site["nativePlacement"]),Rotation(site["orientation"]));
        var columns=new HashSet<Vector2Int>(spec.GetBlocks(placement).Select(b=>new Vector2Int(b.Coordinates.x,b.Coordinates.y)));
        foreach(var c in columns) {
          int h=_terrain.GetTerrainHeight(new Vector3Int(c.x,c.y,0));
          foreach(var b in ObjectsAt(new Vector3Int(c.x,c.y,h)).ToList()) {
            var e=b.GetComponent<EntityComponent>();
            if(e.HasComponent<NaturalResource>()){_entityService.Delete(e);removed++;}
          }
        }
        foreach(JArray cut in (JArray)site["dynamite"]??new JArray()) {
          int x=(int)cut[0],y=(int)cut[1],layers=(int)cut[2];
          int h=_terrain.GetTerrainHeight(new Vector3Int(x,y,0));
          _terrain.UnsetTerrain(new Vector3Int(x,y,h-1),layers);
          blasted++;
          _harness.Add("dynamite: ("+x+","+y+") "+h+" -> "+(h-layers)+" for "+site["label"]);
        }
      }
      _harness.Add("site preparation: "+removed+" natural resources removed from site footprints, "+blasted+" cells blasted");
      Debug.Log(Tag+" site preparation: "+removed+" natural resources removed, "+blasted+" cells blasted; water settles for "+SettleFrames+" frames");
    }

    private void CheckSites() {
      foreach(JObject site in _contract["sites"]) {
        string template=(string)site["template"],rule=(string)site["rule"];
        string subject=template+" "+site["label"];
        if(rule=="hydro") {
          var c=Xyz(site["at"]);
          float depth=_water.WaterDepth(c);
          Record(subject,"dam site holds water",depth>0,"water depth "+depth.ToString("0.00")+", contamination "+_water.ColumnContamination(c).ToString("0.00")+
            " at "+c+"; static natural head "+site["naturalHead"]+" layers");
          continue;
        }
        var blueprint=Blueprint(template);
        var placement=At(Xyz(site["nativePlacement"]),Rotation(site["orientation"]));
        var preview=_previews.Create(blueprint.GetSpec<PlaceableBlockObjectSpec>());
        try {
          var block=preview.BlockObject;
          block.Reposition(placement);
          bool blocks=_validator.BlocksValid(block.PositionedBlocks);
          bool validators=_validation.AreValid(new BaseComponent[]{block},out var message);
          Record(subject,"native preview accepts the site",blocks&&validators,"placement "+placement.Coordinates+" "+placement.Orientation+
            ": native blocks "+(blocks?"valid":"invalid")+", validators "+(validators?"valid":"rejected: "+message));
          if(blueprint.HasSpec<WaterDepthWorkCellsSpec>()) {
            var spec=blueprint.GetSpec<WaterDepthWorkCellsSpec>();
            // Depth range on every work cell; contamination only on WorkCells[0], the native
            // ContaminationBlockableBuilding sample (WaterDepthWorkCells, limit 0.05), as the static check.
            var readings=spec.WorkCells.Select(w=>block.TransformCoordinates(w)).Select(w=>(w,_water.WaterDepth(w),_water.ColumnContamination(w))).ToList();
            bool ok=readings.All(r=>r.Item2>=spec.MinDepth&&r.Item2<=spec.MaxDepth)&&readings[0].Item3<=.05f;
            Record(subject,"work cells in water, contamination sample clean",ok,string.Join("; ",readings.Select(r=>r.w+" depth "+r.Item2.ToString("0.00")+" contamination "+r.Item3.ToString("0.00")))+
              " (sample cell "+readings[0].w+")");
          }
          if(blueprint.HasSpec<Timberborn.WaterBuildings.WaterInputSpec>()) {
            var intake=block.TransformCoordinates(blueprint.GetSpec<Timberborn.WaterBuildings.WaterInputSpec>().WaterInputCoordinates);
            int floor=_terrain.GetTerrainHeight(new Vector3Int(intake.x,intake.y,0));
            float depth=_water.WaterDepth(new Vector3Int(intake.x,intake.y,floor));
            Record(subject,"intake column holds water",depth>0&&floor<=intake.z,"intake "+intake+", column floor "+floor+", water depth "+depth.ToString("0.00"));
          }
        } finally {
          UnityEngine.Object.Destroy(preview.GameObject);
        }
        if(rule=="pit")_pits.Add((site,null));
      }
    }

    // ---------- 3. pits ----------
    private void BuildPits() {
      for(int i=0;i<_pits.Count;i++) {
        var site=_pits[i].Site;
        var spec=Blueprint((string)site["template"]).GetSpec<BlockObjectSpec>();
        var placement=At(Xyz(site["nativePlacement"]),Rotation(site["orientation"]));
        string subject=site["template"]+" "+site["label"];
        if(!_validator.BlocksValid(spec,placement)){Record(subject,"pit built",false,"native placement rejected at "+placement.Coordinates);continue;}
        var b=_factory.CreateFinished(new EntitySetup.Builder(spec.Blueprint).AddInitComponent(new FinishedConstructionSiteInit()),placement);
        bool valid=_validation.IsValid(b);
        Record(subject,"pit built",valid,"finished "+site["template"]+" at "+placement.Coordinates+" "+placement.Orientation);
        _pits[i]=(site,valid?b:null);
      }
    }
    private void CheckPits() {
      foreach(var (site,pit) in _pits) {
        if(!pit)continue;
        string subject=site["template"]+" "+site["label"];
        var yielders=new List<Yielder>();
        pit.GetComponent<InRangeYielders>().GetYielders(yielders);
        var inRange=new HashSet<Vector3Int>(yielders.Select(y=>y.GetComponent<BlockObject>().Coordinates));
        var expected=((JArray)site["depositsInRange"]).Select(d=>(string)d["label"]).ToList();
        var deposits=_contract["placements"].Where(p=>expected.Contains((string)p["label"])).Select(p=>Xyz(p["at"])).ToList();
        var missing=deposits.Where(c=>!inRange.Contains(c)).ToList();
        Record(subject,"deposits in the pit's native range",deposits.Count>0&&missing.Count==0,
          yielders.Count+" yielders in range; static check expects "+deposits.Count+" ("+string.Join(", ",deposits)+")"+
          (missing.Count>0?"; missing "+string.Join(", ",missing):""));
      }
    }

    // ---------- results ----------
    private void Finish() {
      _finished=true;
      WriteResults(true);
      int fails=_checks.Count(c=>c.Status=="FAIL");
      Debug.Log(Tag+" COMPLETE "+_variant+": "+_checks.Count+" checks, "+fails+" failed; results outputs/map-loop-"+_label+"-"+_variant+".json");
    }
    private void WriteResults(bool complete) {
      Directory.CreateDirectory(Outputs);
      var result=new JObject{
        ["label"]=_label,["variant"]=_variant,["complete"]=complete,["startedAt"]=_startedAt.ToString("o"),["writtenAt"]=DateTime.Now.ToString("o"),
        ["harness"]=new JArray(_harness),
        ["failed"]=_checks.Count(c=>c.Status=="FAIL"),
        ["checks"]=new JArray(_checks.Select(c=>new JObject{["subject"]=c.Subject,["check"]=c.Name,["status"]=c.Status,["detail"]=c.Detail}))
      };
      File.WriteAllText(Path.Combine(Outputs,"map-loop-"+_label+"-"+(_variant??"unknown")+".json"),result.ToString(Formatting.Indented));
    }
  }
}
#endif
