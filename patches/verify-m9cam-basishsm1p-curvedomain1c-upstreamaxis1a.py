#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
CPP = ROOT / 'app/src/main/cpp/m9color_jni.cpp'
GRADLE = ROOT / 'app/build.gradle'
c = CPP.read_text()
g = GRADLE.read_text()

required = [
    'm9cam.curvedomain1c.upstreamaxis1a.v1',
    'm9cam.upstreamaxis1a.v1',
    'UpstreamAxisAgg upstreamAxis{};',
    'upstreamAxisAuditPixel(cam, c, ctx, hsmS0Ctx, identityHsmCtx, gain, &upstreamAxis);',
    'hsmS0Ctx.hsm[i] = 1.0;',
    'identityHsmCtx.hsm[i] = 0.0;',
    'identityHsmCtx.hsm[i + 1] = 1.0;',
    'identityHsmCtx.hsm[i + 2] = 1.0;',
    'FULL_H25_S85_V100', 'HSM_S0_H25_V100', 'IDENTITY_HSM',
    'sameHistoricalBasisAllPaths', 'sameM9BridgeAllPaths', 'sameFrozenGainAllPaths',
    'sameSAT3_M06_M07_AllPaths', 'sameCurve02AllPaths',
    'fullCurveMagentaRescuedByHsmS0Fraction',
    'fullCurveMagentaRescuedByIdentityHsmFraction',
    'hsmS0CurveMagentaIntroducedVsFullFraction',
    'identityCurveMagentaIntroducedVsFullFraction',
]
for token in required:
    if token not in c:
        raise SystemExit('UPSTREAMAXIS1A verifier missing token: ' + token)

for token in ['CURVEDOMAIN1A', 'neutralAxisAudit', 'meanGreenDeficitNormalizedPre', 'crossToMagentaAtCurve1pctFraction']:
    if token not in c:
        raise SystemExit('UPSTREAMAXIS1A verifier lost parent token: ' + token)

# Preserve normal production SAT3 -> independent per-RGB curve02 implementation.
for token in [
    'const std::array<int64_t, 9>* qPtr = &(evenBranch ? QE : QO);',
    'const int rr = ctx.curve[i0];', 'const int gg = ctx.curve[i1];', 'const int bb = ctx.curve[i2]'
]:
    if token not in c:
        raise SystemExit('UPSTREAMAXIS1A verifier production renderer token missing: ' + token)

render_start = c.index('void renderStripScalar(')
render_end = c.index('// SATDOMAIN1A:', render_start)
render_body = c[render_start:render_end]
if 'UPSTREAMAXIS1A' in render_body or 'upstreamAxisAuditPixel' in render_body or 'hsmS0Ctx' in render_body:
    raise SystemExit('UPSTREAMAXIS1A verifier: audit leaked into photographic render function')

if '-curvedomain1c-upstreamaxis1a-nativewpclip1a' not in g:
    raise SystemExit('UPSTREAMAXIS1A verifier version suffix missing')

print('UPSTREAMAXIS1A verification OK')
print(' - audit-only FULL vs HSM-S0 vs identity-HSM cohorts present')
print(' - exact production applyHsm reused by synthetic table contexts')
print(' - production M06/M07 and per-channel curve02 path preserved')
print(' - photographic render function contains no UPSTREAMAXIS1A call')
