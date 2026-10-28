using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using Bindito.Core;
using Newtonsoft.Json;
using Timberborn.ErrorReporting;
using Timberborn.GameSaveRuntimeSystem;
using Timberborn.SingletonSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Explicit test launch only (-deepFrontierLoadAcceptance). Records exactly which saved
  // objects the native loader dropped from a fixture. BlockObject.AddToServiceAfterLoad
  // deletes an object that no longer validates against the current blueprints (for example
  // a path inside a block a regenerated factory now occupies) and reports it through
  // ILoadingIssueService, which only keeps per-type counts. The per-object warning text
  // ("Can't validate loaded BlockObject <name> at (x, y, z) ...") is captured from the log,
  // cross-checked against the native counts and written to outputs/acceptance-loading-issues.json.
  // Harnesses decide explicitly which dropped objects they tolerate (Dropped).
  [Context("Game")]
  public sealed class AcceptanceLoadingIssuesConfigurator : Configurator {
    protected override void Configure() {
      if(!Environment.GetCommandLineArgs().Contains("-deepFrontierLoadAcceptance"))return;
      AcceptanceLoadingIssues.StartCapture();
      Bind<AcceptanceLoadingIssues>().AsSingleton();
    }
  }

  internal sealed class AcceptanceDroppedObject {
    public string Name;
    public Vector3Int Coordinates;
    public string Message;
  }

  internal sealed class AcceptanceLoadingIssues : IPostLoadableSingleton {
    private const string Tag="[DeepFrontier Acceptance]";
    private const string BlockObjectIssueLocKey="LoadingIssue.BlockObjectLoadingIssue"; // native BlockObject.BlockObjectLoadingIssueLocKey
    private static readonly Regex Dropped=new(
      @"^Can't validate loaded BlockObject (?<name>.+) at \((?<x>-?\d+), (?<y>-?\d+), (?<z>-?\d+)\)\. It's not backward compatible\. Deleting it\.$");
    private static readonly List<AcceptanceDroppedObject> Captured=new();
    private static bool _capturing;
    private readonly ILoadingIssueService _issues;
    private readonly GameLoader _loader;

    // Objects the native loader deleted from the loaded fixture save.
    public static IReadOnlyList<AcceptanceDroppedObject> DroppedObjects=>Captured;
    public static bool Reported { get; private set; }

    public AcceptanceLoadingIssues(ILoadingIssueService issues,GameLoader loader) {_issues=issues;_loader=loader;}

    public static void StartCapture() {
      Captured.Clear();Reported=false;
      if(_capturing)return;
      _capturing=true;
      Application.logMessageReceived+=OnLog;
    }
    private static void OnLog(string message,string stack,LogType type) {
      if(type!=LogType.Warning)return;
      var match=Dropped.Match(message);
      if(!match.Success)return;
      Captured.Add(new AcceptanceDroppedObject{Name=match.Groups["name"].Value,
        Coordinates=new Vector3Int(int.Parse(match.Groups["x"].Value),int.Parse(match.Groups["y"].Value),int.Parse(match.Groups["z"].Value)),
        Message=message});
    }

    public void PostLoad() {
      var issues=_issues.GetIssues().Select(i=>new {locKey=i.Item1.MessageLocKey,param=i.Item1.MessageParam,count=i.Item2}).ToList();
      // Native AddIssue for dropped block objects uses the BlockObject loading-issue key; every
      // other issue (missing templates, terrain) is listed separately and is never matched here.
      int nativeDropped=issues.Where(i=>i.locKey==BlockObjectIssueLocKey).Sum(i=>i.count);
      foreach(var d in Captured)Debug.LogWarning(Tag+" LOADING ISSUE dropped "+d.Name+" at "+d.Coordinates);
      foreach(var i in issues)Debug.LogWarning(Tag+" LOADING ISSUE "+i.locKey+" "+i.param+" x"+i.count);
      if(nativeDropped!=Captured.Count)
        Debug.LogError(Tag+" LOADING ISSUE capture mismatch: native counts "+nativeDropped+" dropped block objects, captured "+Captured.Count);
      Directory.CreateDirectory(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),"TimberbornModding","outputs"));
      File.WriteAllText(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),"TimberbornModding","outputs",
        "acceptance-loading-issues.json"),JsonConvert.SerializeObject(new {
          save=_loader.IsNewGame?"new game":_loader.LoadedSave.ToString(),
          args=Environment.GetCommandLineArgs().Where(a=>a.StartsWith("-deepFrontier",StringComparison.Ordinal)).ToArray(),
          nativeDroppedCount=nativeDropped,
          dropped=Captured.Select(d=>new {d.Name,coordinates=new[]{d.Coordinates.x,d.Coordinates.y,d.Coordinates.z},d.Message}),
          issues},Formatting.Indented));
      Debug.Log(Tag+" loading issues: "+Captured.Count+" dropped block objects, "+issues.Count+" native issue kinds");
      Reported=nativeDropped==Captured.Count;
    }
  }
}
