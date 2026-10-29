// Native structural contracts. Called by the construction content generator
// only after reviewed meshes have been promoted alongside these blueprints.
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {dirname,resolve} from 'node:path';
import {industrialColliders} from './industrial_occupancy.mjs';
import {scaledCost} from './lategame_costs.mjs';

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

// Overhangs: a 1×N deck whose first A tiles are supported anchors (native
// foundations, GroundOrStackable) and whose other tiles cantilever (Any); every
// tile is a stackable top. Overhang6x1's SideLine layout and CustomPivot on the
// first anchor tile are kept. A = 1 for the concrete 8×1; the steel
// cantilevers need more anchor tiles as they grow (10×1: 1, 12×1: 2, 15×1: 3),
// an AND of native foundations: every anchor tile must stand on ground or a
// stackable top, and losing any one deletes the deck like any native support.
const STEEL_CANTILEVERS={10:1,12:2,15:3};
export function overhangContract(building) {
  const [w,length,layers]=building.size;
  const anchors=building.anchors;
  if(w!==1||layers!==1||!Number.isInteger(anchors)||anchors<1||anchors>=length)
    throw new Error('Overhang geometry contract changed: '+building.id);
  if(building.id==='ConcreteOverhang8x1') {
    if(length!==8||anchors!==1)throw new Error('ConcreteOverhang8x1 must stay 1×8 with one anchor tile');
    return {length,anchors};
  }
  if(STEEL_CANTILEVERS[length]!==anchors||building.id!==`SteelCantilever${length}x1`)
    throw new Error(`Overhang ${building.id} is not a steel cantilever ${Object.entries(STEEL_CANTILEVERS).map(([n,a])=>`${n}×1/${a}`).join(', ')}`);
  steelCost(building,{steel:4*length,concrete:3*length+12*anchors,science:1000*length});
  return {length,anchors};
}

// Steel structures (High-Grade Steel from the steel mill, plus Concrete):
// deliberately heavy late-game costs, set per piece in structural_content.json
// and checked here against these formulas.
//   cantilever N×1, A anchors: 8N steel, 6N + 24A concrete, 1000N science
//   bridge, N span tiles:      10N steel, 48 + 4N concrete, 800N science
//   column, H layers:          10H steel, 12 + 6H concrete, 4000 + 500H science
//   deck n×n:                  6n² steel, 4n² + 40 concrete, 600n² science
// Base costs; scaledCost multiplies them by the science tier's costFactor
// (halved on 2026-10-29 once the x2..x8 factors landed).
function steelCost(building,{steel,concrete,science}) {
  const cost=[['HighGradeSteel',steel],['Concrete',concrete]];
  if(JSON.stringify(building.cost)!==JSON.stringify(cost)||building.science!==science)
    throw new Error(`${building.id} cost/science must be ${JSON.stringify(cost)} / ${science}`);
}

// Steel truss bridges: a clone of the vanilla SuspensionBridge6x1 contract,
// size [1, N+1, 1]: the near tile is the only foundation (GroundOrStackable,
// Bottom, Corners, Path, Middle), the N span tiles need open air below (Air,
// Floor, Bottom, Corners, Path, Middle). Like the vanilla bridge the far end
// needs nothing: it meets a path or platform on the far bank at the same
// height, so a span of N tiles bridges a gap of exactly N tiles.
const STEEL_BRIDGE_SPANS=[8,10,12,15];
export function bridgeSpan(building) {
  const [w,depth,layers]=building.size;
  const span=depth-1;
  if(w!==1||layers!==1||!STEEL_BRIDGE_SPANS.includes(span)||building.id!==`SteelBridge${span}x1`)
    throw new Error('Steel bridge geometry contract changed: '+building.id);
  steelCost(building,{steel:5*span,concrete:24+2*span,science:800*span});
  return span;
}

// Steel columns: stackable trestles H = 1..6 layers, size [1, 1, H], like a tall
// vanilla TriplePlatform: foundation GroundOrStackable at z = 0, Corners all the
// way up, the top block Top, Corners and Stackable. Columns stack on columns.
const STEEL_COLUMN_HEIGHTS=[1,2,3,4,5,6];
export function columnHeight(building) {
  const [w,h,height]=building.size;
  if(w!==1||h!==1||!STEEL_COLUMN_HEIGHTS.includes(height)||building.id!==`SteelColumnH${height}`)
    throw new Error('Steel column geometry contract changed: '+building.id);
  steelCost(building,{steel:5*height,concrete:6+3*height,science:4000+500*height});
  return height;
}

