#!/usr/bin/env python3
"""Compile the real preview fragment shader and exercise its saturation function on Mesa GLES."""
from pathlib import Path
import ctypes as C,json,sys
import numpy as np
here=Path(__file__).resolve().parent;root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
E=C.CDLL('libEGL.so.1');P=C.c_void_p;I=C.c_int;U=C.c_uint;F=C.c_float
E.eglGetProcAddress.argtypes=[C.c_char_p];E.eglGetProcAddress.restype=P
def gl(name,ret,*args):return C.CFUNCTYPE(ret,*args)(E.eglGetProcAddress(name.encode()))
def egl(name,ret,*args):
 f=getattr(E,name);f.argtypes=args;f.restype=ret;return f
display=gl('eglGetPlatformDisplayEXT',P,U,P,P)(0x31dd,None,None)
assert egl('eglInitialize',U,P,P,P)(display,None,None)
assert egl('eglBindAPI',U,U)(0x30a0)
attrs=(I*13)(0x3033,1,0x3040,0x40,0x3024,8,0x3023,8,0x3022,8,0x3021,8,0x3038)
config=P();count=I();assert egl('eglChooseConfig',U,P,P,P,I,P)(display,attrs,C.byref(config),1,C.byref(count)) and count.value
context=egl('eglCreateContext',P,P,P,P,P)(display,config,None,(I*3)(0x3098,3,0x3038));assert context
surface=egl('eglCreatePbufferSurface',P,P,P,P)(display,config,(I*5)(0x3057,1,0x3056,1,0x3038));assert surface
assert egl('eglMakeCurrent',U,P,P,P,P)(display,surface,surface,context)
def shader(kind,source):
 obj=gl('glCreateShader',U,U)(kind);b=source.encode();ptr=C.c_char_p(b)
 gl('glShaderSource',None,U,I,P,P)(obj,1,C.byref(ptr),None);gl('glCompileShader',None,U)(obj)
 ok=I();gl('glGetShaderiv',None,U,U,P)(obj,0x8b81,C.byref(ok))
 log=C.create_string_buffer(65536);gl('glGetShaderInfoLog',None,U,I,P,P)(obj,len(log),None,log)
 assert ok.value,log.value.decode();return obj
source=(root/'app/src/main/assets/shaders/preview/main_fs.glsl').read_text()
shader(0x8b30,'#version 300 es\n'+source)
# Exercise the actual display/probe functions; only replace the OES texture input
# with a uniform so the test does not require an Android camera surface.
def program_for(text,probe=False):
 body=text[:text.index('void main()')]
 expr='previewTc20Probe1A(uInput)' if probe else 'vec4(m9DisplayTransform(uInput,vec2(0)),1)'
 f=shader(0x8b30,'#version 300 es\n'+body+'\nuniform vec3 uInput;void main(){Output='+expr+';}')
 v=shader(0x8b31,'#version 300 es\nvoid main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.0-1.0,0,1);}')
 pr=gl('glCreateProgram',U)()
 for sh in [v,f]:gl('glAttachShader',None,U,U)(pr,sh)
 gl('glLinkProgram',None,U)(pr);ok=I();gl('glGetProgramiv',None,U,U,P)(pr,0x8b82,C.byref(ok));assert ok.value
 return pr
candidate=program_for(source);probe=program_for(source,True)
parent=Path(sys.argv[3]).resolve()
control=program_for((parent/'app/src/main/assets/shaders/preview/main_fs.glsl').read_text())
curve=np.frombuffer((root/'app/src/main/assets/m9/m9_contrast_srgb_firmware.bin').read_bytes(),np.uint8).reshape(5,2048)
inv=np.zeros((2,1024,4),np.uint8)
q=np.rint(np.arange(1024)*65535/1023).astype(np.uint16)
for c in range(3):inv[0,:,c]=q>>8;inv[1,:,c]=q&255
for unit,data,internal,fmt,w,h in [(1,curve,0x8229,0x1903,2048,5),(2,inv,0x8058,0x1908,1024,2)]:
 tex=U();gl('glGenTextures',None,I,P)(1,C.byref(tex));gl('glActiveTexture',None,U)(0x84c0+unit);gl('glBindTexture',None,U,U)(0x0de1,tex)
 for pn in [0x2800,0x2801]:gl('glTexParameteri',None,U,U,I)(0x0de1,pn,0x2600)
 gl('glTexImage2D',None,U,I,I,I,I,I,U,U,P)(0x0de1,0,internal,w,h,0,fmt,0x1401,data.ctypes.data)
identity=np.eye(3,dtype=np.float32);pixel=np.zeros(4,np.uint8)
for pr in [candidate,control,probe]:
 gl('glUseProgram',None,U)(pr)
 loc=lambda n:gl('glGetUniformLocation',I,U,C.c_char_p)(pr,n.encode())
 for name,value in [('uM9Enabled',1),('uM9SourceReady2A',1),('uM9Curve',1),('uM9Inverse2A',2)]:gl('glUniform1i',None,I,I)(loc(name),value)
 for name in ['uM9InputToSensor2A','uM9SensorToPp2A','uM9PpToTarget2A']:gl('glUniformMatrix3fv',None,I,I,U,P)(loc(name),1,0,identity.ctypes.data)
 gl('glUniform3f',None,I,F,F,F)(loc('uM9ClipWhite2A'),1,1,1)
