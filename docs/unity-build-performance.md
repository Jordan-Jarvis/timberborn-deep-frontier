# Unity build performance: bundle reuse, shader stripping, process limits

On 2026-11-09 the flagged Deep Frontier test build (`tools/build_deep_frontier.ps1 -ModdableFluids`) missed Unity's
shader cache and compiled Deep Frontier's shader variants cold. Unity and its shader compilers took every core at
normal priority and the machine stopped responding until the user killed the build. This page records where a build's
CPU time goes and the four changes made in response. Every change is static tooling: none of it has run in Unity yet.

## Where the CPU time goes

Deep Frontier ships three shader graphs, and Moddable Fluids two. Each is a variant of a native Timberborn graph
(`tools/native_shader_variants.mjs`, `tools/moddable_fluids_shader_variants.mjs`):

| Shader | Native graph | Own keyword |
| --- | --- | --- |
| `DeepFrontier/IrradiatedTerrainURP` | `Shader Graphs/TerrainURP` | `_DEEP_FRONTIER_IRRADIATED_SOIL` |
| `DeepFrontier/RadioactiveWaterURP_Opaque`, `_Transparent` | `Shader Graphs/PhysicalWaterURP_Opaque`, `_Transparent` | `_DEEP_FRONTIER_RADIOACTIVE_WATER` |
| `ModdableFluids/FluidWaterURP_Opaque`, `_Transparent` | the same two water graphs | `_MODDABLE_FLUIDS_APPEARANCE` |

One official build compiles each variant up to three times:

- **The player build.** `ModBuilder` builds a throwaway Windows player for the DLLs (`buildCode`). Unity puts every
  `Resources` folder of the project into a player, and every staged mod keeps its bundle assets under
  `AssetBundles/Resources`. The player build therefore compiles the shaders of all staged mods for Direct3D 11: a Deep
  Frontier build also compiles Moddable Fluids' shaders, and the other way round.
- **The Windows bundle**, also Direct3D 11. It shares the shader cache with the player build.
- **The macOS bundle**, Metal.

Each compile is cheap when Unity's shader cache (`Library`) holds the variant, and very expensive when it does not.
The last cold compiles in the logs are builds 271 and 272 (`outputs/unity-official-build271.log`, `...272.log`):

| Shader | Variants per graphics API | Cold CPU time, Direct3D 11 | Cold CPU time, Metal |
| --- | --- | --- | --- |
| IrradiatedTerrainURP | 480 | 1,377 s | 1,459 s |
| RadioactiveWaterURP_Opaque | 448 | 2,644 s | 2,731 s |
| RadioactiveWaterURP_Transparent | 208 | 949 s | 988 s |

The ForwardLit fragment programs dominate: 256 opaque-water fragment variants cost 2,409 s on Direct3D 11. A cold
Deep Frontier build costs about 10,000 s of CPU time for its own shaders. The flagged build that froze the machine was
compiling RadioactiveWaterURP_Opaque and IrradiatedTerrainURP when it was killed. Why the cache missed is not
established: the Moddable Fluids build just before it hit the cache for the same Deep Frontier shaders.

## 1. Bundle reuse (`tools/UnityBundleCache.ps1`)

The three builds fingerprint their bundle inputs after staging:

- `tools/build_deep_frontier.ps1` (default, cache variant `DeepFrontier/default`);
- its `-ModdableFluids` variant (`DeepFrontier/moddable-fluids`, whose bundle inputs differ: see section 4);
- `tools/build_moddable_fluids.ps1` (`ModdableFluids/default`).

When the fingerprint matches the last verified build of that mod and variant, Unity builds the code only (the batch
entry points take `-modBundles reuse`). The script then installs that build's AssetBundles folder, both platforms'
bundles and manifests, byte for byte. Otherwise Unity builds both bundles (`-modBundles build`). The entry points
require one of the two values. The script says which inputs changed.

