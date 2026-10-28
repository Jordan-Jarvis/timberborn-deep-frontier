using System;

namespace DeepFrontier.Scripts.Radiation {
  // The radioactive share r of a native water column, beside the native
  // badwater share b (WaterColumn.Contamination). fresh = 1 - b - r.
  //
  // Native code that changes contamination, and the matching r rule
  // (decompiled Timberborn.WaterSystem 1.1.2.8):
  // - SimulateContaminationTask / UpdateContaminationTask (advection,
  //   diffusion): r runs through the same native kernels on a shadow column
  //   array (RadiationLockstep). The kernels do not keep b + r <= 1 in two
  //   native cases (harness: outputs/radiation-onefluid/harness): advection in a
  //   column whose retained weight (depth - received) is negative, a thin film
  //   that drained and evaporated more than it held, where the native
  //   extrapolates and clamps; and diffusion, whose per-partner min() limits
  //   differ between columns with different partner counts. KernelExcess puts
  //   the radioactive share above 1 - b into the soil.
  // - WaterParametersUpdateTask (evaporation): contamination is unchanged, so
  //   evaporated water carries its share away. Evaporated radioactive volume
  //   goes into the soil (EvaporatedVolume), so a pond that dries out leaves
  //   irradiated ground.
  // - UpdateWaterSourcesTask: (c * I + cSource * (F - I)) / F per source cell;
  //   MixSource is the same formula for r.
  // - UpdateWaterChangesTask (dumps, pumps, workshops, AddRadioactiveWater):
  //   clean and contaminated volumes, each clamped at 0, then c = bad / total;
  //   ReplayChange applies the same steps to (clean, bad, radioactive) with
  //   radioactive water as part of the clean volume.
  // - WaterSimulator geometry (split copies c, merge is depth-weighted, a raised
  //   floor or removed column deletes water): RadiationSimulation.Reconcile
  //   does the same for r and puts deleted radioactive volume into the soil.
  internal static class RadiationMixing {
    public static void RequireShares(float bad, float radioactive, string where) {
      if (!(radioactive >= 0f) || !(bad >= 0f) || bad + radioactive > 1f + RadiationTuning.ShareTolerance)
        throw new InvalidOperationException($"Radiation share invariant broken in {where}: bad {bad} + radioactive {radioactive} must be within 0..1");
    }

    // After the kernels: returns the corrected share and the radioactive share
    // moved to the soil (0 unless one of the two native cases pushed b + r over 1).
    public static float KernelExcess(float bad, float radioactive, out float excess) {
      excess = bad + radioactive - 1f;
      if (excess > RadiationTuning.ShareTolerance) return 1f - bad;
      excess = 0f;
      return radioactive;
    }

    // Native evaporation of one substep: speed by depth, times the column's
    // evaporation modifier, never more than the water there was.
    public static float EvaporatedVolume(float depth, float overflow, float modifier, float deltaTime,
        float fastDepthThreshold, float fastSpeed, float normalSpeed) {
      float speed = depth < fastDepthThreshold ? fastSpeed : normalSpeed;
      float evaporated = speed * modifier * deltaTime;
      float available = depth + overflow;
      return evaporated < available ? evaporated : available;
    }

    // before / after: effective depths (WaterDepth + Overflow * pressure factor)
    // around the native source step; addedRadioactive: radioactive part of the
    // water the sources added.
    public static float MixSource(float radioactive, float before, float after, float addedRadioactive) =>
      after != 0f ? (radioactive * before + addedRadioactive) / after : 0f;

    // One native water change on volumes clean (= fresh + radioactive), bad and
    // radioactive. radioactiveShare: share of added clean water that is
    // radioactive (1 for AddRadioactiveWater, 0 otherwise). Removed clean water
    // leaves at the clean water's own mix. Returns the radioactive volume removed.
    public static float ReplayChange(ref float clean, ref float bad, ref float radioactive,
        float depthChange, float contaminationChange, float radioactiveShare) {
      float cleanChange = depthChange * (1f - contaminationChange);
      float removed = 0f;
      if (cleanChange >= 0f) {
        clean += cleanChange;
        radioactive += cleanChange * radioactiveShare;
      } else {
        float taken = -cleanChange < clean ? -cleanChange : clean;
        removed = clean > 0f ? radioactive * (taken / clean) : 0f;   // never more than radioactive
        radioactive -= removed;
        clean -= taken;
      }
      bad += depthChange * contaminationChange;
      if (bad < 0f) bad = 0f;
      return removed;
    }
  }
}
