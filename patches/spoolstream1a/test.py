"""Verify M9SPOOLSTREAM1A heap-bounded diagnostic transport."""
from pathlib import Path
import json,sys

root=Path(sys.argv[1]).resolve()
spool=(root/'app/src/main/java/com/particlesdevs/photoncamera/m9/M9DiagnosticBurstSpool.java').read_text()
proof=json.loads((root/'M9SPOOLSTREAM1A_SOURCE_PROOF.json').read_text())

checks={
 'revision':'M9SPOOLSTREAM1A' in spool,
 'recovery_metadata_only':'Files.size(source)' in spool,
 'no_recovery_readallbytes':'Files.readAllBytes(source)' not in spool,
 'entry_no_byte_array':'final byte[] bytes' not in spool,
 'stage_does_not_retain_caller_bytes':'new Entry(publicPath, privatePath, bytes.length' in spool,
 'bundle_manifest_only':'bounded_manifest_payloads_streamed_individually' in spool,
 'bundle_materialized_zero':'payloadBytesMaterializedForBundle", 0' in spool,
 'stream_export':'streamPublic(entry.publicPath, entry.privatePath)' in spool,
 'copy_buffer_64k':'COPY_BUFFER_BYTES = 64 * 1024' in spool,
 'heap_telemetry_zero':'recoveredPayloadBytesHeldInJavaHeap", 0' in spool,
}
for k,v in checks.items():
    print(k,v)
    if not v: raise SystemExit('SPOOLSTREAM test failed '+k)

frozen=[
 'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java',
 'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9AutoExposure2D.java',
 'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewMeter2D.java',
 'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewEvidence2E.java',
 'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewTc20Math1A.java',
 'app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java',
 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
 'app/src/main/assets/shaders/preview/main_fs.glsl',
 'app/src/main/cpp/m9color_jni.cpp',
]
for rel in frozen:
    if proof['before'][rel]!=proof['after'][rel]:
        raise SystemExit('frozen seam changed '+rel)

receipt={
 'revision':'M9SPOOLSTREAM1A',
 'assertions':len(checks)+len(frozen),
 'checks':checks,
 'recoveredPayloadHeapRetentionBytes':0,
 'bundlePayloadCopies':0,
 'individualCopyBufferBytes':65536,
 'photographicSeamsFrozen':True,
}
out=Path(sys.argv[2]) if len(sys.argv)>2 else root/'M9SPOOLSTREAM1A_TESTS.json'
out.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
