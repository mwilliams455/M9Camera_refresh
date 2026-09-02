#!/usr/bin/env python3
from pathlib import Path
import hashlib, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-sceneexposure1f.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')

def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'SCENEEXPOSURE1F missing expected file: {rel}')
    return p.read_text()

def write(rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)

def sha256(rel):
    return hashlib.sha256((root / rel).read_bytes()).hexdigest()

scene_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java'
scene = read(scene_rel)
if 'm9cam.sceneexposure.v5.aeefforttonal1e' not in scene:
    raise SystemExit('SCENEEXPOSURE1F requires SCENEEXPOSURE1E first')
if 'diagnostic_only_no_exposure_mutation' not in scene:
    raise SystemExit('SCENEEXPOSURE1F refuses a live/mutating scene-exposure baseline')

# 1F is a diagnostic calibration only. Freeze all capture and photographic seams.
frozen_rels = [
    'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java',
]
frozen_before = {rel: sha256(rel) for rel in frozen_rels}

scene = scene.replace('m9cam.sceneexposure.v5.aeefforttonal1e',
                      'm9cam.sceneexposure.v6.spatialqualification1f', 1)
scene = scene.replace('sceneexposure1e_aeefforttonal1a_after1d_frozen',
                      'sceneexposure1f_spatialqualification1a_after1e_frozen', 1)

const_anchor = '    private static final double AE_EFFORT_MAX_ATTENUATION = 0.90;\n'
const_insert = '''    private static final double AE_EFFORT_MAX_ATTENUATION = 0.90;

    // SCENEEXPOSURE1F diagnostic-only qualification of the 1E starvation bypass.
    // LIVE1A showed that a dark geometric region can force the spatial/backlight
    // bypass even when AE has already spent heavily and the meaningful center is
    // not severely starved. 1F therefore adds a SECOND moderation after frozen 1E.
    // It can engage only when: exposure effort is extreme, a starvation bypass is
    // active, the global body is not collapsed, the center is not severely below
    // the frame, and catastrophic/deep-dark protections are absent.
    // True backlight controls below 10 ISO*s are deliberately untouched.
    private static final double SQ_AE_ENERGY_LOW_ISOS = 10.0;
    private static final double SQ_AE_ENERGY_HIGH_ISOS = 20.0;
    private static final double SQ_STARVATION_PRESSURE_START = 0.35;
    private static final double SQ_STARVATION_PRESSURE_FULL = 0.65;
    private static final double SQ_CENTER_DELTA_SEVERE_Y = -30.0;
    private static final double SQ_CENTER_DELTA_SAFE_Y = -10.0;
    private static final double SQ_GLOBAL_MEDIAN_COLLAPSED_Y = 50.0;
    private static final double SQ_GLOBAL_MEDIAN_SAFE_Y = 70.0;
    private static final double SQ_MAX_ATTENUATION = 0.88;
'''
if const_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1F constants anchor missing')
scene = scene.replace(const_anchor, const_insert, 1)

positive_anchor = '''            double positivePressure = clamp01(sceneexposure1dPositivePressure
                    * (1.0 - aeEffortAttenuation));
            double positiveEvCandidate = MAX_POSITIVE_EV * positivePressure;
'''
positive_insert = '''            // Freeze the exact 1E result before the new 1F qualification stage.
            double sceneexposure1ePositivePressure = clamp01(sceneexposure1dPositivePressure
                    * (1.0 - aeEffortAttenuation));
            double sceneexposure1ePositiveCandidate = MAX_POSITIVE_EV
                    * sceneexposure1ePositivePressure;

            // 1F: qualify whether a high spatial/backlight score really deserves to
            // veto AE-effort moderation. This does NOT weaken true backlight globally.
            // The extra attenuation requires extreme AE effort plus evidence that the
            // center/global body is not actually in severe exposure collapse.
            double sqLog2Low = Math.log(SQ_AE_ENERGY_LOW_ISOS) / Math.log(2.0);
            double sqLog2High = Math.log(SQ_AE_ENERGY_HIGH_ISOS) / Math.log(2.0);
            double spatialQualificationAeEffort = finite(log2PreviewEnergy)
                    ? smoothstep(log2PreviewEnergy, sqLog2Low, sqLog2High) : 0.0;
            double spatialQualificationStarvationPressure = Math.max(
                    clamp01(spatialAxisSeparationScore), clamp01(backlightPressure));
            double spatialQualificationBypassActive = smoothstep(
                    spatialQualificationStarvationPressure,
                    SQ_STARVATION_PRESSURE_START, SQ_STARVATION_PRESSURE_FULL);
            double centerNotSeverelyStarvedEvidence = finite(centerDelta)
                    ? smoothstep(centerDelta,
                    SQ_CENTER_DELTA_SEVERE_Y, SQ_CENTER_DELTA_SAFE_Y) : 0.0;
            double globalBodyNotCollapsedEvidence = smoothstep(median,
                    SQ_GLOBAL_MEDIAN_COLLAPSED_Y, SQ_GLOBAL_MEDIAN_SAFE_Y);

            double spatialFalseStarvationQualificationScore = clamp01(
                    spatialQualificationAeEffort
                    * spatialQualificationBypassActive
                    * centerNotSeverelyStarvedEvidence
                    * globalBodyNotCollapsedEvidence
                    * nonDeepDarkBodyEvidence
                    * noCatastrophicStarvationEvidence);
            double spatialQualificationAttenuation = SQ_MAX_ATTENUATION
                    * spatialFalseStarvationQualificationScore;

            double positivePressure = clamp01(sceneexposure1ePositivePressure
                    * (1.0 - spatialQualificationAttenuation));
            double positiveEvCandidate = MAX_POSITIVE_EV * positivePressure;
'''
if positive_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1F post-1E positive anchor missing')
scene = scene.replace(positive_anchor, positive_insert, 1)

