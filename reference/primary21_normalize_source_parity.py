#!/usr/bin/env python3
"""PRIMARY2.1 source-level parity guard for PRIMARY2 RAW normalization arithmetic."""
from pathlib import Path
import hashlib, sys
if len(sys.argv) != 2:
    raise SystemExit("usage: primary21_normalize_source_parity.py <M9R35Renderer.java>")
s = Path(sys.argv[1]).read_text()
anchor = "private static NormalizeResult normalizeRange"
start = s.index("                int i = row + x;", s.index(anchor))
end = s.index("            }\n        }\n        return new NormalizeResult", start)
body = s[start:end].replace("localClipped", "clipped").replace("localCounts", "rawCounts")
canon = "\n".join(line.strip() for line in body.splitlines()).strip()
want = "7ec1c0039fa0a4e26812eaa20c14cc5532d21495d6fde89ac726ad9ad0b431ee"
got = hashlib.sha256(canon.encode()).hexdigest()
if got != want:
    raise SystemExit(f"PRIMARY2.1 frozen PRIMARY2 normalization arithmetic FAIL: {got} != {want}")
assert "PARALLEL_NORMALIZE_WORKERS" in s
assert "M9NativeColorCore.normalizeRawDirect" in s
assert "native_directbuffer_disjoint_row_ranges_histogram_reduce" in s
assert "nativeNormalizeComputeElapsedMs" in s
print("NORMNATIVE1A frozen PRIMARY2 RAW-normalization arithmetic reference PASS")
print("canonical_normalize_sha256=" + got)
