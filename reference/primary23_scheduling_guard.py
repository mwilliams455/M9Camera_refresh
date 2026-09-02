#!/usr/bin/env python3
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'payload/app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
s=p.read_text()
extract=s.index('cam16.get(y0, 0, worker.camStrip)')
submit=s.index('colorExecutor.submit', extract)
join=s.index('future.get()', submit)
commit=s.index('unrotated.setPixels(strip.argb', join)
assert 'PARALLEL_RENDER_WORKERS = Math.max(2, Math.min(4, Runtime.getRuntime().availableProcessors()))' in s
assert 'RENDER_STRIP_ROWS = 24' in s
assert extract < submit < join < commit
assert 'M9NativeColorCore.renderStrip' in s
assert 'newFixedThreadPool(parallelWorkers' in s
assert 'bounded_strip_native_scalar_math' in s
print('PRIMARY2.3 JNI1 scheduling/serialization guard PASS')
