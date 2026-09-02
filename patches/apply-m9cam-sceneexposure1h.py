#!/usr/bin/env python3
from pathlib import Path
import hashlib, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-sceneexposure1h.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')

def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'SCENEEXPOSURE1H missing expected file: {rel}')
    return p.read_text()

def write(rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)

def sha256(rel):
    return hashlib.sha256((root / rel).read_bytes()).hexdigest()

scene_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java'
scene = read(scene_rel)
if 'm9cam.sceneexposure.v7.subjectbodyadequacy1g' not in scene:
    raise SystemExit('SCENEEXPOSURE1H requires SCENEEXPOSURE1G first')
if 'diagnostic_only_no_exposure_mutation' not in scene:
    raise SystemExit('SCENEEXPOSURE1H refuses a live/mutating scene-exposure baseline')

frozen_rels = [
    'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java',
]
frozen_before = {rel: sha256(rel) for rel in frozen_rels}

scene = scene.replace('m9cam.sceneexposure.v7.subjectbodyadequacy1g',
                      'm9cam.sceneexposure.v8.renderaware1h', 1)
scene = scene.replace('sceneexposure1g_subjectbodyadequacy1a_after1f_frozen',
                      'sceneexposure1h_renderaware1a_after1g_frozen', 1)

const_anchor = '    private static final double BG_MAX_SUBJECT_ADEQUACY_ATTENUATION = 0.85;\n'
const_insert = '''    private static final double BG_MAX_SUBJECT_ADEQUACY_ATTENUATION = 0.85;

    // SCENEEXPOSURE1H diagnostic-only refinement.
    private static final double RH_EARLY_CENTER_LOW_Y = 54.0;
    private static final double RH_EARLY_CENTER_FULL_Y = 60.0;
    private static final double RH_EARLY_DELTA_LOW_Y = -2.0;
    private static final double RH_EARLY_DELTA_FULL_Y = 6.0;
    private static final double RH_EARLY_GLOBAL_DARK_FULL_Y = 55.0;
    private static final double RH_EARLY_GLOBAL_DARK_ZERO_Y = 75.0;
    private static final double RH_EARLY_MAX_ATTENUATION = 0.75;

    private static final double RH_FALSE_SPATIAL_START = 0.55;
    private static final double RH_FALSE_SPATIAL_FULL = 0.75;
    private static final double RH_FALSE_CENTER_DELTA_FULL_Y = -24.0;
    private static final double RH_FALSE_CENTER_DELTA_ZERO_Y = -14.0;
    private static final double RH_FALSE_CENTER_DARK_FULL_Y = 48.0;
    private static final double RH_FALSE_CENTER_DARK_ZERO_Y = 60.0;
    private static final double RH_FALSE_GLOBAL_SAFE_LOW_Y = 55.0;
    private static final double RH_FALSE_GLOBAL_SAFE_FULL_Y = 70.0;
    private static final double RH_HIGHLIGHT_Q99_LOW_Y = 210.0;
    private static final double RH_HIGHLIGHT_Q99_FULL_Y = 240.0;
    private static final double RH_HIGHLIGHT_224_LOW = 0.005;
    private static final double RH_HIGHLIGHT_224_FULL = 0.030;
    private static final double RH_HIGHLIGHT_240_LOW = 0.002;
    private static final double RH_HIGHLIGHT_240_FULL = 0.015;
    private static final double RH_FALSE_SPATIAL_MAX_ATTENUATION = 0.52;

    private static final double RH_RENDER_GLOBAL_LOW_Y = 80.0;
    private static final double RH_RENDER_GLOBAL_FULL_Y = 90.0;
    private static final double RH_RENDER_GLOBAL_HIGH_START_Y = 105.0;
    private static final double RH_RENDER_GLOBAL_HIGH_ZERO_Y = 120.0;
    private static final double RH_RENDER_CENTER_LOW_Y = 55.0;
    private static final double RH_RENDER_CENTER_FULL_Y = 62.0;
    private static final double RH_RENDER_CENTER_HIGH_START_Y = 78.0;
    private static final double RH_RENDER_CENTER_HIGH_ZERO_Y = 90.0;
    private static final double RH_RENDER_DELTA_FULL_Y = -20.0;
    private static final double RH_RENDER_DELTA_ZERO_Y = -8.0;
    private static final double RH_RENDER_MIDCENTER_Q95_LOW_Y = 182.0;
    private static final double RH_RENDER_MIDCENTER_Q95_FULL_Y = 192.0;
    private static final double RH_RENDER_CALM_START = 0.15;
    private static final double RH_RENDER_CALM_ZERO = 0.35;
    private static final double RH_RENDER_MAX_NEGATIVE_EV = 0.30;
'''
if const_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1H constants anchor missing')
scene = scene.replace(const_anchor, const_insert, 1)

