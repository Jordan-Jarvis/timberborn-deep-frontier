using System;
using System.Collections.Generic;
using System.Linq;
using Timberborn.BlockSystem;
using Timberborn.Coordinates;
using Timberborn.MechanicalSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // The civic acceptance fixtures (Restaurant, Hospital, Grocery) build their roads, deck
  // paths, stairs and shaft lines from the installed blueprint (BlockObjectSpec,
  // PlatformDeckSpec, TransputProviderSpec) rather than world literals, so a regenerated or
  // compacted building (2026-10-30: one layer per storey) carries its fixture with it.
  // Every placement still goes through native validation in the fixture's Create; nothing
  // here substitutes a cell when one is rejected.
  internal static class CivicFixtureGeometry {
    internal delegate BlockObject Place(string id,Vector3Int world,Orientation orientation);
    // The disposable fixture map's road row and its junction to the district centre's road
    // (x 173, y 156..159): map data, not building data.
    internal const int RoadY=159;
    internal static readonly Vector3Int RoadJunction=new(173,159,3);
    private static readonly Dictionary<string,Vector3Int> Steps=new() {
      {"Left",new Vector3Int(-1,0,0)},{"Right",new Vector3Int(1,0,0)},{"Down",new Vector3Int(0,-1,0)},{"Up",new Vector3Int(0,1,0)}};
    // Vanilla stairs climb, and belts run, toward -y at Cw0, -x at Cw90, +y at Cw180, +x at Cw270.
    internal static Orientation Toward(Vector3Int d)=>d.x>0?Orientation.Cw270:d.x<0?Orientation.Cw90:d.y>0?Orientation.Cw180:Orientation.Cw0;
    // The installed blueprint's blocks by local cell (unrotated, unflipped).
    internal static Dictionary<Vector3Int,BlockOccupations> Blocks(BlockObjectSpec spec)=>
      spec.GetBlocks(new Placement(Vector3Int.zero,Orientation.Cw0,FlipMode.Unflipped)).ToDictionary(b=>b.Coordinates,b=>b.Occupation);
    internal static bool InBounds(BlockObjectSpec spec,Vector3Int c)=>
      c.x>=0&&c.y>=0&&c.z>=0&&c.x<spec.Size.x&&c.y<spec.Size.y&&c.z<spec.Size.z;
    // Outside the bounds, or a cell of the building with no occupation.
    internal static bool Free(IReadOnlyDictionary<Vector3Int,BlockOccupations> blocks,Vector3Int c)=>
      !blocks.TryGetValue(c,out var o)||o==BlockOccupations.None;
    // Free from the ground (local z 0) up to and including the cell's own layer.
    internal static bool FreeColumn(IReadOnlyDictionary<Vector3Int,BlockOccupations> blocks,Vector3Int c)=>
      Enumerable.Range(0,c.z+1).All(z=>Free(blocks,new Vector3Int(c.x,c.y,z)));
    // Horizontal shaft faces of the blueprint's TransputProviderSpec: (wall cell, outward step).
    internal static List<(Vector3Int Cell,Vector3Int Out)> Faces(TransputProviderSpec spec)=>
      spec.Transputs.SelectMany(t=>t.Directions.ToString().Split(',').Select(d=>d.Trim()).Where(Steps.ContainsKey)
        .Select(d=>(t.Coordinates,Steps[d]))).ToList();
    // An interior cell at the ground layer: fully occupied with fully occupied neighbours on all
    // four sides, where the enclosed room must reject a ground Path.
    internal static Vector3Int RoomCell(BlockObjectSpec spec,string label) {
      var blocks=Blocks(spec);
      bool Solid(Vector3Int c)=>blocks.TryGetValue(c,out var o)&&o==BlockOccupations.All;
      var cell=blocks.Keys.Where(c=>c.z==0&&Solid(c)&&Steps.Values.All(s=>Solid(c+s))).OrderBy(c=>c.y).ThenBy(c=>c.x).ToArray();
      if(cell.Length==0)throw new InvalidOperationException(label+" blueprint has no enclosed ground cell to test room collision on");
      return cell[0];
    }
    // The ground road: the junction column (y 157..159), the road row from the door's column to the
    // junction, then straight north to the door's Entrance cell.
    internal static void Road(Place place,Func<Vector3Int,bool> hasPath,Vector3Int door) {
      if(door.z!=RoadJunction.z||door.y<=RoadY||door.x>=RoadJunction.x)
        throw new InvalidOperationException("Entrance "+door+" is not north-west of the fixture road junction "+RoadJunction);
      for(int y=RoadY-2;y<=RoadY;y++) {
        var c=new Vector3Int(RoadJunction.x,y,RoadJunction.z);
        if(!hasPath(c))place("Path",c,Orientation.Cw0);
      }
      for(int x=door.x;x<RoadJunction.x;x++)place("Path",new Vector3Int(x,RoadY,door.z),Orientation.Cw0);
      for(int y=RoadY+1;y<=door.y;y++)place("Path",new Vector3Int(door.x,y,door.z),Orientation.Cw0);
    }
    // Deck cells: every seed and the 4-connected cells of its layer inside the bounds that take
    // a native Path (the fixture's BlockValidator, before anything is placed on the deck).
    // A seed that takes no Path fails: the PlatformDeckSpec names a deck cell the blocks deny.
    internal static List<Vector3Int> DeckRegion(BlockObjectSpec spec,IEnumerable<Vector3Int> seeds,Func<Vector3Int,bool> takesPath,string label) {
      var start=seeds.Distinct().ToArray();
      var dead=start.Where(c=>!takesPath(c)).ToArray();
      if(dead.Length>0)throw new InvalidOperationException(label+" deck cells named by its PlatformDeckSpec take no native Path: "+string.Join(", ",dead));
      var region=new HashSet<Vector3Int>(start);var open=new Queue<Vector3Int>(start);
      while(open.Count>0) {
        var c=open.Dequeue();
        foreach(var s in Steps.Values) {
          var n=c+s;
          if(InBounds(spec,n)&&!region.Contains(n)&&takesPath(n)){region.Add(n);open.Enqueue(n);}
        }
      }
      return region.OrderBy(c=>c.z).ThenBy(c=>c.y).ThenBy(c=>c.x).ToList();
    }
    // A platform stack from the ground to a world cell and a Path on it.
    internal static void Pad(Place place,Vector3Int top,int groundZ) {
      for(int z=groundZ;z<top.z;z++)place("Platform.IronTeeth",new Vector3Int(top.x,top.y,z),Orientation.Cw0);
      place("Path",top,Orientation.Cw0);
    }
    // A flight of vanilla stairs from the ground to a world cell `top`, stepping away from the
    // building along `away`: a pad under `top` (a deck rail's outside cell; none when `top` is a
    // deck cell of the building), one stair per layer, each on its own platform stack, and a
    // Path at the foot. Returns the walked cells, foot to top.
    internal static List<Vector3Int> Flight(Place place,Vector3Int top,Vector3Int away,int groundZ,bool pad=true) {
      int rise=top.z-groundZ;
      if(rise<1)throw new InvalidOperationException("Stair flight to "+top+" has no rise above the ground layer "+groundZ);
      if(pad)Pad(place,top,groundZ);
      for(int k=1;k<=rise;k++) {
        var c=top+away*k;int z0=top.z-k;
        for(int z=groundZ;z<z0;z++)place("Platform.IronTeeth",new Vector3Int(c.x,c.y,z),Orientation.Cw0);
        place("Stairs.IronTeeth",new Vector3Int(c.x,c.y,z0),Toward(-away));
      }
      var foot=top+away*(rise+1);foot.z=groundZ;
      place("Path",foot,Orientation.Cw0);
      var cells=new List<Vector3Int>{foot};
      for(int k=rise;k>=1;k--) {
        var c=top+away*k;
        cells.Add(new Vector3Int(c.x,c.y,top.z-k));cells.Add(new Vector3Int(c.x,c.y,top.z-k+1));
      }
      cells.Add(top);return cells;
    }
    // A shaft line out of a wall face (local): shafts on the face's outward cell and the next one,
    // each on a platform stack when the face is above the ground, and `generators` stacked
    // DevPowerGenerators on a platform stack one cell further out. Returns the generators.
    internal static MechanicalNode[] ShaftLine(Place place,BlockObject building,(Vector3Int Cell,Vector3Int Out) face,int generators) {
      var result=new List<MechanicalNode>();
      for(int step=1;step<=3;step++) {
        var local=face.Cell+face.Out*step;
        for(int z=0;z<local.z;z++)place("Platform.IronTeeth",building.TransformCoordinates(new Vector3Int(local.x,local.y,z)),Orientation.Cw0);
        var at=building.TransformCoordinates(local);
        if(step<3){place("PowerShaft.IronTeeth",at,Orientation.Cw0);continue;}
        for(int i=0;i<generators;i++) {
          var generator=place("DevPowerGenerator",at,Orientation.Cw0);
          result.Add(generator.GetComponent<MechanicalNode>());at.z+=generator.GetComponent<BlockObjectSpec>().Size.z;
        }
      }
      return result.ToArray();
    }
    // The face whose shaft line (ShaftLine: three cells straight out) has free columns and
    // touches no reserved local cell: lowest layer first, then blueprint order.
    internal static (Vector3Int Cell,Vector3Int Out) ShaftFace(BlockObjectSpec spec,TransputProviderSpec transputs,Func<Vector3Int,bool> reserved,string label) {
      var blocks=Blocks(spec);
      var face=Faces(transputs).Select((f,i)=>(f,i))
        .Where(p=>Enumerable.Range(1,3).Select(s=>p.f.Cell+p.f.Out*s).All(c=>FreeColumn(blocks,c)
          &&Enumerable.Range(0,c.z+1).All(z=>!reserved(new Vector3Int(c.x,c.y,z)))))
        .OrderBy(p=>p.f.Cell.z).ThenBy(p=>p.i).Select(p=>p.f).ToArray();
      if(face.Length==0)throw new InvalidOperationException(label+" blueprint has no wall shaft face with three free cells outside it");
      return face[0];
    }
  }
}
