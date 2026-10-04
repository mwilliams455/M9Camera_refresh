#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
cp = root / 'app/src/main/cpp/m9color_jni.cpp'
bp = root / 'app/build.gradle'

c = cp.read_text()
old_guard = '|| skyChromaMode1A < 0 || skyChromaMode1A > 4'
new_guard = '|| skyChromaMode1A < 0 || skyChromaMode1A > 8'
count = c.count(old_guard)
if count != 1:
    raise SystemExit(f'SKYDOWN1A-FIX1 native mode guard: expected 1 anchor, found {count}')
c = c.replace(
    old_guard,
    '// SKYDOWN1A-FIX1: modes 5..8 are diagnostic-only downstream probes; production remains mode 0.\n            ' + new_guard,
    1,
)
cp.write_text(c)

b = bp.read_text()
old_version = '-basishsm1p-skydown1a-nativewpclip1a'
new_version = '-basishsm1p-skydown1a-fix1-nativewpclip1a'
count = b.count(old_version)
if count != 1:
    raise SystemExit(f'SKYDOWN1A-FIX1 version marker: expected 1 anchor, found {count}')
bp.write_text(b.replace(old_version, new_version, 1))

print('M9Cam BASISHSM1P SKYDOWN1A-FIX1 native mode-contract repair applied')
print(' - native createContext now accepts diagnostic modes 0..8')
print(' - production mode 0 and all photographic arithmetic unchanged')
print(' - SKYDOWN1A modes 5/6/7/8 can reach their existing isolated native branches')
