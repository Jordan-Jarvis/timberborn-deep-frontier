#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using HarmonyLib;
using Timberborn.GameDistricts;
using Timberborn.ModManagerScene;
using Timberborn.SliderToggleSystem;
using Timberborn.TooltipSystem;
using Timberborn.WorkerTypesUI;
using Timberborn.WorkSystem;
using Timberborn.WorkSystemUI;
using UnityEngine;
using UnityEngine.UIElements;

namespace DeepFrontier.Scripts.SuperBots {
  // Harmony for Reactor Bot workplaces (Timberborn 1.1.2.8, decompiled
  // Timberborn.WorkSystem, Timberborn.WorkSystemUI, Timberborn.GameDistrictsUI).
  // Every target and member is checked at mod start; a changed game throws
  // there instead of patching. Why each one is needed:
  //
  // 1. WorkerTypeToggle.Initialize, postfix: the workplace toggle (entity panel
  //    and batch control window, both made by WorkerTypeToggleFactory) is built
  //    there from exactly two SliderToggleItems. The postfix rebuilds its
  //    SliderToggle with the native Beaver item, the native Bot item (active
  //    only while the workplace is not set to Reactor Bots) and a Reactor Bot
  //    item furthest right (the bot icon tinted neon green).
  // 2. DistrictCenterFragment.InitializeFragment, postfix: the same for the
  //    District Center's default worker type.
  // 3. UnemployedWorkers.UpdateUnemployedState, prefix: the native district
  //    assigner hires a bot workplace's crew from its per-worker-type pool of
  //    unemployed workers, and a Reactor Bot is a "Bot" worker (its template's
  //    WorkerSpec). The prefix keeps Reactor Bots out of that pool, so Bot
  //    workplaces get ordinary bots only. Registration in the pool stays native.
  // 4. PriorityOrderedWorkplaces.GetHighestPriorityUnderstaffedWorkplace and
  //    GetLowestPriorityStaffedWorkplace, postfixes: a workplace set to Reactor
  //    Bots keeps the native type Bot, so it sits in the native Bot assigner;
  //    when native picks one, the postfix picks the next workplace not set to
  //    Reactor Bots instead, so native neither hires into it nor takes its crew.
  //    ReactorBotStaffing staffs it.
  // 5. WorkplaceWorkerType.SetWorkerTypeToDistrict, prefix and postfix: a new
  //    workplace takes its district's default type there, once (_wasSet). With
  //    the district's Reactor Bot default it is set to Reactor Bots where that
  //    option is unlocked; elsewhere the native result stands (the native
  //    default is Bot).
  internal sealed class ReactorBotWorkplaceModStarter : IModStarter {
    public void StartMod(IModEnvironment modEnvironment) {
      ReactorBotWorkplacePatches.Apply();
      Debug.Log("[DeepFrontier] Reactor Bot workplace patches applied (worker-type toggles, unemployed pool, workplace order, district default).");
    }
  }

  internal static class ReactorBotWorkplacePatches {
    private const string Tag="[DeepFrontier ReactorBotWorkplacePatches] ";
    private const BindingFlags All=BindingFlags.Instance|BindingFlags.Static|BindingFlags.Public|BindingFlags.NonPublic;

    // WorkerTypeToggle members.
    private static FieldInfo _toggleSlider, _toggleFactory, _toggleWorkerType;
    private static MethodInfo _beaverTooltip, _botTooltip, _beaverState, _botState, _setBeaver;
    private static string _beaverClass, _botClass;
    // DistrictCenterFragment members.
    private static FieldInfo _fragmentSlider, _fragmentFactory, _fragmentRoot, _fragmentDefault;
    private static MethodInfo _fragmentBeaverTooltip, _fragmentBotTooltip;
    // PriorityOrderedWorkplaces._workplaces (a SortedList keyed by a private struct).
    private static FieldInfo _orderedWorkplaces;
    private static PropertyInfo _orderedValues;
    // The patch targets, resolved and checked by Verify before any is patched.
    private static MethodInfo _initialize, _initializeFragment, _update, _toDistrict;
    private static readonly List<(MethodInfo Target, string Postfix)> _ordered=new();

