using System.Collections;
using System.IO.Compression;
using System.Reflection;
using System.Runtime.Loader;
using System.Text;
using System.Text.Json;
using ModdableFluids;
using MoreFluids;

internal static partial class HarnessExtensions {
  static partial void RunMoreFluids(Action<bool, string> check, Action<string, Action> scenario, string managed, string specification, Dictionary<string, object> observations)
    => MoreFluidsContent.Run(check, scenario, managed, specification, observations);
}

/// <summary>
/// More Fluids' game data (src/MoreFluids/Data) against the installed game: every blueprint against the game's own spec
/// types (validated first on every vanilla blueprint), the approved design numbers, faction goods, collections, source
/// templates, localization, tide fog and art paths; and the healing exposure rule.
/// </summary>
internal static class MoreFluidsContent {
  private static readonly string[] Factions = { "Folktails", "IronTeeth" };
  /// <summary>Model, icon and sprite paths the art agent delivers (docs/more-fluids-design.md, Art).</summary>
  private static readonly string[] ArtPaths = BuildArtPaths();

  private static string[] BuildArtPaths() {
    var paths = new List<string>();
    foreach (var building in new[] { "MoreFluidsFluidExtractor", "MoreFluidsDesalinator", "MoreFluidsHealingWell" }) {
      string folder = "Buildings/Water/" + building + "/" + building;
      foreach (var faction in Factions) { paths.Add(folder + "." + faction + ".Model"); paths.Add(folder + "." + faction + ".ConstructionStage0.Model"); }
      paths.Add(folder + "Icon");
    }
    foreach (var map in new[] { "MoreFluidsHealingSpring", "MoreFluidsGeyser" }) { paths.Add("MapEditor/Objects/" + map + "/" + map + ".Model"); paths.Add("MapEditor/Objects/" + map + "/" + map + "Icon"); }
    foreach (var tide in new[] { "MoreFluidsCoffeeTide", "MoreFluidsSaltTide" })
      foreach (var part in new[] { "Icon", "Progress", "Notification" }) paths.Add("Sprites/Weather/" + tide + part);
    return paths.ToArray();
  }

  private sealed class Corpus {
    public required string Root, Data;
    public required Dictionary<string, JsonElement> Vanilla, Ours;   // relative path without ".json" -> document
    public required HashSet<string> VanillaLoc;
    public required List<(string Id, string Text)> Loc;
  }

  internal static void Run(Action<bool, string> check, Action<string, Action> scenario, string managed, string specification, Dictionary<string, object> observations) {
    Func<AssemblyLoadContext, AssemblyName, Assembly?> resolver = (context, name) => {
      string path = Path.Combine(managed, name.Name + ".dll");
      return File.Exists(path) ? context.LoadFromAssemblyPath(path) : null;
    };
    AssemblyLoadContext.Default.Resolving += resolver;
    try {
      var corpus = Load(managed, specification);
      Schema(check, scenario, managed, corpus, observations);
      Content(check, scenario, corpus, observations);
      Exposure(check, scenario);
    } finally { AssemblyLoadContext.Default.Resolving -= resolver; }
  }

  private static Corpus Load(string managed, string specification) {
    var dir = new DirectoryInfo(Path.GetDirectoryName(Path.GetFullPath(specification))!);
    while (dir != null && !File.Exists(Path.Combine(dir.FullName, "src", "MoreFluids", "manifest.json"))) dir = dir.Parent;
    string root = dir?.FullName ?? throw new DirectoryNotFoundException("No repository root above " + specification);
    string data = Path.Combine(root, "src", "MoreFluids", "Data");
    string modding = Path.GetFullPath(Path.Combine(managed, "..", "StreamingAssets", "Modding"));
    var vanilla = new Dictionary<string, JsonElement>(StringComparer.Ordinal);
    using (var zip = ZipFile.OpenRead(Path.Combine(modding, "Blueprints.zip")))
      foreach (var entry in zip.Entries.Where(e => e.FullName.EndsWith(".blueprint.json", StringComparison.Ordinal))) {
        using var reader = new StreamReader(entry.Open(), Encoding.UTF8);
        vanilla[entry.FullName.Replace('\\', '/')[..^5]] = JsonDocument.Parse(reader.ReadToEnd()).RootElement.Clone();
      }
    var vanillaLoc = new HashSet<string>(StringComparer.Ordinal);
    using (var zip = ZipFile.OpenRead(Path.Combine(modding, "Localizations.zip"))) {
      var entry = zip.Entries.Single(e => e.Name == "enUS.csv");
      using var reader = new StreamReader(entry.Open(), Encoding.UTF8);
      foreach (var row in Csv(reader.ReadToEnd()).Skip(1)) vanillaLoc.Add(row[0]);
    }
    var ours = new Dictionary<string, JsonElement>(StringComparer.Ordinal);
    foreach (var file in Directory.EnumerateFiles(data, "*.blueprint.json", SearchOption.AllDirectories))
      ours[Path.GetRelativePath(data, file).Replace('\\', '/')[..^5]] = JsonDocument.Parse(File.ReadAllText(file)).RootElement.Clone();
    var loc = Csv(File.ReadAllText(Path.Combine(data, "Localizations", "enUS.csv"))).ToList();
    if (!loc[0].SequenceEqual(new[] { "ID", "Text", "Comment" }) || loc.Skip(1).Any(r => r.Length != 3)) throw new InvalidDataException("More Fluids enUS.csv must have the ID,Text,Comment columns on every row");
    return new Corpus { Root = root, Data = data, Vanilla = vanilla, Ours = ours, VanillaLoc = vanillaLoc, Loc = loc.Skip(1).Select(r => (r[0], r[1])).ToList() };
  }

