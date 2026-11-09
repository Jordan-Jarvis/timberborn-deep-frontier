# Multi fluid transport prototype

Implemented 2026-11-06 as the first stage of the [Moddable Fluids plan](fluids-api-plan.md). The prototype now includes a [native buffer and stage adapter](fluids-native-adapter.md), tested against installed game tasks and in an isolated host using the game's Mono runtime. It is not yet a packaged mod or an in-game replacement for Deep Frontier's water simulation.

## Implementation

The source is in [FluidTransportPrototype.cs](../src/ModdableFluids/Transport/FluidTransportPrototype.cs) and [FluidVolumes.cs](../src/ModdableFluids/Transport/FluidVolumes.cs). The calculation targets netstandard2.1 without game, Unity, or third-party assembly dependencies. Its namespace is explicitly experimental: `ModdableFluids.Transport.Prototype`. A complete registry and published API stability contract follow the transport prototype.

Each column contains an immutable vector of nonnegative component volumes, including fresh water and badwater. The vector's sum defines its physical volume. All transfers use the same starting snapshot. Off-map discharge and evaporation return component quantities alongside the resulting columns. Additions and native clean/non-bad versus badwater removals are separate measured operations.

The prototype accepts arbitrary component counts rather than a list of named fluids. The harness exercises up to 64 components. Those counts are correctness fixtures, not measured performance limits. Registration IDs, persistence, rendering, source ownership, and live scheduling are later integration work.

## Transfer calculation

For column i, let V_i be the sum of its component volumes and O_i the sum of all outgoing transfer volumes. A batch requires 0 <= O_i <= V_i before producing a result. Transfers from a dry donor cannot borrow incoming water from the same step. The native hydraulic task budgets flows from the old snapshot too.

For component c, retain its old volume multiplied by `(V_i - O_i) / V_i`. Each outgoing edge of volume Q carries the donor's old component volume multiplied by `Q / V_i`. Add those measured quantities at destinations, or to the discharge ledger for an off-map edge. A dry column contributes zero.

Calculate the retained volume directly. Subtracting a sequence of almost equal removed quantities can destroy the small positive remainder, which caused Deep Frontier's earlier near-empty pumping crash. Native selective removals use the same calculation separately for the non-bad cohort and badwater. A request beyond the available amount removes only the available cohort and reports what was removed.

Evaporation runs on the resulting mixture, limited by the water present after flow. It returns the removed component quantities. This avoids using a negative retained-water weight when evaporation and outflow nearly empty a column. Radioactive deposition, decay, cutoff, and other fluid-specific transformations remain consumer responsibilities.

The calculation never repairs a mixture by normalizing its shares or inventing a destination for excess fluid. Negative, nonfinite, mismatched, and overdrawn inputs fail. The two historical radiation traces that already contain more radioactive volume than non-bad water are rejected when constructing their component vector.

## Diffusion calculation

Use one symmetric exchange per eligible unordered pair. Let a and b be the two physical volumes, d_a and d_b their eligible neighbor counts, and alpha the diffusion rate multiplied by timestep. The exchanged volume in each direction is:

```text
exchange = alpha * a * b / ((a + b) * max(d_a, d_b))
```

Require 0 <= alpha <= 1; larger steps need explicit subdivision. Each pair uses the same exchange volume in both directions. Since each exchange is at most `alpha * a / d_a` for donor a, the sum of its exports fits its volume. The symmetric exchange preserves every component globally and total volume locally, including when neighbor counts differ. Zero-volume pairs exchange nothing; duplicate pairs fail visibly.

This is an intentional diffusion-model change from the native independent concentration calculation. The harness uses native-computed eligible pairs for its comparison; the live integration must retain native obstacle and flow-limit eligibility too.

## Native contracts checked

[NativeWaterFixture.cs](../tools/compile-check/fluid-transport-harness/NativeWaterFixture.cs) invokes the actual installed `Timberborn.WaterSystem.dll` using reflection. No decompiled implementation is copied into the prototype or the harness. Simulation coefficients come from the official authoring project's imported `WaterSimulator.blueprint.json`; the report hashes both the installed assembly and that fixture specification. Fixtures use a 3 by 3 map with the native one-cell border, a deliberately chosen 0.25-second substep, and maximum pressure 16. They do not reproduce the production game's complete tick configuration.

