using System;
using System.Collections.Generic;
using System.Linq;
using Timberborn.EntitySystem;
using Timberborn.Persistence;
using Timberborn.SingletonSystem;
using Timberborn.WorldPersistence;

namespace DeepFrontier.Scripts {
  // Colony-wide launch record: completed missions, launch attempts (flight
  // heritage) and the story ending. Saved with the settlement.
  internal sealed class RocketProgramService : ISaveableSingleton, ILoadableSingleton {
    private static readonly SingletonKey Key=new("DeepFrontier.RocketProgram");
    private static readonly ListKey<string> CompletedKey=new("CompletedMissions");
    private static readonly PropertyKey<int> AttemptsKey=new("LaunchAttempts");
    private static readonly PropertyKey<int> FailuresKey=new("FailedLaunches");
    private static readonly PropertyKey<string> LastMissionKey=new("LastMission");
    private static readonly PropertyKey<bool> LastSucceededKey=new("LastSucceeded");
    private static readonly PropertyKey<float> LastFailureChanceKey=new("LastFailureChance");
    private static readonly PropertyKey<bool> StoryKey=new("StoryCompleted");
    private readonly ISingletonLoader _loader;
    private readonly EntityComponentRegistry _registry;
    private readonly List<string> _completed=new();

    public IReadOnlyList<string> CompletedMissions=>_completed;
    public int LaunchAttempts { get; private set; }
    public int FailedLaunches { get; private set; }
    public string LastMission { get; private set; }="";
    public bool LastSucceeded { get; private set; }
    public float LastFailureChance { get; private set; }
    public bool StoryCompleted { get; private set; }

    public RocketProgramService(ISingletonLoader loader,EntityComponentRegistry registry) {
      _loader=loader;_registry=registry;
    }

    public void Load() {
      if(!_loader.TryGetSingleton(Key,out var data))return;
      var completed=data.Get(CompletedKey);
      if(completed.Distinct().Count()!=completed.Count||completed.Any(string.IsNullOrEmpty))
        throw new InvalidOperationException("Saved rocket program has duplicate or empty mission records");
      _completed.AddRange(completed);
      LaunchAttempts=data.Get(AttemptsKey);FailedLaunches=data.Get(FailuresKey);
      LastMission=data.Get(LastMissionKey);LastSucceeded=data.Get(LastSucceededKey);
      LastFailureChance=data.Get(LastFailureChanceKey);StoryCompleted=data.Get(StoryKey);
      if(LaunchAttempts<_completed.Count+FailedLaunches||FailedLaunches<0)
        throw new InvalidOperationException("Saved rocket program launch counts are inconsistent");
    }

    public void Save(ISingletonSaver saver) {
      var data=saver.GetSingleton(Key);
      data.Set(CompletedKey,_completed);data.Set(AttemptsKey,LaunchAttempts);data.Set(FailuresKey,FailedLaunches);
      data.Set(LastMissionKey,LastMission);data.Set(LastSucceededKey,LastSucceeded);
      data.Set(LastFailureChanceKey,LastFailureChance);data.Set(StoryKey,StoryCompleted);
    }

    public bool IsCompleted(string missionId)=>_completed.Contains(missionId);

    public bool IsInFlight(string missionId,RocketLaunchPad except)=>
      _registry.GetEnabled<RocketLaunchPad>().Any(p=>p!=except&&p.InFlight&&p.FlightMission.Id==missionId);

    public int OperatingMissionControls=>_registry.GetEnabled<RocketMissionControl>().Count(m=>m.IsOperating);

    public void RecordLaunch(RocketMissionSpec mission,bool succeeded,float failureChance) {
      if(succeeded&&IsCompleted(mission.Id))
        throw new InvalidOperationException($"Mission {mission.Id} was already completed");
      LaunchAttempts++;
      if(succeeded)_completed.Add(mission.Id);else FailedLaunches++;
      LastMission=mission.Id;LastSucceeded=succeeded;LastFailureChance=failureChance;
      if(succeeded&&mission.CompletesStory)StoryCompleted=true;
    }
  }
}
