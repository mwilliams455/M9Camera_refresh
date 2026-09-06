#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: fix-m9cam-rawshading1a-sidecario1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9RawShadingAudit1A.java'
if not path.exists():
    raise SystemExit('RAWSHADING1A SIDECARIO1A requires M9RawShadingAudit1A.java')
text = path.read_text()

import_anchor = 'import com.particlesdevs.photoncamera.processing.render.Parameters;\n'
transport_import = 'import com.particlesdevs.photoncamera.m9.M9DiagnosticSidecarIO;\n'
if transport_import not in text:
    if import_anchor not in text:
        raise SystemExit('RAWSHADING1A SIDECARIO1A import anchor missing')
    text = text.replace(import_anchor, transport_import + import_anchor, 1)

old = '''            Path sidecar = sidecarPath(dngPath);
            if (sidecar != null) {
                Files.write(sidecar, out.toString(2).getBytes(StandardCharsets.UTF_8));
                out.put("sidecarPath", sidecar.toString());
            }
'''
new = '''            Path sidecar = sidecarPath(dngPath);
            if (sidecar != null) {
                out.put("sidecarPath", sidecar.toString());
                out.put("sidecarTransport", M9DiagnosticSidecarIO.SCHEMA);
                byte[] frozenAudit = out.toString(2).getBytes(StandardCharsets.UTF_8);
                boolean sidecarPersisted = M9DiagnosticSidecarIO.persist(
                        sidecar, frozenAudit, "raw_shading_audit");
                out.put("sidecarPersisted", sidecarPersisted);
            }
'''
if new not in text:
    if old not in text:
        raise SystemExit('RAWSHADING1A SIDECARIO1A Files.write anchor missing')
    text = text.replace(old, new, 1)

path.write_text(text)
print('M9RAWSHADING1A SIDECARIO1A applied')
print(' - shading JSON uses established direct-filesystem-first / SAF-fallback transport')
print(' - renderer pixels, RAW, TC20, JPEG and DNG behavior unchanged')
