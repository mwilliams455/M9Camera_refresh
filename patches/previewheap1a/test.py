"""Static/integration contract tests for M9PREVIEWHEAP1A."""
from pathlib import Path
import json,sys

HERE=Path(__file__).resolve().parent
root=Path(sys.argv[1]).resolve()
trace=(root/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9RootCauseTrace1A.java').read_text()
gradle=(root/'app/build.gradle').read_text()

checks={
 'memory_marker':'M9PREVIEWHEAP1A' in trace,
 'parent_revision_preserved':'public static final String REVISION="M9ROOTCAUSE1A";' in trace,
 'no_copyColorCurve':'copyColorCurve' not in trace,
 'no_float_curve_payload':'new float[' not in trace,
 'no_toneCurvesRgb':'toneCurvesRgb' not in trace,
 'point_counts_retained':'toneCurvePointCountsRgb' in trace,
 'payload_omission_explicit':'omitted_live_heap_guard' in trace,
 'context_period_500ms':'CONTEXT_PERIOD_NS=500000000L' in trace,
 'context_string_shared':'lastCompactContext' in trace and 'new Row(now,timestamp,result.getFrameNumber(),v,lastCompactContext)' in trace,
 'oom_fail_safe':'catch(OutOfMemoryError e)' in trace and 'rows.clear();' in trace,
 'per_frame_values_retained':'double[] v={0,0,0,' in trace,
 'capacity_retained':'CAPACITY=1800' in trace,
 'window_retained':'WINDOW_NS=30000000000L' in trace,
 'snapshot_api_retained':'public static JSONObject snapshot(long shutterNs,String cameraId)' in trace,
 'range_api_retained':'public static JSONObject range(long startNs,long endNs,String cameraId)' in trace,
 'version_name':"versionName '1.74-m9previewheap1a-tg1'" in gradle,
 'version_code':'versionCode 26694' in gradle,
}
bad=[k for k,v in checks.items() if not v]
for k,v in checks.items(): print(k,v)
if bad: raise SystemExit('failed: '+','.join(bad))

# Bound argument: the retained Row no longer contains any copied tone-curve arrays.
# Values[] is fixed scalar metadata and the compact context is sampled at 2 Hz.
receipt={
 'revision':'M9PREVIEWHEAP1A',
 'assertions':len(checks),
 'checks':checks,
 'retainedFullToneCurveArraysPerRow':0,
 'compactContextHz':2,
 'photographicChange':False,
}
(Path(sys.argv[2]) if len(sys.argv)>2 else root/'PREVIEWHEAP1A_TESTS.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
