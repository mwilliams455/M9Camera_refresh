#!/usr/bin/env python3
"""Run the production allocator with mutable fake gyro hardware and recorded inputs."""
from pathlib import Path
import os,shutil,subprocess,sys,tempfile
here=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix='m9-energy-') as temp:
 d=Path(temp)
 harness=(here.parent/'m9exposureplan1b/run.py').read_text()
 old='public boolean getTripod(){return false;}public int getFilteredShakiness(){return 100;}'
 assert harness.count(old)==1
 harness=harness.replace(old,'public boolean tripod=false;public int shake=100;public boolean getTripod(){return tripod;}public int getFilteredShakiness(){return shake;}')
 (d/'run.py').write_text(harness)
 shutil.copyfile(here/'ExposurePlanTest.java',d/'ExposurePlanTest.java')
 env=dict(os.environ);env['M9_ENERGY_FIXTURE2G']=str(here/'device_fixture.json')
 subprocess.run([sys.executable,str(d/'run.py'),*sys.argv[1:]],env=env,check=True)
