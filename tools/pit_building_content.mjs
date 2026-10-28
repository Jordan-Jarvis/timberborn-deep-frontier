import {readFile} from 'node:fs/promises';
import {industrialColliders} from './industrial_occupancy.mjs';
import {applyNativeBuildingAssembly} from './native_building_content.mjs';

const layouts=JSON.parse(await readFile(new URL('./pit-layouts.json',import.meta.url),'utf8'));
const xyz=([X,Y,Z])=>({X,Y,Z});

// Native blocks from the registered column heights (also read by
// validate_freed_cells.mjs).
export function pitBlocks(id) {
  const d=layouts[id];
  if(!d)throw new Error(`Missing pit registration: ${id}`);
  const [w,h,layers]=d.size;
  if(d.columnHeights.length!==h||d.columnHeights.some(row=>row.length!==w))
    throw new Error('Pit column mask dimensions differ');
  const blocks=[];
  for(let z=0;z<layers;z++)for(let y=0;y<h;y++)for(let x=0;x<w;x++) {
    const height=d.columnHeights[y][x];
    if(!Number.isInteger(height)||height<0||height>layers)throw new Error('Invalid pit column height');
    // The authored path cell between the entrance and a set-back door (the
    // sandstone pit); a door on the footprint edge has none (limestone).
    if(d.approachFloor===undefined)throw new Error(`${id}: approachFloor must be declared (a cell or null)`);
    const doorway=d.approachFloor!==null&&x===d.approachFloor[0]&&y===d.approachFloor[1]&&z===d.approachFloor[2];
    blocks.push({
      // A column with no structure (height 0) is free ground: no matter rule.
      MatterBelow:z===0&&height>0?'Ground':'Any',
      // The authored apron is a physical floor. Leave the Path bit free so
      // a native path may occupy the doorway without being buried in timber.
      Occupations:doorway?'Floor':z>=height?'None':'All',
      Stackable:'None',OccupyAllBelow:false,Underground:false,
    });
  }
  return blocks;
}

export async function applyPitLayout(value,building) {
  const d=layouts[building.id];
  if(!d||building.kind!=='pit')throw new Error(`Missing pit registration: ${building.id}`);
  if(JSON.stringify(d.size)!==JSON.stringify(building.size))throw new Error('Pit catalog size differs');
  const blocks=pitBlocks(building.id);
  value.BlockObjectSpec={Size:xyz(d.size),Blocks:blocks,
    Entrance:{HasEntrance:true,Coordinates:xyz(d.entrance)},
    BaseZ:0,Overridable:false,Flippable:true};
  value.PathModelTypeEnforcerSpec={PathModelType:'Roof'};
  const [ix,iy,iz]=d.idle[0],[ox,oy,oz]=d.origin;
  value.BuildingAccessibleSpec.LocalAccess=xyz([ix+ox,iz+oz,iy+oy]);
  value.Children['#Finished'].CollidersSpec=industrialColliders(blocks,d.size,0);
  value.Children['#Unfinished'].Children.ConstructionStage0.CollidersSpec=industrialColliders(blocks,d.size,0);
  value.TransformSlotInitializerSpec={Slots:[{SlotKeyword:'Entrance',Animation:'ForcedIdle',
    Inanimate:false,RandomizeYRotation:false,WaterSlot:false}]};
  value.WorkplaceSlotManagerSpec={};
  // Native ScavengerWorkplaceBehavior keeps its harvesting/hauling ownership.
  // Only the hand-hoist's cosmetic delivery cycle needs an extra decorator.
  value.MineralPitAnimationSpec={};
  await applyNativeBuildingAssembly(value,building.id,d.origin,
    {goodId:building.good,flowNodes:[],wheelNodes:[]});
}
