// Materials Laboratory icon candidate, rendered in the vanilla icon style by
// tools/native_icon_style.mjs. research_building_content.mjs promotes it.
import {readFile} from 'node:fs/promises';
import {writeNativeIcon} from './native_icon_style.mjs';
const root=new URL('../',import.meta.url);
const svg=await readFile(new URL('src/DeepFrontier/Art/Icons/MaterialsLaboratory.svg',root));
const result=await writeNativeIcon(svg,'building',
  new URL('outputs/research-integration/Data/Buildings/Science/MaterialsLaboratory/Icon.png',root),'MaterialsLaboratory');
console.log(`MaterialsLaboratory native-style icon candidate exported (${result.stroke.toFixed(1)} px lines).`);