| Native type or member | Result and implication |
| --- | --- |
| `OutflowsUpdateTask.Run` | The generated raw `WaterFlow` and `DirectedFlow` rates can drive the joint calculation. The harness includes an actual generated-flow case as well as prescribed flow fixtures. |
| `WaterParametersUpdateTask.ProcessWaterDepthChanges` | Stored depth changes use raw base-level and directed transfers, followed by evaporation. Capture these inputs before the buffers are reused. |
| `ColumnOutflows` | The resulting directional summary applies `OutflowBalancingScaler`. Its net can differ from the net used to change depth. It must not substitute for the raw transfer inputs in a conservation calculation. |
| `WaterDepthSetter.SetWaterDepth` | Stored volume is `WaterDepth + Overflow`. Pressure expressions such as `WaterDepth + Overflow * OverflowPressureFactor` are not interchangeable with that volume. Native depth clamping or overflow-cap losses require explicit handling in the future adapter. |
| `SimulateContaminationTask` and `UpdateContaminationTask` | Independent component passes reproduce excess total shares in thin-film and unequal-degree cases. |
| `UpdateWaterSourcesTask.Run` | A fixture source implemented through a reflected native interface adds the expected physical volume. Source badwater composition agrees in the unpressurized control, including a zero-strength source. |
| `UpdateWaterChangesTask.Run` | Unpressurized additions and selective non-bad/bad removals agree on total volume and badwater share. Extra-fluid removals remain proportional within the non-bad cohort. |

The multiple-column fixture keeps lower and upper reservoirs separate at the same map cell and includes physical overflow storage. The source/change controls do not establish equivalence for pressurized inventory conversions.

## Results and behavior differences

The initial transport pass completed 219,939 assertions across 16 scenarios. With the native adapter and the 2026-11-07 source corrections from Deep Frontier, the .NET 8 harness passes 397,175 assertions across 31 scenarios, plus 138 checks in the installed-Mono probe including actual scheduling hooks. Release builds have zero warnings or errors. Evidence is written to `outputs/fluids-api-prototype/transport-report.json` and `mono-report.json`. The [adapter document](fluids-native-adapter.md) describes signed source withdrawals, ordered admission and pressure rejection.

The full repository suite, including Blender source checks, passes 80 checks plus the item-use report. Its remaining Git-only asset guard fails in the scratch mirror because that mirror has no Git metadata, and passes separately in the real checkout. The full log is `outputs/fluids-api-prototype/full-validation.log`.

| Comparison | Independent native concentration passes | Joint transport |
| --- | --- | --- |
| Thin film receiving a mixture while evaporation removes most water | Bad plus radioactive share about 1.80 | Bad plus radioactive share 0.60; all shares total one; evaporation accounts for removed components |
| Center with three diffusion neighbors, each with only one neighbor | Center bad plus radioactive share about 1.05625 | Center bad plus radioactive share one; each component is conserved |
| Opposing raw transfers of 0.25 and 0.125 physical units | Final summary net about 0.15, while depth changes use net 0.125 | Uses the raw transfers, matching net depth change 0.125 |
| Simple one-way flow without evaporation or diffusion | Native component fractions | Matches within float-comparison tolerance |

Joint badwater transport will intentionally differ from native contamination in the reproduced cases, in opposing gross-flow mixing, and potentially in pressure-weighted or evaporation-weighted mixing. Preserving the native badwater concentration byte-for-byte while independently conserving every exclusive component is not established by this prototype. Resolve the live adapter's authority over badwater before migrating existing saves; never conceal a difference by discarding extra fluid or scaling its shares.

## Verification and reproduction

Run the test in the persistent scratch mirror, following the repository instructions:

```powershell
$dev = Get-Content tools/dev-environment.json -Raw | ConvertFrom-Json
& $dev.pwsh -NoProfile -File tools/scratch_mirror.ps1 -Name fluids-api
& $dev.pwsh -NoProfile -File (Join-Path $env:USERPROFILE 'dfs/fluids-api/tools/test_fluid_transport.ps1')
```

The same test is registered as `fluid-transport` in `tools/validate_all.ps1`. [Program.cs](../tools/compile-check/fluid-transport-harness/Program.cs) covers simultaneous branches, discharge, evaporation, source additions, selective pumping, near-empty arithmetic, explicit split/merge/loss remaps, diffusion at unequal degrees and depths, 16-component randomized transport, component ordering, invalid requests, and reflected construction/invocation. Native fixtures cover generated flows, both concentration regressions, pressure storage, upper reservoirs, sources, and water-change tasks.

These are standalone tests against installed managed game code, including the separate installed-Mono probe. The adapter tests also execute actual queued native obstacle edits in the native load phase. Live worker scheduling, automatic game lifecycle delivery, world creation, production-map performance, and save/reload remain unverified. No game process, installed mod, or player save is changed by the tests.

## Next integration work

1. Register a scene-bound owner for the tested scheduler bridge and verify production worker barriers, refreshing native array references after resizing.
2. Bind source/addition resolver callbacks and completed native change results to the registry and public provider contracts.
3. Verify automatic geometry delivery, full-tick completion, scene changes, and world creation in a disposable settlement. Installed-Mono standalone access is already covered.
4. Build the standalone registry, rendering, and persistence package, then migrate Deep Frontier with the documented physical-volume and badwater behavior changes.
