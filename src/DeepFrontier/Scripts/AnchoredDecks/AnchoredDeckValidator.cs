using System;
using Timberborn.BlockSystem;
using Timberborn.Localization;
using UnityEngine;

namespace DeepFrontier.Scripts {
  internal static class AnchoredDeckLoc {
    // English source text: outputs/structural-integration/AnchoredDeckLocalization.enUS.csv
    // (rows are emitted by tools/structural_building_content.mjs).
    public const string RequiresAnchor="DeepFrontier.AnchoredDeck.RequiresAnchor";
  }

  // Hard placement rule for anchored decks: the cell beside the deck edge at the
  // deck layer must be the stackable top block of a structure carrying
  // AnchoredDeckAnchorSpec. Native MatterBelow already requires *some*
  // stackable block under the cleat; this narrows it to the anchor type.
  //
  // Only previews are checked. Placed decks are kept by the native stack
  // support chain through their cleat (BlockValidator on load,
  // TerrainPhysicsPostLoader, TerrainAndBlockObjectsToDeleteFinder and
  // BlockObjectAtopDeletionBlocker on the anchor). Validating placed objects
  // here would delete existing decks during load if load order or a later rule
  // change ever disagreed with this check.
  internal sealed class AnchoredDeckValidator : IBlockObjectValidator {
    private readonly IBlockService _blockService;
    private readonly ILoc _loc;

    public AnchoredDeckValidator(IBlockService blockService,ILoc loc) {
      _blockService=blockService;_loc=loc;
    }

    public bool IsValid(BlockObject blockObject,out string errorMessage) {
      errorMessage=null;
      if(!blockObject.IsPreview)return true;
      if(!blockObject.HasComponent<AnchoredDeckSpec>())return true;
      var spec=blockObject.GetComponent<AnchoredDeckSpec>();
      // Native picking places the CustomPivot (the anchor cell) without
      // FlipMode, while blocks flip as x -> width-1-x. Only the centre column
      // of an odd-width grid survives both flip states; any other anchor would
      // put a flipped deck's cleat beside the hovered anchor block.
      var width=blockObject.GetComponent<BlockObjectSpec>().Size.x;
      if(spec.Anchor.x*2!=width-1)
        throw new InvalidOperationException($"{blockObject.Name}: anchored deck anchor x {spec.Anchor.x} is not the flip-invariant centre of width {width}.");
      var anchor=blockObject.TransformCoordinates(spec.Anchor);
      var cleat=blockObject.PositionedBlocks.GetBlock(blockObject.TransformCoordinates(spec.Anchor+new Vector3Int(0,0,1)));
      if(cleat.MatterBelow!=MatterBelow.Stackable||cleat.Occupation!=BlockOccupations.Floor)
        throw new InvalidOperationException($"{blockObject.Name}: anchored deck cleat above {spec.Anchor} must be a Stackable/Floor block.");
      var objects=_blockService.GetObjectsAt(anchor);
      for(var i=0;i<objects.Count;i++) {
        var candidate=objects[i];
        if(candidate.HasComponent<AnchoredDeckAnchorSpec>()&&
           candidate.PositionedBlocks.GetBlock(anchor).Stackable==BlockStackable.BlockObject)
          return true;
      }
      errorMessage=_loc.T(AnchoredDeckLoc.RequiresAnchor);
      return false;
    }
  }
}
