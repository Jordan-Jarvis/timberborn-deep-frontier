using Timberborn.GameFactionSystem;

namespace DeepFrontier.Scripts {
  // Deep Frontier's gameplay content is authored for Iron Teeth only: its
  // needs (Irradiation, Reactor Bot needs, studies) and goods are appended to
  // the Iron Teeth NeedCollection and GoodCollection. The mod still loads for
  // every faction, and native NeedManager/GoodService hold only the current
  // faction's needs and goods, so a system that is decorated on a
  // faction-agnostic spec (BeaverSpec, BotSpec, Stockpile) or that adds
  // content to a new game asks this one rule before it touches that content.
  // Iron Teeth stays strict: missing Iron Teeth data still fails there.
  //
  // Native FactionService.Load sets Current from the save or the new-game
  // configuration before any entity is created (SingletonLifecycleService
  // loads every singleton, then WorldEntitiesLoader), so components may ask
  // from Awake on. It is bound in the Game context only.
  internal static class DeepFrontierFaction {
    public const string Id = "IronTeeth";

    public static bool Applies(FactionService factions) => factions.Current.Id == Id;
  }
}
