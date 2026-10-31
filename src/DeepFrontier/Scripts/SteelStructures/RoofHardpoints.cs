using System;
using System.Collections.Immutable;
using System.Linq;
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockObjectModelSystem;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.Buildings;
using Timberborn.Common;
using Timberborn.EntitySystem;
using Timberborn.Localization;
using Timberborn.TemplateInstantiation;
using UnityEngine;

namespace DeepFrontier.Scripts.SteelStructures {
  // Roof hardpoints (docs/platforms-design.md, slice 3 "D1"): the top cells of
  // a building's roofs that are not flat, made native stackable blocks by
  // tools/roof_hardpoint_content.mjs, so steel legs can stand on any building
  // with fully native support, picking, load validation, stack deletion and
  // the building's "object atop" deletion blocker. Flat roofs stay what they
  // were (platforms for everything); a hardpoint is for steel supports only.
  internal record RoofHardpointsSpec : ComponentSpec {
    // Local block coordinates of the hardpoint cells (the top cell; the steel
    // piece stands in the cell above).
    [Serialize] public ImmutableArray<Vector3Int> Cells { get; init; }
  }

  // A steel piece that may stand on a roof hardpoint: the steel columns, the
  // steel decks and the leg deck tools.
  internal record SteelSupportSpec : ComponentSpec;

  // A steel column's sleeve: a node of its finished model one layer below its
  // foot, shown while the column stands on a hardpoint so the leg visibly
  // enters the roof.
  internal record HardpointSleeveSpec : ComponentSpec {
    [Serialize] public string NodeName { get; init; }
  }

  internal static class RoofHardpointLoc {
    // English source text: tools/structural_building_content.mjs (STEEL_LEG_ROWS).
    public const string SteelOnly="DeepFrontier.RoofHardpoints.SteelOnly";
  }

  internal sealed class RoofHardpointService {
    private readonly IBlockService _blocks;
    public RoofHardpointService(IBlockService blocks) {_blocks=blocks;}

    // Whether the cell is a hardpoint of a placed building.
    public bool IsHardpoint(Vector3Int cell) {
      if(!_blocks.Contains(cell))return false;
      var objects=_blocks.GetObjectsAt(cell);
      for(int i=0;i<objects.Count;i++) {
        var spec=objects[i].GetComponent<RoofHardpointsSpec>();
        if(spec==null)continue;
        foreach(var local in spec.Cells)
          if(objects[i].TransformCoordinates(local)==cell)return true;
      }
      return false;
    }
  }

  // Only steel supports may rest on a hardpoint; every other preview whose
  // foundation would stand on one is refused, so paths, platforms and
  // buildings still need a flat roof. Previews only: native load validation
  // deletes any loaded object that fails a validator, and what stands on a
  // hardpoint was valid when it was placed.
  internal sealed class RoofHardpointValidator : IBlockObjectValidator {
    private readonly RoofHardpointService _hardpoints;
    private readonly ILoc _loc;
    public RoofHardpointValidator(RoofHardpointService hardpoints,ILoc loc) {_hardpoints=hardpoints;_loc=loc;}
    public bool IsValid(BlockObject blockObject,out string errorMessage) {
      errorMessage=null;
      if(!blockObject.IsPreview||blockObject.HasComponent<SteelSupportSpec>())return true;
      foreach(Vector3Int foundation in blockObject.PositionedBlocks.GetFoundationCoordinates())
        if(_hardpoints.IsHardpoint(foundation.Below())) {
          errorMessage=_loc.T(RoofHardpointLoc.SteelOnly);
          return false;
        }
      return true;
    }
  }

  internal sealed class HardpointSleeve : BaseComponent, IAwakableComponent, IInitializableEntity,
      IPostInitializableEntity, IPostPlacementChangeListener, IModelUpdater {
    private readonly RoofHardpointService _hardpoints;
    private BlockObject _block;
    private GameObject _sleeve;
    public HardpointSleeve(RoofHardpointService hardpoints) {_hardpoints=hardpoints;}

    public void Awake() {
      _block=GetComponent<BlockObject>();
      var name=GetComponent<HardpointSleeveSpec>().NodeName;
      var finished=GameObject.FindChildIfNameNotEmpty(GetComponent<BuildingModelSpec>().FinishedModelName);
      if(finished==null||string.IsNullOrEmpty(name))throw new InvalidOperationException("A hardpoint sleeve needs a finished model and a node name");
      var matches=finished.GetComponentsInChildren<Transform>(true).Where(t=>t.name==name).ToArray();
      if(matches.Length!=1)throw new InvalidOperationException("Hardpoint sleeve node must exist exactly once: "+name);
      _sleeve=matches[0].gameObject;
      _sleeve.SetActive(false);
    }

    public void InitializeEntity()=>Refresh();
    public void PostInitializeEntity()=>Refresh();
    public void OnPostPlacementChanged()=>Refresh();
    public void UpdateModel()=>Refresh();

    // The building under a column cannot be deleted while the column stands
    // (native BlockObjectAtopDeletionBlocker), so placement and model updates
    // are the only times the answer changes.
    private void Refresh() {
      var show=_block.Positioned&&_hardpoints.IsHardpoint(_block.Coordinates.Below());
      if(_sleeve.activeSelf!=show)_sleeve.SetActive(show);
    }
  }

  [Context("Game")]
  public sealed class RoofHardpointConfigurator : Configurator {
    protected override void Configure() {
      Bind<RoofHardpointService>().AsSingleton();
      Bind<RoofHardpointValidator>().AsSingleton();
      MultiBind<IBlockObjectValidator>().ToExisting<RoofHardpointValidator>();
      Bind<HardpointSleeve>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }
    private static TemplateModule Provide() {
      var b=new TemplateModule.Builder();
      b.AddDecorator<HardpointSleeveSpec,HardpointSleeve>();
      return b.Build();
    }
  }
}
