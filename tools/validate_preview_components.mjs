import {readFile,readdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {resolve,relative} from 'node:path';
// Native Timberborn 1.1.2.8 PreviewPlacer.ShowPreviews runs every frame while a
// building preview is shown, not only when the mouse moves:
// - BlockObject.IsValid (all IBlockObjectValidator) and
//   BlockObjectValidationService.AreValid: two or three times per frame;
// - PreviewShower: every IPreviewValidator.IsValid, IPrePreviewShownListener,
//   then Preview.Show -> every IPreviewSelectionListener.OnPreviewSelect;
// - BlockObjectModelController.UpdateModel -> every IModelUpdater.UpdateModel.
// Deep Frontier code on those paths must not allocate collections or run LINQ,
// and the known per-frame paths must keep their change guards.
const root=fileURLToPath(new URL('../',import.meta.url));
const scripts=resolve(root,'src/DeepFrontier/Scripts');
const PER_FRAME={
  IBlockObjectValidator:['IsValid'],
  IPreviewValidator:['IsValid'],
  IPrePreviewShownListener:['OnPrePreviewShown'],
  IPreviewSelectionListener:['OnPreviewSelect','Update'],
  IModelUpdater:['UpdateModel'],
};
// Helpers those methods call on the per-frame path.
const HELPERS={MapEdgeSite:['TouchesMapEdge'],AdaptiveSupports:['Refresh']};
// Guards that make a per-frame call a no-op when nothing changed.
const GUARDS=[
  ['WaterSitePreviewMarkers','OnPreviewSelect',/^\s*if\s*\(\s*Enabled\s*\)\s*return\s*;/],
  ['AdaptiveSupports','Refresh',/if\s*\(\s*!changed\s*\)\s*return\s*;/],
  ['PlatformDeck','UpdateModel',/_applied\.SetEquals\(hidden\)\)\s*return\s*;/],
  ['BuildingWalkway','UpdateModel',/_appliedShown\.SetEquals\(_shown\)\)\s*return\s*;/],
];
const FORBIDDEN=[
  [/(?<!\bMathf?)\.(Select|SelectMany|Where|Any|All|ToArray|ToList|ToHashSet|Distinct|Concat|First|FirstOrDefault|Single|OrderBy|Sum|Max|Min)\s*\(/,'LINQ'],
  [/\.Count\s*\(/,'LINQ Count()'],
  [/new\s+(HashSet|List|Dictionary|Queue|Stack|SortedSet)\s*</,'collection allocation'],
  [/new\s+[A-Za-z_][\w.]*\s*\[/,'array allocation'],
  [/string\.(Join|Format)\s*\(/,'string building'],
];
async function files(directory){
  const result=[];
  for(const entry of await readdir(directory,{withFileTypes:true})){
    const path=resolve(directory,entry.name);
    if(entry.isDirectory())result.push(...await files(path));
    else if(entry.name.endsWith('.cs'))result.push(path);
  }
  return result;
}
// Class name -> {interfaces, text} for every class declaration.
function classes(source){
  const found=[];
  const pattern=/\bclass\s+(\w+)\s*(?::\s*([^{]+))?\{/g;
  let match;
  while((match=pattern.exec(source))){
    const open=match.index+match[0].length-1;
    found.push({name:match[1],bases:(match[2]||'').split(',').map(s=>s.trim().replace(/<.*$/,'')),text:block(source,open)});
  }
  return found;
}
function block(source,open){
  let depth=0;
  for(let i=open;i<source.length;i++){
    if(source[i]==='{')depth++;
    else if(source[i]==='}'&&--depth===0)return source.slice(open+1,i);
  }
  throw new Error('Unbalanced braces');
}
// Body of a method (block or expression body); null when absent.
function method(text,name){
  const pattern=new RegExp(`\\b(?:public|private|internal|protected)[^;{()=]*\\b${name}\\s*\\([^)]*\\)\\s*(\\{|=>)`,'g');
  const match=pattern.exec(text);
  if(!match)return null;
  if(match[1]==='{')return block(text,match.index+match[0].length-1);
  const end=text.indexOf(';',match.index+match[0].length);
  return text.slice(match.index+match[0].length,end);
}
const failures=[];
const checked=[];
const declared=new Map();
for(const path of await files(scripts)){
  const source=(await readFile(path,'utf8')).replace(/\/\/.*$/gm,'');
  for(const c of classes(source)){
    declared.set(c.name,{...c,path});
    const names=new Set(c.bases.flatMap(b=>PER_FRAME[b]||[]));
    for(const name of HELPERS[c.name]||[])names.add(name);
    for(const name of names){
      const body=method(c.text,name);
      if(body===null){
        if(name!=='Update')failures.push(`${relative(root,path)}: ${c.name}.${name} not found`);
        continue;
      }
      checked.push(`${c.name}.${name}`);
      for(const [regex,label] of FORBIDDEN){
        const hit=body.match(regex);
        if(hit)failures.push(`${relative(root,path)}: ${c.name}.${name} runs every preview frame and uses ${label}: ${hit[0]}`);
      }
    }
  }
}
for(const [owner,name,guard] of GUARDS){
  const c=declared.get(owner);
  const body=c&&method(c.text,name);
  if(!body)failures.push(`${owner}.${name}: guarded per-frame path not found`);
  else if(!guard.test(body))failures.push(`${owner}.${name}: lost its per-frame change guard ${guard}`);
}
if(failures.length){
  console.log(failures.map(f=>'FAIL '+f).join('\n'));
  throw new Error(`Preview component validation failed (${failures.length})`);
}
console.log(JSON.stringify({status:'preview-components-checked',methods:checked.sort(),guards:GUARDS.length}));