  // RFC 4180 rows, as the game's CSV reader takes them.
  private static IEnumerable<string[]> Csv(string text) {
    var row = new List<string>(); var cell = new StringBuilder(); bool quoted = false;
    for (int i = 0; i < text.Length; i++) {
      char c = text[i];
      if (quoted) {
        if (c == '"' && i + 1 < text.Length && text[i + 1] == '"') { cell.Append('"'); i++; }
        else if (c == '"') quoted = false;
        else cell.Append(c);
      } else if (c == '"') quoted = true;
      else if (c == ',') { row.Add(cell.ToString()); cell.Clear(); }
      else if (c == '\n' || c == '\r') {
        if (c == '\r' && i + 1 < text.Length && text[i + 1] == '\n') i++;
        row.Add(cell.ToString()); cell.Clear(); yield return row.ToArray(); row.Clear();
      } else cell.Append(c);
    }
    if (cell.Length > 0 || row.Count > 0) { row.Add(cell.ToString()); yield return row.ToArray(); }
  }

  // ---------- Blueprint schema: the game's ComponentSpec types and their [Serialize] properties ----------

  private sealed class Schema_ {
    public readonly Dictionary<string, Type> Specs = new(StringComparer.Ordinal);
    public Type? ComponentSpec;
  }

  private static void Schema(Action<bool, string> check, Action<string, Action> scenario, string managed, Corpus corpus, Dictionary<string, object> observations) {
    scenario("More Fluids blueprints match the game's spec types (the same check passes on every vanilla blueprint)", () => {
      var schema = new Schema_();
      var loaded = AppDomain.CurrentDomain.GetAssemblies().Where(a => !a.IsDynamic).ToDictionary(a => a.GetName().Name!, a => a, StringComparer.Ordinal);
      var assemblies = new List<Assembly>();
      foreach (var file in Directory.EnumerateFiles(managed, "Timberborn.*.dll").OrderBy(f => f, StringComparer.Ordinal)) {
        string name = Path.GetFileNameWithoutExtension(file);
        assemblies.Add(loaded.TryGetValue(name, out var a) ? a : AssemblyLoadContext.Default.LoadFromAssemblyPath(file));
      }
      assemblies.Add(typeof(MoreFluidsLiquids).Assembly);
      schema.ComponentSpec = assemblies.Single(a => a.GetName().Name == "Timberborn.BlueprintSystem").GetType("Timberborn.BlueprintSystem.ComponentSpec", true)!;
      var unloadable = new List<string>();
      void AddSpecs(Schema_ target, Assembly assembly) {
        Type?[] types;
        try { types = assembly.GetTypes(); }
        catch (ReflectionTypeLoadException e) { types = e.Types; unloadable.Add(assembly.GetName().Name + ": " + e.LoaderExceptions.Length + " types"); }
        foreach (var type in types) {
          if (type == null || !type.IsClass || type.IsAbstract || !schema.ComponentSpec.IsAssignableFrom(type)) continue;
          foreach (var key in new[] { type.Name }.Concat(Aliases(type))) {
            if (target.Specs.TryGetValue(key, out var other) && other != type) throw new InvalidOperationException("Two spec types for key " + key + ": " + other.FullName + " and " + type.FullName);
            target.Specs[key] = type;
          }
        }
      }
      foreach (var assembly in assemblies) AddSpecs(schema, assembly);
      observations["moreFluidsSpecTypes"] = schema.Specs.Count;
      // Moddable Weathers' own spec types (the installed 11.0.0), for the ModdableWeatherSpecs blueprints alone: only that
      // optional mod reads them (without it the game logs their two unknown keys and never deserializes them).
      var weatherSchema = new Schema_ { ComponentSpec = schema.ComponentSpec };
      foreach (var (key, type) in schema.Specs) weatherSchema.Specs[key] = type;
      AddSpecs(weatherSchema, AssemblyLoadContext.Default.LoadFromAssemblyPath(ModdableWeathersAssembly(corpus.Root)));
      if (unloadable.Count > 0) observations["moreFluidsSpecAssembliesPartlyLoaded"] = unloadable.ToArray();
      var vanillaProblems = new List<string>();
      foreach (var (path, doc) in corpus.Vanilla) Blueprint(schema, doc, path, false, corpus, vanillaProblems);
      check(vanillaProblems.Count == 0, "The schema check rejects vanilla blueprints (" + vanillaProblems.Count + "): " + string.Join("; ", vanillaProblems.Take(8)));
      var problems = new List<string>();
      foreach (var (path, doc) in corpus.Ours)
        Blueprint(path.StartsWith("ModdableWeatherSpecs/", StringComparison.Ordinal) ? weatherSchema : schema, doc, path, corpus.Vanilla.ContainsKey(path), corpus, problems);
      check(problems.Count == 0, "More Fluids blueprint schema problems (" + problems.Count + "): " + string.Join("; ", problems));
      check(corpus.Ours.Count == 18, "More Fluids blueprint files (6 buildings, 2 map objects, 3 recipes, 3 collections, Sun, map-object materials, 2 Moddable Weathers specs): " + corpus.Ours.Count);
      observations["moreFluidsBlueprints"] = corpus.Ours.Keys.OrderBy(k => k, StringComparer.Ordinal).ToArray();
    });
  }

