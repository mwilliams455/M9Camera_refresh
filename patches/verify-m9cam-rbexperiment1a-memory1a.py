#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(sys.argv[1]) if len(sys.argv)>1 else Path('PhotonCamera')
CPP=ROOT/'app/src/main/cpp/m9color_jni.cpp'
if not CPP.exists(): raise SystemExit('MEMORY1A verify missing '+str(CPP))
s=CPP.read_text()
for n in [
 'RBEXPERIMENT1A_MEMORY1A_ID',
 'rbx1InterpExact(\n                    rbxPlaneA,sharpSourceGreen14,width,height,0,rbxPlaneC,rbxPlaneD);',
 'std::vector<uint16_t>& closureSharp14=rbxPlaneA;',
 'const uint16_t fallbackGreen=mhcNeutralGreenRggb(raw,width,height,y,x,invR,invB);',
 'const int dr=static_cast<int>(rbxPlaneC[p])-mg;',
 'const int db=static_cast<int>(rbxPlaneD[p])-mg;',
]:
    if n not in s: raise SystemExit('MEMORY1A missing anchor: '+n)
for bad in [
 'std::vector<uint16_t> greenPlane',
 'std::vector<uint16_t> rbxRed14',
 'std::vector<uint16_t> rbxBlue14',
]:
    if bad in s: raise SystemExit('MEMORY1A stale full-frame allocation: '+bad)
print('RBEXPERIMENT1A-MEMORY1A verify PASS')
print(' live_candidate_planes=4x u16 full-frame (+ one-halfword Green side-effect guard)')
print(' MHC_green_plane=on-demand fallback only')
print(' R/B outputs reuse Green scratch C/D; sharpened green reuses A')
