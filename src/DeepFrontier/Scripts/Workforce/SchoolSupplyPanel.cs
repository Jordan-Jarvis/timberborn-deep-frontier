#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using HarmonyLib;
using Timberborn.BaseComponentSystem;
using Timberborn.CoreUI;
using Timberborn.EntityPanelSystem;
using Timberborn.GoodConsumingBuildingSystem;
using Timberborn.GoodConsumingBuildingSystemUI;
using Timberborn.InventorySystemUI;
using Timberborn.ModManagerScene;
using UnityEngine;
using UnityEngine.UIElements;

namespace DeepFrontier.Scripts {
  // Why Harmony (Timberborn 1.1.2.8): a Technical School's supplies are those
  // of the profession it teaches (SpecialistSchool), but its one native
  // inventory must allow every profession's goods. Two native views read that
  // inventory or the template spec directly and have no per-entity filter:
  // - GoodConsumingBuildingFragment builds its InventoryFragment with
  //   ShowEmptyRows, so every allowed good gets a row ("0 / 0" for the goods
  //   the school refuses) and, with nothing taught, the hours-left bar reads
  //   float.MaxValue. The postfix applies the native workshop rule
  //   (InventoryRowUpdater.ShouldShow: allowed amount > 0 or in stock), so the
  //   taught profession's goods and leftovers being carried out are shown, and
  //   hides the whole supply fragment while nothing is taught.
  // - GoodConsumingBuildingDescriber lists the consumed goods in the tooltip of
  //   the unbuilt (preview) and unfinished building. A preview never runs
  //   InitializeEntity, so it would list every profession's goods. The postfix
  //   drops that input section while the school teaches nothing; once a
  //   profession is chosen the native section lists its supplies.
  // Both postfixes return at once for every entity without a SpecialistSchool.
  // Verify() resolves every member first and throws if the game changed them.
  internal sealed class SchoolSupplyPanelModStarter : IModStarter {
    public void StartMod(IModEnvironment modEnvironment) {
      SchoolSupplyPanel.Verify();
      var harmony = new Harmony(SchoolSupplyPanel.HarmonyId);
      harmony.CreateClassProcessor(typeof(SchoolSupplyFragmentPatch)).Patch();
      harmony.CreateClassProcessor(typeof(SchoolSupplyDescriberPatch)).Patch();
      Debug.Log("[DeepFrontier] Technical School supply panel patches applied (GoodConsumingBuildingFragment.UpdateFragment, GoodConsumingBuildingDescriber.DescribeEntity).");
    }
  }

  internal static class SchoolSupplyPanel {
    internal const string HarmonyId = "DeepFrontier.SchoolSupplyPanel";
    private const string DescriberTypeName = "Timberborn.GoodConsumingBuildingSystemUI.GoodConsumingBuildingDescriber";
    internal static AccessTools.FieldRef<InventoryFragment, List<InformationalRow>> Rows;

    internal static void Verify() {
      var update = AccessTools.Method(typeof(GoodConsumingBuildingFragment), nameof(GoodConsumingBuildingFragment.UpdateFragment), Type.EmptyTypes);
      Require(update != null && update.ReturnType == typeof(void), "GoodConsumingBuildingFragment.UpdateFragment() : void");
      RequireField(typeof(GoodConsumingBuildingFragment), "_goodConsumingBuilding", typeof(GoodConsumingBuilding));
      RequireField(typeof(GoodConsumingBuildingFragment), "_root", typeof(VisualElement));
      RequireField(typeof(GoodConsumingBuildingFragment), "_inventoryFragment", typeof(InventoryFragment));
      RequireField(typeof(InventoryFragment), "_rows", typeof(List<InformationalRow>));
      Rows = AccessTools.FieldRefAccess<InventoryFragment, List<InformationalRow>>("_rows");
      Require(DescribeEntity() != null, DescriberTypeName + ".DescribeEntity() : IEnumerable<EntityDescription>");
    }

    internal static MethodInfo DescribeEntity() {
      var type = AccessTools.TypeByName(DescriberTypeName);
      var method = type == null ? null : AccessTools.Method(type, "DescribeEntity", Type.EmptyTypes);
      return method != null && method.ReturnType == typeof(IEnumerable<EntityDescription>) && typeof(BaseComponent).IsAssignableFrom(type) ? method : null;
    }

    private static void RequireField(Type type, string name, Type fieldType) =>
      Require(AccessTools.Field(type, name)?.FieldType == fieldType, $"{type.Name}.{name} : {fieldType.Name}");

    private static void Require(bool condition, string member) {
      if (!condition) throw new InvalidOperationException("Timberborn 1.1.2.8 contract changed: " + member);
    }
  }

  [HarmonyPatch(typeof(GoodConsumingBuildingFragment), nameof(GoodConsumingBuildingFragment.UpdateFragment))]
  internal static class SchoolSupplyFragmentPatch {
    private static void Postfix(GoodConsumingBuilding ____goodConsumingBuilding, VisualElement ____root, InventoryFragment ____inventoryFragment) {
      if (!____goodConsumingBuilding || !____goodConsumingBuilding.Enabled) return;
      var school = ____goodConsumingBuilding.GetComponent<SpecialistSchool>();
      if (!school) return;
      if (school.Discipline == null) {
        ____root.ToggleDisplayStyle(visible: false);
        return;
      }
      var inventory = ____goodConsumingBuilding.Inventory;
      foreach (var row in SchoolSupplyPanel.Rows(____inventoryFragment))
        if (inventory.LimitedAmount(row.GoodId) <= 0 && inventory.AmountInStock(row.GoodId) <= 0) row.Hide();
    }
  }

  [HarmonyPatch]
  internal static class SchoolSupplyDescriberPatch {
    private static MethodBase TargetMethod() => SchoolSupplyPanel.DescribeEntity();

    private static void Postfix(BaseComponent __instance, ref IEnumerable<EntityDescription> __result) {
      var school = __instance.GetComponent<SpecialistSchool>();
      if (school && school.Discipline == null) __result = __result.Where(description => !description.Input).ToList();
    }
  }
}
#endif
