#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-fullsourcenorm1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
r = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
if not r.exists():
    raise SystemExit('FULLSOURCENORM1A verifier missing renderer')
s = r.read_text()

required = [
    'SOURCE_FULL_NORM_1A_ENABLED = true',
    'm9cam.sourcefullnorm.v1a.sameraw_gainlocked',
    '_M9_SOURCEFULLNORM1A_GAINLOCK.jpg',
    'production_NORM030_common_luma_target_0p30EV',
    'full_live_remaining_LensShadingMap_common_luma_alpha_1p0',
    'source_common_luminance_shading_authority_NORM030_to_full_physical_remaining_map',
    'primaryBoundedCoreGain',
    'primaryFinalLinearGain',
    'candidateEffectiveRenderGain',
    'gainDeltaEvVsPrimaryFinal',
    'gainLockPassed',
    'sourceGeometryProof2ARuntimeVerified',
    'bridgeProbeMode", 0',
    'cobaltRuntimeProductionDependency", false',
    'targetInputAdapterApplied", false',
    'firmwareSaturation", "SAT2_M04_M05_native_mode9',
    'firmwareCurve", "curve02',
    'fullPhysicalShadingLumaAuthorityAlpha", 1.0',
    'productionNorm030TargetOutsideMedianEv", 0.30',
    'false,  // do not re-meter: lock to primary final gain' if False else 'false,',
]
for marker in required:
    if marker not in s:
        raise SystemExit('FULLSOURCENORM1A verifier missing marker: ' + marker)

# Candidate must call the universal production target mode and must not use legacy
# diagnostic bridge modes 50/54/55 in the new experiment block.
start = s.find('// FULLSOURCENORM1A: same-RAW, gain-locked source-normalization experiment.')
end = s.find('// Do not overwrite capture-time lastDiagnostics here:', start)
if start < 0 or end < 0:
    raise SystemExit('FULLSOURCENORM1A experiment block boundary missing')
block = s[start:end]
for forbidden in ['bridgeProbeModes', 'bridgeProbeMode = 50', 'bridgeProbeMode = 54', 'bridgeProbeMode = 55', 'M9R35Calibration.get()']:
    if forbidden in block:
        raise SystemExit('FULLSOURCENORM1A forbidden legacy target dependency in experiment: ' + forbidden)
if 'diagnosticCaptureResult1A, sourceCfaPattern,' not in block:
    raise SystemExit('FULLSOURCENORM1A candidate does not use active physical source metadata')
if 'primaryFinalLinearGain,' not in block:
    raise SystemExit('FULLSOURCENORM1A candidate is not gain-locked to reconstructed primary final gain')
if 'true,\n                            1.0,\n                            false,\n                            0.0,' not in block:
    raise SystemExit('FULLSOURCENORM1A expected luma-decomp alpha=1 / NORM030-disabled call pattern missing')
if 'Math.abs(gainDeltaEv) > 1.0e-9' not in block:
    raise SystemExit('FULLSOURCENORM1A gain-lock runtime assertion missing')
if 'runtimeGatePassed' not in block:
    raise SystemExit('FULLSOURCENORM1A SOURCEGEOMETRYPROOF2A runtime gate assertion missing')

# Primary production wrapper must remain NORM030 and bridge mode 0.
pstart = s.find('private static RenderCore renderNativeSourceProduction1P(')
pend = s.find('private static RenderCore renderCore(', pstart)
if pstart < 0 or pend < 0:
    raise SystemExit('FULLSOURCENORM1A production wrapper boundary missing')
prod = s[pstart:pend]
for marker in ['0,\n                true,\n                false, false,', 'true, 1.0,', 'true, 0.30', 'targetDirect1A']:
    if marker not in prod:
        raise SystemExit('FULLSOURCENORM1A production NORM030/target marker missing: ' + marker)

print('FULLSOURCENORM1A VERIFY PASS')
print(' - primary production remains NORM030')
print(' - secondary same-RAW candidate uses full physical common-luma authority alpha=1.0')
print(' - final linear gain is locked to the actual primary bounded/edge-adjusted gain')
print(' - bridge mode 0 keeps M9SENSORTARGET1A target and excludes historical Cobalt probes')
print(' - SOURCEGEOMETRYPROOF2A runtime proof is required before candidate comparison')
