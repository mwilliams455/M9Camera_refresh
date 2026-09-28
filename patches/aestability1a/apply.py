#!/usr/bin/env python3
"""2.06 -> 2.07 AESTABILITY1A temporal exposure overlay. No target retuning."""
from pathlib import Path
import hashlib,json,shutil,sys,zipfile

ID='M9AESTABILITY1A'
VERSION='2.07-m9aestability1a-aecadence1a-exactpatch1b-ae1n-perf3i'
CODE=26727
AUTO='app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9AutoExposure2D.java'
GRADLE='app/build.gradle'
PARENT_AUTO='cba682286e3de3e71d9e598db106401cde5b699162f8a02e27fa3c471ce5b2bd'
NEW_AUTO='7f7d6e8de85960d36d5389907d413e93c069676a2a83bd6fa0c1aaf6df90e0f1'
PARENT_GRADLE='1b6fcaf0f0d28e14d1392ee7e7c0425f0a51e75d4f277ebf31b71c43bad990ad'
BASE_APK='e6b46136bd99f4bf98f6c418c822f9e51cc6c66141294c604d1461fb5d868818'
RECEIPT=ID+'_SOURCE_PROOF.json'

def sha(b): return hashlib.sha256(b).hexdigest()
def need(v,m):
    if not v: raise SystemExit(m)
def once(s,a,b):
    need(s.count(a)==1,'anchor mismatch: '+a[:100])
    return s.replace(a,b,1)
def inventory(root):
    files=[root/GRADLE]
    for rel in ['app/src/main','circularbarlib/src/main']:
        files.extend(p for p in (root/rel).rglob('*') if p.is_file())
    return {str(p.relative_to(root)):sha(p.read_bytes()) for p in sorted(files)}
def changed(a,b): return {k for k in set(a)|set(b) if a.get(k)!=b.get(k)}

