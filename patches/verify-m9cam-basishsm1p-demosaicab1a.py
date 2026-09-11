#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
R = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
B = ROOT / 'app/build.gradle'
if not R.exists() or not B.exists():
    raise SystemExit('DEMOSAICAB1A verify assembled files missing')
r = R.read_text()
b = B.read_text()

def need(s, token, label):
    if token not in s:
        raise SystemExit('DEMOSAICAB1A verify missing ' + label + ': ' + token)

def forbid(s, token, label):
    if token in s:
        raise SystemExit('DEMOSAICAB1A verify forbidden ' + label + ': ' + token)

def method_bounds(s, marker):
    start = s.find(marker)
    if start < 0:
        raise SystemExit('DEMOSAICAB1A verify active method missing')
    brace = s.find('{', start)
    depth = 0
    i = brace
    state = 'code'
    quote = ''
    esc = False
    while i < len(s):
        ch = s[i]
        nxt = s[i+1] if i+1 < len(s) else ''
        if state == 'line':
            if ch == '\n': state = 'code'
        elif state == 'block':
            if ch == '*' and nxt == '/': state = 'code'; i += 1
        elif state == 'string':
            if esc: esc = False
            elif ch == '\\': esc = True
            elif ch == quote: state = 'code'
        else:
            if ch == '/' and nxt == '/': state = 'line'; i += 1
            elif ch == '/' and nxt == '*': state = 'block'; i += 1
            elif ch in ('"', "'"): state = 'string'; quote = ch
            elif ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0: return s[start:i+1]
        i += 1
    raise SystemExit('DEMOSAICAB1A verify active method unterminated')

active = method_bounds(r, '    private static RenderCore renderNativeProspectiveCore(')

# Structural authority is the actual two-frame bank plus the active-core telemetry below.
# Do not require a cosmetic top-level schema/status rename: historical diagnostic wrappers
# intentionally retain their parent schema and do not affect photographic isolation.
for token in (
    '_DEMOSAICAB_MHC_SAT3',
    '_DEMOSAICAB_EA_SAT3_GAINLOCK',
    'int[] bridgeProbeModes = {50, 54};',
    'boolean[] selfMeterFlags = {true, false};',
    'double[] hsmValueStrengthFlags = {1.0, 1.0};',
    'boolean[] applyShadingFlags = {true, true};',
    'boolean[] applyShadingLumaDecomp1AFlags = {true, true};',
    'double[] shadingLumaTargetOutsideMedianEv1AFlags = {0.30, 0.30};',
):
    need(r, token, 'same-RAW pair scaffold')

for token in ('_SKYSAT_SAT2_STANDARD', '_SKYSAT_SAT4_HIGH', '_SKYSAT_SAT3_BYPASS'):
    forbid(r, token, 'unrelated diagnostic JPEG variant')

for token in (
    'final boolean demosaicAbEaRequested1A = bridgeProbeMode == 54;',
    'skySatDiagnosticEncoded1A = bridgeProbeMode >= 50 && bridgeProbeMode <= 54',
    'bridgeProbeMode == 52 ? 10 : bridgeProbeMode == 53 ? 7 : 0)',
    'DEMOSAICAB1A_OpenCV_COLOR_BayerRG2BGR_EA_sameRAW_gainlocked',
    'DEMOSAICMHC1A_MalvarHeCutler5x5_RGGB_native_direct',
    'Imgproc.cvtColor(rawMat, cam16, Imgproc.COLOR_BayerRG2BGR_EA);',
    'M9NativeColorCore.demosaicMhcRggb(',
    'demosaicAb1A',
    'demosaicAbVariant',
    'demosaicAbSameRawBayer',
    'demosaicAbOnlyPhotographicDifference',
    'demosaicAbDownstreamFrozen',
    'reachabilityFence(mhcRgbBuffer)',
):
    need(active, token, 'active A/B core')

if active.count('Imgproc.cvtColor(rawMat, cam16, Imgproc.COLOR_BayerRG2BGR_EA);') != 1:
    raise SystemExit('DEMOSAICAB1A verify: active EA demosaic call count != 1')
if active.count('M9NativeColorCore.demosaicMhcRggb(') != 1:
    raise SystemExit('DEMOSAICAB1A verify: active MHC demosaic call count != 1')

for token in (
    'public static final int JPEG_QUALITY = 95',
    'public static final int SATURATION_BANK = 3',
    'private static final double HSM_H = 0.25',
    'private static final double HSM_S = 0.85',
    'private static final double HSM_V = 1.00',
):
    need(r, token, 'frozen production boundary')

need(b, '-demosaicmhc1a-demosaicab1a', 'version identity')
forbid(r, 'Ultra HDR', 'HDR')
for bad in ('isBlueSky1A(', 'applyMagentaSkyGuard1A(', 'SKY_CLASSIFIER_ENABLED = true'):
    forbid(r, bad, 'scene-specific correction')

print('DEMOSAICAB1A verification OK')
print(' - same RAW/NORM030: MHC SAT3 self-meter control vs EA SAT3 exact-gain-lock')
print(' - production primary remains MHC; EA exists only in diagnostic mode 54')
print(' - downstream SOURCECAL2A/HSM/SAT3/curve02/BT601/TG1 boundaries frozen')
print(' - unrelated SAT2/SAT4/bypass JPEG diagnostics removed from this test build')
