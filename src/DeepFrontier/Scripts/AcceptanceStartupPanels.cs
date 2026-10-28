#if !UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Bindito.Core;
using Timberborn.CoreUI;
using Timberborn.SingletonSystem;
using UnityEngine;
using UnityEngine.UIElements;

namespace DeepFrontier.Scripts {
  // Explicit test launch only (-deepFrontierLoadAcceptance). Normal play never binds these.
  //
  // Game scene: a panel pushed during startup (for example Moddable Weathers' Weather Settings
  // dialog on a save without its flag) locks game speed through the native
  // OverlayPanelSpeedLocker, so every harness SpeedManager.ChangeSpeed call is ignored until
  // someone clicks. Before frame 60 (the first harness setup frame) each stacked panel is
  // dismissed exactly as the native Escape key does (PanelStack.ProcessUICancel ->
  // IPanelController.OnUICancelled) and logged. Later panels belong to the harnesses (the
  // rocket run closes its own dialogs) and are only logged.
  //
  // Main menu: the acceptance loader leaves the menu by scene change, so its panels
  // (welcome screen, intro, consent) are only logged.
  //
  // The Mods screen shown before the main menu runs before any mod code is loaded; the
  // launchers pass the native -skipModManager argument for it.
  [Context("MainMenu")]
  public sealed class AcceptanceMenuPanelLogConfigurator : Configurator {
    protected override void Configure() {
      if(Environment.GetCommandLineArgs().Contains("-deepFrontierLoadAcceptance"))
        Bind<AcceptanceMenuPanelLog>().AsSingleton();
    }
  }
  [Context("Game")]
  public sealed class AcceptanceStartupPanelDismisserConfigurator : Configurator {
    protected override void Configure() {
      if(Environment.GetCommandLineArgs().Contains("-deepFrontierLoadAcceptance"))
        Bind<AcceptanceStartupPanelDismisser>().AsSingleton();
    }
  }

  internal static class AcceptancePanels {
    public const string Tag="[DeepFrontier Acceptance]";
    private static readonly FieldInfo StackField=
      typeof(PanelStack).GetField("_stack",BindingFlags.NonPublic|BindingFlags.Instance);
    // Top of the stack first, as Stack<T> enumerates.
    public static List<IPanelController> Stacked(PanelStack panels) {
      if(StackField==null)throw new InvalidOperationException("PanelStack._stack not found; recheck the 1.1.2.8 contract");
      var result=new List<IPanelController>();
      foreach(var stacked in (IEnumerable)StackField.GetValue(panels)) {
        var property=stacked.GetType().GetProperty("PanelController")
          ??throw new InvalidOperationException("StackedPanel.PanelController not found; recheck the 1.1.2.8 contract");
        result.Add((IPanelController)property.GetValue(stacked));
      }
      return result;
    }
    public static string Describe(IPanelController panel) {
      var root=panel.GetPanel();
      var texts=root==null?new List<string>():root.Query<TextElement>().ToList()
        .Select(t=>t.text).Where(t=>!string.IsNullOrWhiteSpace(t)).Select(t=>t.Replace('\n',' ').Trim()).Take(4).ToList();
      // TimberUi dialogs are native DialogBoxes whose root names the mod's dialog type.
      return panel.GetType().FullName+" root="+(root==null?"null":root.GetType().FullName)
        +" text=\""+string.Join(" | ",texts)+"\"";
    }
  }

  public sealed class AcceptanceMenuPanelLog : IUpdatableSingleton {
    private readonly PanelStack _panels;
    private readonly HashSet<IPanelController> _seen=new();
    private int _frame;
    public AcceptanceMenuPanelLog(PanelStack panels) {_panels=panels;}
    public void UpdateSingleton() {
      _frame++;
      foreach(var panel in AcceptancePanels.Stacked(_panels).Where(_seen.Add))
        Debug.Log(AcceptancePanels.Tag+" Main menu panel at frame "+_frame+" left for the loader's scene change: "+AcceptancePanels.Describe(panel));
    }
  }

  public sealed class AcceptanceStartupPanelDismisser : IUpdatableSingleton {
    private const int HarnessSetupFrame=60;
    private readonly PanelStack _panels;
    private readonly HashSet<IPanelController> _seen=new();
    private IPanelController _dismissed;
    private int _frame;
    public AcceptanceStartupPanelDismisser(PanelStack panels) {_panels=panels;}
    public void UpdateSingleton() {
      _frame++;
      var stacked=AcceptancePanels.Stacked(_panels);
      if(stacked.Count==0)return;
      var top=stacked[0];
      if(_frame>=HarnessSetupFrame) {
        foreach(var panel in stacked.Where(_seen.Add))
          Debug.LogWarning(AcceptancePanels.Tag+" Panel shown at game frame "+_frame+" after the startup window; left for the harness: "+AcceptancePanels.Describe(panel));
        return;
      }
      if(ReferenceEquals(top,_dismissed))
        throw new InvalidOperationException("Startup panel did not close on Escape: "+AcceptancePanels.Describe(top));
      _seen.Add(top);
      var description=AcceptancePanels.Describe(top);
      _dismissed=top;
      top.OnUICancelled();
      Debug.Log(AcceptancePanels.Tag+" Dismissed startup panel at game frame "+_frame+" with native Escape (OnUICancelled): "+description);
    }
  }
}
#endif
