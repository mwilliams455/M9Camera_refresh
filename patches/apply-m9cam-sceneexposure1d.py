#!/usr/bin/env python3
from pathlib import Path
import hashlib, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-sceneexposure1d.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')

def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'SCENEEXPOSURE1D missing expected file: {rel}')
    return p.read_text()

def write(rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)

def sha256(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'SCENEEXPOSURE1D quality-freeze guard missing expected file: {rel}')
    return hashlib.sha256(p.read_bytes()).hexdigest()

scene_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java'
scene = read(scene_rel)
if 'm9cam.sceneexposure.v3.signedpressure1c' not in scene:
    raise SystemExit('SCENEEXPOSURE1D requires SCENEEXPOSURE1C first')
for frozen_negative_marker in [
    'NEAR_WHITE224_SUPPORT_LOW = 0.06',
    'NEAR_CLIP240_SUPPORT_LOW = 0.025',
    'BROAD_MIDBRIGHT_GATE_ATTENUATION = 0.80',
    'EMISSIVE_GATE_ATTENUATION = 0.65',
    'negativeHighlightSupportGate',
]:
    if frozen_negative_marker not in scene:
        raise SystemExit(f'SCENEEXPOSURE1D negative-freeze anchor missing: {frozen_negative_marker}')

frozen_rels = [
    'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
]
frozen_before = {rel: sha256(rel) for rel in frozen_rels}

scene = scene.replace('m9cam.sceneexposure.v3.signedpressure1c', 'm9cam.sceneexposure.v4.signedpressure1d', 1)
scene = scene.replace('sceneexposure1c_negative_nearwhitegate1a_positive1b_frozen', 'sceneexposure1d_structurallowkey1a_negative1c_frozen', 1)

const_anchor = '    private static final double EMISSIVE_GATE_ATTENUATION = 0.65;\n'
const_insert = '''    private static final double EMISSIVE_GATE_ATTENUATION = 0.65;

    // SCENEEXPOSURE1D positive-only structural low-key moderation.
    // These terms do not classify literal scene content. They look for coherent
    // low-key structure: low median + broad dark occupancy, little broad-bright
    // area, weak spatial bright/dark axis separation, and no severe backlight.
    private static final double LOWKEY_MEDIAN_FULL_Y = 55.0;
    private static final double LOWKEY_MEDIAN_ZERO_Y = 105.0;
    private static final double LOWKEY_DARK64_LOW = 0.30;
    private static final double LOWKEY_DARK64_HIGH = 0.48;
    private static final double LOWKEY_BRIGHT192_FULL = 0.04;
    private static final double LOWKEY_BRIGHT192_ZERO = 0.15;
    private static final double LOWKEY_AXIS_SEPARATION_FULL = 0.05;
    private static final double LOWKEY_AXIS_SEPARATION_ZERO = 0.35;
    private static final double LOWKEY_BACKLIGHT_FULL = 0.65;
    private static final double LOWKEY_BACKLIGHT_ZERO = 0.85;
    private static final double LOWKEY_MAX_ATTENUATION = 0.68;
'''
if const_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1D constants anchor missing')
scene = scene.replace(const_anchor, const_insert, 1)

component_anchor = '''            double contrastIntentProtection = oldComponents != null
                    ? oldComponents.optDouble("landscapeHighContrastProtectionScore", 0.0) : 0.0;
'''
component_insert = '''            double contrastIntentProtection = oldComponents != null
                    ? oldComponents.optDouble("landscapeHighContrastProtectionScore", 0.0) : 0.0;
            double spatialAxisSeparationScore = oldComponents != null
                    ? oldComponents.optDouble("spatialAxisSeparationScore", 1.0) : 1.0;
'''
if component_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1D LUMA2.4 component anchor missing')
scene = scene.replace(component_anchor, component_insert, 1)

