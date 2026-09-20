"""Prove evidence bypass returns unchanged input; normal shader keeps the inherited oracle."""
from pathlib import Path
import contextlib,io,json,runpy
import numpy as np
repo=Path(__file__).resolve().parents[3]
with contextlib.redirect_stdout(io.StringIO()) as inherited:
    fixture=runpy.run_path(str(repo/'patches/tests/m9livegl2d/gpu_test.py'))
inherited_report_2e=json.loads(inherited.getvalue())
globals().update({k:v for k,v in fixture.items() if not k.startswith('__')})
gl('glUseProgram',None,U)(pfull)
gl('glViewport',None,I,I,I,I)(0,0,32,24)
assert loc(pfull,b'uM9EvidenceStage2E')>=0
rng=np.random.default_rng(29)
pixels=rng.integers(0,256,(24,32,4),dtype=np.uint8);pixels[:,:,3]=255
pixels[0,:,:3]=0;pixels[1,:,:3]=16;pixels[2,:,:3]=75
tex(0,pixels,0x8058,0x1908,0x1401)
readback=np.zeros_like(pixels)
ui(pfull,'uM9EvidenceStage2E',1)
uf(pfull,'uM9ExposureScale1B',8)
gl('glDrawArrays',None,U,I,I)(4,0,3)
gl('glReadPixels',None,I,I,I,I,U,U,P)(0,0,32,24,0x1908,0x1401,readback.ctypes.data)
assert np.array_equal(readback,pixels),'evidence changed incoming RGB or applied display gain'
ui(pfull,'uM9EvidenceStage2E',0)
uf(pfull,'uM9ExposureScale1B',1)
gl('glDrawArrays',None,U,I,I)(4,0,3)
gl('glReadPixels',None,I,I,I,I,U,U,P)(0,0,32,24,0x1908,0x1401,readback.ctypes.data)
assert np.all(readback[0,:,:3]==0),'normal path raised actual zero input'
assert not np.array_equal(readback,pixels),'normal path stayed in diagnostic bypass'
assert geterr()==0
print(json.dumps({'revision':'M9LIVEGL2E_PAIREDPIXELS','inherited':inherited_report_2e,
  'incomingRgbBytesCompared':32*24*3,'incomingBypassMaxCodeDelta':0,
  'normalModeRestored':True,'normalZeroInputStaysBlack':True,
  'phoneSourceRangeOrHazeCauseEstablished':False},indent=2))
