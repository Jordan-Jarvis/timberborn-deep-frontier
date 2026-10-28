using System;
using Timberborn.BaseComponentSystem;
using Timberborn.Workshops;

namespace DeepFrontier.Scripts.Narrative {
  // Decorated onto every native Manufactory. Reports each finished production
  // cycle (native ProductionFinished, raised after the products are given and
  // while CurrentRecipe is still the finished recipe) to the narrative, which
  // counts only the goods and recipes its chapters reference.
  internal sealed class NarrativeProductionReporter : BaseComponent, IAwakableComponent {
    private readonly NarrativeObjectiveService _narrative;
    private Manufactory _manufactory;

    public NarrativeProductionReporter(NarrativeObjectiveService narrative) {_narrative=narrative;}

    public void Awake() {
      _manufactory=GetComponent<Manufactory>();
      _manufactory.ProductionFinished+=OnProductionFinished;
    }

    private void OnProductionFinished(object sender,EventArgs e) {
      if(!_manufactory.HasCurrentRecipe)
        throw new InvalidOperationException("Manufactory finished production without a current recipe");
      _narrative.ReportProduction(_manufactory,_manufactory.CurrentRecipe);
    }
  }
}
