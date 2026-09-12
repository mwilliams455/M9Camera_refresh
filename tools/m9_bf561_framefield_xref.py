#!/usr/bin/env python3
"""Cross-reference BF561 frame/context fields used by M9 R/B closure.

Research-only. Consumes a recovered BF561 LDR/map pair and GNU bfin objdump.
No firmware bytes are embedded or emitted. The output is text/JSON instruction
context only, focused on +0x34/+0x38/+0x3c/+0x40/+0x44 accesses.
"""
from __future__ import annotations
import argparse, json, re, subprocess, tempfile
from pathlib import Path
from collections import defaultdict

from m9_sharpnessforensics1a import parse_map, parse_ldr, read_overlay

FIELDS=(0x34,0x38,0x3c,0x40,0x44)
ZERO_WINDOW=0x180
MAX_WINDOW=0x1800


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--ldr',type=Path,required=True)
    ap.add_argument('--map',dest='map_path',type=Path,required=True)
    ap.add_argument('--objdump',required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)

    syms=sorted(parse_map(a.map_path), key=lambda x:(x['addr'],x['mapoff']))
    _,blocks=parse_ldr(a.ldr)
    by_addr=defaultdict(list)
    for s in syms: by_addr[s['addr']].append(s)

    # Code in this image is concentrated in high address overlays. Skip obvious
    # low-address data symbols and exact duplicate addresses.
    report=[]
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        for addr,group in sorted(by_addr.items()):
            if addr < 0xFE000000: continue
            natural=max(int(s.get('size',0)) for s in group)
            size=natural if natural>0 else ZERO_WINDOW
            size=min(max(size,0x20),MAX_WINDOW)
            try: code=read_overlay(blocks,addr,size)
            except Exception: continue
            if not code: continue
            p=td/f'{addr:08x}.bin'; p.write_bytes(code)
            r=subprocess.run([a.objdump,'-D','-b','binary','-m','bfin',f'--adjust-vma={addr}',str(p)],text=True,capture_output=True)
            if r.returncode: continue
            lines=r.stdout.splitlines()
            hit_idx=[]
            for i,ln in enumerate(lines):
                if any(re.search(rf'\+\s*0x{f:x}\]',ln,re.I) for f in FIELDS): hit_idx.append(i)
            if not hit_idx: continue
            contexts=[]
            for i in hit_idx:
                lo=max(0,i-8); hi=min(len(lines),i+9)
                contexts.append({'line':lines[i].strip(),'context':[x.rstrip() for x in lines[lo:hi]]})
            report.append({
                'address':f'0x{addr:08x}',
                'symbols':[s['name'] for s in group],
                'map_sizes':[int(s.get('size',0)) for s in group],
                'extracted_size':size,
                'field_hits':contexts,
            })

    # Classify exact accesses for quick writer/reader lookup.
    index={f'0x{f:x}':{'reads':[],'writes':[],'other':[]} for f in FIELDS}
    for ent in report:
        for h in ent['field_hits']:
            ln=h['line']
            for f in FIELDS:
                if not re.search(rf'\+\s*0x{f:x}\]',ln,re.I): continue
                rec={'address':ent['address'],'symbols':ent['symbols'],'instruction':ln}
                # GNU bfin syntax: memory on LHS of '=' is a write; on RHS a read.
                lhs=ln.split(':',1)[-1].split('=',1)[0] if '=' in ln else ''
                rhs=ln.split('=',1)[1] if '=' in ln else ''
                mempat=rf'\[[^\]]*\+\s*0x{f:x}\]'
                if re.search(mempat,lhs,re.I): kind='writes'
                elif re.search(mempat,rhs,re.I): kind='reads'
                else: kind='other'
                index[f'0x{f:x}'][kind].append(rec)

    out={'schema':'m9.bf561-framefield-xref.v1','fields':[f'0x{x:x}' for x in FIELDS],
         'symbol_entries_with_hits':len(report),'index':index,'entries':report}
    (a.out/'framefield_xref.json').write_text(json.dumps(out,indent=2)+'\n')
    with (a.out/'framefield_xref.txt').open('w') as f:
        for field,v in index.items():
            f.write(f'===== FIELD {field} =====\n')
            for kind in ('writes','reads','other'):
                f.write(f'-- {kind.upper()} ({len(v[kind])}) --\n')
                for r in v[kind]: f.write(f"{r['address']} {'|'.join(r['symbols'])}: {r['instruction']}\n")
        f.write('\n===== CONTEXTS =====\n')
        for ent in report:
            f.write(f"\n### {ent['address']} {'|'.join(ent['symbols'])}\n")
            for h in ent['field_hits']:
                f.write('\n'.join(h['context'])+'\n---\n')
    print(json.dumps({k:{q:len(v[q]) for q in ('writes','reads','other')} for k,v in index.items()},indent=2))

if __name__=='__main__': main()
