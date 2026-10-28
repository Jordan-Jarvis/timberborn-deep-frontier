import { readFile } from 'node:fs/promises';

const root = new URL('../', import.meta.url);
const manifest = JSON.parse(await readFile(new URL('src/DeepFrontier/manifest.json', root), 'utf8'));
const installed = JSON.parse(await readFile(new URL('tools/installed_dependency_manifests_1_1.json', root), 'utf8'));
const installedById = new Map(installed.packages.map(pkg => [pkg.id,pkg]));
if(installedById.size !== installed.packages.length) throw new Error('Duplicate installed dependency ID');
if(!Array.isArray(manifest.RequiredMods)) throw new Error('RequiredMods must be an explicit array');
const required=manifest.RequiredMods;
for(const entry of required) {
  if(typeof entry !== 'object' || typeof entry.Id !== 'string' || typeof entry.MinimumVersion !== 'string') {
    throw new Error('Each required dependency must declare its exact Id and MinimumVersion');
  }
}
if(new Set(required.map(e=>e.Id)).size!==required.length) throw new Error('Duplicate required dependency ID');
function compareVersions(left,right) {
  for(const version of [left,right]) {
    if(!/^\d+\.\d+(\.\d+){0,2}$/.test(version)) throw new Error(`Invalid package version: ${version}`);
  }
  const a=left.split('.').map(Number),b=right.split('.').map(Number);
  for(let i=0;i<Math.min(a.length,b.length);i++) {
    if(a[i]!==b[i]) return a[i]-b[i];
  }
  return a.length-b.length;
}
const missing=required.filter(e=>!installedById.has(e.Id)).map(e=>e.Id);
const outdated=required.filter(e=>installedById.has(e.Id) && compareVersions(installedById.get(e.Id).version,e.MinimumVersion)<0)
  .map(e=>({id:e.Id,installed:installedById.get(e.Id).version,required:e.MinimumVersion}));

console.log(JSON.stringify({
  mod: manifest.Id,
  targetGame: manifest.MinimumGameVersion,
  requiredCount: required.length,
  installedFoundationCount: installed.packages.length,
  missingRequiredMods: missing,
  outdatedRequiredMods: outdated,
  status: missing.length === 0 && outdated.length === 0 ? 'ok' : 'dependency-errors',
}, null, 2));

if (missing.length > 0 || outdated.length > 0) process.exitCode = 1;
