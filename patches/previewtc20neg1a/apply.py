"""Apply preview-only negative TC20 parity on the exact AUTOEXPOSUREFINISH1B assembly."""
from pathlib import Path
import hashlib,json,shutil,sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

GRADLE='app/build.gradle'
SHADER='app/src/main/assets/shaders/preview/main_fs.glsl'
MAIN='app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java'
METER='app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewMeter2D.java'
EVIDENCE='app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewEvidence2E.java'
MATH='app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewTc20Math1A.java'
ID='M9PREVIEWTC20NEG1A'

BASELINE={
 SHADER:'9fe306415cbad0cba4659eb375e698a62da3a5a3f08af0007ecb20bc8333fa27',
 MAIN:'eb4605557173b3d25a1233f65dd1926810f0268033a55c5c87d62cad22416875',
 METER:'131ff5561f08dfa7659a6e1a8c288ca646545516123948bb069d48f963964aed',
 EVIDENCE:'93f17b167f8efc231815fae69e03ed7ebaba27959297ef0e022aedcb80db62a4',
}
MODIFIED={GRADLE,SHADER,MAIN,METER,EVIDENCE}
ADDED={MATH}

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, found {n}')
    return text.replace(old,new,1)

def transform_shader(s):
    s=one(s,
'''uniform float uM9ExposureScale1B;
uniform bool uM9SourceReady2A;''',
'''uniform float uM9ExposureScale1B;
// M9PREVIEWTC20NEG1A: preview-only bounded TC20 darkening prediction.
uniform float uM9PreviewTc20Gain1A;
uniform bool uM9SourceReady2A;''','shader uniform')

    helper=r'''vec3 previewTc20Probe1A(vec3 oes) {
    // Match the still TC20 signal as closely as controlled OES permits:
    // inverse reported tone/CCM/WB -> sensor -> ProPhoto D50 -> linear sRGB D65 luma.
    // Active selected path uses identity HSM. R/G encode one 16-bit linear-luma value.
    if (!uM9SourceReady2A) return vec3(0.0);
    vec3 linear=vec3(inverseChannel2A(oes.r,0),inverseChannel2A(oes.g,1),inverseChannel2A(oes.b,2));
    vec3 sensor=max(uM9InputToSensor2A*linear,vec3(0));
    sensor=min(sensor*uM9ExposureScale1B,uM9ClipWhite2A);
    vec3 pp=clamp(uM9SensorToPp2A*sensor,0.0,1.0);
    const mat3 PP_D50_TO_SRGB_D65=mat3(
         2.03416363,-0.22892257,-0.00855493,
        -0.72742036, 1.23180685,-0.15329898,
        -0.30691264,-0.00284122, 1.16192600);
    vec3 srgbLinear=max(PP_D50_TO_SRGB_D65*pp,vec3(0));
    float y=max(dot(srgbLinear,vec3(.2126,.7152,.0722)),0.0);
    float q=floor(clamp(y,0.0,1.0)*65535.0+.5);
    float hi=floor(q/256.0);
    float lo=q-hi*256.0;
    return vec3(hi/255.0,lo/255.0,0.0);
}

'''
    s=one(s,'vec3 m9DisplayTransform(vec3 oes,vec2 uv) {',helper+'vec3 m9DisplayTransform(vec3 oes,vec2 uv) {','shader probe helper')

    s=one(s,
'''    vec3 m9=max(uM9PpToTarget2A*pp,vec3(0));
    return tungsten2A(curveSat2M9(m9));''',
'''    vec3 m9=max(uM9PpToTarget2A*pp,vec3(0));
    // Same placement seam as the still renderer: gain before SAT2/curve02.
    m9*=clamp(uM9PreviewTc20Gain1A,0.70710678,1.0);
    return tungsten2A(curveSat2M9(m9));''','shader precurve gain')

    s=one(s,
'''    if (uM9EvidenceStage2E == 1) { Output = vec4(photonColor.rgb, 1.0); return; }
    vec4 color = vec4(m9DisplayTransform(photonColor.rgb, uv), 1.0);''',
'''    if (uM9EvidenceStage2E == 1) { Output = vec4(photonColor.rgb, 1.0); return; }
    if (uM9EvidenceStage2E == 2) { Output = vec4(previewTc20Probe1A(photonColor.rgb), 1.0); return; }
    vec4 color = vec4(m9DisplayTransform(photonColor.rgb, uv), 1.0);''','shader evidence stage')
    return s

