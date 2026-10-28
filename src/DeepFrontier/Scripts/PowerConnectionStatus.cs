using System;
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.BlueprintSystem;
using Timberborn.BlockSystem;
using Timberborn.EntitySystem;
using Timberborn.Localization;
using Timberborn.MechanicalSystem;
using Timberborn.StatusSystem;
using Timberborn.TemplateInstantiation;
using Timberborn.TickSystem;

namespace DeepFrontier.Scripts {
  // Marks a Deep Frontier power consumer (MechanicalNodeSpec.PowerInput > 0); written by
  // tools/status_icon_content.mjs and checked by tools/validate_status_icon_anchors.mjs.
  internal record PowerConnectionStatusSpec : ComponentSpec;

  internal static class PowerConnectionLoc {
    public const string NotConnected = "DeepFrontier.Power.Status.NotConnected";
    public const string NotConnectedShort = "DeepFrontier.Power.Status.NotConnected.Short";
    // Native NoPowerStatus sprite (Timberborn.MechanicalSystemUI, 1.1.2.8).
    public const string Sprite = "NoPower";
  }

  // "Not connected to a power source" (user decision 2026-10-23). The native NoPowerStatus shows
  // only while a consumer draws power, and Moddable Timberborn 11.1.3 (a required mod) also reports
  // a graph with zero demand as powered, so an idle consumer that is not connected to any
  // generator showed no power hint at all (build 146 Bathhouse report). This normal status (alert
  // and floating icon, native NoPower sprite) is active whenever the finished building's mechanical
  // graph has no generator and no battery capacity, whatever the current demand; it clears as soon
  // as a generator or battery joins the graph. It reads the graph's own counts, not
  // MechanicalNode.CanPotentiallyBePowered (which Moddable Timberborn patches). Deep Frontier
  // consumers only; vanilla buildings and the native NoPower status are unchanged.
  internal sealed class PowerConnectionStatus : TickableComponent, IAwakableComponent, IInitializableEntity, IFinishedStateListener {
    private readonly ILoc _loc;
    private MechanicalNode _node;
    private StatusToggle _status;
    private bool _shown;

    public bool NotConnected => _shown;

    public PowerConnectionStatus(ILoc loc) {_loc=loc;}

    public void Awake() {
      _node=GetComponent<MechanicalNode>();
      var spec=GetComponent<MechanicalNodeSpec>();
      if(!_node||spec==null)throw new InvalidOperationException($"{Name}: PowerConnectionStatusSpec requires the native MechanicalNode");
      if(!(spec.PowerInput>0))throw new InvalidOperationException($"{Name}: PowerConnectionStatusSpec on a building that consumes no power (PowerInput {spec.PowerInput})");
      _status=StatusToggle.CreateNormalStatusWithAlertAndFloatingIcon(PowerConnectionLoc.Sprite,_loc.T(PowerConnectionLoc.NotConnected),_loc.T(PowerConnectionLoc.NotConnectedShort));
      DisableComponent();
    }

    public void InitializeEntity()=>GetComponent<StatusSubject>().RegisterStatus(_status);

    public void OnEnterFinishedState() {EnableComponent();Refresh();}

    public void OnExitFinishedState() {DisableComponent();Set(false);}

    public override void Tick()=>Refresh();

    private void Refresh() {
      var graph=_node.Graph;
      Set(graph==null||graph.NumberOfGenerators==0&&graph.BatteryCapacity<=0);
    }

    private void Set(bool shown) {
      if(shown==_shown)return;
      _shown=shown;
      if(shown)_status.Activate();else _status.Deactivate();
    }
  }

  // Startup check of the native members the status mirrors (Timberborn 1.1.2.8): the NoPower
  // sprite name of the native NoPowerStatus and the graph counts it reads.
  internal sealed class PowerConnectionStatusModStarter : Timberborn.ModManagerScene.IModStarter {
    public void StartMod(Timberborn.ModManagerScene.IModEnvironment modEnvironment) {
      const System.Reflection.BindingFlags Static=System.Reflection.BindingFlags.Static|System.Reflection.BindingFlags.NonPublic;
      var native=Type.GetType("Timberborn.MechanicalSystemUI.NoPowerStatus, Timberborn.MechanicalSystemUI")
        ??throw new InvalidOperationException("Power connection status: native Timberborn.MechanicalSystemUI.NoPowerStatus not found (Timberborn 1.1.2.8)");
      if(native.GetField("NoPowerSpriteName",Static)?.GetValue(null) as string!=PowerConnectionLoc.Sprite)
        throw new InvalidOperationException("Power connection status: native NoPowerStatus.NoPowerSpriteName is no longer \""+PowerConnectionLoc.Sprite+"\"");
      if(typeof(MechanicalGraph).GetProperty(nameof(MechanicalGraph.NumberOfGenerators))?.PropertyType!=typeof(int)||
         typeof(MechanicalGraph).GetProperty(nameof(MechanicalGraph.BatteryCapacity))?.PropertyType!=typeof(int))
        throw new InvalidOperationException("Power connection status: MechanicalGraph.NumberOfGenerators/BatteryCapacity changed");
    }
  }

  [Context("Game")]
  public sealed class PowerConnectionStatusConfigurator : Configurator {
    protected override void Configure() {
      Bind<PowerConnectionStatus>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }
    private static TemplateModule Provide() {
      var b=new TemplateModule.Builder();
      b.AddDecorator<PowerConnectionStatusSpec,PowerConnectionStatus>();
      return b.Build();
    }
  }
}
