// Regression for the macOS bundle build: all managed dependency references
// must be available during both player-target compilations, but not in Editor.
import {readFile, readdir} from 'node:fs/promises';
const root = new URL('../', import.meta.url);
const read = path => readFile(new URL(path, root), 'utf8');
const files = (await readdir(new URL('tools/unity/', root))).filter(name => name.endsWith('.dll.meta'));
if (!files.length) throw new Error('No managed dependency import settings found');
for (const name of files) {
  const text = await read(`tools/unity/${name}`);
  for (const platform of ['Win64', 'OSXUniversal']) {
    if (!text.includes(`Exclude ${platform}: 0`) ||
        !new RegExp(`Standalone: ${platform}\\r?\\n    second:\\r?\\n      enabled: 1`).test(text))
      throw new Error(`${name}: ${platform} dependency compilation is disabled`);
  }
  if (!/Editor: Editor\r?\n    second:\r?\n      enabled: 0/.test(text))
    throw new Error(`${name}: dependency must remain excluded from Editor`);
}
const build = await read('tools/unity/DeepFrontierBatchBuild.cs');
for (const platform of ['Windows', 'Mac'])
  if (!build.includes(`build${platform}AssetBundle: true`))
    throw new Error(`${platform} asset bundle must be enabled`);
console.log(`Build platforms valid: Windows and macOS; ${files.length} managed references; Editor excluded.`);
