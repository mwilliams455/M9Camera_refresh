from pathlib import Path
import json,sys
from m9shuttertrace1b import verify
print(json.dumps(verify(Path(sys.argv[1]).resolve()),indent=2))