  /// <summary>The installed Moddable Weathers 11.0.0 assembly (Workshop item 3630523180), from this machine's tools/dev-environment.json.</summary>
  internal static string ModdableWeathersAssembly(string root) {
    using var environment = JsonDocument.Parse(File.ReadAllText(Path.Combine(root, "tools", "dev-environment.json")));
    string path = Path.Combine(environment.RootElement.GetProperty("workshopContent").GetString()!, "3630523180", "version-1.1", "ModdableWeathers.dll");
    if (!File.Exists(path)) throw new FileNotFoundException("Moddable Weathers 11.0.0 is not installed from the Workshop (item 3630523180); the More Fluids Moddable Weathers specs are checked against it", path);
    return path;
  }

  private static IEnumerable<string> Aliases(Type type) {
    var attribute = type.GetCustomAttributes(true).SingleOrDefault(a => a.GetType().Name == "SpecAliasAttribute");
    if (attribute == null) return Array.Empty<string>();
    return ((IEnumerable)attribute.GetType().GetProperty("Aliases")!.GetValue(attribute)!).Cast<string>().ToArray();
  }

  private static Dictionary<string, PropertyInfo> Serialized(Type type) {
    var result = new Dictionary<string, PropertyInfo>(StringComparer.Ordinal);
    for (var t = type; t != null && t != typeof(object); t = t.BaseType)
      foreach (var p in t.GetProperties(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly)) {
        var attribute = p.GetCustomAttributes(true).SingleOrDefault(a => a.GetType().FullName == "Timberborn.BlueprintSystem.SerializeAttribute");
        if (attribute == null || attribute.GetType().GetProperty("SourceName")!.GetValue(attribute) != null) continue;
        result.TryAdd(p.Name, p);
      }
    return result;
  }

  private static void PartialBlueprint(Schema_ schema, JsonElement doc, string where, Corpus corpus, List<string> problems) => Blueprint(schema, doc, where, true, corpus, problems);

  private static void Blueprint(Schema_ schema, JsonElement doc, string where, bool partial, Corpus corpus, List<string> problems) {
    if (doc.ValueKind != JsonValueKind.Object) { problems.Add(where + " is not an object"); return; }
    foreach (var spec in doc.EnumerateObject()) {
      if (spec.Name == "Children") { Children(schema, spec.Value, where, corpus, problems); continue; }
      if (!schema.Specs.TryGetValue(spec.Name, out var type)) { problems.Add(where + ": no game spec type " + spec.Name); continue; }
      Object(schema, spec.Value, type, where + "/" + spec.Name, partial, problems);
    }
  }

  private static void Children(Schema_ schema, JsonElement children, string where, Corpus corpus, List<string> problems) {
    if (children.ValueKind != JsonValueKind.Object) { problems.Add(where + "/Children is not an object"); return; }
    foreach (var child in children.EnumerateObject()) {
      if (child.Name.EndsWith("#nested", StringComparison.Ordinal)) {
        // A nested blueprint: its path, and optionally a partial blueprint modifying it.
        var props = child.Value.EnumerateObject().ToArray();
        if (!child.Value.TryGetProperty("BlueprintPath", out var path) || path.ValueKind != JsonValueKind.String || props.Any(p => p.Name != "BlueprintPath" && p.Name != "Modification")) {
          problems.Add(where + "/" + child.Name + " must hold BlueprintPath and optionally Modification"); continue;
        }
        string target = path.GetString()!;
        if (!corpus.Vanilla.ContainsKey(target) && !corpus.Ours.ContainsKey(target)) problems.Add(where + "/" + child.Name + ": no blueprint " + target);
        if (child.Value.TryGetProperty("Modification", out var modification)) PartialBlueprint(schema, modification, where + "/" + child.Name + "/Modification", corpus, problems);
      } else Blueprint(schema, child.Value, where + "/" + child.Name, false, corpus, problems);
    }
  }

  private static void Object(Schema_ schema, JsonElement value, Type type, string where, bool partial, List<string> problems) {
    if (value.ValueKind != JsonValueKind.Object) { problems.Add(where + " is not an object"); return; }
    var properties = Serialized(type);
    var seen = new HashSet<string>(StringComparer.Ordinal);
    foreach (var json in value.EnumerateObject()) {
      string name = json.Name;
      int modifier = name.IndexOf('#');
      if (modifier >= 0) {
        string suffix = name[modifier..];
        if (!partial || (suffix != "#append" && suffix != "#remove")) { problems.Add(where + ": modifier " + name + " outside a partial blueprint"); continue; }
        name = name[..modifier];
      }
      if (!properties.TryGetValue(name, out var property)) { problems.Add(where + ": " + type.Name + " has no serialized property " + name); continue; }
      seen.Add(name);
      Value(schema, json.Value, property.PropertyType, where + "." + name, partial, problems);
    }
    if (!partial)
      foreach (var missing in properties.Keys.Where(k => !seen.Contains(k))) problems.Add(where + ": missing " + type.Name + "." + missing);
  }