gl('glViewport',None,I,I,I,I)(0,0,1,1);gl('glDisable',None,U)(0x0bd0);gl('glDisable',None,U)(0x0be2)
def draw(pr,rgb,gain=1,exposure=1,bank=2,contrast=2,ready=1):
 gl('glUseProgram',None,U)(pr);loc=lambda n:gl('glGetUniformLocation',I,U,C.c_char_p)(pr,n.encode())
 for name,value in [('uM9SaturationBank',bank),('uM9ContrastLevel',contrast),('uM9SourceReady2A',ready)]:gl('glUniform1i',None,I,I)(loc(name),value)
 gl('glUniform3f',None,I,F,F,F)(loc('uInput'),*map(float,rgb))
 gl('glUniform1f',None,I,F)(loc('uM9PreviewTc20Gain1A'),gain)
 gl('glUniform1f',None,I,F)(loc('uM9ExposureScale1B'),exposure)
 gl('glDrawArrays',None,U,I,I)(4,0,3)
 gl('glReadPixels',None,I,I,I,I,U,U,P)(0,0,1,1,0x1908,0x1401,pixel.ctypes.data)
 return pixel.copy()
firmware=json.loads((here.parent/'saturationmenu1a/firmware_saturation.json').read_text())
m=np.array([[x['even'],x['odd']] for x in firmware['levels']],np.int64).reshape(5,2,3,3)
def inverse_rgb(rgb):return np.interp(np.array(rgb,dtype=np.float32),np.arange(1024)/1023,q/65535).astype(np.float32)
def oracle(rgb,gain,exposure,bank,contrast):
 sensor=np.minimum(inverse_rgb(rgb)*np.float32(exposure),1)
 c=np.rint(np.clip(sensor*np.float32(gain)*np.float32(16383),0,16383)).astype(np.int64)
 encoded=curve[contrast,np.clip((m[bank,int(c[0]<c[1])]@c)>>16,0,2047)].astype(np.int64)
 r,g,b=encoded;y=(4899*r+9617*g+1868*b)>>14
 cb=((-2765*r-5427*g+8192*b)>>14);cr=((8192*r-6860*g-1332*b)>>14)
 cb=((cb+128)&255)-128;cr=((cr+128)&255)-128
 return np.floor(np.clip([y+1.402*cr,y-.344136*cb-.714136*cr,y+1.772*cb],0,255)+.5).astype(np.uint8)
inputs=np.r_[np.random.default_rng(232).uniform(.002,.8,(18,3)),[[0,0,0],[.02,.02,.02],[.08,.08,.08],[.15,.15,.15],[.4,.4,.4],[1,1,1]]]
maxerr=0;legacy=0;positive=0
for bank in range(5):
 for contrast in range(5):
  for rgb in inputs:
   for gain in [2**-.5,1]:
    np.testing.assert_array_equal(draw(candidate,rgb,gain,bank=bank,contrast=contrast),draw(control,rgb,gain,bank=bank,contrast=contrast));legacy+=1
   for gain in [2**.125,2**.3,2**.5]:
    actual=draw(candidate,rgb,gain,bank=bank,contrast=contrast)[:3]
    expected=oracle(rgb,gain,1,bank,contrast)
    error=int(np.max(np.abs(actual.astype(int)-expected.astype(int))));maxerr=max(maxerr,error)
    assert error<=1,(rgb,gain,bank,contrast,actual,expected);positive+=1
# Incomplete contracts retain the accepted exposure-only fallback, even with lift supplied.
for rgb in inputs:
 np.testing.assert_array_equal(draw(candidate,rgb,2**.5,ready=0),draw(control,rgb,1,ready=0))
# New packed headroom is taken before native white clipping, with no tone gain feedback.
mat=np.array([[2.03416363,-.72742036,-.30691264],[-.22892257,1.23180685,-.00284122],[-.00855493,-.15329898,1.16192600]],np.float32)
probeError=0
for rgb in inputs:
 for exposure in [.5,1,2]:
  px=draw(probe,rgb,1,exposure)
  np.testing.assert_array_equal(px,draw(probe,rgb,2**.5,exposure))
  sensor=inverse_rgb(rgb)*np.float32(exposure)
  pp=np.clip(sensor,0,1);y=max(float(np.dot(np.maximum(mat@pp,0),[.2126,.7152,.0722])),0)
  expected=np.rint(np.clip([y,np.max(sensor)],0,1)*65535).astype(int)
  actual=np.array([int(px[0])*256+int(px[1]),int(px[2])*256+int(px[3])])
  error=int(np.max(np.abs(expected-actual)));probeError=max(probeError,error);assert error<=1,(rgb,exposure,expected,actual)
# EV remains upstream sensor energy; it is not divided out by the display correction.
for gain in [1,2**.3]:
 vals=[draw(candidate,[.05,.05,.05],gain,exp)[0] for exp in [.5,1,2]]
 assert vals[0]<vals[1]<vals[2],vals
assert gl('glGetError',U)()==0
report=dict(status='passed',fullProductionFragmentCompiled=True,legacyNegativeAndUnityPixelsExact=legacy,positivePixelsComparedWithFirmwareOracle=positive,positiveMaximumChannelError=maxerr,headroomProbeMaximumU16Error=probeError,all25SaturationContrastCombinations=True,fallbackUnchanged=True,probeIndependentOfDisplayGain=True,evResponseMonotonic=True,driver=gl('glGetString',C.c_char_p,U)(0x1f01).decode(),phoneValidationPending=True)
(out/'PREVIEW_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
