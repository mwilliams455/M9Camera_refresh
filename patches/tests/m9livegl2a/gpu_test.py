"""Execute production GLSL on Mesa GLES3; compare SAT2/curve02 to native C++.
The OES sampler is replaced with a 2D fixture texture only. No camera/HAL claim.
"""
from pathlib import Path
import ctypes as C,ctypes.util,os,sys,tempfile,subprocess,json
import numpy as np
root=Path(sys.argv[1]).resolve();os.environ['EGL_PLATFORM']='surfaceless'
e=C.CDLL(ctypes.util.find_library('EGL'));I=C.c_int;U=C.c_uint;F=C.c_float;P=C.c_void_p

def egl(n,rest,args):
 f=getattr(e,n);f.restype=rest;f.argtypes=args;return f
D=egl('eglGetDisplay',P,[P])(None);a=I();b=I();assert egl('eglInitialize',I,[P,P,P])(D,C.byref(a),C.byref(b))
egl('eglBindAPI',I,[I])(0x30A0);config=P();n=I()
attrs=(I*11)(0x3024,8,0x3023,8,0x3022,8,0x3033,1,0x3040,0x40,0x3038)
assert egl('eglChooseConfig',I,[P,P,P,I,P])(D,attrs,C.byref(config),1,C.byref(n)) and n.value
ctx=egl('eglCreateContext',P,[P,P,P,P])(D,config,None,(I*3)(0x3098,3,0x3038));assert ctx
assert egl('eglMakeCurrent',I,[P,P,P,P])(D,None,None,ctx)
proc=egl('eglGetProcAddress',P,[C.c_char_p])
def gl(name,rest,*args): return C.CFUNCTYPE(rest,*args)(proc(name.encode()))
gl('glDisable',None,U)(0x0BD0)
geterr=gl('glGetError',U);gs=gl('glGetString',C.c_char_p,U)
shader=(root/'app/src/main/assets/shaders/preview/main_fs.glsl').read_text()
source='#version 300 es\n'+shader.replace('#extension GL_OES_EGL_image_external_essl3 : require','').replace('samplerExternalOES','sampler2D')
vs='#version 300 es\nout vec2 texCoord;void main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);texCoord=p;gl_Position=vec4(p*2.-1.,0,1);}'
def compile(type,text):
 sh=gl('glCreateShader',U,U)(type);raw=text.encode();ss=C.c_char_p(raw)
 gl('glShaderSource',None,U,I,P,P)(sh,1,C.byref(ss),None);gl('glCompileShader',None,U)(sh);ok=I();gl('glGetShaderiv',None,U,U,P)(sh,0x8B81,C.byref(ok))
 if not ok.value:
  buf=C.create_string_buffer(10000);gl('glGetShaderInfoLog',None,U,I,P,P)(sh,10000,None,buf);raise AssertionError(buf.value.decode())
 return sh
def program(fs):
 p=gl('glCreateProgram',U)();gl('glAttachShader',None,U,U)(p,compile(0x8B31,vs));gl('glAttachShader',None,U,U)(p,compile(0x8B30,fs));gl('glLinkProgram',None,U)(p)
 ok=I();gl('glGetProgramiv',None,U,U,P)(p,0x8B82,C.byref(ok));assert ok.value,'shader link'
 gl('glUseProgram',None,U)(p);return p
# Compile the entire production program before the focused function oracle.
program('#version 300 es\n'+shader) # Compile the exact OES program too; fixtures execute the 2D variant.
pfull=program(source)
punit=program(source[:source.index('void main() {')]+'''void main(){Output=vec4(tungsten2A(curveSat2M9(texture(sTexture,texCoord).rgb)),1.0);}''')
W=128;H=64;count=W*H
rng=np.random.default_rng(1731);pixels=np.ones((H,W,4),np.float32);pixels[:,:,:3]=rng.random((H,W,3))*1.25
# Greys, every branch and near-zero/white boundaries.
pixels[0,:,:3]=np.linspace(0,1,W)[:,None];pixels[1,:,:3]=np.linspace(1,0,W)[:,None]
pixels[2,:,:3]=0;pixels[3,:,:3]=1
texture=gl('glGenTextures',None,I,P);bind=gl('glBindTexture',None,U,U);active=gl('glActiveTexture',None,U)
def tex(unit,data,internal,format,type):
 t=U();texture(1,C.byref(t));active(0x84C0+unit);bind(0x0DE1,t)
 for k,v in [(0x2801,0x2600),(0x2800,0x2600),(0x2802,0x812F),(0x2803,0x812F)]:gl('glTexParameteri',None,U,U,I)(0x0DE1,k,v)
 gl('glTexImage2D',None,U,I,I,I,I,I,U,U,P)(0x0DE1,0,internal,data.shape[1],data.shape[0],0,format,type,data.ctypes.data)
 return t
tex(0,pixels,0x8814,0x1908,0x1406)
curve=np.frombuffer((root/'app/src/main/assets/m9/m9_curve02_firmware.bin').read_bytes(),np.uint8).reshape(1,2048,1).copy();tex(1,curve,0x8229,0x1903,0x1401)
inverse=np.zeros((2,1024,4),np.uint8)
for x in range(1024):
 code=x/1023;linear=code/12.92 if code<=.04045 else ((code+.055)/1.055)**2.4;q=round(linear*65535)
 inverse[0,x,:3]=q>>8;inverse[1,x,:3]=q&255
