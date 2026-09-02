#!/usr/bin/env python3
from pathlib import Path
import hashlib, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-sceneexposure1e.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')

def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'SCENEEXPOSURE1E missing expected file: {rel}')
    return p.read_text()

def write(rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)

def sha256(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'SCENEEXPOSURE1E quality-freeze guard missing expected file: {rel}')
    return hashlib.sha256(p.read_bytes()).hexdigest()

scene_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java'
scene = read(scene_rel)
if 'm9cam.sceneexposure.v4.signedpressure1d' not in scene:
    raise SystemExit('SCENEEXPOSURE1E requires SCENEEXPOSURE1D first')

for frozen_marker in [
    'NEAR_WHITE224_SUPPORT_LOW = 0.06',
    'NEAR_CLIP240_SUPPORT_LOW = 0.025',
    'BROAD_MIDBRIGHT_GATE_ATTENUATION = 0.80',
    'EMISSIVE_GATE_ATTENUATION = 0.65',
    'LOWKEY_MEDIAN_FULL_Y = 55.0',
    'LOWKEY_MEDIAN_ZERO_Y = 105.0',
    'LOWKEY_DARK64_LOW = 0.30',
    'LOWKEY_DARK64_HIGH = 0.48',
    'LOWKEY_MAX_ATTENUATION = 0.68',
    'structuralLowKeyScore',
    'structuralLowKeyAttenuation',
]:
    if frozen_marker not in scene:
        raise SystemExit(f'SCENEEXPOSURE1E frozen anchor missing: {frozen_marker}')

frozen_rels = [
    'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
]
frozen_before = {rel: sha256(rel) for rel in frozen_rels}

scene = scene.replace('m9cam.sceneexposure.v4.signedpressure1d',
                      'm9cam.sceneexposure.v5.aeefforttonal1e', 1)
scene = scene.replace('sceneexposure1d_structurallowkey1a_negative1c_frozen',
                      'sceneexposure1e_aeefforttonal1a_after1d_frozen', 1)

const_anchor = '    private static final double LOWKEY_MAX_ATTENUATION = 0.68;\n'
const_insert = '''    private static final double LOWKEY_MAX_ATTENUATION = 0.68;

    // SCENEEXPOSURE1E diagnostic-only AE-effort / tonal-adequacy moderation.
    // This stage runs AFTER the frozen 1D positive result. High exposure effort
    // is never sufficient by itself: attenuation requires a moderate/dark but
    // tonally adequate body, no strong spatial/backlight starvation, no relative
    // or catastrophic AE starvation, and no deep-dark body occupancy.
    // AE effort is ramped in log2(ISO*s) because preview exposure energy spans
    // orders of magnitude across real scenes.
    private static final double AE_EFFORT_ENERGY_LOW_ISOS = 1.50;
    private static final double AE_EFFORT_ENERGY_HIGH_ISOS = 5.00;
    private static final double AE_TONAL_MEDIAN_LOW_Y = 60.0;
    private static final double AE_TONAL_MEDIAN_FULL_Y = 82.0;
    private static final double AE_TONAL_MEDIAN_HIGH_FULL_Y = 125.0;
    private static final double AE_TONAL_MEDIAN_HIGH_ZERO_Y = 150.0;
    private static final double AE_SPATIAL_BYPASS_START = 0.20;
    private static final double AE_SPATIAL_BYPASS_FULL = 0.55;
    private static final double AE_BACKLIGHT_BYPASS_START = 0.35;
    private static final double AE_BACKLIGHT_BYPASS_FULL = 0.65;
    private static final double AE_DEEP_DARK64_START = 0.46;
    private static final double AE_DEEP_DARK64_FULL = 0.60;
    private static final double AE_BODY_DOMINANCE_DELTA_START = 0.05;
    private static final double AE_BODY_DOMINANCE_DELTA_ZERO = 0.25;
    private static final double AE_EFFORT_MAX_ATTENUATION = 0.90;
'''
if const_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1E constants anchor missing')
scene = scene.replace(const_anchor, const_insert, 1)

