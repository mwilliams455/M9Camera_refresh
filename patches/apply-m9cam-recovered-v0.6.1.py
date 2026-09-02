#!/usr/bin/env python3
from pathlib import Path
import re, sys
if len(sys.argv)!=2: raise SystemExit('usage: apply-m9cam-recovered-v0.6.1.py <PhotonCamera-root>')
p=Path(sys.argv[1])/'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java'
t=p.read_text()
if 'MOTION_ACTIVATE = 0.60' in t:t=t.replace('MOTION_ACTIVATE = 0.60','MOTION_ACTIVATE = 0.52',1)
if 'PERSISTENCE_PEAK_SCALE' not in t:
    t=t.replace('    public static final double MOTION_ACTIVATE = 0.52;\n','    public static final double MOTION_ACTIVATE = 0.52;\n    public static final double PERSISTENCE_PEAK_SCALE = 0.96;\n    public static final double PERSISTENCE_MAX_BOOST = 0.08;\n',1)
old='        final double score = M9SubjectMotionAnalyzer.getCaptureMotionScore();\n'
new='''        final double rawScore = M9SubjectMotionAnalyzer.getCaptureMotionScore();
        final double recentPeak = M9SubjectMotionAnalyzer.getRecentPeakScore();
        final double persistenceScore = Math.min(recentPeak * PERSISTENCE_PEAK_SCALE, rawScore + PERSISTENCE_MAX_BOOST);
        final double score = Math.max(rawScore, persistenceScore);
'''
if old in t:t=t.replace(old,new,1)
t=t.replace('"m9cam.modern.exposure.v1"','"m9cam.modern.exposure.v2"',1)
old='            o.put("captureMotionScore", score);\n'
new='''            o.put("rawCaptureMotionScore", rawScore);
            o.put("recentPeakScore", recentPeak);
            o.put("persistencePeakScale", PERSISTENCE_PEAK_SCALE);
            o.put("persistenceMaxBoost", PERSISTENCE_MAX_BOOST);
            o.put("persistenceScore", persistenceScore);
            o.put("captureMotionScore", score);
'''
if old in t:t=t.replace(old,new,1)
for required in ['MOTION_ACTIVATE = 0.52','PERSISTENCE_PEAK_SCALE = 0.96','PERSISTENCE_MAX_BOOST = 0.08','ANALOG_HEADROOM_FRACTION = 0.95']:
    if required not in t: raise SystemExit('v0.6.1 recovery tune failed: '+required)
p.write_text(t)

# Recover the historical v0.6.1 IsoExpoSelector source shape consumed by the
# cumulative v0.7N FB1 overlay. The recovered v0.6 foundation used the exact
# same adjustCaps arguments on one line; accepted v0.6.1 had the call wrapped.
# This is source-shape normalization only; arithmetic/order/predicates are unchanged.
iso = Path(sys.argv[1]) / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java'
i = iso.read_text()
inline = """        if (M9Config.isM9Modern()
                && PhotonCamera.getSettings().selectedMode == CameraMode.PHOTO
                && !useTripod) {
            M9ModernExposurePolicy.Decision m9Decision = M9ModernExposurePolicy.adjustCaps(pair.exposure, pair.iso, pair.isoanalog, capStart, capEnd);
            capStart = m9Decision.capStartNs; capEnd = m9Decision.capEndNs;
        }
"""
canonical = """        if (M9Config.isM9Modern()
                && PhotonCamera.getSettings().selectedMode == CameraMode.PHOTO
                && !useTripod) {
            M9ModernExposurePolicy.Decision m9Decision = M9ModernExposurePolicy.adjustCaps(
                    pair.exposure, pair.iso, pair.isoanalog, capStart, capEnd);
            capStart = m9Decision.capStartNs; capEnd = m9Decision.capEndNs;
        }
"""
anchor = """        if (M9Config.isM9Modern()
                && PhotonCamera.getSettings().selectedMode == CameraMode.PHOTO
                && !useTripod) {
            M9ModernExposurePolicy.Decision m9Decision = M9ModernExposurePolicy.adjustCaps(
"""
if inline in i:
    i = i.replace(inline, canonical, 1)
    iso.write_text(i)
elif anchor in i:
    pass
else:
    raise SystemExit('v0.6.1 recovery source-shape failed: M9Modern pre-curve policy seam not recognized')


# Recover the diagnostics type contract used by the current Photon shutter curve.
# PhotonCamera dev declares CAP_RAMP_STOPS as double. The reconstructed foundation
# accidentally retained an early int-only diagnostics signature; that is diagnostics
# storage only, but it makes the otherwise-correct call fail Java compilation.
# Keep the value exact by promoting the diagnostics field/parameter to double rather
# than casting/truncating at the exposure call site. No exposure arithmetic changes.
diag = Path(sys.argv[1]) / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ExposureDiagnostics.java'
d = diag.read_text()
if 'private static int curveRampStops;' in d:
    d = d.replace('private static int curveRampStops;', 'private static double curveRampStops;', 1)
