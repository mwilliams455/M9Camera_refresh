#!/usr/bin/env python3
"""Verify compilation inputs and unchanged native libraries/rendering assets."""
from pathlib import Path
import json
import shutil
import sys
import zipfile

import apply as patch

BASE_APK = 'f96bdc6dcfeb58f87c3f04982a4fe6e1bb7f023252b78d0b233d57b595b990d3'


def main(root, baseline, output):
    root = root.resolve(); output.mkdir(parents=True, exist_ok=True)
    proof = json.loads((root / (patch.ID + '_SOURCE_PROOF.json')).read_text())
    expected, now = proof['after'], patch.inventory(root)
    missing = sorted(set(expected) - set(now))
    modified = sorted(p for p in set(expected) & set(now) if expected[p] != now[p])
    added = sorted(set(now) - set(expected))
    patch.need(not missing and not modified, 'Recorded compilation inputs changed')
    patch.need(all(p.startswith('app/src/main/cpp/') for p in added), 'Unexpected build-generated source')
    patch.need(patch.digest(baseline.read_bytes()) == BASE_APK, 'Unknown 2.06 baseline APK')
    apks = list((root / 'app/build/outputs/apk/debug').glob('*.apk'))
    patch.need(len(apks) == 1, 'Expected exactly one built APK')
    apk = apks[0]
    with zipfile.ZipFile(baseline) as old, zipfile.ZipFile(apk) as new:
        def frozen(z):
            return {n: patch.digest(z.read(n)) for n in z.namelist()
                    if not n.endswith('/') and n.startswith(('lib/', 'assets/', 'res/raw/'))}
        old_entries, new_entries = frozen(old), frozen(new)
        patch.need(bool(old_entries) and old_entries == new_entries,
                   'Packaged native libraries or rendering assets differ from 2.06')
        dex = b''.join(new.read(n) for n in new.namelist() if n.endswith('.dex'))
        for token in [b'captureColorMetadata1A', b'reportedColorCorrectionGainsRGeGoB',
                      b'one_resolved_CaptureResult_passed_to_source_calibration_audit',
                      b'm9.capturecolormetadata.v1a', b'sensorTimestampNs', b'frameNumber',
                      b'captureMetadataReadComplete', b'null_no_inverse_neutral_or_history_substitution',
                      b'M9QUALITYGATE1B_SATDOMAIN_READONLY', b'EXACTPATCHCLIP1B']:
            patch.need(token in dex, 'Missing packaged contract: ' + repr(token))
    destination = output / 'M9Cam_2.07_CAPTURECOLOR1A.apk'
    shutil.copyfile(apk, destination)
    result = dict(revision=patch.ID, status='passed', apk=destination.name,
                  apkSha256=patch.digest(destination.read_bytes()), baselineApkSha256=BASE_APK,
                  recordedInputsUnchanged=True, frozenPackagedEntriesCompared=len(old_entries),
                  nativeLibrariesAndRenderingAssetsIdentical=True,
                  generatedNativeFiles=added, photographicPixelChange=False,
                  deviceValidationPending=True)
    (output / 'PACKAGED_VERIFICATION.json').write_text(json.dumps(result, indent=2) + '\n')
    (output / 'SHA256SUMS.txt').write_text(result['apkSha256'] + '  ' + destination.name + '\n')
    shutil.copyfile(root / (patch.ID + '_SOURCE_PROOF.json'), output / 'SOURCE_PROOF.json')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    patch.need(len(sys.argv) == 4, 'usage: postbuild.py PhotonCamera BASELINE_APK OUTPUT')
    main(*map(Path, sys.argv[1:]))