component_anchor = '''            double spatialAxisSeparationScore = oldComponents != null
                    ? oldComponents.optDouble("spatialAxisSeparationScore", 1.0) : 1.0;
'''
component_insert = '''            double spatialAxisSeparationScore = oldComponents != null
                    ? oldComponents.optDouble("spatialAxisSeparationScore", 1.0) : 1.0;
            // Missing LUMA2.4 starvation telemetry must fail safe by DISABLING the
            // new attenuation rather than assuming the scene is adequate.
            double energyStarvationScore = oldComponents != null
                    ? oldComponents.optDouble("energyStarvationScore", 1.0) : 1.0;
            double catastrophicAeStarvationScore = oldComponents != null
                    ? oldComponents.optDouble("catastrophicAeStarvationScore", 1.0) : 1.0;
'''
if component_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1E LUMA2.4 component anchor missing')
scene = scene.replace(component_anchor, component_insert, 1)

positive_anchor = '''            double positivePressure = clamp01(sceneexposure1cPositivePressure
                    * (1.0 - structuralLowKeyAttenuation));
            double positiveEvCandidate = MAX_POSITIVE_EV * positivePressure;
'''
positive_insert = '''            // Freeze the exact 1D output as the input to 1E.
            double sceneexposure1dPositivePressure = clamp01(sceneexposure1cPositivePressure
                    * (1.0 - structuralLowKeyAttenuation));
            double sceneexposure1dPositiveCandidate = MAX_POSITIVE_EV
                    * sceneexposure1dPositivePressure;

            double log2PreviewEnergy = finite(previewEnergyIsoSeconds)
                    && previewEnergyIsoSeconds > 0.0
                    ? Math.log(previewEnergyIsoSeconds) / Math.log(2.0)
                    : Double.NaN;
            double log2AeEffortLow = Math.log(AE_EFFORT_ENERGY_LOW_ISOS) / Math.log(2.0);
            double log2AeEffortHigh = Math.log(AE_EFFORT_ENERGY_HIGH_ISOS) / Math.log(2.0);
            double aeEffortEvidence = finite(log2PreviewEnergy)
                    ? smoothstep(log2PreviewEnergy, log2AeEffortLow, log2AeEffortHigh)
                    : 0.0;

            double achievedBodyLumaAdequacy = clamp01(
                    smoothstep(median, AE_TONAL_MEDIAN_LOW_Y, AE_TONAL_MEDIAN_FULL_Y)
                    * (1.0 - smoothstep(median,
                    AE_TONAL_MEDIAN_HIGH_FULL_Y, AE_TONAL_MEDIAN_HIGH_ZERO_Y)));
            double noSpatialStarvationEvidence = 1.0 - smoothstep(
                    spatialAxisSeparationScore,
                    AE_SPATIAL_BYPASS_START, AE_SPATIAL_BYPASS_FULL);
            double noBacklightStarvationEvidence = 1.0 - smoothstep(
                    backlightPressure,
                    AE_BACKLIGHT_BYPASS_START, AE_BACKLIGHT_BYPASS_FULL);
            double noRelativeEnergyStarvationEvidence =
                    1.0 - clamp01(energyStarvationScore);
            double nonDeepDarkBodyEvidence = 1.0 - smoothstep(
                    dark64, AE_DEEP_DARK64_START, AE_DEEP_DARK64_FULL);
            double noCatastrophicStarvationEvidence =
                    1.0 - clamp01(catastrophicAeStarvationScore);

            double backlightMinusOrdinary = Math.max(0.0,
                    backlightPressure - ordinaryBodyPressure);
            double ordinaryBodyDominanceEvidence = 1.0 - smoothstep(
                    backlightMinusOrdinary,
                    AE_BODY_DOMINANCE_DELTA_START, AE_BODY_DOMINANCE_DELTA_ZERO);

            double aeEffortTonalAdequacyScore = clamp01(
                    aeEffortEvidence
                    * achievedBodyLumaAdequacy
                    * noSpatialStarvationEvidence
                    * noBacklightStarvationEvidence
                    * noRelativeEnergyStarvationEvidence
                    * nonDeepDarkBodyEvidence
                    * noCatastrophicStarvationEvidence
                    * ordinaryBodyDominanceEvidence);
            double aeEffortAttenuation = AE_EFFORT_MAX_ATTENUATION
                    * aeEffortTonalAdequacyScore;

            double positivePressure = clamp01(sceneexposure1dPositivePressure
                    * (1.0 - aeEffortAttenuation));
            double positiveEvCandidate = MAX_POSITIVE_EV * positivePressure;
'''
if positive_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1E post-1D positive anchor missing')
scene = scene.replace(positive_anchor, positive_insert, 1)