  // Inside a partial blueprint, nested objects are partial too; array elements are always whole values.
  private static void Value(Schema_ schema, JsonElement value, Type type, string where, bool partial, List<string> problems) {
    bool Is(JsonValueKind kind) { if (value.ValueKind == kind) return true; problems.Add(where + " should be " + kind + " (" + type.Name + "), is " + value.ValueKind); return false; }
    if (type == typeof(string)) { Is(JsonValueKind.String); return; }
    if (type == typeof(bool)) { if (value.ValueKind != JsonValueKind.True && value.ValueKind != JsonValueKind.False) problems.Add(where + " should be a bool"); return; }
    if (type == typeof(int) || type == typeof(long)) { if (Is(JsonValueKind.Number) && !value.TryGetInt64(out _)) problems.Add(where + " should be an integer"); return; }
    if (type == typeof(float) || type == typeof(double)) { Is(JsonValueKind.Number); return; }
    if (type.IsEnum) {
      if (!Is(JsonValueKind.String)) return;
      var names = Enum.GetNames(type);
      foreach (var part in value.GetString()!.Split(',').Select(p => p.Trim()))
        if (!names.Contains(part)) problems.Add(where + ": " + part + " is not a " + type.Name);
      return;
    }
    if (type.IsGenericType && type.GetGenericTypeDefinition().FullName == "System.Collections.Immutable.ImmutableArray`1") {
      if (!Is(JsonValueKind.Array)) return;
      int i = 0;
      foreach (var element in value.EnumerateArray()) Value(schema, element, type.GetGenericArguments()[0], where + "[" + i++ + "]", false, problems);
      return;
    }
    if (type.IsGenericType && type.GetGenericTypeDefinition().Name == "AssetRef`1") { Is(JsonValueKind.String); return; }
    if (type.Namespace == "UnityEngine") {
      string[]? fields = type.Name switch {
        "Vector2Int" or "Vector2" => new[] { "X", "Y" }, "Vector3Int" or "Vector3" => new[] { "X", "Y", "Z" }, "Color" => new[] { "r", "g", "b", "a" }, _ => null };
      if (fields == null) { problems.Add(where + ": unsupported Unity type " + type.FullName); return; }
      if (!Is(JsonValueKind.Object)) return;
      var names = value.EnumerateObject().Select(p => p.Name).ToArray();
      if (!names.OrderBy(n => n, StringComparer.Ordinal).SequenceEqual(fields.OrderBy(n => n, StringComparer.Ordinal))) problems.Add(where + ": " + type.Name + " needs exactly " + string.Join(", ", fields));
      foreach (var p in value.EnumerateObject())
        if (p.Value.ValueKind != JsonValueKind.Number || (type.Name.EndsWith("Int", StringComparison.Ordinal) && !p.Value.TryGetInt32(out _))) problems.Add(where + "." + p.Name + " should be a " + (type.Name.EndsWith("Int", StringComparison.Ordinal) ? "integer" : "number"));
      return;
    }
    if (Serialized(type).Count > 0) { Object(schema, value, type, where, partial, problems); return; }
    problems.Add(where + ": unsupported serialized type " + type.FullName);
  }

  // ---------- Content: design numbers, factions, collections, sources, localization, fog, art ----------

  private static JsonElement P(JsonElement e, params string[] path) {
    foreach (var p in path) e = e.GetProperty(p);
    return e;
  }

