import fs from 'node:fs/promises';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
import {fileURLToPath} from 'node:url';
const root=new URL('../',import.meta.url);
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(fileURLToPath(new URL('outputs/Timberborn_Deep_Frontier_Balance_Workbook.xlsx',root))));
for(const [sheet,range] of [['Buildings','A13:AL13'],['Recipes','A17:X17'],['Overview','A35:F37']]) {
  console.log((await wb.inspect({kind:'table',range:`${sheet}!${range}`,include:'values,formulas',tableMaxRows:4,tableMaxCols:38,maxChars:4000})).ndjson);
}
const preview=await wb.render({sheetName:'Buildings',range:'B12:Q14',scale:1,format:'png'});
await fs.writeFile(new URL('outputs/restaurant-workbook-before.png',root),new Uint8Array(await preview.arrayBuffer()));
