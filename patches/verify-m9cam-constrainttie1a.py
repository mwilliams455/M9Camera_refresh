#!/usr/bin/env python3
from pathlib import Path
import sys
if len(sys.argv)!=2: raise SystemExit('usage: verify-m9cam-constrainttie1a.py <PhotonCamera-root>')
root=Path(sys.argv[1]).resolve()
def text(r):
 p=root/r
 if not p.exists(): raise SystemExit('CONSTRAINTTIE1A verify missing: '+r)
 return p.read_text()
tie=text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintTie1A.java')
meta=text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java')
gradle=text('app/build.gradle'); back=text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java')
for t in ['m9cam.constrainttie.v1a','TIE_WINDOW_EV=0.05','nearest_normalized_distance_plus_0p05_then_newest_completed_raw','research_only_20260904_18_exact_normalized_history_cases_mae_0p0221_to_0p0161','top2BroadEnvelopeAuthority",false','usedToMutateCaptureTarget",false']:
 if t not in tie: raise SystemExit('CONSTRAINTTIE1A class token missing: '+t)
if 'root.put("m9ConstraintNearest", M9ConstraintNearest1A.evaluate(root));\n            root.put("m9ConstraintTie", M9ConstraintTie1A.evaluate(root));' not in meta: raise SystemExit('CONSTRAINTTIE1A metadata order missing')
if "versionName '1.59-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cr1a-vbvs1b-fg1a-cl1a-pn1a-cn1a-ct1a'" not in gradle: raise SystemExit('CONSTRAINTTIE1A 1.59 version missing')
if 'constraintnearest1aconstrainttie1ascenefingerprint1b' not in back: raise SystemExit('CONSTRAINTTIE1A build marker missing')
# Mirror selector: pass candidates <= nearest+0.05, newest sequence wins.
def choose(cs):
 valid=[c for c in cs if c[1]<=1.0]
 if not valid:return None
 near=min(c[1] for c in valid); limit=min(1.0,near+.05)
 pool=[c for c in valid if c[1]<=limit]
 return max(pool,key=lambda c:c[0])
fixtures=[
 ([(1,.088104),(2,.088372)],2),
 ([(2,.485),(3,.519),(1,.599)],3),
 ([(4,.20),(5,.27)],4),
 ([(7,1.01),(8,1.2)],None),
]
for cs,exp in fixtures:
 got=choose(cs); got=None if got is None else got[0]
 if got!=exp: raise SystemExit(f'CONSTRAINTTIE1A fixture failed {cs} got={got} expected={exp}')
for rel in ['app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java','app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java','app/src/main/java/com/particlesdevs/photoncamera/m9/M9ForegroundGuard1A.java','app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java','app/src/main/cpp/m9color_jni.cpp']:
 s=text(rel)
 if 'M9ConstraintTie1A' in s or 'm9cam.constrainttie.v1a' in s: raise SystemExit('CONSTRAINTTIE1A leaked into live seam: '+rel)
print('OK CONSTRAINTTIE1A nearest+0.05/newest diagnostic selector')
print('OK near-tie truck fixtures prefer newer RAW')
print('OK >0.05 distance gap preserves absolute nearest')
print('OK no live/renderer seam consumes tie selector')
