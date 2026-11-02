using System;
using System.Collections.Generic;
using System.Linq;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.EntitySystem;
using Timberborn.Localization;
using Timberborn.SingletonSystem;
using Timberborn.StatusSystem;
using Timberborn.TickSystem;
using UnityEngine;

namespace DeepFrontier.Scripts.ModularStorage {
  internal record WarehouseModuleSpec : ComponentSpec {
    [Serialize] public int Capacity { get; init; }
  }

  // A Warehouse Module adds its Capacity (and a slot, up to the core's
  // MaxSlots) to the Modular Warehouse it is attached to. It holds no goods and
  // has no entrance. A finished module attached to no core shows the native
  // "UnconnectedBuilding" status icon.
  internal sealed class WarehouseModule : BaseComponent, IAwakableComponent, IInitializableEntity, IFinishedStateListener {
    public const string UnattachedLocKey = "DeepFrontier.ModularWarehouse.ModuleUnattached";
    private const string UnattachedSprite = "UnconnectedBuilding";
    private readonly ModularWarehouseNetwork _network;
    private readonly ILoc _loc;
    private WarehouseModuleSpec _spec;
    private StatusToggle _unattached;

    public WarehouseModule(ModularWarehouseNetwork network, ILoc loc) { _network = network; _loc = loc; }

    public int Capacity => _spec.Capacity;
    public ModularWarehouse Core { get; private set; }

    public void Awake() {
      _spec = GetComponent<WarehouseModuleSpec>();
      if (_spec.Capacity <= 0) throw new InvalidOperationException("WarehouseModuleSpec.Capacity must be positive");
      _unattached = StatusToggle.CreateNormalStatusWithFloatingIcon(UnattachedSprite, _loc.T(UnattachedLocKey));
      DisableComponent();
    }

    public void InitializeEntity() => GetComponent<StatusSubject>().RegisterStatus(_unattached);

    public void OnEnterFinishedState() {
      EnableComponent();
      _unattached.Activate();
      _network.Add(this);
    }

    public void OnExitFinishedState() {
      _network.Remove(this);
      Core = null;
      _unattached.Deactivate();
      DisableComponent();
    }

    public void SetCore(ModularWarehouse core) {
      Core = core;
      _unattached.Toggle(Enabled && core == null);
    }
  }

  // Which modules belong to which core. A finished module is attached when it
  // touches a finished core or an attached module face to face: side by side on
  // the same layer, or stacked (resting on its top, or carrying it). Diagonal
  // contact does not count. The search runs from every core at once (native
  // block occupancy, IBlockService.GetObjectsAt), so a module that touches two
  // networks joins the nearer core (ties: the core with the lower entity id).
  // It reruns on the tick after a core or module enters or leaves its finished
  // state, and once after loading (PostLoad, when every entity is loaded); each
  // core then gets its module count and capacity (ModularWarehouse.SetNetwork).
  internal sealed class ModularWarehouseNetwork : IPostLoadableSingleton, ITickableSingleton {
    private static readonly Vector3Int[] Faces = {
      new Vector3Int(1, 0, 0), new Vector3Int(-1, 0, 0), new Vector3Int(0, 1, 0),
      new Vector3Int(0, -1, 0), new Vector3Int(0, 0, 1), new Vector3Int(0, 0, -1)};
    private readonly IBlockService _blocks;
    private readonly HashSet<ModularWarehouse> _cores = new HashSet<ModularWarehouse>();
    private readonly HashSet<WarehouseModule> _modules = new HashSet<WarehouseModule>();
    private bool _loaded, _dirty;

    public ModularWarehouseNetwork(IBlockService blocks) { _blocks = blocks; }

    public void Add(ModularWarehouse core) { _cores.Add(core); _dirty = true; }
    public void Remove(ModularWarehouse core) { _cores.Remove(core); _dirty = true; }
    public void Add(WarehouseModule module) { _modules.Add(module); _dirty = true; }
    public void Remove(WarehouseModule module) { _modules.Remove(module); _dirty = true; }

    public void PostLoad() {
      _loaded = true;
      Update();
    }

    public void Tick() {
      if (_loaded && _dirty) Update();
    }

    private void Update() {
      _dirty = false;
      var cores = _cores.OrderBy(c => c.GetComponent<EntityComponent>().EntityId).ToList();
      var modules = _modules.ToDictionary(m => m.GetComponent<BlockObject>(), m => m);
      var owner = new Dictionary<WarehouseModule, ModularWarehouse>();
      var reached = new HashSet<BlockObject>(cores.Select(c => c.GetComponent<BlockObject>()));
      var queue = new Queue<(BlockObject Block, ModularWarehouse Core)>(cores.Select(c => (c.GetComponent<BlockObject>(), c)));
      while (queue.Count > 0) {
        var (block, core) = queue.Dequeue();
        foreach (var neighbour in Neighbours(block)) {
          if (!modules.TryGetValue(neighbour, out var module) || !reached.Add(neighbour)) continue;
          owner[module] = core;
          queue.Enqueue((neighbour, core));
        }
      }
      foreach (var core in cores) {
        var attached = owner.Where(o => o.Value == core).Select(o => o.Key).ToList();
        core.SetNetwork(attached.Count, core.GetComponent<ModularWarehouseSpec>().CoreCapacity + attached.Sum(m => m.Capacity));
      }
      foreach (var module in _modules) module.SetCore(owner.TryGetValue(module, out var core) ? core : null);
    }

    // Objects occupying a cell next to one of the block object's cells, across a face.
    private IEnumerable<BlockObject> Neighbours(BlockObject block) {
      var own = new HashSet<Vector3Int>(block.PositionedBlocks.GetOccupiedCoordinates());
      var seen = new HashSet<BlockObject>();
      foreach (var cell in own) {
        foreach (var face in Faces) {
          var next = cell + face;
          if (own.Contains(next)) continue;
          foreach (var other in _blocks.GetObjectsAt(next))
            if (other != block && seen.Add(other)) yield return other;
        }
      }
    }
  }
}
