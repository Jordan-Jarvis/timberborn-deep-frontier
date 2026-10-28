using System.Collections.Generic;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockSystem;
using Timberborn.CoreUI;
using Timberborn.EntityPanelSystem;
using Timberborn.Localization;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Panel line on every enterable building (homes, workplaces) standing in
  // smog: the footprint average SmogExposure uses for beavers inside, the
  // wellbeing it costs them and how much trees and scrubbers already remove.
  internal sealed class SmogBuildingDescriber : BaseComponent, IAwakableComponent, IEntityDescriber {
    private readonly SmogService _smog;
    private readonly ILoc _loc;
    private BlockObject _blockObject;

    public SmogBuildingDescriber(SmogService smog,ILoc loc) {_smog=smog;_loc=loc;}

    public void Awake() {_blockObject=GetComponent<BlockObject>();}

    public IEnumerable<EntityDescription> DescribeEntity() {
      if(!_blockObject.IsFinished)yield break;
      float intensity=_smog.BuildingIntensity(_blockObject);
      if(!_smog.IsLight(intensity))yield break;
      var (_,green,scrub)=_smog.BuildingBreakdown(_blockObject);
      string text=_loc.T("DeepFrontier.Smog.Building",Mathf.RoundToInt(intensity*100f),_smog.WellbeingPenalty(intensity),_smog.MaxPenalty);
      if(green>0f||scrub>0f)text+="\n"+SpecialStrings.RowStarter+_loc.T("DeepFrontier.Smog.Building.Mitigated",
        Mathf.RoundToInt(green*100f),Mathf.RoundToInt(scrub*100f));
      yield return EntityDescription.CreateTextSection(SpecialStrings.RowStarter+text,1040);
    }
  }
}
