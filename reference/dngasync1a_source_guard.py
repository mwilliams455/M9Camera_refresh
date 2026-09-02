#!/usr/bin/env python3
from pathlib import Path
import hashlib
root=Path(__file__).resolve().parents[1]
q=(root/'payload/app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java').read_text()
t=(root/'payload/app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java').read_text()
b=(root/'payload/app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java').read_text()
r=(root/'payload/app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java').read_text()
p=(root/'patches/apply-m9cam-v0.7-r35-parity.py').read_text()
v=(root/'patches/verify-m9cam-v0.7-r35.py').read_text()
version='1.23-m9modern7r38luma24fb1primary24tc20native1borient1anormnative1ametafreeze1acolornative2afix1name1aqueue1btimingfreeze1adngasync1a'
checks={
 'render queue remains one worker + two pending': 'MAX_PENDING = 2' in q and 'MAX_IN_FLIGHT = 1 + MAX_PENDING' in q,
 'queue1b admission retained': all(x in q for x in ['preflightCaptureAdmission','ADMISSION_REJECT_COUNT','primary_queue_full_nonblocking_reject']),
 'no blocking render queue put': 'getQueue().put(job)' not in q,
 'dng worker single bounded + one pending': all(x in q for x in ['DNG_MAX_PENDING = 1','M9PrimaryDngIO','new ArrayBlockingQueue<>(DNG_MAX_PENDING)']),
 'dng handoff is nonblocking execute': 'DNG_EXECUTOR.execute' in q and 'frameTransferredToDngWorker = true' in q,
 'dng saturation has sync preservation fallback': all(x in q for x in ['RejectedExecutionException dngFull','DNG_HANDOFF_FALLBACK_COUNT.incrementAndGet','runDngAndFinalize(dngJob, false, true']),
 'development dng save centralized': q.count('ImageSaver.Util.saveSingleRaw') == 1 and q.find('ImageSaver.Util.saveSingleRaw') > q.find('private static void runDngAndFinalize'),
 'no second raw copy introduced': 'detachForBackground' not in q and 'copy' not in q.lower().split('rawhandoffcopy')[0] if 'rawhandoffcopy' in q.lower() else 'detachForBackground' not in q,
 'renderer capacity releases after handoff': 'RAW owned by M9PrimaryDngIO; next render may start now' in q and 'IN_FLIGHT_COUNT.decrementAndGet()' in q,
 'async dng owns raw close': 'job.ownedFrame.close()' in q and 'if (dngAsyncAccepted)' in q,
 'timing freeze before async raw close': q.find('M9PrimaryTimingWriter.freezeAndWriteAsync', q.find('private static void runDngAndFinalize')) < q.find('job.ownedFrame.close()', q.find('private static void runDngAndFinalize')),
 'capture metadata stays after dng': q.find('ImageSaver.Util.saveSingleRaw') < q.find('M9DeferredMetadataStore.persistAsyncForDng', q.find('private static void runDngAndFinalize')),
 'timing schema v5 dngasync1a': 'm9cam.primarytiming.v5.dngasync1a' in t,
 'timing freeze immutable bytes retained': all(x in t for x in ['class FrozenTiming','final byte[] bytes','TIMING_WRITER.execute','persistFrozen']),
 'timing storage remains SAF helper': 'SimpleStorageHelper.openOutputStreamByAbsPath(frozen.timingPath.toString())' in t,
 'dng telemetry present': all(x in t for x in ['dngPersistMode','dngAsyncAccepted','dngAsyncFallbackSync','dngQueueDepthAtHandoff','dngQueueWaitElapsedMs','dngWorkerElapsedMs','rawFrameCloseOwner']),
 'build marker updated': version in b,
 'patch emits dngasync build': version in p and 'v0.7ZH DNGASYNC1A' in p,
 'verifier knows dngasync': all(x in v for x in ['DNGASYNC1A bounded single DNG worker','m9cam.primarytiming.v5.dngasync1a','v0.7ZH DNGASYNC1A build identity']),
 'capture metadata dng policy fixed': 'bounded_async_single_worker_after_jpeg_with_sync_fallback' in r and 'primary_worker_after_jpeg' not in r,
}
failed=[]
for name,ok in checks.items():
    print(('PASS ' if ok else 'FAIL ')+name)
    if not ok: failed.append(name)
# Frozen photographic/native hashes must match promoted v0.7ZG base.
base=Path('/mnt/data/dngasync_base/payload/app')
# M9R35Renderer is frozen except for the one intentional metadata literal below.
renderer_rel='src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
base_renderer=(base/renderer_rel).read_text()
normalized_renderer=r.replace('bounded_async_single_worker_after_jpeg_with_sync_fallback', 'primary_worker_after_jpeg')
ok=normalized_renderer == base_renderer
name='renderer unchanged except DNG metadata literal'
print(('PASS ' if ok else 'FAIL ')+name)
if not ok: failed.append(name)
for rel in [
 'src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java',
 'src/main/cpp/m9color_jni.cpp',
 'src/main/assets/m9/m9_r35_calibration.bin',
 'src/main/assets/m9/m9_r35_calibration_manifest.json',
 'src/main/java/com/particlesdevs/photoncamera/m9/M9SubjectMotionAnalyzer.java',
 'src/main/java/com/particlesdevs/photoncamera/m9/M9DeferredMetadataStore.java',
 'src/main/java/com/particlesdevs/photoncamera/m9/M9CapturePathAllocator.java',
]:
    a=(base/rel).read_bytes(); z=(root/'payload/app'/rel).read_bytes()
    ok=hashlib.sha256(a).digest()==hashlib.sha256(z).digest()
    name='frozen payload unchanged '+Path(rel).name
    print(('PASS ' if ok else 'FAIL ')+name)
    if not ok: failed.append(name)
if failed:
    print('FAILED:', ', '.join(failed))
    raise SystemExit(1)
