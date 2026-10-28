"""Preserve a completed native turbine acceptance save without rewriting it."""
import argparse
import hashlib
import json
import math
import shutil
import zipfile
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--build", type=int, required=True)
parser.add_argument("--reload", action="store_true")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
kind = "reload" if args.reload else "run"
log = (root / f"outputs/hydro-{kind}{args.build}.log").read_text(encoding="utf-8")
phase = "RELOAD" if args.reload else "MAIN"
assert f"[DeepFrontier Hydro] ALL {phase} CHECKS PASSED AND SAVED" in log
assert "[DeepFrontier Hydro] FAILED:" not in log
assert "PASS native Pause closes the outlet and stops actual rotor and shaft supply" in log
assert "PASS native Resume restores the previous limit and generation" in log
assert log.count("[DeepFrontier Hydro] PASS actual beaver reached ") == 5
assert not any(line.startswith(("- No Build Restriction (", "- All Buildings Transfer Power ("))
               for line in log.splitlines())
name = "Hydro turbine continuity - verified" if args.reload else "Hydro turbine - verified"
source = Path("C:/Users/Jordan/Documents/Timberborn/ExperimentalSaves/Industrial Acceptance") / f"{name}.timber"
with zipfile.ZipFile(source) as archive:
    world = json.loads(archive.read("world.json"))
entities = {e["Id"]: e for e in world["Entities"]}
assert any(e["Components"]["NamedEntity"]["EntityName"] == "Deep Frontier Acceptance Fixture"
           for e in entities.values() if "NamedEntity" in e["Components"])
record = json.loads((root / "outputs/hydro-reload-expectations.json").read_text())
for expected in record["Entities"]:
    entity = entities[expected["Id"]]
    assert entity["Template"] == expected["Template"]
    assert entity["Components"]["BlockObject"]["Coordinates"] == {
        axis.upper(): expected["Coordinates"][axis] for axis in ("x", "y", "z")}
turbines = [e for e in entities.values() if e["Template"] == "ReinforcedHydroTurbine.IronTeeth"]
assert len(turbines) == 1
turbine = turbines[0]["Components"]
assert turbine["DeepFrontier.HydroTurbine"]["DischargeLimit"] == record["Limit"]
assert turbine["DeepFrontier.HydroTurbine"]["ManuallyClosed"] == record["Closed"]
lever = [e for e in entities.values() if e["Template"] == "Lever.IronTeeth"]
assert len(lever) == 1
assert lever[0]["Components"]["Lever"]["IsOn"] == record["LeverOn"]
assert turbine["Automatable"]["Input"] == lever[0]["Id"]
assert lever[0]["Components"]["Automator"]["State"] == "On"
measurements_name = "hydro-reload-measurements" if args.reload else "hydro-measurements"
measurements = json.loads((root / f"outputs/{measurements_name}.json").read_text())
samples = measurements["samples"]
assert any(s["hp"] > 10 and s["flow"] > .1 for s in samples)
assert all(s["hp"] == 0 for s in samples if s["closed"])
assert all(s["nativeHp"] == math.ceil(s["hp"]) for s in samples)
assert all(s["networkHp"] >= s["nativeHp"] for s in samples)
assert any(s["phase"] == 12 and s["state"] == "Paused" and s["nativeHp"] == 0 for s in samples)
assert any(s["phase"] == 13 and s["nativeHp"] > 0 for s in samples)
assert all(len(s["channelFlows"]) == 2 and len(s["outletDepths"]) == 2 for s in samples)
assert all(abs(s["flow"] - sum(s["channelFlows"])) < .001 for s in samples)
assert all(s["flow"] <= s["limit"] + .001 for s in samples)
assert all(s["hp"] <= 9600.01 for s in samples)
assert "PASS native turbine sound emits audio; measured animation multiplier " in log
assert "PASS native turbine loop silent after fade; animation stopped" in log
assert any(s["audioRms"] > .00001 and s["hp"] > 0 and s["animationEnabled"]
           and any(a["playing"] and not a["muted"] and a["volume"] > 0
                   and a["spatialBlend"] == 1 and a["mixer"] for a in s["audio"])
           for s in samples)
assert any(s["phase"] == 12 and not s["animationEnabled"]
           and all(not a["playing"] or a["volume"] <= .0001 for a in s["audio"])
           for s in samples)
assert any(s["referenceSeconds"] > .05
           and abs(s["playedSeconds"] / s["referenceSeconds"] - 4) < .25
           for s in samples)
if not args.reload:
    assert "PASS high-head 3 m3/s total reaches 8–10k hp; both native outlet cells carry water" in log
    assert any(s["phase"] == 6 and s["hp"] >= 8000 and s["head"] >= 15
               and all(flow > 1.4 for flow in s["channelFlows"])
               and all(depth > .05 for depth in s["outletDepths"]) for s in samples)
stem = "hydro-continuity" if args.reload else "hydro-verified"
preserved = root / f"outputs/{stem}-build{args.build}.timber"
shutil.copyfile(source, preserved)
sha256 = hashlib.sha256(preserved.read_bytes()).hexdigest()
if not args.reload:
    (root / "outputs/hydro-save-checkpoint.json").write_text(json.dumps({
        "SourceSha256": sha256, "SourceBuild": args.build,
    }, indent=2) + "\n")
    shutil.copyfile(root / "outputs/hydro-reload-expectations.json",
                    root / f"outputs/hydro-reload-expectations{args.build}.json")
shutil.copyfile(root / f"outputs/{measurements_name}.json",
                root / f"outputs/{measurements_name}{args.build}.json")
result = {"status": "native-fixture-passed", "build": args.build, "reload": args.reload,
          "entities": len(record["Entities"]), "walkingTargets": 5,
          "save": str(preserved), "sha256": sha256,
          "peakFlow": max(s["flow"] for s in samples), "peakHp": max(s["hp"] for s in samples),
          "nativeAudioAndFourTimesPlaybackVerified": True,
          "scope": "Seeded finite-reservoir fixture; economic, multiple-turbine and pump-loop balance separate"}
(root / f"outputs/{stem}{args.build}.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
