import fs from 'node:fs/promises';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const root='C:/Users/Jordan/Documents/TimberbornModding';
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(`${root}/outputs/Timberborn_Deep_Frontier_Balance_Workbook.xlsx`));
console.log((await wb.inspect({kind:'match',searchTerm:'Materials Laboratory',options:{maxResults:8},summary:'Existing laboratory rows'})).ndjson);
const preview=await wb.render({sheetName:'Buildings',range:'B62:Q62',scale:1,format:'png'});
await fs.writeFile(`${root}/outputs/research-workbook-before.png`,new Uint8Array(await preview.arrayBuffer()));
