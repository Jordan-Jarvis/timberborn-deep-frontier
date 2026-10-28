using System.Collections.Generic;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockSystem;
using Timberborn.EntityPanelSystem;
using Timberborn.EntitySystem;
using Timberborn.Localization;
using Timberborn.NaturalResources;
using Timberborn.NaturalResourcesLifecycle;
using Timberborn.Persistence;
using Timberborn.WorldPersistence;
using UnityEngine;

namespace DeepFrontier.Scripts.Radiation {
  // Irradiated ground kills plants at once (user rule 2026-10-22). "Irradiated"
  // is RadiationSimulation.SoilAt (stored soil or the bank layer) at or above
  // RadiationTuning.IrradiatedGroundThreshold, the level where the yellow-green
  // ground tint appears, so what the player sees is what kills.
  //
  // Native death path (Timberborn 1.1.2.8): LivingNaturalResource.Die, where
  // native contamination and drought deaths end (ContaminatedNaturalResource
  // and WateredNaturalResource run a time trigger that calls it). Died then
  // drives the native dead state: Growable stops, Crop and the dead models
  // switch, DeadCuttableYieldRemover / EmptyDeadNaturalResourceOverrider make
  // the remains clearable. Nothing is deleted.
  //
  // Three moments, together covering "same tick":
  // - ground becomes irradiated under a standing plant:
  //   RadiationSimulation.KillOnIrradiatedGround, every tick, on the rows that
  //   hold soil radiation or banks (a slot is checked when it turns irradiated
  //   or its column geometry changes);
  // - a plant is planted or spawned on irradiated ground:
  //   IrradiatedGroundDeath.PostInitializeEntity;
  // - natural spreading does not seed irradiated ground at all
  //   (IrradiatedGroundSpawnValidator, as native ContaminatedNaturalResourceSpawnValidator
  //   keeps plants off contaminated soil).

  // Planting on irradiated ground stays allowed (user decision); this makes the
  // consequence visible. Decorated on every PlantableSpec (crops and trees):
  // native PlantableDescriber builds the planting tool's tooltip from the
  // template preview's describers, and the entity panel shows the same section.
  internal sealed class IrradiatedPlantWarning : BaseComponent, IEntityDescriber {
    private const int DescriptionOrder = 121;
    private readonly ILoc _loc;

    public IrradiatedPlantWarning(ILoc loc) { _loc = loc; }

    public IEnumerable<EntityDescription> DescribeEntity() {
      yield return EntityDescription.CreateTextSection(_loc.T(RadiationLoc.PlantingWarning), DescriptionOrder);
    }
  }

  // Decorated on every NaturalResourceSpec (the spec native LivingNaturalResource
  // is decorated on): kills a plant created on irradiated ground.
  //
  // Saves: this replaces RadiationFloraDose (per-plant dose, component key
  // "DeepFrontier.RadiationFloraDose", saves up to 2026-10-22). Native entity
  // loading only reads the keys a component asks for (WorldPersistence
  // EntityLoader.TryGetComponent), so the old key would be ignored anyway; Load
  // reads it explicitly and discards it: a dose means nothing once death is
  // immediate, and plants on irradiated ground die on the first tick after the
  // load (KillOnIrradiatedGround starts with no slot checked). Nothing is saved.
  internal sealed class IrradiatedGroundDeath : BaseComponent, IAwakableComponent, IPostInitializableEntity, IPersistentEntity {
    private static readonly ComponentKey LegacyFloraDoseKey = new ComponentKey("DeepFrontier.RadiationFloraDose");
    private static readonly PropertyKey<float> LegacyDoseKey = new PropertyKey<float>("Dose");
    private readonly RadiationSimulation _simulation;
    private LivingNaturalResource _living;
    private BlockObject _block;

    public IrradiatedGroundDeath(RadiationSimulation simulation) { _simulation = simulation; }

    public void Awake() {
      _living = GetComponent<LivingNaturalResource>();
      if (_living == null) throw new System.InvalidOperationException("IrradiatedGroundDeath requires the native LivingNaturalResource");
      _block = GetComponent<BlockObject>();
      if (_block == null) throw new System.InvalidOperationException("IrradiatedGroundDeath requires the native BlockObject");
    }

    // After every component's InitializeEntity, so every native Died listener
    // (subscribed in Awake or InitializeEntity) sees the death.
    public void PostInitializeEntity() {
      if (_block.IsPreview || _living.IsDead) return;
      if (_simulation.IsIrradiatedGround(_block.Coordinates)) _living.Die();
    }

    public void Save(IEntitySaver entitySaver) { }

    public void Load(IEntityLoader entityLoader) {
      // Legacy flora dose (see above): read and discarded on purpose.
      if (entityLoader.TryGetComponent(LegacyFloraDoseKey, out var legacy)) legacy.Get(LegacyDoseKey);
    }
  }

  // Native natural spreading (SpawnValidationService, MultiBind<ISpawnValidator>)
  // does not seed irradiated ground.
  internal sealed class IrradiatedGroundSpawnValidator : ISpawnValidator {
    private readonly RadiationSimulation _simulation;
    public IrradiatedGroundSpawnValidator(RadiationSimulation simulation) { _simulation = simulation; }
    public bool CanSpawn(Vector3Int coordinates, string resourceTemplateName) => !_simulation.IsIrradiatedGround(coordinates);
  }
}