**Fingerprint inputs.** Each file below is recorded by its path relative to the Unity project and its SHA-256 hash:

- `Assets/Mods/<Mod>/AssetBundles/**` and `AssetBundles.meta`, with every `.meta` file. The GUIDs in them determine
  the object ids inside a bundle. Deep Frontier's materials authored by "Create Materials" live here too.
- `Assets/Mods/<Mod>/Editor/**`: Deep Frontier's `DeepFrontierMaterials.cs`, the "Create Materials" step.
- `Assets/Tools/**`, which holds:
  - the official Mod Builder sources, including `AssetBundleBuilder`;
  - the staged batch builds and `ModShaderVariantStripping.cs`;
  - the imported game assets, among them the native shader subgraphs our graphs reference;
  - the editor DLLs, among them the Timbermesh importer.
- `Assets/Plugins/Timberborn/**`, the game assemblies. Bundled timbermesh objects serialize `BinaryData` and
  `ModelMetadata` scripts from them.
- `Assets/Rendering/**`: the URP asset, its renderer data, global settings and volume profile.
- These project settings: `GraphicsSettings`, `QualitySettings`, `ProjectSettings`, `EditorSettings`,
  `ShaderGraphSettings`, `URPProjectSettings` and `ProjectVersion.txt`.
- `Packages/manifest.json` and `Packages/packages-lock.json`: the URP and Shader Graph versions.
- The Unity editor version (`Unity.exe` product version, with its revision).
- Unity's build support for both bundle targets: the Windows and macOS `PlaybackEngines` extension DLLs and
  `modules.asset`. Missing macOS build support fails the fingerprint.

Scripts and Data are not inputs: the official builder copies them into every package, and they do not change bundle
bytes. Moddable Fluids' staging used to delete and recopy its AssetBundles folder before every build, which gave the
shaders new GUIDs each time. It now synchronises file by file and keeps the `.meta` files, as Deep Frontier's staging
already did.

**Cache.** Each verified build is stored in `outputs/unity-bundle-cache/<Mod>/<variant>/`:

- `AssetBundles/` as the official builder wrote it;
- `fingerprint.json`, with the fingerprint, the Unity version, the time and the bundle hashes;
- `inputs.tsv`, one `path<TAB>SHA-256` line per input, which the scripts use to list what changed.

**When it is written.**

- The cache is written only after the build's own checks pass, and the inputs are re-read after Unity exits. The
  "Create Materials" step and URP may rewrite assets during a build.
- Deep Frontier's default build runs the bundle checks of the verify script before it stores anything.
  - `validate_goodmesh_exports.py` checks both platforms.
  - `check_bundle_shaders.py` checks the shader variants (section 2).
- In a reuse build, any input Unity changed while it ran fails the build and deletes the entry. The next build then
  rebuilds the bundles.
- A cache entry whose files differ from its record fails the build. Delete the entry to rebuild.

**Verification.**

- `tools/verify_deep_frontier_package.ps1` and `tools/verify_moddable_fluids_package.ps1` require the installed or
  kept AssetBundles folder to equal the cached one. They record its fingerprint, and the Moddable Fluids check compares
  it with `package-report.json`.
- The flagged build checks the same, and its `package-report.json` records the fingerprint and whether the bundles
  were reused.
- Until a build has stored an entry, both verify scripts fail with "No verified bundles are cached".

**What a code-only build still compiles.** The player build still compiles the Resources shaders of every staged mod
for Direct3D 11. With a warm cache that takes seconds. With a cold cache it costs the Direct3D 11 half of the stripped
figures in the last section.

## 2. Shader variant stripping (`tools/unity/ModShaderVariantStripping.cs`)