positive_output_anchor = '''            positive.put("structuralLowKeyScore", structuralLowKeyScore);
            positive.put("structuralLowKeyAttenuation", structuralLowKeyAttenuation);
            positive.put("positivePressure", positivePressure);
            positive.put("sceneexposure1dPositiveCandidate", positiveEvCandidate);
            positive.put("positiveEvCandidate", positiveEvCandidate);
'''
positive_output_insert = '''            positive.put("structuralLowKeyScore", structuralLowKeyScore);
            positive.put("structuralLowKeyAttenuation", structuralLowKeyAttenuation);
            positive.put("sceneexposure1dPositivePressure", sceneexposure1dPositivePressure);
            positive.put("sceneexposure1dPositiveCandidate", sceneexposure1dPositiveCandidate);
            positive.put("energyStarvationScore", energyStarvationScore);
            positive.put("catastrophicAeStarvationScore", catastrophicAeStarvationScore);
            positive.put("aeEffortEvidence", aeEffortEvidence);
            positive.put("achievedBodyLumaAdequacy", achievedBodyLumaAdequacy);
            positive.put("noSpatialStarvationEvidence", noSpatialStarvationEvidence);
            positive.put("noBacklightStarvationEvidence", noBacklightStarvationEvidence);
            positive.put("noRelativeEnergyStarvationEvidence", noRelativeEnergyStarvationEvidence);
            positive.put("nonDeepDarkBodyEvidence", nonDeepDarkBodyEvidence);
            positive.put("noCatastrophicStarvationEvidence", noCatastrophicStarvationEvidence);
            positive.put("ordinaryBodyDominanceEvidence", ordinaryBodyDominanceEvidence);
            positive.put("aeEffortTonalAdequacyScore", aeEffortTonalAdequacyScore);
            positive.put("aeEffortAttenuation", aeEffortAttenuation);
            positive.put("positivePressure", positivePressure);
            positive.put("sceneexposure1ePositiveCandidate", positiveEvCandidate);
            positive.put("positiveEvCandidate", positiveEvCandidate);
'''
if positive_output_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1E positive output anchor missing')
scene = scene.replace(positive_output_anchor, positive_output_insert, 1)

