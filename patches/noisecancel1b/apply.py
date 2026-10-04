#!/usr/bin/env python3
"""Apply NOISECANCEL1B decoupled AMaZE chroma cancellation after exact 1.85 parent."""
from pathlib import Path
import json,shutil,sys
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

BASE='app/src/main/'
RENDER=BASE+'java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
JAVA=BASE+'java/com/particlesdevs/photoncamera/m9/render/M9NoiseCancel1B.java'
CPP=BASE+'cpp/m9noisecancel1b.cpp'
CMAKE=BASE+'cpp/CMakeLists.txt'
GRADLE='app/build.gradle'
ID='M9NOISECANCEL1B'
CHANGED={RENDER,CMAKE,GRADLE}
ADDED={JAVA,CPP}

def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, found {n}')
    return text.replace(old,new,1)

def transform_renderer(s):
    s=one(s,
      '        JSONObject colourTrial1CJson = null;\n',
      '        JSONObject colourTrial1CJson = null;\n        JSONObject noiseCancel1BJson = null;\n',
      'noise diagnostic declaration')
    anchor='''                        nativeShading.representationScale, nativeCaptureResult, NATIVE_COLOR_WORKERS);
                M9RenderCrash1D.stage("camera_matrix_meter");'''
    repl='''                        nativeShading.representationScale, nativeCaptureResult, NATIVE_COLOR_WORKERS);
                M9RenderCrash1D.stage("decoupled_quiet_chroma");
                noiseCancel1BJson = M9NoiseCancel1B.apply(mhcRgbBuffer, width, height,
                        sourceCfaPattern, nativeLiveGainMap, effectiveShadingLumaAuthorityAlpha,
                        nativeShading.representationScale, nativeCaptureResult);
                M9RenderCrash1D.stage("camera_matrix_meter");'''
    s=one(s,anchor,repl,'post AMaZE insertion')
    diag='''                d.put("detail1HApplied", false);'''
    diag_repl='''                d.put("detail1HApplied", false);
                d.put("noiseCancel1B", noiseCancel1BJson == null ? JSONObject.NULL : noiseCancel1BJson);
                d.put("noiseCancel1BApplied", noiseCancel1BJson != null && noiseCancel1BJson.optBoolean("applied", false));
                d.put("noiseCancel1BRevision", "M9NOISECANCEL1B_DECOUPLED_AMAZE_CHROMA");
                d.put("noiseCancel1BDetailSharpnessDependency", false);
                d.put("noiseCancel1BStage", "post_AMaZE_camera_RGB_pre_SOURCECAL2A");'''
    s=one(s,diag,diag_repl,'PRIMARY diagnostics')
    return s

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root)
    if now!=proof['after']: raise SystemExit('NOISECANCEL1B assembled source drift')
    changed={k for k,v in proof['before'].items() if now.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected changed files: '+repr(sorted(changed)))
    if set(now)-set(proof['before'])!=ADDED: raise SystemExit('Unexpected added files: '+repr(sorted(set(now)-set(proof['before']))))
    if (root/JAVA).read_bytes()!=(HERE/'M9NoiseCancel1B.java').read_bytes(): raise SystemExit('Java payload mismatch')
    if (root/CPP).read_bytes()!=(HERE/'m9noisecancel1b.cpp').read_bytes(): raise SystemExit('native payload mismatch')
    r=(root/RENDER).read_text();c=(root/CMAKE).read_text();g=(root/GRADLE).read_text()
    checks={
      'renderer call':'M9NoiseCancel1B.apply(mhcRgbBuffer' in r,
      'after AMaZE':'M9RenderCrash1D.stage("decoupled_quiet_chroma")' in r,
      'detail remains off':'d.put("detail1HApplied", false)' in r,
      'primary diagnostic':'noiseCancel1BApplied' in r and 'noiseCancel1BRevision' in r,
      'native compiled':'m9noisecancel1b.cpp' in c,
      'old guard retained':'m9detail1h_guard.cpp' in c,
      'revision':'M9NOISECANCEL1B_DECOUPLED_AMAZE_CHROMA' in (root/CPP).read_text(),
      'green frozen':'d.put("greenChannelMutation",false)' in (root/JAVA).read_text(),
      'detail dependency false':'d.put("detailSharpnessDependency",false)' in (root/JAVA).read_text(),
    }
    for name,ok in checks.items():
        if not ok: raise SystemExit('NOISECANCEL1B verify failed: '+name)
    if "versionName '1.86-m9noisecancel1b-decoupled-primaryexport1b-tg1'" not in g or 'versionCode 26706' not in g:
        raise SystemExit('NOISECANCEL1B version mismatch')
    frozen=[
      'app/src/main/cpp/m9detail1h_guard.cpp',
      'app/src/main/cpp/m9detail1h.cpp',
      'app/src/main/cpp/m9detail1h_rb.cpp',
      'app/src/main/cpp/m9color_jni.cpp',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9Detail1H.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9ColourTrial1C.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9AutoExposure2D.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewMeter2D.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/M9DiagnosticBurstSpool.java',
      'app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java',
      'app/src/main/assets/shaders/preview/main_fs.glsl',
      'app/src/main/assets/m9/m9_curve02_firmware.bin',
    ]
    for rel in frozen:
        if proof['before'][rel]!=now[rel]: raise SystemExit('frozen seam changed '+rel)
    return {
      'revision':ID,
      'version':'1.86-m9noisecancel1b-decoupled-primaryexport1b-tg1',
      'versionCode':26706,
      'changed':sorted(CHANGED),
      'added':sorted(ADDED),
      'parent':'1.85_M9PRIMARYEXPORT1B_FRESHFIRST_NOISECANCEL1A',
      'actualActiveNoisePath':'NOISECANCEL1B_post_AMaZE_camera_chroma',
      'detail1HReenabled':False,
      'sharpnessChanged':False,
      'greenChannelMutation':False,
      'noiseAuthority':'Camera2_SENSOR_NOISE_PROFILE',
      'confidenceGateStart':0.65,
      'confidenceGateFull':0.90,
      'maxBlend':0.50,
      'autoExposureChanged':False,
      'TC20ToneColourChanged':False,
      'primaryExport1BPreserved':True,
      'device_validation_pending':True,
    }

def main(root):
    root=root.resolve()
    receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists():
        print(json.dumps(verify(root),indent=2));return
    gradle=(root/GRADLE).read_text()
    if "versionName '1.85-m9primaryexport1b-freshfirst-noisecancel1a-tg1'" not in gradle or 'versionCode 26705' not in gradle:
        raise SystemExit('NOISECANCEL1B requires exact 1.85 parent identity')
    if (root/JAVA).exists() or (root/CPP).exists(): raise SystemExit('NOISECANCEL1B target already exists')
    before=inventory(root)
    render=transform_renderer((root/RENDER).read_text())
    (root/RENDER).write_text(render)
    cmake=(root/CMAKE).read_text()
    cmake=one(cmake,'    ${CMAKE_CURRENT_SOURCE_DIR}/m9detail1h_guard.cpp\n',
              '    ${CMAKE_CURRENT_SOURCE_DIR}/m9detail1h_guard.cpp\n    ${CMAKE_CURRENT_SOURCE_DIR}/m9noisecancel1b.cpp\n',
              'CMake source')
    (root/CMAKE).write_text(cmake)
    shutil.copyfile(HERE/'M9NoiseCancel1B.java',root/JAVA)
    shutil.copyfile(HERE/'m9noisecancel1b.cpp',root/CPP)
    gradle=one(gradle,'versionCode 26705','versionCode 26706','version code')
    gradle=one(gradle,
        "versionName '1.85-m9primaryexport1b-freshfirst-noisecancel1a-tg1'",
        "versionName '1.86-m9noisecancel1b-decoupled-primaryexport1b-tg1'",
        'version name')
    (root/GRADLE).write_text(gradle)
    after=inventory(root)
    changed={k for k,v in before.items() if after.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected mutation set: '+repr(sorted(changed)))
    if set(after)-set(before)!=ADDED: raise SystemExit('Unexpected added set: '+repr(sorted(set(after)-set(before))))
    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__':
    main(Path(sys.argv[1]))
