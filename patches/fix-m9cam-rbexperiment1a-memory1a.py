#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(sys.argv[1]) if len(sys.argv)>1 else Path('PhotonCamera')
CPP=ROOT/'app/src/main/cpp/m9color_jni.cpp'
if not CPP.exists(): raise SystemExit('RBEXPERIMENT1A-MEMORY1A missing '+str(CPP))
s=CPP.read_text()
if 'RBEXPERIMENT1A_EXACT_GREEN_RB_ACTIVE_ID' not in s: raise SystemExit('RBEXPERIMENT1A-MEMORY1A requires RBEXPERIMENT1A parent')
if 'RBEXPERIMENT1A_MEMORY1A_ID' in s: raise SystemExit('RBEXPERIMENT1A-MEMORY1A already applied')

old_green = '''        // SPLITDEMOSAIC1A research seam: retain a 16-bit completed-green frame
        // between interpolation phases. No Sharpness modification is permitted yet.
        std::vector<uint16_t> greenPlane(static_cast<size_t>(pixels64));
        for (int worker = 0; worker < workerCount; ++worker) {
            const int y0 = (height * worker) / workerCount;
            const int y1 = (height * (worker + 1)) / workerCount;
            threads.emplace_back([=, &greenPlane]() {
                for (int y = y0; y < y1; ++y) {
                    for (int x = 0; x < width; ++x) {
                        greenPlane[static_cast<size_t>(y)*static_cast<size_t>(width)+static_cast<size_t>(x)] =
                                mhcNeutralGreenRggb(raw,width,height,y,x,invR,invB);
                    }
                }
            });
        }
        for (auto& thread : threads) thread.join();

'''
new_green = '''        // RBEXPERIMENT1A_MEMORY1A_ID: do not retain a second full-resolution
        // neutral-MHC green plane. The preservation border/fallback computes its
        // MHC green sample on demand during the output pass. This trades bounded
        // extra arithmetic for ~24 MiB less live memory at 4096x3072.

'''
if s.count(old_green)!=1: raise SystemExit('MEMORY1A green-plane anchor count='+str(s.count(old_green)))
s=s.replace(old_green,new_green,1)

old_prep='''        std::vector<uint16_t> rbxRed14;
        std::vector<uint16_t> rbxBlue14;
        if(rbxExperimentOk) {
            // rbxPlaneA now carries the Green-stage colour-difference lattice at
            // the R/B sample sites consumed by ASMRedBlueInterpolation1.
            rbxExperimentOk=rbx1InterpExact(
                    rbxPlaneA,sharpSourceGreen14,width,height,0,rbxRed14,rbxBlue14);
        }
        if(!rbxExperimentOk) {
            // Preserve the validated parent behaviour if the experiment rejects
            // unexpected geometry or an address/side-effect bound.
            m9SharpSourceLeicaGreen14(raw,width,height,sharpSourceGreen14);
            rbxRed14.clear();
            rbxBlue14.clear();
        }
        std::vector<uint16_t> closureSharp14;
        m9ClosureSharpIso160Standard(sharpSourceGreen14, closureSharp14, width, height);'''
new_prep='''        if(rbxExperimentOk) {
            // Reuse the no-longer-needed Green scratch planes as exact R/B outputs.
            // This removes two additional full-resolution 16-bit allocations.
            rbxExperimentOk=rbx1InterpExact(
                    rbxPlaneA,sharpSourceGreen14,width,height,0,rbxPlaneC,rbxPlaneD);
        }
        if(!rbxExperimentOk) {
            // Preserve the validated parent behaviour if the experiment rejects
            // unexpected geometry or an address/side-effect bound.
            m9SharpSourceLeicaGreen14(raw,width,height,sharpSourceGreen14);
        }
        // After interpolation, Green's input/work plane is dead. Reuse it for
        // the sharpened-green result rather than allocating another 12 MP plane.
        std::vector<uint16_t>& closureSharp14=rbxPlaneA;
        m9ClosureSharpIso160Standard(sharpSourceGreen14, closureSharp14, width, height);'''
if s.count(old_prep)!=1: raise SystemExit('MEMORY1A prep anchor count='+str(s.count(old_prep)))
s=s.replace(old_prep,new_prep,1)

old_cap='            threads.emplace_back([=, &greenPlane, &sharpSourceGreen14, &closureSharp14, &rbxRed14, &rbxBlue14]() {'
new_cap='            threads.emplace_back([=, &sharpSourceGreen14, &closureSharp14, &rbxPlaneC, &rbxPlaneD]() {'
if s.count(old_cap)!=1: raise SystemExit('MEMORY1A lambda anchor count='+str(s.count(old_cap)))
s=s.replace(old_cap,new_cap,1)

old_base='''                        uint16_t base[3];
                        mhcPixelNeutralRbCompleteRggb(raw,width,height,y,x,greenPlane[p],base,nr,nb,invR,invB);'''
new_base='''                        uint16_t base[3];
                        const uint16_t fallbackGreen=mhcNeutralGreenRggb(raw,width,height,y,x,invR,invB);
                        mhcPixelNeutralRbCompleteRggb(raw,width,height,y,x,fallbackGreen,base,nr,nb,invR,invB);'''
if s.count(old_base)!=1: raise SystemExit('MEMORY1A fallback anchor count='+str(s.count(old_base)))
s=s.replace(old_base,new_base,1)

s=s.replace('const int dr=static_cast<int>(rbxRed14[p])-mg;','const int dr=static_cast<int>(rbxPlaneC[p])-mg;',1)
s=s.replace('const int db=static_cast<int>(rbxBlue14[p])-mg;','const int db=static_cast<int>(rbxPlaneD[p])-mg;',1)

CPP.write_text(s)
print('RBEXPERIMENT1A-MEMORY1A applied: four Leica planes total; MHC green computed on demand; scratch/output/sharp buffers reused')