center_anchor = '''            double centerDelta = center != null
                    ? center.optDouble("medianMinusGlobalMedian", Double.NaN) : Double.NaN;
'''
center_insert = '''            double centerDelta = center != null
                    ? center.optDouble("medianMinusGlobalMedian", Double.NaN) : Double.NaN;
            JSONObject spatialTiles = spatial != null ? spatial.optJSONObject("tiles") : null;
            JSONObject middleCenterTile = spatialTiles != null
                    ? spatialTiles.optJSONObject("middleCenter") : null;
            double middleCenterQ95 = middleCenterTile != null
                    ? middleCenterTile.optDouble("q95", Double.NaN) : Double.NaN;
'''
if center_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1H center/tile anchor missing')
scene = scene.replace(center_anchor, center_insert, 1)

positive_anchor = '''            double positivePressure = clamp01(qualificationRepairedPositivePressure
                    * (1.0 - subjectBodyAdequacyAttenuation));
            double positiveEvCandidate = MAX_POSITIVE_EV * positivePressure;
'''
positive_insert = '''            double sceneexposure1gPositivePressure = clamp01(qualificationRepairedPositivePressure
                    * (1.0 - subjectBodyAdequacyAttenuation));
            double sceneexposure1gPositiveCandidate = MAX_POSITIVE_EV
                    * sceneexposure1gPositivePressure;

            double earlySubjectCenterEvidence = smoothstep(centerMedian,
                    RH_EARLY_CENTER_LOW_Y, RH_EARLY_CENTER_FULL_Y);
            double earlySubjectRelativeEvidence = finite(centerDelta)
                    ? smoothstep(centerDelta,
                    RH_EARLY_DELTA_LOW_Y, RH_EARLY_DELTA_FULL_Y) : 0.0;
            double earlySubjectGlobalDarkEvidence = 1.0 - smoothstep(median,
                    RH_EARLY_GLOBAL_DARK_FULL_Y, RH_EARLY_GLOBAL_DARK_ZERO_Y);
            double earlySubjectCalmEvidence = 1.0 - smoothstep(
                    spatialQualificationStarvationPressure,
                    BG_CALM_STARVATION_LOW, BG_CALM_STARVATION_ZERO);
            double earlySubjectAdequacyScore = clamp01(
                    spatialQualificationAeEffort
                    * earlySubjectCenterEvidence
                    * earlySubjectRelativeEvidence
                    * earlySubjectGlobalDarkEvidence
                    * earlySubjectCalmEvidence
                    * noCatastrophicStarvationEvidence);
            double earlySubjectAdequacyAttenuation = RH_EARLY_MAX_ATTENUATION
                    * earlySubjectAdequacyScore;

            double absoluteHighlightSupportEvidence = Math.max(
                    smoothstep(q99, RH_HIGHLIGHT_Q99_LOW_Y, RH_HIGHLIGHT_Q99_FULL_Y),
                    Math.max(
                    smoothstep(bright224, RH_HIGHLIGHT_224_LOW, RH_HIGHLIGHT_224_FULL),
                    smoothstep(bright240, RH_HIGHLIGHT_240_LOW, RH_HIGHLIGHT_240_FULL)));
            double weakAbsoluteHighlightEvidence = 1.0 - clamp01(absoluteHighlightSupportEvidence);
            double falseSpatialPressureEvidence = smoothstep(
                    spatialQualificationStarvationPressure,
                    RH_FALSE_SPATIAL_START, RH_FALSE_SPATIAL_FULL);
            double falseSpatialCenterDeltaEvidence = finite(centerDelta)
                    ? 1.0 - smoothstep(centerDelta,
                    RH_FALSE_CENTER_DELTA_FULL_Y, RH_FALSE_CENTER_DELTA_ZERO_Y) : 0.0;
            double falseSpatialCenterDarkEvidence = 1.0 - smoothstep(centerMedian,
                    RH_FALSE_CENTER_DARK_FULL_Y, RH_FALSE_CENTER_DARK_ZERO_Y);
            double falseSpatialGlobalSafeEvidence = smoothstep(median,
                    RH_FALSE_GLOBAL_SAFE_LOW_Y, RH_FALSE_GLOBAL_SAFE_FULL_Y);
            double falseSpatialHighlightQualificationScore = clamp01(
                    spatialQualificationAeEffort
                    * falseSpatialPressureEvidence
                    * falseSpatialCenterDeltaEvidence
                    * falseSpatialCenterDarkEvidence
                    * falseSpatialGlobalSafeEvidence
                    * weakAbsoluteHighlightEvidence
                    * noCatastrophicStarvationEvidence);
            double falseSpatialHighlightAttenuation = RH_FALSE_SPATIAL_MAX_ATTENUATION
                    * falseSpatialHighlightQualificationScore;

            double positivePressure = clamp01(sceneexposure1gPositivePressure
                    * (1.0 - earlySubjectAdequacyAttenuation)
                    * (1.0 - falseSpatialHighlightAttenuation));
            double positiveEvCandidate = MAX_POSITIVE_EV * positivePressure;
'''
if positive_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1H post-1G positive anchor missing')
scene = scene.replace(positive_anchor, positive_insert, 1)

