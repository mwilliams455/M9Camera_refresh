#!/usr/bin/env python3
"""PRIMARY2 source-level parity guard for the frozen PRIMARY1 colour loop."""
from pathlib import Path
import hashlib, sys
if len(sys.argv) != 2:
    raise SystemExit("usage: primary2_parallel_source_parity.py <M9R35Renderer.java>")
s = Path(sys.argv[1]).read_text()
anchor = "private static final class ColorStripWorker"
start = s.index("            for (int sy = 0; sy < rows; sy++)", s.index(anchor))
end = s.index("            return new ColorStripResult", start)
loop = s[start:end]
canon = "\n".join(line.strip() for line in loop.splitlines()).strip()
want = "419a95a0fb147fb4bf0e06eaac4a95f2a1f04e2f6b6594c27f32a211d9b20c1a"
got = hashlib.sha256(canon.encode()).hexdigest()
if got != want:
    raise SystemExit(f"PRIMARY2 frozen colour-loop source parity FAIL: {got} != {want}")
# Scheduling constraints: native reads and Bitmap writes must remain serialized.
assert "PARALLEL_RENDER_WORKERS" in s
assert "Math.min(4, Runtime.getRuntime().availableProcessors())" in s
assert s.index("cam16.get(y0, 0, worker.camStrip)") < s.index("colorExecutor.submit")
assert s.index("future.get()") < s.index("unrotated.setPixels(strip.argb")
assert "for (int x = 0; x < w2; x += 2)" in loop
assert "bounded_strip_math_only" in s
print("PRIMARY2 frozen PRIMARY1 colour-loop source parity PASS")
print("canonical_loop_sha256=" + got)
