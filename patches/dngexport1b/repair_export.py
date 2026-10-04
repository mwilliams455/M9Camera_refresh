#!/usr/bin/env python3
"""Offline metadata-only counterpart of DNGEXPORT1B; never overwrite a source.

Restricted to a single-IFD, uncompressed, unsigned RAW16 little-endian CFA DNG.
Copies the original file, appends aligned metadata/IFD, updates the root pointer.
No firmware profile, sensor transform, shading bake, or RAW filtering is added.
"""
from pathlib import Path
import argparse, hashlib, io, json, struct
import numpy as np
import tifffile

def repair(source, output):
    source, output=Path(source), Path(output)
    if output.exists(): raise FileExistsError(output)
    original=source.read_bytes(); data=bytearray(original)
    assert data[:4]==b'II*\0','Little-endian classic TIFF required'
    with tifffile.TiffFile(source) as f:
        assert len(f.pages)==1
        p=f.pages[0]
        assert p.bitspersample==16 and p.compression==1 and p.photometric==32803
        assert p.samplesperpixel==1 and len(p.dataoffsets)==1
        assert p.dataoffsets[0]%2==0,'Unaligned RAW strip requires complete rewrite'
        before=p.asarray()
        t=p.tags[50717]
        if t.dtype==5:
            n,d=t.value; assert d and n%d==0; white=n//d
        else:
            assert t.dtype in (3,4); white=int(t.value)
        assert 0<=white<=65535
        old=p.offset; n=struct.unpack_from('<H',data,old)[0]
        assert struct.unpack_from('<I',data,old+2+12*n)[0]==0
        entries={}
        for i in range(n):
            pos=old+2+12*i
            tag,typ,count,value=struct.unpack_from('<HHII',data,pos)
            entry=bytes(data[pos:pos+12])
            t=p.tags[tag]
            if tag==50717:
                entry=struct.pack('<HHII',tag,4,1,white)
            elif tag==305:
                payload=b'M9Cam DNGEXPORT1B offline metadata repair\0'
                data.extend(b'\0'*(-len(data)%2)); off=len(data); data.extend(payload)
                entry=struct.pack('<HHII',tag,2,len(payload),off)
            elif t.valuebytecount>4 and value%2:
                payload=original[value:value+t.valuebytecount]
                data.extend(b'\0'*(-len(data)%2)); off=len(data); data.extend(payload)
                entry=struct.pack('<HHII',tag,typ,count,off)
            entries[tag]=entry
        data.extend(b'\0'*(-len(data)%2)); root=len(data)
        data.extend(struct.pack('<H',len(entries)))
        data.extend(b''.join(entries[t] for t in sorted(entries)))
        data.extend(struct.pack('<I',0)); struct.pack_into('<I',data,4,root)
    with tifffile.TiffFile(io.BytesIO(data)) as f, tifffile.TiffFile(source) as old:
        p=f.pages[0]; q=old.pages[0]
        assert np.array_equal(before,p.asarray())
        assert p.tags[50717].dtype==4 and p.tags[50717].value==white
        assert p.offset%2==0
        assert all(t.valueoffset%2==0 for t in p.tags.values() if t.valuebytecount>4)
        assert set(p.tags.keys())==set(q.tags.keys())
        for tag in p.tags.keys():
            if tag not in (305,50717): assert p.tags[tag].value==q.tags[tag].value,tag
        assert data[8:len(original)]==original[8:]
    with output.open('xb') as f: f.write(data)
    return dict(source=source.name,output=output.name,rawSamples=before.size,
                rawSha256=hashlib.sha256(before.astype('<u2').tobytes()).hexdigest(),
                rawPixelsIdentical=True,unchangedCalibrationAndOpcodeValues=True,
                changedTagValues=[305],changedTagTypes=[50717],
                sourceSha256=hashlib.sha256(original).hexdigest(),
                outputSha256=hashlib.sha256(data).hexdigest())

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('source');parser.add_argument('output')
    args=parser.parse_args(); print(json.dumps(repair(args.source,args.output),indent=2))
