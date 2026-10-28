// Native structural contracts. Called by the construction content generator
// only after reviewed meshes have been promoted alongside these blueprints.
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {dirname,resolve} from 'node:path';
import {industrialColliders} from './industrial_occupancy.mjs';

const root=new URL('../',import.meta.url);
const catalog=JSON.parse(await readFile(new URL('tools/structural_content.json',root),'utf8'));
const layouts=JSON.parse(await readFile(new URL('tools/structural-layouts.json',root),'utf8'));
const nativeRoot=new URL('vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources/',root);
const xyz=([X,Y,Z])=>({X,Y,Z});

// Concrete platforms: an n×n deck (n = 3, 4 or 5) on four corner legs
// H = 1, 2 or 3 layers high, size [n, n, H+1]. The cost and science scale with
// k = n² + H: k × (3 Concrete, 2 Metal block, 1 Gear) and 500 × k science.
// Each deck cell and each leg layer carries the same 3:2:1 bill, which
// reproduces the original 3×3, 3-high platform exactly (k = 12: 36/24/12, 6000).
const SCAFFOLD_SPANS=[3,4,5],SCAFFOLD_LEGS=[1,2,3];
export function scaffoldLegs(building) {
  const [w,h,layers]=building.size;
  const legs=layers-1;
  if(w!==h||!SCAFFOLD_SPANS.includes(w)||!SCAFFOLD_LEGS.includes(legs))
    throw new Error('Scaffold geometry contract changed: '+building.id);
  const expectedId=w===3&&legs===3?'ConcreteScaffold3x3':`ConcreteScaffold${w}x${w}H${legs}`;
  if(building.id!==expectedId)throw new Error(`Scaffold ${building.id} must be named ${expectedId}`);
  const k=w*w+legs;
  const cost=[['Concrete',3*k],['MetalBlock',2*k],['Gear',k]];
  if(JSON.stringify(building.cost)!==JSON.stringify(cost)||building.science!==500*k)
    throw new Error(`Scaffold ${building.id} cost/science differs from k=${k} formula`);
  return legs;
}

// Concrete side platforms: a legless n×n deck (n = 3, 4 or 5) hung beside a
// one-cell anchor (ReinforcedDamBlock, marked deckAnchor) at the same layer, so
// the deck top is level with the anchor top. Size [W, n+1, 2] with an odd grid
// width W (n for odd n, n+1 for even n, the extra column empty): deck cells at
// z=0, x<n, y<n; the anchor cell is (a, n, 0) with a = (W-1)/2 = floor(n/2).
// Native picking places a CustomPivot without applying FlipMode, while blocks
// flip as x -> W-1-x, so the anchor (and pivot) column must be the grid's
// centre column or a flipped deck lands its cleat beside the hovered anchor. The only foundation block is the cleat directly above the
// anchor, (a, n, 1): MatterBelow Stackable, Occupations Floor. Floor is the
// lowest native load-order occupation (BlockObjectBatchLoader sorts by
// CoordinatesAtBaseZ.z, then by the highest occupation on the BaseZ layer), so
// paths and stairs built on the deck, which share that load layer, still load
// after it. The cleat makes native stacking rules carry the deck: placement
// (MatterBelow), TerrainPhysicsPostLoader reachability, stack deletion and the
// anchor's "object atop" deletion blocker. AnchoredDeckValidator (C#) narrows
// the stackable anchor to deckAnchor structures. Costs follow the platform
// formula with no leg layers: k = n², k × (3 Concrete, 2 Metal block, 1 Gear),
// 500 × k science.
export function sideDeckSpan(building) {
  const [width,depth,layers]=building.size;
  const n=depth-1;
  if(!SCAFFOLD_SPANS.includes(n)||width!==(n%2?n:n+1)||layers!==2)
    throw new Error('Side platform geometry contract changed: '+building.id);
  return n;
}

export function sideDeckAnchor(building) {
  const n=sideDeckSpan(building);
  if(building.id!==`ConcreteSidePlatform${n}x${n}`)
    throw new Error(`Side platform ${building.id} must be named ConcreteSidePlatform${n}x${n}`);
  const k=n*n;
  const cost=[['Concrete',3*k],['MetalBlock',2*k],['Gear',k]];
  if(JSON.stringify(building.cost)!==JSON.stringify(cost)||building.science!==500*k)
    throw new Error(`Side platform ${building.id} cost/science differs from k=${k} formula`);
  return [Math.floor(n/2),n,0];
}

