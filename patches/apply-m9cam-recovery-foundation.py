#!/usr/bin/env python3
from pathlib import Path
import re, shutil, sys
if len(sys.argv)!=2: raise SystemExit("usage: apply-m9cam-recovery-foundation.py <PhotonCamera-root>")
root=Path(sys.argv[1]).resolve(); here=Path(__file__).resolve().parent; src=here/'recovery_foundation'
if not (root/'app').is_dir(): raise SystemExit(f"not a PhotonCamera root: {root}")
def read(rel): return (root/rel).read_text()
def write(rel,s): (root/rel).write_text(s)
def add_import(t,anchor,imp):
    if imp.strip() in t:return t
    if anchor not in t: raise SystemExit(f"foundation: import anchor missing: {imp.strip()}")
    return t.replace(anchor,anchor+imp,1)
def must(t,old,new,label):
    if old not in t: raise SystemExit(f"foundation: anchor missing for {label}")
    return t.replace(old,new,1)

# Install recovered/reconstructed foundational M9 sources.
dst=root/'app/src/main/java/com/particlesdevs/photoncamera/m9'; dst.mkdir(parents=True,exist_ok=True)
for name in ['M9Config.java','M9ProcessingRoute.java','M9CaptureMetadataWriter.java','M9ExposureDiagnostics.java','M9SubjectMotionAnalyzer.java','M9ModernExposurePolicy.java']:
    shutil.copy2(src/name,dst/name)

# Build identity and separate app id.
g=read('app/build.gradle')
g=re.sub(r"applicationId\s+'com\.particlesdevs\.photoncamera'","applicationId 'com.m9project.m9cam.photon'",g,count=1)
g=re.sub(r"versionName\s+'0\.97(?:-m9[^']*)?'","versionName '0.97-m9modern6'",g,count=1)
g=g.replace('outputFileName = "PhotonCamera-${versionName}${versionBuild}-${variant.name}.apk"','outputFileName = "M9Cam-Photon-${versionName}${versionBuild}-${variant.name}.apk"')
write('app/build.gradle',g)
for rel in ['app/src/main/res/values/strings.xml','app/src/main/res/values-ko-rKR/strings.xml']:
    p=root/rel
    if p.exists(): p.write_text(re.sub(r'<string name="app_name" translatable="false">[^<]*</string>','<string name="app_name" translatable="false">M9Cam Photon Test</string>',p.read_text(),count=1))

# Tolerate transient upstream stale post-pipeline references, as the original v0.6 did.
post_dir=root/'app/src/main/java/com/particlesdevs/photoncamera/processing/opengl/postpipeline'; post=post_dir/'PostPipeline.java'; registry=root/'app/src/main/java/com/particlesdevs/photoncamera/settings/TunableRegistry.java'
missing=[n for n in ['LinearExposure','HeadroomRender','AutoExposureCurve','LocalLaplacian'] if not (post_dir/f'{n}.java').exists()]
if missing and post.exists():
    t=post.read_text()
    for n in missing:t=re.sub(r'^\s*add\(new\s+'+re.escape(n)+r'\(\)\);\s*$','        // M9 recovery build-compat: absent upstream '+n,t,flags=re.M)
    post.write_text(t)
    if registry.exists():
        t=registry.read_text()
        for n in missing:t=re.sub(r'^\s*com\.particlesdevs\.photoncamera\.processing\.opengl\.postpipeline\.'+re.escape(n)+r'\.class,?\s*$','        // M9 recovery build-compat: absent '+n,t,flags=re.M)
        registry.write_text(t)

# One-frame selector.
rel='app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java';t=read(rel);t=add_import(t,'import com.particlesdevs.photoncamera.app.PhotonCamera;\n','import com.particlesdevs.photoncamera.m9.M9Config;\n')
if 'if (M9Config.isCaptureTest())' not in t:t=must(t,'    public static int getFrames() {\n','    public static int getFrames() {\n        if (M9Config.isCaptureTest()) { frameCount = 1; throwCount = 0; return 1; }\n','FrameNumberSelector')
write(rel,t)