invtex=tex(2,inverse,0x8058,0x1908,0x1401)
for k in (0x2801,0x2800):gl('glTexParameteri',None,U,U,I)(0x0DE1,k,0x2601)
out=np.zeros((H,W,4),np.uint8);target=tex(3,out,0x8058,0x1908,0x1401)
fbo=U();gl('glGenFramebuffers',None,I,P)(1,C.byref(fbo));gl('glBindFramebuffer',None,U,U)(0x8D40,fbo);gl('glFramebufferTexture2D',None,U,U,U,U,I)(0x8D40,0x8CE0,0x0DE1,target,0)
assert gl('glCheckFramebufferStatus',U,U)(0x8D40)==0x8CD5
loc=gl('glGetUniformLocation',I,U,C.c_char_p)
def ui(p,n,v):gl('glUniform1i',None,I,I)(loc(p,n.encode()),v)
def uf(p,n,v):gl('glUniform1f',None,I,F)(loc(p,n.encode()),v)
def render(p):
 gl('glViewport',None,I,I,I,I)(0,0,W,H);gl('glDrawArrays',None,U,I,I)(4,0,3);gl('glReadPixels',None,I,I,I,I,U,U,P)(0,0,W,H,0x1908,0x1401,out.ctypes.data);assert geterr()==0;return out[:,:,:3].copy()
# Compile the actual frozen native SAT2/curve02 function into the independent oracle.
cpp=(root/'app/src/main/cpp/m9color_jni.cpp').read_text();const=cpp[cpp.index('constexpr int RAW_MAX'):cpp.index('struct ColorContext')]
fn=cpp[cpp.index('inline int m9CurvePixel'):cpp.index('inline int roundU8')]
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);c=d/'oracle.cpp';lib=d/'oracle.so'
 c.write_text('#include <array>\n#include <cmath>\n#include <cstdint>\n#include <algorithm>\n'+const+'''struct ColorContext{int skyChromaMode1A=9;std::array<uint8_t,2048> curve;};
 int64_t clipl(int64_t v,int64_t lo,int64_t hi){return std::max(lo,std::min(v,hi));}
 '''+fn+'''extern "C" void oracle(const float* input,int n,const uint8_t* curve,double tg,uint8_t* out){ColorContext ctx;std::copy(curve,curve+2048,ctx.curve.begin());for(int i=0;i<n;i++){double m[]={input[4*i],input[4*i+1],input[4*i+2]};int rgb[3];m9CurvePixel(m,1,ctx,rgb);int r=rgb[0],g=rgb[1],b=rgb[2];int y=(4899*r+9617*g+1868*b)>>14;int cb=((-2765*r-5427*g+8192*b)>>14);int cr=((8192*r-6860*g-1332*b)>>14);cb=((cb+128)&255)-128;cr=((cr+128)&255)-128;double cbm=cb*(cb<0?1-.25*tg:1);double crm=cr*(cr<0?1-.16*tg:1);double v[]={y+1.402*crm,y-.344136*cbm-.714136*crm,y+1.772*cbm};for(int k=0;k<3;k++)out[3*i+k]=(uint8_t)(std::max(0.,std::min(255.,v[k]))+.5);}}''')
 subprocess.run(['g++','-std=c++17','-O2','-shared','-fPIC',str(c),'-o',str(lib)],check=True)
 oracle=C.CDLL(str(lib)).oracle;oracle.argtypes=[P,I,P,C.c_double,P]
 results=[]
 for tg in [0,.5,1]:
  gl('glUseProgram',None,U)(punit);ui(punit,'sTexture',0);ui(punit,'uM9Curve',1);uf(punit,'uM9Tungsten2A',tg)
  gpu=render(punit);expected=np.empty((H,W,3),np.uint8);oracle(pixels.ctypes.data,count,curve.ctypes.data,tg,expected.ctypes.data)
  delta=np.abs(gpu.astype(int)-expected.astype(int));assert delta.max()<=2,(tg,delta.max(),np.count_nonzero(delta))
  results.append({'tungstenWeight':tg,'maxCodeDelta':int(delta.max()),'meanCodeDelta':float(delta.mean()),'differentChannels':int(np.count_nonzero(delta))})
# Full source-to-target path and explicit fallback: finite output and monotonic grey EV response.
gl('glUseProgram',None,U)(pfull)
for n,v in [('sTexture',0),('uM9Curve',1),('uM9Inverse2A',2),('enablePeak',0),('mirror',0),('uM9Enabled',1)]:ui(pfull,n,v)
for name in ['uM9InputToSensor2A','uM9SensorToPp2A','uM9PpToTarget2A']:
 m=np.eye(3,dtype=np.float32);gl('glUniformMatrix3fv',None,I,I,I,P)(loc(pfull,name.encode()),1,0,m.ctypes.data)
white=np.ones(3,np.float32);gl('glUniform3fv',None,I,I,P)(loc(pfull,b'uM9ClipWhite2A'),1,white.ctypes.data);uf(pfull,'uM9Tungsten2A',0)
for ready in [0,1]:
 ui(pfull,'uM9SourceReady2A',ready);bracket=[]
 for ev in [.5,1,2]:uf(pfull,'uM9ExposureScale1B',ev);bracket.append(render(pfull)[0])
 assert np.all(bracket[0].astype(int)<=bracket[1].astype(int)+1) and np.all(bracket[1].astype(int)<=bracket[2].astype(int)+1)
 assert np.mean(bracket[2][16:80])>np.mean(bracket[1][16:80])+10
report={'renderer':gs(0x1F01).decode(),'version':gs(0x1F02).decode(),'pixelsPerTungstenState':count,'nativeKernelComparisons':results,'fullProgramAndFallbackBracket':'PASS','deviceParityOrCadenceVerified':False}
print(json.dumps(report,indent=2))
