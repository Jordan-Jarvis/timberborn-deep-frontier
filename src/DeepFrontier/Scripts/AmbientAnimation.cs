using System.Linq;
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.Buildings;
using Timberborn.Common;
using Timberborn.TemplateInstantiation;
using Timberborn.TickSystem;
using Timberborn.TimbermeshAnimations;
using Timberborn.TimeSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Buildings without a workshop (storage such as the Radioactive Waste Vault)
  // still carry ambient machinery: beacons, vents, cranes. The finished model's
  // one native animator plays its whole loop while the building is finished,
  // at the game's animation speed, as MineralPitAnimation and GroceryStore do.
  internal record AmbientAnimationSpec : ComponentSpec {}

  internal sealed class AmbientAnimation : TickableComponent, IAwakableComponent, IFinishedStateListener {
    private readonly NonlinearAnimationManager _animation;
    private IAnimator _animator;

    public AmbientAnimation(NonlinearAnimationManager animation) {_animation=animation;}

    public void Awake() {
      var finished=GameObject.FindChildIfNameNotEmpty(GetComponent<BuildingModelSpec>().FinishedModelName);
      _animator=finished.GetComponentsInChildren<MonoBehaviour>(true).OfType<IAnimator>().Single();
      _animator.Enabled=false;
      DisableComponent();
    }
    public void OnEnterFinishedState() {
      _animator.Enabled=true;_animator.Play("Default");EnableComponent();
    }
    public void OnExitFinishedState() {
      _animator.Stop();_animator.Enabled=false;DisableComponent();
    }
    public override void Tick() {
      _animator.Speed=_animation.SpeedMultiplier;
    }
  }

  [Context("Game")]
  public sealed class AmbientAnimationConfigurator : Configurator {
    protected override void Configure() {
      Bind<AmbientAnimation>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }
    private static TemplateModule Provide() {
      var b=new TemplateModule.Builder();
      b.AddDecorator<AmbientAnimationSpec,AmbientAnimation>();
      return b.Build();
    }
  }
}
