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

print('M9Modern v0.6.1 accepted tune + 0.97-m9modern6p1 identity restored')
