#!/usr/bin/env python3
"""Trace the canonical M9 BF547 Sharpening control beyond its menu descriptor.

Evidence-only.  The earlier Gate-B pass proves the static control descriptor,
control id 0x1005 and the five UI enum values.  This pass anchors on that exact
descriptor and reports every direct data reference plus bounded literal/immediate
breadcrumbs needed to locate the generic controller setter.  It does not label
record +0x0c as Sharpness unless a later code trace proves the write.
"""
from __future__ import annotations

import argparse, hashlib, json, struct
from pathlib import Path
from typing import Iterable

FW_SHA = "4f962bb7799ad9a6745ab36c2a3ba59757bfcbd205f50472ddf1b904a5756d20"
BF_SHA = "f044097bc9ce0deba129f593321aeb20d30c5c2e7b8c3074e44717e7765c66bd"
RAM = 0x20000
CONTROL_ID = 0x1005


def sha(b): return hashlib.sha256(b).hexdigest()


def parse_pwad(data: bytes):
    if data[:4] != b"PWAD": raise ValueError("not PWAD")
    n, d = struct.unpack_from("<II", data, 4)
    out=[]
    for i in range(n):
        o,s,r=struct.unpack_from("<II8s",data,d+16*i)
        if o+s>len(data): raise ValueError("bad PWAD")
        out.append((r.split(b"\0",1)[0].decode("ascii","replace"),data[o:o+s]))
    return out


def walk(data: bytes, prefix="") -> Iterable[tuple[str,str,bytes]]:
    for name,p in parse_pwad(data):
        path=f"{prefix}/{name}" if prefix else name
        yield path,name,p
        if p[:4]==b"PWAD": yield from walk(p,path)


def get_bf547(root: bytes) -> bytes:
    hits=[p for _,n,p in walk(root) if n.upper()=="BF547"]
    if len(hits)!=1: raise RuntimeError(f"BF547 hits={len(hits)}")
    return hits[0]


def find_all(b: bytes, needle: bytes):
    out=[]; p=0
    while True:
        p=b.find(needle,p)
        if p<0: return out
        out.append(p); p+=1


def cstr(b: bytes, off: int, maxlen=128):
    if not 0<=off<len(b): return None
    e=b.find(b"\0",off,min(len(b),off+maxlen))
    if e<=off: return None
    raw=b[off:e]
    if any(x<0x20 or x>0x7e for x in raw): return None
    return raw.decode("ascii")


def ptr_text(b: bytes, ptr: int):
    return cstr(b,ptr-RAM) if RAM<=ptr<RAM+len(b) else None


def window(b: bytes, off: int, radius=48):
    lo=max(0,off-radius); hi=min(len(b),off+radius)
    return {"off":hex(off),"runtime":hex(off+RAM),"lo":hex(lo),"hi":hex(hi),"hex":b[lo:hi].hex(" ")}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("firmware",type=Path); ap.add_argument("--out",type=Path,default=Path("gateb_control_trace.json")); a=ap.parse_args()
    root=a.firmware.read_bytes()
    if sha(root)!=FW_SHA: raise SystemExit("canonical decrypted firmware hash mismatch")
    b=get_bf547(root)
    if sha(b)!=BF_SHA: raise SystemExit("canonical BF547 hash mismatch")

    label_hits=find_all(b,b"Sharpening\0")
    if len(label_hits)!=1: raise SystemExit(f"Sharpening strings={label_hits}")
    label_off=label_hits[0]; label_ptr=label_off+RAM
    desc_xrefs=find_all(b,struct.pack("<I",label_ptr))
    desc=[]
    for off in desc_xrefs:
        if off+0x20>len(b): continue
        vals=struct.unpack_from("<8I",b,off)
        if vals[1]==CONTROL_ID and vals[0]==label_ptr:
            desc.append((off,vals))
    if len(desc)!=1: raise SystemExit(f"matching descriptors={[(hex(x),v) for x,v in desc]}")
    doff,vals=desc[0]
    daddr=doff+RAM
    options=vals[5]

    patterns={
        "descriptor_runtime_u32":struct.pack("<I",daddr),
        "label_runtime_u32":struct.pack("<I",label_ptr),
        "options_runtime_u32":struct.pack("<I",options),
        "control_id_u32":struct.pack("<I",CONTROL_ID),
        "control_id_u16":struct.pack("<H",CONTROL_ID),
        "descriptor_low16":struct.pack("<H",daddr & 0xffff),
        "descriptor_high16":struct.pack("<H",(daddr>>16)&0xffff),
        "options_low16":struct.pack("<H",options & 0xffff),
        "options_high16":struct.pack("<H",(options>>16)&0xffff),
    }
    refs={}
    for name,pat in patterns.items():
        hits=find_all(b,pat)
        refs[name]={"pattern_hex":pat.hex(" "),"count":len(hits),"hits":[window(b,x) for x in hits[:256]]}

    # Directly expose the firmware diagnostic label region that proved the known
    # record field names.  This also shows whether an unreferenced nSharpness
    # string exists adjacent to the +0x0c hole.
    string_region=[]
    for off in range(max(0,0xD52C0),min(len(b),0xD5380)):
        if off==0 or b[off-1]==0:
            s=cstr(b,off,80)
            if s: string_region.append({"off":hex(off),"runtime":hex(off+RAM),"text":s})

    report={
        "schema":"m9.sharpness.gateb-control-trace.v1",
        "bf547_sha256":sha(b),
        "sharpening_descriptor":{
            "file_off":hex(doff),"runtime_addr":hex(daddr),
            "label_ptr":hex(label_ptr),"control_id":hex(vals[1]),
            "type":vals[3],"options_ptr":hex(options),
            "raw_words":[hex(x) for x in vals],
        },
        "references":refs,
        "diagnostic_string_region":string_region,
        "evidence_policy":[
            "A direct data/immediate occurrence is a breadcrumb, not proof of execution or write semantics.",
            "Only a decoded controller code path from control 0x1005/value state to processing-record +0x0c closes the Sharpness field identity.",
            "Do not infer +0x0c from neighboring fields alone."
        ]
    }
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({
        "out":str(a.out),"descriptor_runtime":hex(daddr),"options_ptr":hex(options),
        "reference_counts":{k:v["count"] for k,v in refs.items()},
        "diagnostic_strings":string_region,
    },indent=2))

if __name__=="__main__": main()
