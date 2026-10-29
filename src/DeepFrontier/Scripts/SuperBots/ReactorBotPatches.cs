#if !UNITY_EDITOR
using System;
using HarmonyLib;
using Timberborn.BaseComponentSystem;
using Timberborn.DeteriorationSystem;
using Timberborn.GameDistrictsUI;
using Timberborn.ModManagerScene;
using Timberborn.WalkingSystem;
using UnityEngine;

namespace DeepFrontier.Scripts.SuperBots {
  // Why Harmony (Timberborn 1.1.2.8, decompiled):
  // - Speed: WalkerSpeedManager.Tick sets _baseSpeed from the template
  //   (BaseWalkingSpeed / BaseSlowedSpeed) and _bonusMultiplier from the
  //   MovementSpeed bonus, which BonusTypes/MovementSpeed clamps at 2.0, so a
  //   per-bot x4 has no native route. The postfix scales _baseSpeed, which
  //   both GetWalkerBaseSpeed and GetWalkerSpeedAtCurrentPosition use.
  // - Lifespan: Deteriorable has no rate API (see Workforce/BotWear.cs). The
  //   prefix gives back (1 - 1/L) of everything this tick removes: the native
  //   tick plus BotWearDeteriorationPatch's (M - 1) extra ticks; it removes
  //   the unplated extra (P - 1) / L. All terms are additive on the same
  //   field, so the order of the two prefixes does not matter. Net wear per
  //   tick: (M + P - 1) / L native ticks.
  // - Tint: native CitizenTint.UpdateTint is the only CharacterTint writer
  //   for citizens; it runs on district assignment and renames. The postfix
  //   reapplies the Reactor Bot tint unless a colour name won.
  // Every IModStarter in the mod assembly runs at mod start (ModCodeStarter).
  internal sealed class ReactorBotModStarter : IModStarter {
    public void StartMod(IModEnvironment modEnvironment) {
      Require(AccessTools.Method(typeof(WalkerSpeedManager),nameof(WalkerSpeedManager.Tick)),"WalkerSpeedManager.Tick");
      Require(AccessTools.Field(typeof(WalkerSpeedManager),"_baseSpeed"),"WalkerSpeedManager._baseSpeed");
      Require(AccessTools.Method(typeof(Deteriorable),nameof(Deteriorable.Tick)),"Deteriorable.Tick");
      Require(AccessTools.Field(typeof(Deteriorable),"_currentDeterioration"),"Deteriorable._currentDeterioration");
      Require(AccessTools.Field(typeof(Deteriorable),"_fixedDeltaTimeInDays"),"Deteriorable._fixedDeltaTimeInDays");
      var tint=AccessTools.Method(typeof(CitizenTint),nameof(CitizenTint.UpdateTint),Type.EmptyTypes);
      Require(tint,"CitizenTint.UpdateTint()");
      if(NativeIl.Inlinable(tint))throw new InvalidOperationException($"Timberborn 1.1.2.8 contract changed: CitizenTint.UpdateTint is inlinable (IL {NativeIl.Size(tint)} bytes)");
      var harmony=new Harmony("DeepFrontier.ReactorBots");
      harmony.CreateClassProcessor(typeof(ReactorBotSpeedPatch)).Patch();
      harmony.CreateClassProcessor(typeof(ReactorBotLifespanPatch)).Patch();
      harmony.CreateClassProcessor(typeof(ReactorBotTintPatch)).Patch();
      Debug.Log("[DeepFrontier] Reactor Bot patches applied (speed, lifespan, tint).");
    }

    private static void Require(object member, string name) {
      if(member==null)throw new InvalidOperationException($"Timberborn 1.1.2.8 contract changed: {name} not found");
    }
  }

  [HarmonyPatch(typeof(WalkerSpeedManager),nameof(WalkerSpeedManager.Tick))]
  internal static class ReactorBotSpeedPatch {
    private static void Postfix(WalkerSpeedManager __instance,ref float ____baseSpeed) {
      var bot=__instance.GetComponent<ReactorBot>();
      if(bot&&bot.IsReactor)____baseSpeed*=bot.SpeedMultiplier;
    }
  }

  [HarmonyPatch(typeof(Deteriorable),nameof(Deteriorable.Tick))]
  internal static class ReactorBotLifespanPatch {
    private static void Prefix(Deteriorable __instance,ref float ____currentDeterioration,float ____fixedDeltaTimeInDays) {
      if(____currentDeterioration<=0f)return;
      var bot=__instance.GetComponent<ReactorBot>();
      if(!bot||!bot.IsReactor)return;
      var wear=__instance.GetComponent<BotWear>();
      var workplace=wear&&wear.Wearing?wear.Multiplier:1f;   // what native + BotWearDeteriorationPatch remove
      var l=bot.LifespanMultiplier;
      ____currentDeterioration+=____fixedDeltaTimeInDays*(workplace*(1f-1f/l)-(bot.PlatingWearMultiplier-1f)/l);
    }
  }

  [HarmonyPatch(typeof(CitizenTint),nameof(CitizenTint.UpdateTint))]
  internal static class ReactorBotTintPatch {
    private static void Postfix(BaseComponent __instance)=>__instance.GetComponent<ReactorBot>()?.ApplyTint();
  }
}
#endif
