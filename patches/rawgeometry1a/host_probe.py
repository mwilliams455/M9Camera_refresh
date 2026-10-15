"""JDK-only geometry checks with explicit Android/data stubs, not Android integration.
Runs the 16 pure cases from the candidate test source unchanged, plus six checks
of verbatim extracted production controller methods. Requires Java 17.
"""
from pathlib import Path
import hashlib,json,re,subprocess,sys,tempfile
source=Path(sys.argv[1]).resolve()
parent=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else None
base=source/'app/src/main/java/com/particlesdevs/photoncamera'
controller=(base/'capture/CaptureController.java').read_text()
def method(signature):
 start=controller.index(signature); brace=controller.index('{',start); end=brace+1; depth=1
 while depth:
  depth+=(controller[end]=='{')-(controller[end]=='}');end+=1
 return controller[start:end]
stubs={
'android/graphics/Rect.java':'''package android.graphics; public class Rect {
 public int left,top,right,bottom; public Rect(int l,int t,int r,int b){left=l;top=t;right=r;bottom=b;}
 public Rect(Rect r){this(r.left,r.top,r.right,r.bottom);}
 public boolean equals(Object o){if(!(o instanceof Rect))return false;Rect r=(Rect)o;return left==r.left&&top==r.top&&right==r.right&&bottom==r.bottom;}
 public String toString(){return left+","+top+","+right+","+bottom;}}
''',
'android/graphics/ImageFormat.java':'package android.graphics; public class ImageFormat { public static final int RAW_SENSOR=32; }',
'android/util/Size.java':'''package android.util; public class Size { private final int w,h;
 public Size(int w,int h){this.w=w;this.h=h;}public int getWidth(){return w;}public int getHeight(){return h;}
 public boolean equals(Object o){return o instanceof Size&&((Size)o).w==w&&((Size)o).h==h;} public int hashCode(){return w*31+h;} public String toString(){return w+"x"+h;}}
''',
'android/os/Build.java':'package android.os; public class Build {public static class VERSION {public static int SDK_INT=35;}}',
'android/hardware/camera2/params/SessionConfiguration.java':'package android.hardware.camera2.params; public class SessionConfiguration {}',
'android/hardware/camera2/CameraDevice.java':'package android.hardware.camera2; public class CameraDevice {public boolean isSessionConfigurationSupported(android.hardware.camera2.params.SessionConfiguration c){return true;}}',
'android/hardware/camera2/params/StreamConfigurationMap.java':'package android.hardware.camera2.params; public class StreamConfigurationMap {public android.util.Size[] sizes; public android.util.Size[] getOutputSizes(int f){return sizes;}}',
'android/hardware/camera2/CameraCharacteristics.java':'''package android.hardware.camera2; import android.graphics.Rect; import android.hardware.camera2.params.StreamConfigurationMap; import java.util.*;
 public class CameraCharacteristics {public static class Key<T>{}
 public static final Key<Rect> SENSOR_INFO_ACTIVE_ARRAY_SIZE=new Key<>(),SENSOR_INFO_PRE_CORRECTION_ACTIVE_ARRAY_SIZE=new Key<>();
 public static final Key<StreamConfigurationMap> SCALER_STREAM_CONFIGURATION_MAP=new Key<>();
 private final Map<Key<?>,Object> data=new HashMap<>(); public <T> void put(Key<T> key,T value){data.put(key,value);}
 @SuppressWarnings("unchecked") public <T>T get(Key<T> key){return (T)data.get(key);}}
''',
'org/junit/Test.java':'package org.junit; public @interface Test {}',
'org/junit/Assert.java':'''package org.junit; public class Assert {
 public static void assertTrue(boolean b){if(!b)throw new AssertionError("expected true");}
 public static void assertFalse(boolean b){assertTrue(!b);} public static void assertNull(Object o){if(o!=null)throw new AssertionError("expected null: "+o);}
 public static void assertNotNull(Object o){if(o==null)throw new AssertionError("unexpected null");}
 public static void assertEquals(Object a,Object b){if(!java.util.Objects.equals(a,b))throw new AssertionError(a+" != "+b);}
 public static void assertNotSame(Object a,Object b){if(a==b)throw new AssertionError("same object");}}
''',
'com/particlesdevs/photoncamera/api/CameraReflectionApi.java':'''package com.particlesdevs.photoncamera.api; import android.hardware.camera2.CameraCharacteristics;
 public class CameraReflectionApi {public static int writes=0;
 public static <T> void set(CameraCharacteristics c,CameraCharacteristics.Key<T> key,T value){writes++;c.put(key,value);}}
''',
'com/particlesdevs/photoncamera/app/PhotonCamera.java':'''package com.particlesdevs.photoncamera.app;
 public class PhotonCamera {public static class Settings {public boolean QuadBayer=true;} public static class Sensor {public Sensor selectedSensorSpecifics=this;public int[] preferredResolution=null;}
 static Settings settings=new Settings(); public static Settings getSettings(){return settings;} public static Sensor getSpecificSensor(){return new Sensor();}}
''',
}
resolution=(base/'processing/parameters/ResolutionSolution.java').read_text()
limit=re.search(r'highRes\s*=\s*([^;]+);',resolution).group(1)
methods='\n'.join(method(s) for s in ['    private Size getCameraOutputSize(Size[] sizes, Size previewSize)', '    private static boolean scaleQuadBayerGeometry1A(Size candidate)', '    private String rawSizeCameraKey1A()', '    static class CompareSizesByArea'])
package='com/particlesdevs/photoncamera/capture/'
stubs[package+'CaptureController.java']='''package com.particlesdevs.photoncamera.capture;
import android.graphics.*; import android.util.*; import android.hardware.camera2.*; import android.hardware.camera2.params.*; import java.util.*;
import com.particlesdevs.photoncamera.app.PhotonCamera;import com.particlesdevs.photoncamera.api.CameraReflectionApi;
class CaptureController {
 static CameraCharacteristics mCameraCharacteristics;static int mTargetFormat=32;String logicalID="2",physicalID="2";static String TAG="probe";
 Size target;boolean useMaximumResolutionKey=true;RawSizeCompatibility1A rawSizeCompatibility1A=new RawSizeCompatibility1A();RawSizeCompatibility1A.Discovery rawSizeDiscovery1A;RawSizeCompatibility1A.Trial rawSizeTrial1A;
 static class Log {static void w(String t,String m){}}
 static class ResolutionSolution {static int highRes='''+limit+''';}
 Size select(Size[] sizes){return getCameraOutputSize(sizes,new Size(1920,1080));}
'''+methods+'\n}\n'
tests=(source/'app/src/test/java/com/particlesdevs/photoncamera/capture/RawGeometryTest.java').read_text()
pure=tests[tests.index('public class RawGeometryTest {'):tests.index('    /** Exercise the actual controller')]
names=re.findall(r'@Test public void (\w+)\(',pure);assert len(names)==16
stubs[package+'RawGeometryTest.java']='package com.particlesdevs.photoncamera.capture; import static org.junit.Assert.*; import org.junit.Test; import android.graphics.Rect; import android.util.Size; import java.util.*;\n'+pure+'}\n'
driver='''package com.particlesdevs.photoncamera.capture;
import static org.junit.Assert.*; import android.graphics.*; import android.util.*; import android.hardware.camera2.*; import android.hardware.camera2.params.*; import com.particlesdevs.photoncamera.api.CameraReflectionApi; import java.util.*;
public class HostProbe {
 static final Size standard=new Size(4000,3000),vendor=new Size(8000,6000);
 static CaptureController fixture(Rect active,Rect pre,Size[] publicSizes){
  CaptureController c=new CaptureController(); CameraCharacteristics ch=new CameraCharacteristics();CaptureController.mCameraCharacteristics=ch;
  ch.put(CameraCharacteristics.SENSOR_INFO_ACTIVE_ARRAY_SIZE,active);ch.put(CameraCharacteristics.SENSOR_INFO_PRE_CORRECTION_ACTIVE_ARRAY_SIZE,pre);
  StreamConfigurationMap map=new StreamConfigurationMap();map.sizes=publicSizes;ch.put(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP,map);
  c.rawSizeDiscovery1A=c.rawSizeCompatibility1A.discover("2/2/32",Collections.singletonList(standard),Collections.singletonList(vendor),true,true);
  c.rawSizeTrial1A=c.rawSizeDiscovery1A.trial(vendor,ch,active,pre);CameraReflectionApi.writes=0;return c;
 }
 static Size select(CaptureController c){return c.select(new Size[]{standard,vendor});}
 static void integration(){
  Rect active=new Rect(0,0,4000,3000),pre=new Rect(4,6,4016,3024);
  CaptureController c=fixture(active,pre,new Size[]{standard});assertEquals(vendor,select(c));assertEquals(2,CameraReflectionApi.writes);
  assertEquals(new Rect(0,0,8000,6000),CaptureController.mCameraCharacteristics.get(CameraCharacteristics.SENSOR_INFO_ACTIVE_ARRAY_SIZE));
  assertEquals(new Rect(8,12,8032,6048),CaptureController.mCameraCharacteristics.get(CameraCharacteristics.SENSOR_INFO_PRE_CORRECTION_ACTIVE_ARRAY_SIZE));
  assertEquals(new Rect(0,0,4000,3000),active);assertEquals(new Rect(4,6,4016,3024),pre);assertTrue(c.useMaximumResolutionKey);
  c=fixture(new Rect(0,0,4000,0),pre,new Size[]{standard});assertEquals(standard,select(c));assertEquals(0,CameraReflectionApi.writes);
  c=fixture(active,new Rect(0,0,Integer.MAX_VALUE,3024),new Size[]{standard});assertEquals(standard,select(c));assertEquals(0,CameraReflectionApi.writes);assertEquals(new Rect(0,0,4000,3000),active);
  c=fixture(null,pre,new Size[]{standard});assertEquals(standard,select(c));assertNull(c.rawSizeDiscovery1A);assertNull(c.rawSizeTrial1A);assertFalse(c.useMaximumResolutionKey);
  assertTrue(c.rawSizeCompatibility1A.discover("2/2/32",Collections.singletonList(standard),Collections.singletonList(vendor),true,true).additions.isEmpty());
  assertFalse(c.rawSizeCompatibility1A.discover("3/3/32",Collections.singletonList(standard),Collections.singletonList(vendor),true,true).additions.isEmpty());
  c=fixture(null,pre,null);boolean rejected=false;try{select(c);}catch(IllegalArgumentException expected){rejected=expected.getMessage().contains("RAWGEOMETRY1A");}assertTrue(rejected);assertEquals(0,CameraReflectionApi.writes);
  c=fixture(active,null,new Size[]{standard});assertEquals(standard,select(c));assertEquals(standard,select(c));assertEquals(0,CameraReflectionApi.writes);
 }
 static void legacyMul(Rect in,double k){in.bottom*=k;in.left*=k;in.right*=k;in.top*=k;}
 static void validParity(){
  Random random=new Random(289);
  for(int i=0;i<100000;i++){
   int left=random.nextInt(512),top=random.nextInt(512),w=2048+random.nextInt(20000),h=2048+random.nextInt(20000);
   Rect a=new Rect(left,top,left+w,top+h),p=new Rect(0,0,left+w+32,top+h+32);
   Size target=new Size(4000,h/2+random.nextInt(h*4));
   RawGeometry1A.Pair actual=RawGeometry1A.prepare(a,p,target); assertNotNull(actual);
   Rect expectedA=new Rect(a),expectedP=new Rect(p);double k=(double)target.getHeight()/a.bottom;
   legacyMul(expectedA,k);legacyMul(expectedP,k);assertEquals(expectedA,actual.active);assertEquals(expectedP,actual.preCorrection);
  }
 }
 public static void main(String[] args) throws Exception {
'''+''.join('  new RawGeometryTest().'+n+'();\n' for n in names)+'''  integration();validParity();System.out.println("PASS: 22 host checks and 100000 valid rectangle-pair parity cases (JDK with explicit stubs)");
 }
}
'''
if parent:
 old=(parent/'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java').read_text()
 expected=''.join(re.search(r'private void mul\(Rect in, double k\) \{([^}]+)',old).group(1).split())
 assert expected=='in.bottom*=k;in.left*=k;in.right*=k;in.top*=k;', 'Legacy arithmetic changed'
stubs[package+'HostProbe.java']=driver
for name in ['RawGeometry1A.java','RawSizeCompatibility1A.java']:stubs[package+name]=(base/'capture'/name).read_text()
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp)
 for name,content in stubs.items():
  p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content)
 subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-d',str(root/'classes')]+[str(root/n) for n in stubs],check=True)
 subprocess.run(['java','-cp',str(root/'classes'),'com.particlesdevs.photoncamera.capture.HostProbe'],check=True)
print(json.dumps({'status':'PASS','checks':22,'validPairParityCases':100000,'legacyArithmeticVerifiedAgainstParent':parent is not None,'runtime':'JDK with Android/data stubs; no device or Android build','sourceSha256':{n:hashlib.sha256((base/'capture'/n).read_bytes()).hexdigest() for n in ['CaptureController.java','RawGeometry1A.java','RawSizeCompatibility1A.java']}},indent=2))
