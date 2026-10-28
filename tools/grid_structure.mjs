// Shared explicit structural authoring. No rounding or mesh fitting.
export function structureBlocks(structure,size) {
  const [w,d,h]=size,index=([x,y,z])=>(z*d+y)*w+x;
  const blocks=Array.from({length:w*d*h},()=>({MatterBelow:'Any',Occupations:'None',Stackable:'None',OccupyAllBelow:false,Underground:false}));
  const bounds=b=>{
    if(b.length!==6 || b.some(v=>!Number.isInteger(v)) || b.slice(0,3).some((v,i)=>v<0||v>=b[i+3]||b[i+3]>size[i]))throw new Error('Invalid explicit structural bounds '+b);
  };
  for(const [id,b] of Object.entries(structure.platforms)) {
    bounds(b);const [x0,y0,z0,x1,y1,z1]=b;
    for(let y=y0;y<y1;y++)for(let x=x0;x<x1;x++) {
      Object.assign(blocks[index([x,y,z1-1])],{Occupations:'Top, Corners',Stackable:'BlockObject'});
    }
    for(const [cell,corner,bottom] of structure.supports[id]) {
      if(cell.length!==2||corner.length!==2||corner.some(v=>v!==-1&&v!==1)||!Number.isInteger(bottom)||bottom<z0||bottom>=z1||z1-bottom>2||cell[0]<x0||cell[0]>=x1||cell[1]<y0||cell[1]>=y1)throw new Error('Invalid authored short deck support '+id);
      for(let z=bottom;z<z1;z++) {
        const block=blocks[index([...cell,z])];
        block.MatterBelow=z===0?'GroundOrStackable':'Any';
        if(!block.Occupations.includes('Top'))block.Occupations='Corners';
      }
    }
  }
  for(const b of [...Object.values(structure.rooms),...structure.reservations]) {
    bounds(b);const [x0,y0,z0,x1,y1,z1]=b;
    for(let z=z0;z<z1;z++)for(let y=y0;y<y1;y++)for(let x=x0;x<x1;x++) {
      Object.assign(blocks[index([x,y,z])],{MatterBelow:z===0?'GroundOrStackable':'Any',Occupations:'All',Stackable:'None'});
    }
  }
  // A player may stack on every physically clear deck tile, including tiles
  // with no built-in walking route. Covered rooms keep their solid occupation.
  for(const b of Object.values(structure.platforms))for(let y=b[1];y<b[4];y++)for(let x=b[0];x<b[3];x++) {
    const above=blocks[index([x,y,b[5]])];
    if(above.Occupations!=='All')blocks[index([x,y,b[5]-1])].Stackable='BlockObject';
  }
  return blocks;
}

export function authoredColliders(manifest,structure,baseZ) {
  if(manifest.schema!==1 || manifest.coordinateSystem!=='Native grid XYZ, Z up, before BaseZ')throw new Error('Unsupported structural picking schema');
  if(!Number.isInteger(baseZ)||baseZ<0)throw new Error('Explicit BaseZ required');
  const expected=new Map([...Object.entries(structure.platforms),...Object.entries(structure.rooms)]);
  for(const [id,bounds] of expected) {
    const parts=manifest.parts.filter(p=>p.id===id);
    if(parts.length!==1||JSON.stringify(parts[0].bounds)!==JSON.stringify(bounds))throw new Error('Mesh/placement structural contract differs: '+id);
    if(parts[0].kind==='platform'&&JSON.stringify(parts[0].supports)!==JSON.stringify(structure.supports[id]))throw new Error('Mesh/placement support contract differs: '+id);
  }
  const boxes=manifest.parts.flatMap(p=>p.pickingBoxes);
  if(!boxes.length)throw new Error('No authored picking volumes');
  return {BoxColliders:boxes.map(b=>{
    if(b.center.length!==3||b.size.length!==3||[...b.center,...b.size].some(v=>!Number.isFinite(v))||b.size.some(v=>v<=0))throw new Error('Invalid authored picking box');
    return {Center:{X:b.center[0],Y:b.center[2]-baseZ,Z:b.center[1]},Size:{X:b.size[0],Y:b.size[2],Z:b.size[1]}};
  }),SphereColliders:[],CapsuleColliders:[]};
}

export function roomPowerFaces(structure,size) {
  // Native building-to-shaft transfer at exposed room faces on every floor.
  // Empty platform bays do not acquire invisible mechanical sockets.
  const occupied=new Set();
  for(const b of Object.values(structure.rooms))for(let z=b[2];z<b[5];z++)for(let y=b[1];y<b[4];y++)for(let x=b[0];x<b[3];x++)occupied.add([x,y,z].join(','));
  const result=[];
  for(const key of occupied) {
    const [x,y,z]=key.split(',').map(Number),directions=[];
    for(const [dx,dy,name] of [[-1,0,'Left'],[1,0,'Right'],[0,-1,'Down'],[0,1,'Up']]) {
      const doorway=Object.values(structure.doors).some(door=>{
        const [px,py,pz]=door.position;
        return pz===z && door.outward[0]===dx && door.outward[1]===dy
          && px===x+.5+dx*.5 && py===y+.5+dy*.5;
      });
      if(!occupied.has([x+dx,y+dy,z].join(','))&&!doorway)directions.push(name);
    }
    if(z===0)directions.push('Bottom');
    if(directions.length)result.push({Coordinates:{X:x,Y:y,Z:z},Directions:directions.join(', '),ReverseRotation:false});
  }
  return result;
}
