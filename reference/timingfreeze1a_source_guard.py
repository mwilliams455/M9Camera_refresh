#!/usr/bin/env python3
from pathlib import Path
root = Path(__file__).resolve().parents[1]
q = (root/'payload/app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java').read_text()
t = (root/'payload/app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java').read_text()
b = (root/'payload/app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java').read_text()
p = (root/'patches/apply-m9cam-v0.7-r35-parity.py').read_text()
v = (root/'patches/verify-m9cam-v0.7-r35.py').read_text()
version='1.22-m9modern7r38luma24fb1primary24tc20native1borient1anormnative1ametafreeze1acolornative2afix1name1aqueue1btimingfreeze1a'
checks = {
    'queue max pending retained': 'MAX_PENDING = 2' in q,
    'queue1b admission retained': all(x in q for x in ['preflightCaptureAdmission','MAX_IN_FLIGHT = 1 + MAX_PENDING','ADMISSION_REJECT_COUNT']),
    'no blocking queue put': 'getQueue().put(job)' not in q,
    'fallback rejection retained': 'primary_queue_full_nonblocking_reject' in q and 'RejectedExecutionException' in q,
    'accepted timing uses freeze async': 'M9PrimaryTimingWriter.freezeAndWriteAsync' in q,
    'timing freeze occurs before frame close': q.find('M9PrimaryTimingWriter.freezeAndWriteAsync') >= 0 and q.find('M9PrimaryTimingWriter.freezeAndWriteAsync') < q.find('ownedFrame.close()'),
    'inflight decrement remains after frame close': q.find('ownedFrame.close()') >= 0 and q.find('ownedFrame.close()') < q.find('IN_FLIGHT_COUNT.decrementAndGet()', q.find('ownedFrame.close()')),
    'no synchronous accepted timing write': 'M9PrimaryTimingWriter.write(' not in q,
    'timing schema v4': 'm9cam.primarytiming.v4.timingfreeze1a' in t,
    'immutable frozen timing payload': all(x in t for x in ['class FrozenTiming','final byte[] bytes','new JSONObject(rendererDiagnostics.toString())']),
    'timing I/O executor isolated': all(x in t for x in ['M9PrimaryTimingIO','TIMING_WRITER.execute','persistFrozen']),
    'SAF open occurs only in persistence method': t.find('openOutputStreamByAbsPath') > t.find('private static void persistFrozen'),
    'timing telemetry declares off-worker I/O': all(x in t for x in ['primaryTimingMode','primaryTimingFrozenBeforeFrameRelease','primaryTimingIoOffRenderWorker','primaryTimingFreezeElapsedMs','workerElapsedBoundary']),
    'build marker updated': version in b,
    'patch accepts baseline and emits timingfreeze build': '1.21-m9modern7r38luma24fb1primary24tc20native1borient1anormnative1ametafreeze1acolornative2afix1name1aqueue1b' in p and version in p,
    'patch self-check knows timingfreeze': all(x in p for x in ['m9cam.primarytiming.v4.timingfreeze1a','freezeAndWriteAsync','frozen_bytes_deferred_persist_after_worker']),
    'verifier knows timingfreeze': all(x in v for x in ['TIMINGFREEZE1A accepted timing freeze is asynchronous I/O','TIMINGFREEZE1A render queue freezes before RAW release','m9cam.primarytiming.v4.timingfreeze1a']),
}
failed=[]
for name, ok in checks.items():
    print(('PASS ' if ok else 'FAIL ')+name)
    if not ok: failed.append(name)
if failed:
    raise SystemExit(1)
