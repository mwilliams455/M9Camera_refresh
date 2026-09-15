#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-cfaabstract1b-ultrawide1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
r = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java').read_text()
j = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java').read_text()
c = (root / 'app/src/main/cpp/m9color_jni.cpp').read_text()
resolver = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9CfaResolver.java').read_text()

checks = {
    'conventional_bayer_gate': 'M9CfaResolver.isSupported(sourceCfaPattern)' in r,
    'old_rggb_only_gate_removed': 'expects RGGB CFA=0' not in r,
    'legacy_rggb_dispatch_preserved': 'M9NativeColorCore.demosaicMhcRggb(' in r,
    'generic_bayer_dispatch_present': 'M9NativeColorCore.demosaicMhcBayer(' in r,
    'generic_jni_java_present': 'static native long demosaicMhcBayer(' in j,
    'generic_jni_cpp_present': 'M9NativeColorCore_demosaicMhcBayer(' in c,
    'legacy_jni_cpp_present': 'M9NativeColorCore_demosaicMhcRggb(' in c,
    'rggb_phase': 'RGGB=(0,0)' in c,
    'grbg_phase': 'GRBG=(1,0)' in c,
    'gbrg_phase': 'GBRG=(0,1)' in c,
    'bggr_phase': 'BGGR=(1,1)' in c,
    'semantic_gainmap_route': 'lensShadingChannelAt(x, y, cfaPattern, originX, originY)' in r,
    'origin0_explicit': 'final int sourceRawOriginX = 0;' in r and 'final int sourceRawOriginY = 0;' in r,
    'origin_not_claimed_proven': 'DEVICEPORT1A deliberately did not infer RAW origin' in r,
    'resolver_semantic_channels': 'G-even-sensor-row' in resolver and 'return Math.floorMod(localY + originY, 2) == 0 ? 1 : 2;' in resolver,
    'sharp_source_generic': 'm9SharpSourceLeicaGreen14BayerPhase' in c,
    'neutral_mhc_generic': 'mhcPixelNeutralRbCompleteBayerPhase' in c,
    'plain_mhc_generic': 'mhcPixelBayerPhase' in c,
    'legacy_gainmap_function_still_present': 'private static NativeProspectiveShadingStats applyNativeProspectiveGainMap(\n' in r,
    'legacy_lumadecomp_function_still_present': 'private static NativeProspectiveShadingStats applyNativeProspectiveGainMapLumaDecomp1A(\n' in r,
    'open_cv_control_fail_closed_non_rggb': 'OpenCV diagnostic control remains RGGB/origin0 only' in r,
}
failed = [k for k,v in checks.items() if not v]
for k,v in checks.items():
    print(('PASS ' if v else 'FAIL ') + k)
if failed:
    raise SystemExit('CFAABSTRACT1B verifier failures: ' + ', '.join(failed))
print('CFAABSTRACT1B/ULTRAWIDE1A VERIFY PASS')
