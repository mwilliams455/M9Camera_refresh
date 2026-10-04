#!/usr/bin/env python3
"""Follow the canonical M9 BF547 'Sharpening' controller descriptor to its menu table.

Evidence-only. No Leica firmware bytes are embedded or retained. The tool finds
the controller descriptor by the literal label, verifies the 32-byte descriptor
shape against neighboring controls, follows its +0x14 options pointer, and
decodes consecutive 20-byte Leica menu records by resolving label pointers via
the canonical BF547 +0x20000 static-RAM mapping.
"""
from __future__ import annotations

import argparse, hashlib, json, struct
from pathlib import Path
from typing import Iterable

FW_SHA = "4f962bb7799ad9a6745ab36c2a3ba59757bfcbd205f50472ddf1b904a5756d20"
BF_SHA = "f044097bc9ce0deba129f593321aeb20d30c5c2e7b8c3074e44717e7765c66bd"
RAM = 0x20000
DESC_SIZE = 0x20
OPTIONS_PTR_OFF = 0x14
MENU_STRIDE = 0x14


def sha(b): return hashlib.sha256(b).hexdigest()


def parse_pwad(data: bytes):
    if data[:4] != b"PWAD": raise ValueError("not PWAD")
    n, d = struct.unpack_from('<II', data, 4)
    out=[]
    for i in range(n):
        o,s,r=struct.unpack_from('<II8s',data,d+16*i)
        if o+s>len(data): raise ValueError('bad PWAD')
        out.append((r.split(b'\0',1)[0].decode('ascii','replace'),data[o:o+s]))
    return out


def walk(data: bytes, prefix='') -> Iterable[tuple[str,str,bytes]]:
    for name,p in parse_pwad(data):
        path=f'{prefix}/{name}' if prefix else name
        yield path,name,p
        if p[:4]==b'PWAD': yield from walk(p,path)


def bf547(root: bytes) -> bytes:
    hits=[p for _,n,p in walk(root) if n.upper()=='BF547']
    if len(hits)!=1: raise RuntimeError(f'BF547 hits={len(hits)}')
    return hits[0]


def find_all(b: bytes, needle: bytes):
    out=[]; p=0
    while True:
        p=b.find(needle,p)
        if p<0: return out
        out.append(p); p+=1


def cstr(b: bytes, off: int, maxlen=128):
    if not 0<=off<len(b): return None
    e=b.find(b'\0',off,min(len(b),off+maxlen))
    if e<=off: return None
    raw=b[off:e]
    if any(x<0x20 or x>0x7e for x in raw): return None
    return raw.decode('ascii')


def ptr_text(b: bytes, ptr: int):
    if not RAM<=ptr<RAM+len(b): return None
    return cstr(b,ptr-RAM)


def unique_string_xref(b: bytes, text: str):
    # Match exact NUL-terminated label where possible.
    so=find_all(b,text.encode()+b'\0')
    if not so: so=find_all(b,text.encode())
    ptr_x=[]
    for off in so:
        addr=off+RAM
        pat=struct.pack('<I',addr)
        ptr_x += [(off,x) for x in find_all(b,pat)]
    # Deduplicate exact xref offsets.
    ded={x:(s,x) for s,x in ptr_x}
    return list(ded.values())


def decode_descriptor(b: bytes, xref: int):
    vals=struct.unpack_from('<8I',b,xref)
    return {
        'off':hex(xref),
        'label_ptr':hex(vals[0]),
        'label':ptr_text(b,vals[0]),
        'control_id':hex(vals[1]),
        'word_08':hex(vals[2]),
        'type':vals[3],
        'word_10':hex(vals[4]),
        'options_ptr':hex(vals[5]),
        'word_18':hex(vals[6]),
        'word_1c':hex(vals[7]),
    }


def decode_menu_records(b: bytes, ptr: int, max_records=16):
    off=ptr-RAM
    rows=[]
    for i in range(max_records):
        ro=off+i*MENU_STRIDE
        if ro<0 or ro+MENU_STRIDE>len(b): break
        vals=struct.unpack_from('<5I',b,ro)
        label=ptr_text(b,vals[0])
        if label is None: break
        rows.append({
            'index':i,'record_off':hex(ro),'record_addr':hex(ro+RAM),
            'label_ptr':hex(vals[0]),'label':label,'enum':vals[1],
            'word_08':hex(vals[2]),'word_0c':hex(vals[3]),'word_10':hex(vals[4]),
        })
    return rows


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('firmware',type=Path); ap.add_argument('--out',type=Path,default=Path('gateb_menu_follow.json')); a=ap.parse_args()
    root=a.firmware.read_bytes()
    if sha(root)!=FW_SHA: raise SystemExit('canonical decrypted firmware hash mismatch')
    b=bf547(root)
    if sha(b)!=BF_SHA: raise SystemExit('canonical BF547 hash mismatch')

    controls={}
    for name in ('Sharpening','Contrast','Color saturation','Noise'):
        xs=unique_string_xref(b,name)
        controls[name]=[]
        for so,x in xs:
            d=decode_descriptor(b,x)
            d['string_off']=hex(so)
            op=int(d['options_ptr'],16)
            d['menu_records']=decode_menu_records(b,op) if RAM<=op<RAM+len(b) else []
            controls[name].append(d)

    sharp=controls['Sharpening']
    if len(sharp)!=1: raise SystemExit(f'expected one Sharpening descriptor, got {len(sharp)}')
    s=sharp[0]
    rows=s['menu_records']
    if not rows: raise SystemExit('Sharpening options pointer did not decode as Leica menu records')

    report={
      'schema':'m9.sharpness.gateb-follow-menu.v1',
      'bf547_sha256':sha(b),
      'descriptor_size':DESC_SIZE,
      'options_pointer_offset':hex(OPTIONS_PTR_OFF),
      'menu_record_stride':MENU_STRIDE,
      'controls':controls,
      'sharpening':s,
      'gate_b_candidate_mapping':[{"label":r['label'],"enum":r['enum']} for r in rows],
      'note':'Mapping is firmware-derived from the M9 Sharpening descriptor itself; next trace selector state into process record field/job builder.'
    }
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(report,indent=2)+'\n')
    print('Sharpening descriptor:',json.dumps({k:v for k,v in s.items() if k!='menu_records'},indent=2))
    print('Sharpening menu records:')
    for r in rows: print(f"  {r['index']}: enum={r['enum']} label={r['label']!r} record={r['record_off']}")
    print('report=',a.out)

if __name__=='__main__': main()
