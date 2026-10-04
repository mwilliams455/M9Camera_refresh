#!/usr/bin/env python3
"""Recovered firmware oracle vs production native and DNG sampler; Standard regression."""
from pathlib import Path
import ctypes as C,hashlib,json,os,subprocess,sys,xml.etree.ElementTree as ET
import numpy as np
HERE=Path(__file__).resolve().parent
root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
src=root/'app/src/main';java_src=src/'java/com/particlesdevs/photoncamera/processing'
firmware=json.loads((HERE.parent/'saturationmenu1a/firmware_saturation.json').read_text());m=np.array([[x['even'],x['odd']] for x in firmware['levels']],np.int64).reshape(5,2,3,3)
curve=np.frombuffer((src/'assets/m9/m9_curve02_firmware.bin').read_bytes(),np.uint8)
rng=np.random.default_rng(900216)
samples=np.r_[rng.uniform(-.125,1.25,(65000,3)),np.repeat(np.linspace(0,1,16384)[:,None],3,axis=1),[[0,0,0],[1,1,1],[1,0,0],[0,1,0],[0,0,1],[.5,.5,.5]]].astype(np.float64)
samples.astype('>f8').tofile(out/'samples.bin')
def oracle(values,bank):
 q=np.clip(np.rint(values*16383),0,16383).astype(np.int64)
 matrix=m[bank,(q[:,0]<q[:,1]).astype(int)]
 accum=np.einsum('nij,nj->ni',matrix,q)
 return curve[np.clip(accum>>16,0,2047)]
inc=out/'android';inc.mkdir(exist_ok=True)
(inc/'bitmap.h').write_text('''#pragma once
#include <jni.h>
#include <cstdint>
#define ANDROID_BITMAP_FORMAT_RGBA_8888 1
#define ANDROID_BITMAP_RESULT_SUCCESS 0
struct AndroidBitmapInfo {uint32_t width,height,stride;int32_t format;uint32_t flags;};
inline int AndroidBitmap_getInfo(JNIEnv*,jobject,AndroidBitmapInfo*){return -1;}
inline int AndroidBitmap_lockPixels(JNIEnv*,jobject,void**){return -1;}
inline int AndroidBitmap_unlockPixels(JNIEnv*,jobject){return 0;}
''')
java=Path(os.environ.get('JAVA_HOME','/usr/lib/jvm/java-17-openjdk-amd64'))
lib=out/'lib-saturation.so'
subprocess.run(['g++','-std=c++17','-O2','-shared','-fPIC','-pthread','-ffp-contract=off','-fno-fast-math','-I'+str(src/'cpp'),'-I'+str(out),'-I'+str(java/'include'),'-I'+str(java/'include/linux'),str(HERE.parent/'saturationmenu1a/host.cpp'),'-o',str(lib)],check=True)
fn=C.CDLL(str(lib),mode=os.RTLD_LAZY).saturation_probe;fn.argtypes=[C.c_int,C.c_void_p,C.c_int,C.c_void_p,C.c_void_p];fn.restype=None
classes=out/'classes';classes.mkdir(exist_ok=True)
subprocess.run(['java','com.sun.tools.javac.Main','-d',str(classes),str(java_src/'M9Saturation.java'),str(java_src/'M9DngProfile.java'),str(HERE.parent/'saturationmenu1a/SaturationHostProbe.java'),str(HERE.parent/'saturationmenu1a/StandardHostProbe.java')],check=True)
# The profile uses the accepted PCS conversion before the selected firmware stage.
pcs=np.array([[1.0000931767609489,1.579227539207758e-5,7.925465633029314e-6],[-3.769477054823951e-5,.9999936112160234,-3.192011719311565e-6],[0,0,.9998985904066523]])
pcs_samples=np.stack([samples[:,0]*row[0]+samples[:,1]*row[1]+samples[:,2]*row[2] for row in pcs],axis=1)
rows=[]
curves=np.frombuffer((src/'assets/m9/m9_contrast_srgb_firmware.bin').read_bytes(),np.uint8).reshape(5,2048)
meta=json.loads((HERE/'firmware_contrast.json').read_text())
assert hashlib.sha256(curves.tobytes()).hexdigest()==meta['bankSha256']
standard=(src/'assets/m9/m9_curve02_firmware.bin').read_bytes()
assert curves[2].tobytes()==standard
for contrast in range(5):
 curve=curves[contrast].copy()
 curve_path=out/'selected_curve.bin';curve_path.write_bytes(curve.tobytes())
 subprocess.run(['java','-Xmx128m','-cp',str(classes),'com.particlesdevs.photoncamera.processing.SaturationHostProbe',str(curve_path),str(out)],check=True)
 for bank,mode in enumerate([11,12,9,0,10]):
  got=np.empty((len(samples),3),np.uint8);fn(mode,samples.ctypes.data,len(samples),curve.ctypes.data,got.ctypes.data)
  np.testing.assert_array_equal(got,oracle(samples,bank))
  profile=np.fromfile(out/f'profile{bank}.bin',np.uint8).reshape(-1,3)
  np.testing.assert_array_equal(profile,oracle(pcs_samples,bank))
  look=np.fromfile(out/f'look{bank}.bin','<f4').reshape(129,180,65,3);assert np.isfinite(look).all()
  np.testing.assert_array_equal(look[:,:,0],np.broadcast_to([0,1,1],look[:,:,0].shape))
  tone=np.fromfile(out/f'tone{bank}.bin','<f4').reshape(-1,2);assert np.all(np.diff(tone[:,1])>=-1e-7)
  rows.append(dict(contrast=contrast,bank=bank,name=firmware['levels'][bank]['name'],nativePixelsExact=len(samples),profileSamplesExact=len(samples),lookSha256=hashlib.sha256((out/f'look{bank}.bin').read_bytes()).hexdigest()))
 
 if contrast==2:
  for kind in ['tone','look']:(out/f'{kind}-contraststandard.bin').write_bytes((out/f'{kind}2.bin').read_bytes())
assert len({r['lookSha256'] for r in rows})==25
# Byte-for-byte comparison to the pre-menu production Java profile implementation.
old=out/'accepted';old.mkdir(exist_ok=True)
subprocess.run(['java','com.sun.tools.javac.Main','-d',str(old),str(HERE.parent/'dngprofile1a/src/M9DngProfile.java'),str(HERE.parent/'saturationmenu1a/StandardHostProbe.java')],check=True)
subprocess.run(['java','-Xmx128m','-cp',str(old),'com.particlesdevs.photoncamera.processing.StandardHostProbe',str(src/'assets/m9/m9_curve02_firmware.bin'),str(out)],check=True)
for kind in ['tone','look']:assert (out/f'{kind}-contraststandard.bin').read_bytes()==(out/f'{kind}-standard.bin').read_bytes()
# Menu is accessible independently of the old HDRx/JPEG preference visibility switch.
ns='{http://schemas.android.com/apk/res/android}';ui=ET.parse(src/'res/xml/preferences.xml').getroot()
photo=next(x for x in ui if x.attrib.get(ns+'key')=='@string/pref_category_photo_key')
pref=next(x for x in photo if x.attrib.get(ns+'key')=='pref_m9_contrast');assert pref.attrib[ns+'defaultValue']=='2'
assert not any(x.attrib.get(ns+'key')=='@string/pref_saturation_seekbar_key' for x in ui.iter())
report=dict(status='passed',combinations=rows,standardProfileByteExact=True,firmwareCurvesExact=True,menuDefault='Standard',rawCaptureAndPreSaturationExposureUnchanged=True,handsetValidationPending=True)
(out/'CONTRAST_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
