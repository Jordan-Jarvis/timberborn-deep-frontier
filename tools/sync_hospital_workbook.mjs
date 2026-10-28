import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {FileBlob, SpreadsheetFile} from '@oai/artifact-tool';

// Narrow, ID-keyed workbook synchronization. No sheet reconstruction or styling.
const root = fileURLToPath(new URL('../', import.meta.url));
const workbookPath = `${root}outputs/Timberborn_Deep_Frontier_Balance_Workbook.xlsx`;
const reviewDir = `${root}outputs/hospital-workbook-sync`;
await fs.mkdir(reviewDir, {recursive: true});
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(workbookPath));
const mode = process.argv[2];
if (!['inspect', 'apply'].includes(mode)) throw new Error('Use inspect or apply.');

function findRow(sheetName, key, headerRow = 1) {
  const sheet = workbook.worksheets.getItem(sheetName);
  const values = sheet.getUsedRange().values;
  const rows = values.map((r, i) => r[0] === key ? i + 1 : null).filter(r => r !== null);
  if (rows.length !== 1) throw new Error(`${sheetName}: expected one ${key}, found ${rows.length}`);
  return {sheet, row: rows[0], headers: values[headerRow - 1], values: values[rows[0] - 1]};
}

const targets = {
  Buildings: findRow('Buildings', 'B011'),
  Transport: findRow('Transport', 'T018'),
  Sources: findRow('Sources', 'Hospital reference and native care', 4),
};
console.log((await workbook.inspect({kind: 'sheet', include: 'id,name', maxChars: 4000})).ndjson);
for (const [name, target] of Object.entries(targets)) {
  console.log(JSON.stringify({sheet: name, row: target.row, cells: Object.fromEntries(target.headers.map((h, i) => [h, target.values[i]]))}));
}

if (mode === 'apply') {
  const blueprint = JSON.parse(await fs.readFile(`${root}src/DeepFrontier/Data/Buildings/Wellbeing/Hospital/Hospital.IronTeeth.blueprint.json`, 'utf8'));
  const size = blueprint.BlockObjectSpec.Size;
  if (size.X !== 12 || size.Y !== 9 || size.Z !== 9 || blueprint.PlatformDeckSpec.Openings.length !== 42) {
    throw new Error('Hospital canonical 12x9x9 / 42-opening package has not been generated.');
  }
  const {hospitalBuildingUpdates, hospitalTransport, hospitalSource} = await import('./hospital_workbook.mjs');
  const changes = [];
  function update(name, column, value) {
    const target = targets[name];
    const cell = target.sheet.getCell(target.row - 1, column);
    const before = target.values[column];
    if (before === value) return;
    if (cell.formulas[0][0]) throw new Error(`Refusing to replace formula at ${name}, column ${column + 1}`);
    let n = column + 1, label = '';
    while (n > 0) { n--; label = String.fromCharCode(65 + n % 26) + label; n = Math.floor(n / 26); }
    changes.push({sheet: name, address: `${label}${target.row}`, before, after: value});
    cell.values = [[value]];
  }
  for (const [header, value] of Object.entries(hospitalBuildingUpdates.get('B011'))) {
    const matches = targets.Buildings.headers.map((h, i) => h === header ? i : null).filter(i => i !== null);
    if (matches.length !== 1) throw new Error(`Buildings header mismatch: ${header}`);
    update('Buildings', matches[0], value);
  }
  hospitalTransport.forEach((value, column) => update('Transport', column, value));
  hospitalSource.forEach((value, column) => update('Sources', column, value));
  workbook.recalculate();
  const errors = await workbook.inspect({kind: 'match', searchTerm: '#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!', options: {useRegex: true, maxResults: 100}, summary: 'Hospital sync formula error scan'});
  await fs.writeFile(`${reviewDir}/formula-error-scan.ndjson`, errors.ndjson);
  await fs.writeFile(`${reviewDir}/changes.json`, JSON.stringify(changes, null, 2));
  // The original remains untouched until the read-only preservation gate passes.
  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(`${reviewDir}/hospital-workbook.pending`);
  console.log(JSON.stringify({changedCells: changes.length, pendingFile: `${reviewDir}/hospital-workbook.pending`}));
}

for (const [name, start, end] of [['Buildings', 'B', 'Q'], ['Transport', 'C', 'L'], ['Sources', 'A', 'D']]) {
  const row = targets[name].row;
  const range = `${start}${row}:${end}${row}`;
  const preview = await workbook.render({sheetName: name, range, scale: 1, format: 'png'});
  await fs.writeFile(`${reviewDir}/${name}-${mode}.png`, new Uint8Array(await preview.arrayBuffer()));
}
if (mode === 'apply') {
  for (const [name, start, end] of [['Buildings', 'S', 'AA'], ['Buildings', 'AI', 'AJ'], ['Sources', 'D', 'H']]) {
    const row = targets[name].row;
    const preview = await workbook.render({sheetName: name, range: `${start}${row}:${end}${row}`, scale: 1, format: 'png'});
    await fs.writeFile(`${reviewDir}/${name}-${start}-${end}-apply.png`, new Uint8Array(await preview.arrayBuffer()));
  }
}
await fs.writeFile(`${reviewDir}/inspection.json`, JSON.stringify(Object.fromEntries(Object.entries(targets).map(([name, x]) => [name, {row: x.row, headers: x.headers, values: x.values}])), null, 2));
