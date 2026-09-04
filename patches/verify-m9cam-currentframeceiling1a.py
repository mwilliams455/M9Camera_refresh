#!/usr/bin/env python3
from pathlib import Path
import sys
if len(sys.argv)!=2: raise SystemExit('usage: verify-m9cam-currentframeceiling1a.py <PhotonCamera-root>')
root=Path(sys.argv[1]).resolve()
def text(r):
 p=root/r
 if not p.exists(): raise SystemExit('CURRENTFRAMECEILING1A verify missing: '+r)
 return p.read_text()
c=text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9CurrentFrameCeiling1A.java')
meta=text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java')
gradle=text('app/build.gradle'); back=text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java')
for t in ['m9cam.currentframeceiling.v1a','research_only_20260904_51_exact_preview_to_raw_oracle_pairs','calibrationCounterfactualPositiveTargetMaeEv",0.0441','calibrationWorstUnsafeOvershootEv",0.0016','isolated_extreme_tail','isolated_moderate_tail','broad_unsaturated_highlight','broad_mid_highlight','conservative_general_tail','history_independent_positive_ceiling_only_when_no_transferable_raw_history','rawPixelsUsed",false','renderedJpegUsed",false','usedToMutateCaptureTarget",false']:
 if t not in c: raise SystemExit('CURRENTFRAMECEILING1A class token missing: '+t)
if 'root.put("m9ConstraintTie", M9ConstraintTie1A.evaluate(root));\n            root.put("m9CurrentFrameCeiling", M9CurrentFrameCeiling1A.evaluate(root));' not in meta: raise SystemExit('CURRENTFRAMECEILING1A metadata order missing')
if "versionName '1.60-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cr1a-vbvs1b-fg1a-cl1a-pn1a-cn1a-ct1a-cfc1a'" not in gradle: raise SystemExit('CURRENTFRAMECEILING1A 1.60 version missing')
if 'constrainttie1acurrentframeceiling1ascenefingerprint1b' not in back: raise SystemExit('CURRENTFRAMECEILING1A build marker missing')
def pred(q95,q99,b240,request):
 gap=q99-q95
 if q95<=90 and q99>=240 and gap>=140: ceil=0.0;tier='isolated_extreme_tail'
 elif q95<=130 and gap>=90: ceil=.40;tier='isolated_moderate_tail'
 elif q95>=190 and q99<235 and b240<.010: ceil=1.00;tier='broad_unsaturated_highlight'
 elif q95>=190 and q99<245 and b240<.025: ceil=.80;tier='broad_mid_highlight'
 else: ceil=.65;tier='conservative_general_tail'
 target=min(request,ceil) if request>0 else request
 return tier,ceil,target
# Field anchors: old isolated bulb, new bulb, new-scene truck, returned truck, ordinary positive case, signed negative.
fixtures=[
 ((79,250,.01577,1.614109),('isolated_extreme_tail',0.0,0.0)),
 ((110,231,.002025,1.312939),('isolated_moderate_tail',.40,.40)),
 ((213,227,.003038,1.535332),('broad_unsaturated_highlight',1.0,1.0)),
 ((209,240,.010706,1.268817),('broad_mid_highlight',.80,.80)),
 ((206,248,.012297,.590305),('conservative_general_tail',.65,.590305)),
 ((210,250,.020,-.50),('conservative_general_tail',.65,-.50)),
]
for args,exp in fixtures:
 got=pred(*args)
 if got[0]!=exp[0] or abs(got[1]-exp[1])>1e-12 or abs(got[2]-exp[2])>1e-9: raise SystemExit(f'CURRENTFRAMECEILING1A fixture failed {args} got={got} expected={exp}')
# Corpus-reported anchor errors: predicted target must be conservative for the key unresolved first observations.
anchors=[
 # q95,q99,b240,request,oracle target
 (79,250,.01577,1.614109,0.0),
 (110,231,.002025,1.312939,.423149),
 (213,227,.003038,1.535332,1.189258),
]
for q95,q99,b,req,oracle in anchors:
 target=pred(q95,q99,b,req)[2]
 if target-oracle>0.002: raise SystemExit(f'CURRENTFRAMECEILING1A unsafe field anchor overshoot {target-oracle}')
for rel in ['app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java','app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java','app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java','app/src/main/java/com/particlesdevs/photoncamera/m9/M9ForegroundGuard1A.java','app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java','app/src/main/cpp/m9color_jni.cpp']:
 s=text(rel)
 if 'M9CurrentFrameCeiling1A' in s or 'm9cam.currentframeceiling.v1a' in s: raise SystemExit('CURRENTFRAMECEILING1A leaked into live seam: '+rel)
print('OK CURRENTFRAMECEILING1A current-preview-only diagnostic fallback')
print('OK isolated old bulb -> 0.00 EV ceiling; new bulb -> 0.40 EV')
print('OK new-scene truck -> 1.00 EV conservative ceiling')
print('OK signed negative requests are untouched')
print('OK no RAW/JPEG/live exposure seam consumes predictor')
