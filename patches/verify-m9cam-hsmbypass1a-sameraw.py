#!/usr/bin/env python3
from pathlib import Path
import sys, re

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-hsmbypass1a-sameraw.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
if not p.exists(): raise SystemExit(f'missing renderer: {p}')
s = p.read_text()

def require(token, label):
    if token not in s: raise SystemExit(f'HSMBYPASS1A verify missing {label}: {token}')

def forbid_in(text, token, label):
    if token in text: raise SystemExit(f'HSMBYPASS1A verify forbidden {label}: {token}')

def block(start_token, end_token):
    a = s.index(start_token)
    b = s.index(end_token, a)
    return s[a:b]

require('bridgeProbeName = "native_plus_target_input_adapter1a_hsm_bypass1a";', 'mode4 label')
require('targetInputAdapter1AApplied = true;', 'target adapter retained')
require('bridgeProbeHistoricalHsmApplied = false;', 'historical HSM disabled')
require('ctx.camToPp = matMul3(bridgeProbeBasis, nativeCamToPpBeforeProbe);', 'target adapter basis retained')
require('targetInputAdapterBasisMaxAbsFromIdentity = maxAbsDeltaIdentity3(bridgeProbeBasis);', 'adapter diagnostic retained')
require('sameRawColorVariant", "HSMBYPASS1A"', 'variant telemetry')
require('sameRawColorControl", "HSMCONTROL1A_run_35085472220"', 'control telemetry')
require('d.put("cobaltHueSatMapApplied", false);', 'Cobalt HSM disabled telemetry')
require('d.put("identityHsmApplied", true);', 'identity telemetry')
require('public static final int SATURATION_BANK = 3;', 'SAT3 frozen')

m4 = block('            } else if (bridgeProbeMode == 4) {',
           '            } else if (bridgeProbeMode != 0) {')
forbid_in(m4, 'cal.hsmA', 'Cobalt hsmA in mode4')
forbid_in(m4, 'cal.hsmD65', 'Cobalt hsmD65 in mode4')
if m4.count('0.0, 1.0, 1.0') != 4:
    raise SystemExit('HSMBYPASS1A verify identity HSM does not contain four exact identity entries')
if 'ctx.hueDivisions = 2;' not in m4 or 'ctx.satDivisions = 2;' not in m4:
    raise SystemExit('HSMBYPASS1A verify identity HSM dimensions not 2x2')

# Production call remains mode 4. Match the exact call fragment around its frozen gains.
prod = block('private static RenderCore renderNativeSourceProduction1P(',
             '    private static RenderCore renderCore(')
if not re.search(r'1\.0,\s*\n\s*true,\s*\n\s*4,\s*\n\s*true,', prod):
    raise SystemExit('HSMBYPASS1A verify production bridgeProbeMode is not 4')

# Critical downstream stage declarations must remain intact.
require('M9TargetFirmwareCalibration.get().curve02', 'firmware curve02 path retained')
require('BT601', 'BT601 telemetry retained')
require('TG1', 'TG1 telemetry retained')

print('HSMBYPASS1A_SAMERAW verify OK')
print('  TARGETINPUTADAPTER1A retained: yes')
print('  historical Cobalt HSM applied: no')
print('  identity HSM 2x2: yes')
print('  SAT3 frozen: yes')
print('  production bridgeProbeMode: 4')