  private static void Content(Action<bool, string> check, Action<string, Action> scenario, Corpus corpus, Dictionary<string, object> observations) {
    var (registry, tides) = MoreFluidsScenarios.Freeze();

    scenario("More Fluids buildings carry the approved design: footprint, intake, cost, science, workers, power, toolbar", () => {
      void Building(string template, string folder, (int x, int y, int z) size, int baseZ, (int x, int y, int z)? input, (string good, int amount)[] cost, int science,
          int? workers, int power, int order, string[] recipes) {
        string path = folder + "/" + template + ".blueprint";
        if (!corpus.Ours.TryGetValue(path, out var bp)) { check(false, "Missing blueprint " + path); return; }
        check(P(bp, "TemplateSpec", "TemplateName").GetString() == template, path + " template name");
        var block = P(bp, "BlockObjectSpec");
        check(P(block, "Size", "X").GetInt32() == size.x && P(block, "Size", "Y").GetInt32() == size.y && P(block, "Size", "Z").GetInt32() == size.z
          && P(block, "Blocks").GetArrayLength() == size.x * size.y * size.z && P(block, "BaseZ").GetInt32() == baseZ, template + " footprint");
        var costs = P(bp, "BuildingSpec", "BuildingCost").EnumerateArray().Select(c => (P(c, "Id").GetString()!, P(c, "Amount").GetInt32())).ToArray();
        check(costs.SequenceEqual(cost), template + " cost: " + string.Join(", ", costs));
        check(P(bp, "BuildingSpec", "ScienceCost").GetInt32() == science, template + " science");
        check(bp.TryGetProperty("WorkplaceSpec", out var work) ? workers == P(work, "MaxWorkers").GetInt32() && P(work, "DefaultWorkers").GetInt32() == workers : workers == null, template + " workers");
        check(bp.TryGetProperty("MechanicalNodeSpec", out var node) ? P(node, "PowerInput").GetInt32() == power && P(node, "PowerOutput").GetInt32() == 0 : power == 0, template + " power");
        check(P(bp, "PlaceableBlockObjectSpec", "ToolGroupId").GetString() == "Water" && P(bp, "PlaceableBlockObjectSpec", "ToolOrder").GetInt32() == order
          && !P(bp, "PlaceableBlockObjectSpec", "DevModeTool").GetBoolean(), template + " toolbar");
        if (input is { } i) {
          var c = P(bp, "WaterInputSpec", "WaterInputCoordinates");
          check(P(c, "X").GetInt32() == i.x && P(c, "Y").GetInt32() == i.y && P(c, "Z").GetInt32() == i.z && P(bp, "WaterInputPipeSpec", "MaxDepth").GetInt32() == 6, template + " intake and pipe depth");
          check(!bp.TryGetProperty("ManufactoryWaterConsumerSpec", out _) && !bp.TryGetProperty("ManufactoryWaterContaminationConsumerSpec", out _),
            template + " must not carry a native water consumer: it draws through Moddable Fluids");
        }
        var ids = bp.TryGetProperty("ManufactorySpec", out var m) ? P(m, "ProductionRecipeIds").EnumerateArray().Select(r => r.GetString()!).ToArray() : Array.Empty<string>();
        check(ids.SequenceEqual(recipes), template + " recipes: " + string.Join(", ", ids));
      }
      var extractorCost = new[] { ("Log", 20), ("Gear", 15), ("MetalBlock", 10) };
      var desalinatorCost = new[] { ("Plank", 40), ("Gear", 20), ("MetalBlock", 20) };
      var wellCost = new[] { ("Plank", 40), ("Gear", 30), ("MetalBlock", 20) };
      foreach (var faction in Factions) {
        Building("MoreFluidsFluidExtractor." + faction, "Buildings/Water/MoreFluidsFluidExtractor", (2, 3, 3), 1, (0, 2, -1), extractorCost, 400, 1, 0, 13,
          new[] { faction == "IronTeeth" ? "MoreFluidsCoffee" : "MoreFluidsAntidote" });
        Building("MoreFluidsDesalinator." + faction, "Buildings/Water/MoreFluidsDesalinator", (3, 4, 4), 1, (1, 3, -1), desalinatorCost, 600, 1, 60, 61, new[] { "MoreFluidsDesalinatedWater" });
        Building("MoreFluidsHealingWell." + faction, "Buildings/Water/MoreFluidsHealingWell", (1, 1, 2), 0, null, wellCost, 1000, null, 100, 101, Array.Empty<string>());
      }
      // The pump layouts are the vanilla Deep Badwater Pump / Badwater Pump and Large Water Pump blocks exactly.
      foreach (var (ours, vanilla) in new[] {
          ("Buildings/Water/MoreFluidsFluidExtractor/MoreFluidsFluidExtractor.IronTeeth.blueprint", "Buildings/Water/DeepBadwaterPump/DeepBadwaterPump.IronTeeth.blueprint"),
          ("Buildings/Water/MoreFluidsFluidExtractor/MoreFluidsFluidExtractor.Folktails.blueprint", "Buildings/Water/BadwaterPump/BadwaterPump.Folktails.blueprint"),
          ("Buildings/Water/MoreFluidsDesalinator/MoreFluidsDesalinator.IronTeeth.blueprint", "Buildings/Water/LargeWaterPump/LargeWaterPump.Folktails.blueprint"),
          ("Buildings/Water/MoreFluidsDesalinator/MoreFluidsDesalinator.Folktails.blueprint", "Buildings/Water/LargeWaterPump/LargeWaterPump.Folktails.blueprint") })
        check(P(corpus.Ours[ours], "BlockObjectSpec").GetRawText() == P(corpus.Vanilla[vanilla], "BlockObjectSpec").GetRawText()
          || JsonSerializer.Serialize(P(corpus.Ours[ours], "BlockObjectSpec")) == JsonSerializer.Serialize(P(corpus.Vanilla[vanilla], "BlockObjectSpec")), ours + " keeps the vanilla block layout of " + vanilla);
      foreach (var (id, hours, good, amount) in new[] { ("MoreFluidsCoffee", .33, "Coffee", 1), ("MoreFluidsAntidote", 2.0, "Antidote", 2), ("MoreFluidsDesalinatedWater", .33, "Water", 1) }) {
        var recipe = P(corpus.Ours["Recipes/Recipe." + id + ".blueprint"], "RecipeSpec");
        var products = P(recipe, "Products").EnumerateArray().ToArray();
        check(P(recipe, "Id").GetString() == id && P(recipe, "CycleDurationInHours").GetDouble() == hours && P(recipe, "Ingredients").GetArrayLength() == 0
          && products.Length == 1 && P(products[0], "Id").GetString() == good && P(products[0], "Amount").GetInt32() == amount && P(recipe, "Fuel").GetString() == "", id + " recipe");
      }
      // Fluid per hour at full work: coffee 0.2 / 0.33 h, healing 0.8 / 2 h, saltwater 0.3 / 0.33 h.
      var coffee = FluidIntakeRecipe.Extraction(registry, "Coffee", 1); var antidote = FluidIntakeRecipe.Extraction(registry, "Antidote", 2); var salt = FluidIntakeRecipe.Desalination(registry, "Water", 1);
      observations["moreFluidsIntakeVolumePerHour"] = new Dictionary<string, double> {
        ["coffee"] = Math.Round(coffee.VolumePerCycle / .33, 6), ["healingWater"] = Math.Round(antidote.VolumePerCycle / 2, 6), ["saltwater"] = Math.Round(salt.VolumePerCycle / .33, 6) };
    });

    scenario("More Fluids content: faction goods, collections, source templates, map objects and tide fog", () => {
      var goods = new Dictionary<string, HashSet<string>>(StringComparer.Ordinal);
      foreach (var faction in new[] { "Common" }.Concat(Factions))
        goods[faction] = P(corpus.Vanilla["GoodCollections/GoodCollection." + faction + ".blueprint"], "GoodCollectionSpec", "Goods").EnumerateArray().Select(g => g.GetString()!).ToHashSet();
      var recipes = corpus.Ours.Where(p => p.Key.StartsWith("Recipes/", StringComparison.Ordinal)).ToDictionary(p => P(p.Value, "RecipeSpec", "Id").GetString()!, p => p.Value);
      var templates = new Dictionary<string, string>(StringComparer.Ordinal);
      foreach (var (path, bp) in corpus.Ours) {
        if (!bp.TryGetProperty("TemplateSpec", out var spec)) continue;
        string name = P(spec, "TemplateName").GetString()!;
        check(path.EndsWith("/" + name + ".blueprint", StringComparison.Ordinal) && templates.TryAdd(name, path), path + " template name matches its file and is unique");
        string? faction = Factions.SingleOrDefault(f => name.EndsWith("." + f, StringComparison.Ordinal));
        if (!bp.TryGetProperty("BuildingSpec", out var building)) continue;
        check(faction != null, name + " is a faction building");
        var allowed = new HashSet<string>(goods["Common"].Concat(goods[faction!]));
        foreach (var c in P(building, "BuildingCost").EnumerateArray()) check(allowed.Contains(P(c, "Id").GetString()!), name + " costs " + P(c, "Id").GetString() + ", not a " + faction + " good");
        if (bp.TryGetProperty("ManufactorySpec", out var m))
          foreach (var r in P(m, "ProductionRecipeIds").EnumerateArray()) {
            check(recipes.TryGetValue(r.GetString()!, out var recipe), name + " recipe " + r.GetString() + " exists");
            if (recipe.ValueKind == JsonValueKind.Object)
              foreach (var g in P(recipe, "RecipeSpec", "Products").EnumerateArray()) check(allowed.Contains(P(g, "Id").GetString()!), name + " makes " + P(g, "Id").GetString() + ", not a " + faction + " good");
          }
      }
      // Collections: every building in its faction's collection once, every map object in the map editor's.
      foreach (var faction in Factions) {
        var listed = P(corpus.Ours["TemplateCollections/TemplateCollection.Buildings." + faction + ".blueprint"], "TemplateCollectionSpec", "Blueprints#append").EnumerateArray().Select(b => b.GetString()!).ToArray();
        var expected = templates.Where(t => t.Key.EndsWith("." + faction, StringComparison.Ordinal)).Select(t => t.Value).OrderBy(p => p, StringComparer.Ordinal).ToArray();
        check(listed.OrderBy(p => p, StringComparer.Ordinal).SequenceEqual(expected), faction + " collection lists exactly its buildings: " + string.Join(", ", listed));
      }
      var maps = P(corpus.Ours["TemplateCollections/TemplateCollection.MapEditor.Common.blueprint"], "TemplateCollectionSpec", "Blueprints#append").EnumerateArray().Select(b => b.GetString()!).OrderBy(p => p, StringComparer.Ordinal).ToArray();
      check(maps.SequenceEqual(templates.Where(t => t.Value.StartsWith("MapEditor/", StringComparison.Ordinal)).Select(t => t.Value).OrderBy(p => p, StringComparer.Ordinal)), "Map editor collection: " + string.Join(", ", maps));
      foreach (var map in new[] { "MoreFluidsHealingSpring", "MoreFluidsGeyser" }) {
        var bp = corpus.Ours["MapEditor/Objects/" + map + "/" + map + ".blueprint"];
        check(P(bp, "PlaceableBlockObjectSpec", "ToolGroupId").GetString() == "MapEditorWater" && P(bp, "PlaceableBlockObjectSpec", "ToolOrder").GetInt32() == (map == "MoreFluidsGeyser" ? 530 : 520)
          && !bp.TryGetProperty("BuildingSpec", out _) && P(bp, "BlockObjectSpec", "Blocks")[0].GetProperty("MatterBelow").GetString() == "Ground", map + " map object placement");
      }
      // Every custom source type names one blueprint whose native WaterSourceSpec agrees, as Moddable Fluids checks in game.
      foreach (var type in registry.SourceTypes.Where(t => !t.IsNative)) {
        check(templates.TryGetValue(type.Template, out var path), type.Id + " template " + type.Template + " has a blueprint");
        if (path == null) continue;
        var bp = corpus.Ours[path];
        check(P(bp, "WaterSourceSpec", "Coordinates").GetArrayLength() == type.TileCount && (float)P(bp, "WaterSourceSpec", "DefaultStrength").GetDouble() == type.DefaultStrength,
          type.Id + " tiles and strength match " + path);
        check(P(bp, "WaterSourceContaminationSpec", "DefaultContamination").GetDouble() == 0 && bp.TryGetProperty("BadtideWaterSourceContaminationControllerSpec", out _) == type.BadtideContamination,
          type.Id + " contamination matches " + path);
      }
      check(templates.Values.Count(p => corpus.Ours[p].TryGetProperty("WaterSourceSpec", out _)) == registry.SourceTypes.Count(t => !t.IsNative), "Every More Fluids water source blueprint is a registered source type");
      // Colliders (fitted to the delivered models) stay inside the block footprint: X across, Z along the block Y axis,
      // Y up from the model origin at BaseZ.
      foreach (var path in templates.Values) {
        var bp = corpus.Ours[path];
        var block = P(bp, "BlockObjectSpec");
        double sx = P(block, "Size", "X").GetInt32(), sy = P(block, "Size", "Y").GetInt32(), sz = P(block, "Size", "Z").GetInt32(), baseZ = P(block, "BaseZ").GetInt32();
        int boxes = 0;
        void Boxes(JsonElement e) {
          if (e.ValueKind == JsonValueKind.Object) {
            foreach (var p in e.EnumerateObject()) {
              if (p.Name != "BoxColliders") { Boxes(p.Value); continue; }
              foreach (var b in p.Value.EnumerateArray()) {
                boxes++;
                double cx = P(b, "Center", "X").GetDouble(), cy = P(b, "Center", "Y").GetDouble(), cz = P(b, "Center", "Z").GetDouble();
                double wx = P(b, "Size", "X").GetDouble(), wy = P(b, "Size", "Y").GetDouble(), wz = P(b, "Size", "Z").GetDouble();
                const double slack = .05;
                check(wx > 0 && wy > 0 && wz > 0 && cx - wx / 2 >= -slack && cx + wx / 2 <= sx + slack && cz - wz / 2 >= -slack && cz + wz / 2 <= sy + slack
                  && cy - wy / 2 >= -baseZ - slack && cy + wy / 2 <= sz - baseZ + slack, path + " collider " + JsonSerializer.Serialize(b) + " leaves its footprint");
              }
            }
          } else if (e.ValueKind == JsonValueKind.Array) foreach (var x in e.EnumerateArray()) Boxes(x);
        }
        Boxes(P(bp, "Children"));
        check(boxes > 0, path + " has colliders");
      }
      // Every tide weather has a fog colour in each day stage (the game looks it up when the weather starts).
      var sun = P(corpus.Ours["Configurations/Sun.blueprint"], "SunSpec");
      foreach (var tide in tides.Tides)
        foreach (var stage in new[] { "SunriseColors", "DayColors", "SunsetColors", "NightColors" })
          check(P(sun, stage, "HazardousWeatherFogs#append").EnumerateArray().Count(f => P(f, "HazardousWeatherId").GetString() == tide.NativeWeatherId) == 1, tide.Id + " fog in " + stage);
    });

    scenario("More Fluids localization: every key it uses exists, no row is unused, descriptions stay vanilla-short", () => {
      var used = new HashSet<string>(StringComparer.Ordinal);
      void Walk(JsonElement e) {
        if (e.ValueKind == JsonValueKind.Object) foreach (var p in e.EnumerateObject()) {
          if ((p.Name.EndsWith("LocKey", StringComparison.Ordinal) || p.Name == "DisplayLocKey") && p.Value.ValueKind == JsonValueKind.String && p.Value.GetString() != "") used.Add(p.Value.GetString()!);
          else Walk(p.Value);
        } else if (e.ValueKind == JsonValueKind.Array) foreach (var x in e.EnumerateArray()) Walk(x);
      }
      foreach (var bp in corpus.Ours.Values) Walk(bp);
      foreach (var d in registry.Definitions.Where(d => d.NativeRole == FluidNativeRole.Extra)) { used.Add(d.DisplayNameLocKey); used.Add(d.WaterIntake!.RefusedStatusLocKey); used.Add(d.WaterIntake.RefusedAlertLocKey); }
      foreach (var t in registry.SourceTypes.Where(t => !t.IsNative)) used.Add(t.DisplayNameLocKey);
      foreach (var t in tides.Tides) {
        var p = t.Presentation;
        used.UnionWith(new[] { t.DisplayNameLocKey, t.DescriptionLocKey, p.ApproachingLocKey, p.InProgressLocKey, p.StartedLocKey, p.EndedLocKey, p.ApproachingDescriptionLocKey, p.StartedDescriptionLocKey });
      }
      used.UnionWith(new[] { "MoreFluids.Status.TooDilute", "MoreFluids.Status.NoSaltwater" });   // FluidIntake statuses
      var ids = corpus.Loc.Select(r => r.Id).ToArray();
      check(ids.Distinct(StringComparer.Ordinal).Count() == ids.Length, "Duplicate localization rows: " + string.Join(", ", ids.GroupBy(i => i).Where(g => g.Count() > 1).Select(g => g.Key)));
      var missing = used.Where(k => !ids.Contains(k) && !corpus.VanillaLoc.Contains(k)).ToArray();
      check(missing.Length == 0, "Missing localization: " + string.Join(", ", missing));
      var unused = ids.Where(k => !used.Contains(k)).ToArray();
      check(unused.Length == 0, "Unused More Fluids localization rows: " + string.Join(", ", unused));
      check(!ids.Any(corpus.VanillaLoc.Contains), "More Fluids must not override vanilla text");
      foreach (var (id, text) in corpus.Loc.Where(r => r.Id.StartsWith("Building.", StringComparison.Ordinal) && r.Id.EndsWith("Description", StringComparison.Ordinal)))
        check(text.Length <= 154 && !text.Contains('×'), id + " is " + text.Length + " characters (vanilla at most 154, no ×)");
    });

    scenario("More Fluids art: every model, icon and sprite it references is delivered or on the art list", () => {
      var referenced = new HashSet<string>(StringComparer.Ordinal);
      void Walk(JsonElement e, string key) {
        if (e.ValueKind == JsonValueKind.Object) { foreach (var p in e.EnumerateObject()) Walk(p.Value, p.Name); }
        else if (e.ValueKind == JsonValueKind.Array) { foreach (var x in e.EnumerateArray()) Walk(x, key); }
        else if (e.ValueKind == JsonValueKind.String && (key == "Model" || key == "Icon" || key == "PipeSegmentPrefabPath")) referenced.Add(e.GetString()!);
      }
      foreach (var bp in corpus.Ours.Values) Walk(bp, "");
      foreach (var t in tides.Tides) referenced.UnionWith(new[] { t.Presentation.IconSprite, t.Presentation.ProgressSprite, t.Presentation.NotificationSprite });
      var vanillaText = string.Join("\n", corpus.Vanilla.Values.Select(v => v.GetRawText()));
      var pending = new List<string>();
      foreach (var path in referenced.OrderBy(p => p, StringComparer.Ordinal)) {
        bool ours = path.StartsWith("Buildings/Water/MoreFluids", StringComparison.Ordinal) || path.StartsWith("MapEditor/Objects/MoreFluids", StringComparison.Ordinal)
          || path.StartsWith("Sprites/Weather/MoreFluids", StringComparison.Ordinal);
        if (!ours) { check(vanillaText.Contains("\"" + path + "\"", StringComparison.Ordinal), path + " is not a More Fluids path and no vanilla blueprint uses it"); continue; }
        check(ArtPaths.Contains(path), path + " is not on the art list in docs/more-fluids-design.md");
        string file = Path.Combine(corpus.Data, path.Replace('/', Path.DirectorySeparatorChar));
        bool sprite = path.EndsWith("Icon", StringComparison.Ordinal) || path.StartsWith("Sprites/", StringComparison.Ordinal);
        bool present = sprite ? File.Exists(file + ".png") : File.Exists(file + ".timbermesh");
        if (sprite && present) check(File.Exists(file + ".png.meta.json") && File.ReadAllText(file + ".png.meta.json").Trim() == "{\"isSprite\":true}", path + ".png needs its sprite meta");
        if (!present) pending.Add(path);
      }
      check(ArtPaths.All(referenced.Contains), "Art list paths no blueprint uses: " + string.Join(", ", ArtPaths.Where(p => !referenced.Contains(p))));
      observations["moreFluidsArtPending"] = pending.ToArray();
    });
  }

