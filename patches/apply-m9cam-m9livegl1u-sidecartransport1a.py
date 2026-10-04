#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv)!=2:
    raise SystemExit("usage: apply-m9cam-m9livegl1u-sidecartransport1a.py <PhotonCamera-root>")
root=Path(sys.argv[1]).resolve()
p=root/"app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePairDiagnostics1P.java"
gradle=root/"app/build.gradle"
if not p.exists(): raise SystemExit("GL1U missing M9LivePairDiagnostics1P")
if not gradle.exists(): raise SystemExit("GL1U missing app/build.gradle")
t=p.read_text()

def one(old,new,label):
    global t
    n=t.count(old)
    if n!=1:
        raise SystemExit(f"GL1U {label}: expected 1 anchor, found {n}")
    t=t.replace(old,new,1)

one(
'''import com.particlesdevs.photoncamera.m9.M9SubjectMotionAnalyzer;
''',
'''import com.particlesdevs.photoncamera.m9.M9SubjectMotionAnalyzer;
import com.particlesdevs.photoncamera.m9.M9DiagnosticBurstSpool;
import com.particlesdevs.photoncamera.m9.M9DiagnosticSidecarIO;
''',
"imports")

old='''            File out = new File(dir, "M9_LIVEPAIR_" + pairId + "_" + sensorPart + ".json");
            byte[] bytes = root.toString(2).getBytes(StandardCharsets.UTF_8);
            try (FileOutputStream fos = new FileOutputStream(out)) {
                fos.write(bytes);
                fos.flush();
            }
            Log.d(TAG, BUILD + " wrote " + out.getAbsolutePath() + " bytes=" + bytes.length);
'''
new='''            File out = new File(dir, "M9_LIVEPAIR_" + pairId + "_" + sensorPart + ".json");

            // M9LIVEGL1U_SIDECARTRANSPORT1A
            // Direct FileOutputStream writes to /DCIM/Camera are not reliable under
            // scoped storage on current Android. Route LIVEPAIR through the same
            // private-first diagnostic spool that already successfully transports
            // TTL / device-port / source-cal / PRIMARY sidecars.
            root.put("sidecarTransport", "m9cam.sidecarspool.v1.privatebundle1b");
            root.put("sidecarRole", "live_pair");
            root.put("publicPath", out.getAbsolutePath());
            byte[] bytes = root.toString(2).getBytes(StandardCharsets.UTF_8);

            boolean staged = M9DiagnosticBurstSpool.stage(
                    out.toPath(), bytes, "live_pair");
            if (!staged) {
                staged = M9DiagnosticSidecarIO.persist(
                        out.toPath(), bytes, "live_pair_spool_fallback");
            }
            if (!staged) {
                throw new IllegalStateException("LIVEPAIR sidecar spool+fallback failed");
            }
            Log.d(TAG, "M9LIVEGL1U_SIDECARTRANSPORT1A staged "
                    + out.getAbsolutePath() + " bytes=" + bytes.length);
'''
one(old,new,"write transport")
p.write_text(t)

# Make installed version unmistakable.
g=gradle.read_text()
lines=g.splitlines()
for i,line in enumerate(lines):
    s=line.strip()
    if s.startswith("versionName "):
        prefix=line[:len(line)-len(line.lstrip())]
        value=s[len("versionName "):].strip()
        q='"' if value.startswith('"') else "'"
        if not (value.startswith(q) and value.endswith(q)):
            raise SystemExit("GL1U unsupported versionName syntax")
        base=value[1:-1]
        if "m9livegl1u-sidecartransport1a" not in base.lower():
            lines[i]=prefix+"versionName "+q+base+"-m9livegl1u-sidecartransport1a"+q
        break
else:
    raise SystemExit("GL1U versionName missing")
gradle.write_text("\n".join(lines)+("\n" if g.endswith("\n") else ""))

print("M9LIVEGL1U_SIDECARTRANSPORT1A applied")
print(" - LIVEPAIR uses M9DiagnosticBurstSpool private-first transport")
print(" - direct scoped-storage FileOutputStream path removed")
print(" - existing PRIMARY transport untouched")
