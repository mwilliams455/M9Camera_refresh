#!/usr/bin/env python3
from pathlib import Path
import hashlib, struct, sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
CPP = ROOT / 'app/src/main/cpp/m9color_jni.cpp'
if not CPP.exists():
    raise SystemExit('CLOSURETEST1B verifier missing ' + str(CPP))
s = CPP.read_text()

need = [
    'SHARPNESS_CLOSURETEST1B',
    'const int baseCorr=m9ClosureSlot0Coeff(1024+r);',
    'const int doubledCorr=baseCorr*2;',
    'doubledCorr < -2048 ? -2048 : (doubledCorr > 2048 ? 2048 : doubledCorr)',
    'Standard mode4 x2',
    '[=, &greenPlane, &closureSharp14]',
]
for x in need:
    if x not in s:
        raise SystemExit('CLOSURETEST1B missing anchor: ' + x)
if 'const int corr=m9ClosureSlot0Coeff(1024+r); // Standard == 1x base LUT.' in s:
    raise SystemExit('CLOSURETEST1B stale 1x Standard correction still active')
if 'baseCorr<<1' in s or 'baseCorr << 1' in s:
    raise SystemExit('CLOSURETEST1B must not use signed left shift for negative LUT coefficients')

# Preserve the already-fixed file-scope helper ordering from CLOSURETEST1A.
helper = s.index('inline uint16_t m9ClosureQ14')
jni = s.index('Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_demosaicMhcRggb(')
seam = s.index('// SPLITDEMOSAIC1A research seam')
if not (helper < jni < seam):
    raise SystemExit('CLOSURETEST1B unexpected helper/JNI/seam ordering')

# Independently reconstruct the canonical slot0 base bank and the proven
# Standard/slot0 mode4 transform. Base bytes stay canonical; only working
# coefficients are doubled and clamped exactly as recovered from firmware.
lut = [i-1024 for i in range(2050)]
exc = {
    997:-26,998:-25,999:-24,1000:-23,1001:-21,1002:-20,1003:-19,1004:-17,
    1005:-16,1006:-15,1007:-13,1008:-12,1009:-11,1010:-10,1011:-9,1012:-8,
    1013:-7,1014:-6,1015:-5,1016:-4,1017:-3,1018:-2,1019:-2,1020:-1,1021:-1,
    1022:0,1023:0,1025:0,1026:0,1027:1,1028:1,1029:2,1030:2,1031:3,1032:4,
    1033:5,1034:6,1035:7,1036:8,1037:9,1038:10,1039:11,1040:12,1041:13,
    1042:15,1043:16,1044:17,1045:19,1046:20,1047:21,1048:23,1049:24,1050:25,1051:26,
}
for i,v in exc.items():
    lut[i] = v
base_hash = hashlib.sha256(struct.pack('<2050h', *lut)).hexdigest()
expected = '2317595946f76c3965b7479c1c68fd66e5a9ac8be81292a91f944a6cde85f6e9'
if base_hash != expected:
    raise SystemExit('CLOSURETEST1B canonical slot0 hash mismatch ' + base_hash)

def mode4(v):
    v *= 2
    return -2048 if v < -2048 else (2048 if v > 2048 else v)

work = [mode4(v) for v in lut]
assert work[0] == -2048
assert work[997] == -52
assert work[1024] == 0
assert work[1051] == 52
assert work[2048] == 2048
assert work[2049] == 2048
assert min(work) >= -2048 and max(work) <= 2048
work_hash = hashlib.sha256(struct.pack('<2050h', *work)).hexdigest()

print('CLOSURETEST1B verify PASS')
print(' helper_scope=file')
print(' fixed_iso=160 slot=0 menu=Standard internal_mode=4 scale=2x')
print(' coefficient_clamp=[-2048,+2048]')
print(' slot0_base_sha256=' + base_hash)
print(' slot0_mode4_working_sha256=' + work_hash)
print(' quantization=endpoint-nearest norm16<->14 (unchanged explicit mobile-port choice)')
print(' rb_policy=preserve frozen MHC R-G/B-G around sharpened green (unchanged diagnostic approximation)')