An `IPreprocessShaders` callback (callbackOrder 100, after URP's 0). It touches only shaders whose names start with
`DeepFrontier/` or `ModdableFluids/`. An unknown shader under those prefixes throws, and so does a rule that would
remove every variant of a drawn pass. `tools/stage_deep_frontier.ps1` and `tools/build_moddable_fluids.ps1` stage it
next to the batch builds. Each pass and stage is logged as
`[ModShaderVariantStripping] <shader> | <pass> (<LightMode>) | <stage> | <API>: <before> -> <after>`, and the build
scripts print a per-shader summary from the Unity log.

### What was already stripped

The brief's candidates were lightmaps, dynamic lightmaps, probe volumes, deferred/GBuffer, XR, debug display and LOD
crossfade. The bundles already have none of them:

- The project's GraphicsSettings strip lightmap modes with none kept (`m_LightmapStripping: 1`, every
  `m_LightmapKeep*: 0`). Fog is stripped to exponential only (`m_FogKeepExp: 1`).
- The renderer is Forward (`m_RenderingMode: 0`), so URP strips the GBuffer pass to 0, as the build log shows.
- URP prefilters XR, debug, probe-volume and bicubic-lightmap keywords (`m_PrefilterXRKeywords: 1`,
  `m_PrefilterDebugKeywords: 1`, `m_LightProbeSystem: 0`, and so on).
- Our graphs do not declare `LOD_FADE_CROSSFADE`.

Read with UnityPy, the variants left in the shipped `deepfrontier_win`/`_mac` and `moddablefluids_win`/`_mac` use only
these URP keywords: `FOG_EXP`, `_ADDITIONAL_LIGHTS`, `_LIGHT_COOKIES`, `_MAIN_LIGHT_SHADOWS`,
`_MAIN_LIGHT_SHADOWS_CASCADE` and `_SHADOWS_SOFT`. The game's own compiled `TerrainURP` and `PhysicalWaterURP_*` in
`resources.assets` (Unity 6000.5.11f1) have exactly the same URP keyword combinations, pass by pass. So none of those
renderer keywords is left to strip, and the URP combinations that remain are all ones the game's renderer uses. The
variant counts come from our graphs' material keywords and our own keyword.

### Stripped, with the evidence