# Foundation DefaultSaver route. Keep exact marker consumed by cumulative v0.7 overlay.
rel='app/src/main/java/com/particlesdevs/photoncamera/processing/DefaultSaver.java';t=read(rel);t=add_import(t,'import com.particlesdevs.photoncamera.processing.processor.RawVideoProcessor;\n','import com.particlesdevs.photoncamera.m9.M9CaptureMetadataWriter;\nimport com.particlesdevs.photoncamera.m9.M9Config;\n')
if '// M9 milestone: one untouched RAW + diagnostics' not in t:
    anchor='        Log.d(TAG,"Size:"+IMAGE_BUFFER.size());\n'
    block='''        Log.d(TAG,"Size:"+IMAGE_BUFFER.size());
        // M9 milestone: one untouched RAW + diagnostics, then stop before Hdrx/PostPipeline.
        if (M9Config.isCaptureTest()) {
            Path dngFile = ImagePath.newDNGFilePath();
            ImageFrame frame = IMAGE_BUFFER.get(0);
            boolean imageSaved = false;
            try {
                imageSaved = ImageSaver.Util.saveSingleRaw(dngFile, frame, characteristics, captureResult, cameraRotation);
                M9CaptureMetadataWriter.write(dngFile, frame, characteristics, captureResult, captureRequest, cameraRotation);
                processingEventsListener.notifyImageSavedStatus(imageSaved, dngFile);
                processingEventsListener.onProcessingFinished(imageSaved ? "M9 Capture Test: RAW + metadata saved" : "M9 Capture Test: RAW save failed");
            } finally {
                frame.close(); IMAGE_BUFFER.clear(); bufferLock = false;
            }
            return;
        }
'''
    if anchor not in t:
        m=re.search(r'\s*Log\.d\(TAG,\s*"Size:"\s*\+\s*IMAGE_BUFFER\.size\(\)\);\s*',t)
        if not m: raise SystemExit('foundation: DefaultSaver size anchor missing')
        t=t[:m.start()]+block+t[m.end():]
    else:t=t.replace(anchor,block,1)
write(rel,t)

# Exposure seams recovered from v0.6.
rel='app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java';t=read(rel);t=add_import(t,'import com.particlesdevs.photoncamera.app.PhotonCamera;\n','import com.particlesdevs.photoncamera.m9.M9Config;\nimport com.particlesdevs.photoncamera.m9.M9ExposureDiagnostics;\nimport com.particlesdevs.photoncamera.m9.M9ModernExposurePolicy;\n')
if 'M9ExposureDiagnostics.begin' not in t:
    a='        pair.ExpoCompensateLower(1.0/compensation);\n';ins=a+'''        if (M9Config.isCaptureTest()) {
            M9ExposureDiagnostics.begin(captureController.mPreviewIso, captureController.mPreviewExposureTime,
                    getISOLOW(), getISOHIGH(), getISOAnalog(), getEXPLOW(), getEXPHIGH(), compensation,
                    PhotonCamera.getSettings().selectedMode.name(), useTripod);
            M9ExposureDiagnostics.recordNormalizedTarget(pair.iso, pair.exposure);
        }
''';t=must(t,a,ins,'IsoExpo begin')
if 'm9NominalCapStart' not in t:
    a='        double dynamicFactor = getDynamicScalingFactor();\n';t=must(t,a,'        long m9NominalCapStart = capStart;\n        long m9NominalCapEnd = capEnd;\n'+a,'nominal caps')
if 'm9ScaledCapStart' not in t:
    a='        capEnd = (long) (capEnd * dynamicFactor);\n';t=must(t,a,a+'        long m9ScaledCapStart = capStart;\n        long m9ScaledCapEnd = capEnd;\n','scaled caps')
if 'M9ExposureDiagnostics.recordCaps' not in t:
    a='        pair.applyShutterPriorityCurve(capStart, capEnd, CAP_RAMP_STOPS);\n'
    ins='''        long m9PhotonCapStart = capStart;
        long m9PhotonCapEnd = capEnd;
        if (M9Config.isCaptureTest()) {
            ExpoPair m9PhotonReference = new ExpoPair(pair);
            m9PhotonReference.applyShutterPriorityCurve(m9PhotonCapStart, m9PhotonCapEnd, CAP_RAMP_STOPS);
            M9ExposureDiagnostics.recordPhotonCurrentReference(m9PhotonReference.iso, m9PhotonReference.exposure, m9PhotonCapStart, m9PhotonCapEnd);
        }
        if (M9Config.isM9Modern()
                && PhotonCamera.getSettings().selectedMode == CameraMode.PHOTO
                && !useTripod) {
            M9ModernExposurePolicy.Decision m9Decision = M9ModernExposurePolicy.adjustCaps(pair.exposure, pair.iso, pair.isoanalog, capStart, capEnd);
            capStart = m9Decision.capStartNs; capEnd = m9Decision.capEndNs;
        }
        if (M9Config.isCaptureTest()) {
            int m9Gyro = PhotonCamera.getGyro() != null ? PhotonCamera.getGyro().getFilteredShakiness() : -1;
            M9ExposureDiagnostics.recordCaps(m9NominalCapStart, m9NominalCapEnd, dynamicFactor, m9Gyro, m9ScaledCapStart, m9ScaledCapEnd, m9PhotonCapStart, m9PhotonCapEnd);
            M9ExposureDiagnostics.recordCurveInput(pair.exposure, pair.iso, capStart, capEnd, CAP_RAMP_STOPS);
        }
        pair.applyShutterPriorityCurve(capStart, capEnd, CAP_RAMP_STOPS);
        if (M9Config.isCaptureTest()) M9ExposureDiagnostics.recordCurveOutput(pair.iso, pair.exposure);
'''
    t=must(t,a,ins,'curve seam')