negative_anchor = '''            double negativePressure = negativeAfterBodyProtection;
            double negativeEvCandidate = -MAX_NEGATIVE_EV * negativePressure;
            double sceneexposure1cNegativeCandidate = negativeEvCandidate;

            double signedEv = clamp(positiveEvCandidate + negativeEvCandidate,
                    -MAX_NEGATIVE_EV, MAX_POSITIVE_EV);
'''
negative_insert = '''            double negativePressure = negativeAfterBodyProtection;
            double sceneexposure1cNegativeCandidate = -MAX_NEGATIVE_EV * negativePressure;

            double renderGlobalBandEvidence = clamp01(
                    smoothstep(median, RH_RENDER_GLOBAL_LOW_Y, RH_RENDER_GLOBAL_FULL_Y)
                    * (1.0 - smoothstep(median,
                    RH_RENDER_GLOBAL_HIGH_START_Y, RH_RENDER_GLOBAL_HIGH_ZERO_Y)));
            double renderCenterBandEvidence = clamp01(
                    smoothstep(centerMedian, RH_RENDER_CENTER_LOW_Y, RH_RENDER_CENTER_FULL_Y)
                    * (1.0 - smoothstep(centerMedian,
                    RH_RENDER_CENTER_HIGH_START_Y, RH_RENDER_CENTER_HIGH_ZERO_Y)));
            double renderCenterBelowGlobalEvidence = finite(centerDelta)
                    ? 1.0 - smoothstep(centerDelta,
                    RH_RENDER_DELTA_FULL_Y, RH_RENDER_DELTA_ZERO_Y) : 0.0;
            double renderMiddleCenterHighlightEvidence = finite(middleCenterQ95)
                    ? smoothstep(middleCenterQ95,
                    RH_RENDER_MIDCENTER_Q95_LOW_Y, RH_RENDER_MIDCENTER_Q95_FULL_Y) : 0.0;
            double renderCalmEvidence = 1.0 - smoothstep(
                    spatialQualificationStarvationPressure,
                    RH_RENDER_CALM_START, RH_RENDER_CALM_ZERO);
            double renderNearWhiteAbsentEvidence = 1.0 - smoothstep(bright224,
                    RH_HIGHLIGHT_224_LOW, RH_HIGHLIGHT_224_FULL);
            double renderAwareSubjectHighlightScore = clamp01(
                    spatialQualificationAeEffort
                    * renderGlobalBandEvidence
                    * renderCenterBandEvidence
                    * renderCenterBelowGlobalEvidence
                    * renderMiddleCenterHighlightEvidence
                    * renderCalmEvidence
                    * renderNearWhiteAbsentEvidence
                    * noCatastrophicStarvationEvidence);
            double renderAwareNegativeCandidate = -RH_RENDER_MAX_NEGATIVE_EV
                    * renderAwareSubjectHighlightScore;

            double negativeEvCandidate = clamp(sceneexposure1cNegativeCandidate
                    + renderAwareNegativeCandidate, -MAX_NEGATIVE_EV, 0.0);

            double signedEv = clamp(positiveEvCandidate + negativeEvCandidate,
                    -MAX_NEGATIVE_EV, MAX_POSITIVE_EV);
'''
if negative_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1H negative combination anchor missing')
scene = scene.replace(negative_anchor, negative_insert, 1)

