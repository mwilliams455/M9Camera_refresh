"""Recovered Noise2 equations in DETAIL1D's wider mobile colour domain.

This exposes modes 1..3 with luma disabled. WB scale and ISO selection are mobile
experiments, not calibrated sensor noise or recovered full Leica WB arithmetic.
"""
from pathlib import Path
import ctypes as C
import json, subprocess
import numpy as np

TABLES=Path(__file__).parent/'evidence_noise2/tables.json'

def parameters(slot,nr,nb,tables=None):
    t=json.loads(TABLES.read_text()) if tables is None else tables
    if not isinstance(slot,int) or not 0<=slot<=10:raise ValueError('supported Noise2 slots are 0..10 (ISO160..1600)')
    if not all(np.isfinite(n) and .0625<=n<=16 for n in (nr,nb)):raise ValueError('Noise2 probe neutral ratio outside audited wide range')
    mode=t['chroma_mode'][2][slot]
    if t['luma_enable'][2][slot]!=0 or mode not in (1,2,3):raise ValueError('unsupported Noise2 branch')
    f=np.float32(np.float32(t['iso_strength'][slot])/np.float32(256))*np.float32(t['base_strength'])
    # Mobile gains in 14-bit units, deliberately without firmware uint16 wrap.
    wb=[int(np.floor(16384/nr+.5)),16384,int(np.floor(16384/nb+.5))]
    # Despite its map name, feb19c58 shifts a positive mantissa and TRUNCATES.
    sigma=[int(np.float32(np.float32(np.float32(x)*f)/np.float32(16384))) for x in wb]
    energy=max(sigma[0],sigma[2])**2+sigma[1]**2
    shift=1;power=4
    if energy>=1:
        while True:
            shift+=1
            if power>energy:break
            power*=4
    Q=t['attenuation'];assert Q>0 and Q&(Q-1)==0
    return dict(slot=slot,mode=mode,luma_enable=0,iso_strength=t['iso_strength'][slot],base_strength=t['base_strength'],
        mobile_wb14=wb,sigma=sigma,energy=energy,shift=shift,threshold=1<<shift,attenuation=Q,qshift=Q.bit_length()-1,
        carrier_border=3+2*mode,rounding='nearest_even' if mode==2 else 'floor')

class Noise2:
    def __init__(self,build):
        build=Path(build);build.mkdir(parents=True,exist_ok=True);so=build/'noise2.so'
        subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-fPIC','-shared',str(Path(__file__).with_suffix('.cpp')),'-o',str(so)],check=True)
        self.lib=C.CDLL(str(so.resolve()));self.lut=np.array(json.loads(TABLES.read_text())['brightness_weight'],np.uint8)
        self.lib.noise2_filter.argtypes=[C.c_void_p]*2+[C.c_int]*5+[C.c_void_p]+[C.c_int]*2+[C.c_void_p]*3
        self.lib.noise2_filter.restype=None
        self.lib.noise2_blend.argtypes=[C.c_void_p]*3+[C.c_int,C.c_void_p,C.c_int,C.c_int,C.c_void_p,C.c_void_p]
        self.lib.noise2_blend.restype=None
    def apply(self,carrier,green,cfa,params,rounding=1):
        if cfa not in range(4) or params['mode'] not in (1,2,3) or rounding not in (1,2):raise ValueError('unsupported mode/CFA/rounding')
        c=np.ascontiguousarray(carrier,dtype=np.int32);g=np.ascontiguousarray(green,dtype=np.uint16)
        if c.ndim!=2 or g.shape!=c.shape or min(c.shape)<24 or np.max(g)>16383:raise ValueError('invalid carrier or green')
        if np.max(np.abs(c.astype(np.int64)))>262144 or not 1<=params['shift']<=24:raise ValueError('outside audited arithmetic range')
        h,w=c.shape;s=np.empty_like(c);out=np.empty_like(c);counts=np.zeros(3,np.uint64)
        self.lib.noise2_filter(c.ctypes.data,g.ctypes.data,w,h,cfa,params['mode'],rounding,self.lut.ctypes.data,
            params['shift'],params['qshift'],s.ctypes.data,out.ctypes.data,counts.ctypes.data)
        return out,s,dict(zip(['blend','attenuate','zero'],map(int,counts)))