if 'M9ExposureDiagnostics.recordFinalNormalized' not in t:
    a='        pair.denormalizeSystem();\n        return pair;\n';idx=t.rfind(a)
    if idx<0: raise SystemExit('foundation: final denormalize seam missing')
    ins='''        if (M9Config.isCaptureTest()) {
            M9ExposureDiagnostics.recordFinalNormalized(pair.iso, pair.exposure,
                    pair.isIsoLimited, pair.isShutterLimited, pair.isIsoManualOverLimit, pair.isShutterManualOverLimit);
        }
        pair.denormalizeSystem();
        if (M9Config.isCaptureTest()) M9ExposureDiagnostics.recordFinalSystem(pair.iso, pair.exposure);
        return pair;
''';t=t[:idx]+ins+t[idx+len(a):]
write(rel,t)

# CPU YUV analysis stream. Mirrors the accepted v0.5.3/v0.6 integration but is whitespace tolerant.
rel='app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java';t=read(rel);t=add_import(t,'import com.particlesdevs.photoncamera.app.PhotonCamera;\n','import com.particlesdevs.photoncamera.m9.M9Config;\nimport com.particlesdevs.photoncamera.m9.M9SubjectMotionAnalyzer;\n')
if 'M9SubjectMotionAnalyzer.onImage' not in t:
    s=t.find('mOnYuvImageAvailableListener');e=t.find('mOnRawImageAvailableListener',s+1)
    if s<0 or e<0:raise SystemExit('foundation: YUV listener region missing')
    seg=t[s:e];old='            mImageSaver.initProcess(reader);'
    if old not in seg: raise SystemExit('foundation: YUV saver call missing')
    repl='''            if (M9Config.isCaptureTest()) {
                Image image = null;
                try { image = reader.acquireLatestImage(); if (image != null) M9SubjectMotionAnalyzer.onImage(image); }
                catch (Exception ex) { Log.d(TAG, "M9 subject-motion analysis failed: " + Log.getStackTraceString(ex)); }
                finally { if (image != null) image.close(); }
                return;
            }
            mImageSaver.initProcess(reader);'''
    seg=seg.replace(old,repl,1);t=t[:s]+seg+t[e:]
# Force preview reader to YUV in each initialization block.
if 'M9 recovery diagnostic YUV' not in t:
    pat=re.compile(r'if\s*\(PhotonCamera\.getSettings\(\)\.previewFormat\s*!=\s*0\)\s*\{\s*mPreviewTargetFormat\s*=\s*PhotonCamera\.getSettings\(\)\.previewFormat;\s*\}\s*else\s*\{\s*mPreviewTargetFormat\s*=\s*ImageFormat\.JPEG;\s*\}')
    ms=list(pat.finditer(t));offset=0
    if not ms: raise SystemExit('foundation: preview format blocks missing')
    for m in ms:
        a,b=m.start()+offset,m.end()+offset;orig=t[a:b];extra=orig+'\n        // M9 recovery diagnostic YUV.\n        if (M9Config.isCaptureTest()) { mPreviewTargetFormat = ImageFormat.YUV_420_888; M9SubjectMotionAnalyzer.reset(); }'
        t=t[:a]+extra+t[b:];offset+=len(extra)-len(orig)
# Add analysis surface to capture session when Photon otherwise uses previewFormat 0.
if 'M9 recovery analysis surface' not in t:
    pat=re.compile(r'(?P<indent>\s*)if\s*\(PhotonCamera\.getSettings\(\)\.previewFormat\s*==\s*0\)\s*\{\s*surfaces\s*=\s*Arrays\.asList\(surface,\s*mImageReaderRaw\.getSurface\(\)\);\s*\}')
    m=pat.search(t)
    if not m: raise SystemExit('foundation: session surfaces anchor missing')
    orig=m.group(0);indent=m.group('indent');extra=orig+indent+'// M9 recovery analysis surface\n'+indent+'if (M9Config.isCaptureTest()) { surfaces = Arrays.asList(surface, mImageReaderPreview.getSurface(), mImageReaderRaw.getSurface()); }'
    t=t[:m.start()]+extra+t[m.end():]
if 'M9 recovery repeating analysis target' not in t:
    a='        mPreviewRequestBuilder.addTarget(surface);\n'
    if a not in t: raise SystemExit('foundation: repeating preview target missing')
    t=t.replace(a,a+'        // M9 recovery repeating analysis target\n        if (M9Config.isCaptureTest() && mImageReaderPreview != null) mPreviewRequestBuilder.addTarget(mImageReaderPreview.getSurface());\n',1)
write(rel,t)
print('M9 recovery foundation applied')
