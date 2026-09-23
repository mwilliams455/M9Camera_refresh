"""Build the selected rendering on the exact SHUTTERTRACE1B/TG1 source."""
from pathlib import Path
import sys,json,hashlib,shutil,subprocess
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory
from m9shuttertrace1b import verify as parent_verify
BASE='app/src/main/java/com/particlesdevs/photoncamera/'
RENDERER=BASE+'m9/render/M9R35Renderer.java'
NATIVE='app/src/main/cpp/m9color_jni.cpp'
CMAKE='app/src/main/cpp/CMakeLists.txt'
AUTO=BASE+'m9/preview/M9AutoExposure2D.java'
ID='M9COLOURTRIAL1C'
def replace(s,a,b):
    if s.count(a)!=1:raise ValueError('Expected one anchor: '+a[:100]+' count='+str(s.count(a)))
    return s.replace(a,b,1)
def transform(s):
    offset=s.index("        JSONObject detail1HJson = null;")
    prefix=s[:offset];s=s[offset:]
    s=replace(s,'        JSONObject detail1HJson = null;', '''        JSONObject colourTrial1CJson = null;
        final boolean colourTrial1CActive = !demosaicNeutralEa1A && !demosaicPlainMhc1A && bridgeProbeMode == 0;''')
    a='''            if (demosaicNeutralEa1A) {
                if (sourceCfaPattern'''
    b='''            if (colourTrial1CActive) {
                colourTrial1CJson = M9ColourTrial1C.apply(norm16, dup, mhcRgbBuffer, width, height,
                        sourceCfaPattern, sourceRawOriginX, sourceRawOriginY, black, wl, neutralF,
                        nativeLiveGainMap, effectiveShadingLumaAuthorityAlpha,
                        nativeShading.representationScale, nativeCaptureResult, NATIVE_COLOR_WORKERS);
            } else if (demosaicNeutralEa1A) {
                if (sourceCfaPattern'''
    s=replace(s,a,b)
    start=s.index('            if (!demosaicNeutralEa1A && !demosaicPlainMhc1A && bridgeProbeMode == 0\n')
    end=s.index('            norm16 = null;',start)
    assert 'M9Detail1H.apply(' in s[start:end]
    s=s[:start]+s[end:]
    anchor='''            final long nativeColorCvBaseAddress = nativeColorCvDirectEligible ? cam16.dataAddr() : 0L;'''
    s=replace(s,anchor,anchor+'''
            if (colourTrial1CActive && !nativeColorCvDirectEligible)
                throw new IllegalStateException("COLOURTRIAL1C requires packed camera RGB");
            final long colourTrialPrepareStart = System.nanoTime();
            // Retained Java ByteBuffer is passed to every synchronous JNI call.
            final ByteBuffer colourTrialQ14 = colourTrial1CActive
                    ? M9ColourTrial1C.prepareFrame(nativeContextForFrame, nativeColorCvBaseAddress,
                            width, height, effectiveRenderGain) : null;
            if (colourTrial1CJson != null) colourTrial1CJson.put("chromaPrepareMs",
                    (System.nanoTime() - colourTrialPrepareStart) / 1_000_000.0);''')
    start=s.index('            for (int y0 = 0; y0 < height; y0 += NATIVE_COLOR_BLOCK_ROWS) {',s.index('final ByteBuffer colourTrialQ14'))
    end=s.index('                nativeColorJniElapsedNsSum +=',start)
    block=s[start:end]
    block=replace(block,'M9NativeColorCore.renderBlockParallelDirectBitmap(', 'M9ColourTrial1C.renderBlockParallelDirectBitmap(')
    assert block.count('M9NativeColorCore.renderBlockParallelDirect(')==2
    block=block.replace('M9NativeColorCore.renderBlockParallelDirect(', 'M9ColourTrial1C.renderBlockParallelDirect(')
    a='effectiveRenderGain, tgCbGain, tgCrGain, rotation, NATIVE_COLOR_WORKERS, nativeStats);'
    assert block.count(a)==4
    # Bitmap, two direct int[] calls, then untouched copied non-production fallback.
    parts=block.split(a)
    block=parts[0]+a[:-2]+', colourTrialQ14);'+parts[1]+a[:-2]+', colourTrialQ14, y0, height);'+parts[2]+a[:-2]+', colourTrialQ14, y0, height);'+parts[3]+a+parts[4]
    s=s[:start]+block+s[end:]
    start=s.index('            if (detail1HJson != null) {')
    end=s.index('            d.put("colorContextElapsedMs"',start)
    s=s[:start]+'''            if (colourTrial1CJson != null) {
                d.put("colourTrial1C", colourTrial1CJson);
                d.put("detail1HApplied", false);
                d.put("demosaicControl", "COLOURTRIAL1C_AMAZE_QUARTER");
                d.put("demosaicMode", "AMaZE_with_true_noSharp_MHC_16px_border");
                d.put("demosaicNeutralVariant", "COLOURTRIAL1C_SAT2_TG1");
                d.put("demosaicMhcNeutral1A", false);
                d.put("demosaicMhcNeutralFrozen1A", false);
                d.put("demosaicNeutralOnlyPhotographicDifference", "AMaZE_RAW_quarter_preSAT_chroma_quarter");
                d.put("demosaicPhotographicChangeScope", "AMaZE_RAW_quarter_preSAT_chroma_quarter_Auto_headroom");
                d.put("demosaicNativeElapsedMs", colourTrial1CJson.get("reconstructionMs"));
                d.put("demosaicWorkersUsed", NATIVE_COLOR_WORKERS);
                d.put("pipeline", "NORM030 -> RAW_quarter -> AMaZE -> SOURCECAL2A_identityHSM -> TC20_gain -> Q14_chroma_quarter -> SAT2 -> curve02 -> BT601_422 -> TG1");
                d.put("reference", "M9COLOURTRIAL1C accepted working colour balance on SHUTTERTRACE1B TG1");
            }
''' +s[end:]
    assert 'M9Detail1H.apply(' not in s
    return prefix+s

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text());now=inventory(root)
    assert now==proof['after'],'source drift'
    expected={RENDERER,NATIVE,CMAKE,AUTO,'app/build.gradle'}
    assert {k for k in proof['before'] if now[k]!=proof['before'][k]}==expected
    native=root/'app/src/main/cpp/colourtrial1c'
    for name in ['reconstruct.cpp','phase_noise.cpp','chroma.cpp','native.inc']:
        assert (native/name).read_bytes()==(HERE/name).read_bytes()
    for source in (HERE/'upstream').rglob('*'):
        if source.is_file():assert (native/'upstream'/source.relative_to(HERE/'upstream')).read_bytes()==source.read_bytes()
    provenance=json.loads((HERE/'upstream/PROVENANCE.json').read_text())
    for rel,digest in provenance['files'].items():assert hashlib.sha256((native/'upstream'/rel).read_bytes()).hexdigest()==digest
    assert (root/(BASE+'m9/render/M9ColourTrial1C.java')).read_bytes()==(HERE/'M9ColourTrial1C.java').read_bytes()
    assert (root/AUTO).read_bytes()==(HERE.parent/'colourtrial1a/M9AutoExposure2D.java').read_bytes()
    assert 'M9Detail1H.apply(' not in (root/RENDERER).read_text()
    for k,v in proof['before'].items():
        if k.startswith('app/src/main/assets/'):assert now[k]==v
    return {'revision':ID,'source_files':len(now),'changed_existing':sorted(expected),'assets_capture_requests_exif_preview_shader_unchanged':True,'version':'1.65-m9colourtrial1c-tg1','code':26685,'device_validation_pending':True}

