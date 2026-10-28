// Vanilla smoke and steam at the flue mouths of late-game buildings, the
// Grocery Market and the civic, industrial and research buildings.
//
// Emitters come from the study registration (smokeEmitters: kind, mouth
// position in artwork coordinates, mouth radius), recorded by
// lategame_kit.emitter / lategame_kit.stack(emits=...) and written by
// render_lategame_studies.py or register_grocery_market.py. For the civic,
// industrial and research buildings (Restaurant, Hospital, FisheryWorks,
// CementKiln, MaterialsLaboratory) register_smoke_emitters.py writes the same
// shape to outputs/<pipeline>-integration/<Model>-smoke-registration.json, in
// the native grid frame (artwork + registration origin) and checked against
// the saved scene; read it with sceneSmokeRegistration.
//
// Timberborn 1.1 contract (decompiled TemplateAttachments, ParticlesCache and
// the particle controllers): an attachment instantiates its prefab under the
// transform named by Parent (recursive name search, which throws when absent)
// at Position/Rotation/Scale in that transform's local frame. '#Finished' is
// the blueprint child that holds the finished model, so no model node is
// needed; the model's local frame is (x, z, y) of the artwork, the mapping the
// exporter uses for worker slots. The construction-stage model is a copy of
// the finished one, so named empties would exist twice; '#Finished' avoids it.
//
// Effects are the shipped Iron Teeth ones, read from the vanilla blueprints:
// - smoke: Smelter's SmelterSmoke, bent by WindParticleController as on the
//   Smelter.
// - steam: SteamEngine's SteamEngineSmoke (small stack-top steam).
// - towerSteam: GeothermalEngine's GeothermalEngineSmoke (broad plume) for
//   cooling-tower mouths.
// - fountainSpray: the Folktails Fountain of Joy's FountainOfJoyWater (spray
//   and bucket pour), over a native Fountain of Joy prop at its vanilla
//   attachment point.
// Scale: the vanilla attachment scale at REFERENCE_RADIUS, proportional to the
// recorded mouth radius. The reference radii are estimates (the vanilla
// prefabs and meshes are not in the repo); tune them from in-game review.
//
// Start/stop: workshops use WorkshopParticleController (plays while the
// workshop works; for the reactor, a WorkshopPoweredGenerator, that is while
// it generates). Native good-powered generators (the coal and oil power
// plants, cloned from the vanilla Steam Engine) use the Steam Engine's
// PowerGeneratorParticleController, which plays while
// MechanicalNode.ActiveAndPowered and OutputMultiplier > 0, i.e. while they
// generate. Other enterable buildings use EnterableParticleController
// (plays while anyone is inside). A powered building that is neither (the
// Smog Scrubber) uses the native MechanicalNodeParticlesController, which
// plays while MechanicalNode.ActiveAndPowered and its power efficiency exceeds
// MinEfficiency, as on the vanilla Wind Tunnel (0.2). Anything else fails
// explicitly.
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';

const root = new URL('../', import.meta.url);
const vanillaRoot = 'vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources/';
const vanilla = async (path) => JSON.parse(await readFile(new URL(vanillaRoot + path, root), 'utf8'));

async function vanillaEffect(path, attachmentId) {
  const blueprint = await vanilla(path);
  const attachment = blueprint.TemplateAttachmentsSpec?.Attachments?.find((a) => a.AttachmentId === attachmentId);
  if (!attachment) throw new Error(`${path}: no vanilla ${attachmentId} attachment`);
  const {Prefab, Rotation, Scale, CreateInstantly} = attachment;
  if (Scale.X !== Scale.Y || Scale.Y !== Scale.Z) throw new Error(`${path}: ${attachmentId} scale is not uniform`);
  const wind = Boolean(blueprint.WindParticleControllerSpec?.AttachmentIds?.includes(attachmentId));
  return {Prefab, Rotation, scale: Scale.X, CreateInstantly, wind};
}

const EFFECTS = {
  smoke: await vanillaEffect('Buildings/Metal/Smelter/Smelter.IronTeeth.blueprint.json', 'Smoke'),
  steam: await vanillaEffect('Buildings/Power/SteamEngine/SteamEngine.IronTeeth.blueprint.json', 'Smoke1'),
  towerSteam: await vanillaEffect('Buildings/Power/GeothermalEngine/GeothermalEngine.IronTeeth.blueprint.json', 'Smoke'),
  fountainSpray: await vanillaEffect('Buildings/Monuments/FountainOfJoy/FountainOfJoy.Folktails.blueprint.json', 'Water'),
};
// Mouth radius (tiles) at which the vanilla attachment scale applies.
// fountainSpray: the Fountain of Joy's half-width (5 x 5 model), so a native
// fountain prop at scale s records radius 2.5 s and gets the vanilla effect at s.
const REFERENCE_RADIUS = {smoke: .2, steam: .15, towerSteam: 1.0, fountainSpray: 2.5};
const PREFIX = {smoke: 'Smoke', steam: 'Steam', towerSteam: 'TowerSteam', fountainSpray: 'FountainSpray'};
export const PARTICLE_SPECS = ['TemplateAttachmentsSpec', 'WorkshopParticleControllerSpec', 'WindParticleControllerSpec',
  'PowerGeneratorParticleControllerSpec', 'EnterableParticleControllerSpec', 'BlockableObjectParticleControllerSpec',
  'MechanicalNodeParticlesControllerSpec'];
