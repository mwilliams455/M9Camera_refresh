#!/usr/bin/env python3
from pathlib import Path
import shutil, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-sceneexposure1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')
here = Path(__file__).resolve().parent


def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'SCENEEXPOSURE1A missing expected file: {rel}')
    return p.read_text()


def write(rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)

# This overlay must be applied after EXPOSUREAUDIT1A. It is diagnostic only.
audit_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ExposureAudit.java'
if not (root / audit_rel).exists():
    raise SystemExit('SCENEEXPOSURE1A requires EXPOSUREAUDIT1A first')

src = here / 'sceneexposure1a' / 'M9SceneExposureDiagnostic.java'
dst = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java'
shutil.copy2(src, dst)

iso_rel = 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java'
t = read(iso_rel)
if 'import com.particlesdevs.photoncamera.m9.M9SceneExposureDiagnostic;' not in t:
    anchor = 'import com.particlesdevs.photoncamera.m9.M9ExposureAudit;\n'
    if anchor not in t:
        raise SystemExit('SCENEEXPOSURE1A: EXPOSUREAUDIT1A import anchor missing')
    t = t.replace(anchor, anchor + 'import com.particlesdevs.photoncamera.m9.M9SceneExposureDiagnostic;\n', 1)

# Evaluate the signed pressure model at the same actual step-0 decision point used by
# EXPOSUREAUDIT1A. No pair/cap/exposure value is modified by this call.
if 'M9SceneExposureDiagnostic.evaluateStep0' not in t:
    anchor = '''            if (M9Config.isCaptureTest() && step == 0) {
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
    if anchor not in t:
        raise SystemExit('SCENEEXPOSURE1A: step-0 feedback audit anchor missing')
    ins = anchor + '''            if (M9Config.isCaptureTest() && step == 0) {
                M9SceneExposureDiagnostic.evaluateStep0(
                        step, m9PreviewEnergyIsoSeconds, m9FeedbackRotationDegrees);
            }
'''
    t = t.replace(anchor, ins, 1)
write(iso_rel, t)

# Persist beside the exact exposure ledger. This is a recommendation only.
meta_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java'
m = read(meta_rel)
if 'root.put("m9SceneExposureDiagnostic"' not in m:
    anchor = '            root.put("m9ExposureAudit", M9ExposureAudit.snapshotJson(root));\n'
    if anchor not in m:
        raise SystemExit('SCENEEXPOSURE1A: metadata exposure-audit anchor missing')
    m = m.replace(anchor, anchor + '            root.put("m9SceneExposureDiagnostic", M9SceneExposureDiagnostic.snapshotJson());\n', 1)
write(meta_rel, m)

# Distinct build identity only; frozen renderer/exposure arithmetic is unchanged.
gradle_rel = 'app/build.gradle'
g = read(gradle_rel)
old_v = "versionName '1.33-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1a'"
new_v = "versionName '1.34-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1a'"
if new_v not in g:
    if old_v not in g:
        raise SystemExit('SCENEEXPOSURE1A: expected EXPOSUREAUDIT1A versionName missing')
    g = g.replace(old_v, new_v, 1)
write(gradle_rel, g)

back_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java'
b = read(back_rel)
old_b = '1.33-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1a'
new_b = '1.34-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1a'
if new_b not in b:
    if old_b not in b:
        raise SystemExit('SCENEEXPOSURE1A: build identity anchor missing')
    b = b.replace(old_b, new_b, 1)
write(back_rel, b)

print('M9Cam SCENEEXPOSURE1A applied: signed exposure recommendation is diagnostic-only; live FB1/Photon/motion allocation unchanged')
