#!/usr/bin/env python3
from pathlib import Path
import hashlib, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-sceneexposure1g.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')

def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'SCENEEXPOSURE1G missing expected file: {rel}')
    return p.read_text()

def write(rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)

def sha256(rel):
    return hashlib.sha256((root / rel).read_bytes()).hexdigest()

scene_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java'
scene = read(scene_rel)
if 'm9cam.sceneexposure.v6.spatialqualification1f' not in scene:
    raise SystemExit('SCENEEXPOSURE1G requires SCENEEXPOSURE1F first')
if 'diagnostic_only_no_exposure_mutation' not in scene:
    raise SystemExit('SCENEEXPOSURE1G refuses a live/mutating scene-exposure baseline')

# 1G is diagnostic-only. Freeze all capture and photographic seams.
frozen_rels = [
    'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java',
]
frozen_before = {rel: sha256(rel) for rel in frozen_rels}

scene = scene.replace('m9cam.sceneexposure.v6.spatialqualification1f',
                      'm9cam.sceneexposure.v7.subjectbodyadequacy1g', 1)
scene = scene.replace('sceneexposure1f_spatialqualification1a_after1e_frozen',
                      'sceneexposure1g_subjectbodyadequacy1a_after1f_frozen', 1)

const_anchor = '    private static final double SQ_MAX_ATTENUATION = 0.88;\n'
const_insert = '''    private static final double SQ_MAX_ATTENUATION = 0.88;

    // SCENEEXPOSURE1G diagnostic-only subject/body adequacy calibration.
    // Two independent corrections are intentionally narrow:
    //  (A) repair 1F over-moderation only when a genuinely severe spatial split
    //      coexists with an absolutely dark center/body (191151 class);
    //  (B) moderate globally-dark frames when AE effort is already extreme but the
    //      center/body is absolutely adequate, relatively elevated, and spatially calm
    //      (191403 class). This avoids brightening a well-placed subject merely to lift
    //      intentionally dark surroundings.
    private static final double BG_RESTORE_SPATIAL_START = 0.75;
    private static final double BG_RESTORE_SPATIAL_FULL = 0.95;
    private static final double BG_CENTER_STARVED_FULL_Y = 50.0;
    private static final double BG_CENTER_STARVED_ZERO_Y = 70.0;
    private static final double BG_MAX_1F_RESTORE_FRACTION = 0.42;

    private static final double BG_CENTER_ADEQUATE_LOW_Y = 55.0;
    private static final double BG_CENTER_ADEQUATE_FULL_Y = 75.0;
    private static final double BG_CENTER_DELTA_ADEQUATE_LOW_Y = -5.0;
    private static final double BG_CENTER_DELTA_ADEQUATE_FULL_Y = 15.0;
    private static final double BG_GLOBAL_DARK_FULL_Y = 55.0;
    private static final double BG_GLOBAL_DARK_ZERO_Y = 80.0;
    private static final double BG_CALM_STARVATION_LOW = 0.20;
    private static final double BG_CALM_STARVATION_ZERO = 0.50;
    private static final double BG_MAX_SUBJECT_ADEQUACY_ATTENUATION = 0.85;
'''
if const_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1G constants anchor missing')
scene = scene.replace(const_anchor, const_insert, 1)

