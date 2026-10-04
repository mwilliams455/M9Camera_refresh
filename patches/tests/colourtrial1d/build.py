from pathlib import Path
import sys,importlib.util,os,ctypes as C
spec=importlib.util.spec_from_file_location('base',Path(__file__).resolve().parents[1]/'colourtrial1c/run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.HERE=Path(__file__).resolve().parent
if len(sys.argv)>3 and sys.argv[3]=='scalar':
 real=m.subprocess.run
 def invoke(cmd,**kw):
  if cmd[0]=='g++':cmd=cmd[:1]+['-U__SSE2__']+cmd[1:]
  return real(cmd,**kw)
 m.subprocess.run=invoke
root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();so,ref=m.build(root,out)
lib=m.configure(C.CDLL(str(so)));ref=C.CDLL(str(ref));ref.partial_chroma.argtypes=lib.partial_chroma.argtypes;ref.phase_noise.argtypes=lib.phase_noise.argtypes
m.checks(root,out,lib,ref)
