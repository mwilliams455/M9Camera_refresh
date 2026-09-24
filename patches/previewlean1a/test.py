"""Verify M9PREVIEWLEAN1A diagnostic-only isolation and photographic freezes."""
from pathlib import Path
import json,sys

root=Path(sys.argv[1]).resolve()
controller=(root/'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java').read_text()
main=(root/'app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java').read_text()
gpu=(root/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9GpuPreview2A.java').read_text()
proof=json.loads((root/'M9PREVIEWLEAN1A_SOURCE_PROOF.json').read_text())

checks={
 'root_trace_disabled_in_modern':'!M9Config.isM9Modern() && M9Config.isCaptureTest()' in controller,
 'shutter_pixels_not_constructed':'mM9ShutterPixels = null;' in main,
 'shutter_pixels_not_registered':'M9ShutterTrace1A.registerPixels(null);' in main,
 'no_reported_curve_array_field':'reportedCurves' not in gpu,
 'curve_point_counts_retained':'reportedCurvePointCounts' in gpu,
 'reported_curve_diag_key_retained':'reportedToneCurveRgb2E","omitted_production_heap_guard' in gpu,
}
for k,v in checks.items():
    print(k,v)
    if not v: raise SystemExit('failed '+k)

frozen=[
 'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9AutoExposure2D.java',
 'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewMeter2D.java',
 'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewEvidence2E.java',
 'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewTc20Math1A.java',
 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
 'app/src/main/assets/shaders/preview/main_fs.glsl',
 'app/src/main/cpp/m9color_jni.cpp',
]
for rel in frozen:
    if proof['before'][rel]!=proof['after'][rel]:
        raise SystemExit('frozen seam changed '+rel)

receipt={
 'revision':'M9PREVIEWLEAN1A',
 'assertions':len(checks)+len(frozen),
 'checks':checks,
 'heavyRootCauseMetadataDisabledInModern':True,
 'rootCausePixelHistoryDisabledInModern':True,
 'reportedCurveArraysNotRetainedByPreviewFrame':True,
 'photographicSeamsFrozen':True,
}
out=Path(sys.argv[2]) if len(sys.argv)>2 else root/'M9PREVIEWLEAN1A_TESTS.json'
out.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
