#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-virtualbv1a-cal1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9VirtualBv1A.java'
if not p.exists():
    raise SystemExit('VIRTUALBV1A-CAL1A requires generated M9VirtualBv1A.java')
s = p.read_text()
if 'public static final String SCHEMA = "m9cam.virtualbv.v1"' not in s:
    raise SystemExit('VIRTUALBV1A-CAL1A schema anchor missing')
if 'private static final double PROVISIONAL_REFERENCE_Y = 100.0;' not in s:
    raise SystemExit('VIRTUALBV1A-CAL1A initial reference-Y anchor missing')
s = s.replace('private static final double PROVISIONAL_REFERENCE_Y = 100.0;',
              'private static final double PROVISIONAL_REFERENCE_Y = 120.0;', 1)
s = s.replace('provisional_zero_offset_reference_y100_not_absolute_m9_ttl_calibration',
              'provisional_zero_offset_reference_y120_from_existing_m9cam_corpus_not_absolute_m9_ttl_calibration', 1)
p.write_text(s)
print('M9Cam VIRTUALBV1A CAL1A applied')
print(' - provisional neutral meter proxy Y changed from 100 to 120')
print(' - value is corpus-derived research calibration, NOT an M9 or M10-R firmware constant')
print(' - no exposure mutation; raw signed meter delta remains unbounded')
