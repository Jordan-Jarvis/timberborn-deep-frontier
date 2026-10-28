import {readFile} from 'node:fs/promises';
const root=new URL('../',import.meta.url);
const catalog=JSON.parse(await readFile(new URL('tools/structural_content.json',root),'utf8'));
const hydro=JSON.parse(await readFile(new URL('tools/hydro_content.json',root),'utf8'));
const name=id=>id.replace(/([a-z])([A-Z])/g,'$1 $2');
const costs=rows=>rows.map(([id,n])=>`${n} ${name(id)}`).join('; ');
const source='tools/structural_content.json; tools/structural_building_content.mjs';
export function structuralWorkbookRows(headers) {
  const result=catalog.buildings.map(b=>{
    const [w,d,h]=b.size;
    const side=b.kind==='sidedeck';
    // Side platforms: an n×n deck plus one anchor row, one cleat layer and,
    // for even n, one empty column in their block grid; report the deck itself.
    const n=side?d-1:0;
    const deck=side?n*n:w*d;
    const fields={
      'Building ID':b.id,'Building / Machine':b.name,'Infobox':'Structure',
      'Categories':`${b.kind==='block'||b.kind==='dam'?'Landscaping':'Paths'}; Deep Frontier`,
      'Faction':'Iron Teeth','Buildable?':'Yes','Availability':'Authored build menu',
      'Width':side?n:w,'Length':side?n:d,'Footprint':side?`${n}x${n} deck + 1 anchor tile`:`${w}x${d}`,'Footprint tiles':deck,'Height':side?1:h,
      'Workers':0,'Power demand (hp)':0,'Power output (hp)':0,'Power role':'Passive / transport',
      'Science unlock':b.science,'Bot unlock':'n.a.','Build materials':costs(b.cost),
      'Flags':`${deck} top support cells; `+(b.kind==='block'?'Full water obstacle':b.kind==='dam'?'0.65-layer spill crest':'No water obstacle'),
      'Recipe names':'None','Source':source,'Data status':catalog.status,'Stage':'3. Industrial city',
      'Role':b.description,'Stackable':'Yes','Stacking rule':'Native supported top; no artificial layer cap',
      'Conveyor-only solids':'No','Pipe ports':'None','Power mode':'None',
      'Unlock prerequisites':`${b.cost.some(([id])=>id==='Concrete')?'Concrete production':'Stone gathering and cement production'}; science and listed construction materials`,
      'Inputs':'None during use','Outputs':'Supported construction or water control','Waste / side effect':'None',
      'Placement':b.kind==='overhang'?'One supported anchor tile':b.kind==='scaffold'?'Four supported corner columns':
        side?'Hangs beside the top block of a reinforced dam column, level with its top; cleat on the dam top':'Ground or stackable support',
      'Player cue':b.description,'Status':catalog.status,
      'Notes':(b.kind==='scaffold'?`Concrete platform, ${w}×${d} deck on ${h-1}-layer legs. Cost k×(3 Concrete, 2 Metal Block, 1 Gear) and 500k science, k = n²+H = ${w*d+h-1}. `:'')+
        (side?`Concrete side platform, legless ${n}×${n} deck. Cost k×(3 Concrete, 2 Metal Block, 1 Gear) and 500k science, k = n² = ${n*n}. Anchor: ReinforcedDamBlock (AnchoredDeckAnchorSpec). Initial cost balance. Source geometry and exports checked; native placement, load and deletion untested.`:
         b.id==='ConcreteScaffold3x3'||b.kind!=='scaffold'?'Initial cost balance. Source geometry and exports checked; native support/water/traversal acceptance tracked in STATUS.':
         'Initial cost balance. Source geometry and exports checked; native placement, support and traversal untested.')
    };
    for(const h of headers)if(!Object.hasOwn(fields,h))throw new Error('Missing structural workbook field: '+h);
    return headers.map(h=>fields[h]);
  });
  return result;
}
export const structuralSource=['Reinforced construction',source,'Original native-material meshes and native support/water components',
  '2026-10-21','Eighteen authored structures: seven natively accepted, plus eight concrete platform size/height variants (3×3/4×4/5×5 decks, 1–3 layer legs) and three concrete side platforms hung from reinforced dam blocks, pending native acceptance. Static mesh/export checks are separate from native acceptance. No power or workers.',
  'DeepFrontier',catalog.status,'Dimensions; construction costs; top support; water retention and spill height'];
export const hydroSource=['Controlled dam turbines','docs/hydroelectric-construction.md; installed 1.1.2.8 water APIs',
  'Original model, native water services and automation; provisional balance','2026-10-20',
  'Dam-base turbine with m³/s limit, actual through-flow/head and hp generation. Native valve probe 92 passed; exact authored catalog is tools/hydro_content.json. See STATUS for turbine runtime evidence.',
  'DeepFrontier',hydro.status,'Exact authored dimensions, costs, science and maximum nameplate; actual output varies with flow/head'];
export const hydroBuildingRow=['ReinforcedHydroTurbine','Reinforced hydroelectric turbine','Generator',
  'Power; water control; Deep Frontier','Iron Teeth','Yes','Authored build menu',
  hydro.size[0],hydro.size[1],`${hydro.size[0]}x${hydro.size[1]}`,hydro.size[0]*hydro.size[1],hydro.size[2],
  0,0,hydro.maxDischarge*hydro.maxGeneratingHead*hydro.hpPerFlowAndHead,
  'Generator',hydro.science,'n.a.',costs(hydro.cost),
  `Two-cell submerged outlet; 0–${hydro.maxDischarge} m³/s total limit`,'None','docs/hydroelectric-construction.md',
  hydro.status,'4. Wonder transition',
  'Substantial renewable power from actual through-flow and positive reservoir head',
  'Yes; 21 support cells','Native support at deck layer 2 and cap layer 6; no arbitrary layer cap','No','Two-cell world-water passage; not inventory Water',
  'Produces','Concrete production; advanced metalwork; listed science and construction materials','Actual reservoir water flow and head',
  'hp plus downstream water','Water and contamination retained in simulation','Bottom of a sealed dam; clear downstream outlet',
  'Panel distinguishes requested m³/s, actual flow, head and hp',hydro.status,
  hydro.balanceStatus+' Nameplate is a maximum, not constant generation. No heat or maintenance.'];
