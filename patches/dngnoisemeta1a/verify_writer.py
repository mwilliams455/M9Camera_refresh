#!/usr/bin/env python3
"""Compile production TinyDNGWriter and independently decode its TIFF output."""
from pathlib import Path
import hashlib, json, subprocess, sys
import numpy as np
import tifffile

def verify(source, out):
    source, out = Path(source).resolve(), Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    header = source/'app/src/main/cpp/deps/tiny_dng_writer.h'
    subprocess.run(['g++','-std=c++17','-O2','-DCHECK_INVALID_WHITE',
                    '-I'+str(header.parent),str(Path(__file__).with_name('writer_probe.cpp')),
                    '-o',str(out/'writer_probe')],check=True)
    subprocess.run([str(out/'writer_probe'),str(out)],check=True)
    total=0
    for k in range(4):
        with tifffile.TiffFile(out/f'cfa{k}.dng') as f:
            p=f.pages[0]; assert p.shape==(34,66)
            assert p.tags[51041].dtype==12 and p.tags[51041].count==6
            assert p.tags[51041].value==(0.01,0.001,0.03,0.002,0.04,0.003)
            assert p.tags[50730].dtype==10
            n,d=p.tags[50730].value
            assert n/d==[-0.5,0,0.5,-1.5][k]
            assert p.tags[50717].dtype==4 and p.tags[50717].value==65535
            expected=((np.arange(66*34,dtype=np.uint32)*73+k*123)&65535).astype(np.uint16).reshape(34,66)
            assert np.array_equal(p.asarray(),expected)
            assert p.tags[33422].value==[b'\0\1\1\2',b'\1\0\2\1',b'\1\2\0\1',b'\2\1\1\0'][k]
            assert p.tags[50714].value==(64,65,66,67)
            assert p.tags[50728].value==(1,2,1,1,3,4)
            assert p.offset%2==0 and p.dataoffsets[0]%2==0
            assert all(t.valueoffset%2==0 for t in p.tags.values() if t.valuebytecount>4)
            total+=expected.size
    with tifffile.TiffFile(out/'odd_multi.tif') as f:
        assert len(f.pages)==2
        for p in f.pages:
            assert p.offset%2==0 and p.dataoffsets[0]%2==0
            assert p.databytecounts==(9,)
            assert 51041 not in p.tags
            assert np.array_equal(p.asarray().reshape(-1),np.arange(9,dtype=np.uint8))
    result=dict(status='passed',noiseProfileExactDouble6=True,absentNoiseProfileOmitted=True,baselineExposureSignedRationals=[-0.5,0,0.5,-1.5],invalidBaselineValuesRejected=4,cfaPatterns=4,rawSamplesCompared=total,
                oddByteMultiImagePages=2,invalidWhiteInputsRejected=7,
                headerSha256=hashlib.sha256(header.read_bytes()).hexdigest(),
                scope='production C++ serializer on host; not Android/JNI or handset execution')
    (out/'WRITER_VERIFICATION.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__=='__main__': verify(*sys.argv[1:])