inputs_anchor = '''            inputs.put("centerMedian", centerMedian);
            if (finite(centerDelta)) inputs.put("centerMedianMinusGlobalMedian", centerDelta);
'''
inputs_insert = '''            inputs.put("centerMedian", centerMedian);
            if (finite(centerDelta)) inputs.put("centerMedianMinusGlobalMedian", centerDelta);
            if (finite(middleCenterQ95)) inputs.put("middleCenterQ95", middleCenterQ95);
'''
if inputs_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1H inputs anchor missing')
scene = scene.replace(inputs_anchor, inputs_insert, 1)

positive_output_anchor = '''            positive.put("subjectBodyAdequacyScore", subjectBodyAdequacyScore);
            positive.put("subjectBodyAdequacyAttenuation", subjectBodyAdequacyAttenuation);
            positive.put("positivePressure", positivePressure);
            positive.put("sceneexposure1gPositiveCandidate", positiveEvCandidate);
            positive.put("positiveEvCandidate", positiveEvCandidate);
'''
positive_output_insert = '''            positive.put("subjectBodyAdequacyScore", subjectBodyAdequacyScore);
            positive.put("subjectBodyAdequacyAttenuation", subjectBodyAdequacyAttenuation);
            positive.put("sceneexposure1gPositivePressure", sceneexposure1gPositivePressure);
            positive.put("sceneexposure1gPositiveCandidate", sceneexposure1gPositiveCandidate);
            positive.put("earlySubjectCenterEvidence", earlySubjectCenterEvidence);
            positive.put("earlySubjectRelativeEvidence", earlySubjectRelativeEvidence);
            positive.put("earlySubjectGlobalDarkEvidence", earlySubjectGlobalDarkEvidence);
            positive.put("earlySubjectCalmEvidence", earlySubjectCalmEvidence);
            positive.put("earlySubjectAdequacyScore", earlySubjectAdequacyScore);
            positive.put("earlySubjectAdequacyAttenuation", earlySubjectAdequacyAttenuation);
            positive.put("absoluteHighlightSupportEvidence", absoluteHighlightSupportEvidence);
            positive.put("weakAbsoluteHighlightEvidence", weakAbsoluteHighlightEvidence);
            positive.put("falseSpatialPressureEvidence", falseSpatialPressureEvidence);
            positive.put("falseSpatialCenterDeltaEvidence", falseSpatialCenterDeltaEvidence);
            positive.put("falseSpatialCenterDarkEvidence", falseSpatialCenterDarkEvidence);
            positive.put("falseSpatialGlobalSafeEvidence", falseSpatialGlobalSafeEvidence);
            positive.put("falseSpatialHighlightQualificationScore", falseSpatialHighlightQualificationScore);
            positive.put("falseSpatialHighlightAttenuation", falseSpatialHighlightAttenuation);
            positive.put("positivePressure", positivePressure);
            positive.put("sceneexposure1hPositiveCandidate", positiveEvCandidate);
            positive.put("positiveEvCandidate", positiveEvCandidate);
'''
if positive_output_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1H positive output anchor missing')
scene = scene.replace(positive_output_anchor, positive_output_insert, 1)

