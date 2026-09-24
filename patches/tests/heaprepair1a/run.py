from pathlib import Path
import ast,sys,subprocess,hashlib,json
root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
here=Path(__file__).resolve().parent;repo=here.parents[2];j=root/'app/src/main/java/com/particlesdevs/photoncamera'
gson=Path(sys.argv[3]).resolve();jsonjar=Path(sys.argv[4]).resolve()
tree=ast.parse((here.parent/'colourtrial1e/run.py').read_text())
stubs=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='stubs' for t in n.targets)))
stubs={k:v for k,v in stubs.items() if k in ['android/content/Context.java','android/os/Process.java','com/particlesdevs/photoncamera/app/PhotonCamera.java']}
stubs['android/content/Context.java']='package android.content;import java.io.*;public class Context {final File dir;public Context(File f){dir=f;}public File getFilesDir(){return dir;}}'
stubs['com/particlesdevs/photoncamera/util/Log.java']='package com.particlesdevs.photoncamera.util;public class Log {public static void d(String t,String m){}public static void w(String t,String m){}public static void e(String t,String m,Throwable e){}}'
stubs['com/particlesdevs/photoncamera/util/SimpleStorageHelper.java']='''package com.particlesdevs.photoncamera.util;import java.io.*;import java.nio.file.*;public class SimpleStorageHelper {public static boolean fail;public static int opens,active;
 public static OutputStream openOutputStreamByAbsPath(String p)throws IOException{opens++;if(fail)throw new IOException("injected failure");Path path=Paths.get(p);Files.createDirectories(path.getParent());active++;return new FilterOutputStream(Files.newOutputStream(path)){public void write(byte[] b,int o,int n)throws IOException{out.write(b,o,n);}public void close()throws IOException{try{super.close();}finally{active--;}}};}}'''
src=out/'src';classes=out/'classes';classes.mkdir(exist_ok=True)
for name,body in stubs.items():p=src/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body)
cp=str(gson)+':'+str(jsonjar);compiler=['java','-m','jdk.compiler/com.sun.tools.javac.Main']
sources=[j/'m9/M9DiagnosticBurstSpool.java',j/'m9/M9DiagnosticStream1A.java',j/'gallery/viewmodel/M9TiffMetadata1A.java']
subprocess.run([*compiler,'-cp',cp,'-d',str(classes),*[str(p) for p in src.rglob('*.java')],*[str(p) for p in sources],str(here/'HeapIoTest.java'),str(here/'TiffTest.java')],check=True)
cp=str(classes)+':'+cp
for mode,folder in [('stage','restart'),('recover','restart'),('updates','updates')]:
 subprocess.run(['java','-Xmx64m','-ea','-cp',cp,'HeapIoTest',mode,str(out/folder)],check=True,timeout=90)
subprocess.run(['java','-Xmx16m','-ea','-cp',cp,'TiffTest',str(out/'offset.dng')],check=True,timeout=30)
for p in (out/'restart/public').glob('*.json'):
 data=json.loads(p.read_text())
 if p.name.startswith('p'):
  i=int(p.stem[1:]);assert data=={'id':i,'body':'x'*(2*1024*1024-len('{"id":'+str(i)+',"body":"')-2)}
 else:
  for entry in data['entries']:assert entry['payload']['body'].startswith('x') and 'id' in entry['payload']
assert json.loads((out/'updates/public/latest.json').read_text())['id']==99
(out/'checks.json').write_text(json.dumps({'production_Java':True,'payloadMiB':160,'heapMiB':64,'TIFF_offsetMiB':80,'TIFF_heapMiB':16,'exact_payloads':True,'restart_streaming_failure_retry_coalescing_background_gate':'PASS'},indent=2)+'\n')
print('PASS exact streamed bundle and individual JSON data; native/Android device verification separate')
