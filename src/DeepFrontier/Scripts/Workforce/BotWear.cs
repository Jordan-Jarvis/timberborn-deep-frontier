using System;
using Timberborn.BaseComponentSystem;
using Timberborn.EnterableSystem;
using Timberborn.Persistence;
using Timberborn.WorkSystem;
using Timberborn.WorldPersistence;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Faster bot deterioration inside heavy industry.
  //
  // Native Deteriorable (1.1.2.8) counts _currentDeterioration down by one
  // fixed tick per Tick and kills the bot at zero (Iron Teeth bots: 70 days).
  // It exposes no rate or setter, so BotWearDeteriorationPatch (Harmony,
  // registered by WorkforceModStarter) subtracts (Multiplier - 1) extra ticks
  // while this bot stands inside a workplace whose FrontierWorkforceRiskSpec
  // declares BotWearMultiplier > 1. Saves stay native: only the native field
  // changes.
  //
  // Maintenance (BotMaintenance): a dose of oil taken at a wearing workplace
  // multiplies that workplace's rate by the good's WearFactor (never below
  // 1x) for ServiceHours of wearing time. The dose stays with the bot and is
  // saved with it.
  internal sealed class BotWear : BaseComponent, IAwakableComponent, IPersistentEntity {
    private static readonly ComponentKey Key=new("DeepFrontier.BotWear");
    private static readonly PropertyKey<string> ServiceGoodKey=new("ServiceGood");
    private static readonly PropertyKey<float> ServiceWearFactorKey=new("ServiceWearFactor");
    private static readonly PropertyKey<float> ServiceHoursLeftKey=new("ServiceHoursLeft");

    private Worker _worker;
    private Enterer _enterer;

    public IndustrialRisk Risk { get; private set; }
    public bool Wearing=>Risk&&Risk.BotWearMultiplier>1f&&_enterer.CurrentBuilding==Risk.Enterable;
    public float Multiplier=>!Wearing?1f:IsServiced?Serviced(Risk.BotWearMultiplier,ServiceWearFactor):Risk.BotWearMultiplier;
    // null while no maintenance dose is active.
    public string ServiceGood { get; private set; }
    public float ServiceWearFactor { get; private set; }
    public float ServiceHoursLeft { get; private set; }
    public bool IsServiced=>ServiceGood!=null;

    public static float Serviced(float multiplier, float wearFactor)=>Mathf.Max(1f,multiplier*wearFactor);

    public void Awake() {
      _worker=GetComponent<Worker>();
      _enterer=GetComponent<Enterer>();
      if(!_worker||!_enterer)throw new InvalidOperationException($"{Name}: bot wear needs a native Worker and Enterer");
      // Load re-employs through Workplace.AssignWorker, which raises GotEmployed.
      _worker.GotEmployed+=(_,_)=>Risk=_worker.Workplace.GetComponent<IndustrialRisk>();
      _worker.GotUnemployed+=(_,_)=>Risk=null;
    }

    public void Service(string goodId, float wearFactor, float hours) {
      if(IsServiced)throw new InvalidOperationException($"{Name} is already serviced with {ServiceGood}");
      if(string.IsNullOrEmpty(goodId)||!(wearFactor>0f&&wearFactor<1f)||!(hours>0f))
        throw new ArgumentException($"{Name}: invalid maintenance dose {goodId} x{wearFactor} for {hours} h");
      ServiceGood=goodId;ServiceWearFactor=wearFactor;ServiceHoursLeft=hours;
    }

    public void ElapseService(float hours) {
      if(!IsServiced)return;
      ServiceHoursLeft-=hours;
      if(ServiceHoursLeft>0f)return;
      ServiceGood=null;ServiceWearFactor=0f;ServiceHoursLeft=0f;
    }

    public void Save(IEntitySaver saver) {
      if(!IsServiced)return;
      var data=saver.GetComponent(Key);
      data.Set(ServiceGoodKey,ServiceGood);
      data.Set(ServiceWearFactorKey,ServiceWearFactor);
      data.Set(ServiceHoursLeftKey,ServiceHoursLeft);
    }

    public void Load(IEntityLoader loader) {
      if(!loader.TryGetComponent(Key,out var data))return; // no active dose (or saved before maintenance existed)
      Service(data.Get(ServiceGoodKey),data.Get(ServiceWearFactorKey),data.Get(ServiceHoursLeftKey));
    }
  }
}
