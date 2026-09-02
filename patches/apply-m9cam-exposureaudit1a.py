#!/usr/bin/env python3
from pathlib import Path
import re, shutil, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-exposureaudit1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')
here = Path(__file__).resolve().parent


def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'EXPOSUREAUDIT1A missing expected file: {rel}')
    return p.read_text()


def write(rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)

# Install diagnostic-only ledger class.
src = here / 'exposureaudit1a' / 'M9ExposureAudit.java'
dst = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ExposureAudit.java'
shutil.copy2(src, dst)

iso_rel = 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java'
t = read(iso_rel)
if 'import com.particlesdevs.photoncamera.m9.M9ExposureAudit;' not in t:
    anchor = 'import com.particlesdevs.photoncamera.m9.M9ExposureDiagnostics;\n'
    if anchor not in t:
        raise SystemExit('EXPOSUREAUDIT1A: exposure diagnostics import anchor missing')
    t = t.replace(anchor, anchor + 'import com.particlesdevs.photoncamera.m9.M9ExposureAudit;\n', 1)

# Record the actual step-0 target. Preflight step -1 and later burst steps are intentionally ignored.
if 'M9ExposureAudit.beginStep0' not in t:
    anchor = '        pair.ExpoCompensateLower(1.0/compensation);\n'
    if anchor not in t:
        raise SystemExit('EXPOSUREAUDIT1A: normalized target anchor missing')
    ins = anchor + '''        if (M9Config.isCaptureTest() && step == 0) {
            M9ExposureAudit.beginStep0(step, getISOLOW(), captureController.mPreviewIso,
                    captureController.mPreviewExposureTime, pair.iso, pair.exposure);
        }
'''
    t = t.replace(anchor, ins, 1)

# Stock Photon shutter-priority counterfactual, before FB1 and M9 motion caps.
if 'M9ExposureAudit.recordPhotonReferenceStep0' not in t:
    anchor = '            M9ExposureDiagnostics.recordPhotonCurrentReference(m9PhotonReference.iso, m9PhotonReference.exposure, m9PhotonCapStart, m9PhotonCapEnd);\n'
    if anchor not in t:
        raise SystemExit('EXPOSUREAUDIT1A: Photon reference anchor missing')
    ins = anchor + '''            if (step == 0) {
                M9ExposureAudit.recordPhotonReferenceStep0(step, getISOLOW(),
                        m9PhotonReference.iso, m9PhotonReference.exposure,
                        m9PhotonCapStart, m9PhotonCapEnd);
            }
'''
    t = t.replace(anchor, ins, 1)

# Capture the FB1 decision attached to the actual step-0 allocation and calculate
# a diagnostic feedback-only allocation using the untouched Photon caps.
if 'M9ExposureAudit.recordFeedbackStep0' not in t:
    anchor = '''            M9BacklightDiagnostic.recordLiveFeedbackApplication(
                    m9Feedback,
                    m9PreviewEnergyIsoSeconds,
                    m9FeedbackRotationDegrees,
                    m9PreFeedbackExposureNs,
                    m9PreFeedbackIsoNormalized,
                    pair.exposure,
                    pair.iso);
'''
    if anchor not in t:
        raise SystemExit('EXPOSUREAUDIT1A: FB1 application anchor missing')
    ins = anchor + '''            if (M9Config.isCaptureTest() && step == 0) {
                ExpoPair m9AuditFeedbackOnly = new ExpoPair(pair);
                m9AuditFeedbackOnly.applyShutterPriorityCurve(
                        m9PhotonCapStart, m9PhotonCapEnd, CAP_RAMP_STOPS);
                M9ExposureAudit.recordFeedbackStep0(step, getISOLOW(),
                        m9FeedbackEligible, m9Feedback.wouldApply,
                        m9Feedback.recommendedEv, m9Feedback.appliedEv, m9Feedback.reason,
                        pair.iso, pair.exposure,
                        m9AuditFeedbackOnly.iso, m9AuditFeedbackOnly.exposure);
            }
'''
    t = t.replace(anchor, ins, 1)

