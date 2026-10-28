// Civic room shafts only where an authored wall closes the face (2026-10-21).
//
// roomPowerFaces offers every exposed horizontal room face plus 'Bottom' on
// the ground layer. This keeps only the horizontal faces that the saved scene
// actually closes, as measured by tools/asset-pipeline/civic_wall_faces.py
// (outputs/civic-integration/<Model>-wall-faces.json); 'Bottom' keeps the
// vanilla ground-layer rule. The measurement must belong to the exact saved
// scene: a stale record fails explicitly instead of guessing.
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {roomPowerFaces} from './grid_structure.mjs';

const root = new URL('../', import.meta.url);

export async function wallRoomPowerFaces(ident, structure, size) {
  const record = JSON.parse(await readFile(new URL(`outputs/civic-integration/${ident}-wall-faces.json`, root), 'utf8'));
  const scene = await readFile(new URL(`src/DeepFrontier/Art/Source/${ident}-ReferenceStudy.blend`, root));
  if (record.model !== ident || record.sourceSha256 !== createHash('sha256').update(scene).digest('hex'))
    throw new Error(`${ident}: wall faces were measured on a different scene; rerun civic_wall_faces.py`);
  const walls = new Set(record.walls.map((f) => f.join(',')));
  const result = [];
  for (const t of roomPowerFaces(structure, size)) {
    const {X, Y, Z} = t.Coordinates;
    const directions = t.Directions.split(', ').filter((d) => d === 'Bottom' || walls.has([X, Y, Z, d].join(',')));
    if (directions.length) result.push({...t, Directions: directions.join(', ')});
  }
  if (!result.length) throw new Error(`${ident}: no authored wall closes a room face`);
  return result;
}
