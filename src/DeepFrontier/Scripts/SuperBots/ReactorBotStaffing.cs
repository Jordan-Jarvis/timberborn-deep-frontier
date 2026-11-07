using System;
using System.Collections.Generic;
using System.Linq;
using Timberborn.BaseComponentSystem;
using Timberborn.Characters;
using Timberborn.EntitySystem;
using Timberborn.GameDistricts;
using Timberborn.TickSystem;
using Timberborn.WorkSystem;

namespace DeepFrontier.Scripts.SuperBots {
  // Decorated on every bot (BotSpec), beside ReactorBot: the bot's native
  // worker parts, registered for ReactorBotStaffing.
  internal sealed class ReactorBotWorker : BaseComponent, IAwakableComponent, IInitializableEntity, IDeletableEntity {
    private readonly ReactorBotStaffing _staffing;

    public ReactorBot Bot { get; private set; }
    public Worker Worker { get; private set; }
    public Citizen Citizen { get; private set; }
    public WorkRefuser WorkRefuser { get; private set; }
    public Character Character { get; private set; }
    public bool IsReactor=>Bot.IsReactor;

    public ReactorBotWorker(ReactorBotStaffing staffing) {_staffing=staffing;}

    public void Awake() {
      Bot=GetComponent<ReactorBot>();
      Worker=GetComponent<Worker>();
      Citizen=GetComponent<Citizen>();
      WorkRefuser=GetComponent<WorkRefuser>();
      Character=GetComponent<Character>();
      if(!Bot||!Worker||!Citizen||!WorkRefuser||!Character)
        throw new InvalidOperationException($"{Name}: a Reactor Bot worker needs ReactorBot and the native Worker, Citizen and WorkRefuser");
    }

    public void InitializeEntity()=>_staffing.Register(this);
    public void DeleteEntity()=>_staffing.Unregister(this);

    // ReactorBot is decorated on BotSpec, so every bot has one; beavers do not.
    public static bool IsReactorBot(Worker worker) {
      var bot=worker.GetComponent<ReactorBot>();
      return bot&&bot.IsReactor;
    }
  }

  // Staffs workplaces set to Reactor Bots with Reactor Bots and keeps Reactor
  // Bots out of every other workplace (the modes are exclusive). The pattern of
  // SpecialistStaffing: the native district assigner never staffs these
  // workplaces (ReactorBotWorkplacePatches: PriorityOrderedWorkplaces postfixes)
  // and never holds Reactor Bots as unemployed (UnemployedWorkers prefix), so
  // this pass fills the native Workplace. Native desired workers, priority,
  // overstaffing release, work refusal, district checks and saves stay native.
  //
  // Each tick:
  // - a Reactor Bot employed at a workplace not set to Reactor Bots is released
  //   (a bot that has just finished its retrofit, a Bot Assembler bot the native
  //   assigner took before its state was set, or a save from before the modes
  //   were exclusive);
  // - anyone else at a Reactor Bot workplace is released;
  // - each Reactor Bot workplace, highest priority first, takes Reactor Bots of
  //   its district: unemployed ones first, then ones from a lower-priority
  //   Reactor Bot workplace (as the native assigner moves workers up).
  internal sealed class ReactorBotStaffing : ITickableSingleton {
    private readonly ReactorBotWorkplaceRegistry _workplaces;
    private readonly List<ReactorBotWorker> _bots=new();
    private readonly List<Worker> _scratch=new();

    public ReactorBotStaffing(ReactorBotWorkplaceRegistry workplaces) {_workplaces=workplaces;}

    public void Register(ReactorBotWorker bot) {
      if(!_bots.Contains(bot))_bots.Add(bot);
    }

    public void Unregister(ReactorBotWorker bot) {_bots.Remove(bot);}

    public void Tick() {
      foreach(var bot in _bots) {
        if(!bot.IsReactor)continue;
        var workplace=bot.Worker.Workplace;
        if(workplace&&!_workplaces.IsReactor(workplace))bot.Worker.Unemploy();
      }
      if(_workplaces.All.Count==0)return;
      foreach(var workplace in _workplaces.All.Where(w=>w.Workplace.Enabled).OrderByDescending(w=>w.Priority.Priority).ToList()) {
        ReleaseOthers(workplace.Workplace);
        while(workplace.Workplace.Understaffed) {
          var candidate=FindCandidate(workplace);
          if(!candidate)break;
          if(candidate.Worker.Workplace)candidate.Worker.Unemploy();
          workplace.Workplace.AssignWorker(candidate.Worker);
        }
      }
    }

    private void ReleaseOthers(Workplace workplace) {
      _scratch.Clear();
      foreach(var worker in workplace.AssignedWorkers)
        if(!ReactorBotWorker.IsReactorBot(worker))_scratch.Add(worker);
      foreach(var worker in _scratch)workplace.UnassignWorker(worker);
    }

    // 0 = unemployed, 1 = at a lower-priority Reactor Bot workplace, -1 = not available.
    private int Rank(ReactorBotWorker bot, ReactorBotWorkplace workplace) {
      if(!bot.Character.Alive||!bot.IsReactor||bot.WorkRefuser.RefusesWork)return -1;
      var district=workplace.DistrictBuilding.District;
      if(!district||!bot.Citizen.HasAssignedDistrict||bot.Citizen.AssignedDistrict!=district)return -1;
      var current=bot.Worker.Workplace;
      if(!current)return 0;
      if(current==workplace.Workplace||!_workplaces.IsReactor(current))return -1;
      var priority=current.GetComponent<WorkplacePriority>();
      return priority.Priority<workplace.Priority.Priority?1:-1;
    }

    private ReactorBotWorker FindCandidate(ReactorBotWorkplace workplace) {
      ReactorBotWorker best=null;
      var bestRank=int.MaxValue;
      foreach(var bot in _bots) {
        var rank=Rank(bot,workplace);
        if(rank>=0&&rank<bestRank) {best=bot;bestRank=rank;}
      }
      return best;
    }
  }
}
