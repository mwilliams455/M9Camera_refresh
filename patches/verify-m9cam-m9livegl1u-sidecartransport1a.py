#!/usr/bin/env python3
from pathlib import Path
import sys
if len(sys.argv)!=2: raise SystemExit("usage: verify <PhotonCamera-root>")
root=Path(sys.argv[1]).resolve()
p=root/"app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePairDiagnostics1P.java"
g=root/"app/build.gradle"
if not p.exists() or not g.exists(): raise SystemExit("GL1U source missing")
t=p.read_text(); gr=g.read_text()
checks=[
("GL1U marker","M9LIVEGL1U_SIDECARTRANSPORT1A" in t),
("burst spool import","M9DiagnosticBurstSpool" in t),
("fallback import","M9DiagnosticSidecarIO" in t),
("live_pair stage",'M9DiagnosticBurstSpool.stage(' in t and '"live_pair"' in t),
("sidecar schema",'m9cam.sidecarspool.v1.privatebundle1b' in t),
("fallback persist",'M9DiagnosticSidecarIO.persist(' in t and 'live_pair_spool_fallback' in t),
("public path recorded",'root.put("publicPath", out.getAbsolutePath())' in t),
("old direct write removed","new FileOutputStream(out)" not in t),
("GL1P capture snapshot retained","capturePreviewSnapshot(" in t),
("GL1P completion retained","writeCompleted(" in t),
("version label","m9livegl1u-sidecartransport1a" in gr.lower()),
]
for label,ok in checks:
    print(("OK   " if ok else "FAIL ")+label)
    if not ok: raise SystemExit("GL1U contract failure: "+label)
print("M9LIVEGL1U_SIDECARTRANSPORT1A VERIFY PASS")