    internal static void Apply()=>NativePatches.Install("DeepFrontier.ReactorBotWorkplaces",Verify,harmony=>{
      var self=typeof(ReactorBotWorkplacePatches);
      harmony.Patch(_initialize,postfix:new HarmonyMethod(self,nameof(WorkerTypeTogglePostfix)));
      harmony.Patch(_initializeFragment,postfix:new HarmonyMethod(self,nameof(DistrictCenterFragmentPostfix)));
      harmony.Patch(_update,prefix:new HarmonyMethod(self,nameof(UpdateUnemployedStatePrefix)));
      foreach(var (target,postfix) in _ordered)harmony.Patch(target,postfix:new HarmonyMethod(self,postfix));
      harmony.Patch(_toDistrict,prefix:new HarmonyMethod(self,nameof(SetWorkerTypeToDistrictPrefix)),postfix:new HarmonyMethod(self,nameof(SetWorkerTypeToDistrictPostfix)));
    });

    private static void Verify() {
      NativeWorkerTypeAccess.Verify();

      // 1. WorkerTypeToggle.
      var toggle=typeof(WorkerTypeToggle);
      var initialize=Method(toggle,"Initialize",typeof(VisualElement),typeof(string));
      var blockable=Method(typeof(SliderToggleItem),nameof(SliderToggleItem.CreateBlockable),typeof(Func<TooltipContent>),typeof(string),typeof(Action),typeof(Func<SliderToggleState>));
      var callees=NativeIl.Callees(initialize);
      Require(callees.Count(m=>Same(m,blockable))==2,"WorkerTypeToggle.Initialize no longer builds two blockable items");
      Require(callees.Any(m=>m.DeclaringType==typeof(SliderToggleFactory)&&(m.Name==nameof(SliderToggleFactory.Create)||m.Name==nameof(SliderToggleFactory.CreateBindable))),
        "WorkerTypeToggle.Initialize no longer creates its SliderToggle through SliderToggleFactory");
      Require(NativeIl.Calls(Method(typeof(WorkerTypeToggleFactory),nameof(WorkerTypeToggleFactory.CreateBindable),typeof(VisualElement),typeof(string)),initialize),
        "WorkerTypeToggleFactory.CreateBindable no longer calls WorkerTypeToggle.Initialize");
      _toggleSlider=Field(toggle,"_sliderToggle",typeof(SliderToggle));
      _toggleFactory=Field(toggle,"_sliderToggleFactory",typeof(SliderToggleFactory));
      _toggleWorkerType=Field(toggle,"_workplaceWorkerType",typeof(WorkplaceWorkerType));
      _beaverTooltip=Returning(toggle,"GetBeaverButtonTooltip",typeof(TooltipContent));
      _botTooltip=Returning(toggle,"GetBotButtonTooltip",typeof(TooltipContent));
      _beaverState=Returning(toggle,"GetBeaverToggleState",typeof(SliderToggleState));
      _botState=Returning(toggle,"GetBotToggleState",typeof(SliderToggleState));
      _setBeaver=Returning(toggle,"SetBeaverWorkerType",typeof(void));
      _beaverClass=StaticString(toggle,"BeaverClass");
      _botClass=StaticString(toggle,"BotClass");
      _initialize=initialize;

      // 2. DistrictCenterFragment (internal).
      // Internal types are taken from their assembly through a public type of it, so it is loaded.
      var fragment=Internal(typeof(Timberborn.GameDistrictsUI.ConnectionAnchorPointSpec),"Timberborn.GameDistrictsUI.DistrictCenterFragment");
      var initializeFragment=Method(fragment,"InitializeFragment");
      var item=Method(typeof(SliderToggleItem),nameof(SliderToggleItem.Create),typeof(Func<string>),typeof(string),typeof(Action),typeof(Func<bool>));
      var fragmentCallees=NativeIl.Callees(initializeFragment);
      Require(fragmentCallees.Count(m=>Same(m,item))==2,"DistrictCenterFragment.InitializeFragment no longer builds two worker-type items");
      Require(fragmentCallees.Any(m=>m.DeclaringType==typeof(SliderToggleFactory)&&m.Name==nameof(SliderToggleFactory.Create)),
        "DistrictCenterFragment.InitializeFragment no longer creates its SliderToggle through SliderToggleFactory.Create");
      _fragmentSlider=Field(fragment,"_sliderToggle",typeof(SliderToggle));
      _fragmentFactory=Field(fragment,"_sliderToggleFactory",typeof(SliderToggleFactory));
      _fragmentRoot=Field(fragment,"_workerTypeRoot",typeof(VisualElement));
      _fragmentDefault=Field(fragment,"_districtDefaultWorkerType",typeof(DistrictDefaultWorkerType));
      _fragmentBeaverTooltip=Returning(fragment,"GetBeaverWorkerTooltip",typeof(string));
      _fragmentBotTooltip=Returning(fragment,"GetBotWorkerTooltip",typeof(string));
      Require(StaticString(fragment,"BeaverClass")==_beaverClass&&StaticString(fragment,"BotClass")==_botClass,
        "DistrictCenterFragment and WorkerTypeToggle no longer share their icon classes");
      _initializeFragment=initializeFragment;

      // 3. UnemployedWorkers (internal).
      var unemployed=Internal(typeof(Workplace),"Timberborn.WorkSystem.UnemployedWorkers");
      var update=Method(unemployed,"UpdateUnemployedState",typeof(Worker),typeof(WorkRefuser));
      Require(!NativeIl.Inlinable(update),"UnemployedWorkers.UpdateUnemployedState is small enough to be inlined");
      Field(unemployed,"_unemployed",typeof(HashSet<Worker>));
      foreach(var caller in new[] {"AddWorker","OnGotUnemployed","OnRefusesWorkChanged"})
        Require(NativeIl.Calls(Method(unemployed,caller,caller=="AddWorker"?new[] {typeof(Worker)}:new[] {typeof(object),typeof(EventArgs)}),update),
          $"UnemployedWorkers.{caller} no longer calls UpdateUnemployedState");
      Require(update.GetParameters().Select(p=>p.Name).SequenceEqual(new[] {"worker","workRefuser"}),"UnemployedWorkers.UpdateUnemployedState parameters renamed");
      _update=update;

      // 4. PriorityOrderedWorkplaces.
      var ordered=typeof(PriorityOrderedWorkplaces);
      _orderedWorkplaces=AccessTools.Field(ordered,"_workplaces");
      Require(_orderedWorkplaces!=null&&_orderedWorkplaces.FieldType.IsGenericType&&_orderedWorkplaces.FieldType.GetGenericTypeDefinition()==typeof(SortedList<,>)
        &&_orderedWorkplaces.FieldType.GetGenericArguments()[1]==typeof(WorkplacePriority),"PriorityOrderedWorkplaces._workplaces is no longer a SortedList of WorkplacePriority");
      _orderedValues=_orderedWorkplaces.FieldType.GetProperty(nameof(SortedList<int,int>.Values));
      Require(_orderedValues!=null&&_orderedValues.PropertyType==typeof(IList<WorkplacePriority>),"SortedList.Values is no longer an IList of WorkplacePriority");
      _ordered.Clear();
      foreach(var name in new[] {nameof(PriorityOrderedWorkplaces.GetHighestPriorityUnderstaffedWorkplace),nameof(PriorityOrderedWorkplaces.GetLowestPriorityStaffedWorkplace)}) {
        var method=Returning(ordered,name,typeof(WorkplacePriority));
        Require(!NativeIl.Inlinable(method),$"PriorityOrderedWorkplaces.{name} is small enough to be inlined");
        _ordered.Add((method,name==nameof(PriorityOrderedWorkplaces.GetHighestPriorityUnderstaffedWorkplace)?nameof(HighestUnderstaffedPostfix):nameof(LowestStaffedPostfix)));
      }

      // 5. WorkplaceWorkerType.SetWorkerTypeToDistrict.
      var toDistrict=Method(typeof(WorkplaceWorkerType),"SetWorkerTypeToDistrict",typeof(DistrictCenter));
      Require(!NativeIl.Inlinable(toDistrict),"WorkplaceWorkerType.SetWorkerTypeToDistrict is small enough to be inlined");
      Require(NativeIl.Calls(toDistrict,Method(typeof(WorkplaceWorkerType),nameof(WorkplaceWorkerType.SetWorkerType),typeof(string))),
        "WorkplaceWorkerType.SetWorkerTypeToDistrict no longer calls SetWorkerType");
      Require(toDistrict.GetParameters().Single().Name=="districtCenter","WorkplaceWorkerType.SetWorkerTypeToDistrict parameter renamed");
      Field(typeof(WorkplaceWorkerType),"_wasSet",typeof(bool));
      _toDistrict=toDistrict;
    }