if 'long capStart,long capEnd,int rampStops)' in d:
    d = d.replace('long capStart,long capEnd,int rampStops)', 'long capStart,long capEnd,double rampStops)', 1)
if 'private static double curveRampStops;' not in d or 'long capStart,long capEnd,double rampStops)' not in d:
    raise SystemExit('v0.6.1 recovery diagnostics type failed: expected double curveRampStops/recordCurveInput rampStops')
diag.write_text(d)

# Cross-check the caller contract before the cumulative overlay. This catches future
# upstream type drift at the recovery boundary rather than during Gradle compilation.
iso_type_text = iso.read_text()
if not re.search(r'private\s+static\s+final\s+double\s+CAP_RAMP_STOPS\s*=', iso_type_text):
    raise SystemExit('v0.6.1 recovery diagnostics type failed: Photon CAP_RAMP_STOPS is no longer double')

# Recover the historical v0.6.1 metadata-writer source shape consumed by the
# cumulative v0.7 renderer/LUMA/METAFREEZE overlays. The reconstructed recovery
# foundation kept the same persistence operations on one compact line, while the
# accepted v0.6.1 source used the formatted block below. This is source-shape
# normalization only: SAF-first write, java.nio fallback, UTF-8 bytes, flush,
# logging and return semantics are unchanged.
meta = Path(sys.argv[1]) / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java'
m = meta.read_text()
compact_meta_output = """            OutputStream safOut=SimpleStorageHelper.openOutputStreamByAbsPath(jsonPath.toString());if(safOut!=null){try(OutputStream out=safOut){out.write(root.toString(2).getBytes(StandardCharsets.UTF_8));out.flush();}}else{try(OutputStream out=Files.newOutputStream(jsonPath)){out.write(root.toString(2).getBytes(StandardCharsets.UTF_8));out.flush();}}Log.d(TAG,\"Saved sidecar: \"+jsonPath);return true;"""
canonical_meta_output = """            OutputStream safOut = SimpleStorageHelper.openOutputStreamByAbsPath(jsonPath.toString());
            if (safOut != null) {
                try (OutputStream out = safOut) {
                    out.write(root.toString(2).getBytes(StandardCharsets.UTF_8));
                    out.flush();
                }
            } else {
                try (OutputStream out = Files.newOutputStream(jsonPath)) {
                    out.write(root.toString(2).getBytes(StandardCharsets.UTF_8));
                    out.flush();
                }
            }
            Log.d(TAG, \"Saved sidecar: \" + jsonPath);
            return true;"""
canonical_anchor = '            OutputStream safOut = SimpleStorageHelper.openOutputStreamByAbsPath(jsonPath.toString());\n'
canonical_tail = '            Log.d(TAG, "Saved sidecar: " + jsonPath);\n            return true;'
if compact_meta_output in m:
    m = m.replace(compact_meta_output, canonical_meta_output, 1)
    meta.write_text(m)
elif canonical_anchor in m and canonical_tail in m:
    pass
else:
    raise SystemExit('v0.6.1 recovery source-shape failed: metadata output persistence seam not recognized')

# Recover the historical v0.6.1 build-identity transition consumed by the
# cumulative v0.7 overlay.  The v0.6 foundation deliberately installs
# 0.97-m9modern6; accepted v0.6.1 exposure tune was 0.97-m9modern6p1.
gradle = Path(sys.argv[1]) / 'app/build.gradle'
g = gradle.read_text()
if re.search(r"versionName\s+(['\"])0\.97-m9modern6p1\1", g):
    pass
elif re.search(r"versionName\s+(['\"])0\.97-m9modern6\1", g):
    g, n = re.subn(
        r"versionName\s+(['\"])0\.97-m9modern6\1",
        "versionName '0.97-m9modern6p1'",
        g,
        count=1,
    )
    if n != 1:
        raise SystemExit('v0.6.1 recovery identity failed: could not promote 0.97-m9modern6 -> 0.97-m9modern6p1')
    gradle.write_text(g)
else:
    found = re.findall(r"(?m)^.*versionName.*$", g)
    detail = found[0].strip() if found else '<missing versionName>'
    raise SystemExit('v0.6.1 recovery identity failed: expected 0.97-m9modern6 or 0.97-m9modern6p1; found: ' + detail)

print('M9Modern v0.6.1 accepted tune + historical source/type contracts + 0.97-m9modern6p1 identity restored')
