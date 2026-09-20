"""Precision regression for the production packed inverse-tone sampler on GLES3.
Runs the inherited native colour oracle, then tests actual inverse GLSL in a float
render target. No assertion of parity with a phone camera or its input pixels.
"""
from pathlib import Path
import contextlib,io,json,runpy,sys
import numpy as np
repo=Path(__file__).resolve().parents[3]
with contextlib.redirect_stdout(io.StringIO()) as inherited:
    fixture=runpy.run_path(str(repo/'patches/tests/m9livegl2a/gpu_test.py'))
base_report=json.loads(inherited.getvalue())
globals().update({k:v for k,v in fixture.items() if not k.startswith('__')})
# Keep the exact production functions; isolate inverse transfer from film tone,
# integer colour conversion and output quantization.
pinverse=program(source[:source.index('void main() {')]+'''void main(){
vec3 c=texture(sTexture,texCoord).rgb;
Output=vec4(inverseChannel2A(c.r,0),inverseChannel2A(c.g,1),inverseChannel2A(c.b,2),1.0);
}''')
ui(pinverse,'sTexture',0);ui(pinverse,'uM9Inverse2A',2)
# Dense ramp through byte carries, independent channel curves and endpoints.
x=np.linspace(0,1,count,dtype=np.float32).reshape(H,W)
inputs=np.ones((H,W,4),np.float32)
inputs[:,:,0]=x;inputs[:,:,1]=x[:,::-1];inputs[:,:,2]=np.roll(x,137,axis=None).reshape(H,W)
tex(0,inputs,0x8814,0x1908,0x1406)
grid=np.arange(1024)/1023
linear=np.stack([np.where(grid<=.04045,grid/12.92,((grid+.055)/1.055)**2.4),grid**2,grid],axis=1)
q=np.floor(linear*65535+.5).astype(np.uint16)
packed=np.zeros((2,1024,4),np.uint8);packed[0,:,:3]=q>>8;packed[1,:,:3]=q&255
tex(2,packed,0x8058,0x1908,0x1401)
# Test both modes: production must no longer depend on byte-plane filtering.
results=[]
floatout=np.zeros((H,W,4),np.float32);floattarget=tex(3,floatout,0x8814,0x1908,0x1406)
gl('glFramebufferTexture2D',None,U,U,U,U,I)(0x8D40,0x8CE0,0x0DE1,floattarget,0)
assert gl('glCheckFramebufferStatus',U,U)(0x8D40)==0x8CD5,'float test framebuffer'
expected=np.empty((H,W,3),np.float64)
for channel in range(3):expected[:,:,channel]=np.interp(inputs[:,:,channel].astype(float),grid,q[:,channel]/65535.)
previous=None
for filtering in [0x2601,0x2600]:
    active(0x84C2)
    for key in [0x2801,0x2800]:gl('glTexParameteri',None,U,U,I)(0x0DE1,key,filtering)
    gl('glViewport',None,I,I,I,I)(0,0,W,H);gl('glDrawArrays',None,U,I,I)(4,0,3)
    gl('glReadPixels',None,I,I,I,I,U,U,P)(0,0,W,H,0x1908,0x1406,floatout.ctypes.data)
    assert geterr()==0
    actual=floatout[:,:,:3].copy();delta=np.abs(actual-expected)
    assert np.all(np.isfinite(actual))
    assert delta.max()<2e-6,('packed inverse precision',filtering,float(delta.max()))
    red=actual[:,:,0].reshape(-1)
    assert np.min(np.diff(red))>=0,('inverse gradient reversal',float(np.min(np.diff(red))))
    assert red[0]==0 and abs(red[-1]-1)<2e-7,'inverse endpoints'
    if previous is not None:assert np.array_equal(actual,previous),'sampling depends on hardware filter'
    previous=actual
    for ev in [-4,0,1,1.75,2.75,3,3.25,4]:
        assert np.max(np.abs(actual.astype(float)*2**ev-expected*2**ev))<2e-6*2**ev
    results.append({'filter':'linear' if filtering==0x2601 else 'nearest','samples':int(actual.size),'maxLinearError':float(delta.max()),'minimumRedGradientStep':float(np.min(np.diff(red)))})
print(json.dumps({'revision':'M9LIVEGL2C_INVERSEPRECISION','inherited':base_report,'inverseSampler':results,'deviceInputOrCadenceVerified':False},indent=2))
