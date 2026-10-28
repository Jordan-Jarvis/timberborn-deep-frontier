using System;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.Linq;
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.Buildings;
using Timberborn.Common;
using Timberborn.EntitySystem;
using Timberborn.InventorySystem;
using Timberborn.Rendering;
using Timberborn.SingletonSystem;
using Timberborn.TemplateInstantiation;
using Timberborn.TickSystem;
using Timberborn.TimbermeshAnimations;
using Timberborn.TimeSystem;
using Timberborn.Workshops;
using UnityEngine;

namespace DeepFrontier.Scripts {
  internal record NativeBuildingProp {
    [Serialize] public string Node { get; init; }
    [Serialize] public Vector3 Position { get; init; }
    [Serialize] public Vector3 Rotation { get; init; }
    [Serialize] public Vector3 Scale { get; init; }
    [Serialize] public bool Flowering { get; init; }
  }

  internal record NativeBuildingPropsSpec : ComponentSpec {
    [Serialize] public ImmutableArray<NativeBuildingProp> Props { get; init; }
  }

  // TimbermeshSpec creates the original game asset. Only its authored placement
  // belongs to us; models, UVs, materials and native animation remain unchanged.
  internal sealed class NativeBuildingProps : BaseComponent, IAwakableComponent, IInitializableEntity {
    public void Awake() {
      var finished = GameObject.FindChildIfNameNotEmpty(GetComponent<BuildingModelSpec>().FinishedModelName);
      foreach (var prop in GetComponent<NativeBuildingPropsSpec>().Props) {
        var matches = finished.GetComponentsInChildren<Transform>(true).Where(t => t.name == prop.Node).ToArray();
        if (matches.Length != 1 || prop.Scale.x <= 0 || prop.Scale.y <= 0 || prop.Scale.z <= 0)
          throw new InvalidOperationException($"Invalid native prop placement: {prop.Node}");
        var node = matches[0];
        node.localPosition = prop.Position;
        node.localRotation = Quaternion.Euler(prop.Rotation);
        node.localScale = prop.Scale;
      }
    }
    public void InitializeEntity() {
      // Native GatherableModel.UpdateMaterial uses this property for flowers
      // and fruit. EntityMaterials has already made per-entity instances here.
      var finished=GameObject.FindChildIfNameNotEmpty(GetComponent<BuildingModelSpec>().FinishedModelName);
      foreach(var prop in GetComponent<NativeBuildingPropsSpec>().Props.Where(p=>p.Flowering)) {
        var node=finished.GetComponentsInChildren<Transform>(true).Single(t=>t.name==prop.Node);
        var materials=new List<Material>();GetComponent<EntityMaterials>().GetChildMaterials(node,materials);
        if(materials.Count==0 || materials.Any(m=>!m.HasProperty("_EnableDetail")))
          throw new InvalidOperationException("Flowering native prop lacks its detail material: "+prop.Node);
        foreach(var material in materials)material.SetFloat("_EnableDetail",1);
      }
    }
  }

  internal record ReservoirSurfaceSpec {
    [Serialize] public string Node { get; init; }
    [Serialize] public AssetRef<Mesh> Mesh { get; init; }
    [Serialize] public Vector3 Position { get; init; }
    [Serialize] public Vector3 Scale { get; init; }
    [Serialize] public float EmptyHeight { get; init; }
    [Serialize] public float FullHeight { get; init; }
  }

  internal record WorkshopReservoirSpec : ComponentSpec {
    [Serialize] public string GoodId { get; init; }
    [Serialize] public int Capacity { get; init; }
    [Serialize] public AssetRef<Material> Material { get; init; }
    [Serialize] public ImmutableArray<ReservoirSurfaceSpec> Surfaces { get; init; }
    [Serialize] public ImmutableArray<string> FlowNodes { get; init; }
    [Serialize] public ImmutableArray<string> WheelNodes { get; init; }
  }