negative_output_anchor = '''            negative.put("negativeAfterBodyProtection", negativeAfterBodyProtection);
            negative.put("negativePressure", negativePressure);
            negative.put("sceneexposure1cNegativeCandidate", sceneexposure1cNegativeCandidate);
            negative.put("negativeEvCandidate", negativeEvCandidate);
'''
negative_output_insert = '''            negative.put("negativeAfterBodyProtection", negativeAfterBodyProtection);
            negative.put("negativePressure", negativePressure);
            negative.put("sceneexposure1cNegativeCandidate", sceneexposure1cNegativeCandidate);
            negative.put("renderGlobalBandEvidence", renderGlobalBandEvidence);
            negative.put("renderCenterBandEvidence", renderCenterBandEvidence);
            negative.put("renderCenterBelowGlobalEvidence", renderCenterBelowGlobalEvidence);
            negative.put("renderMiddleCenterHighlightEvidence", renderMiddleCenterHighlightEvidence);
            negative.put("renderCalmEvidence", renderCalmEvidence);
            negative.put("renderNearWhiteAbsentEvidence", renderNearWhiteAbsentEvidence);
            negative.put("renderAwareSubjectHighlightScore", renderAwareSubjectHighlightScore);
            negative.put("renderAwareNegativeCandidate", renderAwareNegativeCandidate);
            negative.put("negativeEvCandidate", negativeEvCandidate);
'''
if negative_output_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1H negative output anchor missing')
scene = scene.replace(negative_output_anchor, negative_output_insert, 1)

limits_anchor = '            limits.put("bgMaxSubjectAdequacyAttenuation", BG_MAX_SUBJECT_ADEQUACY_ATTENUATION);\n'
limits_insert = '''            limits.put("bgMaxSubjectAdequacyAttenuation", BG_MAX_SUBJECT_ADEQUACY_ATTENUATION);
            limits.put("rhEarlyCenterLowY", RH_EARLY_CENTER_LOW_Y);
            limits.put("rhEarlyCenterFullY", RH_EARLY_CENTER_FULL_Y);
            limits.put("rhEarlyDeltaLowY", RH_EARLY_DELTA_LOW_Y);
            limits.put("rhEarlyDeltaFullY", RH_EARLY_DELTA_FULL_Y);
            limits.put("rhEarlyMaxAttenuation", RH_EARLY_MAX_ATTENUATION);
            limits.put("rhFalseSpatialStart", RH_FALSE_SPATIAL_START);
            limits.put("rhFalseSpatialFull", RH_FALSE_SPATIAL_FULL);
            limits.put("rhFalseSpatialMaxAttenuation", RH_FALSE_SPATIAL_MAX_ATTENUATION);
            limits.put("rhHighlightQ99LowY", RH_HIGHLIGHT_Q99_LOW_Y);
            limits.put("rhHighlightQ99FullY", RH_HIGHLIGHT_Q99_FULL_Y);
            limits.put("rhRenderMiddleCenterQ95LowY", RH_RENDER_MIDCENTER_Q95_LOW_Y);
            limits.put("rhRenderMiddleCenterQ95FullY", RH_RENDER_MIDCENTER_Q95_FULL_Y);
            limits.put("rhRenderMaxNegativeEv", -RH_RENDER_MAX_NEGATIVE_EV);
'''
if limits_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1H limits anchor missing')
scene = scene.replace(limits_anchor, limits_insert, 1)

