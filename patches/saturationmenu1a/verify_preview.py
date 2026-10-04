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
function=source[source.index('vec3 curveSat2M9('):source.index('vec3 tungsten2A(')]
fragment=shader(0x8b30,'#version 300 es\nprecision highp float;precision highp int;uniform sampler2D uM9Curve;uniform int uM9SaturationBank;uniform ivec3 uInput;out vec4 outputColor;\n'+function+'\nvoid main(){outputColor=vec4(curveSat2M9(vec3(uInput)/16383.0),1.0);}')
vertex=shader(0x8b31,'#version 300 es\nvoid main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.0-1.0,0,1);}')
program=gl('glCreateProgram',U)()
for sh in [vertex,fragment]:gl('glAttachShader',None,U,U)(program,sh)
gl('glLinkProgram',None,U)(program);ok=I();gl('glGetProgramiv',None,U,U,P)(program,0x8b82,C.byref(ok));assert ok.value
gl('glUseProgram',None,U)(program)
loc=lambda name:gl('glGetUniformLocation',I,U,C.c_char_p)(program,name.encode())
bank_loc,input_loc=loc('uM9SaturationBank'),loc('uInput')
gl('glUniform1i',None,I,I)(loc('uM9Curve'),0)
texture=U();gl('glGenTextures',None,I,P)(1,C.byref(texture));gl('glBindTexture',None,U,U)(0x0de1,texture)
for pname in [0x2800,0x2801]:gl('glTexParameteri',None,U,U,I)(0x0de1,pname,0x2600)
curve=np.frombuffer((root/'app/src/main/assets/m9/m9_curve02_firmware.bin').read_bytes(),np.uint8)
gl('glTexImage2D',None,U,I,I,I,I,I,U,U,P)(0x0de1,0,0x8229,2048,1,0,0x1903,0x1401,curve.ctypes.data)
gl('glViewport',None,I,I,I,I)(0,0,1,1);gl('glDisable',None,U)(0x0bd0)
firmware=json.loads((here/'firmware_saturation.json').read_text());m=np.array([[x['even'],x['odd']] for x in firmware['levels']],np.int64).reshape(5,2,3,3)
q=np.r_[np.random.default_rng(216).integers(0,16384,(250,3)),[[0,0,0],[16383,16383,16383],[16383,0,0],[0,16383,0],[0,0,16383],[8192,8192,8192]]]
pixel=np.zeros(4,np.uint8)
for bank in range(5):
 gl('glUniform1i',None,I,I)(bank_loc,bank)
 for row in q:
  gl('glUniform3i',None,I,I,I,I)(input_loc,*map(int,row));gl('glDrawArrays',None,U,I,I)(4,0,3)
  gl('glReadPixels',None,I,I,I,I,U,U,P)(0,0,1,1,0x1908,0x1401,pixel.ctypes.data)
  expected=curve[np.clip((m[bank,int(row[0]<row[1])]@row)>>16,0,2047)]
  np.testing.assert_array_equal(pixel[:3],expected,err_msg=f'bank {bank} input {row}')
assert gl('glGetError',U)()==0
result=dict(status='passed',fullProductionFragmentCompiled=True,levels=5,pixelsPerLevel=len(q),firmwareLookupExact=True,driver=gl('glGetString',C.c_char_p,U)(0x1f01).decode(),handsetValidationPending=True)
(out/'PREVIEW_VERIFICATION.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
