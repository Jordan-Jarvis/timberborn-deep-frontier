using System;
using System.Linq;
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.BlueprintSystem;
using Timberborn.EntitySystem;
using Timberborn.TemplateInstantiation;
using Timberborn.WaterSourceSystem;
using UnityEngine;

namespace DeepFrontier.Scripts.Radiation {
  // Radioactive Spring: a native water source (vanilla DevWaterSource /
  // map-editor clone with its native WaterSourceSpec, strength UI, saving and
  // WaterSourceContaminationSpec at 0) whose water is radioactive. Two
  // templates share this spec: RadioactiveSpring (in-game dev tool) and
  // RadioactiveSpringSource (map editor). The native UpdateWaterSourcesTask
  // adds the water; RadiationSimulation mixes RadioactiveShare of it into r.
  internal record RadioactiveWaterSourceSpec : ComponentSpec {
    [Serialize] public float RadioactiveShare { get; init; }
  }

  // Game only (RadiationConfigurator).
  internal sealed class RadioactiveWaterSource : BaseComponent, IAwakableComponent, IInitializableEntity, IDeletableEntity {
    private readonly RadiationSimulation _radiation;
    private WaterSource _source;
    private float _share;

    public RadioactiveWaterSource(RadiationSimulation radiation) { _radiation = radiation; }

    public void Awake() {
      _source = GetComponent<WaterSource>();
      if (_source == null) throw new InvalidOperationException("RadioactiveWaterSourceSpec requires the native WaterSource");
      _share = GetComponent<RadioactiveWaterSourceSpec>().RadioactiveShare;
    }

    public void InitializeEntity() => _radiation.RegisterSpring(_source, _share);

    public void DeleteEntity() => _radiation.UnregisterSpring(_source);
  }

  // Draws the spring model's pool and mineral crusts (its RadioactiveGlow node,
  // tools/map_objects.json glowNode) with the radioactive material; the vent's
  // rock keeps its native material.
  internal sealed class RadioactiveSpringVisual : BaseComponent, IAwakableComponent, IInitializableEntity {
    internal const string GlowNode = "RadioactiveGlow";
    private readonly RadiationMaterials _materials;
    public RadioactiveSpringVisual(RadiationMaterials materials) { _materials = materials; }
    public void Awake() => Tint();
    public void InitializeEntity() {
      if (Tint() == 0) throw new InvalidOperationException($"Radioactive Spring model has no {GlowNode} renderer to tint");
    }
    private int Tint() {
      var tinted = 0;
      foreach (var renderer in GameObject.GetComponentsInChildren<MeshRenderer>(true)) {
        if (renderer.gameObject.name != GlowNode) continue;
        renderer.sharedMaterials = Enumerable.Repeat(_materials.Spring, renderer.sharedMaterials.Length).ToArray();
        tinted++;
      }
      return tinted;
    }
  }

  [Context("Game")]
  [Context("MapEditor")]
  public sealed class RadioactiveSpringConfigurator : Configurator {
    protected override void Configure() {
      Bind<RadiationMaterials>().AsSingleton();
      Bind<RadioactiveSpringVisual>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }

    private static TemplateModule Provide() {
      var builder = new TemplateModule.Builder();
      builder.AddDecorator<RadioactiveWaterSourceSpec, RadioactiveSpringVisual>();
      return builder.Build();
    }
  }
}
