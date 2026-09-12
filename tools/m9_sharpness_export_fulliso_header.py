#!/usr/bin/env python3
"""Export the canonical Leica M9 13x2050 Sharp base LUT bank as a C++ header.

Build-time derived resource only. Input must be the canonical decrypted M9 1.216
container. Also verifies the later-proven Standard selector row.
"""
from __future__ import annotations
import argparse, hashlib, struct
from pathlib import Path

FW_SHA="4f962bb7799ad9a6745ab36c2a3ba59757bfcbd205f50472ddf1b904a5756d20"
EXPECTED_SIZE=427744
BANK_OFF=0xACF8
COUNT=2050
ROWS=13
MODE_OFF=0x5F8
STANDARD_SELECTOR=2
STANDARD_EXPECT=[4,4,4,4,4,4,3,3,3,3,3,2,2]

def sha(b): return hashlib.sha256(b).hexdigest()
def pwad(data):
    if data[:4]!=b'PWAD': raise ValueError('not PWAD')
    n,d=struct.unpack_from('<II',data,4)
    for i in range(n):
        off,size,raw=struct.unpack_from('<II8s',data,d+16*i)
        name=raw.split(b'\0',1)[0].decode('ascii','replace')
        yield name,data[off:off+size]
def walk(data,prefix=''):
    for name,p in pwad(data):
        path=f'{prefix}/{name}' if prefix else name
        yield path,name,p
        if p[:4]==b'PWAD': yield from walk(p,path)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('firmware',type=Path); ap.add_argument('--out',type=Path,required=True); a=ap.parse_args()
    fw=a.firmware.read_bytes()
    if sha(fw)!=FW_SHA: raise SystemExit('canonical decrypted firmware hash mismatch')
    candidates=[]
    for path,name,p in walk(fw):
        if len(p)==EXPECTED_SIZE or name.upper()=='LUTS' or path.upper().endswith('/PROCESS/LUTS'):
            if len(p)>=BANK_OFF+ROWS*COUNT*2 and struct.unpack_from('<I',p,0x10)[0]==BANK_OFF and struct.unpack_from('<I',p,0x5F4)[0]==COUNT:
                candidates.append((path,p))
    if len(candidates)!=1: raise SystemExit(f'expected one canonical LUTS candidate, got {len(candidates)}')
    path,p=candidates[0]
    row_off=MODE_OFF+STANDARD_SELECTOR*ROWS*4
    modes=[struct.unpack_from('<I',p,row_off+4*i)[0] for i in range(ROWS)]
    if modes!=STANDARD_EXPECT: raise SystemExit(f'Standard mode row mismatch: {modes}')
    rows=[]; hashes=[]
    for s in range(ROWS):
        lo=BANK_OFF+s*COUNT*2
        b=p[lo:lo+COUNT*2]
        hashes.append(sha(b)); rows.append(struct.unpack('<'+('h'*COUNT),b))
    lines=['#pragma once','#include <cstdint>','// Generated from canonical Leica M9 1.216 LUTS resource; do not hand-edit.',f'// firmware_sha256={FW_SHA}',f'// resource_path={path}','static constexpr int M9_SHARP_ISO_ROWS=13;','static constexpr int M9_SHARP_LUT_COUNT=2050;','static constexpr int M9_SHARP_STANDARD_MODE[13]={4,4,4,4,4,4,3,3,3,3,3,2,2};','static constexpr int16_t M9_SHARP_BASE[13][2050]={']
    for i,row in enumerate(rows):
        lines.append('  {')
        for j in range(0,COUNT,32): lines.append('    '+','.join(str(x) for x in row[j:j+32])+',')
        lines.append('  },')
    lines.append('};')
    lines.append('// slot row SHA256:')
    for i,h in enumerate(hashes): lines.append(f'// {i}: {h}')
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text('\n'.join(lines)+'\n')
    print('resource',path); print('standard_modes',modes); print('row_hashes',hashes); print('out',a.out)
if __name__=='__main__': main()