export function structuralBlocks(building) {
  const [w,h,layers]=building.size;
  if(building.kind==='block'||building.kind==='dam') {
    if(w!==1||h!==1||layers!==1)throw new Error('Masonry modules must be 1×1×1');
    return [{MatterBelow:'GroundOrStackable',Occupations:'All',Stackable:'BlockObject',
      OccupyAllBelow:false,Underground:false}];
  }
  if(building.kind==='sidedeck') {
    const [ax,ay]=sideDeckAnchor(building);
    const blocks=[];
    for(let z=0;z<layers;z++)for(let y=0;y<h;y++)for(let x=0;x<w;x++) {
      const deck=z===0&&y<ay&&x<ay, cleat=z===1&&y===ay&&x===ax;
      blocks.push({MatterBelow:cleat?'Stackable':'Any',
        Occupations:deck?'Top':cleat?'Floor':'None',
        Stackable:deck?'BlockObject':'None',OccupyAllBelow:false,Underground:false});
    }
    return blocks;
  }
  if(building.kind!=='overhang'&&building.kind!=='scaffold')throw new Error('Unknown structure kind');
  const blocks=[];
  for(let z=0;z<layers;z++)for(let y=0;y<h;y++)for(let x=0;x<w;x++) {
    let occupation,below,stackable;
    if(building.kind==='overhang') {
      if(w!==1||h!==8||layers!==1)throw new Error('Overhang geometry contract changed');
      occupation=y===0?'Top, Corners':'Top';
      below=y===0?'GroundOrStackable':'Any';
      stackable='BlockObject';
    } else {
      scaffoldLegs(building);
      const deck=layers-1;
      const corner=(x===0||x===w-1)&&(y===0||y===h-1);
      // Corner columns occupy the four corner cells below the deck; knee
      // braces, girders and joists stay inside the deck layer. The central
      // cross remains clear through the entire structure.
      occupation=z===deck?(corner?'All':'Top'):(corner?'Corners':'None');
      below=z===0&&corner?'GroundOrStackable':'Any';
      stackable=z===deck?'BlockObject':'None';
    }
    blocks.push({MatterBelow:below,Occupations:occupation,Stackable:stackable,
      OccupyAllBelow:false,Underground:false});
  }
  return blocks;
}

// Localization for src/DeepFrontier/Scripts/AnchoredDecks (AnchoredDeckLoc).
export const ANCHORED_DECK_ROWS=[
  ['DeepFrontier.AnchoredDeck.RequiresAnchor',
   'Must hang from the side of a reinforced dam block, level with its top. Point at the top of the dam block to place it.'],
];