def transform_main(s):
    s=one(s,
'''        GLES20.glUniform1f(uM9ExposureScale1B, frame1W.exposureScale);
        GLES20.glUniform1i(uM9EvidenceStage2E, 0);''',
'''        final float previewTc20Gain1A = mM9Evidence2E != null
                ? mM9Evidence2E.predictedTc20Gain(frame1W) : 1.0f;
        GLES20.glUniform1f(uM9ExposureScale1B, frame1W.exposureScale);
        GLES20.glUniform1f(uM9PreviewTc20Gain1A, previewTc20Gain1A);
        GLES20.glUniform1i(uM9EvidenceStage2E, 0);''','main bind gain')

    s=one(s,
'''        if (mM9CurveTex != 0 && mM9Meter2D != null)
            mM9Meter2D.sample(frame1W, textureTimestamp1W, uM9ExposureScale1B, enablePeak, peakEnabled);
        if (mM9Evidence2E != null)
            mM9Evidence2E.sample(frame1W, textureTimestamp1W, mSTexture,
                    uM9ExposureScale1B, enablePeak, peakEnabled, uM9EvidenceStage2E);''',
'''        if (mM9CurveTex != 0 && mM9Meter2D != null)
            mM9Meter2D.sample(frame1W, textureTimestamp1W, uM9ExposureScale1B,
                    enablePeak, peakEnabled, uM9PreviewTc20Gain1A, previewTc20Gain1A);
        if (mM9Evidence2E != null)
            mM9Evidence2E.sample(frame1W, textureTimestamp1W, mSTexture,
                    uM9ExposureScale1B, enablePeak, peakEnabled, uM9EvidenceStage2E,
                    uM9PreviewTc20Gain1A, previewTc20Gain1A);''','main probe calls')

    s=one(s,
'''    private int mM9CurveTex, uM9Enabled, uM9Curve, uM9ExposureScale1B;''',
'''    private int mM9CurveTex, uM9Enabled, uM9Curve, uM9ExposureScale1B, uM9PreviewTc20Gain1A;''','main field')

    s=one(s,
'''        uM9ExposureScale1B = GLES20.glGetUniformLocation(hProgram, "uM9ExposureScale1B");''',
'''        uM9ExposureScale1B = GLES20.glGetUniformLocation(hProgram, "uM9ExposureScale1B");
        uM9PreviewTc20Gain1A = GLES20.glGetUniformLocation(hProgram, "uM9PreviewTc20Gain1A");''','main location')
    return s