// Steel decks: an n×n one-layer deck (n = 3, 5), size [n, n, 1], resting on its
// four corner tiles: the corners are the only foundations (GroundOrStackable,
// Top, Corners), every other tile Any/Top; all tiles are stackable tops. The
// corners can stand on ground, platforms or steel columns of different heights.
const STEEL_DECK_SPANS=[3,5];
export function deckSpan(building) {
  const [n,depth,layers]=building.size;
  if(n!==depth||layers!==1||!STEEL_DECK_SPANS.includes(n)||building.id!==`SteelDeck${n}x${n}`)
    throw new Error('Steel deck geometry contract changed: '+building.id);
  steelCost(building,{steel:3*n*n,concrete:2*n*n+20,science:600*n*n});
  return n;
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
  const block=(MatterBelow,Occupations,Stackable)=>({MatterBelow,Occupations,Stackable,OccupyAllBelow:false,Underground:false});
  if(building.kind==='bridge') {
    const span=bridgeSpan(building);
    return Array.from({length:span+1},(_,y)=>y===0?block('GroundOrStackable','Bottom, Corners, Path, Middle','None')
      :block('Air','Floor, Bottom, Corners, Path, Middle','None'));
  }
  if(building.kind==='column') {
    const height=columnHeight(building);
    return Array.from({length:height},(_,z)=>block(z===0?'GroundOrStackable':'Any',
      z===height-1?'Top, Corners':'Corners',z===height-1?'BlockObject':'None'));
  }
  if(building.kind==='deck') {
    const n=deckSpan(building);
    const blocks=[];
    for(let y=0;y<n;y++)for(let x=0;x<n;x++) {
      const corner=(x===0||x===n-1)&&(y===0||y===n-1);
      blocks.push(block(corner?'GroundOrStackable':'Any',corner?'Top, Corners':'Top','BlockObject'));
    }
    return blocks;
  }
  if(building.kind!=='overhang'&&building.kind!=='scaffold')throw new Error('Unknown structure kind');
  const anchors=building.kind==='overhang'?overhangContract(building).anchors:0;
  const blocks=[];
  for(let z=0;z<layers;z++)for(let y=0;y<h;y++)for(let x=0;x<w;x++) {
    let occupation,below,stackable;
    if(building.kind==='overhang') {
      occupation=y<anchors?'Top, Corners':'Top';
      below=y<anchors?'GroundOrStackable':'Any';
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

// The vanilla SuspensionBridge6x1 path: one path edge group with a one-way edge
// off the near end (0,0)->(0,-1), two-way edges along the bridge and a one-way
// edge off the far end onto the bank (0,N)->(0,N+1); the PathSpec main path on
// the abutment tile and a straight driveway in front of it. The edges are
// rebuilt for N span tiles; any other vanilla shape is refused.
function bridgePath(v,span) {
  const edge=(a,b,IsTwoWay)=>({Start:{X:0,Y:a,Z:0},End:{X:0,Y:b,Z:0},IsTwoWay});
  const vanilla=[edge(0,-1,false),...Array.from({length:6},(_,k)=>edge(k,k+1,true)),edge(6,7,false)];
  const nav=v.BlockObjectNavMeshSettingsSpec;
  if(nav.EdgeGroups.length!==1||!nav.EdgeGroups[0].IsPath||
     JSON.stringify(nav.EdgeGroups[0].AddedEdges)!==JSON.stringify(vanilla)||nav.GenerateFloorsOnStackable!==false||
     JSON.stringify(v.PathSpec)!==JSON.stringify({MainPathCoordinates:{X:0,Y:0,Z:0}})||!v.BlockObjectWithPathRangeSpec||
     v.DrivewayModelsSpec?.Driveways?.length!==1||v.PlaceableBlockObjectSpec.Layout!=='Single')
    throw new Error('Native suspension bridge path contract changed');
  nav.EdgeGroups[0].AddedEdges=[edge(0,-1,false),...Array.from({length:span},(_,k)=>edge(k,k+1,true)),edge(span,span+1,false)];
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
    bridge:'Buildings/Paths/SuspensionBridge6x1/SuspensionBridge6x1.IronTeeth.blueprint.json',
    column:'Buildings/Paths/TriplePlatform/TriplePlatform.IronTeeth.blueprint.json',
    deck:'Buildings/Paths/MetalPlatform5x5/MetalPlatform5x5.IronTeeth.blueprint.json',
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
    v.BuildingSpec.BuildingCost=scaledCost(b.cost.map(([Id,Amount])=>({Id,Amount})),b.science);
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
    if(b.kind==='bridge')bridgePath(v,bridgeSpan(b));
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
