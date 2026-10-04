#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: fix-m9cam-sourcecal1d-sidecarspool1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit('SOURCECAL1D SIDECARSPOOL1A: not a PhotonCamera root')

source_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9SourceCalibrationAudit1A.java'
raw_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9RawShadingAudit1A.java'
spool_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9DiagnosticBurstSpool.java'
renderer_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'


def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit('SOURCECAL1D missing expected file: ' + rel)
    return p.read_text()


def write(rel, text):
    (root / rel).write_text(text)


def sha(rel):
    return hashlib.sha256((root / rel).read_bytes()).hexdigest()

spool = read(spool_rel)
if 'm9cam.sidecarspool.v1.privatebundle1b' not in spool or 'public static boolean stage(' not in spool:
    raise SystemExit('SOURCECAL1D requires CAPTURESPLIT1C M9DiagnosticBurstSpool')

# Storage-only change. Preserve the renderer itself byte-for-byte.
renderer_before = sha(renderer_rel)

source = read(source_rel)
source = source.replace(
    'import com.particlesdevs.photoncamera.m9.M9DiagnosticSidecarIO;\n',
    'import com.particlesdevs.photoncamera.m9.M9DiagnosticBurstSpool;\n', 1)
source_old = '''                out.put("sidecarPath", sidecar.toString());
                out.put("sidecarTransport", M9DiagnosticSidecarIO.SCHEMA);
                byte[] frozen = out.toString(2).getBytes(StandardCharsets.UTF_8);
                boolean persisted = M9DiagnosticSidecarIO.persist(sidecar, frozen, "source_calibration_audit");
                out.put("sidecarPersisted", persisted);
'''
source_new = '''                out.put("sidecarPath", sidecar.toString());
                out.put("sidecarTransport", M9DiagnosticBurstSpool.SCHEMA);
                byte[] frozen = out.toString(2).getBytes(StandardCharsets.UTF_8);
                boolean staged = M9DiagnosticBurstSpool.stage(sidecar, frozen, "source_calibration_audit");
                out.put("sidecarStaged", staged);
'''
if source_old not in source:
    raise SystemExit('SOURCECAL1D SOURCECAL blocking-sidecar anchor missing')
source = source.replace(source_old, source_new, 1)
write(source_rel, source)

raw = read(raw_rel)
raw = raw.replace(
    'import com.particlesdevs.photoncamera.m9.M9DiagnosticSidecarIO;\n',
    'import com.particlesdevs.photoncamera.m9.M9DiagnosticBurstSpool;\n', 1)
raw_old = '''                out.put("sidecarPath", sidecar.toString());
                out.put("sidecarTransport", M9DiagnosticSidecarIO.SCHEMA);
                byte[] frozenAudit = out.toString(2).getBytes(StandardCharsets.UTF_8);
                boolean sidecarPersisted = M9DiagnosticSidecarIO.persist(
                        sidecar, frozenAudit, "raw_shading_audit");
                out.put("sidecarPersisted", sidecarPersisted);
'''
raw_new = '''                out.put("sidecarPath", sidecar.toString());
                out.put("sidecarTransport", M9DiagnosticBurstSpool.SCHEMA);
                byte[] frozenAudit = out.toString(2).getBytes(StandardCharsets.UTF_8);
                boolean sidecarStaged = M9DiagnosticBurstSpool.stage(
                        sidecar, frozenAudit, "raw_shading_audit");
                out.put("sidecarStaged", sidecarStaged);
'''
if raw_old not in raw:
    raise SystemExit('SOURCECAL1D RAWSHADING blocking-sidecar anchor missing')
raw = raw.replace(raw_old, raw_new, 1)
write(raw_rel, raw)

for rel in [source_rel, raw_rel]:
    text = read(rel)
    for marker in [
        'M9DiagnosticBurstSpool.stage(',
        'M9DiagnosticBurstSpool.SCHEMA',
        'sidecarStaged',
    ]:
        if marker not in text:
            raise SystemExit('SOURCECAL1D spool marker missing in %s: %s' % (rel, marker))
    if 'M9DiagnosticSidecarIO.persist(' in text:
        raise SystemExit('SOURCECAL1D blocking diagnostic persistence still active in ' + rel)

if sha(renderer_rel) != renderer_before:
    raise SystemExit('SOURCECAL1D unexpectedly changed frozen renderer')

print('M9SOURCECAL1D SIDECARSPOOL1A applied')
print(' - SOURCECAL and RAWSHADING immutable JSON stage immediately to existing SIDECAR1B private spool')
print(' - public burst bundle/legacy individual exports occur asynchronously')
print(' - direct-first/SAF persistence removed from render-worker audit calls')
print(' - renderer, RAW, DNG, TC20, exposure, source transform and GainMap application unchanged')
