#if !UNITY_EDITOR
using System.Linq;
using Bindito.Core;
using DeepFrontier.Scripts.Radiation;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockSystem;
using Timberborn.Localization;
using Timberborn.WaterBuildings;
using TimberUi.CommonUi;
using UnityEngine;
using UnityEngine.UIElements;

namespace DeepFrontier.Scripts.Sensors {
  // Radiation readout for the native Stream Gauge (Timberborn 1.1.2.8,
  // Timberborn.WaterBuildings.StreamGauge). The gauge is a display only: it
  // is not an automation transmitter and compares nothing against a
  // threshold, so it gets no "Measures" choice. Its native panel
  // (StreamGaugeFragment) shows Depth, Greatest depth, Current and
  // "Contamination", the badwater share StreamGauge.ContaminationLevel; this
  // fragment adds the radioactive share of the same column, from the same
  // cell (native StreamGauge.SetCoordinates: the first occupied block) and
  // under the same condition (water above the gauge's base, StreamGauge
  // .WaterLevel > 0; native resets the readings to 0 otherwise). Radiation is
  // read only through IRadiationService; below the 0.5% cutoff it reads 0.
  internal sealed class StreamGaugeRadiationPanel : BaseEntityPanelFragment<StreamGauge> {
    private readonly ILoc _loc;
    private readonly IRadiationService _radiation;
    private Label _reading;

    public StreamGaugeRadiationPanel(ILoc loc, IRadiationService radiation) {
      _loc = loc;
      _radiation = radiation;
    }

    protected override void InitializePanel() {
      _reading = panel.AddGameLabel();
    }

    public override void ShowFragment(BaseComponent entity) {
      base.ShowFragment(entity);
      UpdateFragment();
    }

    // Shown while the native gauge fragment is (StreamGaugeFragment: the gauge component enabled).
    public override void UpdateFragment() {
      if (!component) return;
      panel.Visible = component.Enabled;
      if (!component.Enabled) return;
      _reading.text = string.Format(_loc.T(ContaminationSensorLoc.RadiationReading), Percent(RadioactiveShare(component)));
    }

    private float RadioactiveShare(StreamGauge gauge) {
      if (!(gauge.WaterLevel > 0f)) return 0f;
      Vector3Int cell = gauge.GetComponent<BlockObject>().PositionedBlocks.GetOccupiedCoordinates().First();
      return _radiation.Sample(cell).WaterRadiation;
    }

    // As the Contamination Sensor readout: finer than whole percent, because
    // pumps refuse radioactive water from 0.5% (RadiationTuning.DetectionLimit).
    private static string Percent(float share) => (share * 100f).ToString("0.##");
  }

  [Context("Game")]
  public sealed class StreamGaugeRadiationPanelConfigurator : Configurator {
    protected override void Configure() {
      this.BindFragment<StreamGaugeRadiationPanel>();
    }
  }
}
#endif
