using System;
using ModdableFluids;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.EntitySystem;
using Timberborn.Localization;
using Timberborn.Persistence;
using Timberborn.StatusSystem;
using Timberborn.TickSystem;
using Timberborn.WaterBuildings;
using Timberborn.Workshops;
using Timberborn.WorldPersistence;

namespace MoreFluids {
  /// <summary>Marks the Fluid Extractor (<c>MoreFluidsFluidExtractor.&lt;Faction&gt;</c>).</summary>
  internal record MoreFluidsFluidExtractorSpec : ComponentSpec { }

  /// <summary>Marks the Desalinator (<c>MoreFluidsDesalinator.&lt;Faction&gt;</c>).</summary>
  internal record MoreFluidsDesalinatorSpec : ComponentSpec { }

  /// <summary>
  /// A manufactory that draws one fluid through its native intake pipe, like a vanilla pump with
  /// <c>ManufactoryWaterConsumer</c> and <c>WaterInputManufactoryLimiter</c>, but through Moddable Fluids' selective
  /// extraction: only that fluid leaves the column, and only while its share there is high enough (otherwise the
  /// building shows its status and stops). As <see cref="IFluidCustomIntake"/>, Moddable Fluids' water-intake guard
  /// leaves it alone. The drawn, unused volume is saved with the building.
  /// </summary>
  internal abstract class FluidIntake : TickableComponent, IAwakableComponent, IInitializableEntity, IFinishedStateListener, IPersistentEntity,
      IManufactoryLimiter, IFluidCustomIntake {
    private const string StatusSprite = "NothingToDo";
    private static readonly PropertyKey<float> StoredKey = new PropertyKey<float>("Stored");
    private readonly MoreFluidsScene _fluids;
    private readonly ILoc _loc;
    private readonly FluidIntakeBuffer _buffer = new FluidIntakeBuffer();
    private Manufactory _manufactory;
    private WaterInput _input;
    private StatusToggle _status;
    private FluidIntakeRecipe _recipe;
    private bool _starved = true;

    protected FluidIntake(MoreFluidsScene fluids, ILoc loc) { _fluids = fluids; _loc = loc; }

    protected abstract ComponentKey SaveKey { get; }
    /// <summary>Owned ID reported with this building's extraction losses.</summary>
    protected abstract string RequesterId { get; }
    protected abstract string StatusLocKey { get; }
    protected abstract FluidIntakeRecipe Read(FluidRegistry registry, string productGood, int productAmount);

    public void Awake() {
      _manufactory = GetComponent<Manufactory>();
      _input = GetComponent<WaterInput>();
      if (_manufactory == null || _input == null) throw new InvalidOperationException(GetType().Name + " requires the native Manufactory and WaterInput");
      _status = StatusToggle.CreateNormalStatusWithFloatingIcon(StatusSprite, _loc.T(StatusLocKey));
      DisableComponent();
    }

    public void InitializeEntity() {
      GetComponent<StatusSubject>().RegisterStatus(_status);
      _manufactory.RecipeChanged += (_, _) => _recipe = null;
      _manufactory.ProductionProgressed += (_, e) => _buffer.Consume(e.ProductionProgressChange * Recipe().VolumePerCycle);
    }

    public void OnEnterFinishedState() => EnableComponent();

    public void OnExitFinishedState() {
      DisableComponent();
      _starved = true;
      _status.Deactivate();
    }

    // The status and efficiency follow the intake column at the last completed fluid tick; the extraction itself
    // checks the minimum share again when it is resolved.
    public override void Tick() {
      var world = _fluids.Scene.World;
      if (!_manufactory.HasCurrentRecipe || !world.HasState || !_input.IsUnderwater) {
        _starved = true;
        _status.Deactivate();
        return;
      }
      var recipe = Recipe();
      var cell = _input.Coordinates;
      _starved = !world.TrySample(cell.x, cell.y, cell.z, out var column) || !recipe.Accepts(column.GetShare(recipe.Fluid));
      _status.Toggle(_starved);
    }

    public float ProductionEfficiency() => _starved ? 0f : 1f;

    public float MaxProductionProgressChange(float expectedProductionProgressChange) {
      if (_starved) return 0f;
      var recipe = Recipe();
      double request = _buffer.Demand(expectedProductionProgressChange * recipe.VolumePerCycle);
      if (request > 0) {
        var cell = _input.Coordinates;
        _fluids.Scene.Extraction.RequestExtraction(RequesterId, cell.x, cell.y, cell.z, recipe.Fluid, request, recipe.MinimumShare,
          resolved => _buffer.Resolve(resolved.ExtractedVolume));
      }
      return (float)_buffer.MaxProgress(recipe.VolumePerCycle);
    }

    private FluidIntakeRecipe Recipe() {
      if (_recipe != null) return _recipe;
      var products = _manufactory.CurrentRecipe.Products;
      if (products.Length != 1) throw new InvalidOperationException(GetType().Name + " recipe " + _manufactory.CurrentRecipe.Id + " must make exactly one good");
      return _recipe = Read(_fluids.Scene.Registry, products[0].Id, products[0].Amount);
    }

    public void Save(IEntitySaver entitySaver) {
      if (_buffer.Stored > 0) entitySaver.GetComponent(SaveKey).Set(StoredKey, (float)_buffer.Stored);
    }

    public void Load(IEntityLoader entityLoader) {
      if (entityLoader.TryGetComponent(SaveKey, out var loader)) _buffer.Load(loader.Get(StoredKey));
    }
  }

  /// <summary>Coffee into Coffee (Iron Teeth) or healing water into Antidote (Folktails); "Too dilute" below the extractor's share.</summary>
  internal sealed class FluidExtractor : FluidIntake {
    private static readonly ComponentKey Key = new ComponentKey("MoreFluids.FluidExtractor");
    public FluidExtractor(MoreFluidsScene fluids, ILoc loc) : base(fluids, loc) { }
    protected override ComponentKey SaveKey => Key;
    protected override string RequesterId => "MoreFluids.FluidExtractor";
    protected override string StatusLocKey => "MoreFluids.Status.TooDilute";
    protected override FluidIntakeRecipe Read(FluidRegistry registry, string productGood, int productAmount) => FluidIntakeRecipe.Extraction(registry, productGood, productAmount);
  }

  /// <summary>Saltwater into Water: 0.3 saltwater per Water good, of which 0.1 leaves as brine (all of it in this requester's extraction losses).</summary>
  internal sealed class Desalinator : FluidIntake {
    private static readonly ComponentKey Key = new ComponentKey("MoreFluids.Desalinator");
    public Desalinator(MoreFluidsScene fluids, ILoc loc) : base(fluids, loc) { }
    protected override ComponentKey SaveKey => Key;
    protected override string RequesterId => "MoreFluids.Desalinator";
    protected override string StatusLocKey => "MoreFluids.Status.NoSaltwater";
    protected override FluidIntakeRecipe Read(FluidRegistry registry, string productGood, int productAmount) => FluidIntakeRecipe.Desalination(registry, productGood, productAmount);
  }
}