positive_anchor = '''            double positivePressure = clamp01(sceneexposure1ePositivePressure
                    * (1.0 - spatialQualificationAttenuation));
            double positiveEvCandidate = MAX_POSITIVE_EV * positivePressure;
'''
positive_insert = '''            // Freeze the exact 1F result before 1G.
            double sceneexposure1fPositivePressure = clamp01(sceneexposure1ePositivePressure
                    * (1.0 - spatialQualificationAttenuation));
            double sceneexposure1fPositiveCandidate = MAX_POSITIVE_EV
                    * sceneexposure1fPositivePressure;

            // 1G-A: restore a bounded fraction of the 1F attenuation only where the
            // spatial split itself is extreme AND the absolute center/body is still
            // dark. This is the missing protection exposed by 191151.
            double severeSpatialSeparationEvidence = smoothstep(spatialAxisSeparationScore,
                    BG_RESTORE_SPATIAL_START, BG_RESTORE_SPATIAL_FULL);
            double absoluteCenterStarvationEvidence = 1.0 - smoothstep(centerMedian,
                    BG_CENTER_STARVED_FULL_Y, BG_CENTER_STARVED_ZERO_Y);
            double spatialQualificationRestorationScore = clamp01(
                    spatialQualificationAeEffort
                    * severeSpatialSeparationEvidence
                    * absoluteCenterStarvationEvidence
                    * noCatastrophicStarvationEvidence);
            double spatialQualificationRestoreFraction = BG_MAX_1F_RESTORE_FRACTION
                    * spatialQualificationRestorationScore;
            double effectiveSpatialQualificationAttenuation = spatialQualificationAttenuation
                    * (1.0 - spatialQualificationRestoreFraction);
            double qualificationRepairedPositivePressure = clamp01(
                    sceneexposure1ePositivePressure
                    * (1.0 - effectiveSpatialQualificationAttenuation));

            // 1G-B: high-AE subject/body adequacy in a globally dark context. The
            // center must be absolutely healthy, elevated relative to global, and the
            // spatial/backlight starvation signal must be calm. This lets 191403 fall
            // toward neutral without touching true backlight or ordinary 1E successes.
            double absoluteCenterAdequacyEvidence = smoothstep(centerMedian,
                    BG_CENTER_ADEQUATE_LOW_Y, BG_CENTER_ADEQUATE_FULL_Y);
            double relativeCenterAdequacyEvidence = finite(centerDelta)
                    ? smoothstep(centerDelta,
                    BG_CENTER_DELTA_ADEQUATE_LOW_Y, BG_CENTER_DELTA_ADEQUATE_FULL_Y) : 0.0;
            double globalDarkContextEvidence = 1.0 - smoothstep(median,
                    BG_GLOBAL_DARK_FULL_Y, BG_GLOBAL_DARK_ZERO_Y);
            double calmStarvationEvidence = 1.0 - smoothstep(
                    Math.max(clamp01(spatialAxisSeparationScore), clamp01(backlightPressure)),
                    BG_CALM_STARVATION_LOW, BG_CALM_STARVATION_ZERO);
            double subjectBodyAdequacyScore = clamp01(
                    spatialQualificationAeEffort
                    * absoluteCenterAdequacyEvidence
                    * relativeCenterAdequacyEvidence
                    * globalDarkContextEvidence
                    * calmStarvationEvidence
                    * noCatastrophicStarvationEvidence);
            double subjectBodyAdequacyAttenuation = BG_MAX_SUBJECT_ADEQUACY_ATTENUATION
                    * subjectBodyAdequacyScore;

            double positivePressure = clamp01(qualificationRepairedPositivePressure
                    * (1.0 - subjectBodyAdequacyAttenuation));
            double positiveEvCandidate = MAX_POSITIVE_EV * positivePressure;
'''
if positive_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1G post-1F positive anchor missing')
scene = scene.replace(positive_anchor, positive_insert, 1)

positive_output_anchor = '''            positive.put("spatialFalseStarvationQualificationScore", spatialFalseStarvationQualificationScore);
            positive.put("spatialQualificationAttenuation", spatialQualificationAttenuation);
            positive.put("positivePressure", positivePressure);
            positive.put("sceneexposure1fPositiveCandidate", positiveEvCandidate);
            positive.put("positiveEvCandidate", positiveEvCandidate);
'''
positive_output_insert = '''            positive.put("spatialFalseStarvationQualificationScore", spatialFalseStarvationQualificationScore);
            positive.put("spatialQualificationAttenuation", spatialQualificationAttenuation);
            positive.put("sceneexposure1fPositivePressure", sceneexposure1fPositivePressure);
            positive.put("sceneexposure1fPositiveCandidate", sceneexposure1fPositiveCandidate);
            positive.put("severeSpatialSeparationEvidence", severeSpatialSeparationEvidence);
            positive.put("absoluteCenterStarvationEvidence", absoluteCenterStarvationEvidence);
            positive.put("spatialQualificationRestorationScore", spatialQualificationRestorationScore);
            positive.put("spatialQualificationRestoreFraction", spatialQualificationRestoreFraction);
            positive.put("effectiveSpatialQualificationAttenuation", effectiveSpatialQualificationAttenuation);
            positive.put("qualificationRepairedPositivePressure", qualificationRepairedPositivePressure);
            positive.put("absoluteCenterAdequacyEvidence", absoluteCenterAdequacyEvidence);
            positive.put("relativeCenterAdequacyEvidence", relativeCenterAdequacyEvidence);
            positive.put("globalDarkContextEvidence", globalDarkContextEvidence);
            positive.put("calmStarvationEvidence", calmStarvationEvidence);
            positive.put("subjectBodyAdequacyScore", subjectBodyAdequacyScore);
            positive.put("subjectBodyAdequacyAttenuation", subjectBodyAdequacyAttenuation);
            positive.put("positivePressure", positivePressure);
            positive.put("sceneexposure1gPositiveCandidate", positiveEvCandidate);
            positive.put("positiveEvCandidate", positiveEvCandidate);
'''
if positive_output_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1G positive output anchor missing')
scene = scene.replace(positive_output_anchor, positive_output_insert, 1)

