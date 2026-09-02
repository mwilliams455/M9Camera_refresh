#!/usr/bin/env python3
from pathlib import Path
import sys
if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-exposureaudit1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
checks = {
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ExposureAudit.java': [
        'm9cam.exposureaudit.v1', 'step0_only_preflight_immune', 'motionIsoPenaltyStopsVsFeedbackOnly',
        'camera2RequestVsAllocatorEnergyEv'],
    'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java': [
        'M9ExposureAudit.beginStep0', 'M9ExposureAudit.recordPhotonReferenceStep0',
        'M9ExposureAudit.recordFeedbackStep0', 'M9ExposureAudit.recordMotionCapsStep0',
        'M9ExposureAudit.recordFinalNormalizedStep0', 'M9ExposureAudit.recordCaptureRequestStep0'],
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java': [
        'root.put("m9ExposureAudit"'],
    'app/build.gradle': ['1.33-m9modern7r38luma24fb1primary25perf3i'],
}
for rel, needles in checks.items():
    p = root / rel
    if not p.exists(): raise SystemExit('FAIL missing ' + rel)
    t = p.read_text()
    for n in needles:
        if n not in t: raise SystemExit(f'FAIL {n!r} missing from {rel}')
print('PASS EXPOSUREAUDIT1A source contract')
