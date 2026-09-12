#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
CPP = ROOT / 'app/src/main/cpp/m9color_jni.cpp'
JAVA = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java'
for p in (CPP, JAVA):
    if not p.exists():
        raise SystemExit('SHARPSOURCE1C-RBANCHOR1A missing ' + str(p))

s = CPP.read_text()
if 'SHARPNESS_SHARPSOURCE1B_ID' not in s or 'm9SharpSourceLeicaGreen14' not in s:
    raise SystemExit('SHARPSOURCE1C-RBANCHOR1A requires assembled SHARPSOURCE1B parent')
if 'SHARPNESS_SHARPSOURCE1C_RBANCHOR1A_ID' in s:
    raise SystemExit('SHARPSOURCE1C-RBANCHOR1A already applied')

old = '''                        // GreenInterpolationWithCo(+3) + Noise mode2(+4) + Sharp(+2)
                        // gives the firmware-proven cumulative support margin of 9 px.
                        if(x>=9 && x<width-9 && y>=9 && y<height-9){
                            const int delta=static_cast<int>(closureSharp14[p])-static_cast<int>(sharpSourceGreen14[p]);
                            dst[0]=m9ClosureQ16(m9ClosureClamp14(static_cast<int>(m9ClosureQ14(base[0]))+delta));
                            dst[1]=m9ClosureQ16(m9ClosureClamp14(static_cast<int>(m9ClosureQ14(base[1]))+delta));
                            dst[2]=m9ClosureQ16(m9ClosureClamp14(static_cast<int>(m9ClosureQ14(base[2]))+delta));
                        }else{
                            // Outside Leica's valid accumulated support region, leave the
                            // validated frozen neutral-MHC output byte-for-byte untouched.
                            dst[0]=base[0]; dst[1]=base[1]; dst[2]=base[2];
                        }'''
new = '''                        // GreenInterpolationWithCo(+3) + Noise mode2(+4) + Sharp(+2)
                        // gives the firmware-proven cumulative support margin of 9 px.
                        if(x>=9 && x<width-9 && y>=9 && y<height-9){
                            // SHARPSOURCE1C-RBANCHOR1A: do not graft a Leica-source Sharp
                            // delta onto a different MHC-green baseline. Anchor reconstructed
                            // RGB to the sharpened Leica green/base exactly, then carry the
                            // frozen neutral-MHC R-G and B-G differences only as temporary
                            // colour-difference proxies until exact BF561 lane semantics close.
                            const int sg=static_cast<int>(closureSharp14[p]);
                            const int mg=static_cast<int>(m9ClosureQ14(base[1]));
                            const int dr=static_cast<int>(m9ClosureQ14(base[0]))-mg;
                            const int db=static_cast<int>(m9ClosureQ14(base[2]))-mg;
                            dst[0]=m9ClosureQ16(m9ClosureClamp14(sg+dr));
                            dst[1]=m9ClosureQ16(static_cast<uint16_t>(sg));
                            dst[2]=m9ClosureQ16(m9ClosureClamp14(sg+db));
                        }else{
                            // Outside Leica's valid accumulated support region, leave the
                            // validated frozen neutral-MHC output byte-for-byte untouched.
                            dst[0]=base[0]; dst[1]=base[1]; dst[2]=base[2];
                        }'''
if s.count(old) != 1:
    raise SystemExit('SHARPSOURCE1C-RBANCHOR1A closure anchor count=' + str(s.count(old)))
s = s.replace(old, new, 1)

old_id = '// SHARPNESS_SHARPSOURCE1B_ID: menu=Standard slot=0 internalMode=4 scale=2x nNoise=2 supportMargin=9 sharpSource=LeicaGreen14 rgbFoundation=MHCNeutralFrozen'
new_id = '// SHARPNESS_SHARPSOURCE1C_RBANCHOR1A_ID: menu=Standard slot=0 internalMode=4 scale=2x nNoise=2 supportMargin=9 sharpSource=LeicaGreen14 rgbFoundation=MHCNeutralFrozen rbPolicy=sharpLeicaGreen_plus_frozenMhcRgBg_differences'
if s.count(old_id) != 1:
    raise SystemExit('SHARPSOURCE1C-RBANCHOR1A native identity anchor count=' + str(s.count(old_id)))
s = s.replace(old_id, new_id, 1)
CPP.write_text(s)

j = JAVA.read_text()
repls = {
    'root.put("sharpnessResearch", "SHARPSOURCE1B");': 'root.put("sharpnessResearch", "SHARPSOURCE1C_RBANCHOR1A");',
    'root.put("sharpnessRgbFoundation", "MHCNeutralFrozen");': 'root.put("sharpnessRgbFoundation", "MHCNeutralFrozen_color_difference_proxy");',
    'root.put("sharpnessCorrectionPolicy", "delta(sharp(leicaGreen14)-leicaGreen14)-applied-equally-to-frozen-MHC-RGB");': 'root.put("sharpnessCorrectionPolicy", "anchor_to_sharpLeicaGreen14_then_restore_frozenMHC_RminusG_BminusG_proxy");',
}
for a,b in repls.items():
    if j.count(a) != 1:
        raise SystemExit('SHARPSOURCE1C-RBANCHOR1A timing anchor count for ' + a + '=' + str(j.count(a)))
    j = j.replace(a,b,1)
rb_anchor = '        root.put("sharpnessCorrectionPolicy", "anchor_to_sharpLeicaGreen14_then_restore_frozenMHC_RminusG_BminusG_proxy");\n'
rb_insert = rb_anchor + '        root.put("sharpnessRbPolicy", "RBANCHOR1A_sharpLeicaGreen_plus_frozenMHC_color_differences_proxy");\n'
if j.count(rb_anchor) != 1:
    raise SystemExit('SHARPSOURCE1C-RBANCHOR1A rbPolicy insert anchor count=' + str(j.count(rb_anchor)))
j = j.replace(rb_anchor, rb_insert, 1)
JAVA.write_text(j)
print('SHARPSOURCE1C-RBANCHOR1A applied: sharpened Leica green anchors RGB; frozen MHC R-G/B-G retained only as proxy differences; supportMargin=9')
