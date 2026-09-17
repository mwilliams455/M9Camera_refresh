#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
P = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
s = P.read_text()
checks = []

def ck(name, cond):
    ok = bool(cond)
    checks.append((name, ok))
    print(('PASS' if ok else 'FAIL'), name)

bank_start = s.find('if (primaryRoute && DEMOSAIC_DIAGNOSTIC_BANK_ENABLED)')
bank_end = s.find('// FULLSOURCENORM1A: same-RAW, gain-locked source-normalization experiment.', bank_start)
bank = s[bank_start:bank_end] if bank_start >= 0 and bank_end > bank_start else ''

ck('bank_boundaries', bool(bank))
ck('legacy_rggb_skip_removed', 'skipped_legacy_diagnostic_requires_RGGB' not in bank)
ck('legacy_raw_cfa_guard_removed', 'if ((params.cfaPattern & 0xff) != 0)' not in bank)
ck('resolved_cfa_telemetry', '"resolvedSourceCfaPattern", sourceCfaPattern' in bank)
ck('resolved_cfa_authority_telemetry', '"resolvedSourceCfaAuthority", sourceCfaAuthority' in bank)
ck('portable_marker', '"toeBankCfaPortable1A", true' in bank)
ck('legacy_guard_removed_marker', '"toeBankLegacyRggbGuardRemoved", true' in bank)
ck('resolved_cfa_gate', 'if (!M9CfaResolver.isSupported(sourceCfaPattern))' in bank)
ck('unsupported_fail_closed', 'skipped_toebank_unsupported_resolved_cfa' in bank)
ck('toe_control_suffix', '_M9_TOE1A_A_CONTROL' in bank)
ck('toe_mild_suffix', '_M9_TOE1A_B_MILD20' in bank)
ck('toe_moderate_suffix', '_M9_TOE1A_C_MODERATE40' in bank)
ck('toe_experiment', 'M9TOEBANK1A_sameRAW_control_mild_moderate' in bank)
ck('source_cfa_passed_to_render', 'sourceCfaPattern,' in bank)
ck('toe_helper_retained', 'private static JSONObject applyM9Toe1A(Bitmap bitmap, double strength)' in s)
ck('tonebound050_retained', 'm9cam.tonebound.v1a.050ev' in s)
ck('fullsource_retained', '_M9_SOURCEFULLNORM1A_GAINLOCK.jpg' in s)
ck('m9_target_retained', 'M9SENSORTARGET1A' in s)
ck('sat2_retained', 'SAT2_M04_M05' in s)
ck('curve02_retained', 'm9_curve02_firmware.bin' in s or 'firmware curve02' in s)

bad = [name for name, ok in checks if not ok]
if bad:
    raise SystemExit('M9TOEBANK1A CFAPORTABLEFIX verify failed: ' + ', '.join(bad))
print('M9TOEBANK1A CFAPORTABLEFIX VERIFY PASS', len(checks), 'checks')
print('Toe bank is no longer restricted to raw params RGGB and uses resolved CFA authority')
