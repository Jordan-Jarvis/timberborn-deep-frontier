import {readFile} from 'node:fs/promises';
const data=new URL('../src/DeepFrontier/Data/',import.meta.url);
const xyz=([X,Y,Z])=>({X,Y,Z});

// Model coordinates are authored X/across, Y/back, Z/up. Convert exactly once
// into Unity local coordinates with the explicit building registration origin.
export async function applyNativeBuildingAssembly(value,ident,origin,{goodId,flowNodes,wheelNodes}){
  const assembly=JSON.parse(await readFile(new URL(`../outputs/reference-studies/${ident}-native-assembly.json`,import.meta.url),'utf8'));
  const position=([x,y,z])=>xyz([x+origin[0],z+origin[2],y+origin[1]]);
  const finished=value.Children['#Finished'];
  // The producing blueprint owns this child collection. Existing children are
  // preserved and duplicate authored prop IDs are errors.
  if(!Object.hasOwn(finished,'Children'))finished.Children={};
  for(const prop of assembly.props){
    if(Object.hasOwn(finished.Children,prop.name))throw new Error(`Duplicate native building prop: ${prop.name}`);
    finished.Children[prop.name]={TimbermeshSpec:{Model:prop.resource}};
  }
  for(const p of assembly.props)if(Object.hasOwn(p,'plantAppearance')&&p.plantAppearance!=='Flowering')throw new Error('Unknown authored native plant appearance: '+p.plantAppearance);
  // A building without native props (no forced ground decoration,
  // 2026-10-22) carries no NativeBuildingPropsSpec at all.
  if(assembly.props.length)value.NativeBuildingPropsSpec={Props:assembly.props.map(p=>({Node:p.name,Position:position(p.position),
    Rotation:xyz([0,p.yaw,0]),Scale:xyz([p.scale,p.scale,p.scale]),Flowering:p.plantAppearance==='Flowering'}))};
  else delete value.NativeBuildingPropsSpec;
  if(assembly.liquids.length===0)return;
  const recipes=await Promise.all(value.ManufactorySpec.ProductionRecipeIds.map(async id=>
    JSON.parse(await readFile(new URL(`Recipes/Recipe.${id}.blueprint.json`,data),'utf8')).RecipeSpec));
  const allowances=recipes.flatMap(r=>r.Ingredients.filter(g=>g.Id===goodId).map(g=>g.Amount*r.CyclesCapacity));
  if(allowances.length===0)throw new Error(`${ident} has visible water but no water-consuming recipe`);
  const capacity=Math.max(...allowances);
  value.WorkshopReservoirSpec={GoodId:goodId,Capacity:capacity,Material:'Materials/Goods/Water',
    Surfaces:assembly.liquids.map(s=>{
      const meshes={SmallLiquidPlane:'StockpileGoodModels/SmallLiquidPlane',Rectangle:'Meshes/DeepFrontier/ReservoirRectangle'};
      if(!Object.hasOwn(meshes,s.shape))throw new Error('Unknown authored reservoir shape: '+s.name+' / '+s.shape);
      return {Node:s.name,Mesh:meshes[s.shape],Position:position([...s.center,0]),
        Scale:xyz([s.scale[0],1,s.scale[1]]),EmptyHeight:s.bottom+origin[2],FullHeight:s.top+origin[2]};
    }),FlowNodes:flowNodes,WheelNodes:wheelNodes};
}
