"""Recover the BF547 WB producer and independently check its normalization tail."""
from pathlib import Path
import argparse
import ctypes as C
import hashlib
import json
import re
import subprocess
import sys
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'tools'))
from m9_sharpness_gateb_control_trace import FW_SHA, BF_SHA, walk
from m9_sharpnessforensics1a import parse_ldr, read_overlay


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--firmware',type=Path,required=True)
    ap.add_argument('--objdump',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    fw=a.firmware.read_bytes();assert sha(fw)==FW_SHA
    assets={p:b for p,_,b in walk(fw)};bf=assets['BF547'];assert sha(bf)==BF_SHA
    evidence=[]
    targets=[('Gain_from_measurement',0xa98d4,0xa9af2),
             ('Gain_from_estimate',0xab588,0xab7bc),
             ('Auto_to_gain_estimate',0xaba1e,0xaba36),
             ('WB_dispatch_and_unity_snap',0xaba68,0xabd08),
             ('Gain_to_capture_record',0xb00ec,0xb02f6),
             ('Capture_record_to_packet',0x39f74,0x3a066),
             ('Integer_divide',0xb4a24,0xb4a6a)]
    for name,start,end in targets:
        evidence.append((name,start,bf[start-0x20000:end-0x20000],'BF547'))
    temp=a.out/'temporary.ldr';temp.write_bytes(assets['BF561/bf1'])
    _,blocks=parse_ldr(temp);temp.unlink()
    # These establish that the pedestal is context+0x7c, not the geometry
    # field at frame+0x7c. The context is initially zeroed at Init.
    for name,start,size in [('Init_zero_WB_context',0xfeb1ca48,0x68),
                            ('Run_context_base',0xff61022c,0x14),
                            ('Run_frame_base',0xff610430,0x12)]:
        evidence.append((name,start,read_overlay(blocks,start,size),'BF561/bf1'))
    records=[]
    for name,start,b,asset in evidence:
        temp=a.out/'temporary.bin';temp.write_bytes(b)
        text=subprocess.check_output([str(a.objdump),'-D','-b','binary','-m','bfin',
                                      f'--adjust-vma={start}',str(temp)],text=True)
        temp.unlink();lines=[]
        for line in text.splitlines():
            m=re.match(r'\s*([0-9a-f]+):\s+(?:[0-9a-f]{2} )+\s*\t(.+)',line)
            if m:lines.append(m[1]+': '+m[2].split('/*')[0].strip())
        dest=a.out/f'{name}_{start:08x}.asm.txt';dest.write_text('\n'.join(lines)+'\n')
        records.append(dict(name=name,address=hex(start),size=len(b),asset=asset,
                            code_sha256=sha(b),file=dest.name,text_sha256=sha(dest.read_bytes())))
    cpp=Path(__file__).with_suffix('.cpp');so=a.out/'wb_gain_contract.so'
    subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-shared','-fPIC',str(cpp),'-o',str(so)],check=True)
    lib=C.CDLL(str(so.resolve()));lib.wb_gain_contract.argtypes=[C.c_void_p,C.c_void_p,C.c_int]
    lib.wb_gain_contract.restype=None
    # Dense two-dimensional bounded-gain grid and exhaustive 16-bit sweeps
    # through three other-channel gains. Include representational corner cases.
    grid=np.unique(np.r_[np.arange(8192,65537,127),8192,16383,16384,16385,65534,65535,65536])
    r,b=np.meshgrid(grid,grid);pairs=np.c_[r.ravel(),b.ravel()]
    sweeps=[np.c_[np.arange(8192,65537),np.full(65537-8192,v)] for v in (8192,16384,49152)]
    pairs=np.ascontiguousarray(np.vstack([pairs,*sweeps]),dtype=np.int32)
    out=np.empty((len(pairs),3),np.uint16);lib.wb_gain_contract(pairs.ctypes.data,out.ctypes.data,len(pairs))
    x=pairs.astype(np.int64)
    scale=np.where(x.min(axis=1)>=16384,16384,268435456//x.min(axis=1))
    products=np.c_[x[:,0]*scale,scale*16384,x[:,1]*scale]
    signed=(products+2**31)%2**32-2**31
    oracle=np.clip(signed//16384,16384,65536)%65536
    oracle[np.isin(oracle,[16383,16385])]=16384
    assert np.array_equal(out,oracle)
    # The safe subset excludes every overflowing product and 65536 narrowing.
    safe=(products.max(axis=1)<2**31)&np.all(out!=0,axis=1)
    assert np.all(np.any(out[safe]==16384,axis=1))
    assert np.all(out[safe]>=16384)
    # Selected caller's green-unity phone case. Quantization is an adaptation
    # of DNG neutral ratios, not a recovered M9 estimate for this phone sensor.
    phone=np.array([[16384*1024//428,16384*1024//659]],np.int32)
    pg=np.empty((1,3),np.uint16);lib.wb_gain_contract(phone.ctypes.data,pg.ctypes.data,1)
    report=dict(schema='m9.wb_gain_contract.v1',firmware_sha256=sha(fw),bf547_sha256=sha(bf),
                wbparam_sha256=sha(assets['LUTS/WBPARAM']),wbparam_bytes=len(assets['LUTS/WBPARAM']),
                evidence=records,source_sha256=sha(cpp.read_bytes()),probe_sha256=sha(Path(__file__).read_bytes()),
                exact_gain_triplets=len(pairs),safe_gain_triplets=int(safe.sum()),
                safe_subset_all_have_exact_unity=True,non_safe_cases=int((~safe).sum()),
                packet_zero_cases=int(np.any(out==0,axis=1).sum()),
                phone_preliminary_rb_q14=phone[0].tolist(),phone_packet_rgb_q14=pg[0].tolist(),
                pedestal_source_correction='context+0x7c, not frame+0x7c; context initially zeroed, complete later-writer audit not claimed',
                normalization='Green-relative preliminary R/B; divide all gains by their minimum when below unity; fixed-point floor; final 16383/16385 ->16384 snap.',
                limits='Scoped normalization tail only. Inputs tested 8192..65536; preserve signed 32-bit products and uint16 narrowing. No WB estimator, WBPARAM format, hardware trace or complete sensor calibration claim.',
                android_implementation_changed=False)
    (a.out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('exact_gain_triplets','safe_gain_triplets','packet_zero_cases','phone_packet_rgb_q14')},indent=2))


if __name__=='__main__':main()
