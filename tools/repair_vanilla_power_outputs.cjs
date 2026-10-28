const fs = require('fs');
const path = 'C:/Users/Jordan/Documents/TimberbornModding/tools/vanilla_1_1_data.json';
const data = JSON.parse(fs.readFileSync(path, 'utf8'));
let repaired = 0;
for (const building of data.buildings ?? []) {
  const powerRecipe = (building.recipes ?? []).find((r) => r.name === 'Power output');
  if (!powerRecipe) continue;
  const match = String(powerRecipe.outputs ?? '').match(/(\d+(?:\.\d+)?)\s*hp/i) || String(powerRecipe.rawProduces ?? '').match(/(\d+(?:\.\d+)?)\s*hp/i);
  if (!match) continue;
  const hp = Number(match[1]);
  if (building.powerOutputHp !== hp) {
    building.powerOutputHp = hp;
    repaired++;
  }
}
for (const recipe of data.recipes ?? []) {
  if (recipe.recipe !== 'Power output') continue;
  const match = String(recipe.outputs ?? '').match(/(\d+(?:\.\d+)?)\s*hp/i) || String(recipe.rawProduces ?? '').match(/(\d+(?:\.\d+)?)\s*hp/i);
  if (!match) continue;
  const hp = Number(match[1]);
  if (recipe.powerOutputHp !== hp) {
    recipe.powerOutputHp = hp;
    repaired++;
  }
}
fs.writeFileSync(path, JSON.stringify(data, null, 2) + '\n');
console.log(JSON.stringify({ path, repaired }));
