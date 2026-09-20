#!/usr/bin/env python3
"""Reuse the established fake-hardware compiler with additional real-allocator regressions."""
from pathlib import Path
import os,shutil,subprocess,sys,tempfile
here=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix='m9-ev-floor-') as temp:
 d=Path(temp)
 shutil.copyfile(here.parent/'m9exposureplan1b/run.py',d/'run.py')
 shutil.copyfile(here/'ExposurePlanTest.java',d/'ExposurePlanTest.java')
 env=dict(os.environ);env['M9_EXPOSURE_FIXTURE1C']=str(here/'device_fixture.json')
 subprocess.run([sys.executable,str(d/'run.py'),*sys.argv[1:]],env=env,check=True)
