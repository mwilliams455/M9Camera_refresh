#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
r = (ROOT/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java').read_text()
c = (ROOT/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java').read_text()
n = (ROOT/'app/src/main/cpp/m9color_jni.cpp').read_text()
g = (ROOT/'app/build.gradle').read_text()
checks = {
    'renderer MHC call': 'M9NativeColorCore.demosaicMhcRggb(' in r,
    'renderer direct Mat': 'CvType.CV_16UC3, mhcRgbBuffer' in r,
    'renderer EA production removed': 'Imgproc.cvtColor(rawMat, cam16, Imgproc.COLOR_BayerRG2BGR_EA);' not in r,
    'diagnostic identity': 'DEMOSAICMHC1A_MalvarHeCutler5x5_RGGB_native_direct' in r,
    'JNI declaration': 'static native long demosaicMhcRggb(' in c,
    'native kernel': 'mhcPixelRggb(' in n,
    'native JNI': 'M9NativeColorCore_demosaicMhcRggb' in n,
    'RGGB red site': 'if (evenY && evenX)' in n,
    'version suffix': 'demosaicmhc1a' in g.lower(),
    'SAT3 frozen constants': '16754, -7632, -922' in n and '18160, -9034, -922' in n,
    'curve02 still native': 'ctx.curve' in n,
}
failed = [k for k,v in checks.items() if not v]
for k,v in checks.items(): print(('OK  ' if v else 'FAIL') + k)
if failed: raise SystemExit('DEMOSAICMHC1A verifier failed: ' + ', '.join(failed))
print('DEMOSAICMHC1A verifier passed')
