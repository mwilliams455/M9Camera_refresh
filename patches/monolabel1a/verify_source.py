"""Verify that only the circle label and APK version differ from 2.46."""
from pathlib import Path
import hashlib, json, sys

parent, root = (Path(p).resolve() for p in sys.argv[1:])
here = Path(__file__).resolve().parent
def files(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for d in ['app/src', 'circularbarlib/src'] for p in (root/d).rglob('*') if p.is_file()} | {
                'app/build.gradle': hashlib.sha256((root/'app/build.gradle').read_bytes()).hexdigest()}
a, b = files(parent), files(root)
overlay = 'app/src/main/java/com/particlesdevs/photoncamera/ui/camera/M9OverlayController.java'
changed = sorted(p for p in a.keys() | b.keys() if a.get(p) != b.get(p))
assert changed == sorted(['app/build.gradle', overlay]), changed
before = (parent/overlay).read_text()
assert before.count('isMonochrom()?"Monochrom":"M9"') == 1
assert (root/overlay).read_text() == before.replace('isMonochrom()?"Monochrom":"M9"', 'isMonochrom()?"Mono":"M9"')
expected_gradle = (parent/'app/build.gradle').read_text().replace('27246', '27247').replace('2.46-monoswitch1a', '2.47-monolabel1a').replace('2.46_MONOSWITCH1A', '2.47_MONOLABEL1A')
assert (root/'app/build.gradle').read_text() == expected_gradle
m = json.loads((here/'manifest.json').read_text())
for name, value in m['fileOverrides'].items():
    assert b[name] == value, name
report = dict(status='PASS', parent='2.46-monoswitch1a', version='2.47-monolabel1a',
              changedFiles=changed, allOtherSourceFilesUnchanged=len(a)-2,
              onlyCircleLabelAndVersionChanged=True, fullMonochromPickerAndSettingsRetained=True)
(here/'SOURCE_VERIFICATION.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
