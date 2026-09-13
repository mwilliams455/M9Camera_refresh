#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
CPP = ROOT / 'app/src/main/cpp/m9color_jni.cpp'
R = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
T = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java'
G = ROOT / 'app/build.gradle'
for p in (CPP, R, T, G):
    if not p.exists():
        raise SystemExit('ONEOFF-SAT2 missing ' + str(p))

cpp = CPP.read_text()
r = R.read_text()
t = T.read_text()
g = G.read_text()

# Guard: this patch is valid only after the exact FULLISO/RBANCHOR parent is assembled.
for marker in (
    'SHARPNESS_STANDARD_FULLISO1A_ID',
    'constexpr std::array<int64_t, 9> Q2E',
    'constexpr std::array<int64_t, 9> Q2O',
    'const std::array<int64_t, 9>* qPtr = &(evenBranch ? QE : QO);',
):
    if marker not in cpp:
        raise SystemExit('ONEOFF-SAT2 required native marker missing: ' + marker)
if 'STANDARD_FULLISO1A_RBANCHOR1A' not in t:
    raise SystemExit('ONEOFF-SAT2 requires STANDARD_FULLISO1A_RBANCHOR1A timing identity')

# One and only photographic mutation in this branch:
# production/default saturation family becomes exact recovered SAT2 Standard M04/M05.
old = 'const std::array<int64_t, 9>* qPtr = &(evenBranch ? QE : QO);'
new = '''// ONEOFF_SAT2_FULLISO1A: production/default family uses exact recovered Leica SAT2 Standard M04/M05.\n    // Disposable A/B only; canonical production remains SAT3 M06/M07 on all normal branches.\n    const std::array<int64_t, 9>* qPtr = &(evenBranch ? Q2E : Q2O);'''
if cpp.count(old) != 1:
    raise SystemExit('ONEOFF-SAT2 default saturation selector anchor count=' + str(cpp.count(old)))
cpp = cpp.replace(old, new, 1)

# Preserve explicit diagnostic selectors. Mode 9 still points to the same SAT2 family;
# mode 10 remains SAT4 and all other downstream math is unchanged.
identity_anchor = '// SHARPNESS_STANDARD_FULLISO1A_ID:'
idx = cpp.find(identity_anchor)
if idx < 0:
    raise SystemExit('ONEOFF-SAT2 FULLISO identity marker missing')
line_end = cpp.find('\n', idx)
cpp = cpp[:line_end+1] + '// ONEOFF_SAT2_FULLISO1A_ID: saturation=SAT2_STANDARD_M04_M05 exact; disposable_nonproduction_AB\n' + cpp[line_end+1:]

# Telemetry/provenance only: make it impossible to confuse this APK with SAT3 production.
if 'root.put("sharpnessResearch", "STANDARD_FULLISO1A_RBANCHOR1A");' in t:
    t = t.replace(
        'root.put("sharpnessResearch", "STANDARD_FULLISO1A_RBANCHOR1A");',
        'root.put("sharpnessResearch", "STANDARD_FULLISO1A_RBANCHOR1A");\n        root.put("saturationOneOff", "SAT2_STANDARD_M04_M05");\n        root.put("saturationOneOffProductionEligible", false);',
        1)
else:
    raise SystemExit('ONEOFF-SAT2 timing telemetry anchor missing')

# Renderer diagnostics get a branch-local marker without changing any arithmetic.
diag_anchor = 'd.put("sharpnessMenu", "Standard");'
if r.count(diag_anchor) != 1:
    raise SystemExit('ONEOFF-SAT2 renderer telemetry anchor count=' + str(r.count(diag_anchor)))
r = r.replace(
    diag_anchor,
    diag_anchor + '\n            d.put("saturationFamily", "SAT2_STANDARD_M04_M05_ONEOFF");\n            d.put("saturationDefaultProductionFamily", "SAT3_M06_M07_on_normal_branches");',
    1)

# Branch-local APK identity only.
if 'oneoffsat2' not in g.lower():
    import re
    m = re.search(r'versionName\s+[\'\"]([^\'\"]+)[\'\"]', g)
    if not m:
        raise SystemExit('ONEOFF-SAT2 versionName anchor missing')
    old_version = m.group(1)
    new_version = old_version + '-oneoffsat2'
    g = g[:m.start(1)] + new_version + g[m.end(1):]

CPP.write_text(cpp)
R.write_text(r)
T.write_text(t)
G.write_text(g)
print('ONEOFF SAT2 FULLISO1A applied')
print(' - production/default saturation family: exact SAT2 Standard M04/M05')
print(' - normal branches remain SAT3 M06/M07')
print(' - FULLISO/RBANCHOR1A/Noise2/support9/TC20/NORM030/HSM/curve02/BT601/TG1 unchanged')