    // Initialization. Native EntityPanel.Load builds the entity-panel toggles
    // while singletons are still loading (SingletonLifecycleService.LoadAll:
    // every Load, then the entities, then every PostLoad), so these postfixes
    // touch no Deep Frontier singleton: the items reach ReactorBotWorkplaceUi
    // through the shown entity's component, in their callbacks, which run only
    // when the panel is shown, updated or clicked, and the third icon is tinted
    // on its first update.
    private static void WorkerTypeTogglePostfix(WorkerTypeToggle __instance, VisualElement parent, string toggleBindingKey) {
      ((SliderToggle)_toggleSlider.GetValue(__instance)).Root.RemoveFromHierarchy();
      ReactorBotWorkplace Workplace()=>ReactorBotWorkplaceUi.Of((WorkplaceWorkerType)_toggleWorkerType.GetValue(__instance));
      var beaverState=MakeDelegate<Func<SliderToggleState>>(_beaverState,__instance);
      var botState=MakeDelegate<Func<SliderToggleState>>(_botState,__instance);
      var setBeaver=MakeDelegate<Action>(_setBeaver,__instance);
      var tint=new LazyTint();
      var items=new[] {
        SliderToggleItem.CreateBlockable(MakeDelegate<Func<TooltipContent>>(_beaverTooltip,__instance),_beaverClass,
          ()=>{var workplace=Workplace();if(workplace.NativeBeaverAllowed)workplace.Disable();setBeaver();},beaverState),
        SliderToggleItem.CreateBlockable(MakeDelegate<Func<TooltipContent>>(_botTooltip,__instance),_botClass,
          ()=>{var workplace=Workplace();workplace.Ui.SelectBot(workplace);},
          ()=>{var state=botState();return state==SliderToggleState.Active&&Workplace().ReactorMode?SliderToggleState.None:state;}),
        SliderToggleItem.CreateBlockable(()=>{var workplace=Workplace();return workplace.Ui.ReactorTooltip(workplace);},_botClass,
          ()=>{var workplace=Workplace();workplace.Ui.SelectReactor(workplace);},
          ()=>{var workplace=Workplace();tint.Apply(workplace.Ui.IconTint);return workplace.Ui.ReactorState(workplace);}),
      };
      var factory=(SliderToggleFactory)_toggleFactory.GetValue(__instance);
      var slider=string.IsNullOrWhiteSpace(toggleBindingKey)?factory.Create(parent,items):factory.CreateBindable(parent,toggleBindingKey,items);
      tint.Icon=ThirdIcon(slider);
      _toggleSlider.SetValue(__instance,slider);
    }

