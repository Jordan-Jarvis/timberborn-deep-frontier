// Access to a building whose doorstep stands over its understructure
// (Deep Mine over the Deep Ore Vein, quarries over their Deep Seam, since the
// 5x5 second shrink, 2026-11-01).
//
// Over the marker the building may claim only Top (UnderstructureFinder.FindStrict),
// so the doorstep is a Top-only cell on the marker's Floor|Bottom|Corners cell.
// The native navmesh does not walk from the entrance path into such a cell by
// itself: vanilla EfficientMine (1.1.2.8 blueprint), whose doorstep (2, 0) stands
// over UndergroundRuins the same way, adds the edges entrance (2, -1, 0) ->
// (2, 0, 0) -> ... -> (2, 2, 0) and puts its LocalAccess at (2.5, 0, 2.5), the
// centre of the last cell. Without them the access was unreachable on build 239:
// the all-buildings sites batch found the Deep Mine and both quarries "not
// connected to any district" with "inaccessible" entrances and no production.
// Here: one two-way edge from the entrance into the doorstep and the access at
// the doorstep's centre.
export function doorstepOverUnderstructure(entrance, doorstep, id) {
  const [ex, ey, ez] = entrance, [dx, dy, dz] = doorstep;
  if (ez !== 0 || dz !== 0 || Math.abs(ex - dx) + Math.abs(ey - dy) !== 1)
    throw new Error(`${id}: entrance ${entrance} and doorstep ${doorstep} must be neighbouring ground cells`);
  return {
    edgeGroup: {Cost: 1.0, Group: {UseGroup: false, GroupName: ''}, IsPath: false,
      AddedEdges: [{Start: {X: ex, Y: ey, Z: 0}, End: {X: dx, Y: dy, Z: 0}, IsTwoWay: true}]},
    // LocalAccess is (x, height, y), as BuildingAccessibleSpec stores it.
    localAccess: {X: dx + 0.5, Y: 0, Z: dy + 0.5},
  };
}
