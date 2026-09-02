#!/usr/bin/env python3
from pathlib import Path
import sys
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path('.')
p=(root/'patches/apply-m9cam-v0.7-r35-parity.py').read_text()
r=(root/'payload/app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java').read_text()
b=(root/'payload/app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java').read_text()
checks={
 '64KiB buffer': 'new java.io.BufferedOutputStream(timedRawOutputStream, 64 * 1024)' in p,
 'timing below buffer': 'OutputStream timedRawOutputStream = new M9TimingOutputStream(rawOutputStream, timing);' in p,
 'quality 95 path retained': 'Bitmap.CompressFormat.JPEG, jpgQuality, outputStream' in p,
 'PERF3E marker': 'PERF3E_JPEGBUF64K1A_TC20LUMA8A_COLOR8A' in r,
 'build 1.28': '1.28-m9modern7r38luma24fb1primary25perf3ejpegbuf64k1atc20luma8acolor8adngasync1a' in b,
}
for k,v in checks.items(): print(('OK   ' if v else 'FAIL ')+k)
if not all(checks.values()): raise SystemExit(1)