| Rule | Shaders | Evidence |
| --- | --- | --- |
| Every variant of the pass tagged `LightMode=Universal2D` (Shader Graph's "Universal 2D") | all five | The game data has one `UniversalRenderPipelineAsset` and one `UniversalRendererData` (`globalgamemanagers.assets`), and no `Renderer2DData` among the MonoBehaviours of `globalgamemanagers.assets`, `resources.assets` and the `sharedassets` files. Only URP's 2D renderer draws this pass. URP means to strip it in that case (`ShaderScriptableStripper.StripUnusedPass_2D`), but it compares the pass *name* with `Universal2D`, and Shader Graph names the pass `Universal 2D` (`UniversalLitSubTarget.cs`: displayName "Universal 2D", lightMode "Universal2D"). So the pass survives in the game's own build and in ours. |
| Variants without `_CALCULATE_OUTFLOWS` (applied only where a pass declares the keyword) | both water shaders of each mod | Both native water materials, `PhysicalWater_Opaque` and `PhysicalWater_Transparent` (`resources.assets`), enable it. No game assembly contains the string, so the game never toggles it. Deep Frontier's `ShaderSwap` keeps the native material's keywords, and Moddable Fluids' scene copies take them from the native materials. Our graphs compile it as multi_compile only because a bundle holds no material that would keep a shader_feature variant. |
| Variants with `_USE_TRIPLANAR_SPLATMAP` but without `_SAMPLE_SPLATMAP` | IrradiatedTerrainURP | The game's own compiled TerrainURP has six material-keyword combinations, none of them triplanar without the splatmap. The five native terrain materials it is swapped onto don't use that combination either: Grass (`_USELAYERTOOL`), Cliff (all three), CliffEdge (splatmap, layer tool), SlopeCliff (splatmap, triplanar) and SlopeCliffEdge (splatmap). No game assembly names these keywords. |

Not stripped:

- **The URP keywords above.** The game's own shaders keep both states of each.
- **`_HIGH_QUALITY_WATER_ENABLED` and `_USE_LEVEL_VISIBILITY`.** `Timberborn.GraphicsQualitySystem` and
  `Timberborn.LevelVisibilitySystem` toggle them.
- **`_USELAYERTOOL`.** Native materials use both states.
- **The ShadowCaster, MotionVectors, DepthOnly and DepthNormals passes.**
- **Our own keywords.** They are the feature.

Variants per graphics API, before and after (the same on Direct3D 11 and Metal):

| Shader | Before | After | ForwardLit fragment |
| --- | --- | --- | --- |
| DeepFrontier/IrradiatedTerrainURP | 480 | 336 | 256 -> 192 |
| DeepFrontier/RadioactiveWaterURP_Opaque | 448 | 208 | 256 -> 128 |
| DeepFrontier/RadioactiveWaterURP_Transparent | 208 | 96 | 128 -> 64 |
| ModdableFluids/FluidWaterURP_Opaque | 448 | 208 | 256 -> 128 |
| ModdableFluids/FluidWaterURP_Transparent | 208 | 96 | 128 -> 64 |

### The check: `tools/asset-pipeline/check_bundle_shaders.py`

Run by every build before it caches bundles, by the flagged build on every package, and by both verify scripts.

For each of our shaders in the Windows and the macOS bundle, it requires the exact variant set. That set is, pass by
pass and stage by stage, the keyword sets of the native counterpart in the installed game that the rules keep, each
with and without our keyword. Anything missing fails ("lacks"), which catches over-stripping before it shows pink. Any
variant the rules remove fails too ("holds stripped").

It also re-checks the evidence in the installed game:

- the render pipeline objects;
- every material on the native water and terrain shaders;
- the keyword strings in every game assembly.

So a game update that breaks a rule fails the build instead of shipping a wrong strip. It reads the game's files
read-only and commits nothing from them.

Run on the bundles shipped before this change, it reported exactly the variants the rules remove: 102 lines per
platform for Deep Frontier and 60 for Moddable Fluids. It found no missing variant on Windows or macOS.

### Further reductions, not done

These need a decision:

- **Our own keyword as a dynamic branch** instead of multi_compile. This halves every one of our shaders again, but
  changes how the variants run.
- **Stripping our shaders entirely in the throwaway player build.** This would make a code-only build free of shader
  compiles even with a cold cache. It needs a verified way to tell the player build from the bundle builds:
  `BuildPipeline.isBuildingPlayer` is true for both.

## 3. Unity at below-normal priority on fewer cores (`tools/UnityProcess.ps1`)

`Start-UnityProcess` creates the editor suspended, at `BELOW_NORMAL_PRIORITY_CLASS`, sets its affinity mask, and only
then resumes it. The mask is this session's logical processors without the two lowest: one whole physical core with
SMT, `0xFFC` of `0xFFF` on this 12-thread machine. Children inherit the affinity mask, and a below-normal priority
class unless they ask for another. So the shader compilers, Bee and the compiler server run the same way from their
first instruction.

Every Unity launch in the repository goes through it:

- the three build scripts;
- `tools/open_deep_frontier_builder.ps1`, the interactive editor (not hidden);
- `tools/setup_dev.py`'s first project import, through `tools/run_unity.ps1`.

`tools/test_unity_build_tools.ps1` (validate_all check `unity-build-tools`) proves this with a harmless process tree
in PowerShell 7 and in Windows PowerShell 5.1. `cmd.exe` starts `ping.exe` at once, both run at BelowNormal on
`0xFFC`, and the exit code comes back.

Not yet verified: whether Unity starts `UnityShaderCompiler.exe` with an explicit priority class. The affinity holds
either way. Check it in Task Manager during the next build.

## 4. The flagged build leaves out the radioactive-water shaders

Moddable Fluids draws the water in the flagged build. Nothing in that build loads Deep Frontier's water variants:

- **`RadiationRenderer`** is the only loader of `RadiationShading.WaterOpaqueVariant`/`WaterTransparentVariant`.
  `RadiationConfigurator` binds it only in the `#else` of `DEEP_FRONTIER_MODDABLE_FLUIDS`.
- **`RadioactiveWaterSurface`** is constructed only by `RadiationRenderer`.
- **`WaterShadingProbe`** refuses to run under the flag.
- **`SceneCycleAcceptance`** expects the native water shaders under the flag.
- **`ModdableFluidsSoilRenderer`** loads only `TerrainVariant`.
- **No bundled material** references the two graphs. Only the graphs themselves exist to use them.

`tools/build_deep_frontier_moddable_fluids.ps1` therefore moves the two `.shadergraph` files and their `.meta` files
out of the staging into its backup folder for the build. It restores them byte for byte in its finally block, before
the default staging, and a failed restore keeps the backup and stops later flagged builds. The irradiated-soil
variant stays. The package check runs `check_bundle_shaders.py --expect DeepFrontier/IrradiatedTerrainURP`, which
fails if either water shader is in either bundle.

## What the next builds will do, and their cost

The cold figures below are CPU time from the builds 271 and 272 per-pass costs, scaled to the stripped variant counts.
Wall-clock time assumes the shader compilers keep 10 logical processors busy, as in those builds (11.6x on 12).

| Build | First run after this change | Cold cost if the shader cache misses |
| --- | --- | --- |
| Deep Frontier default | No cache entry, so it builds both bundles. The kept variants are a subset of the old ones with the same cache keys, so a warm cache compiles nothing new. Then it stores `DeepFrontier/default`. | About 2,780 s on Direct3D 11 plus 2,900 s on Metal (was about 10,150 s). That is about 10 minutes on 10 logical processors, plus about 1,760 s if Moddable Fluids' Direct3D 11 variants are cold in the player build. |
| Flagged Deep Frontier | No cache entry, so it builds the bundles with IrradiatedTerrainURP alone, then stores `DeepFrontier/moddable-fluids`. | About 2,100 s (was about 10,150 s), plus the player build's Direct3D 11 compile of the staged Moddable Fluids shaders if those are cold. |
| Moddable Fluids | No cache entry: builds, then stores `ModdableFluids/default`. The staging now keeps the shaders' `.meta` files, so later builds with unchanged inputs reuse it. | About 3,570 s (was about 7,300 s), plus about 2,780 s if Deep Frontier's Direct3D 11 variants are cold in the player build. |
| Any later build with unchanged bundle inputs | Code only, with the cached bundles installed. | The player build's Direct3D 11 compile only, normally cache hits. |

## In-game checks for the run list

The stripping removes only variants the game never draws. Unity falls back to the nearest variant, so a wrong strip
would mostly look subtly wrong, and in the worst case pink. Check both factions, Folktails and Iron Teeth, in daylight
and at night, with shadows on, and in level-visibility (layer) view:

- **Shipped build: radioactive water.** Deep Frontier's water variants on native water, opaque and transparent, on a
  calm surface, a waterfall and an outflow. Mixed with badwater, and after a save and reload.
- **Shipped build: irradiated soil.** Every terrain material is drawn by the variant: grass, cliff, cliff edge, slope
  cliff and slope cliff edge. Check each on irradiated and on clean ground.
- **Flagged build: Moddable Fluids water.** Radioactive water tinted by Moddable Fluids, plain water and badwater on
  the scene copies. Also the More Fluids coffee, salt and healing waters when it is installed. Irradiated soil comes
  from the Deep Frontier variant.

Look for pink, black or missing surfaces, and for missing shadows, fog or flow on these surfaces. A failure there
means a rule above is wrong. macOS is checked only statically (the Metal bundle's variant sets).
