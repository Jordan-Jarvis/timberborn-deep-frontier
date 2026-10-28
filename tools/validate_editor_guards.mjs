import {readFile,readdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {resolve,relative} from 'node:path';
// The official Mod Builder first compiles the Scripts tree as an editor
// assembly (UNITY_EDITOR defined) without the dependency-mod DLLs, which are
// referenced only by the mod build (tools/build_deep_frontier.ps1). Code using a
// dependency mod must therefore sit inside `#if !UNITY_EDITOR`. The dotnet
// compile check references every DLL and cannot catch this (build 122 failed
// on an unguarded CryogenicTank.cs).
const root=fileURLToPath(new URL('../',import.meta.url));
const scripts=resolve(root,'src/DeepFrontier/Scripts');
// The optional assemblies (Scripts/RadioactiveTide/ModdableWeathers packaged as
// *.dll.ModdableWeathers.optional, Scripts/SluiceIsBack as *.dll.SluiceIsBack.optional)
// are scanned with the tree.
const DEPENDENCIES=['TimberPipes','ConveyorBelt','PowerLines','ModSettings','TimberUi','ModdableRecipes','ModdableTimberborn','ModdableWeathers','SluiceIsBack','HarmonyLib'];
const usage=new RegExp(`\\b(${DEPENDENCIES.join('|')})\\.[A-Za-z_]|\\busing\\s+(${DEPENDENCIES.join('|')})\\b|\\bHarmony\\b`);
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
let checked=0;
for(const path of await files(scripts)){
  checked++;
  // Stack of preprocessor branches: true when the branch excludes the editor.
  const stack=[];
  const lines=(await readFile(path,'utf8')).split(/\r?\n/);
  lines.forEach((raw,i)=>{
    const line=raw.trim();
    const directive=/^#\s*(if|elif|else|endif)\b(.*)$/.exec(line);
    if(directive){
      const [,kind,condition]=directive;
      if(kind==='if')stack.push(/^\s*!\s*UNITY_EDITOR\s*$/.test(condition));
      else if(kind==='elif')stack[stack.length-1]=/^\s*!\s*UNITY_EDITOR\s*$/.test(condition);
      else if(kind==='else')stack[stack.length-1]=false;
      else if(kind==='endif'){
        if(!stack.length)throw new Error(`${relative(root,path)}:${i+1}: #endif without #if`);
        stack.pop();
      }
      return;
    }
    const code=line.replace(/\/\/.*$/,'');
    if(usage.test(code)&&!stack.includes(true))
      failures.push(`${relative(root,path)}:${i+1}: dependency-mod code outside #if !UNITY_EDITOR: ${code.slice(0,100)}`);
  });
  if(stack.length)throw new Error(`${relative(root,path)}: unterminated #if`);
}
if(failures.length)throw new Error('Editor-guard check failed:\n'+failures.join('\n'));
console.log(JSON.stringify({status:'editor-guards-checked',files:checked,dependencies:DEPENDENCIES}));
