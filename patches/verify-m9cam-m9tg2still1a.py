#!/usr/bin/env python3
from pathlib import Path
import hashlib,sys
if len(sys.argv)!=2: raise SystemExit("usage: verify-m9cam-m9tg2still1a.py <PhotonCamera-root>")
root=Path(sys.argv[1]).resolve()
java=root/"app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java"
cpp=root/"app/src/main/cpp/m9color_jni.cpp"
hdr=root/"app/src/main/cpp/m9tg2_chroma.h"
gradle=root/"app/build.gradle"
shader=root/"app/src/main/assets/shaders/preview/main_fs.glsl"
for p in [java,cpp,hdr,gradle,shader]:
    if not p.exists(): raise SystemExit("TG2STILL1A missing "+str(p))
j=java.read_text();c=cpp.read_text();h=hdr.read_text();g=gradle.read_text();s=shader.read_text()
checks={
 "java weight transport":"final double tgCbGain = tgWeight;" in j and "final double tgCrGain = tgWeight;" in j,
 "still revision":"TG2NEUTRAL1A_STILL" in j,
 "native header include":'#include "m9tg2_chroma.h"' in c,
 "native helper call":"m9Tg2NeutralChroma1A(" in c,
 "old native one-sided math removed":"cb < 0 ? cb * tgCbGain" not in c and "cr < 0 ? cr * tgCrGain" not in c,
 "header orange correction":"orangeGate" in h and "0.42" in h,
 "header neutral gate":"38.0, 78.0" in h,
 "preview TG2 retained":"M9TG2NEUTRAL1A" in s,
 "version":"1.61-m9detail1h-tg2still1a" in g,
}
for name,ok in checks.items():
    print(name,ok)
    if not ok: raise SystemExit("TG2STILL1A verify failed: "+name)
print("M9TG2STILL1A_VERIFY_PASS")
