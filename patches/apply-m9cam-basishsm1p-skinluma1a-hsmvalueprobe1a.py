#!/usr/bin/env python3
from pathlib import Path
import base64, hashlib, zlib
base = Path(__file__).resolve().parent
parts = ["01a", "01b1", "01b2", "01c1", "01c2", "02", "03", "04"]
payload = ''.join((base / f"skinluma1a_payload_{part}.txt").read_text().strip() for part in parts)
source = zlib.decompress(base64.b64decode(payload))
expected = "6044ab2232e8dd27d7b99849c0955334435e7a1fe6d96f18ca482b18ac414cef"
actual = hashlib.sha256(source).hexdigest()
if actual != expected:
    raise SystemExit(f"SKINLUMA1A payload sha256 mismatch: {actual} != {expected}")
exec(compile(source, __file__, "exec"))