def transform(raw):
    need(sha(raw)==PARENT_AUTO,'Unknown 2.06 M9AutoExposure2D source')
    s=raw.decode()
    s=once(s,
'''    private static final long SAFE_FAST_MAX_SAMPLE_AGE_NS=250000000L;

    // Deliberately low-key targets.''',
'''    private static final long SAFE_FAST_MAX_SAMPLE_AGE_NS=250000000L;

    // AESTABILITY1A: the rendered target remains on the inherited 0.25-EV grid,
    // but the applied exposure moves on a finer temporal ramp. Faster 125-ms
    // measurement cadence is retained; large 0.50/0.75-EV single-frame jumps are not.
    private static final double STABILITY_NEAR_STEP_EV=.125;
    private static final double STABILITY_FAR_STEP_EV=.25;
    private static final double STABILITY_FAR_GAP_EV=.75;
    private static final double STABILITY_REVERSAL_BYPASS_GAP_EV=1.00;
    private static final int STABILITY_REVERSAL_CONFIRMATIONS=2;
    private static final long STABILITY_INVALID_HOLD_NS=375000000L;

    // Deliberately low-key targets.''')
    s=once(s,
'''    private static double pendingLowerTargetEv=Double.NaN;
    private static int lowerTargetConfirmations;

    // 1F/1J: keep the same coherent 4x6 body and readability target while''',
'''    private static double pendingLowerTargetEv=Double.NaN;
    private static int lowerTargetConfirmations;

    // AESTABILITY1A temporal state. This does not alter the photographic target.
    private static int stabilityLastDirection;
    private static int stabilityPendingDirection;
    private static int stabilityPendingConfirmations;
    private static double stabilityRawTargetEv;
    private static double stabilityStableTargetEv;
    private static double stabilityLastStepEv;
    private static boolean stabilityHardSafetyRelease;
    private static long stabilityLastValidDecisionNs;
    private static boolean stabilityTransientHold;

    // 1F/1J: keep the same coherent 4x6 body and readability target while''')
    s=once(s,'responsePending1A=true;probeTiming1A=null;',
             'responsePending1A=true;probeTiming1A=null;resetAeStability1A(true);')
    s=once(s,
'''            owner=key;heldAutoEv=0;haveAuto=false;consumedSampleNs=-1;
            backlightLatched=false;resetLowerTargetHysteresis();resetBodyLock();''',
'''            owner=key;heldAutoEv=0;haveAuto=false;consumedSampleNs=-1;
            backlightLatched=false;resetLowerTargetHysteresis();resetBodyLock();
            resetAeStability1A(true);''')
    s=once(s,
'''            tapEpochSeen=tapEpoch;resetBodyLock();resetLowerTargetHysteresis();
            backlightLatched=false;consumedSampleNs=-1;''',
'''            tapEpochSeen=tapEpoch;resetBodyLock();resetLowerTargetHysteresis();
            backlightLatched=false;consumedSampleNs=-1;resetAeStability1A(false);''')
    s=once(s,
'''            result=0;target=0;heldAutoEv=0;haveAuto=false;consumedSampleNs=-1;
            backlightLatched=false;resetLowerTargetHysteresis();resetBodyLock();
            reason="manual_ISO_or_shutter";''',
'''            result=0;target=0;heldAutoEv=0;haveAuto=false;consumedSampleNs=-1;
            backlightLatched=false;resetLowerTargetHysteresis();resetBodyLock();resetAeStability1A(true);
            reason="manual_ISO_or_shutter";''')
    s=once(s,
'''            if(!haveAuto){heldAutoEv=legacy;haveAuto=true;}
            result=heldAutoEv;target=result;reason="manual_EV_holds_auto_baseline";''',
'''            if(!haveAuto){heldAutoEv=legacy;haveAuto=true;}
            resetAeStability1A(false);
            result=heldAutoEv;target=result;reason="manual_EV_holds_auto_baseline";''')
    s=once(s,
'''            result=0;target=0;heldAutoEv=0;haveAuto=false;consumedSampleNs=-1;
            backlightLatched=false;resetLowerTargetHysteresis();resetBodyLock();
            reason="auto_scene_placement_not_eligible";''',
'''            result=0;target=0;heldAutoEv=0;haveAuto=false;consumedSampleNs=-1;
            backlightLatched=false;resetLowerTargetHysteresis();resetBodyLock();resetAeStability1A(true);
            reason="auto_scene_placement_not_eligible";''')
    s=once(s,
'''            positiveRiseStepEv=safeFastAcquire075?SAFE_FAST_POSITIVE_SLEW_EV
                    :(fastAcquire?FAST_POSITIVE_SLEW_EV:NORMAL_POSITIVE_SLEW_EV);

            if(target>current+1e-9) {
                resetLowerTargetHysteresis();
                result=freshSample?Math.min(target,current+positiveRiseStepEv):current;
            } else if(target<current-1e-9) {
                if(hardSafetyRelease) {
                    // A real highlight/headroom loss remains immediate.
                    result=Math.min(target,positiveLimit);
                    resetLowerTargetHysteresis();
                } else if(freshSample) {
                    // Ordinary target/classification noise needs two fresh samples
                    // before stepping down, preventing 0.25-EV preview ping-pong.
                    if(!Double.isFinite(pendingLowerTargetEv)
                            ||Math.abs(target-pendingLowerTargetEv)>.125) {
                        pendingLowerTargetEv=target;lowerTargetConfirmations=1;result=current;
                    } else {
                        lowerTargetConfirmations++;
                        if(lowerTargetConfirmations>=2) {
                            result=Math.max(target,current-.25);
                            if(result<=target+1e-9)resetLowerTargetHysteresis();
                            else {pendingLowerTargetEv=target;lowerTargetConfirmations=0;}
                        } else result=current;
                    }
                } else result=current;
            } else {
                result=current;resetLowerTargetHysteresis();
            }
            consumedSampleNs=sample.submittedNs;heldAutoEv=result;haveAuto=true;''',
'''            // AESTABILITY1A: target selection above is unchanged. Apply a finer
            // temporal ramp at the faster cadence, with confirmation only when
            // ordinary motion reverses direction. Real headroom loss is immediate.
            result=applyAeStability1A(target,current,freshSample,hardSafetyRelease,nowNs);
            positiveRiseStepEv=stabilityLastStepEv;
            resetLowerTargetHysteresis();
            consumedSampleNs=sample.submittedNs;heldAutoEv=result;haveAuto=true;''')
    s=once(s,
'''        } else {
            double bounded=legacy>0?0:legacy;
            heldAutoEv=bounded;haveAuto=true;result=bounded;target=bounded;
            reason="rendered_meter_unavailable_or_stale";
        }

        responsePending1A=autoEligible&&manualExposure==0&&manualIso==0&&Math.abs(userEv)<=1e-6
                &&(!valid||Math.abs(target-result)>1e-9||lowerTargetConfirmations>0
                    ||pendingBodyConfirmations>0);''',
'''        } else {
            double bounded=legacy>0?0:legacy;
            boolean hold=haveAuto&&stabilityLastValidDecisionNs>0
                    &&nowNs>=stabilityLastValidDecisionNs
                    &&nowNs-stabilityLastValidDecisionNs<=STABILITY_INVALID_HOLD_NS;
            if(hold) {
                result=heldAutoEv;target=result;stabilityTransientHold=true;
                reason="rendered_meter_transient_hold";
            } else {
                heldAutoEv=bounded;haveAuto=true;result=bounded;target=bounded;
                resetAeStability1A(false);
                reason="rendered_meter_unavailable_or_stale";
            }
        }

        responsePending1A=autoEligible&&manualExposure==0&&manualIso==0&&Math.abs(userEv)<=1e-6
                &&(!valid||Math.abs(target-result)>1e-9||stabilityPendingConfirmations>0
                    ||pendingBodyConfirmations>0);''')
    s=once(s,
'''            cadenceDiagnostics1A(o);
            o.put("revision",REVISION).put("reason",reason)''',
'''            cadenceDiagnostics1A(o);
            stabilityDiagnostics1A(o);
            o.put("revision",REVISION).put("reason",reason)''')
    s=once(s,
'''    private static void resetLowerTargetHysteresis() {
        pendingLowerTargetEv=Double.NaN;lowerTargetConfirmations=0;
    }
''',
'''    private static void resetAeStability1A(boolean clearValidTime) {
        stabilityLastDirection=0;stabilityPendingDirection=0;stabilityPendingConfirmations=0;
        stabilityRawTargetEv=0;stabilityStableTargetEv=clearValidTime?0:heldAutoEv;stabilityLastStepEv=0;
        stabilityHardSafetyRelease=false;stabilityTransientHold=false;
        if(clearValidTime)stabilityLastValidDecisionNs=0;
    }
    private static int stabilityDirection1A(double delta) {
        return delta>1e-9?1:(delta<-1e-9?-1:0);
    }
    private static double stabilityStep1A(double gap) {
        return gap>=STABILITY_FAR_GAP_EV-1e-9?STABILITY_FAR_STEP_EV:STABILITY_NEAR_STEP_EV;
    }
    private static double applyAeStability1A(double rawTarget,double current,boolean fresh,
            boolean hardSafety,long nowNs) {
        stabilityRawTargetEv=rawTarget;stabilityTransientHold=false;
        stabilityHardSafetyRelease=hardSafety;stabilityLastStepEv=0;
        if(!fresh){stabilityStableTargetEv=current;return current;}
        stabilityLastValidDecisionNs=nowNs;
        int direction=stabilityDirection1A(rawTarget-current);
        if(direction==0) {
            stabilityStableTargetEv=rawTarget;stabilityPendingDirection=0;
            stabilityPendingConfirmations=0;return current;
        }
        if(hardSafety&&direction<0) {
            stabilityStableTargetEv=rawTarget;stabilityPendingDirection=0;
            stabilityPendingConfirmations=0;stabilityLastDirection=-1;
            stabilityLastStepEv=Math.abs(current-rawTarget);return rawTarget;
        }
        double gap=Math.abs(rawTarget-current);
        boolean reversal=stabilityLastDirection!=0&&direction!=stabilityLastDirection;
        if(reversal&&gap<STABILITY_REVERSAL_BYPASS_GAP_EV-1e-9) {
            if(stabilityPendingDirection!=direction) {
                stabilityPendingDirection=direction;stabilityPendingConfirmations=1;
                stabilityStableTargetEv=current;return current;
            }
            stabilityPendingConfirmations++;
            if(stabilityPendingConfirmations<STABILITY_REVERSAL_CONFIRMATIONS) {
                stabilityStableTargetEv=current;return current;
            }
        }
        stabilityPendingDirection=0;stabilityPendingConfirmations=0;
        stabilityStableTargetEv=rawTarget;
        double step=Math.min(gap,stabilityStep1A(gap));
        stabilityLastStepEv=step;stabilityLastDirection=direction;
        return current+direction*step;
    }
    private static void stabilityDiagnostics1A(JSONObject o) throws org.json.JSONException {
        o.put("aeStabilityRevision","M9AESTABILITY1A")
                .put("aeRawTargetEv",stabilityRawTargetEv)
                .put("aeStableTargetEv",stabilityStableTargetEv)
                .put("aeAppliedStepEv",stabilityLastStepEv)
                .put("aeMotionDirection",stabilityLastDirection)
                .put("aeReversalPendingDirection",stabilityPendingDirection)
                .put("aeReversalConfirmations",stabilityPendingConfirmations)
                .put("aeNearStepEv",STABILITY_NEAR_STEP_EV)
                .put("aeFarStepEv",STABILITY_FAR_STEP_EV)
                .put("aeFarGapEv",STABILITY_FAR_GAP_EV)
                .put("aeReversalBypassGapEv",STABILITY_REVERSAL_BYPASS_GAP_EV)
                .put("aeInvalidHoldMs",STABILITY_INVALID_HOLD_NS/1e6)
                .put("aeTransientMeterHold",stabilityTransientHold)
                .put("aeHardSafetyRelease",stabilityHardSafetyRelease)
                .put("aeExposureTargetsChangedByStability",false);
    }

    private static void resetLowerTargetHysteresis() {
        pendingLowerTargetEv=Double.NaN;lowerTargetConfirmations=0;
    }
''')
    s=once(s,
'''            target=Math.min(requested,limit);
            boolean fresh=consumedSampleNs!=s.submittedNs;
            // Tap is an explicit new target; do not inherit the old body/target or its
            // confidence contest. Retain the existing normal quarter-stop acquisition.
            if(target>current)result=fresh?Math.min(target,current+NORMAL_POSITIVE_SLEW_EV):current;
            else result=target; // a new explicit selection and hard limits may reduce immediately
            consumedSampleNs=s.submittedNs;heldAutoEv=result;haveAuto=true;''',
'''            target=Math.min(requested,limit);
            boolean fresh=consumedSampleNs!=s.submittedNs;
            // AESTABILITY1A applies the same temporal contract to explicit subject
            // priority. A newly tighter highlight/background limit is safety and may
            // still pull exposure down immediately.
            boolean hardSafety=limit<current-1e-9&&target<current-1e-9;
            result=applyAeStability1A(target,current,fresh,hardSafety,now);
            consumedSampleNs=s.submittedNs;heldAutoEv=result;haveAuto=true;''')
    s=once(s,
'''        } else if(s==null||!s.matches(camera,mode,now,energy)) {
            result=0;target=0;heldAutoEv=0;haveAuto=false;M9TapMeter1A.status("M9 tap: waiting for meter");
        }
        responsePending1A=!valid||Math.abs(target-result)>1e-9;
        try {
            JSONObject o=new JSONObject().put("revision",REVISION).put("tapMeterRevision",M9TapMeter1A.REVISION)''',
'''        } else if(s==null||!s.matches(camera,mode,now,energy)) {
            boolean hold=haveAuto&&stabilityLastValidDecisionNs>0&&now>=stabilityLastValidDecisionNs
                    &&now-stabilityLastValidDecisionNs<=STABILITY_INVALID_HOLD_NS;
            if(hold) {
                result=heldAutoEv;target=result;stabilityTransientHold=true;
                reason="tap_transient_meter_hold";M9TapMeter1A.status("M9 tap: holding while meter refreshes");
            } else {
                result=0;target=0;heldAutoEv=0;haveAuto=false;resetAeStability1A(false);
                M9TapMeter1A.status("M9 tap: waiting for meter");
            }
        }
        responsePending1A=!valid||Math.abs(target-result)>1e-9||stabilityPendingConfirmations>0;
        try {
            JSONObject o=new JSONObject().put("revision",REVISION).put("tapMeterRevision",M9TapMeter1A.REVISION)''')
    s=once(s,
'''            cadenceDiagnostics1A(o);
            return new Decision(result,reason,o);''',
'''            cadenceDiagnostics1A(o);
            stabilityDiagnostics1A(o);
            return new Decision(result,reason,o);''')
    need(sha(s.encode())==NEW_AUTO,'Candidate source hash mismatch')
    return s.encode()