# Record the exact motion-cap change used by the real capture path.
if 'M9ExposureAudit.recordMotionCapsStep0' not in t:
    anchor = '''            capStart = m9Decision.capStartNs; capEnd = m9Decision.capEndNs;
        }
'''
    if anchor not in t:
        raise SystemExit('EXPOSUREAUDIT1A: M9 motion cap anchor missing')
    ins = '''            capStart = m9Decision.capStartNs; capEnd = m9Decision.capEndNs;
            if (M9Config.isCaptureTest() && step == 0) {
                JSONObject m9AuditMotion = M9ModernExposurePolicy.snapshotJson();
                M9ExposureAudit.recordMotionCapsStep0(step, m9Decision.applied,
                        m9AuditMotion.optString("reason", "unknown"),
                        m9AuditMotion.optDouble("captureMotionScore", 0.0),
                        m9PhotonCapStart, m9PhotonCapEnd,
                        m9Decision.capStartNs, m9Decision.capEndNs);
            }
        }
'''
    t = t.replace(anchor, ins, 1)
    if 'import org.json.JSONObject;' not in t:
        import_anchor = 'import java.util.Locale;\n'
        if import_anchor not in t:
            raise SystemExit('EXPOSUREAUDIT1A: java.util.Locale import anchor missing')
        t = t.replace(import_anchor, import_anchor + 'import org.json.JSONObject;\n', 1)

# Final normalized allocation after all existing Photon/M9/manual/HDR transforms.
if 'M9ExposureAudit.recordFinalNormalizedStep0' not in t:
    anchor = '''        if (M9Config.isCaptureTest()) {
            M9ExposureDiagnostics.recordFinalNormalized(pair.iso, pair.exposure,
                    pair.isIsoLimited, pair.isShutterLimited, pair.isIsoManualOverLimit, pair.isShutterManualOverLimit);
        }
'''
    if anchor not in t:
        raise SystemExit('EXPOSUREAUDIT1A: final normalized anchor missing')
    ins = anchor + '''        if (M9Config.isCaptureTest() && step == 0) {
            M9ExposureAudit.recordFinalNormalizedStep0(step, getISOLOW(), pair.iso, pair.exposure);
        }
'''
    t = t.replace(anchor, ins, 1)

# Record the denormalized pair that setExpo actually writes into CaptureRequest.Builder.
if 'M9ExposureAudit.recordCaptureRequestStep0' not in t:
    anchor = '        ExpoPair pair = GenerateExpoPair(step,captureController);\n'
    if anchor not in t:
        raise SystemExit('EXPOSUREAUDIT1A: setExpo pair anchor missing')
    ins = anchor + '''        if (M9Config.isCaptureTest() && step == 0) {
            M9ExposureAudit.recordCaptureRequestStep0(step, getISOLOW(), pair.iso, pair.exposure);
        }
'''
    t = t.replace(anchor, ins, 1)

write(iso_rel, t)

# Persist the preflight-immune audit alongside the existing capture metadata.
meta_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java'
m = read(meta_rel)
if 'root.put("m9ExposureAudit"' not in m:
    anchor = '            root.put("m9ExposureFeedback", M9BacklightDiagnostic.feedbackSnapshotJson());\n'
    if anchor not in m:
        raise SystemExit('EXPOSUREAUDIT1A: metadata FB1 anchor missing')
    m = m.replace(anchor, anchor + '            root.put("m9ExposureAudit", M9ExposureAudit.snapshotJson(root));\n', 1)
write(meta_rel, m)

# Mark the build distinctly without touching renderer/math constants.
gradle_rel = 'app/build.gradle'
g = read(gradle_rel)
old_v = "versionName '1.32-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1a'"
new_v = "versionName '1.33-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1a'"
if new_v not in g:
    if old_v not in g:
        raise SystemExit('EXPOSUREAUDIT1A: expected PERF3I versionName missing')
    g = g.replace(old_v, new_v, 1)
write(gradle_rel, g)

back_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java'
b = read(back_rel)
old_b = '1.32-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1a'
new_b = '1.33-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1a'
if new_b not in b:
    if old_b not in b:
        raise SystemExit('EXPOSUREAUDIT1A: build identity anchor missing')
    b = b.replace(old_b, new_b, 1)
write(back_rel, b)

print('M9Cam EXPOSUREAUDIT1A applied: diagnostic only; PERF3I renderer/exposure arithmetic unchanged')
