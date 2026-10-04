from pathlib import Path
import ctypes as C,hashlib,json,re,struct,subprocess,sys
import numpy as np
here=Path(__file__).resolve().parent;out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
so=out/'libsharp_host.so'
subprocess.run(['g++','-std=c++17','-O3','-fno-fast-math','-DM9_SHARP_HOST','-fPIC','-shared',str(here/'m9_sharpness.cpp'),'-o',str(so)],check=True)
lib=C.CDLL(str(so));ptr=C.POINTER(C.c_uint16);dp=C.POINTER(C.c_double)
lib.m9_sharp_coeff.argtypes=[C.c_int]*3
lib.m9_sharp_plane.argtypes=[ptr,ptr]+[C.c_int]*5
lib.m9_sharp_rgb.argtypes=[ptr]+[C.c_int]*4+[dp]
s=(here/'m9_sharpness_bank.h').read_text();tables=re.findall(r'\{([^{}]+)\}',s)
modes=np.array([[int(x) for x in a.split(',') if x.strip()] for a in tables[:5]])
bank=np.array([[int(x) for x in a.split(',') if x.strip()] for a in tables[5:]],dtype=np.int16)
assert bank.shape==(13,2050)
assert hashlib.sha256(bank.astype('<i2').tobytes()).hexdigest()=='a9c60000a8ec60ce922f8715436aa45223988f16c5b00fbfc417e546cdf7a8eb'
def oracle_lut(slot,level):
    v=bank[slot].astype(np.int64);m=modes[level,slot]
    if level==0:return np.zeros(2050,dtype=np.int64)
    v={1:lambda:v>>2,2:lambda:v>>1,3:lambda:v,4:lambda:v*2,5:lambda:v*4,6:lambda:(v>>1)*3,7:lambda:v*3}[int(m)]()
    return np.clip(v,-2048,2048)
def plane(src,slot,level,border):
    a=src.astype(np.int64);g=(a[:-2,:-2]+2*a[:-2,1:-1]+a[:-2,2:]+2*a[1:-1,:-2]+4*a[1:-1,1:-1]+2*a[1:-1,2:]+a[2:,:-2]+2*a[2:,1:-1]+a[2:,2:])//16
    corr=oracle_lut(slot,level)[1024+np.clip(a[1:-1,1:-1]-g,-1024,1024)]
    o=a.copy();tmp=np.clip(a[1:-1,1:-1]+corr,0,16383)
    o[border:-border,border:-border]=tmp[border-1:-(border-1),border-1:-(border-1)]
    return o.astype(np.uint16)
rng=np.random.default_rng(228);src=rng.integers(0,16384,(83,91),dtype=np.uint16)
coeff_count=0;plane_count=0
for slot in range(13):
 for level in range(5):
    oracle=oracle_lut(slot,level)
    for r in range(-1024,1025):assert lib.m9_sharp_coeff(slot,level,r)==oracle[1024+r],(slot,level,r)
    coeff_count+=2049
    dst=np.empty_like(src)
    assert lib.m9_sharp_plane(src.ctypes.data_as(ptr),dst.ctypes.data_as(ptr),91,83,slot,level,2)==0
    assert np.array_equal(dst,plane(src,slot,level,2));plane_count+=src.size
def rgb_run(src,slot,level):
    a=src.copy();stats=np.zeros(7,np.float64)
    assert lib.m9_sharp_rgb(a.ctypes.data_as(ptr),a.shape[1],a.shape[0],slot,level,stats.ctypes.data_as(dp))==0
    return a,stats
