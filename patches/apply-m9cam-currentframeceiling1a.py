#!/usr/bin/env python3
from pathlib import Path
import hashlib, sys
if len(sys.argv)!=2: raise SystemExit('usage: apply-m9cam-currentframeceiling1a.py <PhotonCamera-root>')
root=Path(sys.argv[1]).resolve()
if not (root/'app').is_dir(): raise SystemExit(f'not a PhotonCamera root: {root}')
def read(r):
 p=root/r
 if not p.exists(): raise SystemExit('CURRENTFRAMECEILING1A missing expected file: '+r)
 return p.read_text()
def sha(r): return hashlib.sha256((root/r).read_bytes()).hexdigest()
meta_rel='app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java'; gradle_rel='app/build.gradle'; back_rel='app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java'
meta=read(meta_rel); gradle=read(gradle_rel); back=read(back_rel)
expected="versionName '1.59-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cr1a-vbvs1b-fg1a-cl1a-pn1a-cn1a-ct1a'"
if expected not in gradle: raise SystemExit('CURRENTFRAMECEILING1A expected 1.59 version missing')
frozen=['app/src/main/java/com/particlesdevs/photoncamera/m9/M9NegativeFeedback1A.java','app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintLocal1A.java','app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintNearest1A.java','app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintTie1A.java','app/src/main/java/com/particlesdevs/photoncamera/m9/M9ForegroundGuard1A.java','app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintRef1A.java','app/src/main/java/com/particlesdevs/photoncamera/m9/M9VirtualBv1A.java','app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintSplit1A.java','app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java','app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java','app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java','app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java','app/src/main/cpp/m9color_jni.cpp']
before={r:sha(r) for r in frozen}
rel='app/src/main/java/com/particlesdevs/photoncamera/m9/M9CurrentFrameCeiling1A.java'; p=root/rel
if p.exists(): raise SystemExit('CURRENTFRAMECEILING1A target already exists')
p.write_text(r'''package com.particlesdevs.photoncamera.m9;
import org.json.JSONObject;
/** Current-preview-only positive ceiling research. Never reads RAW or rendered JPEG. */
public final class M9CurrentFrameCeiling1A {
 public static final String SCHEMA="m9cam.currentframeceiling.v1a";
 private M9CurrentFrameCeiling1A(){}
 public static JSONObject evaluate(JSONObject root){
  JSONObject o=contract();
  try{
   JSONObject scene=root!=null?root.optJSONObject("m9SceneExposureDiagnostic"):null;
   JSONObject in=scene!=null?scene.optJSONObject("inputs"):null;
   JSONObject guard=root!=null?root.optJSONObject("m9ForegroundGuard"):null;
   JSONObject tie=root!=null?root.optJSONObject("m9ConstraintTie"):null;
   if(in==null||guard==null) return invalid(o,"current_preview_or_guard_missing");
   double q95=in.optDouble("globalQ95",Double.NaN), q99=in.optDouble("globalQ99",Double.NaN), b240=in.optDouble("brightFractionGE240",Double.NaN);
   double med=in.optDouble("globalMedian",Double.NaN), dark=in.optDouble("darkFractionLE64",Double.NaN);
   double request=guard.optDouble("preSensorGuardedTargetFromPhotonEv",Double.NaN);
   if(!finite(q95)||!finite(q99)||!finite(b240)||!finite(request)) return invalid(o,"required_preview_tail_inputs_missing");
   double gap=q99-q95, ceiling; String tier;
   if(q95<=90.0 && q99>=240.0 && gap>=140.0){ceiling=0.0;tier="isolated_extreme_tail";}
   else if(q95<=130.0 && gap>=90.0){ceiling=0.40;tier="isolated_moderate_tail";}
   else if(q95>=190.0 && q99<235.0 && b240<0.010){ceiling=1.00;tier="broad_unsaturated_highlight";}
   else if(q95>=190.0 && q99<245.0 && b240<0.025){ceiling=0.80;tier="broad_mid_highlight";}
   else {ceiling=0.65;tier="conservative_general_tail";}
   boolean historyAvailable=tie!=null&&tie.optBoolean("historyConstraintAvailable",false);
   double target=request>0.0?Math.min(request,ceiling):request;
   double magnitude=Math.max(0.0,request-target);
   o.put("valid",true);o.put("tier",tier);put(o,"globalMedian",med);put(o,"globalQ95",q95);put(o,"globalQ99",q99);put(o,"q99MinusQ95",gap);put(o,"darkFractionLE64",dark);put(o,"brightFractionGE240",b240);put(o,"preSensorGuardedTargetFromPhotonEv",request);put(o,"currentFramePositiveCeilingFromPhotonEv",ceiling);put(o,"counterfactualTargetFromPhotonEv",target);put(o,"bindingMagnitudeEv",magnitude);o.put("wouldBindPositiveRequest",magnitude>1e-9);o.put("transferableHistoryAvailable",historyAvailable);o.put("fallbackNeededForNoTransferableHistory",!historyAvailable);o.put("promotionRoleCandidate","history_independent_positive_ceiling_only_when_no_transferable_raw_history");o.put("reason","preview_tail_tier_recorded_no_live_exposure_change");
  }catch(Throwable t){try{invalid(o,"currentframeceiling1a_exception");o.put("error",t.toString());}catch(Exception ignored){}}
  return o;
 }
 private static JSONObject contract(){JSONObject o=new JSONObject();try{o.put("schema",SCHEMA);o.put("mode","diagnostic_only_no_exposure_mutation");o.put("liveEligible",false);o.put("usedToMutateCaptureTarget",false);o.put("historyIndependent",true);o.put("rawPixelsUsed",false);o.put("renderedJpegUsed",false);o.put("previewInputs","global_q95_global_q99_bright240_plus_context_only");o.put("calibration","research_only_20260904_51_exact_preview_to_raw_oracle_pairs");o.put("calibrationCounterfactualPositiveTargetMaeEv",0.0441);o.put("calibrationWorstUnsafeOvershootEv",0.0016);o.put("calibrationWorstConservativeUndershootEv",0.190);o.put("tierRule","q95_q99_tail_support_conservative_piecewise_v1a");o.put("negativeRequestRule","positive_current_frame_ceiling_never_brightens_or_changes_nonpositive_request");}catch(Exception ignored){}return o;}
 private static JSONObject invalid(JSONObject o,String r){try{o.put("valid",false);o.put("reason",r);o.put("liveEligible",false);o.put("usedToMutateCaptureTarget",false);}catch(Exception ignored){}return o;}
 private static void put(JSONObject o,String k,double v){try{o.put(k,finite(v)?v:JSONObject.NULL);}catch(Exception ignored){}}
 private static boolean finite(double v){return !Double.isNaN(v)&&!Double.isInfinite(v);}
}
''')
anchor='''            root.put("m9ConstraintTie", M9ConstraintTie1A.evaluate(root));\n            root.put("m9BacklightDiagnostic", M9BacklightDiagnostic.snapshotJson(root));\n'''
repl='''            root.put("m9ConstraintTie", M9ConstraintTie1A.evaluate(root));\n            root.put("m9CurrentFrameCeiling", M9CurrentFrameCeiling1A.evaluate(root));\n            root.put("m9BacklightDiagnostic", M9BacklightDiagnostic.snapshotJson(root));\n'''
if anchor not in meta: raise SystemExit('CURRENTFRAMECEILING1A metadata anchor missing')
(root/meta_rel).write_text(meta.replace(anchor,repl,1))
(root/gradle_rel).write_text(gradle.replace(expected,"versionName '1.60-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cr1a-vbvs1b-fg1a-cl1a-pn1a-cn1a-ct1a-cfc1a'",1))
marker='constraintnearest1aconstrainttie1ascenefingerprint1b'; replm='constraintnearest1aconstrainttie1acurrentframeceiling1ascenefingerprint1b'
if marker not in back: raise SystemExit('CURRENTFRAMECEILING1A marker anchor missing')
back=back.replace(marker,replm,1)
if '1.59-' not in back: raise SystemExit('CURRENTFRAMECEILING1A backlight version anchor missing')
(root/back_rel).write_text(back.replace('1.59-','1.60-',1))
for r,h in before.items():
 if sha(r)!=h: raise SystemExit('CURRENTFRAMECEILING1A frozen seam changed: '+r)
print('M9Cam CURRENTFRAMECEILING1A current-preview fallback diagnostic applied')
print(' - history independent; no RAW/JPEG pixels used')
print(' - 5 conservative preview-tail tiers calibrated on 51 exact oracle pairs')
print(' - intended only as no-transferable-history positive-ceiling candidate')
print(' - negative/nonpositive signed requests remain untouched')
print(' - no Camera2, allocator, history matcher, guard, renderer, JPEG or DNG mutation')
