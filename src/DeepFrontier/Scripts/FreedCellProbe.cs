using System;
using System.Collections.Generic;
using System.Linq;
using Timberborn.BlockSystem;
using Timberborn.Coordinates;
using Timberborn.TemplateSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Ground freed by the 2026-10-22 no-forced-decoration footprint pass must take the
  // player's own Path or a 1x1 decoration (sources: tools/asset-pipeline/validate_freed_cells.py,
  // tools/validate_freed_cells.mjs and tools/lategame_freed_cells.json). Acceptance drivers
  // ask the native BlockValidator, without placing anything, whether a vanilla Path and a
  // vanilla 1x1 decoration fit on each freed cell beside the building they just placed:
  // Shrub.IronTeeth (two layers, the static validators' probe) or, where the building
  // overhangs the second layer, Brazier.IronTeeth (one layer).
  internal static class FreedCellProbe {
    private static readonly string[] Decorations={"Shrub.IronTeeth","Brazier.IronTeeth"};
    // Returns one failure line per rejected cell; empty when every cell accepts both.
    public static List<string> Check(TemplateService templates,BlockValidator validator,BlockObject building,
      IEnumerable<Vector3Int> localCells,out string accepted) {
      var path=Spec(templates,"Path");
      var decorations=Decorations.Select(id=>(Id:id,Spec:Spec(templates,id))).ToArray();
      var failures=new List<string>();var used=new List<string>();
      foreach(var local in localCells) {
        var world=building.TransformCoordinates(local);
        var placement=new Placement(world,Orientation.Cw0,FlipMode.Unflipped);
        bool pathFits=validator.BlocksValid(path,placement);
        var decoration=decorations.FirstOrDefault(d=>validator.BlocksValid(d.Spec,placement)).Id;
        if(!pathFits||decoration==null)
          failures.Add("local "+local+" world "+world+": Path "+(pathFits?"fits":"rejected")+", 1x1 decoration "+(decoration??"rejected"));
        else used.Add(local+" "+decoration.Split('.')[0]);
      }
      accepted=string.Join(", ",used);
      return failures;
    }
    // Throwing form for drivers that stop at the first failed check.
    public static void Require(TemplateService templates,BlockValidator validator,BlockObject building,
      IEnumerable<Vector3Int> localCells,string label,Action<string> pass) {
      var cells=localCells.ToArray();
      if(cells.Length==0)throw new InvalidOperationException(label+": no freed cells listed");
      var failures=Check(templates,validator,building,cells,out var accepted);
      if(failures.Count>0)throw new InvalidOperationException(label+": freed cells reject native placement: "+string.Join("; ",failures));
      pass(label+": "+cells.Length+" freed cells accept a native Path and a 1x1 decoration ("+accepted+")");
    }
    // Every cell of a rectangle of local cells (inclusive bounds) at one layer.
    public static IEnumerable<Vector3Int> Rect(int xMin,int xMax,int yMin,int yMax,int z=0) {
      for(int y=yMin;y<=yMax;y++)for(int x=xMin;x<=xMax;x++)yield return new Vector3Int(x,y,z);
    }
    // The former footprint (inclusive bounds, in the new local frame) minus the new bounds:
    // ground the building no longer covers at all.
    public static IEnumerable<Vector3Int> Outside(int xMin,int xMax,int yMin,int yMax,Vector3Int size)=>
      Rect(xMin,xMax,yMin,yMax).Where(c=>c.x<0||c.y<0||c.x>=size.x||c.y>=size.y);
    private static BlockObjectSpec Spec(TemplateService templates,string id) {
      var template=templates.GetAll<TemplateSpec>().SingleOrDefault(t=>t.TemplateName==id);
      if(template==null)throw new InvalidOperationException("Freed-cell probe template not loaded: "+id);
      return templates.GetAll<BlockObjectSpec>().Single(s=>s.Blueprint==template.Blueprint);
    }
  }
}
