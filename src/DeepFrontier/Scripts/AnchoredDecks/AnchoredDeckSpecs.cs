using Timberborn.BlueprintSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Marks a structure whose top may carry the bracket cleat of an anchored
  // concrete deck (currently only ReinforcedDamBlock). Names are prefixed to
  // avoid colliding with other mods' spec names (More Platforms ships
  // SidePlatformSpec).
  internal record AnchoredDeckAnchorSpec : ComponentSpec;

  // A legless concrete deck hung beside an anchor block at the same layer.
  // Anchor is the local cell of the anchor block, beside the deck edge at the
  // deck layer (z = 0). Its x is the centre column of an odd-width grid so
  // it stays under the cursor when the player flips the deck. The deck's only foundation block is the cleat directly
  // above it (Anchor + up): MatterBelow Stackable, Occupations Floor. Native
  // support, load validation, stack deletion and the "object atop" deletion
  // blocker all follow from that cleat; this spec only names the anchor so the
  // preview validator can require the anchor component.
  internal record AnchoredDeckSpec : ComponentSpec {
    [Serialize] public Vector3Int Anchor { get; init; }
  }
}
