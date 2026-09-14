#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT=Path(sys.argv[1]) if len(sys.argv)>1 else Path('PhotonCamera')
CPP=ROOT/'app/src/main/cpp/m9color_jni.cpp'
JAVA=ROOT/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java'
RENDER=ROOT/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
for p in (CPP,JAVA,RENDER):
    if not p.exists(): raise SystemExit('RBEXPERIMENT1A verify missing '+str(p))
s=CPP.read_text(); j=JAVA.read_text(); r=RENDER.read_text()
required_cpp=[
 'RBEXPERIMENT1A_EXACT_GREEN_RB_ID',
 'RBEXPERIMENT1A_EXACT_GREEN_RB_ACTIVE_ID',
 'rbx1GreenComposite(',
 'rbx1Filter010(',
 'rbx1Filter101040(',
 'rbx1RedBlueDiffer(',
 'rbx1Filter101000(',
 'rbx1InterpExact(',
 'rbxExperimentOk=rbx1GreenComposite(',
 'width,height,2,0,rbxGreenPhaseFinal',
 'rbxExperimentOk=rbx1InterpExact(',
 'rbxPlaneA,sharpSourceGreen14,width,height,0,rbxRed14,rbxBlue14',
 'std::vector<uint16_t> sharpSourceGreen14(rbxPixels+1u,0);',
 'const int dr=static_cast<int>(rbxRed14[p])-mg;',
 'const int db=static_cast<int>(rbxBlue14[p])-mg;',
 'if(x>=9 && x<width-9 && y>=9 && y<height-9)',
 'm9SharpSourceLeicaGreen14(raw,width,height,sharpSourceGreen14);',
]
for n in required_cpp:
    if n not in s: raise SystemExit('RBEXPERIMENT1A missing C++ anchor: '+n)
required_java=[
 'root.put("sharpnessResearch", "RBEXPERIMENT1A_EXACT_GREEN_RB");',
 'root.put("sharpnessSupportMargin", 9);',
 'root.put("sharpnessRgbFoundation", "LeicaGreenRbExactCandidate_MHCNeutralFrozen_border_fallback");',
 'root.put("sharpnessCorrectionPolicy", "anchor_to_sharpLeicaGreen14_then_restore_exact_RBORACLE7B_RminusG_BminusG");',
 'root.put("sharpnessRbPolicy", "RBEXPERIMENT1A_GREENORACLE6O_phase0_RBORACLE7B_support0_interior9_MHC_fallback");',
 'root.put("rbExperiment1A", true);',
 'root.put("rbExperimentGreenParity", 0);',
 'root.put("rbExperimentSupportBefore", 0);',
 'root.put("rbExperimentProductionRunGlueClaimed", false);',
]
for n in required_java:
    if n not in j: raise SystemExit('RBEXPERIMENT1A missing timing anchor: '+n)
for rejected in [
 'SHARPNESS_SHARPSOURCE1C_RBANCHOR1A_ID',
 'rbPolicy=sharpLeicaGreen_plus_frozenMhcRgBg_differences',
]:
    if rejected in s: raise SystemExit('RBEXPERIMENT1A stale native identity remains: '+rejected)
print('RBEXPERIMENT1A verify PASS')
print(' green=GREENORACLE6O closed helper composition, canonical RGGB phase0')
print(' rb=RBORACLE7B closed interpolation arithmetic/lattice, support-before0')
print(' promotion=interior9 only; neutral-MHC preserved for border/failure')
print(' production_Run_glue_claimed=false')
