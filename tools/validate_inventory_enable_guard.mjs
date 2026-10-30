import {readFile,readdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {resolve,relative} from 'node:path';
// Moddable Recipes 11.0.0 workarounds (Scripts/InventoryEnableGuard.cs).
// MR's SetRecipe prefix (ManufactoryPatches.InitInventoryForRecipe) calls Inventory.Disable()/Enable()
// and always leaves the inventory enabled: before the native finished-state Enable of a single-recipe
// manufactory (registered with the district twice), and on construction sites (registered while the
// site exists, never unregistered when the site is deleted unfinished). A worker emptying a good such a
// deleted building accepted then crashed the game (all-buildings run b161). This check keeps both fixes
// exactly as approved (2026-10-24):
//   InventoryEnableGuard        one prefix on Inventory.Enable that skips only an already enabled
//                               inventory; native signatures checked at mod start; Disable not patched;
//   ModdableRecipesEnabledState a Priority.First prefix on MR's InitInventoryForRecipe recording
//                               inventory.Enabled and a Priority.Last postfix that disables again only
//                               an inventory MR enabled after finding it disabled; MR's signature and
//                               Deep Frontier's other hooks on that method checked at mod start;
//   both applied from DeepFrontierModStarter, all Harmony code inside #if !UNITY_EDITOR.
const root=fileURLToPath(new URL('../',import.meta.url));
const scripts=resolve(root,'src/DeepFrontier/Scripts');
const failures=[];
const strip=text=>text.split(/\r?\n/).map(l=>l.replace(/\/\/.*$/,'')).join('\n');
// Text between #if !UNITY_EDITOR and its #endif (no nesting is used in these files).
const guarded=text=>[...text.matchAll(/#if !UNITY_EDITOR\n([\s\S]*?)#endif/g)].map(m=>m[1]).join('\n');
const compact=text=>text.replace(/\s+/g,'');
const has=(text,needle)=>compact(text).includes(compact(needle));

const whole=strip(await readFile(resolve(scripts,'InventoryEnableGuard.cs'),'utf8'));
const split=whole.indexOf('internal static class ModdableRecipesEnabledState');
if(split<0)failures.push('InventoryEnableGuard.cs: class ModdableRecipesEnabledState missing');
const guardPart=split<0?whole:whole.slice(0,whole.lastIndexOf('#if !UNITY_EDITOR',split));
const restorePart=split<0?'':whole.slice(whole.lastIndexOf('#if !UNITY_EDITOR',split));

// --- Inventory.Enable guard
const guardInside=guarded(guardPart);
if(!has(guardInside,'[HarmonyPatch(typeof(Inventory),nameof(Inventory.Enable))]'))
  failures.push('InventoryEnableGuard: [HarmonyPatch(typeof(Inventory),nameof(Inventory.Enable))] missing or outside #if !UNITY_EDITOR');
const guardPrefix=/private static bool Prefix\(Inventory __instance\)\s*\{([\s\S]*?)\n\s*\}/.exec(guardInside);
if(!guardPrefix||compact(guardPrefix[1])!=='if(!__instance.Enabled)returntrue;Skipped++;returnfalse;')
  failures.push(`InventoryEnableGuard: Prefix must run the native Enable unless the inventory is already enabled (found: ${guardPrefix?guardPrefix[1].trim():'none'})`);
for(const needle of ['AccessTools.Method(typeof(Inventory),nameof(Inventory.Enable),Type.EmptyTypes)',
                     'AccessTools.PropertyGetter(typeof(Inventory),"Enabled")',
                     'throw new InvalidOperationException("Timberborn 1.1.2.8 instance void Inventory.Enable() changed")',
                     'new Harmony(HarmonyId).CreateClassProcessor(typeof(InventoryEnableGuard)).Patch()'])
  if(!has(guardInside,needle))failures.push(`InventoryEnableGuard: missing inside #if !UNITY_EDITOR: ${needle}`);
if(/Postfix\(|Transpiler\(|Finalizer\(/.test(guardPart))failures.push('InventoryEnableGuard: only the Enable prefix is allowed');

// --- MR enabled-state restore
const restoreInside=guarded(restorePart);
if(!has(restoreInside,'[HarmonyPatch(typeof(ModdableRecipes.Patches.ManufactoryPatches),nameof(ModdableRecipes.Patches.ManufactoryPatches.InitInventoryForRecipe))]'))
  failures.push('ModdableRecipesEnabledState: HarmonyPatch on ManufactoryPatches.InitInventoryForRecipe missing or outside #if !UNITY_EDITOR');
const restorePrefix=/\[HarmonyPriority\(Priority\.First\)\]\s*private static void Prefix\(Manufactory __0,out bool\? __state\)\s*\{([\s\S]*?)\n\s*\}/.exec(restoreInside);
if(!restorePrefix||compact(restorePrefix[1])!=='varinventory=__0?__0.Inventory:null;__state=inventory?inventory.Enabled:(bool?)null;')
  failures.push('ModdableRecipesEnabledState: a Priority.First prefix must only record inventory.Enabled');
const restorePostfix=/\[HarmonyPriority\(Priority\.Last\)\]\s*private static void Postfix\(Manufactory __0,bool\? __state\)\s*\{([\s\S]*?)\n\s*\}/.exec(restoreInside);
if(!restorePostfix||compact(restorePostfix[1])!=='if(__state!=false)return;varinventory=__0.Inventory;if(!inventory||!inventory.Enabled)return;inventory.Disable();Restored++;')
  failures.push('ModdableRecipesEnabledState: a Priority.Last postfix must only disable an inventory MR enabled after finding it disabled');
for(const needle of ['AccessTools.Method(typeof(ModdableRecipes.Patches.ManufactoryPatches),nameof(ModdableRecipes.Patches.ManufactoryPatches.InitInventoryForRecipe),new[]{typeof(Manufactory),typeof(RecipeSpec)})',
                     'AccessTools.Method(typeof(RestaurantKitchenRecipeCompatibility),"Prefix")',
                     'AccessTools.Method(typeof(BotMaintenanceRecipeCompatibility),"Postfix")',
                     'new Harmony(HarmonyId).CreateClassProcessor(typeof(ModdableRecipesEnabledState)).Patch()'])
  if(!has(restoreInside,needle))failures.push(`ModdableRecipesEnabledState: missing inside #if !UNITY_EDITOR: ${needle}`);

// --- The other Deep Frontier hooks on the MR method keep the shapes the restore is ordered against.
const restaurant=strip(await readFile(resolve(scripts,'RestaurantKitchenInventory.cs'),'utf8'));
const restaurantClass=restaurant.slice(restaurant.indexOf('class RestaurantKitchenRecipeCompatibility'),restaurant.indexOf('class RestaurantKitchenStock'));
if(!has(restaurantClass,'class RestaurantKitchenRecipeCompatibility{private static bool Prefix(Manufactory __0)')||restaurantClass.includes('HarmonyPriority'))
  failures.push('RestaurantKitchenRecipeCompatibility: expected a default-priority Prefix(Manufactory __0) : bool');
const bots=strip(await readFile(resolve(scripts,'Workforce/BotMaintenanceInventory.cs'),'utf8'));
if(!has(bots,'class BotMaintenanceRecipeCompatibility{private static void Postfix(Manufactory __0,RecipeSpec __1)'))
  failures.push('BotMaintenanceRecipeCompatibility: expected a default-priority Postfix(Manufactory __0,RecipeSpec __1)');
if(!/bool enabled=inventory\.Enabled;\s*if\(enabled\)inventory\.Disable\(\);[\s\S]*?if\(enabled\)inventory\.Enable\(\);/.test(bots))
  failures.push('BotMaintenanceInventory.RestoreExtraGoods must keep the enabled state it finds (the restore postfix runs after it)');

// --- Applied from the mod starter
const starter=guarded(strip(await readFile(resolve(scripts,'DeepFrontierModStarter.cs'),'utf8')));
for(const call of ['InventoryEnableGuard.Apply();','ModdableRecipesEnabledState.Apply();'])
  if(!starter.includes(call))failures.push(`DeepFrontierModStarter.cs: ${call} is not called inside #if !UNITY_EDITOR`);

// --- Disable stays native; one patch each
async function files(directory){
  const result=[];
  for(const entry of await readdir(directory,{withFileTypes:true})){
    const path=resolve(directory,entry.name);
    if(entry.isDirectory())result.push(...await files(path));
    else if(entry.name.endsWith('.cs'))result.push(path);
  }
  return result;
}
for(const path of await files(scripts)){
  const text=compact(strip(await readFile(path,'utf8')));
  const file=relative(scripts,path).replace(/\\/g,'/');
  if(text.includes('HarmonyPatch(typeof(Inventory),nameof(Inventory.Disable))')||text.includes('HarmonyPatch(typeof(Inventory),"Disable")'))
    failures.push(`${file}: patches Inventory.Disable; the approved workaround leaves Disable native`);
  if(file!=='InventoryEnableGuard.cs'&&(text.includes('HarmonyPatch(typeof(Inventory),nameof(Inventory.Enable))')||text.includes('HarmonyPatch(typeof(Inventory),"Enable")')))
    failures.push(`${file}: a second patch on Inventory.Enable`);
}
if(failures.length){
  console.error(failures.join('\n'));
  process.exit(1);
}
console.log('Inventory.Enable guard: idempotent prefix only, Disable native. Moddable Recipes enabled-state restore: first prefix records, last postfix disables only what MR enabled. Signatures checked at mod start; both applied from the mod starter.');
