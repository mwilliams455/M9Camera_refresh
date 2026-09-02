#!/usr/bin/env python3
from pathlib import Path
import sys
root = Path(__file__).resolve().parents[1]
q = (root/'payload/app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java').read_text()
t = (root/'payload/app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java').read_text()
a = (root/'payload/app/src/main/java/com/particlesdevs/photoncamera/m9/M9CapturePathAllocator.java').read_text()
p = (root/'patches/apply-m9cam-v0.7-r35-parity.py').read_text()
v = (root/'patches/verify-m9cam-v0.7-r35.py').read_text()
checks = {
    'queue max pending retained': 'MAX_PENDING = 2' in q,
    'explicit inflight accounting': all(x in q for x in ['MAX_IN_FLIGHT = 1 + MAX_PENDING','IN_FLIGHT_COUNT','preflightCaptureAdmission']),
    'admission rejection counter': 'ADMISSION_REJECT_COUNT' in q,
    'no blocking put': 'getQueue().put(job)' not in q,
    'fallback rejection retained': 'primary_queue_full_nonblocking_reject' in q and 'RejectedExecutionException' in q,
    'timing v3 queue1b': 'm9cam.primarytiming.v3.queue1b' in t,
    'timing name policy': 'captureStemPolicy' in t and 'shutterAdmissionPolicy' in t,
    'allocator no fs probe': 'Files.exists' not in a and 'SimpleStorageHelper' not in a,
    'allocator clock+sequence': 'System.currentTimeMillis()' in a and 'sameTokenSequence' in a,
    'patch unique path seam': 'M9CapturePathAllocator.allocate(ImagePath.newDNGFilePath())' in p,
    'patch m9 ui guard': 'M9Config.isCaptureTest() && !M9PrimaryRenderQueue.preflightCaptureAdmission()' in p,
    'patch gate before takePicture': (lambda i: i >= 0 and p.find('M9PrimaryRenderQueue.preflightCaptureAdmission()', i) < p.find('cameraFragment.captureController.takePicture()', i))(p.find('queue1b_timer =')),
    'build version': '1.21-m9modern7r38luma24fb1primary24tc20native1borient1anormnative1ametafreeze1acolornative2afix1name1aqueue1b' in p,
    'verifier knows new seams': all(x in v for x in ['NAME1A allocator present','QUEUE1B gates before takePicture','m9cam.primarytiming.v3.queue1b']),
}
failed=[k for k,val in checks.items() if not val]
for k,val in checks.items():
    print(('PASS ' if val else 'FAIL ')+k)
if failed:
    raise SystemExit(1)
