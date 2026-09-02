#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
queue = (root / 'payload/app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java').read_text()
timing = (root / 'payload/app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java').read_text()
patch = (root / 'patches/apply-m9cam-v0.7-r35-parity.py').read_text()
backlight = (root / 'payload/app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java').read_text()

checks = {
    'bounded queue retained': 'MAX_PENDING = 2' in queue and 'ArrayBlockingQueue' in queue,
    'blocking put removed': 'getQueue().put(job)' not in queue,
    'boolean enqueue contract': 'public static boolean enqueue' in queue and 'return true;' in queue and 'return false;' in queue,
    'queue-full counter': 'QUEUE_FULL_COUNT' in queue and 'AtomicLong' in queue,
    'nonblocking rejection marker': 'primary_queue_full_nonblocking_reject' in queue,
    'rejection metadata persistence': 'persistAsyncForDng(dngPath)' in queue,
    'async rejection timing': 'writeRejectedAsync' in queue and 'Executors.newSingleThreadExecutor' in timing,
    'timing schema bumped': 'm9cam.primarytiming.v2.queue1a' in timing,
    'queue telemetry': all(k in timing for k in [
        'queueDepthAtEnqueue', 'activeRenderCountAtEnqueue', 'queueCapacity',
        'queueFullCountAtEnqueue', 'enqueueWaitElapsedMs', 'queueAccepted', 'queueOutcome']),
    'DefaultSaver consumes enqueue result': 'queued = M9PrimaryRenderQueue.enqueue' in patch,
    'QUEUE1A version': '1.20-m9modern7r38luma24fb1primary24tc20native1borient1anormnative1ametafreeze1acolornative2afix1queue1a' in backlight,
    'renderer schema frozen': 'm9cam.renderer.r38.h25tg1.full12.android.v19.primary2p4tc20native1borient1anormnative1acolornative2afix1' in backlight,
}

bad = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(('PASS ' if ok else 'FAIL ') + name)
if bad:
    raise SystemExit(1)
print('QUEUE1A nonblocking source guard PASSED')