positive_anchor = '''            double centerProtectedPositivePressure = clamp01(rawPositivePressure
                    * (1.0 - healthyCenterAttenuation));
            double positivePressure = clamp01(centerProtectedPositivePressure
                    * (1.0 - 0.75 * clamp01(contrastIntentProtection)));
            double positiveEvCandidate = MAX_POSITIVE_EV * positivePressure;
'''
positive_insert = '''            double centerProtectedPositivePressure = clamp01(rawPositivePressure
                    * (1.0 - healthyCenterAttenuation));
            double sceneexposure1cPositivePressure = clamp01(centerProtectedPositivePressure
                    * (1.0 - 0.75 * clamp01(contrastIntentProtection)));
            double sceneexposure1cPositiveCandidate = MAX_POSITIVE_EV
                    * sceneexposure1cPositivePressure;

            double lowKeyMedianEvidence = 1.0 - smoothstep(median,
                    LOWKEY_MEDIAN_FULL_Y, LOWKEY_MEDIAN_ZERO_Y);
            double lowKeyDarkBodyEvidence = smoothstep(dark64,
                    LOWKEY_DARK64_LOW, LOWKEY_DARK64_HIGH);
            double lowBroadBrightEvidence = 1.0 - smoothstep(bright192,
                    LOWKEY_BRIGHT192_FULL, LOWKEY_BRIGHT192_ZERO);
            double lowSpatialAxisSeparationEvidence = 1.0 - smoothstep(
                    spatialAxisSeparationScore,
                    LOWKEY_AXIS_SEPARATION_FULL, LOWKEY_AXIS_SEPARATION_ZERO);
            double nonSevereBacklightEvidence = 1.0 - smoothstep(backlightPressure,
                    LOWKEY_BACKLIGHT_FULL, LOWKEY_BACKLIGHT_ZERO);
            double existingLandscapeProtectionBypass =
                    1.0 - clamp01(contrastIntentProtection);

            double structuralLowKeyScore = clamp01(
                    Math.min(lowKeyMedianEvidence, lowKeyDarkBodyEvidence)
                    * lowBroadBrightEvidence
                    * lowSpatialAxisSeparationEvidence
                    * nonSevereBacklightEvidence
                    * existingLandscapeProtectionBypass);
            double structuralLowKeyAttenuation =
                    LOWKEY_MAX_ATTENUATION * structuralLowKeyScore;

            double positivePressure = clamp01(sceneexposure1cPositivePressure
                    * (1.0 - structuralLowKeyAttenuation));
            double positiveEvCandidate = MAX_POSITIVE_EV * positivePressure;
'''
if positive_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1D positive-pressure anchor missing')
scene = scene.replace(positive_anchor, positive_insert, 1)

positive_output_anchor = '''            positive.put("contrastIntentProtection", contrastIntentProtection);
            positive.put("positivePressure", positivePressure);
            positive.put("positiveEvCandidate", positiveEvCandidate);
'''
positive_output_insert = '''            positive.put("contrastIntentProtection", contrastIntentProtection);
            positive.put("sceneexposure1cPositivePressure", sceneexposure1cPositivePressure);
            positive.put("sceneexposure1cPositiveCandidate", sceneexposure1cPositiveCandidate);
            positive.put("spatialAxisSeparationScore", spatialAxisSeparationScore);
            positive.put("lowKeyMedianEvidence", lowKeyMedianEvidence);
            positive.put("lowKeyDarkBodyEvidence", lowKeyDarkBodyEvidence);
            positive.put("lowBroadBrightEvidence", lowBroadBrightEvidence);
            positive.put("lowSpatialAxisSeparationEvidence", lowSpatialAxisSeparationEvidence);
            positive.put("nonSevereBacklightEvidence", nonSevereBacklightEvidence);
            positive.put("existingLandscapeProtectionBypass", existingLandscapeProtectionBypass);
            positive.put("structuralLowKeyScore", structuralLowKeyScore);
            positive.put("structuralLowKeyAttenuation", structuralLowKeyAttenuation);
            positive.put("positivePressure", positivePressure);
            positive.put("sceneexposure1dPositiveCandidate", positiveEvCandidate);
            positive.put("positiveEvCandidate", positiveEvCandidate);
'''
if positive_output_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1D positive output anchor missing')
scene = scene.replace(positive_output_anchor, positive_output_insert, 1)

