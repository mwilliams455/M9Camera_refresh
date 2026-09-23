#!/usr/bin/env python3
from pathlib import Path
import json,sys
from m9rbrollback1a import verify
if len(sys.argv)!=2:raise SystemExit('usage: verify-m9cam-m9rbrollback1a.py PhotonCamera')
print(json.dumps(verify(Path(sys.argv[1]).resolve()),indent=2))
