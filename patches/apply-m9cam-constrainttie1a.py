#!/usr/bin/env python3
from pathlib import Path
import hashlib, sys
if len(sys.argv) != 2: raise SystemExit('usage: apply-m9cam-constrainttie1a.py <PhotonCamera-root>')
root=Path(sys.argv[1]).resolve()
if not (root/'app').is_dir(): raise SystemExit(f'not a PhotonCamera root: {root}')
def read(r):
 p=root/r
 if not p.exists(): raise SystemExit(f'CONSTRAINTTIE1A missing expected file: {r}')
 return p.read_text()
def sha(r): return hashlib.sha256((root/r).read_bytes()).hexdigest()
meta_rel='app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java'
local_rel='app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintLocal1A.java'
gradle_rel='app/build.gradle'; back_rel='app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java'
meta=read(meta_rel); local=read(local_rel); gradle=read(gradle_rel); back=read(back_rel)
expected="versionName '1.58-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cr1a-vbvs1b-fg1a-cl1a-pn1a-cn1a'"
if expected not in gradle: raise SystemExit('CONSTRAINTTIE1A expected 1.58 versionName missing')
for t in ['photometricNormalizedPassCount','photometricNormalizedDistance','referenceAlignedPositiveCeilingFromPhotonEv']:
 if t not in local: raise SystemExit('CONSTRAINTTIE1A requires normalized candidate telemetry: '+t)