  // No second water inventory: this is a view of the native workshop inventory.
  // The capacity is authored from the recipe's water storage allowance. Empty
  // reservoirs hide their surface. Production-driven flow stops without water,
  // workers, power or product space. A consumed batch is already being processed;
  // it is not added back to the amount displayed as stored water.
  internal sealed class WorkshopReservoir : TickableComponent,
      IAwakableComponent, IFinishedStateListener {
    private readonly NonlinearAnimationManager _animation;
    private readonly EventBus _events;
    private WorkshopReservoirSpec _spec;
    private Manufactory _manufactory;
    private Workshop _workshop;
    private Inventory _inventory;
    private readonly List<(ReservoirSurfaceSpec Spec, Transform Node, MeshRenderer Renderer)> _surfaces = new();
    private readonly List<GameObject> _flow = new();
    private readonly List<IAnimator> _wheels = new();
    private bool _finished;
    private bool _initialized;
    public int StoredAmount { get; private set; }
    public bool Flowing { get; private set; }
    public IReadOnlyList<float> SurfaceHeights => _surfaces.Select(s => s.Node.localPosition.y).ToArray();
    public bool SurfacesVisible => _surfaces.All(s => s.Node.gameObject.activeSelf);
    public IReadOnlyList<float> WheelTimes => _wheels.Select(w=>w.Time).ToArray();
    public bool WheelsEnabled => _wheels.Any(w=>w.Enabled);

    public WorkshopReservoir(NonlinearAnimationManager animation,EventBus events) {
      _animation=animation;_events=events;
    }

    public void Awake() {
      _spec = GetComponent<WorkshopReservoirSpec>();
      _manufactory = GetComponent<Manufactory>();
      _workshop = GetComponent<Workshop>();
      if (string.IsNullOrEmpty(_spec.GoodId) || _spec.Capacity <= 0 || _spec.Surfaces.IsDefaultOrEmpty)
        throw new InvalidOperationException("Reservoir requires an explicit good, capacity and surfaces.");
      DisableComponent();
    }

    private void InitializeModel() {
      // EntityMaterials has completed Awake before finished-state entry. Adding
      // our instances here avoids registering a renderer's material twice.
      var finished = GameObject.FindChildIfNameNotEmpty(GetComponent<BuildingModelSpec>().FinishedModelName);
      var names = new HashSet<string>();
      foreach (var surface in _spec.Surfaces) {
        if (!names.Add(surface.Node) || surface.EmptyHeight >= surface.FullHeight
            || surface.Scale.x <= 0 || surface.Scale.y <= 0 || surface.Scale.z <= 0)
          throw new InvalidOperationException($"Invalid reservoir surface: {surface.Node}");
        var obj = new GameObject(surface.Node);
        obj.transform.SetParent(finished.transform, false);
        obj.transform.localPosition = surface.Position;
        obj.transform.localScale = surface.Scale;
        obj.AddComponent<MeshFilter>().sharedMesh = surface.Mesh.Asset;
        var renderer = obj.AddComponent<MeshRenderer>();
        renderer.sharedMaterial = new Material(_spec.Material.Asset);
        GetComponent<EntityMaterials>().AddMaterial(obj.transform, renderer.sharedMaterial);
        // Building model visibility controls renderer.enabled. The reservoir
        // owns its child object's active state so empty water stays absent.
        obj.SetActive(false);
        _surfaces.Add((surface, obj.transform, renderer));
      }
      var transforms = finished.GetComponentsInChildren<Transform>(true);
      Transform Node(string name) {
        var matches = transforms.Where(t => t.name == name).ToArray();
        if (matches.Length != 1) throw new InvalidOperationException($"Reservoir needs exactly one node {name}.");
        return matches[0];
      }
      foreach (var name in _spec.FlowNodes) { var obj = Node(name).gameObject; obj.SetActive(false); _flow.Add(obj); }
      foreach (var name in _spec.WheelNodes) {
        var animators = Node(name).GetComponentsInChildren<MonoBehaviour>(true).OfType<IAnimator>().ToArray();
        if (animators.Length != 1) throw new InvalidOperationException($"Native wheel needs one animator: {name}");
        animators[0].Play("Default"); animators[0].Speed = 0; _wheels.Add(animators[0]);
      }
      _initialized = true;
    }

    public void OnEnterFinishedState() {
      if (_finished) throw new InvalidOperationException("Reservoir entered finished state twice.");
      if (!_initialized) InitializeModel();
      _finished = true;
      _inventory = _manufactory.Inventory;
      _inventory.InventoryChanged += OnInventoryChanged;
      _workshop.WorkshopStateChanged += OnWorkshopChanged;
      _events.Register(this);
      EnableComponent();
      Refresh();
    }

    public void OnExitFinishedState() {
      if (!_finished) throw new InvalidOperationException("Reservoir left finished state without entering it.");
      _inventory.InventoryChanged -= OnInventoryChanged;
      _workshop.WorkshopStateChanged -= OnWorkshopChanged;
      _events.Unregister(this);
      _finished = false;
      foreach (var surface in _surfaces) surface.Node.gameObject.SetActive(false);
      SetFlow(false);
      DisableComponent();
    }

    private void OnInventoryChanged(object sender, InventoryChangedEventArgs args) {
      if (args.GoodId == _spec.GoodId) Refresh();
    }
    public override void Tick() { Refresh(); }
    private void OnWorkshopChanged(object sender,WorkshopStateChangedEventArgs args) { Refresh(); }
    [OnEvent] public void OnSpeedChanged(CurrentSpeedChangedEvent args) { SetFlow(Flowing); }

    private void Refresh() {
      StoredAmount = _inventory.AmountInStock(_spec.GoodId);
      if (StoredAmount < 0 || StoredAmount > _spec.Capacity)
        throw new InvalidOperationException($"Reservoir {_spec.GoodId}: {StoredAmount} exceeds authored capacity {_spec.Capacity}.");
      float fill = (float)StoredAmount / _spec.Capacity;
      foreach (var surface in _surfaces) {
        var position = surface.Spec.Position;
        position.y = surface.Spec.EmptyHeight + (surface.Spec.FullHeight - surface.Spec.EmptyHeight) * fill;
        surface.Node.localPosition = position;
        surface.Node.gameObject.SetActive(StoredAmount > 0);
      }
      SetFlow(StoredAmount > 0 && _workshop.CurrentlyWorking && _manufactory.IsReadyToProduce);
    }

    private void SetFlow(bool flowing) {
      Flowing = flowing;
      foreach (var obj in _flow) obj.SetActive(flowing);
      foreach (var wheel in _wheels) {
        wheel.Enabled=flowing;
        wheel.Speed=flowing ? _animation.SpeedMultiplier : 0;
      }
    }
  }

  [Context("Game")]
  public sealed class WorkshopReservoirConfigurator : Configurator {
    protected override void Configure() {
      Bind<NativeBuildingProps>().AsTransient();
      Bind<WorkshopReservoir>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(ProvideTemplateModule).AsSingleton();
    }
    private static TemplateModule ProvideTemplateModule() {
      var builder = new TemplateModule.Builder();
      builder.AddDecorator<NativeBuildingPropsSpec, NativeBuildingProps>();
      builder.AddDecorator<NativeBuildingPropsSpec, EntityMaterials>();
      builder.AddDecorator<WorkshopReservoirSpec, WorkshopReservoir>();
      builder.AddDecorator<WorkshopReservoirSpec, EntityMaterials>();
      return builder.Build();
    }
  }
}
