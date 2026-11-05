#if !UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using System.Reflection;
using Bindito.Core;
using Timberborn.Attractions;
using Timberborn.BehaviorSystem;
using Timberborn.Buildings;
using Timberborn.Effects;
using Timberborn.EnterableSystem;
using Timberborn.EntitySystem;
using Timberborn.GoodConsumingBuildingSystem;
using Timberborn.Goods;
using Timberborn.NeedBehaviorSystem;
using Timberborn.NeedSpecs;
using Timberborn.SingletonSystem;
using Timberborn.TimeSystem;
using Timberborn.WalkingSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  [Context("Game")]
  public sealed class SchoolVisitAcceptanceConfigurator : Configurator {
    protected override void Configure() {
      if (Environment.GetCommandLineArgs().Contains("-deepFrontierSchoolVisitAcceptance"))
        Bind<SchoolVisitAcceptance>().AsSingleton();
    }
  }

  // Real native attraction decisions/executors on a disposable save. No saved mutations.
  internal sealed class SchoolVisitAcceptance : IPostLoadableSingleton, IUpdatableSingleton {
    private const string Tag = "[DeepFrontier SchoolVisit] ";
    private readonly EntityRegistry _entities;
    private readonly SpeedManager _speed;
    private int _frame;
    public SchoolVisitAcceptance(EntityRegistry entities, SpeedManager speed) {
      _entities=entities; _speed=speed;
    }
    private static void Require(bool value, string message) {
      if (!value) throw new InvalidOperationException(Tag+message);
    }
    public void PostLoad() {
      Require(Path.GetFileName(MemoryLoadProbe.SavePath())=="school-visit-repro-copy.timber",
        "Requires the explicitly named disposable school save");
      Require(!Environment.GetCommandLineArgs().Contains(MemoryLoadProbe.SaveAsFlag),"Test must not save mutations");
    }
    public void UpdateSingleton() {
      if (++_frame!=300) return;
      _speed.ChangeSpeed(0);
      var school=_entities.Entities.Select(e=>e.GetComponent<SpecialistSchool>()).Single(s=>s);
      school.Teach("Metallurgy");
      var pause=school.GetComponent<PausableBuilding>(); pause.Resume();
      var consumer=school.GetComponent<GoodConsumingBuilding>();
      foreach(var good in school.Supplies) {
        int missing=school.AllowedAmount(good.GoodId)-consumer.Inventory.AmountInStock(good.GoodId);
        if(missing>0)consumer.Inventory.GiveExisting(new GoodAmount(good.GoodId,missing));
      }
      var attraction=school.GetComponent<Attraction>();
      Require(attraction.IsUsable,"Fixture school must have native power, supplies and access");
      Require(attraction.Effects.Count==1&&!attraction.SatisfiesAnyNeedToMaxValue,
        "Authored study sessions must release to root needs");
      var student=_entities.Entities.Select(e=>e.GetComponent<SpecialistTrait>())
        .First(t=>t&&t.Alive&&!t.Has("Metallurgy"));
      var needs=student.NeedManager;
      foreach(var id in new[]{"Hunger","Thirst","Sleep","StudyMetallurgy"})
        needs.ApplyEffect(new InstantEffect(id,-needs.GetNeedPoints(id),1));
      var enterer=student.GetComponent<Enterer>();
      enterer.UnreserveSlotAndExit();
      student.GetComponent<Walker>().StopNextTick();
      enterer.Enter(school.GetComponent<Enterable>());
      var behavior=school.GetComponent<AttractionNeedBehavior>();
      var agent=student.GetComponent<BehaviorAgent>();
      var effects=attraction.Effects.ToList();
      var effectsProperty=typeof(Attraction).GetProperty(nameof(Attraction.Effects));
      var maxProperty=typeof(Attraction).GetProperty(nameof(Attraction.SatisfiesAnyNeedToMaxValue));
      Require(effectsProperty?.GetSetMethod(true)!=null&&maxProperty?.GetSetMethod(true)!=null,"Native attraction setters changed");
      // Reproduce the old authored policy using the native decision, not a copied model.
      effectsProperty.SetValue(attraction,effects.Select(e=>new ContinuousEffectSpec {
        NeedId=e.NeedId, PointsPerHour=e.PointsPerHour, SatisfyToMaxValue=true }).ToList());
      maxProperty.SetValue(attraction,true);
      var previous=behavior.Decide(agent);
      Require(previous.Executor is ApplyEffectExecutor&&previous.ShouldReturnToBehavior,
        "Old policy no longer reproduces bypassing root needs");
      Debug.Log(Tag+"PASS old policy returns to study despite empty hunger, thirst and sleep needs");
      effectsProperty.SetValue(attraction,effects); maxProperty.SetValue(attraction,false);
      var current=behavior.Decide(agent);
      Require(current.Executor is ApplyEffectExecutor&&!current.ShouldReturnToBehavior,
        "Ordinary study visit did not release to root needs after the session");
      Debug.Log(Tag+"PASS authored policy releases to native root needs after each short study session");
      student.AddStudyHours("Metallurgy",(school.StudyHours-student.StudyHoursIn("Metallurgy"))/2f,school.StudyHours);
      float progress=student.StudyHoursIn("Metallurgy");
      pause.Pause();
      Require(!attraction.IsUsable,"Paused school remains usable");
      Require(current.Executor.Tick(0)==ExecutorStatus.Failure,"Pausing did not abort the active native lesson");
      var stopped=behavior.Decide(agent);
      Require(stopped.Executor==null&&!stopped.ShouldReturnToBehavior,"Paused lesson retained control of the student");
      Require(behavior.ActionPosition(needs)==null,"Paused school still accepts incoming students");
      Require(student.StudyHoursIn("Metallurgy")==progress,"Pausing discarded accumulated study hours");
      pause.Resume();
      Require(attraction.IsUsable,"Resumed school did not reopen");
      var resumed=behavior.Decide(agent);
      Require(resumed.Executor is ApplyEffectExecutor&&!resumed.ShouldReturnToBehavior,"Resume restored noninterruptible study");
      enterer.UnreserveSlotAndExit();
      Debug.Log(Tag+"COMPLETE native study priority, occupied pause, incoming pause, resume and preserved progress passed; no save written");
    }
  }
}
#endif
