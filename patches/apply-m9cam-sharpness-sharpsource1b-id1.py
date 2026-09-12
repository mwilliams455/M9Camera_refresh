#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
JAVA = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java'
if not JAVA.exists():
    raise SystemExit('SHARPSOURCE1B-ID1 missing ' + str(JAVA))
s = JAVA.read_text()
if '"sharpnessResearch", "SHARPSOURCE1B"' in s:
    raise SystemExit('SHARPSOURCE1B-ID1 already applied')
anchor = '''        root.put("route", ROUTE);
        root.put("primaryPhotonFinishedImage", true);'''
insert = '''        root.put("route", ROUTE);

        // SHARPSOURCE1B-ID1 -- research identity only. No photographic behavior.
        // Keep these fields in the PRIMARY timing sidecar so a field capture can
        // independently prove which sharpness research arithmetic produced it.
        root.put("sharpnessResearch", "SHARPSOURCE1B");
        root.put("sharpnessMenu", "Standard");
        root.put("sharpnessSlot", 0);
        root.put("sharpnessInternalMode", 4);
        root.put("sharpnessScale", "2x");
        root.put("sharpnessNoiseMode", 2);
        root.put("sharpnessSupportMargin", 9);
        root.put("sharpnessSource", "LeicaGreenInterpolationWithCo-interior14bit");
        root.put("sharpnessRgbFoundation", "MHCNeutralFrozen");
        root.put("sharpnessCorrectionPolicy", "delta(sharp(leicaGreen14)-leicaGreen14)-applied-equally-to-frozen-MHC-RGB");
        root.put("sharpnessBorderPolicy", "outside-9px-preserve-frozen-MHC-exactly");

        root.put("primaryPhotonFinishedImage", true);'''
if s.count(anchor) != 1:
    raise SystemExit('SHARPSOURCE1B-ID1 timing anchor count=' + str(s.count(anchor)))
s = s.replace(anchor, insert, 1)
JAVA.write_text(s)
print('SHARPSOURCE1B-ID1 applied: PRIMARY timing sidecar explicit research identity; renderer unchanged')