def rgb_oracle(src,slot,level):
    a=src.astype(np.uint64);q=((a[:,:,1]*16383+32767)//65535).astype(np.uint16)
    v=plane(q,slot,level,18).astype(np.uint64);e=q.astype(np.uint64)
    active=(v!=e)&(e>0);num=np.where(active,v,1);den=np.where(active,e,1)
    peak=a.max(axis=2);limited=num*peak>65535*den
    num=np.where(limited,65535,num);den=np.where(limited,peak,den)
    return ((a*num[:,:,None]+den[:,:,None]//2)//den[:,:,None]).astype(np.uint16)
fixtures={}
fixtures['random_colour']=rng.integers(0,65536,(83,91,3),dtype=np.uint16)
fixtures['neutral_noise']=np.repeat(rng.integers(0,65536,(83,91,1),dtype=np.uint16),3,axis=2)
for name,value in [('black',0),('flat',16000),('white',65535)]:fixtures[name]=np.full((83,91,3),value,np.uint16)
for name,ratios in [('skin_warm',(1.7,1.,.65)),('blue',(0.5,1.,2.7)),('leaf',(0.4,1.,.25))]:
    lum=rng.integers(500,20000,(83,91,1));fixtures[name]=np.clip(lum*np.array(ratios),0,65535).astype(np.uint16)
f=np.full((83,91,3),12000,np.uint16);f[:,45:]=45000;fixtures['edge']=f
checks=0;maxratio=0;level_changes=[]
for name,fixture in fixtures.items():
 for slot in range(13):
  for level in range(5):
    got,stats=rgb_run(fixture,slot,level);expected=rgb_oracle(fixture,slot,level)
    assert np.array_equal(got,expected),(name,slot,level)
    if level==0 or name in ('black','flat','white'):assert np.array_equal(got,fixture)
    mask=np.ones(got.shape[:2],bool);mask[18:-18,18:-18]=False
    assert np.array_equal(got[mask],fixture[mask])
    if name=='neutral_noise':assert np.array_equal(got[:,:,0],got[:,:,1]) and np.array_equal(got[:,:,1],got[:,:,2])
    # Cross products bound colour-ratio error from independent half-code rounding.
    a=fixture.astype(np.int64);b=got.astype(np.int64)
    for c in (0,2):
      err=np.abs(b[:,:,c]*a[:,:,1]-b[:,:,1]*a[:,:,c]);bound=(a[:,:,1]+a[:,:,c]+1)//2
      assert np.all(err<=bound),(name,slot,level,int((err-bound).max()))
    checks+=1
for n in range(5):level_changes.append(int(rgb_run(fixtures['edge'],0,n)[1][1]))
assert level_changes[0]==0 and all(n>0 for n in level_changes[1:])
fine=np.full((83,91,3),12000,np.uint16);fine[:,45:]=14000
fine_levels=[]
for level in range(5):
    rendered,_=rgb_run(fine,0,level);fine_levels.append([int(rendered[40,44,1]),int(rendered[40,45,1])])
assert len({tuple(v) for v in fine_levels})==5
# Native entry rejects invalid dimensions/selectors; tiny frames remain unchanged.
tiny=np.full((3,3,3),1234,np.uint16)
for n in range(5):assert np.array_equal(rgb_run(tiny,0,n)[0],tiny)
stats=np.zeros(7);a=fixtures['edge'].copy()
assert lib.m9_sharp_rgb(a.ctypes.data_as(ptr),91,83,13,2,stats.ctypes.data_as(dp))==-1
# Representative 12MP cost and O(width) memory bound.
big=np.tile(fixtures['edge'],(38,46,1))[:3072,:4096].copy();got,stats=rgb_run(big,0,2)
report=dict(status='passed',firmwareCoefficientComparisons=coeff_count,kernelPixelComparisons=plane_count,
    rgbFixtureCases=checks,offByteExact=True,flatFieldsExact=True,neutralRgbExact=True,ratioErrorBoundHalfCode=True,
    inherited18PixelBorderExact=True,edgeChangedPixels=level_changes,fineEdgeLevelSeparationGreen16=fine_levels,kernelScratchBytesAt4096=stats[5],host12MpElapsedMs=stats[4],
    scope='Firmware integer kernel and documented AMaZE RGB adaptation; not full original Leica reconstruction or phone validation')
(out/'NATIVE_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
