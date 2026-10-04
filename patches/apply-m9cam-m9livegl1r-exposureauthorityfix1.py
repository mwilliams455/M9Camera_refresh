#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply-m9cam-m9livegl1r-exposureauthorityfix1.py <PhotonCamera-root>")
root = Path(sys.argv[1]).resolve()
tone_path = root / "app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LiveToneModel1F.java"
if not tone_path.exists():
    raise SystemExit("GL1R FIX1 missing tone model: " + str(tone_path))

t = tone_path.read_text()

def one(old, new, label):
    global t
    n = t.count(old)
    if n != 1:
        raise SystemExit(f"GL1R FIX1 {label}: expected 1 anchor, found {n}")
    t = t.replace(old, new, 1)

one(
'''        final double sceneKey1R = clamp01(sceneKey1I + 0.55 * positivePlacementStress1R);
''',
'''        // M9LIVEGL1R_FIX1_EXPOSUREAUTHORITY1A
        // Exposure-domain telemetry is diagnostic only. The photographer's GL1B
        // exposure choice must never be counteracted by live tone classification.
        final double sceneKey1R = sceneKey1I;
''',
"scene key authority")

one(
'''        double gainEv = -0.30 - 2.02 * sceneKey1R;
''',
'''        double gainEv = -0.30 - 2.02 * sceneKey1I;
''',
"gain authority")

one(
'''        double gamma = 1.12 + 0.26 * sceneKey1R;
''',
'''        double gamma = 1.12 + 0.26 * sceneKey1I;
''',
"gamma authority")

one(
'''        // Do not let a positive intended exposure deactivate the pair curve merely
        // because the virtually exposed median became high. That was the 15U video
        // failure mode: GL1B opened the viewfinder while the RAW still path retained
        // much denser M9 lower/mid-tone placement.
        double shoulder = Math.max(basePairCurveStrength1Q,
                clamp01(positivePlacementStress1R * (0.65 + 0.35 * spreadKey1Q)));
''',
'''        // M9LIVEGL1R_FIX1_EXPOSUREAUTHORITY1A
        // GL1Q strength remains a property of the observed scene structure only.
        // Positive/negative intended exposure is not an automatic tone correction.
        double shoulder = basePairCurveStrength1Q;
''',
"pair curve authority")

one(
'''            o.put("gl1rPolicy", "preview_YUV_plus_GL1B_intended_exposure_only_no_capture_or_JPEG_feedback");
''',
'''            o.put("gl1rPolicy", "preview_YUV_plus_GL1B_intended_exposure_telemetry_only_no_tone_feedback");
            o.put("gl1rExposureDomainAffectsGain", false);
            o.put("gl1rExposureDomainAffectsGamma", false);
            o.put("gl1rExposureDomainAffectsPairCurve", false);
            o.put("gl1rExposureAuthority", "GL1B_user_intent_authoritative_no_compensation");
            o.put("gl1rFix", "M9LIVEGL1R_FIX1_EXPOSUREAUTHORITY1A");
''',
"diagnostic contract")

tone_path.write_text(t)
print("M9LIVEGL1R_FIX1_EXPOSUREAUTHORITY1A applied")
print(" - GL1R exposure-domain stats retained for diagnostics")
print(" - GL1R no longer changes scene key, gain, gamma, or pair-curve strength")
print(" - GL1B user exposure remains authoritative")