    private static void DistrictCenterFragmentPostfix(object __instance) {
      ((SliderToggle)_fragmentSlider.GetValue(__instance)).Root.RemoveFromHierarchy();
      DistrictDefaultWorkerType Native()=>(DistrictDefaultWorkerType)_fragmentDefault.GetValue(__instance);
      ReactorBotDistrictDefault Reactor()=>Native().GetComponent<ReactorBotDistrictDefault>()
        ??throw new InvalidOperationException(Tag+"district centre without a Reactor Bot district default");
      var beaver=WorkerTypeHelper.BeaverWorkerType;
      var bot=WorkerTypeHelper.BotWorkerType;
      var tint=new LazyTint();
      var items=new[] {
        SliderToggleItem.Create(MakeDelegate<Func<string>>(_fragmentBeaverTooltip,__instance),_beaverClass,
          ()=>{Reactor().Set(false);Native().SetWorkerType(beaver);},()=>Native().WorkerType==beaver),
        SliderToggleItem.Create(MakeDelegate<Func<string>>(_fragmentBotTooltip,__instance),_botClass,
          ()=>{Reactor().Set(false);Native().SetWorkerType(bot);},()=>Native().WorkerType==bot&&!Reactor().ReactorMode),
        SliderToggleItem.Create(()=>Reactor().Ui.DisplayName,_botClass,()=>Reactor().Set(true),
          ()=>{var reactor=Reactor();tint.Apply(reactor.Ui.IconTint);return reactor.ReactorMode;}),
      };
      var slider=((SliderToggleFactory)_fragmentFactory.GetValue(__instance)).Create((VisualElement)_fragmentRoot.GetValue(__instance),items);
      tint.Icon=ThirdIcon(slider);
      _fragmentSlider.SetValue(__instance,slider);
    }

    // The third button's icon (each SliderToggleButton has one Image "Icon").
    private static VisualElement ThirdIcon(SliderToggle slider) {
      var icons=slider.Root.Query<Image>("Icon").ToList();
      if(icons.Count!=3)throw new InvalidOperationException(Tag+$"expected three worker-type icons, found {icons.Count}");
      return icons[2];
    }

