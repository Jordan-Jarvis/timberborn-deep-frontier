// Shaft connections on every solid wall (user direction, 2026-10-21).
// Since 2026-10-23 the generated families' lists only seed the authored
// order: tools/connection_content.mjs keeps their entries that are still flat
// exterior faces and adds every other one (outputs/connection-faces).
//
// A native TransputProviderSpec transput is one building cell plus the faces
// a shaft may meet. Every fully occupied ('All') cell gets each horizontal
// face whose neighbour is open ground a shaft can stand in (outside the
// footprint, or an unoccupied cell inside it), plus 'Bottom' on the ground
// layer, as vanilla buildings and roomPowerFaces do. Faces toward door or
// entrance cells are excluded so shafts never block access. Existing
// authored sockets are kept, so tested connections stay valid.
//
// Optional `walls`: the horizontal faces an authored wall actually closes,
// as [x, y, z, 'Left'|'Right'|'Down'|'Up'] entries (measured from the saved
// scene). When given, a generated horizontal face is offered only if it is
// listed, and every horizontal direction of a kept socket must be listed
// (an unlisted one throws). 'Bottom' keeps the vanilla ground-layer rule.
// Callers that omit `walls` get exactly the previous behaviour.
const SIDES = [[-1, 0, 'Left'], [1, 0, 'Right'], [0, -1, 'Down'], [0, 1, 'Up']];
const ORDER = ['Left', 'Right', 'Down', 'Up', 'Bottom', 'Top'];

export function solidPowerFaces(blocks, size, {exclude = [], keep = [], walls} = {}) {
  const [w, h, layers] = Array.isArray(size) ? size : [size.X, size.Y, size.Z];
  if (blocks.length !== w * h * layers) throw new Error('Block count does not match the footprint');
  const index = ([x, y, z]) => (z * h + y) * w + x;
  const inside = ([x, y, z]) => x >= 0 && y >= 0 && z >= 0 && x < w && y < h && z < layers;
  const free = (c) => !inside(c) || blocks[index(c)].Occupations === 'None';
  const blocked = new Set(exclude.map((c) => c.join(',')));
  let walled = null;
  if (walls !== undefined) {
    walled = new Set();
    for (const face of walls) {
      if (!Array.isArray(face) || face.length !== 4 || !SIDES.some(([, , name]) => name === face[3]) || !inside(face.slice(0, 3)))
        throw new Error('Invalid wall face ' + JSON.stringify(face));
      walled.add(face.join(','));
    }
  }
  const closed = (cell, direction) => walled === null || walled.has([...cell, direction].join(','));
  const faces = new Map();
  const add = (cell, direction) => {
    const key = cell.join(',');
    if (!faces.has(key)) faces.set(key, {cell, directions: new Set()});
    faces.get(key).directions.add(direction);
  };
  for (let z = 0; z < layers; z++) for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    if (blocks[index([x, y, z])].Occupations !== 'All') continue;
    for (const [dx, dy, name] of SIDES) {
      const neighbour = [x + dx, y + dy, z];
      if (free(neighbour) && !blocked.has(neighbour.join(',')) && closed([x, y, z], name)) add([x, y, z], name);
    }
    if (z === 0) add([x, y, z], 'Bottom');
  }
  for (const t of keep) {
    const cell = [t.Coordinates.X, t.Coordinates.Y, t.Coordinates.Z];
    // Authored sockets were tested in game, including some on walkway cells.
    if (!inside(cell) || blocks[index(cell)].Occupations === 'None') throw new Error('Kept power socket is not on an occupied cell: ' + cell);
    for (const d of t.Directions.split(',').map((s) => s.trim())) {
      if (!ORDER.includes(d)) throw new Error('Unknown transput direction ' + d);
      if (SIDES.some(([, , name]) => name === d) && !closed(cell, d))
        throw new Error('Kept power socket has no wall: ' + cell + ' ' + d);
      add(cell, d);
    }
  }
  // Kept sockets stay first, in their authored order (acceptance fixtures may
  // rely on the first entry); generated ones follow in grid order.
  const keptKeys = keep.map((t) => [t.Coordinates.X, t.Coordinates.Y, t.Coordinates.Z].join(','));
  const keys = [...new Set([...keptKeys, ...faces.keys()])];
  return keys.map((key) => {
    const {cell, directions} = faces.get(key);
    const [X, Y, Z] = cell;
    return {Coordinates: {X, Y, Z}, Directions: ORDER.filter((d) => directions.has(d)).join(', '), ReverseRotation: false};
  });
}
