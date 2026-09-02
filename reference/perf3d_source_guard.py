#!/usr/bin/env python3
from pathlib import Path
import hashlib, sys
root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
cpp = (root/'payload/app/src/main/cpp/m9color_jni.cpp').read_text()
renderer = (root/'payload/app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java').read_text()

def extract(src, name):
    idx = src.find(name + '(')
    if idx < 0: raise SystemExit(f'missing function {name}')
    start = src.rfind('\n', 0, idx) + 1
    brace = src.find('{', idx)
    depth = 0
    for i in range(brace, len(src)):
        if src[i] == '{': depth += 1
        elif src[i] == '}':
            depth -= 1
            if depth == 0: return src[start:i+1]
    raise SystemExit(f'unclosed function {name}')

expected = {
    'applyHsm':'7f4e1e8224d976b65be68ae21fe5fcd3d5ef43d461507ea33f87c2007fffbe5a',
    'cameraToSrgbLuma':'d2247d137a35f6ef0729df2977c494f30d54da438ed0b98197a529bdb7bbe382',
    'cameraToM9':'a3d216769a59128825c44b5b69f7f9d9219dddb76c43e00bb462293afedf2bc9',
    'm9CurvePixel':'0c88877b5d50cf409bae84fe95e6e172184f2e7f0c39352b763fd5dafa7a9d5f',
    'renderStripScalar':'c157a252e4d29657ff000f3241c21a3c9cb89dfa57769b0579e6f22ac928faa0',
    'orientCompletedStrip':'534221e756b6d5af9e54312dfad441e25120d2941e288473d7b5aeda28faa51d',
}
for name, want in expected.items():
    got = hashlib.sha256(extract(cpp, name).encode()).hexdigest()
    if got != want: raise SystemExit(f'{name} changed: {got} != {want}')
    print(f'OK {name} frozen {got}')

required = [
    'NATIVE_COLOR_BLOCK_ROWS = 384',
    'Math.min(8, Runtime.getRuntime().availableProcessors())',
    'JPEG_QUALITY = 95', 'SATURATION_BANK = 3',
    'TG_NEG_CB_COMPRESSION = 0.25', 'TG_NEG_CR_COMPRESSION = 0.16',
    'HSM_H = 0.25', 'HSM_S = 0.85', 'HSM_V = 1.00',
    'm9cam.renderer.r38.h25tg1.full12.android.v19.primary2p4tc20native1borient1anormnative1acolornative2afix1',
    'PERF3E_JPEGBUF64K1A_TC20LUMA8A_COLOR8A',
    'tc20NativeLumaComputeElapsedMs', 'tc20NativeOrderBuildElapsedMs',
    'jpegCompressElapsedMs', 'jpegStreamWriteElapsedMs', 'jpegExifSaveElapsedMs',
]
for token in required:
    if token not in renderer: raise SystemExit(f'missing renderer invariant {token}')
    print(f'OK renderer invariant {token}')
for token in ['lumaWorkerCount', 'orderBuildStarted', 'workerWallStarted', 'totalWeightStarted', 'medianStarted', 'p98Started']:
    if token not in cpp: raise SystemExit(f'missing retained native probe {token}')
    print(f'OK retained native probe {token}')
print('PERF3E JPEGBUF64K1A source guard PASS')
