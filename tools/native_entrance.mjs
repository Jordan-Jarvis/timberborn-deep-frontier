// The native Entrance of a generated building, from the door cell of its layout.
//
// Vanilla convention (138 of 139 shipped Timberborn 1.1.2.8 buildings; the exception is the
// Folktails Carousel): BlockObjectSpec.Entrance is the path cell in front of the door, and its
// native doorstep (PositionedEntrance.DoorstepCoordinates = Entrance - Direction2D offset, the
// direction always Down before rotation) is the door cell, one step north. A player's ordinary
// Path laid on that Entrance cell is the building's access: BuildingAccessible puts the access at
// the Entrance cell centre, and DynamicPathModel draws the path's connection stub toward the
// entrance flag on that path cell.
//
// An Entrance on the door cell itself (FisheryWorks and FishHatchery until 2026-10-26) puts the
// access inside the building's own block, where a player cannot lay a Path: the path in front of
// the door shows no connection stub (FisheryWorks), or the access is not on the road network at
// all and the building reports "not connected" (FishHatchery, whose bank-row door is a floor
// without a Path occupation). civic_building_content.mjs fixed the Restaurant the same way.
//
// door: [x, y, z] local door cell (layout `entrance`), at the entrance level.
// Returns the native Entrance [x, y - 1, z] after checking that the door is occupied by the
// building and that the Entrance cell is open (outside the footprint, or an unoccupied cell).
export function nativeEntrance(name, door, size, blocks) {
  const [w, d, h] = size;
  const index = ([x, y, z]) => (z * d + y) * w + x;
  const inside = ([x, y, z]) => x >= 0 && y >= 0 && z >= 0 && x < w && y < d && z < h;
  if (!inside(door) || blocks[index(door)].Occupations === 'None')
    throw new Error(`${name}: the door cell ${door} must be an occupied building cell (the native doorstep)`);
  const entrance = [door[0], door[1] - 1, door[2]];
  if (inside(entrance) && blocks[index(entrance)].Occupations !== 'None')
    throw new Error(`${name}: the Entrance path cell ${entrance} in front of the door is occupied by the building`);
  return entrance;
}
