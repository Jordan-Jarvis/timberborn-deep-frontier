// Native access analyzer: lists every reference a compiled mod assembly makes to a type or member that is not
// public in the shipped (non-publicized) assemblies, and every reference the shipped assemblies do not define.
//
//   dotnet run --project tools/compile-check/native-access -- <compiled.dll>... --managed <shipped Managed dir>
//     [--workshop <Workshop content dir>] [--assembly <dll>]... --out <report.json>
//
// --managed is the game's own Timberborn_Data/Managed (dev-environment.json gameManaged), never the publicized
// ModsBuildManaged. Assemblies not found there (other mods) are looked up in --workshop by file name; one that
// cannot be located, or has several different Workshop copies, is listed under unresolvedAssemblies and nothing
// under it is checked. --assembly names the exact file to use for an assembly (repeatable).
//
// Report: { inputs, managed, workshop, assemblies, nonPublic, missing, unresolvedAssemblies }. A nonPublic or
// missing entry is { assembly, type, member, kind ("type"|"field"|"method"), signature, inputs, referencedBy };
// nonPublic adds visibility, fromSubclass and internalsVisibleTo (Findings.cs). referencedBy names input code:
// "Ns.Type::Method" for a method's IL, locals, signature and attributes, "Ns.Type::(metadata)" for a type's own
// metadata (base type, interfaces, field/property/event types, attributes) and "(metadata)" for assembly-level or
// otherwise unattributed references. Attribute arguments are not scanned: typeof() and enum values are stored as
// type-name strings, so [HarmonyPatch(typeof(T), "name")] targets and reflection by name are not covered.
//
// Exit code: 0 when the report is written and nothing is missing (non-public references are data), 1 when
// "missing" is not empty, 2 on invalid arguments; any other failure throws.
using System.Text.Encodings.Web;
using System.Text.Json;
using NativeAccess;

Options options;
try {
  options = Options.Parse(args);
} catch (ArgumentException error) {
  Console.Error.WriteLine("native-access: " + error.Message);
  Console.Error.WriteLine("Usage: dotnet run --project tools/compile-check/native-access -- <compiled.dll>... --managed <dir> [--workshop <dir>] [--assembly <dll>]... --out <report.json>");
  return 2;
}

var resolver = new AssemblyResolver(options);
var findings = new Findings();
foreach (var input in resolver.Inputs) new ReferenceScanner(input, resolver, findings).Run();

var report = new Report(
  resolver.Inputs.Select(input => input.Path).ToList(),
  options.Managed,
  options.Workshop,
  resolver.Resolved.Where(assembly => assembly.Origin != "input")
    .Select(assembly => new ResolvedAssembly(assembly.Name, assembly.Origin, assembly.Path))
    .OrderBy(assembly => assembly.Assembly, StringComparer.Ordinal).ToList(),
  findings.NonPublicEntries(),
  findings.MissingEntries(),
  resolver.Unresolved.OrderBy(entry => entry.Assembly, StringComparer.Ordinal).ToList());

Directory.CreateDirectory(Path.GetDirectoryName(options.Out)!);
var json = JsonSerializer.Serialize(report, new JsonSerializerOptions {
  WriteIndented = true,
  PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
  Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
});
File.WriteAllText(options.Out, json.ReplaceLineEndings("\n") + "\n");

Console.WriteLine($"native-access: {report.NonPublic.Count} non-public references, {report.Missing.Count} missing, {report.UnresolvedAssemblies.Count} unresolved assemblies -> {options.Out}");
foreach (var group in report.NonPublic.GroupBy(entry => entry.Kind).OrderBy(group => group.Key, StringComparer.Ordinal))
  Console.WriteLine($"  {group.Key}: {group.Count()} ({group.Count(entry => entry.FromSubclass)} from subclasses, {group.Count(entry => entry.InternalsVisibleTo)} through InternalsVisibleTo)");
foreach (var entry in report.Missing)
  Console.Error.WriteLine($"MISSING {entry.Kind} {entry.Assembly}: {entry.Type}{(entry.Member == null ? "" : " :: " + entry.Signature)} (used by {string.Join(", ", entry.ReferencedBy)})");
foreach (var entry in report.UnresolvedAssemblies)
  Console.Error.WriteLine($"UNRESOLVED {entry.Assembly}: {entry.Reason}; {entry.UncheckedReferences} references not checked");
return report.Missing.Count == 0 ? 0 : 1;

sealed record Options(IReadOnlyList<string> Inputs, string Managed, string? Workshop, IReadOnlyList<string> Pinned, string Out) {
  public static Options Parse(string[] args) {
    var inputs = new List<string>();
    var pinned = new List<string>();
    string? managed = null, workshop = null, output = null;
    for (int i = 0; i < args.Length; i++) {
      var arg = args[i];
      switch (arg) {
        case "--managed": managed = Once(managed, arg, Value(args, ref i)); break;
        case "--workshop": workshop = Once(workshop, arg, Value(args, ref i)); break;
        case "--out": output = Once(output, arg, Value(args, ref i)); break;
        case "--assembly": pinned.Add(Value(args, ref i)); break;
        default:
          if (arg.StartsWith('-')) throw new ArgumentException($"Unknown option {arg}");
          inputs.Add(arg);
          break;
      }
    }
    if (inputs.Count == 0) throw new ArgumentException("No compiled DLL given");
    if (managed == null) throw new ArgumentException("--managed is required");
    if (output == null) throw new ArgumentException("--out is required");
    foreach (var file in inputs.Concat(pinned))
      if (!File.Exists(file)) throw new ArgumentException($"{file} does not exist");
    foreach (var directory in new[] { managed, workshop }.OfType<string>())
      if (!Directory.Exists(directory)) throw new ArgumentException($"{directory} is not a directory");
    return new Options(
      inputs.Select(Path.GetFullPath).ToList(),
      Path.GetFullPath(managed),
      workshop == null ? null : Path.GetFullPath(workshop),
      pinned.Select(Path.GetFullPath).ToList(),
      Path.GetFullPath(output));
  }

  static string Value(string[] args, ref int i) =>
    ++i < args.Length ? args[i] : throw new ArgumentException($"{args[i - 1]} needs a value");

  static string Once(string? current, string option, string value) =>
    current == null ? value : throw new ArgumentException($"{option} is given twice");
}

sealed record ResolvedAssembly(string Assembly, string Origin, string Path);

sealed record Report(
  IReadOnlyList<string> Inputs,
  string Managed,
  string? Workshop,
  IReadOnlyList<ResolvedAssembly> Assemblies,
  IReadOnlyList<NonPublicReference> NonPublic,
  IReadOnlyList<MissingReference> Missing,
  IReadOnlyList<UnresolvedAssembly> UnresolvedAssemblies);
