"""Exact source transform for the GL2G native-RGB rollback on TG2STILL1A."""
from pathlib import Path
import hashlib,json

ID='M9RBROLLBACK1A'
VERSION='1.61-m9rbrollback1a-tg2still1a'
RENDERER='app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
GRADLE='app/build.gradle'
OLD_CALL='''                detail1HJson = M9Detail1H.apply(norm16, dup, mhcRgbBuffer, width, height,
                        sourceCfaPattern, sourceRawOriginX, sourceRawOriginY, black, wl, neutralF,
                        nativeLiveGainMap, effectiveShadingLumaAuthorityAlpha,
                        nativeShading.representationScale, nativeCaptureResult);'''
NEW_CALL='''                // M9RBROLLBACK1A: keep the completed native GL2G RGB buffer.
                // Disabling only the guard still runs D; bypass the entire overwrite.
                detail1HJson = new JSONObject();
                detail1HJson.put("id", "M9RBROLLBACK1A");
                detail1HJson.put("reconstructionApplied", false);
                detail1HJson.put("guardRequested", false);
                detail1HJson.put("guardApplied", false);
                detail1HJson.put("nativeRgbPreserved", true);
                detail1HJson.put("greenAndIso160SharpUnchanged", true);
                detail1HJson.put("reason", "DETAIL1D_H_overwrite_bypassed");
                detail1HJson.put("fallback", "GL2G_native_RGB");'''
REPLACEMENTS=[
    (OLD_CALL,NEW_CALL),
    ('d.put("demosaicControl", "DETAIL1H_corrected_RB_guarded_noise_candidate");',
     'd.put("demosaicControl", "RBROLLBACK1A_GL2G_native_RGB");'),
    ('d.put("demosaicNeutralVariant", "DETAIL1H_SAT2_NATIVE_GUARD");',
     'd.put("demosaicNeutralVariant", "RBROLLBACK1A_TG2STILL1A");'),
    ('d.put("demosaicMhcNeutralFrozen1A", false);',
     'd.put("demosaicMhcNeutralFrozen1A", true);'),
    ('d.put("demosaicPhotographicChangeScope", "DETAIL1D_RB_DETAIL1F_guard_green_Sharp_fixed");',
     'd.put("demosaicPhotographicChangeScope", "RBROLLBACK1A_native_RGB_TG2_retained");')]

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def transform(renderer):
    s=renderer
    for old,new in REPLACEMENTS:
        if s.count(old)!=1:raise ValueError('RBROLLBACK1A anchor count '+str(s.count(old))+': '+old[:70])
        s=s.replace(old,new,1)
    assert 'M9Detail1H.apply(' not in s
    return s

def inventory(root):
    files=[root/GRADLE]
    for rel in ['app/src/main','circularbarlib/src/main']:
        files.extend(p for p in (root/rel).rglob('*') if p.is_file())
    return {str(p.relative_to(root)):sha(p) for p in sorted(files)}

def verify(root):
    manifest=json.loads(Path(__file__).with_name('m9rbrollback1a-manifest.json').read_text())
    for rel,expected in manifest['frozen'].items():
        assert sha(root/rel)==expected,('frozen source changed',rel)
    for rel,expected in manifest['changed'].items():
        assert sha(root/rel)==expected['after'],('rollback source changed',rel)
    source=(root/RENDERER).read_text()
    assert 'M9Detail1H.apply(' not in source
    # Native demosaic is still dispatched normally. Only its subsequent overwrite is removed.
    assert 'if(mhcNativeNs<0)' in source and 'mhcRgbBuffer' in source
    assert 'TG2NEUTRAL1A_STILL' in source
    assert source.count('"nativeRgbPreserved", true')==1
    receipt=json.loads((root/'M9RBROLLBACK1A_SOURCE_PROOF.json').read_text())
    after=inventory(root);before=receipt['before']
    assert set(after)==set(before),'source file set changed'
    changed=sorted(k for k in before if before[k]!=after[k])
    assert changed==sorted([RENDERER,GRADLE]),changed
    # Reverse the exact transform to prove no other renderer logic changed.
    original=source
    for old,new in reversed(REPLACEMENTS):
        assert original.count(new)==1;original=original.replace(new,old,1)
    assert digest(original)==manifest['changed'][RENDERER]['before']
    return dict(id=ID,version=VERSION,changed_files=changed,frozen_source_files=len(after)-len(changed),
        renderer_reverse_transform_exact=True,detail_apply_call_absent=True,
        native_RGB_producer_unchanged=True,TG2_still_and_preview_unchanged=True,
        scope='Whole D/H R/B overwrite bypass. Existing GL2G green/Sharp remains active. Phone photographic validation pending.')
