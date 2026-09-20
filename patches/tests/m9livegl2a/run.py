from pathlib import Path
import subprocess,sys,tempfile
root=Path(sys.argv[1]).resolve();here=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as t:
 subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-d',t,str(root/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewMath2A.java'),str(here/'MathTest.java')],check=True)
 subprocess.run(['java','-ea','-cp',t,'MathTest'],check=True)