// Vanilla Wind Tunnel MechanicalNodeParticlesControllerSpec.MinEfficiency.
const POWERED_MIN_EFFICIENCY = (await vanilla('Buildings/Wellbeing/WindTunnel/WindTunnel.IronTeeth.blueprint.json'))
  .MechanicalNodeParticlesControllerSpec.MinEfficiency;
const round = (v) => Math.round(v * 1e4) / 1e4;

export function applyVanillaSmoke(value, registration, id) {
  if (!Array.isArray(registration.smokeEmitters)) {
    throw new Error(`${id}: registration has no smokeEmitters; re-register the study`);
  }
  for (const spec of PARTICLE_SPECS) {
    if (value[spec]) throw new Error(`${id}: template ${spec} survives; remove the template's effects at the source`);
  }
  if (!registration.smokeEmitters.length) return [];
  const controller = value.WorkshopSpec ? 'WorkshopParticleControllerSpec'
    : value.GoodPoweredGeneratorSpec ? 'PowerGeneratorParticleControllerSpec'
    : value.EnterableSpec ? 'EnterableParticleControllerSpec'
    : value.MechanicalBuildingSpec && value.MechanicalNodeSpec?.PowerInput > 0 ? 'MechanicalNodeParticlesControllerSpec' : null;
  if (!controller) throw new Error(`${id}: smoke emitters need a workshop, a good-powered generator, an enterable or a powered building to run them`);
  const attachments = [];
  const wind = [];
  const counts = {};
  for (const {kind, position, radius} of registration.smokeEmitters) {
    const effect = EFFECTS[kind];
    if (!effect) throw new Error(`${id}: unknown emitter kind ${kind}`);
    if (!(radius > 0)) throw new Error(`${id}: ${kind} emitter at ${position} has no mouth radius`);
    const [x, y, z] = position;
    const AttachmentId = PREFIX[kind] + (counts[kind] = (counts[kind] ?? 0) + 1);
    const s = round(effect.scale * radius / REFERENCE_RADIUS[kind]);
    attachments.push({AttachmentId, Prefab: effect.Prefab, Parent: '#Finished', Position: {X: x, Y: z, Z: y},
      Rotation: {...effect.Rotation}, Scale: {X: s, Y: s, Z: s}, CreateInstantly: effect.CreateInstantly});
    if (effect.wind) wind.push(AttachmentId);
  }
  value.TemplateAttachmentsSpec = {Attachments: attachments};
  value[controller] = controller === 'MechanicalNodeParticlesControllerSpec'
    ? {MinEfficiency: POWERED_MIN_EFFICIENCY, AttachmentIds: attachments.map((a) => a.AttachmentId)}
    : {AttachmentIds: attachments.map((a) => a.AttachmentId)};
  if (wind.length) value.WindParticleControllerSpec = {AttachmentIds: wind};
  return attachments;
}

// The smoke registration of a civic, industrial or research building
// (register_smoke_emitters.py). It must belong to the exact saved scene and to
// the building registration (layout origin, BaseZ and size) the blueprint
// uses; otherwise the mouths may not match the model and generation stops.
export async function sceneSmokeRegistration(folder, ident, layout) {
  const record = JSON.parse(await readFile(new URL(`outputs/${folder}/${ident}-smoke-registration.json`, root), 'utf8'));
  const scene = await readFile(new URL(`src/DeepFrontier/Art/Source/${ident}-ReferenceStudy.blend`, root));
  if (record.ident !== ident || record.sourceSha256 !== createHash('sha256').update(scene).digest('hex')) {
    throw new Error(`${ident}: smoke emitters were registered on a different scene; rerun register_smoke_emitters.py`);
  }
  const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  if (!same(record.origin, layout.origin) || record.baseZ !== layout.baseZ || !same([...record.footprint, record.height], layout.size)) {
    throw new Error(`${ident}: smoke registration differs from the building registration (origin, BaseZ or size); rerun register_smoke_emitters.py`);
  }
  return record;
}
