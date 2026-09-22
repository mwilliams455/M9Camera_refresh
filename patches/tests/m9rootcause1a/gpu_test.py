"""Real GLES: shifted-viewport crops must equal the corresponding full-render pixels."""
from pathlib import Path
import contextlib,io,json,runpy
import numpy as np
repo=Path(__file__).resolve().parents[3]
with contextlib.redirect_stdout(io.StringIO()):
    fixture=runpy.run_path(str(repo/'patches/tests/m9tg2neutral1a/gpu_test.py'))
globals().update({k:v for k,v in fixture.items() if not k.startswith('__')})
gl('glUseProgram',None,U)(pfull)
for key,value in [('uM9SourceReady2A',1),('uM9Enabled',1),('enablePeak',0),('mirror',0)]:ui(pfull,key,value)
uf(pfull,'uM9Tungsten2A',0)
rng=np.random.default_rng(233)
pixels=rng.integers(0,256,(24,32,4),dtype=np.uint8);pixels[:,:,3]=255
tex(0,pixels,0x8058,0x1908,0x1401)
target=tex(3,np.zeros((24,32,4),np.uint8),0x8058,0x1908,0x1401)
gl('glFramebufferTexture2D',None,U,U,U,U,I)(0x8D40,0x8CE0,0x0DE1,target,0)
assert gl('glCheckFramebufferStatus',U,U)(0x8D40)==0x8CD5
results=[]
for stage,gain in [(1,8.),(0,1.),(0,8.)]:
    ui(pfull,'uM9EvidenceStage2E',stage);uf(pfull,'uM9ExposureScale1B',gain)
    gl('glDisable',None,U)(0x0C11)
    gl('glViewport',None,I,I,I,I)(0,0,32,24)
    gl('glDrawArrays',None,U,I,I)(4,0,3)
    full=np.empty((24,32,4),np.uint8)
    gl('glReadPixels',None,I,I,I,I,U,U,P)(0,0,32,24,0x1908,0x1401,full.ctypes.data)
    gl('glEnable',None,U)(0x0C11);gl('glScissor',None,I,I,I,I)(0,0,8,8)
    gl('glViewport',None,I,I,I,I)(-12,-8,32,24)
    gl('glDrawArrays',None,U,I,I)(4,0,3)
    cropped=np.empty((8,8,4),np.uint8)
    gl('glReadPixels',None,I,I,I,I,U,U,P)(0,0,8,8,0x1908,0x1401,cropped.ctypes.data)
    assert np.array_equal(cropped,full[8:16,12:20]),(stage,gain,'crop resampled or shifted')
    if stage==1:assert np.array_equal(cropped,pixels[8:16,12:20]),'source bypass changed bytes'
    results.append(dict(stage=stage,gain=gain,maxCodeDelta=0))
assert geterr()==0
print(json.dumps({'revision':'M9ROOTCAUSE1A','nativeViewportCropEqualsFullRender':results,'hardwareCadenceVerified':False},indent=2))
