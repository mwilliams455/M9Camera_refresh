#!/usr/bin/env python3
"""Apply PRIMARYRECOVERY1A after exact 1.83 NOISECANCEL1A."""
from pathlib import Path
import json,sys
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

WRITER='app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java'
GRADLE='app/build.gradle'
ID='M9PRIMARYRECOVERY1A'
CHANGED={WRITER,GRADLE}

def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, found {n}')
    return text.replace(old,new,1)

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root)
    if now!=proof['after']: raise SystemExit('PRIMARYRECOVERY1A assembled source drift')
    changed={k for k,v in proof['before'].items() if now.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected changed files: '+repr(sorted(changed)))
    w=(root/WRITER).read_text();g=(root/GRADLE).read_text()
    checks={
      'revision':'M9PRIMARYRECOVERY1A' in w,
      'spool import':'import com.particlesdevs.photoncamera.m9.M9DiagnosticBurstSpool;' in w,
      'exact bytes staged':'M9DiagnosticBurstSpool.stage(frozen.timingPath, frozen.bytes, RECOVERY_ROLE)' in w,
      'public persist fallback':'stageRecovery(frozen, "public_persist_failure", t)' in w,
      'schedule fallback':'stageRecovery(frozen, "schedule_failure", t)' in w,
      'compat role':'private static final String RECOVERY_ROLE = "primary_timing";' in w,
      'recovery diagnostic':'primaryTimingRecoveryFallbackEnabled' in w,
      'frozen byte authority':'exact_frozen_PRIMARY_bytes' in w,
    }
    for name,ok in checks.items():
        if not ok: raise SystemExit('PRIMARYRECOVERY1A verify failed: '+name)
    if "versionName '1.84-m9primaryrecovery1a-noisecancel1a-tg1'" not in g or 'versionCode 26704' not in g:
        raise SystemExit('PRIMARYRECOVERY1A version mismatch')

    frozen=[
      'app/src/main/cpp/m9detail1h_guard.cpp',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9Detail1H.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9AutoExposure2D.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewMeter2D.java',
      'app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/M9DiagnosticBurstSpool.java',
      'app/src/main/assets/shaders/preview/main_fs.glsl',
      'app/src/main/assets/m9/m9_curve02_firmware.bin',
    ]
    for rel in frozen:
        if proof['before'][rel]!=now[rel]: raise SystemExit('frozen seam changed '+rel)

    return {
      'revision':ID,
      'version':'1.84-m9primaryrecovery1a-noisecancel1a-tg1',
      'versionCode':26704,
      'changed':sorted(CHANGED),
      'parent':'1.83_M9NOISECANCEL1A_QUIETCHROMA',
      'normalPrimaryPublicWritePreserved':True,
      'fallbackTrigger':'public_PRIMARY_persist_or_async_schedule_failure',
      'fallbackTransport':'M9SPOOLSTREAM1A_private_durable_stage_then_eventual_individual_export',
      'fallbackRole':'primary_timing',
      'payloadAuthority':'exact_frozen_PRIMARY_bytes',
      'renderingChanged':False,
      'noisePolicyChanged':False,
      'autoExposureChanged':False,
      'JPEG_DNG_preview_changed':False,
      'device_validation_pending':True,
    }

def main(root):
    root=root.resolve()
    receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists():
        print(json.dumps(verify(root),indent=2));return

    g=(root/GRADLE).read_text()
    if "versionName '1.83-m9noisecancel1a-quietchroma-tg1'" not in g or 'versionCode 26703' not in g:
        raise SystemExit('PRIMARYRECOVERY1A requires exact 1.83 parent identity')

    before=inventory(root)
    w=(root/WRITER).read_text()
    if 'M9PRIMARYRECOVERY1A' in w: raise SystemExit('PRIMARYRECOVERY1A already applied')
    w=one(w,
      'import com.particlesdevs.photoncamera.util.Log;\n',
      'import com.particlesdevs.photoncamera.m9.M9DiagnosticBurstSpool;\nimport com.particlesdevs.photoncamera.util.Log;\n',
      'spool import')
    w=one(w,
      '    private static final String TAG = "M9PrimaryTiming";\n',
      '    private static final String TAG = "M9PrimaryTiming";\n    private static final String RECOVERY_REVISION = "M9PRIMARYRECOVERY1A";\n    private static final String RECOVERY_ROLE = "primary_timing";\n',
      'recovery constants')
    w=one(w,
      '''        if (dngPath == null) return false;
        try {
            FrozenTiming frozen = freezeInternal(
''',
      '''        if (dngPath == null) return false;
        FrozenTiming frozen = null;
        try {
            frozen = freezeInternal(
''',
      'freeze variable')
    w=one(w,
      '            TIMING_WRITER.execute(() -> persistFrozen(frozen));\n',
      '''            final FrozenTiming scheduled = frozen;
            TIMING_WRITER.execute(() -> persistFrozen(scheduled));
''',
      'schedule handoff')
    w=one(w,
      '''            return true;
        } catch (Throwable t) {
''',
      '''            return true;
        } catch (Throwable t) {
            if (frozen != null && stageRecovery(frozen, "schedule_failure", t)) {
                return true;
            }
''',
      'schedule fallback')
    w=one(w,
      '        root.put("primaryTimingMode", "frozen_bytes_deferred_persist_after_dng_stage");\n',
      '''        root.put("primaryTimingMode", "frozen_bytes_deferred_persist_after_dng_stage");
        root.put("primaryTimingRecoveryRevision", RECOVERY_REVISION);
        root.put("primaryTimingRecoveryFallbackEnabled", true);
        root.put("primaryTimingRecoveryFallbackRole", RECOVERY_ROLE);
        root.put("primaryTimingRecoveryAuthority", "exact_frozen_PRIMARY_bytes");
''',
      'recovery diagnostics')
    w=one(w,
      '''        } catch (Throwable t) {
            Log.e(TAG, "Unable to persist PRIMARY2.4 DNGASYNC1A timing sidecar", t);
        }
    }
}
''',
      '''        } catch (Throwable t) {
            if (!stageRecovery(frozen, "public_persist_failure", t)) {
                Log.e(TAG, "Unable to persist PRIMARY2.4 DNGASYNC1A timing sidecar and recovery stage failed", t);
            }
        }
    }

    /**
     * PRIMARYRECOVERY1A: if public PRIMARY persistence fails, retain the exact
     * already-frozen bytes in the existing durable diagnostic spool. The spool
     * exports the same public path later while the app is visible and can recover
     * retained manifests after restart. No renderer object or RAW ownership crosses
     * this boundary.
     */
    private static boolean stageRecovery(FrozenTiming frozen, String reason, Throwable cause) {
        if (frozen == null || frozen.timingPath == null || frozen.bytes == null) return false;
        try {
            boolean staged = M9DiagnosticBurstSpool.stage(
                    frozen.timingPath, frozen.bytes, RECOVERY_ROLE);
            if (staged) {
                Log.w(TAG, RECOVERY_REVISION + " staged exact frozen PRIMARY bytes after "
                        + reason + ": " + frozen.timingPath
                        + "; bytes=" + frozen.bytes.length
                        + "; cause=" + String.valueOf(cause));
            } else {
                Log.e(TAG, RECOVERY_REVISION + " spool rejected PRIMARY recovery after "
                        + reason + ": " + frozen.timingPath, cause);
            }
            return staged;
        } catch (Throwable recoveryError) {
            Log.e(TAG, RECOVERY_REVISION + " PRIMARY recovery threw after " + reason
                    + ": " + frozen.timingPath, recoveryError);
            return false;
        }
    }
}
''',
      'persist fallback')

    (root/WRITER).write_text(w)
    g=one(g,'versionCode 26703','versionCode 26704','version code')
    g=one(g,
      "versionName '1.83-m9noisecancel1a-quietchroma-tg1'",
      "versionName '1.84-m9primaryrecovery1a-noisecancel1a-tg1'",
      'version name')
    (root/GRADLE).write_text(g)

    after=inventory(root)
    changed={k for k,v in before.items() if after.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected mutation set: '+repr(sorted(changed)))
    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__':
    main(Path(sys.argv[1]))
