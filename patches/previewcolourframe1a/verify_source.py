from pathlib import Path
import hashlib,json,sys,xml.etree.ElementTree as ET
parent,root,out=map(lambda s:Path(s).resolve(),sys.argv[1:]);here=Path(__file__).resolve().parent
manifest=json.loads((here/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(here/'preview.patch')==manifest['patchSha256']
for n,h in manifest['parentFiles'].items():assert sha(parent/n)==h,n
for n,h in manifest['fileOverrides'].items():assert sha(root/n)==h,n
def files(p):
 result={f.relative_to(p).as_posix():f for tree in ['app/src','circularbarlib/src'] for f in (p/tree).rglob('*') if f.is_file()};result['app/build.gradle']=p/'app/build.gradle';return result
a,b=files(parent),files(root);assert not a.keys()-b.keys()
changed={n for n in b if n not in a or sha(a[n])!=sha(b[n])};assert changed==set(manifest['fileOverrides'])
J='app/src/main/java/com/particlesdevs/photoncamera/';A='app/src/main/assets/'
frozen=[n for n in a if n.startswith((J+'m9/render/',J+'m9/export/',J+'processing/',J+'capture/','app/src/main/cpp/',A+'m9/'))]
for n in frozen:assert n not in changed,n
for n in [J+'m9/M9ExposurePlan1A.java',J+'manual/ParamController.java',J+'m9/preview/M9AutoExposure2D.java',J+'m9/preview/M9TapMeter1A.java',J+'m9/preview/M9GpuPreview2A.java',J+'m9/preview/M9PreviewMath2A.java']:assert n not in changed,n
# Exact colour function text is frozen, including exposure, firmware and tungsten seams.
pfs=(parent/(A+'shaders/preview/main_fs.glsl')).read_text();cfs=(root/(A+'shaders/preview/main_fs.glsl')).read_text()
for function in ['vec3 srgbToLinearM9','float inverseTexel2C','float inverseChannel2A','vec3 curveSat2M9','vec3 tungsten2A','vec4 previewTc20Probe1A','vec3 m9DisplayTransform']:
 assert pfs.split(function,1)[1].split('\n}',1)[0]==cfs.split(function,1)[1].split('\n}',1)[0],function
assert cfs.count('texture(sTexture, cameraUv1A(')==2
main=(root/(J+'ui/camera/views/viewfinder/MainRenderer.java')).read_text()
assert 'surface.getTransformMatrix(mCameraTextureMatrix)' in main
assert 'multiplyMM(mCameraSamplingMatrix,0,mCameraTextureMatrix,0,LEGACY_TO_GL,0)' in main
assert 'm9TapViewport1A,mTapGeometryTransforms,mMirrorPreview' in main
assert main.count('1, false, mCameraSamplingMatrix, 0)')==2
old=ET.parse(parent/'app/src/main/res/values/m9_ev.xml').getroot();new=ET.parse(root/'app/src/main/res/values/m9_ev.xml').getroot()
values=lambda tree:[n.text for n in tree.find("string-array[@name='m9_ev_values']")]
assert values(old)==values(new)
labels=[n.text for n in new.find("string-array[@name='m9_ev_entries']")]
expected=[('0.0' if n==0 else ('+' if n>0 else '−')+f'{abs(n/3):.1f}')+' EV' for n in range(-9,10)]
assert labels==expected
report=dict(status='passed',revision='M9PREVIEWCOLOURFRAME1A',changedFiles=sorted(changed),unchangedFiles=len(set(a)-changed),frozenPhotographicFiles=len(frozen),exactThirdsUnchanged=True,decimalLabels=labels,savedRendererDngCaptureUnchanged=True,previewColourFunctionsUnchanged=True,meteringPolicyUnchanged=True,textureMatrixUsedBySharpBlurPeakingAndSharedProbes=True,phoneValidationPending=True)
out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
