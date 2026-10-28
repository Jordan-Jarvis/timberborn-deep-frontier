using System;
using System.Linq;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockSystem;
using Timberborn.Buildings;
using Timberborn.Common;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Shows the stacked rocket on the pad during preparation and flies it on
  // liftoff: the authored rocket node rises (eased) with the exhaust node
  // lit; a failing rocket disappears at the spec's failure point. Both nodes
  // are un-animated children of the finished Timbermesh model, so the native
  // workshop animator (arms, elevator, beacons) never writes them.
  internal sealed class RocketLaunchVisual : BaseComponent, IAwakableComponent, IUpdatableComponent,
      IFinishedStateListener {
    private RocketLaunchVisualSpec _spec;
    private RocketLaunchPad _pad;
    private Transform _rocket,_exhaust;
    private Vector3 _rocketBase;
    private bool _finished;

    public bool RocketVisible=>_rocket.gameObject.activeSelf;
    public bool ExhaustVisible=>_exhaust.gameObject.activeSelf;
    public float RocketHeight=>_rocket.localPosition.y-_rocketBase.y;

    public void Awake() {
      _spec=GetComponent<RocketLaunchVisualSpec>();_pad=GetComponent<RocketLaunchPad>();
      if(!_pad||!(_spec.AscentHeight>0f))throw new InvalidOperationException("Rocket visual requires the Launch Pad program and a positive ascent height");
      // Search only the finished model: #Unfinished/ConstructionStage0 is an
      // exported copy of the same mesh and repeats every node name.
      var finished=GameObject.FindChildIfNameNotEmpty(GetComponent<BuildingModelSpec>().FinishedModelName);
      if(!finished)throw new InvalidOperationException("Launch Pad has no finished model");
      var transforms=finished.GetComponentsInChildren<Transform>(true);
      Transform Node(string name) {
        var matches=transforms.Where(t=>t.name==name).ToArray();
        if(matches.Length!=1)throw new InvalidOperationException($"Launch Pad model must contain exactly one '{name}' node; found {matches.Length}");
        return matches[0];
      }
      _rocket=Node(_spec.RocketNode);_exhaust=Node(_spec.ExhaustNode);
      if(_exhaust==_rocket||!_exhaust.IsChildOf(_rocket))
        throw new InvalidOperationException("The exhaust node must be a child of the rocket node so it rises with it");
      _rocketBase=_rocket.localPosition;
      Show(false,false,0f);
    }
    public void OnEnterFinishedState() {_finished=true;}
    public void OnExitFinishedState() {_finished=false;Show(false,false,0f);}

    public void Update() {
      if(!_finished)return;
      if(_pad.InFlight) {
        var p=Mathf.Clamp01(_pad.FlightProgress);
        var lost=_pad.FlightFails&&p>=_pad.Spec.FailurePointFraction;
        Show(!lost,!lost,_spec.AscentHeight*p*p);
      } else Show(_pad.RocketStacked,false,0f);
    }

    private void Show(bool rocket,bool exhaust,float height) {
      if(_rocket.gameObject.activeSelf!=rocket)_rocket.gameObject.SetActive(rocket);
      if(_exhaust.gameObject.activeSelf!=exhaust)_exhaust.gameObject.SetActive(exhaust);
      // World up, whatever rotation/scale the exported hierarchy carries.
      _rocket.localPosition=_rocketBase+_rocket.parent.InverseTransformVector(Vector3.up*height);
    }
  }
}
