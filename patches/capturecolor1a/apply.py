#!/usr/bin/env python3
"""CAPTURECOLOR1A: bounded same-result color metadata on exact QUALITYGATE1B.

Only source-audit JSON, its helper, and Android version identity may change.
No capture fixtures or scene-derived data are required.
"""
from pathlib import Path
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
ID = 'M9CAPTURECOLOR1A_READONLY'
VERSION = '2.07-m9capturecolor1a-qualitygate1b'
CODE = 26727
JAVA = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/'
AUDIT = JAVA + 'M9SourceCalibrationAudit1A.java'
HELPER = JAVA + 'M9CaptureColorMetadata1A.java'
RENDER = JAVA + 'M9R35Renderer.java'
GRADLE = 'app/build.gradle'
BASE_AUDIT = 'a390ce19a5e7e0082b4b4c4d38521ad97c6873ed70ec2b6a5eeaf2c84f843586'
BASE_RENDER = 'a6c269e89ad802ed6aeb65c4c14c4adface9a65ffe3a639d55020bac9223a24e'
BASE_GRADLE = '99db2a530540682f40c7868c515f3116b964d22407c03f55705c171a7f4824e2'
ANCHOR = '            out.put("captureColorCorrectionTransform", matrix(transform(captureCct)));\n'
INSERT = '''
            // CAPTURECOLOR1A: retain actual gains and matrix from this exact result.
            out.put("captureColorMetadata1A", M9CaptureColorMetadata1A.capture(
                    captureResult, params != null ? params.cameraID : null));
'''


def need(condition, message):
    if not condition:
        raise SystemExit(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inventory(root):
    files = [root / GRADLE]
    for directory in ['app/src/main', 'circularbarlib/src/main']:
        files.extend(p for p in (root / directory).rglob('*') if p.is_file())
    return {str(p.relative_to(root)): digest(p.read_bytes()) for p in sorted(files)}


def candidates(audit, gradle):
    need(digest(audit) == BASE_AUDIT, 'Unknown source audit baseline')
    need(digest(gradle) == BASE_GRADLE, 'Unknown QUALITYGATE1B Gradle baseline')
    text = audit.decode()
    need(text.count(ANCHOR) == 1, 'Capture CCM audit anchor is not unique')
    text = text.replace(ANCHOR, ANCHOR + INSERT, 1)
    gs = gradle.decode()
    for old, new in [('versionCode 26726', f'versionCode {CODE}'),
                     ("versionName '2.06-m9qualitygate1b-satdiag-exactpatch1b'",
                      f"versionName '{VERSION}'")]:
        need(gs.count(old) == 1, 'Version anchor mismatch')
        gs = gs.replace(old, new, 1)
    return {AUDIT: text.encode(), GRADLE: gs.encode(),
            HELPER: (HERE / 'M9CaptureColorMetadata1A.java').read_bytes()}


def verify(root):
    proof = json.loads((root / (ID + '_SOURCE_PROOF.json')).read_text())
    before, after = proof['before'], inventory(root)
    need(proof['revision'] == ID and after == proof['after'], 'CAPTURECOLOR1A source drift')
    need(len(before) == 1006 and len(after) == 1007, 'Unexpected full source inventory')
    changed = {p for p in set(before) | set(after) if before.get(p) != after.get(p)}
    need(changed == {AUDIT, HELPER, GRADLE}, 'Unexpected source changes')
    need(before[AUDIT] == BASE_AUDIT and before[GRADLE] == BASE_GRADLE,
         'Unknown source parent')
    need(before[RENDER] == after[RENDER] == BASE_RENDER, 'Renderer changed')
    audit = (root / AUDIT).read_text()
    need(audit.count(INSERT) == 1, 'Missing or duplicate metadata hook')
    need(digest(audit.replace(INSERT, '', 1).encode()) == BASE_AUDIT,
         'Audit changes extend beyond the metadata hook')
    need((root / HELPER).read_bytes() == (HERE / 'M9CaptureColorMetadata1A.java').read_bytes(),
         'Helper differs from reviewed source')
    return dict(revision=ID, version=VERSION, versionCode=CODE,
                parent='2.06_QUALITYGATE1B_SATDIAG', changed=sorted(changed),
                photographicPixelChange=False, rendererChanged=False,
                exposureChanged=False, nativeCodeChanged=False, resourcesChanged=False,
                actualGainsFromSameResolvedResult=True, missingGainsRemainNull=True,
                greenChannelsKeptSeparate=True, phoneValidationPending=True)


def apply(root):
    root = root.resolve(); receipt = root / (ID + '_SOURCE_PROOF.json')
    if receipt.exists():
        return verify(root)
    before = inventory(root)
    need(len(before) == 1006, 'Expected complete assembled QUALITYGATE1B app source')
    need(before.get(RENDER) == BASE_RENDER, 'Unknown QUALITYGATE1B renderer')
    need(not (root / HELPER).exists(), 'Metadata helper already exists without receipt')
    outputs = candidates((root / AUDIT).read_bytes(), (root / GRADLE).read_bytes())
    for name, data in outputs.items():
        (root / name).write_bytes(data)
    after = inventory(root)
    receipt.write_text(json.dumps(dict(revision=ID, before=before, after=after), indent=2) + '\n')
    return verify(root)


if __name__ == '__main__':
    need(len(sys.argv) == 2, 'usage: apply.py PhotonCamera')
    print(json.dumps(apply(Path(sys.argv[1])), indent=2))
