#if !UNITY_EDITOR
using System.Linq;
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.Buildings;
using Timberborn.EnterableSystem;
using Timberborn.EntityPanelSystem;
using Timberborn.GoodConsumingBuildingSystem;
using Timberborn.Goods;
using Timberborn.Localization;
using TimberUi.CommonUi;
using UnityEngine.UIElements;

namespace DeepFrontier.Scripts {
  // Localization rows: tools/hospital_building_content.mjs (HOSPITAL_LOCALIZATION).
  internal static class HospitalPanelLoc {
    public const string Title = "DeepFrontier.Hospital.Panel.Title";
    public const string Patients = "DeepFrontier.Hospital.Panel.Patients";
    public const string Crew = "DeepFrontier.Hospital.Panel.Crew";
    public const string Meals = "DeepFrontier.Hospital.Panel.Meals";
    public const string Fed = "DeepFrontier.Hospital.Panel.Fed";
    public const string UnderConstruction = "DeepFrontier.Hospital.Panel.UnderConstruction";
    public const string Paused = "DeepFrontier.Hospital.Panel.Paused";
    public const string NoPower = "DeepFrontier.Hospital.Panel.NoPower";
    public const string NoCrew = "DeepFrontier.Hospital.Panel.NoCrew";
    public const string NoMeals = "DeepFrontier.Hospital.Panel.NoMeals";
    public const string NoSupplies = "DeepFrontier.Hospital.Panel.NoSupplies";
    public const string Treating = "DeepFrontier.Hospital.Panel.Treating";
    public const string AreaActive = "DeepFrontier.Hospital.Panel.AreaActive";
    public const string AreaInactive = "DeepFrontier.Hospital.Panel.AreaInactive";
  }

  internal sealed class HospitalPanel : BaseEntityPanelFragment<Hospital> {
    private readonly ILoc _loc;
    private readonly IGoodService _goods;
    private Label _patients,_staff,_meals,_fed,_care,_area;
    public HospitalPanel(ILoc loc,IGoodService goods) {_loc=loc;_goods=goods;}
    protected override void InitializePanel() {
      panel.AddGameLabel(_loc.T(HospitalPanelLoc.Title),bold:true);
      _patients=panel.AddGameLabel();_staff=panel.AddGameLabel();
      _meals=panel.AddGameLabel();_meals.style.whiteSpace=WhiteSpace.Normal;
      _fed=panel.AddGameLabel();
      _care=panel.AddGameLabel();_care.style.whiteSpace=WhiteSpace.Normal;
      _area=panel.AddGameLabel();
    }
    public override void ShowFragment(BaseComponent entity) {base.ShowFragment(entity);UpdateFragment();}
    public override void UpdateFragment() {
      if(!component)return;
      var ward=component.GetComponent<Enterable>();var pantry=component.Pantry;
      _patients.text=_loc.T(HospitalPanelLoc.Patients,ward.NumberOfEnterersInside,ward.Capacity);
      _staff.text=_loc.T(HospitalPanelLoc.Crew,component.CrewAssigned,component.GetComponent<HospitalSpec>().RequiredStaff,component.AttendingStaff);
      var stock=string.Join(", ",pantry.Foods.Select(id=>(id,amount:pantry.Inventory.AmountInStock(id))).Where(g=>g.amount>0)
        .Select(g=>$"{g.amount} {_goods.GetGood(g.id).PluralDisplayName.Value}"));
      _meals.text=_loc.T(HospitalPanelLoc.Meals,pantry.FoodInStock,pantry.WaterInStock,stock.Length>0?stock:"-");
      _fed.text=_loc.T(HospitalPanelLoc.Fed,pantry.PatientsFed,pantry.Patients);
      if(!component.Enabled)_care.text=_loc.T(HospitalPanelLoc.UnderConstruction);
      else if(component.GetComponent<PausableBuilding>().Paused)_care.text=_loc.T(HospitalPanelLoc.Paused);
      else if(!component.IsOperating)_care.text=_loc.T(HospitalPanelLoc.NoPower);
      else if(component.CrewAssigned==0)_care.text=_loc.T(HospitalPanelLoc.NoCrew);
      else if(pantry.MealsShort)_care.text=_loc.T(HospitalPanelLoc.NoMeals);
      else if(!component.GetComponent<GoodConsumingBuilding>().CanUse)_care.text=_loc.T(HospitalPanelLoc.NoSupplies);
      else _care.text=_loc.T(HospitalPanelLoc.Treating,(component.Efficiency*100).ToString("0"));
      _area.text=_loc.T(component.ProvidesNeighborhoodCare?HospitalPanelLoc.AreaActive:HospitalPanelLoc.AreaInactive);
    }
  }
  [Context("Game")]
  public sealed class HospitalPanelConfigurator : Configurator {
    protected override void Configure() {this.BindFragment<HospitalPanel>();}
  }
}
#endif
