// Explicit structural cells for the reviewed meshes. Bounds use native grid XYZ
// (Z is height), and are inclusive. Empty space is deliberately unoccupied.
export function industrialBlocks(ident, size) {
  const [w,h,layers]=size;
  const blocks=Array.from({length:w*h*layers},()=>({MatterBelow:'Any',Occupations:'None',Stackable:'None',OccupyAllBelow:false,Underground:false}));
  const region=(bounds,occupation)=>{
    const [x0,y0,z0,x1,y1,z1]=bounds;
    if(x0<0||y0<0||z0<0||x1>=w||y1>=h||z1>=layers)throw new Error(`Structural region outside ${ident}: ${bounds}`);
    for(let z=z0;z<=z1;z++)for(let y=y0;y<=y1;y++)for(let x=x0;x<=x1;x++){
      const b=blocks[(z*h+y)*w+x];b.Occupations=occupation;
      b.MatterBelow=z===0?'GroundOrStackable':'Any';
    }
  };
  // Cells follow the grid-registered artwork. Since 2026-10-21 these
  // machines have no walkable decks or balconies: every cell holding real
  // structure is occupied and everything else, including the ground around
  // the machinery, stays None. Checked against the saved scenes with the
  // alignment audit (outputs/alignment-audit/trio-after).
  const clear=(...cells)=>{for(const [x,y,z] of cells){
    const b=blocks[(z*h+y)*w+x];b.Occupations='None';b.MatterBelow='Any';
  }};
  // 2026-10-22: footprints end at the walls on all four sides (no apron,
  // yard or decoration tiles beyond them); coordinates follow the shrunk
  // registrations in industrial_layouts.py.
  if(ident==='StoneCrusher') {
    region([0,0,0,3,3,1],'All'); // workshop housing (walls on the x=0, x=4, y=4 edges), porch, output bin
    region([0,0,2,3,3,2],'All'); // concrete machine floor: flywheel, rolls, bearings, hopper legs
    clear([0,2,2]);              // open strip beside the hopper
    region([0,2,3,3,3,3],'All'); // hopper and roll canopy
    region([0,1,3,2,1,3],'All'); // hopper front and flywheel top
  } else if(ident==='CementKiln') {
    // Compact 5x3x4 (2026-10-30), grid y = artwork y + 1.
    region([0,0,0,4,0,0],'All'); // log stack, coal bin, porch and doorstep (3,0,0), output bin
    region([2,0,1,4,0,1],'All'); // porch canopy and its eaves
    region([0,1,0,4,2,2],'All'); // feed house, drum hall and roof, firebox and crown
    region([4,2,3,4,2,3],'All'); // chimney stack
  } else if(ident==='ConcreteMixer') {
    // Compact 4x3x3 (2026-10-30).
    region([0,0,0,3,2,1],'All'); // operator room and canopy (doorstep (1,0,0)), drum, drive, tray, tank pedestal
    region([0,1,2,3,2,2],'All'); // hoppers on the room roof, their chutes, drum crown, header tank
  } else if(ident==='MineralQuarry') {
    // Compact 8x6x5 (2026-10-30), grid y = artwork y - 1. Stone plinth and
    // the ground front row (water tank, cabin and doorstep (1,0,0), stone bin);
    // the cabin roof, supply bins and spoil heap on the front strip; the tool
    // room; the supply pipe; the boarded headframe with receiver and sheave;
    // the winding house; the belt, screen and drives.
    region([0,0,0,7,5,0],'All');
    region([0,0,1,5,0,1],'All');
    region([0,1,1,1,5,2],'All');
    region([2,1,1,3,1,1],'All');
    region([4,2,1,6,4,4],'All');
    region([3,4,1,6,5,2],'All');
    region([6,1,1,7,3,1],'All');region([7,3,2,7,3,2],'All');
    // Only these 25 foundations require one native 5x5 seam (the old
    // registration's cells, so a saved quarry stays over its seam).
    region([3,1,0,7,5,0],'Top');
    for(let y=1;y<6;y++)for(let x=3;x<8;x++)blocks[y*w+x].MatterBelow='Ground';
  } else throw new Error(`No structural occupation authored for ${ident}`);
  return blocks;
}

export function industrialColliders(blocks,[w,h],baseZ) {
  if(!Number.isInteger(baseZ)||baseZ<0)throw new Error('Collider registration requires explicit nonnegative native BaseZ');
  const boxes=[];
  const box=(x,y,z,sx,sy,sz)=>boxes.push({Center:{X:x,Y:z-baseZ,Z:y},Size:{X:sx,Y:sz,Z:sy}});
  blocks.forEach((b,i)=>{
    const x=i%w,y=Math.floor(i/w)%h,z=Math.floor(i/(w*h));
    const mask=new Set(b.Occupations.split(', '));
    if(mask.has('All')){box(x+.5,y+.5,z+.5,1,1,1);return;}
    if(mask.has('Top'))box(x+.5,y+.5,z+.94,1,1,.12);
    if(mask.has('Floor')||mask.has('Bottom'))box(x+.5,y+.5,z+.025,1,1,.05);
    if(mask.has('Corners'))for(const dx of [.09,.91])for(const dy of [.09,.91])box(x+dx,y+dy,z+.5,.18,.18,1);
  });
  return {BoxColliders:boxes,SphereColliders:[],CapsuleColliders:[]};
}
