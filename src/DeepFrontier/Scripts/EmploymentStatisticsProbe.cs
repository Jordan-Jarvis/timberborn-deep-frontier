#if !UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using Bindito.Core;
using Newtonsoft.Json;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockingSystem;
using Timberborn.Characters;
using Timberborn.EntitySystem;
using Timberborn.GameDistricts;
using Timberborn.PopulationStatisticsSystem;
using Timberborn.PopulationWorkStatistics;
using Timberborn.SingletonSystem;
using Timberborn.WorkSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  [Context("Game")]
  public sealed class EmploymentStatisticsProbeConfigurator : Configurator {
    protected override void Configure() {
      if(Environment.GetCommandLineArgs().Contains("-deepFrontierEmploymentProbe"))Bind<EmploymentStatisticsProbe>().AsSingleton();
    }
  }
  // Read-only audit of native registries, cached event totals and actual workers.
  internal sealed class EmploymentStatisticsProbe : IPostLoadableSingleton,IUpdatableSingleton {
    private const string Tag="[DeepFrontier EmploymentProbe] ";
    private readonly EntityRegistry _entities;
    private readonly GlobalEmploymentStatisticsProvider _employment;
    private readonly GlobalWorkRefusingStatisticsProvider _refusing;
    private readonly Queue<string> _events=new();
    private float _next;
    private string _last;
    private int _frame;
    private float _auditStart;
    private bool _verified,_failed;
    public EmploymentStatisticsProbe(EntityRegistry entities,GlobalEmploymentStatisticsProvider employment,GlobalWorkRefusingStatisticsProvider refusing) {
      _entities=entities;_employment=employment;_refusing=refusing;
    }
    private static object Field(object target,string name) => (target.GetType().GetField(name,BindingFlags.NonPublic|BindingFlags.Instance)
      ??throw new MissingFieldException(target.GetType().FullName,name)).GetValue(target);
    private void Record(string value) { if(_events.Count==24)_events.Dequeue();_events.Enqueue(value); }
    public void PostLoad() {
      if(Path.GetFileName(MemoryLoadProbe.SavePath())!="employment-repro-copy.timber" || Environment.GetCommandLineArgs().Contains(MemoryLoadProbe.SaveAsFlag))
        throw new InvalidOperationException("Employment probe requires its named disposable copy and must not save");
      foreach(var entity in _entities.Entities) {
        var registry=entity.GetComponent<DistrictBuildingRegistry>();
        if(registry) {
          registry.FinishedBuildingRegistered+=(_,a)=>Record("district registered "+a.Building.Name+" "+a.Building.GetComponent<EntityComponent>().EntityId);
          registry.FinishedBuildingUnregistered+=(_,a)=>Record("district unregistered "+a.Building.Name+" "+a.Building.GetComponent<EntityComponent>().EntityId);
        }
        var workplace=entity.GetComponent<Workplace>();
        if(workplace) {
          workplace.WorkerAssigned+=(_,a)=>Record("assigned "+a.Worker.Name+" to "+workplace.Name);
          workplace.WorkerUnassigned+=(_,a)=>Record("unassigned "+a.Worker.Name+" from "+workplace.Name);
        }
        var refuser=entity.GetComponent<WorkRefuser>();
        if(refuser)refuser.RefusesWorkChanged+=(_,a)=>Record("refusal "+refuser.Name+"="+refuser.RefusesWork);
      }
    }
    public void UpdateSingleton() {
      if(++_frame<60||Time.unscaledTime<_next)return;
      if(_frame==60)_auditStart=Time.unscaledTime;
      _next=Time.unscaledTime+2;
      var workers=_entities.Entities.Select(e=>e.GetComponent<Worker>()).Where(w=>w).ToArray();
      var workplaces=_entities.Entities.Select(e=>e.GetComponent<Workplace>()).Where(w=>w&&w.Enabled).ToArray();
      var districts=_entities.Entities.Select(e=>e.GetComponent<DistrictCenter>()).Where(d=>d&&d.Enabled).ToArray();
      var rows=new List<object>();
      bool mismatch=false;
      foreach(var type in new[]{"Beaver","Bot"}) {
        var living=workers.Where(w=>w.WorkerType==type&&w.GetComponent<Character>().Alive).ToArray();
        var employed=_employment.GetEmploymentStatistics(type);
        var refusing=_refusing.GetWorkRefusingStatistics(type);
        int actualEmployed=living.Count(w=>w.Workplace),actualRefusing=living.Count(w=>w.GetComponent<WorkRefuser>().RefusesWork);
        mismatch|=employed.EmployedWorkers!=actualEmployed || refusing.RefusingWorkers!=actualRefusing || refusing.NotRefusingWorkers!=living.Length-actualRefusing;
        rows.Add(new {type,alive=living.Length,actualEmployed,actualRefusing,reportedEmployed=employed.EmployedWorkers,
          reportedRefusing=refusing.RefusingWorkers,reportedEmployable=refusing.NotRefusingWorkers,unemployed=refusing.NotRefusingWorkers-employed.EmployedWorkers});
      }
      string summary=JsonConvert.SerializeObject(rows);
      if(Time.unscaledTime-_auditStart>=30) {
        if(mismatch&&!_failed) {_failed=true;Debug.LogError(Tag+"FAILED employment/eligibility mismatch after district startup: "+summary);}
        else if(!mismatch&&!_verified&&!_failed) {_verified=true;Debug.Log(Tag+"PASS native employment and refusal totals match living workers after district startup");}
      }
      if(summary==_last)return;
      _last=summary;Debug.Log(Tag+summary);
      if(!mismatch)return;
      var counterErrors=new List<object>();
      foreach(var w in workplaces) {
        var counter=w.GetComponent<WorkplaceWorkerCounter>();
        var cached=counter.GetCurrentEmploymentStatistics();
        bool unblocked=w.GetComponent<BlockableObject>().IsUnblocked;
        int expected=unblocked?w.NumberOfAssignedWorkers:0;
        string workerType=w.GetComponent<WorkplaceWorkerType>().WorkerType;
        if(cached.EmployedWorkers!=expected||cached.WorkerType!=workerType)counterErrors.Add(new {name=w.Name,id=w.GetComponent<EntityComponent>().EntityId,cached=cached.EmployedWorkers,expected,cachedType=cached.WorkerType,workerType});
      }
      var districtRows=districts.Select(d=>new {id=d.GetComponent<EntityComponent>().EntityId,types=new[]{"Beaver","Bot"}.Select(t=>new {
        type=t,reported=d.GetComponent<DistrictEmploymentStatisticsProvider>().GetEmploymentStatistics(t).EmployedWorkers,
        actual=workplaces.Where(w=>w.GetComponent<DistrictBuilding>().District==d&&w.GetComponent<BlockableObject>().IsUnblocked&&w.GetComponent<WorkplaceWorkerType>().WorkerType==t).Sum(w=>w.NumberOfAssignedWorkers)
      }).ToArray()}).ToArray();
      var invalid=workers.Where(w=>w.Workplace&&(!w.GetComponent<Character>().Alive||w.GetComponent<WorkRefuser>().RefusesWork))
        .Select(w=>new {w.Name,alive=w.GetComponent<Character>().Alive,refuses=w.GetComponent<WorkRefuser>().RefusesWork,workplace=w.Workplace.Name}).ToArray();
      var registry=(IDictionary)Field(Field(_refusing,"_workRefuserRegistry"),"_workerTypeWorkRefusers");
      var registryErrors=new List<object>();
      foreach(DictionaryEntry entry in registry) {
        foreach(var field in new[]{"_refusingWorkRefusers","_notRefusingWorkRefusers"}) {
          var members=((IEnumerable)Field(entry.Value,field)).Cast<WorkRefuser>().ToArray();
          foreach(var r in members.Where(r=>!r.GetComponent<Character>().Alive || r.RefusesWork!=(field=="_refusingWorkRefusers")))
            registryErrors.Add(new {type=entry.Key,field,r.Name,alive=r.GetComponent<Character>().Alive,r.RefusesWork});
        }
      }
      var providerIds=((IEnumerable)Field(_employment,"_districtEmploymentStatisticsProviders")).Cast<DistrictEmploymentStatisticsProvider>()
        .Select(d=>d.GetComponent<EntityComponent>().EntityId).ToArray();
      Debug.Log(Tag+"MISMATCH "+JsonConvert.SerializeObject(new {counterErrors,districtRows,invalid,registryErrors,providerIds,events=_events.ToArray()}));
    }
  }
}
#endif
