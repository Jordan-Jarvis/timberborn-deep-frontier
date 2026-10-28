# Concrete mixer reference revision

The source is the right-hand isometric building in [02-concrete-production-concept-v1.png](../../concepts/02-concrete-production-concept-v1.png). The top view and printed tile count were excluded.

The new Blender scene retains the tall feed frame, two separate ingredient bins, exposed plated drum, projecting drive wheel, independent water tower and descending concrete tray. The operator room is enclosed, with an arched ground entrance, small clerestory windows and a low canopy. Separate exterior galleries sit at layer 2. There are no integral stairs or decorative beavers.

Native Iron Teeth wood, roofing, metal and plaster materials supply the main surfaces. The water tank and two barrels are references to shipped meshes; their preview copies are excluded from the mod export. The header surface uses the workshop's real Water inventory. The cement hopper contains a powder mound; the aggregate hopper contains individual stones.

The final source render corrected the first candidate's unsupported storage barrels and moved a water-tower support clear of the right-hand walkway. The gallery has outer rail panels and fixed inner guardrails around open machinery.

- [Front isometric render](ConcreteMixer-front.png)
- [Opposite isometric render](ConcreteMixer-front-right.png)
- [Rear isometric render](ConcreteMixer-rear.png)
- [Source validation](source-validation.json)

Source checks passed 198 floor/headroom samples across 19 route cells, 262,306 native atlas UV corners, and two moving parts with complete 121-frame loops. The official Timbermesh exporter produced 153 nodes, two animation tracks and bindings for 23 adaptive rail openings.

Official build 79 passed native placement, stairs, supported platform stacks, under-deck construction, five actual walking destinations, selective railing openings, shaft power and visible reservoir levels. Three input-accounted batches made twelve Concrete; cutting power stopped both recipe progress and drum motion. A fresh-process reload restored exact stock/progress/identity and produced another batch while repeating the walking checks.

- [Native model, build 79](ConcreteMixer-native-build79.png)
- [Native inventory and ivory icons](ConcreteMixer-native-build79-panel.png)
- [Construction icon sheet, 128px and 32px](construction-ivory-icons.png)

The tall platform stack and outside stairs in the build 79 screenshots are separate player-buildable test structures. Conveyor and pipe delivery were tested separately in build 81 below.

Canonical source: `src/DeepFrontier/Art/Source/ConcreteMixer-ReferenceStudy.blend`. Generator: `tools/asset-pipeline/mixer_isometric_geometry.py`. Explicit grid registration: `tools/asset-pipeline/industrial_layouts.py`; authored registration is 8×6×7 with the gallery at layer 2. The dimensions follow the artwork.
## Native transport follow-up

Build 81 passed real rear conveyor inputs/output, piped water, buffer limits,
wrong-good/face rejection, power/valve interruption, conservation and two further
batches after exact saved-queue reload. The [native transport view](ConcreteMixer-native-transport-build81.jpg)
shows the tank/pump/valve at the rear corner and three conveyor warehouse lanes.
The isolated donor/receiver warehouses deliberately lack roads to exclude hauling.
The reload required a native developer needs boost for one starving test worker;
these tests do not establish economic throughput.

Build 82's [native cable view](ConcreteMixer-native-power-lines-build82.jpg) shows
the new connection on the existing rear-right frame. One remote 350 hp source
powered the mixer, six belts and pump at an observed active demand of 312 hp.
Disconnecting that cable stopped the line; reconnecting it restored two actual
production batches. The screenshot's paused mixer omits its 250 hp load, so the
panel shows the remaining 62 hp transport load. Fresh-process build 83 restored
the saved cable and transport contents, repeated the disconnection test and
delivered two further batches. It explicitly withdrew eight old Concrete after
checking saved stock to make room in the 30-unit receiver.

