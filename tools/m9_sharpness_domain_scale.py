#!/usr/bin/env python3
"""Quantify 16-bit normalized -> Leica 14-bit Sharp working-domain mappings.

The Xiaomi renderer's native normalizer is:
  v = clamp((raw-black)/(white-black), 0, 1)
  norm16 = round_half_up(v * 65535)
The Leica Sharp kernel clamps its working samples to 0..16383.

This tool compares integer mappings from norm16 to the direct scene-normalized
14-bit target round_half_up(v*16383). It does not choose a production policy;
it records exact error statistics so the policy can be evidence based.
"""
from __future__ import annotations
import argparse, json, math
from pathlib import Path

MAX16=65535
MAX14=16383

def rhup(x: float)->int:
    return int(math.floor(x+0.5))

def map_shift(n:int)->int:
    return n>>2

def map_ratio_round(n:int)->int:
    # exact integer round-to-nearest for n * 16383 / 65535
    return (n*MAX14 + MAX16//2)//MAX16

def map_ratio_floor(n:int)->int:
    return (n*MAX14)//MAX16

def evaluate(white:int, black:float):
    methods={'shift2':map_shift,'ratio_round':map_ratio_round,'ratio_floor':map_ratio_floor}
    stat={k:{'mismatch':0,'max_abs':0,'sum_abs':0,'bias_sum':0,'first':[]} for k in methods}
    denom=max(1.0,float(white)-black)
    samples=0
    for raw in range(0,white+1):
        v=(float(raw)-black)/denom
        if v<0: v=0.0
        if v>1: v=1.0
        n16=rhup(v*MAX16)
        direct=rhup(v*MAX14)
        samples+=1
        for name,fn in methods.items():
            got=fn(n16); e=got-direct; a=abs(e)
            s=stat[name]
            s['mismatch']+=int(e!=0); s['max_abs']=max(s['max_abs'],a); s['sum_abs']+=a; s['bias_sum']+=e
            if e!=0 and len(s['first'])<8: s['first'].append({'raw':raw,'v':v,'norm16':n16,'direct14':direct,'mapped14':got,'error':e})
    for s in stat.values():
        s['samples']=samples
        s['mismatch_fraction']=s['mismatch']/samples
        s['mean_abs_error']=s['sum_abs']/samples
        s['mean_signed_error']=s['bias_sum']/samples
        del s['sum_abs']; del s['bias_sum']
    return stat

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',type=Path)
    args=ap.parse_args()
    # Include exact-integer and fractional black cases typical of Camera2/DNG metadata.
    cases=[]
    for white,black in [(16383,0.0),(16383,512.0),(16383,512.25),(16383,1024.0),(4095,64.0),(4095,256.5)]:
        cases.append({'white':white,'black':black,'methods':evaluate(white,black)})
    # Also test every possible normalized16 code against the continuous endpoint ratio.
    allcodes={}
    for name,fn in [('shift2',map_shift),('ratio_round',map_ratio_round),('ratio_floor',map_ratio_floor)]:
        errs=[]
        for n in range(65536):
            ideal=n*MAX14/MAX16
            errs.append(fn(n)-ideal)
        allcodes[name]={'min_error':min(errs),'max_error':max(errs),'mean_error':sum(errs)/len(errs)}
    report={'schema':'m9.sharpness-domain-scale.v1','normalizer':'round_half_up(clamp((raw-black)/(white-black))*65535)',
            'direct14_target':'round_half_up(clamp((raw-black)/(white-black))*16383)',
            'max16':MAX16,'max14':MAX14,'cases':cases,'all_norm16_codes':allcodes,
            'policy_selected':False,
            'note':'ratio_round is the endpoint-preserving nearest conversion; firmware/domain evidence is still required before enabling Sharp in the renderer.'}
    text=json.dumps(report,indent=2,sort_keys=True)+'\n'
    if args.out: args.out.write_text(text)
    print(text,end='')
if __name__=='__main__': main()
