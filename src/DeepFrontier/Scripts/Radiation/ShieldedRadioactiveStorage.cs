using System;
using System.Collections.Generic;
using System.Linq;
using Timberborn.BlueprintSystem;
using Timberborn.Goods;

namespace DeepFrontier.Scripts.Radiation {
  // A sealed vault can hold recovered radioactive liquid in shielded vessels.
  // Keep the good's Liquid type: factories and Timber Pipes use that contract.
  internal record ShieldedRadioactiveStorageSpec : ComponentSpec { }

  internal static class ShieldedRadioactiveStorage {
    internal static void Configure(List<StorableGoodAmount> goods, bool shielded, int capacity) {
      if (capacity <= 0) throw new ArgumentOutOfRangeException(nameof(capacity));
      string id = RadiationTuning.SludgeGoodId;
      int index = goods.FindIndex(g => g.StorableGood.GoodId == id);
      if (shielded) {
        var amount = new StorableGoodAmount(StorableGood.CreateGiveableAndTakeable(id), capacity);
        if (index < 0) goods.Add(amount);
        else goods[index] = amount;
      } else if (index >= 0) {
        // Output-only, zero incoming capacity. Existing saved stock must remain
        // withdrawable, never deleted when the storage rule changes. Native
        // unwanted-stock hauling moves it out and native deletion stays blocked.
        goods[index] = new StorableGoodAmount(StorableGood.CreateAsTakeable(id), 0);
      }
      if (goods.Count(g => g.StorableGood.GoodId == id) > 1)
        throw new InvalidOperationException("Duplicate radioactive-water storage entry");
    }
  }
}
