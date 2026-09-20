"""Replay the actual GL2E device pair through unchanged production GLSL.
This proves the old amplification and the guarded fallback, not the HAL response
to the new uniform-input request; that needs the candidate APK on the phone.
"""
from pathlib import Path
import contextlib,io,json,runpy
import numpy as np
repo=Path(__file__).resolve().parents[3];here2f=Path(__file__).resolve().parent
with contextlib.redirect_stdout(io.StringIO()) as inherited:
    fixture=runpy.run_path(str(repo/'patches/tests/m9livegl2e/gpu_test.py'))
inherited_report_2f=json.loads(inherited.getvalue())
globals().update({k:v for k,v in fixture.items() if not k.startswith('__')})
pair=json.loads((here2f/'telephoto_curve_samples.json').read_text());sc=pair['sourceContract']
gl('glUseProgram',None,U)(pfull)
ui(pfull,'uM9EvidenceStage2E',0);ui(pfull,'uM9SourceReady2A',1)
for name,key in [('uM9InputToSensor2A','inputToSensorGL'),('uM9SensorToPp2A','sensorToProPhotoGL'),('uM9PpToTarget2A','proPhotoToM9GL')]:
    a=np.array(sc[key],np.float32);gl('glUniformMatrix3fv',None,I,I,I,P)(loc(pfull,name.encode()),1,0,a.ctypes.data)
a=np.array(sc['clipWhite'],np.float32);gl('glUniform3fv',None,I,I,P)(loc(pfull,b'uM9ClipWhite2A'),1,a.ctypes.data)
uf(pfull,'uM9Tungsten2A',sc['tungstenWeight']);uf(pfull,'uM9ExposureScale1B',pair['displayExposureScale'])
def panel(name):
    key='input' if name=='incomingOes' else 'render'
    samples=np.array([s[key] for s in pair['colorSamples']],np.uint8)
    return np.tile(samples,(12,1)).reshape(24,32,3)
pix=np.ones((24,32,4),np.uint8)*255;pix[:,:,:3]=panel('incomingOes');tex(0,pix,0x8058,0x1908,0x1401)
result=np.zeros_like(pix);grid=np.arange(1024)/1023;linear=np.zeros((1024,3))
for c in range(3):
    points=np.array(sc['reportedToneCurveRgb2E'][c]).reshape(-1,2);linear[:,c]=np.interp(grid,points[:,1],points[:,0])
q=np.floor(linear*65535+.5).astype(np.uint16);packed=np.zeros((2,1024,4),np.uint8);packed[0,:,:3]=q>>8;packed[1,:,:3]=q&255
tex(2,packed,0x8058,0x1908,0x1401)
def draw2f():
    gl('glDrawArrays',None,U,I,I)(4,0,3);gl('glReadPixels',None,I,I,I,I,U,U,P)(0,0,32,24,0x1908,0x1401,result.ctypes.data)
    assert geterr()==0
    return result[:,:,:3].copy()
old=draw2f();delta=np.abs(old.astype(int)-panel('displayRender').astype(int))
assert delta.max()<=4 and delta.mean()<1,'actual device haze not reproduced within input quantization'
oldmin=int(old.min());assert oldmin>=70 and int(pix[:,:,:3].min())<20
ui(pfull,'uM9SourceReady2A',0);guarded=draw2f()
guard_delta=np.abs(guarded.astype(int)-pix[:,:,:3].astype(int))
assert guard_delta.max()<=1,'contract fallback introduced a floor or other colour processing'
print(json.dumps({'revision':'M9LIVEGL2F_CURVECONTRACT','inherited':inherited_report_2f,
 'recordedTelephotoReplay':{'uniqueColorPairs':64,'rgbChannelsWithRepetition':2304,'maxCodeDelta':int(delta.max()),'meanCodeDelta':float(delta.mean()),'renderMinimumRgb':oldmin},
 'rejectedContractFallback':{'maxInputCodeDelta':int(guard_delta.max()),'renderMinimumRgb':int(guarded.min())},
 'newCurvePhoneResponseVerified':False,'stillPreviewParityVerified':False},indent=2))
