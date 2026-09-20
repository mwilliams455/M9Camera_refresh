"""Actual M9 GLSL exposure atlases -> actual Java Auto policy, plus inherited colour oracle."""
from pathlib import Path
import contextlib,io,json,runpy,sys,subprocess,tempfile,urllib.request,hashlib
import numpy as np
repo=Path(__file__).resolve().parents[3]
with contextlib.redirect_stdout(io.StringIO()) as inherited:
    fixture=runpy.run_path(str(repo/'patches/tests/m9livegl2c/gpu_test.py'))
inherited_report_2d=json.loads(inherited.getvalue())
globals().update({k:v for k,v in fixture.items() if not k.startswith('__')})
gl('glUseProgram',None,U)(pfull)
for name in ['uM9InputToSensor2A','uM9SensorToPp2A','uM9PpToTarget2A']:
    matrix=np.eye(3,dtype=np.float32);gl('glUniformMatrix3fv',None,I,I,I,P)(loc(pfull,name.encode()),1,0,matrix.ctypes.data)
white=np.ones(3,np.float32);gl('glUniform3fv',None,I,I,P)(loc(pfull,b'uM9ClipWhite2A'),1,white.ctypes.data)
for key,value in [('sTexture',0),('uM9Curve',1),('uM9Inverse2A',2),('uM9Enabled',1),('uM9SourceReady2A',1),('enablePeak',0),('mirror',0)]:ui(pfull,key,value)
uf(pfull,'uM9Tungsten2A',0)
tex(2,inverse,0x8058,0x1908,0x1401)
atlas=np.zeros((24,224,4),np.uint8);target=tex(3,atlas,0x8058,0x1908,0x1401)
gl('glFramebufferTexture2D',None,U,U,U,U,I)(0x8D40,0x8CE0,0x0DE1,target,0)
assert gl('glCheckFramebufferStatus',U,U)(0x8D40)==0x8CD5
scenes={}
for name,value in [('dark',40),('healthy',100),('black',0),('window',40),('highlight',40),('small_dark_object',130)]:
    rgb=np.full((24,32,4),value,np.uint8);rgb[:,:,3]=255
    if name=='window':rgb[:6,:,:3]=255
    if name=='highlight':rgb[:6,:,:3]=160
    if name=='small_dark_object':rgb[8:16,8:24,:3]=20
    scenes[name]=rgb
with tempfile.TemporaryDirectory() as temp:
    d=Path(temp)
    for name,pixels in scenes.items():
        tex(0,pixels,0x8058,0x1908,0x1401)
        for i in range(7):
            gl('glViewport',None,I,I,I,I)(32*i,0,32,24);uf(pfull,'uM9ExposureScale1B',2**(i*.25))
            gl('glDrawArrays',None,U,I,I)(4,0,3)
        gl('glReadPixels',None,I,I,I,I,U,U,P)(0,0,224,24,0x1908,0x1401,atlas.ctypes.data)
        assert geterr()==0
        (d/(name+'.rgba')).write_bytes(atlas.tobytes())
    # Java consumes the actual readback, not copied threshold logic in Python.
    java='''import java.nio.*;import java.nio.file.*;import com.particlesdevs.photoncamera.m9.preview.M9AutoExposure2D;import org.json.*;
public class GpuPolicyTest {public static void main(String[] args)throws Exception {JSONArray report=new JSONArray();
for(String name:new String[]{"dark","healthy","black","window","highlight","small_dark_object"}) {
byte[] b=Files.readAllBytes(Paths.get(args[0],name+".rgba"));M9AutoExposure2D.Stats[] s=M9AutoExposure2D.measure(ByteBuffer.wrap(b));
int selected=M9AutoExposure2D.select(s);JSONArray med=new JSONArray(),clip=new JSONArray();for(M9AutoExposure2D.Stats v:s){med.put(v.median);clip.put(v.clipped);}
if((name.equals("dark")||name.equals("window")) && selected==0)throw new AssertionError(name+" stays dark");
if((name.equals("healthy")||name.equals("black")||name.equals("small_dark_object")) && selected!=0)throw new AssertionError(name+" was lifted");
if(name.equals("highlight") && selected>1)throw new AssertionError("highlight guard failed: "+selected+" med="+med+" clip="+clip);
report.put(new JSONObject().put("scene",name).put("selectedEv",M9AutoExposure2D.ev(selected)).put("weightedMedianBracket",med).put("clipBracket",clip));
}System.out.println(report.toString());}}'''
    (d/'GpuPolicyTest.java').write_text(java)
    jar=d/'json.jar';urllib.request.urlretrieve('https://repo.maven.apache.org/maven2/org/json/json/20240303/json-20240303.jar',jar)
    assert hashlib.sha256(jar.read_bytes()).hexdigest()=='3cf6cd6892e32e2b4c1c39e0f52f5248a2f5b37646fdfbb79a66b46b618414ed'
    policy=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9AutoExposure2D.java'
    subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-cp',str(jar),'-d',str(d),str(policy),str(d/'GpuPolicyTest.java')],check=True)
    result=subprocess.check_output(['java','-ea','-cp',str(d)+':'+str(jar),'GpuPolicyTest',str(d)],text=True)
    scene_report=json.loads(result)
print(json.dumps({'revision':'M9LIVEGL2D_AUTOPLACEMENT','inherited':inherited_report_2d,'shaderToPolicyScenes':scene_report,'phoneCadenceOrParityVerified':False},indent=2))
