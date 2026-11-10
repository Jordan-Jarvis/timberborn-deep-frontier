using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace DeepFrontier.ModdableFluidsMigration {
  /// <summary>One stage of a saved Moddable Weathers cycle (11.0.0 Historical/WeatherCycleStage), the fields the import reads.</summary>
  public sealed class ModdableWeathersStage {
    public int Index { get; }
    public bool IsBenign { get; }
    public string WeatherId { get; }
    public int Days { get; }

    public ModdableWeathersStage(int index, bool isBenign, string weatherId, int days) {
      Index = index; IsBenign = isBenign; WeatherId = weatherId; Days = days;
    }
  }

  /// <summary>
  /// The radioactive tide of a save played under the shipped Deep Frontier with Moddable Weathers 11.0.0. There Deep
  /// Frontier's optional bridge (Scripts/RadioactiveTide/ModdableWeathers) registers the tide as the Moddable Weathers
  /// weather <c>RadioactiveTideWeather</c> and saves nothing of its own: neither <c>DeepFrontier.RadioactiveTide</c> nor
  /// <c>DeepFrontier.RadioactiveTideSettings</c> is written (RadioactiveTideConfigurator binds neither service while Moddable
  /// Weathers is loaded, and a save holds only the singletons bound when it was made). The save keeps instead:
  /// <list type="bullet">
  /// <item>the settings in Moddable Weathers' singleton <c>ModdableWeatherSettingsService</c>, property <c>Settings</c>: one
  /// JSON object with an entry per settings type, keyed by its full name (BaseWeatherSettingsService.SerializeSettings);
  /// the bridge's is <see cref="BridgeSettingsType"/>, its [Description] properties Enabled, StartCycle (= cycles without
  /// tide + 1), ChancePercent, MinDurationDays and MaxDurationDays (IBaseWeatherSettings.DefaultSerialize);</item>
  /// <item>the chosen stages in Moddable Weathers' singleton <c>WeatherHistoryRegistry</c>, list <c>WeatherCycles</c>: entry
  /// i is cycle i (entry 0 the empty cycle 0), each one WeatherCycle as Newtonsoft JSON with its Stages (Index, IsBenign,
  /// WeatherId, WeatherModifierIds, Days);</item>
  /// <item>the game's position in the native <c>GameCycleService</c> (Cycle, CycleDay).</item>
  /// </list>
  /// <see cref="Read"/> turns that into the state Deep Frontier's own tide would have saved, as Moddable Fluids' Moddable
  /// Weathers adapter derives it from the same history (FluidTideModdableWeathersService.Derive), so the adapter's load
  /// check accepts the import: the last tide is the latest non-benign stage naming the tide's weather in this or an earlier
  /// cycle, with its days; the cycle's tide is Moddable Weathers' current or next hazardous stage in this cycle (the
  /// stage WeatherCycleService.UpdateReferences finds for the cycle day, else the next one GetNextWeatherInCycle finds;
  /// their rules are transcribed below, quirks included). Every value is required with its type; nothing is defaulted.
  /// </summary>
  public sealed class RadioactiveTideModdableWeathersSave {
    public const string SettingsSingleton = "ModdableWeatherSettingsService";
    public const string SettingsProperty = "Settings";
    public const string HistorySingleton = "WeatherHistoryRegistry";
    public const string HistoryList = "WeatherCycles";
    /// <summary>The full name of the bridge's RadioactiveTideModdableWeatherSettings, its key in Moddable Weathers' settings.</summary>
    public const string BridgeSettingsType = "DeepFrontier.RadioactiveTideModdableWeathers.RadioactiveTideModdableWeatherSettings";
    public const string Source = "this save's Moddable Weathers settings (Deep Frontier's Moddable Weathers radioactive tide)";

    public RadioactiveTideSavedState State { get; }
    public bool Enabled { get; }
    /// <summary>The earliest cycle with a tide, as the bridge keeps it; cycles without tide = StartCycle - 1.</summary>
    public int StartCycle { get; }
    public int ChancePercent { get; }
    public int MinDurationDays { get; }
    public int MaxDurationDays { get; }
    public int CyclesWithoutTide => StartCycle - 1;

    private RadioactiveTideModdableWeathersSave(RadioactiveTideSavedState state, bool enabled, int startCycle, int chancePercent, int minDurationDays, int maxDurationDays) {
      State = state; Enabled = enabled; StartCycle = startCycle; ChancePercent = chancePercent; MinDurationDays = minDurationDays; MaxDurationDays = maxDurationDays;
    }

    /// <summary>
    /// The save's radioactive tide as the bridge kept it, or null when its Moddable Weathers settings hold no entry for the
    /// bridge (no Moddable Weathers, or Deep Frontier never ran with it): the save's own keys apply then.
    /// </summary>
    /// <param name="weatherId">The tide's native weather ID, which the bridge's weather used as its Moddable Weathers ID.</param>
    /// <param name="hasOwnTideKeys">Whether the save also holds DeepFrontier.RadioactiveTide or DeepFrontier.RadioactiveTideSettings.</param>
    /// <param name="settingsJson">ModdableWeatherSettingsService's Settings, or null when the save has no such singleton.</param>
    /// <param name="weatherCycles">WeatherHistoryRegistry's WeatherCycles, or null when the save has no such singleton.</param>
    /// <param name="gameCycle">GameCycleService's Cycle and CycleDay, or null when the save has no such singleton.</param>
    public static RadioactiveTideModdableWeathersSave Read(string weatherId, bool hasOwnTideKeys, string settingsJson, IReadOnlyList<string> weatherCycles,
        (int Cycle, int Day)? gameCycle) {
      if (string.IsNullOrEmpty(weatherId)) throw new ArgumentException("The radioactive tide's weather ID is required", nameof(weatherId));
      JObject bridge = settingsJson == null ? null : BridgeSettings(settingsJson);
      if (bridge == null) {
        if (weatherCycles != null && ReadHistory(weatherCycles, weatherId).Any(c => c.Any(s => s.WeatherId == weatherId)))
          throw new InvalidOperationException("This save's Moddable Weathers history (" + HistorySingleton + ") holds radioactive tides (" + weatherId + "), but its Moddable Weathers settings ("
            + SettingsSingleton + ") hold no " + BridgeSettingsType + ": the save no longer has the radioactive tide settings it was played with");
        return null;
      }
      if (hasOwnTideKeys)
        throw new InvalidOperationException("This save holds both Deep Frontier's own radioactive tide keys (DeepFrontier.RadioactiveTide or DeepFrontier.RadioactiveTideSettings) and the radioactive tide settings of its Moddable Weathers weather ("
          + BridgeSettingsType + "); one game never writes both");
      if (weatherCycles == null)
        throw new InvalidOperationException("This save holds the radioactive tide settings of Deep Frontier's Moddable Weathers weather but no Moddable Weathers history (" + HistorySingleton + ")");
      if (gameCycle == null) throw new InvalidOperationException("This save has no GameCycleService (Cycle, CycleDay); the radioactive tide in Moddable Weathers' history cannot be placed");
      var state = StateAt(ReadHistory(weatherCycles, weatherId), weatherId, gameCycle.Value.Cycle, gameCycle.Value.Day);
      return new RadioactiveTideModdableWeathersSave(state, Bool(bridge, "Enabled", BridgeSettingsType), Int(bridge, "StartCycle", BridgeSettingsType),
        Int(bridge, "ChancePercent", BridgeSettingsType), Int(bridge, "MinDurationDays", BridgeSettingsType), Int(bridge, "MaxDurationDays", BridgeSettingsType));
    }

    public override string ToString() =>
      (Enabled ? "on, from cycle " + StartCycle + ", " + ChancePercent + "%, " + MinDurationDays + "-" + MaxDurationDays + " days" : "off")
      + "; " + (State.LastTideCycle == 0 ? "no tide yet" : (State.CurrentCycleIsTide ? "this cycle's tide" : "last tide") + " in cycle " + State.LastTideCycle + " for " + State.LastTideDuration + " days");

    // The bridge's entry in ModdableWeatherSettingsService's Settings, or null.
    private static JObject BridgeSettings(string json) {
      var root = Parse(json, SettingsSingleton + "." + SettingsProperty);
      if (!root.TryGetValue(BridgeSettingsType, out var entry)) return null;
      return entry as JObject ?? throw new InvalidOperationException("Moddable Weathers' saved settings for " + BridgeSettingsType + " are " + entry.Type + ", not an object");
    }

    /// <summary>WeatherHistoryRegistry's cycles, entry i being cycle i, each with its stages in saved order.</summary>
    public static IReadOnlyList<IReadOnlyList<ModdableWeathersStage>> ReadHistory(IReadOnlyList<string> weatherCycles, string weatherId) {
      if (weatherCycles == null) throw new ArgumentNullException(nameof(weatherCycles));
      var history = new List<IReadOnlyList<ModdableWeathersStage>>(weatherCycles.Count);
      for (int i = 0; i < weatherCycles.Count; i++) {
        string what = HistorySingleton + "." + HistoryList + "[" + i + "]";
        var cycle = Parse(weatherCycles[i], what);
        int number = Int(cycle, "Cycle", what);
        if (number != i) throw new InvalidOperationException("Moddable Weathers' history holds cycle " + number + " at entry " + i + "; entry i is cycle i");
        if (!cycle.TryGetValue("Stages", out var stagesToken) || !(stagesToken is JArray stages))
          throw new InvalidOperationException(what + " has no Stages list");
        var list = new List<ModdableWeathersStage>(stages.Count);
        foreach (var stageToken in stages) {
          string where = what + " stage " + list.Count;
          var stage = stageToken as JObject ?? throw new InvalidOperationException(where + " is " + stageToken.Type + ", not an object");
          var read = new ModdableWeathersStage(Int(stage, "Index", where), Bool(stage, "IsBenign", where), String(stage, "WeatherId", where), Int(stage, "Days", where));
          if (read.Index < 0 || read.Days < 0) throw new InvalidOperationException(where + " has index " + read.Index + " and lasts " + read.Days + " days");
          if (read.IsBenign && read.WeatherId == weatherId) throw new InvalidOperationException(where + " is a benign stage of the radioactive tide (" + weatherId + "), which is hazardous");
          list.Add(read);
        }
        history.Add(list);
      }
      return history;
    }

    private static RadioactiveTideSavedState StateAt(IReadOnlyList<IReadOnlyList<ModdableWeathersStage>> history, string weatherId, int cycle, int cycleDay) {
      int last = history.Count - 1;
      if (cycle < 1 || cycle > last)
        throw new InvalidOperationException("The game is in cycle " + cycle + ", outside Moddable Weathers' history (cycles 1 to " + last + ")");
      // The last tide: the latest non-benign stage naming the tide's weather in this or an earlier cycle (the last such stage of its cycle).
      int lastCycle = 0, lastDays = 0;
      for (int c = cycle; c >= 1 && lastCycle == 0; c--)
        foreach (var stage in history[c])
          if (!stage.IsBenign && stage.WeatherId == weatherId) { lastCycle = c; lastDays = stage.Days; }
      var current = CurrentOrNextHazardous(history[cycle], cycle, cycleDay);
      return new RadioactiveTideSavedState(current != null && current.WeatherId == weatherId, lastCycle, lastDays);
    }

    /// <summary>
    /// Moddable Weathers 11.0.0's current or next hazardous stage in this cycle (Cycles/WeatherCycleService):
    /// UpdateReferences takes the first stage, in list order, whose last day (stages laid end to end from day 1) is at or
    /// after the cycle day, else the last stage; GetCurrentOrNextWeatherInThisCycle returns it when it is hazardous, else
    /// GetNextWeatherInCycle the first hazardous stage at list positions from the current stage's Index + 1 on, and only
    /// when the current stage lasts more than 0 days. A stage is hazardous by its saved IsBenign: Moddable Weathers
    /// generates a hazardous stage only from its hazardous weathers.
    /// </summary>
    private static ModdableWeathersStage CurrentOrNextHazardous(IReadOnlyList<ModdableWeathersStage> stages, int cycle, int cycleDay) {
      if (stages.Count == 0) throw new InvalidOperationException("Moddable Weathers' history has no stages for the current cycle " + cycle);
      int end = 0, i;
      for (i = 0; i < stages.Count; i++) {
        int start = end + 1;
        end = start + stages[i].Days - 1;
        if (end >= cycleDay) break;
      }
      if (i >= stages.Count) i = stages.Count - 1;
      var current = stages[i];
      if (!current.IsBenign) return current;
      for (int j = current.Index + 1; j < stages.Count; j++)
        if (current.Days > 0 && !stages[j].IsBenign) return stages[j];
      return null;
    }

    private static JObject Parse(string json, string what) {
      if (json == null) throw new InvalidOperationException(what + " is missing");
      try {
        using (var reader = new JsonTextReader(new StringReader(json)) { DateParseHandling = DateParseHandling.None }) {
          var token = JToken.ReadFrom(reader);
          if (reader.Read()) throw new InvalidOperationException(what + " continues after its JSON value");
          return token as JObject ?? throw new InvalidOperationException(what + " is " + token.Type + ", not a JSON object");
        }
      } catch (JsonException e) {
        throw new InvalidOperationException(what + " is not valid JSON: " + e.Message, e);
      }
    }

    private static JToken Required(JObject data, string key, string what) =>
      data.TryGetValue(key, out var token) ? token : throw new InvalidOperationException(what + " has no " + key);

    private static int Int(JObject data, string key, string what) {
      var token = Required(data, key, what);
      if (token.Type != JTokenType.Integer) throw new InvalidOperationException(what + "." + key + " is " + token.Type + ", not an integer");
      long value = token.Value<long>();
      if (value < int.MinValue || value > int.MaxValue) throw new InvalidOperationException(what + "." + key + " (" + value + ") is beyond an int");
      return (int)value;
    }

    private static bool Bool(JObject data, string key, string what) {
      var token = Required(data, key, what);
      if (token.Type != JTokenType.Boolean) throw new InvalidOperationException(what + "." + key + " is " + token.Type + ", not a boolean");
      return token.Value<bool>();
    }

    private static string String(JObject data, string key, string what) {
      var token = Required(data, key, what);
      if (token.Type != JTokenType.String || ((string)token).Length == 0) throw new InvalidOperationException(what + "." + key + " is not a weather ID");
      return (string)token;
    }
  }
}
