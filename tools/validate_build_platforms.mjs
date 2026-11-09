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
// Both platform bundles are built together, or (-modBundles reuse) both are installed from the last verified build's
// cache, which holds the whole AssetBundles folder (tools/UnityBundleCache.ps1, docs/unity-build-performance.md).
const build = await read('tools/unity/DeepFrontierBatchBuild.cs');
for (const platform of ['Windows', 'Mac'])
  if (!build.includes(`build${platform}AssetBundle: buildBundles`))
    throw new Error(`${platform} asset bundle must be built whenever bundles are built (buildBundles)`);
if (!build.includes('foreach (var platform in new[] { "win", "mac" })'))
  throw new Error('the Deep Frontier build must check both platform bundles after the official builder');
const fluids = await read('tools/unity/ModdableFluidsBatchBuild.cs');
if (!fluids.includes('buildWindowsAssetBundle: bundles,') || !fluids.includes('buildMacAssetBundle: bundles,'))
  throw new Error('Moddable Fluids must build its Windows and macOS bundles together');
const cache = await read('tools/UnityBundleCache.ps1');
for (const support of ['windowsstandalonesupport/', 'MacStandaloneSupport/'])
  if (!cache.includes(`'${support}`)) throw new Error(`the bundle fingerprint must cover Unity's ${support} build support`);
console.log(`Build platforms valid: Windows and macOS; ${files.length} managed references; Editor excluded.`);
