#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using DeepFrontier.Scripts.RadioactiveTide;
using DeepFrontier.Scripts.Sensors;
using DeepFrontier.Scripts.WeatherStations;
using Timberborn.Automation;
using Timberborn.AutomationBuildings;
using Timberborn.BlockSystem;
using Timberborn.Debugging;
using Timberborn.GameCycleSystem;
using Timberborn.HazardousWeatherSystem;
using Timberborn.WeatherSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Contamination and weather consumer probes of the all-buildings acceptance. They run after the
  // last batch (pad and sites), on the emptied pad, one after the other:
  //   Sluice (Sluice is Back!, through the optional DeepFrontier.SluiceIsBack bridge)
  //     A 1x4 pool sealed by a ring of ReinforcedDamBlocks holds 0.4 clean + 0.4 radioactive water on
  //     the sluice's source and downstream cells (radioactive share about 0.5, badwater 0). The sluice
  //     is in auto mode with the outflow (depth) rule off, so only its contamination rule decides
  //     Sluice.IsOpen. Per case the Measures choice and the mod's own toggle and limit are set and the
  //     state is read after the sluice has ticked:
  //       Badwater, close above 5%   -> open   (radiation ignored)
  //       Radiation, close above 5%  -> closed
  //       Any, close above 5%        -> closed
  //       Radiation, close below r+0.1 -> closed;  close below r-0.1 -> open
  //       Badwater, close below 5%   -> closed (badwater 0 < 5%; with radiation counted it would be open)
  //     Skipped when Sluice is Back! is not loaded.
  //   Weather Station (vanilla tide or the Moddable Weathers bridge, whichever runs)
  //     Four stations: Radioactive Tide mode; the same with the native early activation at its maximum;
  //     native Badtide; native Temperate. The dev command "Deep Frontier: radioactive tide next cycle"
  //     forces the next cycle's tide, then the native dev "Jump to next season" moves through the
  //     seasons (and whole native days, IDayNightCycle.SetTimeToNextDay as the native fast forwarder
  //     does, into the early-activation window). At every stop each station's native Automator state
  //     is compared with the native weather state:
  //       tide mode        On iff the cycle's hazardous weather is the tide and it has started
  //       tide + early     On iff the cycle's hazardous weather is the tide and the start is within the
  //                        early activation hours (or has passed)
  //       Badtide mode     Off during a tide;  Temperate mode  Off while the tide is in progress
  //     and the forced cycle must hold the tide.
  // Findings are recorded on two probe subjects (Kind "Probe") and the run continues.
  internal sealed partial class AllBuildingsAcceptance {
    private const int ProbePhase=20;
    private const float ProbeSettleHours=.3f,ProbeStepHours=.15f;
    private const string DamTemplate="ReinforcedDamBlock.IronTeeth",StationTemplate="WeatherStation.IronTeeth";
    private const string TideCommand="Deep Frontier: radioactive tide next cycle",JumpCommand="Jump to next season";
    private const int MaxJumps=4,MaxDaySkips=40;
    private readonly IEnumerable<IDevModule> _devModules;
    private readonly HazardousWeatherService _hazardousWeather;
    private readonly WeatherService _weather;
    private readonly GameCycleService _cycles;
    private readonly Queue<(Subject Subject,IEnumerator<float> Steps)> _probes=new();
    private (Subject Subject,IEnumerator<float> Steps)? _probe;
    private bool _probesStarted;
    private float _probeDue;

    // After the last batch (StartBatch with nothing left); returns false once the probes have run.
    private bool StartProbes() {
      if(_probesStarted)return false;
      _probesStarted=true;
      _wave.Clear();_current=null;_batchObjects.Clear();
      var sluice=new Subject{Template=SluiceIsBackBridge.Template,Kind="Probe",Batch="probes"};
      var station=new Subject{Template=StationTemplate,Kind="Probe",Batch="probes"};
      _subjects.Add(sluice);_subjects.Add(station);
      _probes.Enqueue((sluice,SluiceProbe(sluice)));
      _probes.Enqueue((station,StationProbe(station)));
      Debug.Log(Tag+" PROBES on the emptied pad "+_pad+": sluice radiation measurement, weather station radioactive tide");
      _probeDue=_clock.PartialDayNumber;
      _speed.ChangeSpeed(3);
      Phase(ProbePhase,"contamination and weather probes");
      return true;
    }

    // Each probe is an iterator yielding the game hours to wait before its next step.
    private void ProbeTick() {
      if(_clock.PartialDayNumber<_probeDue)return;
      if(_probe==null) {
        if(_probes.Count==0){Finish();return;}
        _probe=_probes.Dequeue();
      }
      var (subject,steps)=_probe.Value;
      bool more;
      try {more=steps.MoveNext();}
      catch(Exception error){Record(subject,"probe completed",false,"exception: "+error.GetType().Name+": "+error.Message);more=false;}
      if(!more){_probe=null;return;}
      _probeDue=_clock.PartialDayNumber+steps.Current/24f;
    }

    // ---------- sluice ----------
    private IEnumerator<float> SluiceProbe(Subject s) {
      if(Template(SluiceIsBackBridge.Template)==null){Skip(s,"sluice: radiation measurement",SluiceIsBackBridge.ModId+" (Sluice is Back!) is not loaded");yield break;}
      int x0=_pad.xMax-Margin-3,y0=_pad.yMin+Margin;
      var gate=new Vector3Int(x0+1,y0+2,_ground);
      var source=gate+new Vector3Int(0,-1,0);
      var downstream=gate+new Vector3Int(0,2,0);
      var dam=Spec(DamTemplate);int blocks=0;
      for(int x=x0;x<=x0+2;x++)for(int y=y0;y<=y0+5;y++)
        if(x==x0||x==x0+2||y==y0||y==y0+5){Create(dam,At(new Vector3Int(x,y,_ground)));blocks++;}
      var sluice=Create(Spec(SluiceIsBackBridge.Template),At(gate));
      var choice=sluice.GetComponent<IContaminationSubstanceChoice>();
      Require(choice!=null,"the sluice has no IContaminationSubstanceChoice: the "+SluiceIsBackBridge.BridgeAssembly+" bridge did not decorate it");
      object state=ModComponent(sluice,"SluiceIsBack.Components.SluiceState"),gateComponent=ModComponent(sluice,"SluiceIsBack.Components.Sluice");
      Call(state,"SetAuto");Call(state,"DisableAutoCloseOnOutflow");
      foreach(var c in new[]{source,downstream}){_waterService.AddCleanWater(c,.4f);_radiation.AddRadioactiveWater(c,.4f);}
      Record(s,"sluice: placed with the badwater default",choice.Substance==SensedSubstance.Badwater,"sluice at "+gate+" Cw0 (source "+source+", downstream "+downstream+
        ") inside "+blocks+" "+DamTemplate+"; 0.4 clean + 0.4 radioactive water on the source and downstream cells; auto mode, depth rule off; measures "+choice.Substance);
      yield return ProbeSettleHours;
      var sample=_radiation.Sample(source);
      float r=sample.WaterRadiation;
      Record(s,"sluice: source column radioactive",r>=.2f&&sample.BadwaterShare<.01f,"source "+source+" radioactive share "+r.ToString("0.000")+", badwater "+
        sample.BadwaterShare.ToString("0.000")+", depth "+_water.WaterDepth(source).ToString("0.00"));
      if(r<.2f)yield break;
      float above=Mathf.Round((r+.1f)*100f)/100f,below=Mathf.Round((r-.1f)*100f)/100f;
      var cases=new (SensedSubstance Substance,bool Above,float Limit,bool Open)[]{
        (SensedSubstance.Badwater,true,.05f,true),(SensedSubstance.Radiation,true,.05f,false),(SensedSubstance.Any,true,.05f,false),
        (SensedSubstance.Radiation,false,above,false),(SensedSubstance.Radiation,false,below,true),(SensedSubstance.Badwater,false,.05f,false)};
      foreach(var (substance,closeAbove,limit,open) in cases) {
        string check="sluice: measures "+substance+", close "+(closeAbove?"above ":"below ")+(limit*100f).ToString("0")+"% -> "+(open?"open":"closed");
        choice.SetSubstance(substance);
        Call(state,closeAbove?"EnableAutoCloseOnAbove":"EnableAutoCloseOnBelow");
        Call(state,closeAbove?"SetAboveContaminationLimit":"SetBelowContaminationLimit",limit);
        yield return ProbeStepHours;
        bool isOpen=(bool)Property(gateComponent,"IsOpen");
        var now=_radiation.Sample(source);
        Record(s,check,isOpen==open&&choice.Substance==substance,"IsOpen="+isOpen+"; source radioactive "+now.WaterRadiation.ToString("0.000")+", badwater "+
          now.BadwaterShare.ToString("0.000")+"; choice "+choice.Substance+", AutoCloseOnAbove="+Property(state,"AutoCloseOnAbove")+" ("+Property(state,"OnAboveLimit")+
          "), AutoCloseOnBelow="+Property(state,"AutoCloseOnBelow")+" ("+Property(state,"OnBelowLimit")+")");
      }
    }
    // Sluice is Back! types are reached by name: the main assembly must not reference the optional mod.
    private static object ModComponent(BlockObject b,string fullName)=>
      b.AllComponents.SingleOrDefault(c=>c.GetType().FullName==fullName)??throw new InvalidOperationException(b.Name+" has no "+fullName);
    private static void Call(object target,string method,params object[] args) {
      var m=target.GetType().GetMethod(method,BindingFlags.Instance|BindingFlags.Public,null,args.Select(a=>a.GetType()).ToArray(),null)
        ??throw new InvalidOperationException(target.GetType().Name+"."+method+" not found (Sluice is Back! 11.0.0)");
      m.Invoke(target,args);
    }
    private static object Property(object target,string name)=>
      (target.GetType().GetProperty(name,BindingFlags.Instance|BindingFlags.Public)??throw new InvalidOperationException(target.GetType().Name+"."+name+" not found (Sluice is Back! 11.0.0)"))
        .GetValue(target);

    // ---------- weather station ----------
    private sealed class Stations {
      public WeatherStation Tide,Early,Badtide,Temperate;
    }
    private IEnumerator<float> StationProbe(Subject s) {
      var force=DevCommand(TideCommand);var jump=DevCommand(JumpCommand);
      string path=RadioactiveTideModStarter.ModdableWeathersLoaded?"Moddable Weathers (RadioactiveTideModdableWeather)":"vanilla (RadioactiveTideWeather)";
      var spec=Spec(StationTemplate);
      int y=_pad.yMax-Margin-2,x=_pad.xMin+Margin;
      WeatherStation Place(int i)=>Create(spec,At(new Vector3Int(x+4*i,y,_ground))).GetComponent<WeatherStation>();
      var st=new Stations{Tide=Place(0),Early=Place(1),Badtide=Place(2),Temperate=Place(3)};
      st.Tide.GetComponent<WeatherStationRadioactiveTide>().SetSignalsRadioactiveTide(true);
      st.Early.GetComponent<WeatherStationRadioactiveTide>().SetSignalsRadioactiveTide(true);
      st.Early.SetEarlyActivationEnabled(true);st.Early.SetEarlyActivationHours(Mathf.FloorToInt(st.Early.MaxEarlyActivationHours));
      st.Badtide.SetMode(WeatherStationMode.Badtide);st.Temperate.SetMode(WeatherStationMode.Temperate);
      Add(s,"weather station: tide path","INFO",path+"; stations at x "+x+".."+(x+12)+", y "+y+"; early activation "+st.Early.EarlyActivationHours+" h");
      yield return ProbeSettleHours;
      int cycle=_cycles.Cycle;
      CheckStations(s,st,"weather station: cycle "+cycle+" before the command");
      force.Invoke();
      Add(s,"weather station: dev command","INFO","'"+TideCommand+"' in cycle "+cycle+", day "+_cycles.PartialCycleDay.ToString("0.0")+" ("+WeatherState()+")");
      yield return ProbeStepHours;
      // Through the rest of the forced command's cycle.
      for(int jumps=0;_cycles.Cycle==cycle;jumps++) {
        Require(jumps<MaxJumps,"'"+JumpCommand+"' did not leave cycle "+cycle+" in "+MaxJumps+" jumps ("+WeatherState()+")");
        jump.Invoke();
        yield return ProbeSettleHours;
        CheckStations(s,st,"weather station: after a season jump (cycle "+_cycles.Cycle+")");
      }
      Record(s,"weather station: the forced cycle holds the tide",_cycles.Cycle==cycle+1&&IsTide(),WeatherState());
      if(!IsTide())yield break;
      // Into the early activation window before the tide, a native day at a time.
      float early=st.Early.EarlyActivationHours;
      for(int days=0;!_weather.IsHazardousWeather&&HoursToHazard()>early-6f;days++) {
        Require(days<MaxDaySkips,"the tide's start stayed "+HoursToHazard().ToString("0")+" h away after "+MaxDaySkips+" days");
        _clock.SetTimeToNextDay();
        yield return ProbeStepHours;
      }
      if(!_weather.IsHazardousWeather)
        Record(s,"weather station: advance warning (early activation) before the tide",On(st.Early)&&!On(st.Tide),
          "tide starts in "+HoursToHazard().ToString("0.0")+" h, early activation "+early+" h; "+States(st));
      // The tide itself.
      for(int jumps=0;!_weather.IsHazardousWeather;jumps++) {
        Require(jumps<MaxJumps,"'"+JumpCommand+"' did not start the tide in "+MaxJumps+" jumps ("+WeatherState()+")");
        jump.Invoke();
        yield return ProbeSettleHours;
      }
      Record(s,"weather station: signals while the radioactive tide is active",IsTide()&&On(st.Tide)&&On(st.Early)&&!On(st.Badtide)&&!On(st.Temperate),
        WeatherState()+"; "+States(st)+" (expected tide On, tide+early On, Badtide Off, Temperate Off)");
      CheckStations(s,st,"weather station: during the tide");
      int tideCycle=_cycles.Cycle;
      for(int jumps=0;_cycles.Cycle==tideCycle;jumps++) {
        Require(jumps<MaxJumps,"'"+JumpCommand+"' did not end the tide's cycle in "+MaxJumps+" jumps ("+WeatherState()+")");
        jump.Invoke();
        yield return ProbeSettleHours;
      }
      Record(s,"weather station: stops after the tide",!IsTide()&&!On(st.Tide)&&!On(st.Early),WeatherState()+"; "+States(st));
    }
    // Every station against the native weather state at this stop.
    private void CheckStations(Subject s,Stations st,string check) {
      bool tide=IsTide(),started=tide&&_weather.IsHazardousWeather;
      bool early=tide&&(_weather.IsHazardousWeather||HoursToHazard()<=st.Early.EarlyActivationHours);
      bool ok=On(st.Tide)==started&&On(st.Early)==early&&(!tide||!On(st.Badtide))&&(!started||!On(st.Temperate));
      Record(s,check,ok,WeatherState()+"; "+States(st)+"; expected tide "+(started?"On":"Off")+", tide+early "+(early?"On":"Off")+
        (tide?", Badtide Off":"")+(started?", Temperate Off":""));
    }
    private bool IsTide()=>_hazardousWeather.CurrentCycleHazardousWeather?.Id==RadioactiveTideTuning.WeatherId;
    private float HoursToHazard()=>(_weather.HazardousWeatherStartCycleDay-_cycles.PartialCycleDay)*24f;
    private static bool On(WeatherStation station)=>station.GetComponent<Automator>().State==AutomatorState.On;
    private string WeatherState()=>"cycle "+_cycles.Cycle+" day "+_cycles.PartialCycleDay.ToString("0.00")+", hazardous weather of the cycle "+
      (_hazardousWeather.CurrentCycleHazardousWeather?.Id??"none")+" from day "+_weather.HazardousWeatherStartCycleDay+(_weather.IsHazardousWeather?" (in progress)":" (not started)");
    private static string States(Stations st)=>"tide "+State(st.Tide)+", tide+early "+State(st.Early)+", Badtide "+State(st.Badtide)+", Temperate "+State(st.Temperate);
    private static string State(WeatherStation station)=>station.GetComponent<Automator>().State.ToString();
    private DevMethod DevCommand(string name) {
      var found=_devModules.SelectMany(m=>m.GetDefinition().Methods).Where(m=>m.Name==name).ToList();
      Require(found.Count==1,"expected one dev method '"+name+"', found "+found.Count);
      return found[0];
    }
  }
}
#endif