def apply(root):
    root=root.resolve(); proof=root/RECEIPT
    now=inventory(root)
    if proof.exists():
        rec=json.loads(proof.read_text()); need(now==rec['after'],'Candidate source drift')
    else:
        parent=json.loads((root/'M9AECADENCE1A_SOURCE_PROOF.json').read_text())
        need(now==parent['after'] and len(now)==1007,'Unknown 2.06 parent inventory')
        need(now.get(AUTO)==PARENT_AUTO and now.get(GRADLE)==PARENT_GRADLE,'Unknown 2.06 parent source')
        before=now
        (root/AUTO).write_bytes(transform((root/AUTO).read_bytes()))
        g=(root/GRADLE).read_text()
        g=once(g,'versionCode 26726',f'versionCode {CODE}')
        g=once(g,"versionName '2.06-m9aecadence1a-exactpatch1b-ae1n-perf3i'",f"versionName '{VERSION}'")
        (root/GRADLE).write_text(g)
        now=inventory(root)
        need(changed(before,now)=={AUTO,GRADLE},'Unexpected production changes')
        rec={'revision':ID,'before':before,'after':now}
        proof.write_text(json.dumps(rec,indent=2)+'\n')
    need(now.get(AUTO)==NEW_AUTO,'Wrong candidate exposure source')
    need(changed(rec['before'],now)=={AUTO,GRADLE},'Wrong child change set')
    need(f'versionCode {CODE}' in (root/GRADLE).read_text(),'Wrong versionCode')
    return {'revision':ID,'version':VERSION,'versionCode':CODE,
            'changedFiles':[AUTO,GRADLE],'exposureTargetsChanged':False,
            'probeCadenceChanged':False,'tapSearchRangeChanged':False,
            'nightPlacementChanged':False,'signedTapImplemented':False,
            'rendererChanged':False,'phoneValidationPending':True}

