"""Apply only the audited Auto policy to an explicitly supplied assembled tree."""
from pathlib import Path
import hashlib
import sys

HERE = Path(__file__).resolve().parent
root = Path(sys.argv[1]).resolve()
target = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9AutoExposure2D.java'
candidate = (HERE / target.name).read_bytes()
current = target.read_bytes()
if current == candidate:
    print('Auto headroom policy already applied')
elif hashlib.sha256(current).hexdigest() != (HERE / 'base.sha256').read_text().strip():
    raise SystemExit('Unexpected Auto policy source; refusing to overwrite')
else:
    target.write_bytes(candidate)
    print('Applied Auto headroom policy; no reconstruction or colour files changed')
