from pathlib import Path
import subprocess,sys,tempfile,shutil
here=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as tmp:
    d=Path(tmp)
    shutil.copyfile(here.parent/'m9exposureplan1b/run.py',d/'run.py')
    shutil.copyfile(here/'ExposurePlanTest.java',d/'ExposurePlanTest.java')
    subprocess.run([sys.executable,str(d/'run.py'),*sys.argv[1:]],check=True)
