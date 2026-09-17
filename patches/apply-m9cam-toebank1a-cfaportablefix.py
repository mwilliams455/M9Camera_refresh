#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
P = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
s = P.read_text()

old = '''                    nativeAb1A.put("cfaPattern", params.cfaPattern & 0xff);
                    nativeAb1A.put("physicalCameraIdUsedAsSemanticRole", false);
                    nativeAb1A.put("cameraArrayTopologyUsedForRendering", false);
                    if ((params.cfaPattern & 0xff) != 0) {
                        nativeAb1A.put("status", "skipped_legacy_diagnostic_requires_RGGB");
                        nativeAb1A.put("legacyDiagnosticRequiredCfa", 0);
                    } else {
'''
new = '''                    nativeAb1A.put("cfaPattern", params.cfaPattern & 0xff);
                    nativeAb1A.put("resolvedSourceCfaPattern", sourceCfaPattern);
                    nativeAb1A.put("resolvedSourceCfaAuthority", sourceCfaAuthority);
                    nativeAb1A.put("toeBankCfaPortable1A", true);
                    nativeAb1A.put("toeBankLegacyRggbGuardRemoved", true);
                    nativeAb1A.put("physicalCameraIdUsedAsSemanticRole", false);
                    nativeAb1A.put("cameraArrayTopologyUsedForRendering", false);
                    if (!M9CfaResolver.isSupported(sourceCfaPattern)) {
                        nativeAb1A.put("status", "skipped_toebank_unsupported_resolved_cfa");
                        nativeAb1A.put("unsupportedResolvedSourceCfaPattern", sourceCfaPattern);
                    } else {
'''
count = s.count(old)
if count != 1:
    raise SystemExit(f'TOEBANK1A CFAPORTABLEFIX: expected exactly one legacy RGGB guard, found {count}')
s = s.replace(old, new, 1)

# The toe bank must continue to pass the already-resolved physical source CFA into
# the portable renderer. This is the photographic safety condition for BGGR/GRBG/GBRG.
start = s.find('// M9TOEBANK1A: same-RAW global toe-isolation A/B/C bank.')
end = s.find('// FULLSOURCENORM1A: same-RAW, gain-locked source-normalization experiment.', start)
if start < 0 or end < 0:
    raise SystemExit('TOEBANK1A CFAPORTABLEFIX: toe bank boundaries missing')
block = s[start:end]
if 'sourceCfaPattern,' not in block:
    raise SystemExit('TOEBANK1A CFAPORTABLEFIX: toe bank does not pass resolved sourceCfaPattern')
if '_M9_TOE1A_A_CONTROL' not in block or '_M9_TOE1A_B_MILD20' not in block or '_M9_TOE1A_C_MODERATE40' not in block:
    raise SystemExit('TOEBANK1A CFAPORTABLEFIX: toe outputs missing')

P.write_text(s)
print('M9TOEBANK1A CFAPORTABLEFIX applied')
print('legacy raw params RGGB-only diagnostic guard removed')
print('toe bank now gates on resolved sourceCfaPattern via M9CfaResolver.isSupported')
print('BGGR/GRBG/GBRG/RGGB use the same already-resolved portable render path')
print('unsupported CFA remains fail-closed')
