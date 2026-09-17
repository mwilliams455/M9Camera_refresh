#!/usr/bin/env python3
from pathlib import Path
import runpy
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-sourceshading2a-fix1.py <PhotonCamera-root>')

legacy = Path(__file__).with_name('apply-m9cam-sourceshading2a.py')
if not legacy.exists():
    raise SystemExit('SOURCESHADING2A FIX1 missing base patch')
runpy.run_path(str(legacy), run_name='__main__')

root = Path(sys.argv[1]).resolve()
p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
s = p.read_text()

def one(old, new, label):
    global s
    n = s.count(old)
    if n != 1:
        raise SystemExit(f'SOURCESHADING2A FIX1 {label}: expected 1, found {n}')
    s = s.replace(old, new, 1)

one('''                sourceShading2ABank.put("controlOriginalTc20Gain", controlOriginalTc20);
                sourceShading2ABank.put("controlBoundedEffectiveRenderGain", controlBoundedGain);''',
'''                sourceShading2ABank.put("controlOriginalTc20Gain", Double.isFinite(controlOriginalTc20)
                        ? controlOriginalTc20 : JSONObject.NULL);
                sourceShading2ABank.put("controlBoundedEffectiveRenderGain", Double.isFinite(controlBoundedGain)
                        ? controlBoundedGain : JSONObject.NULL);''',
'control finite JSON')

one('''                        sourceShading2ABank.put("variantComputedTc20GainBeforeLock",
                                shaded.diagnostics.optDouble("sourceShading2AComputedTc20GainBeforeLock", Double.NaN));''',
'''                        double variantComputedTc20 = shaded.diagnostics.optDouble(
                                "sourceShading2AComputedTc20GainBeforeLock", Double.NaN);
                        sourceShading2ABank.put("variantComputedTc20GainBeforeLock",
                                Double.isFinite(variantComputedTc20) ? variantComputedTc20 : JSONObject.NULL);''',
'variant TC20 finite JSON')

one('''                            sourceShading2ABank.put("variantBoundedEffectiveRenderGain", shadedBounded);
                            if (Double.isFinite(controlBoundedGain) && Double.isFinite(shadedBounded)) {''',
'''                            sourceShading2ABank.put("variantBoundedEffectiveRenderGain",
                                    Double.isFinite(shadedBounded) ? shadedBounded : JSONObject.NULL);
                            if (Double.isFinite(controlBoundedGain) && Double.isFinite(shadedBounded)) {''',
'variant bounded finite JSON')

one('''                        sourceShading2ABank.put("variantRgb8ClipFraction",
                                shaded.diagnostics.optDouble("rgb8ClipFraction", Double.NaN));
                        sourceShading2ABank.put("variantRenderNearWhiteFraction",
                                shaded.diagnostics.optDouble("renderNearWhiteFraction", Double.NaN));''',
'''                        double variantRgbClip = shaded.diagnostics.optDouble("rgb8ClipFraction", Double.NaN);
                        double variantNearWhite = shaded.diagnostics.optDouble("renderNearWhiteFraction", Double.NaN);
                        sourceShading2ABank.put("variantRgb8ClipFraction",
                                Double.isFinite(variantRgbClip) ? variantRgbClip : JSONObject.NULL);
                        sourceShading2ABank.put("variantRenderNearWhiteFraction",
                                Double.isFinite(variantNearWhite) ? variantNearWhite : JSONObject.NULL);''',
'variant output finite JSON')

p.write_text(s)
print('SOURCESHADING2A FIX1 applied')
print(' - non-finite diagnostic values serialize as JSON null')
