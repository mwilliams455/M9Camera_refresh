#!/usr/bin/env python3
from pathlib import Path
import math, re, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-m10r-mfmtest1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()

def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit('M10RMFMTEST1A verify missing: ' + rel)
    return p.read_text()

def ok(name, cond):
    if not cond:
        raise SystemExit('FAIL ' + name)
    print('OK  ', name)

gradle = read('app/build.gradle')
analyzer = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9SubjectMotionAnalyzer.java')
mfm = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9M10rMfmTest1A.java')
iso = read('app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java')
meta = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java')
renderer = read('app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java')

ok('version 1.61 M10R MFM test',
   "versionName '1.61-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cr1a-vbvs1b-fg1a-cl1a-pn1a-cn1a-ct1a-cfc1a-m10rmfm1a'" in gradle)
ok('16x22 preview grid schema', 'm9cam.previewluma.m10rgrid.v1a' in analyzer)
ok('16x22 grid emitted', 'o.put("m10rAeGrid16x22"' in analyzer)
ok('grid is display oriented', 'orientForDisplay(sensorFrame, rotation)' in analyzer)
ok('M10R test schema', 'm9cam.m10r.mfmtest.v1a' in mfm)
ok('explicitly not numerical parity', 'm10rNumericalParity' in mfm and 'exact13FeatureGeneratorApplied' in mfm)
ok('M10R 4x6 / 24 regions', 'REG_R = 4' in mfm and 'REG_C = 6' in mfm and 'double[] out = new double[24]' in mfm)
ok('CA9 reference 524 deliberately not imported', 'leicaReference524UsedForLiveCorrection' in mfm)
ok('M10R live seam active', 'M9M10rMfmTest1A.evaluateLiveFeedback' in iso)
ok('signed M10R correction reaches allocator', 'Math.abs(m9Feedback.appliedEv) > 1.0e-9' in iso)
ok('legacy LUMA2.4 kept counterfactual', 'legacyLuma24RecommendedEv' in mfm)
ok('manual EV bypass retained', 'Math.abs(PhotonCamera.getSettings().exposureCompensation) < 1.0e-9' in iso)
ok('manual ISO/shutter bypass retained',
   'getCurrentExposureValue() == 0' in iso and 'getCurrentISOValue() == 0' in iso)
ok('metadata publishes M10R test', 'root.put("m9M10rMfmTest"' in meta)
ok('positive bound 0.75', 'MAX_POSITIVE_EV = 0.75' in mfm)
ok('negative bound 0.50', 'MAX_NEGATIVE_EV = 0.50' in mfm)
ok('0.08 deadband', 'DEAD_BAND_EV = 0.08' in mfm)
ok('row/column/block asymmetry proxy present',
   'edgeVsInnerEv' in mfm and 'upperVsLowerEv' in mfm and 'positiveGeometryConfidence' in mfm)
ok('renderer JPEG quality frozen', 'public static final int JPEG_QUALITY = 95;' in renderer)
ok('TC20 frozen base target still present', 'private static final double METER_TARGET = 0.107 * (8192.0 / 10000.0);' in renderer)
ok('renderer does not depend on M10R test class', 'M9M10rMfmTest1A' not in renderer)

# Recover exact firmware integral mask literal and verify size/sum.
mm = re.search(r'INTEGRAL_MASK\s*=\s*new int\[\]\s*\{(.*?)\};', mfm, re.S)
ok('integral mask literal found', mm is not None)
vals = [int(x) for x in re.findall(r'-?\d+', mm.group(1))]
ok('integral mask has 352 entries', len(vals) == 352)
ok('integral mask exact sum 14160', sum(vals) == 14160)
ok('integral mask only recovered weight alphabet',
   set(vals).issubset({0,10,20,30,40,50,60,80,100}))

# Host-side behavioral smoke tests for the same research equations.
MASK = vals
def smooth(x, lo, hi):
    if hi <= lo: return 1.0 if x >= hi else 0.0
    t = max(0.0, min(1.0, (x-lo)/(hi-lo)))
    return t*t*(3.0-2.0*t)
def score(cell):
    integral = sum(v*w for v,w in zip(cell,MASK))/sum(MASK)
    regs=[]
    for rr in range(4):
        r0=rr*16//4; r1=(rr+1)*16//4
        for cc in range(6):
            c0=cc*22//6; c1=(cc+1)*22//6
            q=[cell[r*22+c] for r in range(r0,r1) for c in range(c0,c1)]
            regs.append(sum(q)/len(q))
    s=sorted(regs)
    median=.5*(s[11]+s[12])
    low=sum(s[:6])/6; high=sum(s[18:])/6
    spread=math.log2(max(high,1e-6)/max(low,1e-6))
    def rect(r0,r1,c0,c1):
        q=[regs[r*6+c] for r in range(r0,r1) for c in range(c0,c1)]
        return sum(q)/len(q)
    center=rect(1,3,1,5); lower=rect(2,4,0,6); upper=rect(0,1,0,6)
    edge=[regs[r*6+c] for r in range(4) for c in range(6) if r in (0,3) or c in (0,5)]
    inner=[regs[r*6+c] for r in range(4) for c in range(6) if not (r in (0,3) or c in (0,5))]
    edgey=sum(edge)/len(edge); innery=sum(inner)/len(inner)
    im=math.log2(max(integral,1e-6)/max(median,1e-6))
    ic=math.log2(max(integral,1e-6)/max(center,1e-6))
    il=math.log2(max(integral,1e-6)/max(lower,1e-6))
    edgeinner=math.log2(max(edgey,1e-6)/max(innery,1e-6))
    upperlower=math.log2(max(upper,1e-6)/max(lower,1e-6))
    centerover=math.log2(max(center,1e-6)/max(integral,1e-6))
    inneredge=math.log2(max(innery,1e-6)/max(edgey,1e-6))
    br=sum(v >= median*2**0.5 for v in regs)/24.0
    rawpos=max(0.0,.55*im+.25*ic+.20*il)
    posgeo=max(smooth(edgeinner,.05,.65),smooth(upperlower,.15,1.0))
    pos=rawpos*smooth(spread,.7,2.2)*smooth(br,.08,.30)*posgeo
    neggeo=max(smooth(inneredge,.05,.65),smooth(centerover,.15,.65))
    neg=-.70*max(0.0,centerover-.10)*smooth(spread,.45,1.6)*neggeo
    cand=max(-.50,min(.75,pos+neg))
    if abs(cand)<.08: cand=0.0
    return cand

uniform=[100.0]*352
ok('uniform synthetic scene stays neutral', abs(score(uniform)) < 1e-12)

back=[55.0]*352
for r in range(0,8):
    for c in range(0,7):
        back[r*22+c]=240.0
for r in range(5,15):
    for c in range(7,19):
        back[r*22+c]=45.0
ok('synthetic edge/top backlight requests positive EV', score(back) > 0.08)

darkobj=[150.0]*352
for r in range(9,13):
    for c in range(9,13):
        darkobj[r*22+c]=20.0
ok('isolated dark object control stays neutral', abs(score(darkobj)) < 0.08)

print('PASS M10RMFMTEST1A verifier')