def transform_meter(s):
    s=one(s,
'''    public void sample(M9PreviewFrameState1W frame,long textureNs,int exposureUniform,
            int peakUniform,int peakValue) {''',
'''    public void sample(M9PreviewFrameState1W frame,long textureNs,int exposureUniform,
            int peakUniform,int peakValue,int tc20Uniform,float displayTc20Gain) {''','meter signature')
    s=one(s,
'''            GLES30.glDisable(GLES30.GL_SCISSOR_TEST);
            GLES30.glUniform1i(peakUniform,0);
            for(int i=0;i<STEPS;i++) {''',
'''            GLES30.glDisable(GLES30.GL_SCISSOR_TEST);
            GLES30.glUniform1i(peakUniform,0);
            // Auto evidence must remain neutral-reference evidence, never display feedback.
            GLES30.glUniform1f(tc20Uniform,1.0f);
            for(int i=0;i<STEPS;i++) {''','meter unity')
    s=one(s,
'''            GLES30.glUniform1f(exposureUniform,frame.exposureScale);
            GLES30.glUniform1i(peakUniform,peakValue);''',
'''            GLES30.glUniform1f(exposureUniform,frame.exposureScale);
            GLES30.glUniform1f(tc20Uniform,displayTc20Gain);
            GLES30.glUniform1i(peakUniform,peakValue);''','meter restore')
    return s

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root)
    if now!=proof['after']: raise SystemExit('PREVIEWTC20 assembled source drift')
    before=proof['before']
    modified={k for k in before if now.get(k)!=before[k]}
    added=set(now)-set(before)
    removed=set(before)-set(now)
    if modified!=MODIFIED or added!=ADDED or removed:
        raise SystemExit('unexpected source delta modified=%r added=%r removed=%r'%
                         (sorted(modified),sorted(added),sorted(removed)))
    if (root/EVIDENCE).read_bytes()!=(HERE/'M9PreviewEvidence2E.java').read_bytes():
        raise SystemExit('preview evidence candidate mismatch')
    if (root/MATH).read_bytes()!=(HERE/'M9PreviewTc20Math1A.java').read_bytes():
        raise SystemExit('preview TC20 math mismatch')
    shader=(root/SHADER).read_text();main=(root/MAIN).read_text();meter=(root/METER).read_text()
    for marker in ['M9PREVIEWTC20NEG1A','uM9PreviewTc20Gain1A','previewTc20Probe1A','PP_D50_TO_SRGB_D65']:
        if marker not in shader: raise SystemExit('shader marker missing '+marker)
    if 'GLES30.glUniform1f(tc20Uniform,1.0f);' not in meter:
        raise SystemExit('Auto meter does not neutralize preview TC20')
    if main.count('predictedTc20Gain(frame1W)')!=1:
        raise SystemExit('MainRenderer preview TC20 owner mismatch')
    gradle=(root/GRADLE).read_text()
    if "versionName '1.70-m9previewtc20neg1a-tg1'" not in gradle or 'versionCode 26690' not in gradle:
        raise SystemExit('preview TC20 build identity mismatch')
    return {
      'revision':ID,'version':'1.70-m9previewtc20neg1a-tg1','versionCode':26690,
      'modified':sorted(MODIFIED),'added':sorted(ADDED),
      'previewTc20AuthorityEv':[-0.5,0.0],
      'positiveTc20Prediction':False,
      'autoMeterTc20ForcedUnity':True,
      'placement':'M9_target_pre_SAT2_curve02',
      'stillRenderer_capture_Auto_JPEG_DNG_unchanged':True,
      'device_validation_pending':True,
    }

def main(root):
    root=root.resolve();receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists(): print(json.dumps(verify(root),indent=2));return
    for rel,expected in BASELINE.items():
        actual=sha(root/rel)
        if actual!=expected: raise SystemExit(f'PREVIEWTC20 baseline mismatch {rel}: {actual}')
    if (root/MATH).exists(): raise SystemExit('preview TC20 helper already exists')
    gradle=(root/GRADLE).read_text()
    if "versionName '1.69-m9autoexposurefinish1b-tg1'" not in gradle or 'versionCode 26689' not in gradle:
        raise SystemExit('PREVIEWTC20 requires exact AUTOEXPOSUREFINISH1B build identity')

    before=inventory(root)
    (root/SHADER).write_text(transform_shader((root/SHADER).read_text()))
    (root/MAIN).write_text(transform_main((root/MAIN).read_text()))
    (root/METER).write_text(transform_meter((root/METER).read_text()))
    shutil.copyfile(HERE/'M9PreviewEvidence2E.java',root/EVIDENCE)
    shutil.copyfile(HERE/'M9PreviewTc20Math1A.java',root/MATH)
    gradle=one(gradle,'versionCode 26689','versionCode 26690','version code')
    gradle=one(gradle,"versionName '1.69-m9autoexposurefinish1b-tg1'",
               "versionName '1.70-m9previewtc20neg1a-tg1'",'version name')
    (root/GRADLE).write_text(gradle)
    after=inventory(root)
    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__': main(Path(sys.argv[1]))
