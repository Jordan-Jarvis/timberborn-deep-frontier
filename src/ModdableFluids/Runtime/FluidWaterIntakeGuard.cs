using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockingSystem;
using Timberborn.BlockSystem;
using Timberborn.EntitySystem;
using Timberborn.Localization;
using Timberborn.StatusSystem;
using Timberborn.TemplateInstantiation;
using Timberborn.TickSystem;
using Timberborn.WaterBuildings;
using ModdableFluids;
using ModdableFluids.World.Prototype;
using UnityEngine;

namespace ModdableFluids.Runtime.Prototype {
  /// <summary>
  /// Moddable Fluids' one guard on native water intakes (capability <c>ModdableFluids.Policies.WaterIntakes</c>), the
  /// generalisation of Deep Frontier's RadiationIntakeGuard. Decorated onto every native <c>WaterInput</c> (water and
  /// badwater pumps, mechanical pumps, other intake buildings) through the native template module. While the intake's
  /// column holds an extra fluid at or above that fluid's refusal share, it blocks the building through the native
  /// <c>BlockableObject</c> (workshops and <c>WaterMover</c> stop) and shows the fluid's own status; it resumes below.
  /// One status per refusing fluid; no hysteresis. It reads the last completed fluid tick, so before a scene's first
  /// completed tick it decides nothing. An entity with an <see cref="IFluidCustomIntake"/> component draws through
  /// extraction requests and is left alone.
  /// </summary>
  public sealed class FluidWaterIntakeGuard : TickableComponent, IAwakableComponent, IInitializableEntity, IFinishedStateListener {
    /// <summary>The native status icon of a building blocked by contamination.</summary>
    public const string StatusSprite = "BuildingBlockedByContamination";
    private readonly ModdableFluidsSceneOwner _owner;
    private readonly ILoc _loc;
    private WaterInput _input;
    private BlockableObject _blockable;
    private StatusToggle[] _statuses;
    private bool[] _active;
    private bool _exempt, _blocked;
    /// <summary>Registry slots of the fluids refusing this intake now.</summary>
    public IReadOnlyList<int> Refusing { get; private set; } = Array.Empty<int>();
    public bool IsExempt => _exempt;
    public bool IsBlocked => _blocked;

    public FluidWaterIntakeGuard(ModdableFluidsSceneOwner owner, ILoc loc) { _owner = owner; _loc = loc; }

    public void Awake() {
      _exempt = GetComponent<IFluidCustomIntake>() != null;
      _input = GetComponent<WaterInput>();
      _blockable = GetComponent<BlockableObject>();
      if (!_exempt && _blockable == null)
        throw new InvalidOperationException("Moddable Fluids' water-intake guard needs the native BlockableObject on " + Name + "; a water intake without one cannot be stopped");
      var registry = ModdableFluidsEntry.Host.Registry;
      _statuses = new StatusToggle[registry.Count]; _active = new bool[registry.Count];
      for (int i = 0; i < registry.Count; i++) {
        var policy = registry.Definitions[i].WaterIntake;
        if (policy != null) _statuses[i] = StatusToggle.CreateNormalStatusWithAlertAndFloatingIcon(StatusSprite, _loc.T(policy.RefusedStatusLocKey), _loc.T(policy.RefusedAlertLocKey));
      }
      DisableComponent();
    }

    public void InitializeEntity() {
      if (_exempt) return;
      var subject = GetComponent<StatusSubject>();
      foreach (var status in _statuses) if (status != null) subject.RegisterStatus(status);
    }

    public void OnEnterFinishedState() {
      if (_exempt) return;
      EnableComponent();
      Evaluate();
    }

    public void OnExitFinishedState() {
      if (_exempt) return;
      DisableComponent();
      Apply(Array.Empty<int>());
    }

    public override void Tick() => Evaluate();

    private void Evaluate() {
      var world = _owner.World;
      if (world == null || !world.HasState) return;
      var cell = _input.Coordinates;
      Apply(world.TrySample(cell.x, cell.y, cell.z, out var sample) ? FluidIntakeRefusal.Refusing(world.Registry, sample) : Array.Empty<int>());
    }

    private void Apply(IReadOnlyList<int> refusing) {
      Refusing = refusing;
      for (int i = 0; i < _statuses.Length; i++) {
        if (_statuses[i] == null) continue;
        bool on = refusing.Contains(i);
        if (on == _active[i]) continue;
        _active[i] = on;
        if (on) _statuses[i].Activate(); else _statuses[i].Deactivate();
      }
      bool blocked = refusing.Count > 0;
      if (blocked == _blocked) return;
      _blocked = blocked;
      if (blocked) _blockable.Block(this); else _blockable.Unblock(this);
    }

    /// <summary>The template module that decorates every native <c>WaterInput</c> with the guard.</summary>
    public static TemplateModule Module() {
      var builder = new TemplateModule.Builder();
      builder.AddDecorator<WaterInput, FluidWaterIntakeGuard>();
      return builder.Build();
    }

    /// <summary>
    /// The native members the guard compiles against, checked before it is bound so a changed game fails with one
    /// message at scene start instead of a missing-member error in the first intake.
    /// </summary>
    public static IReadOnlyList<string> CheckContract() {
      const BindingFlags members = BindingFlags.Instance | BindingFlags.Public;
      var problems = new List<string>();
      void Require(bool ok, string member) { if (!ok) problems.Add(member); }
      Require(typeof(WaterInput).GetProperty("Coordinates", members)?.PropertyType == typeof(Vector3Int), "WaterInput.Coordinates : Vector3Int");
      Require(typeof(BlockableObject).GetMethod("Block", members, null, new[] { typeof(object) }, null) != null, "BlockableObject.Block(object)");
      Require(typeof(BlockableObject).GetMethod("Unblock", members, null, new[] { typeof(object) }, null) != null, "BlockableObject.Unblock(object)");
      Require(typeof(StatusToggle).GetMethod("CreateNormalStatusWithAlertAndFloatingIcon", BindingFlags.Static | BindingFlags.Public, null,
        new[] { typeof(string), typeof(string), typeof(string), typeof(float) }, null)?.ReturnType == typeof(StatusToggle), "StatusToggle.CreateNormalStatusWithAlertAndFloatingIcon(string, string, string, float)");
      Require(typeof(StatusToggle).GetMethod("Activate", members, null, Type.EmptyTypes, null) != null && typeof(StatusToggle).GetMethod("Deactivate", members, null, Type.EmptyTypes, null) != null,
        "StatusToggle.Activate() and Deactivate()");
      Require(typeof(StatusSubject).GetMethod("RegisterStatus", members, null, new[] { typeof(StatusToggle) }, null) != null, "StatusSubject.RegisterStatus(StatusToggle)");
      Require(typeof(TemplateModule.Builder).GetMethods(members).Any(m => m.Name == "AddDecorator" && m.IsGenericMethodDefinition && m.GetGenericArguments().Length == 2),
        "TemplateModule.Builder.AddDecorator<TSubject, TDecorator>()");
      Require(typeof(ILoc).GetMethod("T", new[] { typeof(string) })?.ReturnType == typeof(string), "ILoc.T(string) : string");
      return problems;
    }
  }
}