  // ---------- Healing exposure ----------

  private static void Exposure(Action<bool, string> check, Action<string, Action> scenario) {
    scenario("Healing exposure: at least 20% healing water, standing in it, heals Injury and contamination 0.25 a day each", () => {
      var (registry, _) = MoreFluidsScenarios.Freeze();
      var dose = HealingDose.From(registry.Definitions.Single(d => d.Id == MoreFluidsLiquids.HealingWater), registry.GetHandle(MoreFluidsLiquids.HealingWater));
      FluidColumnSample Column(double water, double healing, double other = 0) {
        var volumes = new double[registry.Count];
        volumes[FluidRegistry.WaterIndex] = water; volumes[dose.Fluid.Index] = healing;
        if (other > 0) volumes[registry.GetHandle(MoreFluidsLiquids.Coffee).Index] = other;   // another fluid only changes the share
        return new FluidColumnSample(3, 10, volumes);
      }
      check(dose.MinimumShare == .2, "Threshold 20%");
      check(dose.Heals(Column(.8, .2), 3), "Exactly 20% heals");
      check(!dose.Heals(Column(.80001, .19999), 3), "Just under 20% does not");
      check(dose.Heals(Column(0, .05), 3), "A shallow pure pool heals");
      check(!dose.Heals(Column(0, 0), 3), "A dry column does not");
      check(!dose.Heals(Column(.2, .3), 4), "Above the water surface does not");
      check(dose.Heals(Column(1.2, .8), 4) && !dose.Heals(Column(1.2, .8), 2), "Standing in the column, not below its floor");
      check(dose.Heals(Column(.4, .3, .3), 3) && !dose.Heals(Column(.4, .1, .5), 3), "Another fluid only dilutes the healing share");
      var rates = dose.Rates;
      check(rates.Length == 2 && rates[0].NeedId == "Injury" && rates[1].NeedId == "BadwaterContamination" && rates.All(r => r.PointsPerDay == .25), "Rates: " + string.Join(", ", rates));
    });
  }
}