def post(root,baseline,out):
    root=root.resolve();out.mkdir(parents=True,exist_ok=True)
    rec=json.loads((root/RECEIPT).read_text());now=inventory(root)
    modified=[p for p,h in rec['after'].items() if now.get(p)!=h]
    added={p:h for p,h in now.items() if p not in rec['after']}
    (out/'POSTBUILD_INPUTS.json').write_text(json.dumps({'modified':modified,'added':added},indent=2)+'\n')
    need(not modified,'Audited input changed after build')
    need(all(p.startswith('app/src/main/cpp/') for p in added),'Unexpected generated source')
    apks=list((root/'app/build/outputs/apk/debug').glob('*.apk'));need(len(apks)==1,'Expected one APK')
    bases=list(baseline.rglob('M9Cam_2.06_AECADENCE1A.apk'));need(len(bases)==1,'Missing 2.06 APK')
    old=bases[0];need(sha(old.read_bytes())==BASE_APK,'Wrong 2.06 baseline bytes')
    def frozen(z): return {n:sha(z.read(n)) for n in z.namelist()
                           if not n.endswith('/') and n.startswith(('lib/','assets/','res/raw/'))}
    with zipfile.ZipFile(old) as a,zipfile.ZipFile(apks[0]) as b:
        fa=frozen(a);need(fa==frozen(b),'Photographic packaged bytes changed')
        dex=b''.join(b.read(n) for n in b.namelist() if n.endswith('.dex'))
        for token in [b'M9AESTABILITY1A',b'aeRawTargetEv',b'aeTransientMeterHold',
                      b'M9AECADENCE1A',b'EXACTPATCHCLIP1B']:
            need(token in dex,'Missing DEX marker '+repr(token))
    target=out/'M9Cam_2.07_AESTABILITY1A.apk';shutil.copyfile(apks[0],target)
    proof={'version':VERSION,'versionCode':CODE,'apkSha256':sha(target.read_bytes()),
           'baselineApkSha256':BASE_APK,'frozenEntries':len(fa),
           'frozenEntriesByteIdentical':True,'phoneValidationPending':True}
    (out/'APK_PROOF.json').write_text(json.dumps(proof,indent=2)+'\n')
    (out/'SHA256SUMS.txt').write_text(proof['apkSha256']+'  '+target.name+'\n')
    return proof

if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='apply': out=apply(Path(sys.argv[2]))
    elif len(sys.argv)==5 and sys.argv[1]=='post': out=post(*map(Path,sys.argv[2:]))
    else: raise SystemExit('usage: apply.py apply ROOT | post ROOT BASELINE OUTPUT')
    print(json.dumps(out,indent=2))
