using System;
using System.Linq;
using Bindito.Core;
using Timberborn.Debugging;
using Timberborn.SingletonSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Explicit local authoring switch. Normal launches never bind this service.
  [Context("Game")]
  public sealed class ArtReviewConfigurator : Configurator {
    protected override void Configure() {
      if (Environment.GetCommandLineArgs().Contains("-deepFrontierArtReview")) {
        Bind<ArtReviewMode>().AsSingleton();
      }
    }
  }

  public sealed class ArtReviewMode : IPostLoadableSingleton {
    private readonly DevModeManager _devModeManager;

    public ArtReviewMode(DevModeManager devModeManager) {
      _devModeManager = devModeManager;
    }

    public void PostLoad() {
      _devModeManager.Enable();
      Debug.Log("[DeepFrontier] Explicit art review launch: native developer tools enabled.");
    }
  }
}
