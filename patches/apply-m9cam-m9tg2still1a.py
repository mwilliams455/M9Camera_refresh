#!/usr/bin/env python3
"""Port validated M9TG2NEUTRAL1A preview math into native saved-JPEG BT.601 4:2:2."""
from pathlib import Path
import hashlib,shutil,sys
if len(sys.argv)!=2: raise SystemExit("usage: apply-m9cam-m9tg2still1a.py <PhotonCamera-root>")
root=Path(sys.argv[1]).resolve();here=Path(__file__).resolve().parent;repo=here.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
java=root/"app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java"
cpp=root/"app/src/main/cpp/m9color_jni.cpp"
hdr=root/"app/src/main/cpp/m9tg2_chroma.h"
gradle=root/"app/build.gradle"
if sha(java)!="a7dfa41df5eaa92c69ef4236e6d697f10e6681cadfbfc46d66869628d405ab56": raise SystemExit("TG2STILL1A still baseline mismatch")
if sha(cpp)!="23037daba9fe5acbffb68f4bdf1fdce394eb476d7312ef0b57d514678b95a1bc": raise SystemExit("TG2STILL1A native baseline mismatch")
if hdr.exists(): raise SystemExit("TG2STILL1A unexpected existing header")

def one(s,o,n,label):
    if s.count(o)!=1: raise SystemExit(f"TG2STILL1A {label}: expected 1 anchor, found {s.count(o)}")
    return s.replace(o,n,1)

j=java.read_text()
j=one(j,
"""            final double tgWeight = tungstenGuardWeight(ctx.cct);
            final double tgCbGain = 1.0 - TG_NEG_CB_COMPRESSION * tgWeight;
            final double tgCrGain = 1.0 - TG_NEG_CR_COMPRESSION * tgWeight;
""",
"""            final double tgWeight = tungstenGuardWeight(ctx.cct);
            // M9TG2STILL1A keeps the stable JNI signature. Both legacy gain
            // slots now carry the same 0..1 tungsten weight; native colour
            // computes bounded yellow/orange/green chroma correction directly.
            final double tgCbGain = tgWeight;
            final double tgCrGain = tgWeight;
""","Java TG2 weight transport")
j=one(j,'d.put("tungstenGuard", "TG1");','d.put("tungstenGuard", "TG2NEUTRAL1A_STILL");',"diagnostic revision")
j=one(j,
'''            d.put("tungstenGuardNegativeCbCompression", TG_NEG_CB_COMPRESSION);
            d.put("tungstenGuardNegativeCrCompression", TG_NEG_CR_COMPRESSION);
''',
'''            d.put("tungstenGuardChromaPolicy", "bounded_warm_quadrant_neutralisation");
            d.put("tungstenGuardYellowCompressionRange", "0.18..0.58");
            d.put("tungstenGuardPositiveCrOrangeMax", 0.42);
            d.put("tungstenGuardNegativeCrGreenRange", "0.10..0.22");
            d.put("tungstenGuardNeutralGateChromaCodes", "38..78");
''',"diagnostic policy")
java.write_text(j)

c=cpp.read_text()
c=one(c,"#include <vector>\n","#include <vector>\n#include \"m9tg2_chroma.h\"\n","native include")
c=one(c,
"""            const double cbModern = cb < 0 ? cb * tgCbGain : static_cast<double>(cb);
            const double crModern = cr < 0 ? cr * tgCrGain : static_cast<double>(cr);
""",
"""            // M9TG2STILL1A: exact source-horizontal 4:2:2 chroma remains
            // authoritative. Apply the same bounded TG2 chroma function as live
            // preview after the pair chroma is formed; BT.601 Y is untouched.
            const M9Tg2Chroma1A tg2 = m9Tg2NeutralChroma1A(
                    static_cast<double>(cb), static_cast<double>(cr), tgCbGain);
            const double cbModern = tg2.cb;
            const double crModern = tg2.cr;
""","native TG2 kernel")
cpp.write_text(c)
hdr.parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile(repo/"patches/m9tg2neutral1a/m9tg2_chroma.h",hdr)
g=gradle.read_text()
g=one(g,"versionName '1.61-m9detail1h-tg2neutral1a'","versionName '1.61-m9detail1h-tg2still1a'","version")
gradle.write_text(g)
print("M9TG2STILL1A applied: native 4:2:2 TG2; JNI signature unchanged; preview transport untouched")