limits_anchor = '            limits.put("lowKeyMaxAttenuation", LOWKEY_MAX_ATTENUATION);\n'
limits_insert = '''            limits.put("lowKeyMaxAttenuation", LOWKEY_MAX_ATTENUATION);
            limits.put("aeEffortEnergyLowIsoSeconds", AE_EFFORT_ENERGY_LOW_ISOS);
            limits.put("aeEffortEnergyHighIsoSeconds", AE_EFFORT_ENERGY_HIGH_ISOS);
            limits.put("aeTonalMedianLowY", AE_TONAL_MEDIAN_LOW_Y);
            limits.put("aeTonalMedianFullY", AE_TONAL_MEDIAN_FULL_Y);
            limits.put("aeTonalMedianHighFullY", AE_TONAL_MEDIAN_HIGH_FULL_Y);
            limits.put("aeTonalMedianHighZeroY", AE_TONAL_MEDIAN_HIGH_ZERO_Y);
            limits.put("aeSpatialBypassStart", AE_SPATIAL_BYPASS_START);
            limits.put("aeSpatialBypassFull", AE_SPATIAL_BYPASS_FULL);
            limits.put("aeBacklightBypassStart", AE_BACKLIGHT_BYPASS_START);
            limits.put("aeBacklightBypassFull", AE_BACKLIGHT_BYPASS_FULL);
            limits.put("aeDeepDark64Start", AE_DEEP_DARK64_START);
            limits.put("aeDeepDark64Full", AE_DEEP_DARK64_FULL);
            limits.put("aeBodyDominanceDeltaStart", AE_BODY_DOMINANCE_DELTA_START);
            limits.put("aeBodyDominanceDeltaZero", AE_BODY_DOMINANCE_DELTA_ZERO);
            limits.put("aeEffortMaxAttenuation", AE_EFFORT_MAX_ATTENUATION);
'''
if limits_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1E limits anchor missing')
scene = scene.replace(limits_anchor, limits_insert, 1)

top_output_anchor = '''            out.put("sceneexposure1cPositiveCandidate", sceneexposure1cPositiveCandidate);
            out.put("sceneexposure1dPositiveCandidate", positiveEvCandidate);
            out.put("positiveEvCandidate", positiveEvCandidate);
'''
top_output_insert = '''            out.put("sceneexposure1cPositiveCandidate", sceneexposure1cPositiveCandidate);
            out.put("sceneexposure1dPositiveCandidate", sceneexposure1dPositiveCandidate);
            out.put("sceneexposure1ePositiveCandidate", positiveEvCandidate);
            out.put("positiveEvCandidate", positiveEvCandidate);
'''
if top_output_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1E top-level output anchor missing')
scene = scene.replace(top_output_anchor, top_output_insert, 1)

reason_anchor = '''            } else if (signedEv > 0.0 && structuralLowKeyAttenuation > 0.05) {
                out.put("reason", "signed_positive_moderated_by_structural_low_key");
'''
reason_insert = '''            } else if (signedEv > 0.0 && aeEffortAttenuation > 0.05) {
                out.put("reason", "signed_positive_moderated_by_ae_effort_tonal_adequacy");
            } else if (signedEv > 0.0 && structuralLowKeyAttenuation > 0.05) {
                out.put("reason", "signed_positive_moderated_by_structural_low_key");
'''
if reason_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1E reason anchor missing')
scene = scene.replace(reason_anchor, reason_insert, 1)
write(scene_rel, scene)

gradle_rel = 'app/build.gradle'
g = read(gradle_rel)
old_v = "versionName '1.37-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1d'"
new_v = "versionName '1.38-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1e'"
if new_v not in g:
    if old_v not in g:
        raise SystemExit('SCENEEXPOSURE1E: expected SCENEEXPOSURE1D versionName missing')
    g = g.replace(old_v, new_v, 1)
write(gradle_rel, g)

back_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java'
b = read(back_rel)
old_b = '1.37-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1d'
new_b = '1.38-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1e'
if new_b not in b:
    if old_b not in b:
        raise SystemExit('SCENEEXPOSURE1E: build identity anchor missing')
    b = b.replace(old_b, new_b, 1)
write(back_rel, b)

for rel, before in frozen_before.items():
    after = sha256(rel)
    if after != before:
        raise SystemExit(f'SCENEEXPOSURE1E QUALITY FREEZE FAILED: {rel} changed')
    print(f'OK   quality-freeze unchanged: {rel}')

print('M9Cam SCENEEXPOSURE1E applied: diagnostic-only AE-effort/tonal-adequacy moderation after frozen 1D; live FB1, negative gate, structural-low-key logic, motion allocation, renderer and capture path unchanged')
