import {readFile,readdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {resolve,basename} from 'node:path';
// Scripts/FootprintChangeLoadOrder.cs adds its listed buildings before every
// other object in their native load layer, so a path or platform that now
// overlaps a smaller footprint is removed on load instead of the building.
// That order is only valid for a building that needs nothing else in its own
// layer: every foundation block (solid MatterBelow) at or below BaseZ, no
// stackable block below BaseZ (those are StackableBaseLoadOrder's deck
// carriers, ranked first), and no understructure to stand on (the Deep Mine
// and the quarries load after their deposit; MineFootprintSaveMigration.cs
// moves them). Fails on a listed template without a blueprint or breaking
// one of these.
const root=fileURLToPath(new URL('../',import.meta.url));
const source=await readFile(resolve(root,'src/DeepFrontier/Scripts/FootprintChangeLoadOrder.cs'),'utf8');
const list=/Templates=new\(StringComparer\.Ordinal\)\s*\{([^}]*)\}/.exec(source);
if(!list)throw new Error('FootprintChangeLoadOrder.cs: Templates list not found');
const templates=[...list[1].matchAll(/"([^"]+)"/g)].map(m=>m[1]);
if(!templates.length)throw new Error('FootprintChangeLoadOrder.cs: empty Templates list');
if(new Set(templates).size!==templates.length)throw new Error('FootprintChangeLoadOrder.cs: duplicate template');
async function blueprints(directory){
  const result=new Map();
  for(const entry of await readdir(directory,{withFileTypes:true})){
    const path=resolve(directory,entry.name);
    if(entry.isDirectory())for(const [k,v] of await blueprints(path))result.set(k,v);
    else if(entry.name.endsWith('.blueprint.json'))result.set(basename(entry.name,'.blueprint.json'),path);
  }
  return result;
}
const known=await blueprints(resolve(root,'src/DeepFrontier/Data/Buildings'));
const failures=[];
for(const template of templates){
  const path=known.get(template);
  if(!path){failures.push(`${template}: no blueprint under src/DeepFrontier/Data/Buildings`);continue;}
  const blueprint=JSON.parse(await readFile(path,'utf8'));
  const spec=blueprint.BlockObjectSpec;
  if(!blueprint.BuildingSpec||!spec){failures.push(`${template}: not a building with a BlockObjectSpec`);continue;}
  const understructure=Object.keys(blueprint).filter(k=>/Understructure/.test(k));
  if(understructure.length)failures.push(`${template}: stands on an understructure (${understructure.join(', ')}); it must load after its deposit`);
  const {X,Y}=spec.Size;
  const baseZ=spec.BaseZ??0;
  spec.Blocks.forEach((block,i)=>{
    const z=Math.floor(i/(X*Y));
    const matter=block.MatterBelow??'Any';
    if(matter!=='Any'&&z>baseZ)failures.push(`${template}: foundation block ${i} (MatterBelow ${matter}) at layer ${z} above BaseZ ${baseZ}`);
    if(z<baseZ&&(block.Stackable??'None')!=='None')failures.push(`${template}: stackable block ${i} below BaseZ (a deck carrier: StackableBaseLoadOrder ranks it)`);
  });
}
if(failures.length){
  for(const f of failures)console.error(f);
  process.exit(1);
}
console.log(`Footprint-change load order: ${templates.length} listed buildings need nothing else in their own load layer.`);
