// Reinforced hydro turbine icon candidate, rendered in the vanilla icon style by
// tools/native_icon_style.mjs. hydro_building_content.mjs promotes it.
import {readFile} from 'node:fs/promises';
import {writeNativeIcon} from './native_icon_style.mjs';
const root=new URL('../',import.meta.url);
const svg=await readFile(new URL('src/DeepFrontier/Art/Icons/ReinforcedHydroTurbine.svg',root));
const result=await writeNativeIcon(svg,'building',
  new URL('outputs/hydro-integration/Data/Buildings/Power/ReinforcedHydroTurbine/Icon.png',root),'ReinforcedHydroTurbine');
console.log(`ReinforcedHydroTurbine native-style icon candidate exported (${result.stroke.toFixed(1)} px lines).`);
