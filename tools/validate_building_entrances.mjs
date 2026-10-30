import {readFile,readdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {resolve,relative} from 'node:path';
// Every Deep Frontier building's native Entrance must be reachable by a player's ordinary Path, as
// in vanilla (138 of 139 shipped Timberborn 1.1.2.8 buildings; tools/native_entrance.mjs):
//   - the Entrance cell is at the building's base level (z = BaseZ: the ground or bank the
//     building stands on) and open: outside the footprint, or an unoccupied cell of a porch/notch
//     that connects through unoccupied cells at that level to the outside of the footprint;
//   - its native doorstep, the door cell one step north (PositionedEntrance.DoorstepCoordinates
//     with the unrotated direction Down), is an occupied building cell.
// An Entrance on a building's own block puts the access where no Path can be laid: FisheryWorks'
// player path showed no connection to its door and FishHatchery reported "not connected" (user
// reports on build 174). A building may only deviate if it is listed in EXCEPTIONS with the native
// access that replaces the path (none are needed today).
const EXCEPTIONS={};
const root=fileURLToPath(new URL('../',import.meta.url));
const data=resolve(root,process.argv[2]??'src/DeepFrontier/Data','Buildings');
async function files(directory){
  const result=[];
  for(const entry of await readdir(directory,{withFileTypes:true})){
    const path=resolve(directory,entry.name);
    if(entry.isDirectory())result.push(...await files(path));
    else if(entry.name.endsWith('.blueprint.json'))result.push(path);
  }
  return result;
}
const failures=[],report=[];
for(const path of await files(data)){
  const b=JSON.parse((await readFile(path,'utf8')).replace(/^﻿/,''));
  const spec=b.BlockObjectSpec;
  if(!spec?.Entrance?.HasEntrance)continue;
  const name=(b.TemplateSpec?.TemplateName??relative(data,path)).replace(/\.IronTeeth$/,'');
  const {X:w,Y:d,Z:h}=spec.Size,E=spec.Entrance.Coordinates,base=spec.BaseZ;
  const inside=(x,y,z)=>x>=0&&y>=0&&z>=0&&x<w&&y<d&&z<h;
  const block=(x,y,z)=>spec.Blocks[(z*d+y)*w+x];
  // A vanilla Path (Occupations 'Path') shares a cell with blocks that hold only Top and
  // Corners, as under a vanilla Platform or Overhang; a one-layer deck's slab cell over a
  // doorstep is such a block (the Restaurant's layer-1 dining balcony, 2026-10-30).
  const pathFits=o=>['None','Top','Corners','Top, Corners'].includes(o);
  const occupied=(x,y,z)=>inside(x,y,z)&&!pathFits(block(x,y,z).Occupations);
  const problems=[];
  if(E.Z!==base)problems.push(`Entrance level z=${E.Z} is not the base level BaseZ=${base}`);
  let kind='outside the footprint';
  if(occupied(E.X,E.Y,E.Z))problems.push(`Entrance (${E.X},${E.Y},${E.Z}) is the building's own ${block(E.X,E.Y,E.Z).Occupations} cell: no player Path can be laid there`);
  else if(inside(E.X,E.Y,E.Z)) {
    // A porch: the unoccupied cells at the entrance level must lead out of the footprint.
    const seen=new Set([E.X+','+E.Y]),queue=[[E.X,E.Y]];let open=false;
    while(queue.length&&!open){
      const [x,y]=queue.shift();
      for(const [dx,dy] of [[1,0],[-1,0],[0,1],[0,-1]]){
        const nx=x+dx,ny=y+dy;
        if(!inside(nx,ny,E.Z)){open=true;break;}
        if(seen.has(nx+','+ny)||occupied(nx,ny,E.Z))continue;
        seen.add(nx+','+ny);queue.push([nx,ny]);
      }
    }
    kind='an open porch cell inside the bounds';
    if(!open)problems.push(`Entrance porch (${E.X},${E.Y},${E.Z}) is enclosed by the building at its level`);
  }
  if(!(inside(E.X,E.Y+1,E.Z)&&block(E.X,E.Y+1,E.Z).Occupations!=='None'))problems.push(`the native doorstep (${E.X},${E.Y+1},${E.Z}) north of the Entrance is not an occupied building cell`);
  const exception=EXCEPTIONS[name];
  if(problems.length&&!exception)failures.push(`${name}: ${problems.join('; ')}`);
  report.push(`${name}: Entrance (${E.X},${E.Y},${E.Z}) ${problems.length?'EXCEPTION '+(exception??''):kind}`);
}
for(const name of Object.keys(EXCEPTIONS))if(!report.some(r=>r.startsWith(name+':')))failures.push(`EXCEPTIONS lists ${name}, which has no entrance`);
if(failures.length){
  console.error(failures.join('\n'));
  process.exit(1);
}
console.log(`${report.length} building entrances take a player's ordinary Path (${report.filter(r=>r.includes('porch')).length} in open porches)`);
