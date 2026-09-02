#!/usr/bin/env python3
from pathlib import Path
import sys
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path('.')
p=(root/'patches/apply-m9cam-v0.7-r35-parity.py').read_text()
r=(root/'payload/app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java').read_text()
q=(root/'payload/app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java').read_text()
f=(root/'payload/app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9JpegFinalizeQueue.java').read_text()
t=(root/'payload/app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java').read_text()
b=(root/'payload/app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java').read_text()
checks={
 'M9 payload helper added': 'saveBitmapAsJPGPayloadM9' in p and 'saveBitmapAsJPGPayloadM9' in r,
 'quality path retained': 'img.compress(Bitmap.CompressFormat.JPEG, jpgQuality, outputStream)' in p,
 '64KiB buffer retained': 'new java.io.BufferedOutputStream(timedRawOutputStream, 64 * 1024)' in p,
 'same EXIF operations': 'ParseExif.setAllAttributes(jpegPath.toFile(), exifData)' in f and 'inter.saveAttributes()' in f,
 'publish after EXIF': f.find('inter.saveAttributes()') >= 0 and f.find('notifyImageSavedStatus(true, jpegPath)') > f.find('inter.saveAttributes()'),
 'bounded one-worker finalizer': 'new ArrayBlockingQueue<>(MAX_PENDING)' in f and 'MAX_PENDING = 2' in f and '1, 1, 0L' in f,
 'sync fallback retained': 'RejectedExecutionException' in f and 'runFinalize(ticket, jpegPath, exifData, processingEventsListener, false)' in f,
 'render queue no direct JPEG publish': 'processingEventsListener.notifyImageSavedStatus(true, jpegPath)' not in q,
 'final timing waits for EXIF': 'jpegFinalizeTicket.awaitCompletion()' in q and 'jpegFinalizeTicket.isSuccess()' in q,
 'DNG publication waits for JPEG finalizer': q.find('jpegFinalizeTicket.awaitCompletion()') >= 0 and q.find('job.processingEventsListener.notifyImageSavedStatus(true, job.dngPath)') > q.find('jpegFinalizeTicket.awaitCompletion()'),
 'finalizer diagnostics merged': 'jpegFinalizeTicket.appendDiagnostics(rendererDiagnostics)' in q,
 'timing schema v6': 'm9cam.primarytiming.v6.exifasync1a.dngasync1a' in t,
 'PERF3F marker': 'PERF3F_EXIFASYNC1A_JPEGBUF64K1A_TC20LUMA8A_COLOR8A' in r,
 'build 1.29': '1.29-m9modern7r38luma24fb1primary25perf3fexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1a' in b,
}
for k,v in checks.items(): print(('OK   ' if v else 'FAIL ')+k)
if not all(checks.values()): raise SystemExit(1)
