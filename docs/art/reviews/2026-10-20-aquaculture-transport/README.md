# Aquaculture water connections

The accepted Fishery and Hatchery meshes remain the active reference-derived models. This integration uses Timber Pipes 11.4.0 and their existing native recipe inventories. It adds no second water store.

The Fishery's rear tank intake is local cell (5,9,0), facing Up. The Hatchery's pump canopy intake is (7,2,1), facing Right; its grid registration includes BaseZ=1. Both faces accept input only. The canonical definitions are in `tools/aquaculture_pipe_ports.json`.

Each marked test line uses a native Medium Tank, a 50 hp horizontal pipe pump, a straight pipe and a valve. The test checks actual delivery, rejection of Badwater and unlisted faces, the 90/60-unit factory limits, valve closure/reopening, and water conservation across tank, pipes and inventory. Visible reservoir surfaces must follow the same stock; paused production must stop circulation.

Native attempt 75 placed the Fishery line, then correctly rejected the Hatchery valve because its position was still inside the original hillside. The earlier disposable test pad ended at x=194. Build 76 extends only the marked fixture's pad through the native terrain service before placing that line. No building placement rule or architecture was changed for the test.

Physical acceptance 76 passed both lines, incorrect-face/Badwater rejection, the 90/60-unit limits, valve closure/reopening, conserved water and matching reservoir surfaces. The preserved native save is `outputs/aquaculture-pipes-build76.timber`, SHA256 `d6ed16c1159f84f191193191cb0a36fdd99edcfe7ae2396a0c3173d79d56b64b`. Each line retains 290 Water-equivalent units, including three full pipe cells.

Fresh-process continuation 76 passed exact workshop/tank identities and stocks, signed fractional tank volume, every pipe's saved volume/good and valve settings. Both lines passed another valve interruption and refill. Five native workers then completed two Fishery batches and one Hatchery batch. The observed recipe debits were three Water and two Water respectively: the Fishery's first batch already had prepaid progress in the original save. Flow was observed on both buildings and the native Fishery wheel advanced during production.

The final native save is `outputs/aquaculture-pipe-continuity-build76.timber`, SHA256 `b9f7be74f9ff2faa5c0c0c875be5a1d4403db327cb165f725039ee34e50e678f`. Final buffers are 90/60 Water. After two explicit ten-unit fixture withdrawals per line and actual recipe consumption, total saved Water-equivalent is 267.00056839/268.000091555. These agree with 290−20−3 / 290−20−2 within the 0.02 floating-point tolerance. Evidence: `outputs/aquaculture-pipes-reload76.log`, `outputs/aquaculture-pipe-continuity76.json`.

The automatically captured main-test overview is at night. A daylight installed view and the native Fishery panel were subsequently inspected and archived as [waterfront-installed-build76.jpg](waterfront-installed-build76.jpg) and [fishery-stock-after-pipes-build76.jpg](fishery-stock-after-pipes-build76.jpg). The panel shows the saved 90/90 Water and eight FreshFish after production. Rear pipe connections are obscured from this camera angle; their physical behavior is established by the runtime checks above.
