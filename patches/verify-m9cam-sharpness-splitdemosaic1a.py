#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(sys.argv[1]) if len(sys.argv)>1 else Path('PhotonCamera')
CPP=ROOT/'app/src/main/cpp/m9color_jni.cpp'
R=ROOT/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
for p in (CPP,R):
    if not p.exists(): raise SystemExit('SPLITDEMOSAIC1A verify missing '+str(p))
cpp=CPP.read_text(); r=R.read_text()

def one(s,t,n):
    c=s.count(t)
    if c!=1: raise SystemExit(f'SPLITDEMOSAIC1A verify {n} count={c}')

one(cpp,'inline uint16_t mhcNeutralGreenRggb(','green-pass helper')
one(cpp,'inline void mhcPixelNeutralRbCompleteRggb(','RB-completion helper')
one(cpp,'std::vector<uint16_t> greenPlane(','intermediate green plane')
one(cpp,'mhcNeutralGreenRggb(raw,width,height,y,x,invR,invB)','green-pass call')
one(cpp,'mhcPixelNeutralRbCompleteRggb(raw,width,height,y,x,greenPlane[p],dst,nr,nb,invR,invB)','RB-completion call')
one(cpp,'inline void mhcPixelNeutralRggb(','frozen monolithic oracle retained')
if 'Sharpness modification is permitted yet' not in cpp:
    raise SystemExit('SPLITDEMOSAIC1A verify Sharp-disabled guard missing')
if 'ASMUMGauss3LUT' in cpp or 'sharpLut' in cpp or 'sharpnessLut' in cpp:
    raise SystemExit('SPLITDEMOSAIC1A verify unexpected Sharp arithmetic in native renderer')
# Frozen photographic downstream anchors must survive untouched.
one(cpp,'16754, -7632, -922','SAT3 M06 anchor')
one(cpp,'18160, -9034, -922','SAT3 M07 anchor')
if 'DEMOSAICMHCNEUTRAL1A_FROZEN1A' not in r:
    raise SystemExit('SPLITDEMOSAIC1A verify frozen MHC foundation missing')
print('SPLITDEMOSAIC1A verify OK: green/RB seam present, monolithic oracle retained, Sharp disabled, downstream frozen')
