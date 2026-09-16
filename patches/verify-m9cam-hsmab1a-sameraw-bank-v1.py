#!/usr/bin/env python3
from pathlib import Path
import sys, re

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-hsmab1a-sameraw-bank.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
if not p.exists():
    raise SystemExit(f'HSMAB1A missing renderer: {p}')
s = p.read_text()

def require(token, label):
    if token not in s:
        raise SystemExit(f'HSMAB1A verify missing {label}: {token}')

def span(start_token, end_token):
    a = s.index(start_token)
    b = s.index(end_token, a)
    return s[a:b]

require('private static final boolean DEMOSAIC_DIAGNOSTIC_BANK_ENABLED = true; // HSMAB1A same-RAW research bank', 'enabled bank')
require('public static final int SATURATION_BANK = 3;', 'SAT3 frozen')
require('public static final int JPEG_QUALITY = 95;', 'JPEG quality frozen')
require('int[] bridgeProbeModes = {4, 60};', 'A/B modes')
require('boolean[] selfMeterFlags = {true, false};', 'gain lock')
require('_HSMCONTROL1A_SAMERAW', 'A suffix')
require('_HSMBYPASS1A_SAMERAW_GAINLOCK', 'B suffix')
require('HSMBYPASS1A_B_locked_to_HSMCONTROL1A_A_exact_effective_render_gain', 'gain telemetry')
require('skipped_hsmab1a_requires_conventional_bayer', 'generic Bayer gate')
if 'skipped_legacy_diagnostic_requires_RGGB' in s:
    raise SystemExit('HSMAB1A verify legacy RGGB-only diagnostic gate still present')

mode4 = span('            } else if (bridgeProbeMode == 4) {',
             '            } else if (bridgeProbeMode == 60) {')
for token in ['targetInputAdapter1AApplied = true;', 'cal.hsmA[i]', 'cal.hsmD65[i]',
              'ctx.hueDivisions = cal.hueDivisions;', 'ctx.satDivisions = cal.satDivisions;']:
    if token not in mode4:
        raise SystemExit('HSMAB1A verify A control lost ' + token)

mode60 = span('            } else if (bridgeProbeMode == 60) {',
              '            } else if (bridgeProbeMode != 0) {')
for token in ['targetInputAdapter1AApplied = true;',
              'TargetInputAdapter1A targetInput = buildTargetInputAdapter1A(nativeSource, cal);',
              'ctx.camToPp = matMul3(bridgeProbeBasis, nativeCamToPpBeforeProbe);',
              'ctx.hueDivisions = 2;', 'ctx.satDivisions = 2;']:
    if token not in mode60:
        raise SystemExit('HSMAB1A verify B lost ' + token)
if 'cal.hsmA' in mode60 or 'cal.hsmD65' in mode60:
    raise SystemExit('HSMAB1A verify B still references historical Cobalt HSM tables')
if mode60.count('0.0, 1.0, 1.0') != 4:
    raise SystemExit('HSMAB1A verify B identity HSM is not exact 2x2 identity')

prod = span('private static RenderCore renderNativeSourceProduction1P(',
            '    private static RenderCore renderCore(')
if not re.search(r'1\.0,\s*\n\s*true,\s*\n\s*4,\s*\n\s*true,', prod):
    raise SystemExit('HSMAB1A verify primary production mode is no longer mode 4')
for token in ['d.put("cobaltHueSatMapApplied", true);',
              'd.put("identityHsmApplied", false);',
              'd.put("targetInputAdapter1AProduction", true);']:
    if token not in prod:
        raise SystemExit('HSMAB1A verify primary control telemetry lost ' + token)

main_save = s.index('boolean jpgSaved = ImageSaver.Util.saveBitmapAsJPGPayloadM9')
bank = s.index('if (primaryRoute && DEMOSAIC_DIAGNOSTIC_BANK_ENABLED)')
if bank <= main_save:
    raise SystemExit('HSMAB1A diagnostic bank runs before primary JPEG save')
require('variantFixedGain = skyChromaControlEffectiveRenderGain;', 'B uses A gain')
require('variantDiag.put("sameRawAsPrimary", true);', 'same RAW telemetry')
require('nativeAb1A.put("productionBehaviorChanged", false);', 'primary preservation telemetry')

print('HSMAB1A_SAMERAW_BANK verify OK')
print('  primary: frozen TARGETINPUTADAPTER1A + historical HSM mode4')
print('  A diagnostic: mode4 same-RAW control')
print('  B diagnostic: mode60 target-input + exact identity HSM')
print('  B gain locked to A: yes')
print('  conventional Bayer CFA 0..3 eligible: yes')
print('  SAT3/JPEG95 frozen: yes')
print('  diagnostic bank runs after primary JPEG save: yes')