def main(root):
    receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists():print(json.dumps(verify(root),indent=2));return
    parent_verify(root);before=inventory(root)
    s=transform((root/RENDERER).read_text())
    n=(root/NATIVE).read_text();n=replace(n,'    int skyChromaMode1A = 0;','    int skyChromaMode1A = 0;\n    bool colourTrialPrepared = false;')
    a='inline void cameraToM9(const jshort* cam, int c, const ColorContext& ctx, double* hsmOut, double* m9Out) {'
    n=replace(n,a,a+'''\n    if (ctx.colourTrialPrepared) {
        for(int ch=0;ch<3;ch++) hsmOut[ch]=m9Out[ch]=double(u16(cam[c+ch]))/double(RAW_MAX);
        return;
    }''')
    n+='\n#include "colourtrial1c/native.inc"\n'
    g=(root/'app/build.gradle').read_text();g=replace(g,'versionCode 26684','versionCode 26685');g=replace(g,"versionName '1.64-m9shuttertrace1b-tg1'","versionName '1.65-m9colourtrial1c-tg1'")
    # Validate every source anchor before changing the assembled source tree.
    assert hashlib.sha256((root/AUTO).read_bytes()).hexdigest()==(HERE.parent/'colourtrial1a/base.sha256').read_text().strip()
    (root/RENDERER).write_text(s);(root/NATIVE).write_text(n);(root/'app/build.gradle').write_text(g)
    (root/CMAKE).write_text((root/CMAKE).read_text()+'\n'+(HERE/'cmake.txt').read_text())
    shutil.copyfile(HERE.parent/'colourtrial1a/M9AutoExposure2D.java',root/AUTO)
    shutil.copyfile(HERE/'M9ColourTrial1C.java',root/(BASE+'m9/render/M9ColourTrial1C.java'))
    target=root/'app/src/main/cpp/colourtrial1c';target.mkdir()
    for f in ['reconstruct.cpp','phase_noise.cpp','chroma.cpp','native.inc']:shutil.copyfile(HERE/f,target/f)
    shutil.copytree(HERE/'upstream',target/'upstream')
    # Preserve upstream license in the distributable too; original assets remain exact.
    licensePath=root/'app/src/main/assets/m9/AMaZE_LICENSE.txt';licensePath.write_bytes((HERE/'upstream/LICENSE.txt').read_bytes())
    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':inventory(root)},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))
if __name__=='__main__':main(Path(sys.argv[1]).resolve())