top_output_anchor = '''            out.put("sceneexposure1fPositiveCandidate", sceneexposure1fPositiveCandidate);
            out.put("sceneexposure1gPositiveCandidate", positiveEvCandidate);
            out.put("positiveEvCandidate", positiveEvCandidate);
'''
top_output_insert = '''            out.put("sceneexposure1fPositiveCandidate", sceneexposure1fPositiveCandidate);
            out.put("sceneexposure1gPositiveCandidate", sceneexposure1gPositiveCandidate);
            out.put("sceneexposure1hPositiveCandidate", positiveEvCandidate);
            out.put("positiveEvCandidate", positiveEvCandidate);
'''
if top_output_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1H top-level positive output anchor missing')
scene = scene.replace(top_output_anchor, top_output_insert, 1)

top_negative_anchor = '''            out.put("sceneexposure1cNegativeCandidate", sceneexposure1cNegativeCandidate);
            out.put("negativeEvCandidate", negativeEvCandidate);
'''
top_negative_insert = '''            out.put("sceneexposure1cNegativeCandidate", sceneexposure1cNegativeCandidate);
            out.put("renderAwareNegativeCandidate", renderAwareNegativeCandidate);
            out.put("negativeEvCandidate", negativeEvCandidate);
'''
if top_negative_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1H top-level negative output anchor missing')
scene = scene.replace(top_negative_anchor, top_negative_insert, 1)

reason_anchor = '''            if (signedEv > 0.0 && legacy1bNegativeCandidate < -0.20
                    && negativeHighlightSupportGate < 0.05) {
'''
reason_insert = '''            if (signedEv < 0.0 && renderAwareNegativeCandidate < -NEUTRAL_DEADBAND_EV) {
                out.put("reason", "signed_negative_render_aware_central_highlight_pressure");
            } else if (signedEv > 0.0 && falseSpatialHighlightAttenuation > 0.05) {
                out.put("reason", "signed_positive_moderated_by_weak_absolute_highlight_support");
            } else if (signedEv > 0.0 && earlySubjectAdequacyAttenuation > 0.05) {
                out.put("reason", "signed_positive_moderated_by_early_subject_body_adequacy");
            } else if (signedEv > 0.0 && legacy1bNegativeCandidate < -0.20
                    && negativeHighlightSupportGate < 0.05) {
'''
if reason_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1H reason anchor missing')
scene = scene.replace(reason_anchor, reason_insert, 1)

write(scene_rel, scene)

gradle_rel = 'app/build.gradle'
g = read(gradle_rel)
old_v = "versionName '1.40-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1g'"
new_v = "versionName '1.41-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1h'"
if old_v not in g:
    raise SystemExit('SCENEEXPOSURE1H expected 1G versionName missing')
g = g.replace(old_v, new_v, 1)
write(gradle_rel, g)

back_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java'
b = read(back_rel)
old_b = '1.40-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1g'
new_b = '1.41-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1h'
if old_b not in b:
    raise SystemExit('SCENEEXPOSURE1H build identity anchor missing')
b = b.replace(old_b, new_b, 1)
write(back_rel, b)

for rel, before in frozen_before.items():
    after = sha256(rel)
    if after != before:
        raise SystemExit(f'SCENEEXPOSURE1H quality-freeze violation: {rel} changed')

print('M9Cam SCENEEXPOSURE1H applied: diagnostic-only early subject adequacy, absolute-highlight spatial qualification, and bounded render-aware negative pressure; live exposure/renderer/motion seams unchanged')
