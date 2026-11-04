#if !UNITY_EDITOR
using System;
using System.Linq;
using Bindito.Core;
using HarmonyLib;
using Timberborn.BlockSystem;
using Timberborn.Buildings;
using Timberborn.ConstructionSites;
using Timberborn.Coordinates;
using Timberborn.Effects;
using Timberborn.EntityNaming;
using Timberborn.EntitySystem;
using Timberborn.GameSaveRepositorySystem;
using Timberborn.GameSaveRuntimeSystem;
using Timberborn.Goods;
using Timberborn.InventorySystem;
using Timberborn.MechanicalSystem;
using Timberborn.NeedSystem;
using Timberborn.SimpleOutputBuildings;
using Timberborn.SingletonSystem;
using Timberborn.TemplateSystem;
using Timberborn.TimeSystem;
using Timberborn.Workshops;
using Timberborn.WorkSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  [Context("Game")]
  public sealed class OreHaulingAcceptanceConfigurator : Configurator {
    protected override void Configure() {
      var args = Environment.GetCommandLineArgs();
      if (args.Contains("-deepFrontierOreHauling") || args.Contains("-deepFrontierOreReload"))
        Bind<OreHaulingAcceptance>().AsSingleton();
    }
  }

  // Opt-in disposable settlement only. Ore is never seeded into an inventory:
  // a real scavenger must extract it and native workers must deliver it to the drill.
  // Only water/operating supplies and developer power are supplied by this fixture.
  internal sealed class OreHaulingAcceptance : IPostLoadableSingleton, IUpdatableSingleton {
    private const string Tag = "[DeepFrontier Ore Hauling] ";
    private readonly EntityRegistry _entities;
    private readonly BlockObjectFactory _factory;
    private readonly TemplateService _templates;
    private readonly BlockValidator _validator;
    private readonly IBlockService _blocks;
    private readonly SpeedManager _speed;
    private readonly WorkingHoursManager _hours;
    private readonly GameSaver _saver;
    private readonly GameLoader _loader;
    private readonly bool _reload = Environment.GetCommandLineArgs().Contains("-deepFrontierOreReload");
    private readonly MineralDeposit[] _deposits = new MineralDeposit[3];
    private static readonly string[] SourceNames = {"DeepOreSource", "SandstoneOutcrop", "LimestoneOutcrop"};
    private BlockObject _flag, _drill;
    private Manufactory _machine;
    private int _frame, _phase, _batches, _hauled, _waterUsed;
    private float _started;
    private bool _finished;

    public OreHaulingAcceptance(EntityRegistry entities, BlockObjectFactory factory, TemplateService templates,
        BlockValidator validator, IBlockService blocks, SpeedManager speed, WorkingHoursManager hours,
        GameSaver saver, GameLoader loader) {
      _entities=entities; _factory=factory; _templates=templates; _validator=validator; _blocks=blocks;
      _speed=speed; _hours=hours; _saver=saver; _loader=loader;
    }
    private static void Require(bool condition, string message) {
      if (!condition) throw new InvalidOperationException(message);
    }
    private static void Pass(string message) => Debug.Log(Tag + "PASS " + message);
    public void PostLoad() {
      Require(_entities.Entities.Any(e=>e.HasComponent<NamedEntity>() &&
        e.GetComponent<NamedEntity>().EntityName=="Deep Frontier Acceptance Fixture"), "Disposable fixture marker required");
      _speed.ChangeSpeed(0);
    }
    private BlockObject Create(string id, Vector3Int position) {
      var template=_templates.GetAll<TemplateSpec>().Single(t=>t.TemplateName==id);
      var placement=new Placement(position, Orientation.Cw0, FlipMode.Unflipped);
      Require(_validator.BlocksValid(template.Blueprint.GetSpec<BlockObjectSpec>(), placement), "Invalid placement: "+id+" "+position);
      return _factory.CreateFinished(new EntitySetup.Builder(template.Blueprint)
        .AddInitComponent(new FinishedConstructionSiteInit()), placement);
    }
    private BlockObject Find(string id, Vector3Int position) => _entities.Entities
      .Where(e=>e.HasComponent<BlockObject>() && e.GetComponent<TemplateSpec>().TemplateName==id)
      .Select(e=>e.GetComponent<BlockObject>()).Single(b=>b.Coordinates==position);

    private void Setup() {
      foreach (var e in _entities.Entities.Where(e=>e.HasComponent<Workplace>() && e.HasComponent<PausableBuilding>()))
        e.GetComponent<PausableBuilding>().Pause();
      for (int i=0;i<3;i++) {
        var position=new Vector3Int(155-i*4,167,3);
        var source=_reload?Find(SourceNames[i],position):Create(SourceNames[i],position);
        _deposits[i]=source.GetComponent<MineralDeposit>();
        if (_reload) {
          Require(_deposits[i].Amount==0 && Math.Abs(_deposits[i].RechargeProgress-.25f)<.005f,
            SourceNames[i]+": saved empty reserve/recovery clock changed");
        } else _deposits[i].SetAmount(i==0?16:0);
      }
      if (_reload) {
        Pass("all three depleted outcrops and their 25% recovery clocks survived a fresh-process load");
        foreach (var deposit in _deposits) {
          // Test-only time acceleration through the native trigger. Production
          // uses the authored five-day interval, and completion still requires a real tick.
          var trigger=(ITimeTrigger)AccessTools.Field(typeof(MineralDeposit),"_recharge").GetValue(deposit);
          trigger.FastForwardProgress(.999f-deposit.RechargeProgress);
        }
        _phase=2; _speed.ChangeSpeed(3); return;
      }
      for(int y=157;y<=159;y++) if(!_blocks.GetPathObjectAt(new Vector3Int(173,y,3))) Create("Path",new Vector3Int(173,y,3));
      for(int x=155;x<173;x++) if(!_blocks.GetPathObjectAt(new Vector3Int(x,159,3))) Create("Path",new Vector3Int(x,159,3));
      _flag=Create("ScavengerFlag.IronTeeth",new Vector3Int(155,160,3));
      _drill=Create("DeepDrill.IronTeeth",new Vector3Int(160,160,3));
      Create("PowerShaft.IronTeeth",new Vector3Int(159,160,3));
      var generator=Create("DevPowerGenerator",new Vector3Int(158,160,3));
      var node=generator.GetComponent<MechanicalNode>();
      node.SetOutputMultiplier((float)Math.Ceiling(_drill.GetComponent<MechanicalNodeSpec>().PowerInput /
        (double)generator.GetComponent<MechanicalNodeSpec>().PowerOutput));
      _machine=_drill.GetComponent<Manufactory>();
      Require(_machine.Inventory.AmountInStock("RawDeepOre")==0 && _machine.Inventory.AmountInStock("DeepOre")==0,
        "Fresh drill must have no ore");
      foreach(var good in new[]{new GoodAmount("Water",60),new GoodAmount("MetalBlock",2),new GoodAmount("TreatedPlank",2)})
        _machine.Inventory.GiveExisting(good);
      _machine.ProductionFinished+=(_,_)=>_batches++;
      _machine.Inventory.InventoryStockChanged+=(_,args)=> {
        if(args.GoodAmount.GoodId=="RawDeepOre" && args.GoodAmount.Amount>0) _hauled+=args.GoodAmount.Amount;
        if(args.GoodAmount.GoodId=="Water" && args.StockChangeType==StockChangeType.Consumed) _waterUsed-=args.GoodAmount.Amount;
      };
      foreach(var inv in _entities.Entities.Where(e=>e.HasComponent<Inventories>())
          .SelectMany(e=>e.GetComponent<Inventories>().AllInventories)
          .Where(v=>v!=_machine.Inventory && v!=_flag.GetComponent<SimpleOutputInventory>().Inventory && v.Enabled && v.PublicOutput
            &&(v.OutputGoods.Contains("RawDeepOre") || v.OutputGoods.Contains("DeepOre")))) inv.Disable();
      _hours.WorkedPartOfDay=1;
      Pass("native flag, visible ore, connected drill, and real input inventory placed; no ore seeded");
    }
    private void StartWorkers() {
      Require(_drill.GetComponent<MechanicalNode>().Graph.PowerSupply>=1000,"Drill has no power");
      var workers=_entities.Entities.Where(e=>e.HasComponent<Worker>()).Select(e=>e.GetComponent<Worker>())
        .Where(w=>w.WorkerType=="Beaver").Take(4).ToArray();
      Require(workers.Length==4,"Four fixture workers required");
      _flag.GetComponent<PausableBuilding>().Resume(); _drill.GetComponent<PausableBuilding>().Resume();
      for(int i=0;i<workers.Length;i++) {
        var needs=workers[i].GetComponent<NeedManager>();
        foreach(var id in new[]{"Hunger","Thirst","Sleep"})
          needs.ApplyEffect(new InstantEffect(id,needs.GetNeedSpec(id).MaximumValue-needs.GetNeedPoints(id),1));
        workers[i].Unemploy(); workers[i].EmployAt((i==0?_flag:_drill).GetComponent<Workplace>());
      }
      _speed.ChangeSpeed(3); _phase=1;
    }
    private void SaveRecoveryCheckpoint() {
      _flag.GetComponent<PausableBuilding>().Pause(); _drill.GetComponent<PausableBuilding>().Pause();
      foreach(var deposit in _deposits) {
        deposit.SetAmount(0);
        var trigger=(ITimeTrigger)AccessTools.Field(typeof(MineralDeposit),"_recharge").GetValue(deposit);
        trigger.FastForwardProgress(.25f);
      }
      _speed.ChangeSpeed(0); _finished=true;
      _saver.QueueSave(new SaveReference("Ore hauling - verified",_loader.LoadedSave.SettlementReference),
        ()=>Pass("RECOVERY CHECKPOINT SAVED through native GameSaver"));
    }
    public void UpdateSingleton() {
      if(_finished)return;
      try {
        if(++_frame==60){_started=Time.realtimeSinceStartup;Setup();}
        if(_frame==240 && !_reload)StartWorkers();
        if(_phase==1 && _batches>0) {
          Require(_hauled>0 && _deposits[0].Amount<16,"Production did not use scavenged, hauled ore");
          Require(_waterUsed>=3,"Drill did not consume recipe water");
          var upkeep=_drill.GetComponent<WorkplaceUpkeep>();
          Require(upkeep.Spec.Goods.Select(g=>g.GoodId).SequenceEqual(new[]{"MetalBlock","TreatedPlank"}),"Wrong operating supplies");
          Require(Enumerable.Range(0,2).All(i=>upkeep.Remaining(i)>0),"Both operating supplies must have been used");
          Pass("scavenger extracted raw ore, native hauling delivered "+_hauled+", drill produced "+_batches+
            " batch(es), consumed water and used metal blocks/treated planks");
          SaveRecoveryCheckpoint();
        }
        if(_phase==2 && _deposits.All(d=>d.Amount==20)) {
          Require(_deposits.All(d=>!d.IsRecharging),"Nonempty source still recovering");
          _speed.ChangeSpeed(0);_finished=true;
          Pass("ALL RECOVERY CHECKS PASSED: each native trigger restored exactly 20; no source deleted");
        }
        if(_frame%1800==0 && _phase==1) Debug.Log(Tag+"STATUS raw="+_deposits[0].Amount+" hauled="+_hauled+" batches="+_batches);
        if(_frame>=60)Require(Time.realtimeSinceStartup-_started<600,"Timed out waiting for native extraction/hauling/recovery");
      } catch(Exception e){_finished=true;_speed.ChangeSpeed(0);Debug.LogError(Tag+"FAILED "+e);}
    }
  }
}
#endif
