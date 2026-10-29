import {readFile,readdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {resolve,relative} from 'node:path';
// Native StatusSubject.ActiveStatuses (Timberborn 1.1.2.8, decompiled
// Timberborn.StatusSystem) returns ONLY the priority statuses while any
// priority status is active, so a priority status hides native NoPower,
// no-workers and lack-of-resources statuses (panel and floating icon).
// Deep Frontier keeps priority only for genuine hazards (user decision
// 2026-10-23); every other status must be a normal one. This check fails on
// any StatusToggle.CreatePriority* outside the listed hazard toggles.
const root=fileURLToPath(new URL('../',import.meta.url));
const scripts=resolve(root,'src/DeepFrontier/Scripts');
// File (relative to Scripts, forward slashes) -> the toggle fields allowed to be priority.
const HAZARDS={
  'Meltdown/ReactorCore.cs':['_overheatStatus','_scramStatus','_coolantDryStatus','_wasteFullStatus'],
  'Cryogenics/CryogenicTank.cs':['_ventingStatus','_wrongNetworkStatus'],
  'Meltdown/WasteLeak.cs':['_leakingStatus'],
};
async function files(directory){
  const result=[];
  for(const entry of await readdir(directory,{withFileTypes:true})){
    const path=resolve(directory,entry.name);
    if(entry.isDirectory())result.push(...await files(path));
    else if(entry.name.endsWith('.cs'))result.push(path);
  }
  return result;
}
const failures=[];
const seen=new Set();
for(const path of await files(scripts)){
  const file=relative(scripts,path).replace(/\\/g,'/');
  const lines=(await readFile(path,'utf8')).split(/\r?\n/);
  lines.forEach((raw,i)=>{
    const code=raw.replace(/\/\/.*$/,'');
    if(!/\bCreatePriority\w*\s*\(/.test(code))return;
    const field=/(\w+)\s*=\s*StatusToggle\.CreatePriority/.exec(code)?.[1];
    if(field&&(HAZARDS[file]??[]).includes(field)){seen.add(file+':'+field);return;}
    failures.push(`${file}:${i+1}: priority status ${field??'(unassigned)'} is not a listed hazard; use a normal status so native statuses stay visible`);
  });
}
for(const [file,fields] of Object.entries(HAZARDS))
  for(const field of fields)
    if(!seen.has(file+':'+field))failures.push(`${file}: listed hazard ${field} is no longer a priority status; update HAZARDS`);
if(failures.length)throw new Error('Priority-status check failed:\n'+failures.join('\n'));
console.log(JSON.stringify({status:'priority-statuses-checked',hazards:[...seen]}));