limits_anchor = '''            limits.put("nearClip240SupportLow", NEAR_CLIP240_SUPPORT_LOW);
            limits.put("nearClip240SupportHigh", NEAR_CLIP240_SUPPORT_HIGH);
'''
limits_insert = '''            limits.put("nearClip240SupportLow", NEAR_CLIP240_SUPPORT_LOW);
            limits.put("nearClip240SupportHigh", NEAR_CLIP240_SUPPORT_HIGH);
            limits.put("lowKeyMedianFullY", LOWKEY_MEDIAN_FULL_Y);
            limits.put("lowKeyMedianZeroY", LOWKEY_MEDIAN_ZERO_Y);
            limits.put("lowKeyDark64Low", LOWKEY_DARK64_LOW);
            limits.put("lowKeyDark64High", LOWKEY_DARK64_HIGH);
            limits.put("lowKeyBright192Full", LOWKEY_BRIGHT192_FULL);
            limits.put("lowKeyBright192Zero", LOWKEY_BRIGHT192_ZERO);
            limits.put("lowKeyAxisSeparationFull", LOWKEY_AXIS_SEPARATION_FULL);
            limits.put("lowKeyAxisSeparationZero", LOWKEY_AXIS_SEPARATION_ZERO);
            limits.put("lowKeyBacklightFull", LOWKEY_BACKLIGHT_FULL);
            limits.put("lowKeyBacklightZero", LOWKEY_BACKLIGHT_ZERO);
            limits.put("lowKeyMaxAttenuation", LOWKEY_MAX_ATTENUATION);
'''
if limits_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1D limits anchor missing')
scene = scene.replace(limits_anchor, limits_insert, 1)

top_output_anchor = '''            out.put("positiveEvCandidate", positiveEvCandidate);
            out.put("legacy1bNegativeCandidate", legacy1bNegativeCandidate);
'''
top_output_insert = '''            out.put("sceneexposure1cPositiveCandidate", sceneexposure1cPositiveCandidate);
            out.put("sceneexposure1dPositiveCandidate", positiveEvCandidate);
            out.put("positiveEvCandidate", positiveEvCandidate);
            out.put("legacy1bNegativeCandidate", legacy1bNegativeCandidate);
'''
if top_output_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1D top-level output anchor missing')
scene = scene.replace(top_output_anchor, top_output_insert, 1)

reason_anchor = '''            } else if (signedEv > 0.0 && healthyCenterAttenuation > 0.05) {
                out.put("reason", "signed_positive_moderated_by_healthy_center");
'''
reason_insert = '''            } else if (signedEv > 0.0 && structuralLowKeyAttenuation > 0.05) {
                out.put("reason", "signed_positive_moderated_by_structural_low_key");
            } else if (signedEv > 0.0 && healthyCenterAttenuation > 0.05) {
                out.put("reason", "signed_positive_moderated_by_healthy_center");
'''
if reason_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1D reason anchor missing')
scene = scene.replace(reason_anchor, reason_insert, 1)
write(scene_rel, scene)

gradle_rel = 'app/build.gradle'
g = read(gradle_rel)
old_v = "versionName '1.36-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1c'"
new_v = "versionName '1.37-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1d'"
if new_v not in g:
    if old_v not in g:
        raise SystemExit('SCENEEXPOSURE1D: expected SCENEEXPOSURE1C versionName missing')
    g = g.replace(old_v, new_v, 1)
write(gradle_rel, g)

back_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java'
b = read(back_rel)
old_b = '1.36-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1c'
new_b = '1.37-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1d'
if new_b not in b:
    if old_b not in b:
        raise SystemExit('SCENEEXPOSURE1D: build identity anchor missing')
    b = b.replace(old_b, new_b, 1)
write(back_rel, b)

for rel, before in frozen_before.items():
    after = sha256(rel)
    if after != before:
        raise SystemExit(f'SCENEEXPOSURE1D QUALITY FREEZE FAILED: {rel} changed')
    print(f'OK   quality-freeze unchanged: {rel}')

print('M9Cam SCENEEXPOSURE1D applied: structural low-key positive moderation only; 1C negative gate, live FB1, motion allocation, renderer and capture path unchanged')