limits_anchor = '            limits.put("sqMaxAttenuation", SQ_MAX_ATTENUATION);\n'
limits_insert = '''            limits.put("sqMaxAttenuation", SQ_MAX_ATTENUATION);
            limits.put("bgRestoreSpatialStart", BG_RESTORE_SPATIAL_START);
            limits.put("bgRestoreSpatialFull", BG_RESTORE_SPATIAL_FULL);
            limits.put("bgCenterStarvedFullY", BG_CENTER_STARVED_FULL_Y);
            limits.put("bgCenterStarvedZeroY", BG_CENTER_STARVED_ZERO_Y);
            limits.put("bgMax1fRestoreFraction", BG_MAX_1F_RESTORE_FRACTION);
            limits.put("bgCenterAdequateLowY", BG_CENTER_ADEQUATE_LOW_Y);
            limits.put("bgCenterAdequateFullY", BG_CENTER_ADEQUATE_FULL_Y);
            limits.put("bgCenterDeltaAdequateLowY", BG_CENTER_DELTA_ADEQUATE_LOW_Y);
            limits.put("bgCenterDeltaAdequateFullY", BG_CENTER_DELTA_ADEQUATE_FULL_Y);
            limits.put("bgGlobalDarkFullY", BG_GLOBAL_DARK_FULL_Y);
            limits.put("bgGlobalDarkZeroY", BG_GLOBAL_DARK_ZERO_Y);
            limits.put("bgCalmStarvationLow", BG_CALM_STARVATION_LOW);
            limits.put("bgCalmStarvationZero", BG_CALM_STARVATION_ZERO);
            limits.put("bgMaxSubjectAdequacyAttenuation", BG_MAX_SUBJECT_ADEQUACY_ATTENUATION);
'''
if limits_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1G limits anchor missing')
scene = scene.replace(limits_anchor, limits_insert, 1)

top_output_anchor = '''            out.put("sceneexposure1ePositiveCandidate", sceneexposure1ePositiveCandidate);
            out.put("sceneexposure1fPositiveCandidate", positiveEvCandidate);
            out.put("positiveEvCandidate", positiveEvCandidate);
'''
top_output_insert = '''            out.put("sceneexposure1ePositiveCandidate", sceneexposure1ePositiveCandidate);
            out.put("sceneexposure1fPositiveCandidate", sceneexposure1fPositiveCandidate);
            out.put("sceneexposure1gPositiveCandidate", positiveEvCandidate);
            out.put("positiveEvCandidate", positiveEvCandidate);
'''
if top_output_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1G top-level output anchor missing')
scene = scene.replace(top_output_anchor, top_output_insert, 1)

reason_anchor = '''            } else if (signedEv > 0.0 && spatialQualificationAttenuation > 0.05) {
                out.put("reason", "signed_positive_moderated_by_spatial_starvation_qualification");
'''
reason_insert = '''            } else if (signedEv > 0.0 && subjectBodyAdequacyAttenuation > 0.05) {
                out.put("reason", "signed_positive_moderated_by_subject_body_adequacy");
            } else if (signedEv > 0.0 && spatialQualificationRestoreFraction > 0.05) {
                out.put("reason", "signed_positive_1f_restored_by_absolute_center_starvation");
            } else if (signedEv > 0.0 && spatialQualificationAttenuation > 0.05) {
                out.put("reason", "signed_positive_moderated_by_spatial_starvation_qualification");
'''
if reason_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1G reason anchor missing')
scene = scene.replace(reason_anchor, reason_insert, 1)
write(scene_rel, scene)

# Distinct diagnostic build identity.
gradle_rel = 'app/build.gradle'
g = read(gradle_rel)
old_v = "versionName '1.39-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1f'"
new_v = "versionName '1.40-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1g'"
if old_v not in g:
    raise SystemExit('SCENEEXPOSURE1G expected 1F versionName missing')
g = g.replace(old_v, new_v, 1)
write(gradle_rel, g)

back_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java'
b = read(back_rel)
old_b = '1.39-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1f'
new_b = '1.40-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1g'
if old_b not in b:
    raise SystemExit('SCENEEXPOSURE1G build identity anchor missing')
b = b.replace(old_b, new_b, 1)
write(back_rel, b)

for rel, before in frozen_before.items():
    after = sha256(rel)
    if after != before:
        raise SystemExit(f'SCENEEXPOSURE1G quality-freeze violation: {rel} changed')

print('M9Cam SCENEEXPOSURE1G applied: diagnostic-only absolute-center restoration plus high-AE subject/body adequacy; capture/renderer/motion seams unchanged')
