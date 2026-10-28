import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {applyHatcheryStructure} from './hatchery_building_content.mjs';
const root=new URL('../',import.meta.url),folder=new URL('outputs/hatchery-platform-candidate/',root);
const read=async path=>JSON.parse(await readFile(path,'utf8'));
const layout=await read(new URL('FishHatchery-layout.json',folder));
const manifest=await read(new URL('FishHatchery-structure.json',folder));
const current=await read(new URL('src/DeepFrontier/Data/Buildings/Food/FishHatchery/FishHatchery.IronTeeth.blueprint.json',root));
const value=applyHatcheryStructure(structuredClone(current),layout,manifest);
const block=(x,y,z)=>value.BlockObjectSpec.Blocks[(z*8+y)*8+x];
assert.deepEqual(value.BlockObjectSpec.Size,{X:8,Y:8,Z:5});
assert.equal(value.BlockObjectSpec.BaseZ,1);assert.equal(value.BlockObjectSpec.Flippable,true);
assert.deepEqual(value.BuildingAccessibleSpec.LocalAccess,{X:2.5,Y:1,Z:1});
assert.ok(!Object.hasOwn(value,'BuildingWalkwaySpec'));
assert.ok(value.BlockObjectSpec.Blocks.every(b=>!b.Occupations.includes('Path')));
for(let x=0;x<8;x++) {
  assert.equal(block(x,0,0).Occupations,'None');assert.equal(block(x,0,1).MatterBelow,'GroundOrStackable');
}
for(const x of [0,1,2,5])assert.equal(block(x,0,1).Occupations,'Floor');
assert.deepEqual(value.PathModelTypeEnforcerSpec,{PathModelType:'Roof'});
for(const [x,y,z] of layout.buildableCells) {
  assert.equal(block(x,y,z).Occupations,'None');assert.equal(block(x,y,z-1).Stackable,'BlockObject');
}
assert.equal(block(2,2,1).Occupations,'All');assert.equal(block(2,5,1).Occupations,'None');
assert.equal(block(2,5,0).Stackable,'None');assert.equal(block(6,5,0).Occupations,'Top, Corners');
assert.equal(block(5,3,1).Occupations,'All');assert.equal(block(7,3,1).Occupations,'All');
assert.deepEqual(value.BlockObjectNavMeshSettingsSpec.EdgeGroups.flatMap(g=>g.AddedEdges),[
  {Start:{X:2,Y:1,Z:1},End:{X:2,Y:0,Z:1},IsTwoWay:true}]);
const ports=value.TransputProviderSpec.Transputs;
const port=(x,y,z)=>ports.find(p=>p.Coordinates.X===x&&p.Coordinates.Y===y&&p.Coordinates.Z===z);
assert.ok(port(1,1,1).Directions.includes('Left'));assert.ok(port(3,2,1).Directions.includes('Up'));
assert.ok(port(7,1,1).Directions.includes('Right'));assert.equal(port(2,1,1),undefined);
for(const field of ['MechanicalNodeSpec','WorkplaceSpec','ManufactorySpec','WaterDepthWorkCellsSpec','AdaptiveSupportsSpec','BuildingPipeTargetPortsSpec'])
  assert.deepEqual(value[field],current[field],field+' changed during structure migration');
assert.equal(value.MechanicalNodeSpec.PowerInput,55);assert.equal(value.MechanicalNodeSpec.PowerOutput,0);
assert.equal(value.BuildingSpec.ScienceCost,600);assert.equal(value.WorkplaceSpec.MaxWorkers,2);
const digest=createHash('sha256').update(JSON.stringify({layout,manifest})).digest('hex');
const report={scope:'Candidate authoring contracts only; native placement still pending',contractSha256:digest,
  playerPathCells:layout.suggestedPathCells.length,stackableDockCells:layout.buildableCells.length,
  powerPortCells:ports.length,actualPickingBoxes:value.Children['#Finished'].CollidersSpec.BoxColliders.length,
  baseZ:1,science:600,workers:2,powerInputHp:55,powerOutputHp:0};
await writeFile(new URL('structural-contract-checks.json',folder),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report));