positive_output_anchor = '''            positive.put("aeEffortTonalAdequacyScore", aeEffortTonalAdequacyScore);
            positive.put("aeEffortAttenuation", aeEffortAttenuation);
            positive.put("positivePressure", positivePressure);
            positive.put("sceneexposure1ePositiveCandidate", positiveEvCandidate);
            positive.put("positiveEvCandidate", positiveEvCandidate);
'''
positive_output_insert = '''            positive.put("aeEffortTonalAdequacyScore", aeEffortTonalAdequacyScore);
            positive.put("aeEffortAttenuation", aeEffortAttenuation);
            positive.put("sceneexposure1ePositivePressure", sceneexposure1ePositivePressure);
            positive.put("sceneexposure1ePositiveCandidate", sceneexposure1ePositiveCandidate);
            positive.put("spatialQualificationAeEffort", spatialQualificationAeEffort);
            positive.put("spatialQualificationStarvationPressure", spatialQualificationStarvationPressure);
            positive.put("spatialQualificationBypassActive", spatialQualificationBypassActive);
            positive.put("centerNotSeverelyStarvedEvidence", centerNotSeverelyStarvedEvidence);
            positive.put("globalBodyNotCollapsedEvidence", globalBodyNotCollapsedEvidence);
            positive.put("spatialFalseStarvationQualificationScore", spatialFalseStarvationQualificationScore);
            positive.put("spatialQualificationAttenuation", spatialQualificationAttenuation);
            positive.put("positivePressure", positivePressure);
            positive.put("sceneexposure1fPositiveCandidate", positiveEvCandidate);
            positive.put("positiveEvCandidate", positiveEvCandidate);
'''
if positive_output_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1F positive output anchor missing')
scene = scene.replace(positive_output_anchor, positive_output_insert, 1)

limits_anchor = '            limits.put("aeEffortMaxAttenuation", AE_EFFORT_MAX_ATTENUATION);\n'
limits_insert = '''            limits.put("aeEffortMaxAttenuation", AE_EFFORT_MAX_ATTENUATION);
            limits.put("sqAeEnergyLowIsoSeconds", SQ_AE_ENERGY_LOW_ISOS);
            limits.put("sqAeEnergyHighIsoSeconds", SQ_AE_ENERGY_HIGH_ISOS);
            limits.put("sqStarvationPressureStart", SQ_STARVATION_PRESSURE_START);
            limits.put("sqStarvationPressureFull", SQ_STARVATION_PRESSURE_FULL);
            limits.put("sqCenterDeltaSevereY", SQ_CENTER_DELTA_SEVERE_Y);
            limits.put("sqCenterDeltaSafeY", SQ_CENTER_DELTA_SAFE_Y);
            limits.put("sqGlobalMedianCollapsedY", SQ_GLOBAL_MEDIAN_COLLAPSED_Y);
            limits.put("sqGlobalMedianSafeY", SQ_GLOBAL_MEDIAN_SAFE_Y);
            limits.put("sqMaxAttenuation", SQ_MAX_ATTENUATION);
'''
if limits_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1F limits anchor missing')
scene = scene.replace(limits_anchor, limits_insert, 1)

top_output_anchor = '''            out.put("sceneexposure1dPositiveCandidate", sceneexposure1dPositiveCandidate);
            out.put("sceneexposure1ePositiveCandidate", positiveEvCandidate);
            out.put("positiveEvCandidate", positiveEvCandidate);
'''
top_output_insert = '''            out.put("sceneexposure1dPositiveCandidate", sceneexposure1dPositiveCandidate);
            out.put("sceneexposure1ePositiveCandidate", sceneexposure1ePositiveCandidate);
            out.put("sceneexposure1fPositiveCandidate", positiveEvCandidate);
            out.put("positiveEvCandidate", positiveEvCandidate);
'''
if top_output_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1F top-level output anchor missing')
scene = scene.replace(top_output_anchor, top_output_insert, 1)

reason_anchor = '''            } else if (signedEv > 0.0 && aeEffortAttenuation > 0.05) {
                out.put("reason", "signed_positive_moderated_by_ae_effort_tonal_adequacy");
'''
reason_insert = '''            } else if (signedEv > 0.0 && spatialQualificationAttenuation > 0.05) {
                out.put("reason", "signed_positive_moderated_by_spatial_starvation_qualification");
            } else if (signedEv > 0.0 && aeEffortAttenuation > 0.05) {
                out.put("reason", "signed_positive_moderated_by_ae_effort_tonal_adequacy");
'''
if reason_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1F reason anchor missing')
scene = scene.replace(reason_anchor, reason_insert, 1)
write(scene_rel, scene)

# Distinct diagnostic build identity.
gradle_rel = 'app/build.gradle'
g = read(gradle_rel)
old_v = "versionName '1.38-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1e'"
new_v = "versionName '1.39-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1f'"
if old_v not in g:
    raise SystemExit('SCENEEXPOSURE1F expected 1E versionName missing')
g = g.replace(old_v, new_v, 1)
write(gradle_rel, g)

back_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java'
b = read(back_rel)
old_b = '1.38-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1e'
new_b = '1.39-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1f'
if old_b not in b:
    raise SystemExit('SCENEEXPOSURE1F build identity anchor missing')
b = b.replace(old_b, new_b, 1)
write(back_rel, b)

for rel, before in frozen_before.items():
    after = sha256(rel)
    if after != before:
        raise SystemExit(f'SCENEEXPOSURE1F quality-freeze violation: {rel} changed')

print('M9Cam SCENEEXPOSURE1F applied: diagnostic-only high-AE spatial-starvation qualification after frozen 1E; capture/renderer/motion seams unchanged')
