#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
R = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
B = ROOT / 'app/build.gradle'
for p in (R, B):
    if not p.exists():
        raise SystemExit('FROZEN1A missing ' + str(p))

def rep(s, old, new, name):
    c = s.count(old)
    if c != 1:
        raise SystemExit(f'FROZEN1A {name} anchor count={c}')
    return s.replace(old, new, 1)

r = R.read_text()
b = B.read_text()

# Promotion is intentionally narrow: the validated live-neutral MHC path is already
# the primary render path. Freeze it and stop emitting the three-way same-RAW bank.
r = rep(
    r,
    '    public static final boolean SAVE_PARITY_PNG = false;\n',
    '    public static final boolean SAVE_PARITY_PNG = false;\n'
    '    // DEMOSAICMHCNEUTRAL1A-FROZEN1A: validation bank retained in source only as a\n'
    '    // rollback/forensic control. Normal capture emits one production JPEG + DNG.\n'
    '    private static final boolean DEMOSAIC_DIAGNOSTIC_BANK_ENABLED = false;\n',
    'bank constant')

r = rep(
    r,
    '            // BASISHSM1C-SHADINGPARITY1A: same-RAW BASIS_HSM self-meter shading OFF-vs-ON. Primary JPEG is already\n'
    '            // encoded above and is never replaced by either experimental output.\n'
    '            if (primaryRoute) {',
    '            // DEMOSAICMHCNEUTRAL1A-FROZEN1A: the historical same-RAW bank is dormant.\n'
    '            // It stays compiled for explicit forensic rollback, but normal capture must not emit it.\n'
    '            if (primaryRoute && DEMOSAIC_DIAGNOSTIC_BANK_ENABLED) {',
    'bank gate')

r = rep(
    r,
    '            d.put("demosaicNeutralVariant", demosaicNeutralEa1A ? "EA_SAT3_GAINLOCK" : (demosaicPlainMhc1A ? "MHC_PLAIN_SAT3_GAINLOCK" : "MHC_NEUTRAL_SAT3_CONTROL"));',
    '            d.put("demosaicNeutralVariant", demosaicNeutralEa1A ? "EA_SAT3_GAINLOCK"\n'
    '                    : (demosaicPlainMhc1A ? "MHC_PLAIN_SAT3_GAINLOCK"\n'
    '                    : (bridgeProbeMode == 50 ? "MHC_NEUTRAL_SAT3_CONTROL"\n'
    '                    : "MHC_NEUTRAL_SAT3_PRODUCTION")));\n'
    '            d.put("demosaicMhcNeutralFrozen1A", !demosaicNeutralEa1A\n'
    '                    && !demosaicPlainMhc1A && bridgeProbeMode != 50);',
    'variant telemetry')

r = rep(
    r,
    '            d.put("demosaicControl", demosaicNeutralEa1A\n'
    '                    ? "active_sameRAW_OpenCV_EA_gainlocked_control"\n'
    '                    : demosaicPlainMhc1A ? "active_sameRAW_plain_MHC_gainlocked_control" : "production_candidate_liveNeutral_balanced_MHC");',
    '            d.put("demosaicControl", demosaicNeutralEa1A\n'
    '                    ? "active_sameRAW_OpenCV_EA_gainlocked_control"\n'
    '                    : (demosaicPlainMhc1A ? "active_sameRAW_plain_MHC_gainlocked_control"\n'
    '                    : (bridgeProbeMode == 50 ? "sameRAW_liveNeutral_MHC_control"\n'
    '                    : "production_frozen_liveNeutral_balanced_MHC")));',
    'control telemetry')

# The primary-pipeline description occurs in background diagnostics, primary diagnostics,
# and the production renderer. All three describe the same primary path and must now
# explicitly name the promoted demosaic stage.
old_pipeline = 'NORM030 physical LensShadingMap -> native Xiaomi SOURCECAL2A -> BASISHSM1A historical working-basis/H25 target role -> M9 bridge -> TC20 -> SAT3 M06/M07 -> curve02 -> exact BT601 4:2:2 -> M9Modern TG1'
new_pipeline = 'NORM030 physical LensShadingMap -> DEMOSAICMHCNEUTRAL1A live-neutral balanced 5x5 MHC -> native Xiaomi SOURCECAL2A -> BASISHSM1A historical working-basis/H25 target role -> M9 bridge -> TC20 -> SAT3 M06/M07 -> curve02 -> exact BT601 4:2:2 -> M9Modern TG1'
if r.count(old_pipeline) != 3:
    raise SystemExit('FROZEN1A primary pipeline anchor count=' + str(r.count(old_pipeline)))
r = r.replace(old_pipeline, new_pipeline)

# Add promotion-state telemetry only to the unique production wrapper.
r = rep(
    r,
    '        d.put("fixedPrimaryGainReferenceRole", "diagnostic_placeholder_only_not_render_gain_when_selfMeter_true");\n'
    '        d.remove("meterParityGainRatioVsPrimary");\n'
    '        d.remove("meterParityGainDeltaEvVsPrimary");\n'
    '        d.put("pipeline", "' + new_pipeline + '");',
    '        d.put("fixedPrimaryGainReferenceRole", "diagnostic_placeholder_only_not_render_gain_when_selfMeter_true");\n'
    '        d.remove("meterParityGainRatioVsPrimary");\n'
    '        d.remove("meterParityGainDeltaEvVsPrimary");\n'
    '        d.put("pipeline", "' + new_pipeline + '");\n'
    '        d.put("demosaicFoundation", "DEMOSAICMHCNEUTRAL1A_FROZEN1A");\n'
    '        d.put("demosaicDiagnosticBankEnabled", DEMOSAIC_DIAGNOSTIC_BANK_ENABLED);',
    'production promotion telemetry')

version_old = '-demosaicmhc1a-demosaicab1a-demosaicmhcneutral1a'
if b.count(version_old) != 1:
    raise SystemExit('FROZEN1A version anchor count=' + str(b.count(version_old)))
b = b.replace(version_old, version_old + '-frozen1a', 1)

R.write_text(r)
B.write_text(b)
print('DEMOSAICMHCNEUTRAL1A-FROZEN1A promoted: neutral MHC frozen; diagnostic bank disabled; production JPEG+DNG unchanged')
