#!/usr/bin/env python3
"""Read-only RAW boundary logger on the exact delivered CAPTURECOLOR1A inventory."""
from pathlib import Path
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
ID = 'M9PHOTONBOUNDARY2Q_READONLY'
VERSION = '2.08-m9photonboundary2q-capturecolor1a'
CODE = 26728
JAVA = 'app/src/main/java/com/particlesdevs/photoncamera/'
HELPER = JAVA + 'm9/render/M9PhotonBoundary2Q.java'
FQ = 'com.particlesdevs.photoncamera.m9.render.M9PhotonBoundary2Q'
FRAME = JAVA + 'processing/ImageFrame.java'
SAVER = JAVA + 'processing/SaverImplementation.java'
QUEUE = JAVA + 'm9/render/M9PrimaryRenderQueue.java'
DNG = JAVA + 'processing/ImageSaver.java'
GRADLE = 'app/build.gradle'

def sha(data): return hashlib.sha256(data).hexdigest()
def need(condition, message):
    if not condition: raise SystemExit(message)
def inventory(root):
    files = [root / GRADLE]
    for directory in ['app/src/main', 'circularbarlib/src/main']:
        files.extend(p for p in (root / directory).rglob('*') if p.is_file())
    return {str(p.relative_to(root)): sha(p.read_bytes()) for p in sorted(files)}
def once(text, old, new):
    need(text.count(old) == 1, 'Non-unique hook anchor: ' + old[:100])
    return text.replace(old, new, 1)

def candidates(root):
    out = {}
    s = (root / FRAME).read_text()
    s = once(s, '    public ByteBuffer buffer;\n',
             '    public ByteBuffer buffer;\n    public ' + FQ + '.Trace m9PhotonBoundary2Q;\n')
    out[FRAME] = s.encode()
    s = (root / SAVER).read_text()
    anchor = '        ImageFrame frame = new ImageFrame(image.getPlanes()[0].getBuffer(), image.getFormat(), width, image.getPlanes()[0].getRowStride(), offset, capacity);\n'
    insert = ('        final ' + FQ + '.Trace boundary2Q =\n'
              '                com.particlesdevs.photoncamera.m9.M9Config.isCaptureTest()\n'
              '                ? ' + FQ + '.beforeCopy(image, width, height, offset, capacity, Allocator.binning) : null;\n')
    s = once(s, anchor, insert + anchor + '        frame.m9PhotonBoundary2Q = boundary2Q;\n')
    s = once(s, '        return frame;\n',
             '        ' + FQ + '.frame(frame, "photonOwnedAfterCopy", null, null);\n        return frame;\n')
    out[SAVER] = s.encode()
    s = (root / QUEUE).read_text()
    anchor = '                renderResult = M9R35Renderer.renderAndSavePrimary(\n'
    s = once(s, anchor, '                M9PhotonBoundary2Q.frame(ownedFrame, "rendererEntry", captureResult, null);\n' + anchor)
    anchor = '            boolean primaryTimingPersistScheduled = M9PrimaryTimingWriter.freezeAndWriteAsync(\n'
    s = once(s, anchor,
             '            if (rendererDiagnostics == null) rendererDiagnostics = new JSONObject();\n'
             '            try {\n'
             '                rendererDiagnostics.put("photonBoundary2Q", M9PhotonBoundary2Q.finish(job.ownedFrame, dngSaved));\n'
             '            } catch (Throwable boundaryError) {\n'
             '                Log.e(DNG_TAG, "PHOTONBOUNDARY2Q final diagnostic failed", boundaryError);\n'
             '            }\n\n' + anchor)
    out[QUEUE] = s.encode()
    s = (root / DNG).read_text()
    anchor = '            return saveSingleRaw(dngFilePath, image.buffer, parameters);\n'
    s = once(s, anchor,
             '            ' + FQ + '.frame(image, "dngWriterInput", captureResult, parameters.cameraID);\n'
             '            boolean boundary2QSaved = saveSingleRaw(dngFilePath, image.buffer, parameters);\n'
             '            ' + FQ + '.frame(image, "dngWriterReturn", captureResult, parameters.cameraID);\n'
             '            return boundary2QSaved;\n')
    out[DNG] = s.encode()
    s = (root / GRADLE).read_text()
    s = once(s, 'versionCode 26727', f'versionCode {CODE}')
    s = once(s, "versionName '2.07-m9capturecolor1a-qualitygate1b'", f"versionName '{VERSION}'")
    out[GRADLE] = s.encode()
    out[HELPER] = (HERE / 'M9PhotonBoundary2Q.java').read_bytes()
    return out

def apply(root):
    baseline = json.loads((HERE / 'baseline_inventory.json').read_text())
    need(len(baseline) == 1007, 'Expected delivered 2.07 full source inventory')
    receipt = root / (ID + '_SOURCE_PROOF.json')
    if receipt.exists():
        proof = json.loads(receipt.read_text())
        need(proof['before'] == baseline, 'Unknown diagnostic source parent')
        need(inventory(root) == proof['after'], 'Diagnostic source drift')
        need((root / HELPER).read_bytes() == (HERE / 'M9PhotonBoundary2Q.java').read_bytes(), 'Helper drift')
        return proof
    before = inventory(root)
    need(before == baseline, 'Source differs from exact delivered 2.07 inventory')
    changes = candidates(root)
    for p, data in changes.items(): (root / p).write_bytes(data)
    after = inventory(root)
    need({p for p in set(before) | set(after) if before.get(p) != after.get(p)} == set(changes), 'Mutation scope mismatch')
    proof = dict(revision=ID, version=VERSION, versionCode=CODE, before=before, after=after,
                 changed=sorted(changes), rendererSourceUnchanged=True, nativeCodeUnchanged=True,
                 exposureSourceUnchanged=True, diagnosticReadsOnly=True,
                 captureTimingMayChange=True, deviceValidationPending=True)
    receipt.write_text(json.dumps(proof, indent=2) + '\n')
    return proof

if __name__ == '__main__':
    need(len(sys.argv) == 2, 'usage: apply.py PhotonCamera')
    proof = apply(Path(sys.argv[1]).resolve())
    print(json.dumps({k:v for k,v in proof.items() if k not in ('before','after')}, indent=2))