    // The bot icon tinted with the Reactor Bot window colour, applied on the
    // first update of the toggle (after loading).
    private sealed class LazyTint {
      public VisualElement Icon;
      private bool _applied;
      public void Apply(Color color) {
        if(_applied)return;
        Icon.style.unityBackgroundImageTintColor=new StyleColor(color);
        _applied=true;
      }
    }

    private static bool UpdateUnemployedStatePrefix(Worker worker, HashSet<Worker> ____unemployed) {
      if(!ReactorBotWorker.IsReactorBot(worker))return true;
      ____unemployed.Remove(worker);
      return false;
    }

    // The mode comes from the workplace's own component (every workplace has
    // one, decorated on WorkplaceWorkerType); no static state.
    private static bool IsReactor(WorkplacePriority workplace)=>workplace.GetComponent<ReactorBotWorkplace>().ReactorMode;

    private static void HighestUnderstaffedPostfix(PriorityOrderedWorkplaces __instance, ref WorkplacePriority __result) {
      if(!__result||!IsReactor(__result))return;
      __result=null;
      foreach(var workplace in Ordered(__instance))
        if(workplace.Workplace.Understaffed&&!IsReactor(workplace)) {__result=workplace;return;}
    }

    private static void LowestStaffedPostfix(PriorityOrderedWorkplaces __instance, ref WorkplacePriority __result) {
      if(!__result||!IsReactor(__result))return;
      __result=null;
      var ordered=Ordered(__instance);
      for(var i=ordered.Count-1;i>=0;i--) {
        var workplace=ordered[i];
        if(workplace.Workplace.NumberOfAssignedWorkers>0&&!IsReactor(workplace)) {__result=workplace;return;}
      }
    }

    // SortedList<,>.Values, in key (priority) order (it implements IList<TValue>, not the non-generic IList).
    private static IList<WorkplacePriority> Ordered(PriorityOrderedWorkplaces instance)=>(IList<WorkplacePriority>)_orderedValues.GetValue(_orderedWorkplaces.GetValue(instance));

    private static void SetWorkerTypeToDistrictPrefix(bool ____wasSet, out bool __state) {__state=____wasSet;}

    private static void SetWorkerTypeToDistrictPostfix(WorkplaceWorkerType __instance, DistrictCenter districtCenter, bool __state) {
      if(__state||!districtCenter)return;
      var district=districtCenter.GetComponent<ReactorBotDistrictDefault>();
      if(!district||!district.ReactorMode)return;
      var workplace=ReactorBotWorkplaceUi.Of(__instance);
      if(workplace.Unlocked)workplace.Enable();
    }

    private static T MakeDelegate<T>(MethodInfo method, object instance) where T : System.Delegate=>(T)method.CreateDelegate(typeof(T),instance);

    private static bool Same(MethodBase a, MethodBase b)=>a.Module==b.Module&&a.MetadataToken==b.MetadataToken;

    private static void Require(bool condition, string message) {
      if(!condition)throw new InvalidOperationException(Tag+message+"; recheck the 1.1.2.8 contract");
    }

    private static Type Internal(Type anchor, string name)=>anchor.Assembly.GetType(name)
      ??throw new InvalidOperationException(Tag+$"{name} not found in {anchor.Assembly.GetName().Name}; recheck the 1.1.2.8 contract");

    private static MethodInfo Method(Type type, string name, params Type[] parameters) {
      var method=type.GetMethod(name,All,null,parameters,null);
      Require(method!=null,$"{type.Name}.{name}({string.Join(", ",parameters.Select(p=>p.Name))}) not found");
      return method;
    }

    private static MethodInfo Returning(Type type, string name, Type returnType) {
      var method=Method(type,name);
      Require(method.ReturnType==returnType&&!method.IsStatic,$"{type.Name}.{name} no longer returns {returnType.Name}");
      return method;
    }

    private static FieldInfo Field(Type type, string name, Type fieldType) {
      var field=type.GetField(name,All);
      Require(field!=null&&field.FieldType==fieldType,$"{type.Name}.{name} ({fieldType.Name}) not found");
      return field;
    }

    private static string StaticString(Type type, string name) {
      var field=type.GetField(name,All);
      Require(field!=null&&field.IsStatic&&field.FieldType==typeof(string),$"{type.Name}.{name} (static string) not found");
      return (string)field.GetValue(null);
    }
  }
}
#endif
