#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: verify-m9cam-m9livegl1r-exposureauthorityfix1.py <PhotonCamera-root>")
root = Path(sys.argv[1]).resolve()
tone = root / "app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LiveToneModel1F.java"
cf = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/CameraFragment.java"
an = root / "app/src/main/java/com/particlesdevs/photoncamera/m9/M9SubjectMotionAnalyzer.java"
shader = root / "app/src/main/assets/shaders/preview/main_fs.glsl"
for p in (tone, cf, an, shader):
    if not p.exists():
        raise SystemExit("GL1R FIX1 missing " + str(p))

t=tone.read_text(); c=cf.read_text(); a=an.read_text(); s=shader.read_text()
checks=[
    ("fix marker", "M9LIVEGL1R_FIX1_EXPOSUREAUTHORITY1A" in t),
    ("GL1R telemetry retained", "fillLiveToneStats1R(mM9LiveExposureScale1R" in c and "m9cam.livepreview.gl1r.exposuredomain1a" in a),
    ("placement stress retained diagnostic", "positivePlacementStress1R" in t and "gl1rPositivePlacementStress" in t),
    ("scene key not exposure corrected", "final double sceneKey1R = sceneKey1I;" in t),
    ("gain uses original scene key", "double gainEv = -0.30 - 2.02 * sceneKey1I;" in t),
    ("gamma uses original scene key", "double gamma = 1.12 + 0.26 * sceneKey1I;" in t),
    ("pair curve uses scene only", "double shoulder = basePairCurveStrength1Q;" in t),
    ("diagnostic-only gain flag", 'o.put("gl1rExposureDomainAffectsGain", false)' in t),
    ("diagnostic-only gamma flag", 'o.put("gl1rExposureDomainAffectsGamma", false)' in t),
    ("diagnostic-only curve flag", 'o.put("gl1rExposureDomainAffectsPairCurve", false)' in t),
    ("GL1B shader exposure retained", "linear *= uM9ExposureScale1B" in s),
    ("GL1Q pair curve retained", "M9LIVEGL1Q_PAIRCURVE1A" in s and "m9PairCurve1Q" in s),
]
for label,ok in checks:
    print(("OK   " if ok else "FAIL ")+label)
    if not ok: raise SystemExit("GL1R FIX1 contract failure: "+label)

for forbidden in (
    "sceneKey1I + 0.55 * positivePlacementStress1R",
    "Math.max(basePairCurveStrength1Q,\n                clamp01(positivePlacementStress1R",
):
    if forbidden in t:
        raise SystemExit("GL1R FIX1 stale exposure compensation active: "+forbidden)

print("M9LIVEGL1R_FIX1_EXPOSUREAUTHORITY1A VERIFY PASS")