frozen=['app/src/main/java/com/particlesdevs/photoncamera/m9/M9NegativeFeedback1A.java',local_rel,'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintNearest1A.java','app/src/main/java/com/particlesdevs/photoncamera/m9/M9ForegroundGuard1A.java','app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintRef1A.java','app/src/main/java/com/particlesdevs/photoncamera/m9/M9VirtualBv1A.java','app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintSplit1A.java','app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java','app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java','app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java','app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java','app/src/main/cpp/m9color_jni.cpp']
before={r:sha(r) for r in frozen}
rel='app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintTie1A.java'; p=root/rel
if p.exists(): raise SystemExit('CONSTRAINTTIE1A target already exists')
p.write_text(r'''package com.particlesdevs.photoncamera.m9;
import org.json.JSONArray;
import org.json.JSONObject;
/** Diagnostic-only nearest-distance cluster selector. */
public final class M9ConstraintTie1A {
 public static final String SCHEMA="m9cam.constrainttie.v1a";
 private static final double TIE_WINDOW_EV=0.05;
 private static final double MATCH_THRESHOLD=1.0;
 private M9ConstraintTie1A(){}
 public static JSONObject evaluate(JSONObject root){
  JSONObject out=contract();
  try{
   JSONObject local=root!=null?root.optJSONObject("m9ConstraintLocal"):null;
   if(local==null||!local.optBoolean("valid",false)) return invalid(out,"constraintlocal_missing");
   JSONArray a=local.optJSONArray("candidates");
   double request=local.optDouble("preSensorGuardedTargetFromPhotonEv",Double.NaN);
   put(out,"preSensorGuardedTargetFromPhotonEv",request);
   if(a==null) a=new JSONArray();
   double nearest=Double.POSITIVE_INFINITY;
   for(int i=0;i<a.length();i++){
    JSONObject c=a.optJSONObject(i); if(c==null||!c.optBoolean("photometricNormalizedValid",false)) continue;
    double d=c.optDouble("photometricNormalizedDistance",Double.NaN);
    if(finite(d)&&d<=MATCH_THRESHOLD&&d<nearest) nearest=d;
   }
   put(out,"nearestDistance",nearest);
   double limit=finite(nearest)?Math.min(MATCH_THRESHOLD,nearest+TIE_WINDOW_EV):Double.NaN;
   put(out,"tieWindowUpperDistance",limit);
   JSONObject chosen=null; long bestSeq=Long.MIN_VALUE; int n=0; JSONArray seqs=new JSONArray();
   if(finite(limit)) for(int i=0;i<a.length();i++){
    JSONObject c=a.optJSONObject(i); if(c==null||!c.optBoolean("photometricNormalizedValid",false)) continue;
    double d=c.optDouble("photometricNormalizedDistance",Double.NaN); if(!finite(d)||d>limit) continue;
    long s=c.optLong("sourceCompletedSequence",Long.MIN_VALUE); n++; if(s!=Long.MIN_VALUE) seqs.put(s);
    if(s>bestSeq){bestSeq=s;chosen=c;}
   }
   out.put("tieClusterCandidateCount",n); out.put("tieClusterCompletedSequences",seqs);
   if(chosen==null){out.put("valid",true);out.put("historyConstraintAvailable",false);out.put("reason","no_normalized_candidate_in_tie_cluster");return out;}
   double d=chosen.optDouble("photometricNormalizedDistance",Double.NaN);
   double pos=chosen.optDouble("referenceAlignedPositiveCeilingFromPhotonEv",Double.NaN);
   boolean mandAvail=chosen.optBoolean("referenceAlignedMandatoryCeilingAvailable",false);
   double mand=chosen.optDouble("referenceAlignedMandatoryCeilingFromPhotonEv",Double.NaN);
   out.put("valid",true);out.put("historyConstraintAvailable",true);out.put("selectedCompletedSequence",bestSeq);put(out,"selectedDistance",d);put(out,"selectedPositiveCeilingFromPhotonEv",pos);out.put("selectedMandatoryCeilingAvailable",mandAvail&&finite(mand));put(out,"selectedMandatoryCeilingFromPhotonEv",mandAvail?mand:Double.NaN);
   double target=request;String cause="none";
   if(finite(request)&&mandAvail&&finite(mand)&&mand<target){target=mand;cause="mandatory_raw_protection";}
   else if(finite(request)&&request>0&&finite(pos)&&pos<target){target=pos;cause="positive_raw_ceiling";}
   put(out,"counterfactualTargetFromPhotonEv",target);out.put("bindingCause",cause);put(out,"bindingMagnitudeEv",finite(request)&&finite(target)?Math.max(0,request-target):Double.NaN);
   out.put("reason","normalized_nearest_distance_cluster_newest_candidate_selected_no_live_mutation");
  }catch(Throwable t){try{invalid(out,"constrainttie1a_exception");out.put("error",t.toString());}catch(Exception ignored){}}
  return out;
 }
 private static JSONObject contract(){JSONObject o=new JSONObject();try{o.put("schema",SCHEMA);o.put("mode","diagnostic_only_no_exposure_mutation");o.put("liveEligible",false);o.put("usedToMutateCaptureTarget",false);o.put("selectionRule","nearest_normalized_distance_plus_0p05_then_newest_completed_raw");o.put("tieWindowEv",TIE_WINDOW_EV);o.put("matchThreshold",MATCH_THRESHOLD);o.put("calibration","research_only_20260904_18_exact_normalized_history_cases_mae_0p0221_to_0p0161");o.put("top2BroadEnvelopeAuthority",false);}catch(Exception ignored){}return o;}
 private static JSONObject invalid(JSONObject o,String r){try{o.put("valid",false);o.put("reason",r);o.put("liveEligible",false);o.put("usedToMutateCaptureTarget",false);}catch(Exception ignored){}return o;}
 private static void put(JSONObject o,String k,double v){try{o.put(k,finite(v)?v:JSONObject.NULL);}catch(Exception ignored){}}
 private static boolean finite(double v){return !Double.isNaN(v)&&!Double.isInfinite(v);}
}
''')
anchor='''            root.put("m9ConstraintNearest", M9ConstraintNearest1A.evaluate(root));\n            root.put("m9BacklightDiagnostic", M9BacklightDiagnostic.snapshotJson(root));\n'''
repl='''            root.put("m9ConstraintNearest", M9ConstraintNearest1A.evaluate(root));\n            root.put("m9ConstraintTie", M9ConstraintTie1A.evaluate(root));\n            root.put("m9BacklightDiagnostic", M9BacklightDiagnostic.snapshotJson(root));\n'''
if anchor not in meta: raise SystemExit('CONSTRAINTTIE1A metadata anchor missing')
(root/meta_rel).write_text(meta.replace(anchor,repl,1))
(root/gradle_rel).write_text(gradle.replace(expected,"versionName '1.59-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cr1a-vbvs1b-fg1a-cl1a-pn1a-cn1a-ct1a'",1))
marker='photometricnorm1aconstraintnearest1ascenefingerprint1b'; replm='photometricnorm1aconstraintnearest1aconstrainttie1ascenefingerprint1b'
if marker not in back: raise SystemExit('CONSTRAINTTIE1A forensic marker missing')
back=back.replace(marker,replm,1)
if '1.58-' not in back: raise SystemExit('CONSTRAINTTIE1A backlight version anchor missing')
(root/back_rel).write_text(back.replace('1.58-','1.59-',1))
for r,h in before.items():
 if sha(r)!=h: raise SystemExit('CONSTRAINTTIE1A frozen seam changed: '+r)
print('M9Cam CONSTRAINTTIE1A diagnostic selector applied')
print(' - nearest distance +0.05 cluster; newest completed RAW wins ties')
print(' - top2/broad remain non-authoritative')
print(' - no matcher, Camera2, allocator, guard, renderer, JPEG or DNG mutation')
