#!/usr/bin/env python3
from pathlib import Path
import hashlib, sys
root=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
cpp=(root/'payload/app/src/main/cpp/m9color_jni.cpp').read_text()
renderer=(root/'payload/app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java').read_text()
native_java=(root/'payload/app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java').read_text()
apply=(root/'patches/apply-m9cam-v0.7-r35-parity.py').read_text()

def extract(src,name):
    idx=src.find(name+'(')
    if idx<0: raise SystemExit(f'missing function {name}')
    start=src.rfind('\n',0,idx)+1
    brace=src.find('{',idx); depth=0
    for i in range(brace,len(src)):
        if src[i]=='{': depth+=1
        elif src[i]=='}':
            depth-=1
            if depth==0: return src[start:i+1]
    raise SystemExit(f'unclosed {name}')

expected={
'applyHsm':'7f4e1e8224d976b65be68ae21fe5fcd3d5ef43d461507ea33f87c2007fffbe5a',
'cameraToSrgbLuma':'d2247d137a35f6ef0729df2977c494f30d54da438ed0b98197a529bdb7bbe382',
'cameraToM9':'a3d216769a59128825c44b5b69f7f9d9219dddb76c43e00bb462293afedf2bc9',
'm9CurvePixel':'0c88877b5d50cf409bae84fe95e6e172184f2e7f0c39352b763fd5dafa7a9d5f',
'renderStripScalar':'c157a252e4d29657ff000f3241c21a3c9cb89dfa57769b0579e6f22ac928faa0',
'orientCompletedStrip':'534221e756b6d5af9e54312dfad441e25120d2941e288473d7b5aeda28faa51d',
}
for name,want in expected.items():
    got=hashlib.sha256(extract(cpp,name).encode()).hexdigest()
    if got!=want: raise SystemExit(f'{name} changed: {got} != {want}')
    print(f'OK frozen {name} {got}')

for token in [
    '#include <android/bitmap.h>',
    'Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_renderBlockParallelDirectBitmap',
    'AndroidBitmap_getInfo', 'AndroidBitmap_lockPixels', 'AndroidBitmap_unlockPixels',
    'ANDROID_BITMAP_FORMAT_RGBA_8888', 'storeArgbAsRgba8888', 'writeCompletedSubrangeToBitmap',
]:
    if token not in cpp: raise SystemExit(f'missing PERF3I native seam: {token}')
for token in ['renderBlockParallelDirectBitmap', 'android.graphics.Bitmap bitmap']:
    if token not in native_java: raise SystemExit(f'missing PERF3I Java native seam: {token}')
for token in [
    'PERF3I_BITMAPDIRECT1A_CVDIRECT1A_ORIENTFUSE8A_EXIFASYNC1A_JPEGBUF64K1A_TC20LUMA8A_COLOR8A',
    'nativeColorBitmapDirectEligible', 'nativeColorBitmapDirectActive',
    'nativeColorBitmapDirectBlocks', 'nativeColorBitmapFallbackBlocks',
    'androidbitmap_rgba8888_direct1a', 'Bitmap.Config.ARGB_8888', 'oriented.isMutable()',
    'oriented.getRowBytes()', 'oriented.setPixels(argbBlock', 'JPEG_QUALITY = 95',
]:
    if token not in renderer: raise SystemExit(f'missing PERF3I renderer seam: {token}')
# PERF3H preservation fallback must remain byte-for-byte available.
for token in ['renderBlockParallelDirect(', 'cam16.get(y0, 0, camBlock)', 'M9NativeColorCore.renderBlockParallel(', 'opencv_mat_dataaddr_direct1a']:
    if token not in renderer: raise SystemExit(f'missing PERF3H preservation fallback: {token}')
for token in ['find_library(M9_JNIGRAPHICS_LIB jnigraphics)', 'target_link_libraries(m9color PRIVATE ${M9_JNIGRAPHICS_LIB})']:
    if token not in apply: raise SystemExit(f'missing jnigraphics build seam: {token}')
if 'new int[orientedWidth * orientedHeight]' in renderer or 'new int[Math.multiplyExact(orientedWidth, orientedHeight)]' in renderer:
    raise SystemExit('unexpected full-frame int staging buffer')
print('PERF3I BITMAPDIRECT1A source guard PASS')