export async function structuralBlueprints() {
  const result=[];
  const templates={
    block:'Buildings/Landscaping/Levee/Levee.IronTeeth.blueprint.json',
    dam:'Buildings/Landscaping/Dam/Dam.IronTeeth.blueprint.json',
    overhang:'Buildings/Paths/Overhang6x1/Overhang6x1.IronTeeth.blueprint.json',
    scaffold:'Buildings/Paths/MetalPlatform3x3/MetalPlatform3x3.IronTeeth.blueprint.json',
    sidedeck:'Buildings/Paths/MetalPlatform3x3/MetalPlatform3x3.IronTeeth.blueprint.json',
  };
  const anchors=catalog.buildings.filter(b=>b.deckAnchor);
  if(catalog.buildings.some(b=>b.kind==='sidedeck')&&!anchors.length)
    throw new Error('Side platforms need at least one deckAnchor structure');
  if(anchors.some(b=>b.kind!=='block'))
    throw new Error('Deck anchors must be stackable 1×1×1 blocks');
  for(const [index,b] of catalog.buildings.entries()) {
    if(!Object.hasOwn(templates,b.kind))throw new Error('Unknown structural template kind: '+b.kind);
    const layout=layouts[b.id];
    // Side platforms are picked from the anchor top (native BaseZ 1); their
    // art origin is one layer down so the deck top is the model's z = 0.
    const [originZ,baseZ]=b.kind==='sidedeck'?[-1,1]:[0,0];
    if(!layout||JSON.stringify(layout.size)!==JSON.stringify(b.size)||
       JSON.stringify(layout.origin)!==JSON.stringify([0,0,originZ])||layout.baseZ!==baseZ)
      throw new Error('Structural mesh registration differs: '+b.id);
    const v=JSON.parse(await readFile(new URL(templates[b.kind],nativeRoot),'utf8'));
    const model=`Buildings/Platforms/${b.id}/${b.id}.IronTeeth`;
    v.TemplateSpec.TemplateName=b.id+'.IronTeeth';
    v.TemplateSpec.BackwardCompatibleTemplateNames=[];
    v.BuildingSpec.BuildingCost=b.cost.map(([Id,Amount])=>({Id,Amount}));
    v.BuildingSpec.ScienceCost=b.science;
    v.BuildingModelSpec.FinishedUncoveredModelName='';
    const blocks=structuralBlocks(b);
    v.BlockObjectSpec={Size:xyz(b.size),Blocks:blocks,
      Entrance:{HasEntrance:false,Coordinates:xyz([0,0,0])},BaseZ:baseZ,Overridable:false,Flippable:true};
    const placement=v.PlaceableBlockObjectSpec;
    placement.ToolOrder=200+index;
    if(b.kind==='scaffold'||b.kind==='sidedeck')placement.Layout='Single';
    if(b.kind==='sidedeck') {
      // The cursor cell is the anchor: hovering a dam top hangs the deck beside it.
      const anchor=sideDeckAnchor(b);
      placement.CustomPivot={HasCustomPivot:true,Coordinates:{X:anchor[0]+.5,Y:anchor[1]+.5,Z:0}};
      v.AnchoredDeckSpec={Anchor:xyz(anchor)};
    }
    if(b.deckAnchor)v.AnchoredDeckAnchorSpec={};
    v.LabeledEntitySpec={
      DisplayNameLocKey:`Building.${b.id}.DisplayName`,
      DescriptionLocKey:`Building.${b.id}.Description`,
      FlavorDescriptionLocKey:`Building.${b.id}.FlavorDescription`,
      Icon:`Buildings/Platforms/${b.id}/Icon`,
    };
    v.ConstructionSiteProgressVisualizerSpec={ProgressThresholds:[]};
    const colliders=industrialColliders(blocks,b.size,baseZ);
    v.Children={
      '#Finished':{TimbermeshSpec:{Model:model+'.Model'},CollidersSpec:colliders},
      '#Unfinished':{Children:{ConstructionStage0:{
        TimbermeshSpec:{Model:model+'.ConstructionStage0.Model'},CollidersSpec:colliders}}},
    };
    if(b.kind==='block'||b.kind==='dam') {
      const height=b.kind==='block'?1:.65;
      if(v.WaterObstacleSpec.Coordinates.length!==1||v.FinishableWaterObstacleSpec.Height!==height)
        throw new Error('Native retaining water contract changed');
    } else if(v.WaterObstacleSpec||v.FinishableWaterObstacleSpec)
      throw new Error('Open structures must not obstruct water');
    if(v.MechanicalNodeSpec||v.WorkplaceSpec||v.ManufactorySpec)
      throw new Error('Passive structure acquired work or power behavior');
    const rows=[
      [`Building.${b.id}.DisplayName`,b.name],
      [`Building.${b.id}.Description`,b.description],
      [`Building.${b.id}.FlavorDescription`,'Room for the next layer of the colony.'],
    ];
    // The anchor rule's placement message ships once, with the first anchor.
    if(b===anchors[0])rows.push(...ANCHORED_DECK_ROWS);
    result.push({id:b.id,blueprint:v,path:model+'.blueprint.json',rows});
  }
  return result;
}

if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  for(const entry of await structuralBlueprints()) {
    const path=fileURLToPath(new URL('outputs/structural-integration/Data/'+entry.path,root));
    await mkdir(dirname(path),{recursive:true});
    await writeFile(path,JSON.stringify(entry.blueprint,null,2)+'\n');
  }
  console.log('Structural candidate blueprints authored; active data unchanged.');
}
