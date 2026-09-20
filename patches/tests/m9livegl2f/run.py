"""Exercise actual production request, curve agreement, cache and fallback using API stubs."""
from pathlib import Path
import hashlib,shutil,subprocess,sys,tempfile,urllib.request
root=Path(sys.argv[1]).resolve();here=Path(__file__).resolve().parent
stubs={
'android/util/Rational.java':'package android.util;public class Rational {public double doubleValue(){return 1;}}',
'android/os/Build.java':'package android.os;public class Build {public static class VERSION {public static int SDK_INT=36;}}',
'android/hardware/camera2/CameraCharacteristics.java':'''package android.hardware.camera2;import java.util.*;public class CameraCharacteristics {
 public static class Key<T>{} public static final Key<int[]> TONEMAP_AVAILABLE_TONE_MAP_MODES=new Key<>();public static final Key<Integer> TONEMAP_MAX_CURVE_POINTS=new Key<>();
 private Map<Key<?>,Object> values=new HashMap<>();public <T> void put(Key<T> k,T v){values.put(k,v);}public <T>T get(Key<T> k){return (T)values.get(k);}}''',
'android/hardware/camera2/CaptureRequest.java':'''package android.hardware.camera2;import android.hardware.camera2.params.*;import java.util.*;public class CaptureRequest {
 public static final int TONEMAP_MODE_CONTRAST_CURVE=0;public static class Key<T>{}public static final Key<Integer> TONEMAP_MODE=new Key<>();public static final Key<TonemapCurve> TONEMAP_CURVE=new Key<>();
 public static class Builder {private Map<Key<?>,Object> values=new HashMap<>();public <T>void set(Key<T>k,T v){values.put(k,v);}public <T>T get(Key<T>k){return (T)values.get(k);}}}''',
'android/hardware/camera2/CaptureResult.java':'''package android.hardware.camera2;import android.hardware.camera2.params.*;import android.util.Rational;import java.util.*;public class CaptureResult {public static final int TONEMAP_MODE_CONTRAST_CURVE=0;
 public static class Key<T>{}public static final Key<Integer> TONEMAP_MODE=new Key<>(),CONTROL_POST_RAW_SENSITIVITY_BOOST=new Key<>();
 public static final Key<TonemapCurve> TONEMAP_CURVE=new Key<>();public static final Key<ColorSpaceTransform> COLOR_CORRECTION_TRANSFORM=new Key<>();
 public static final Key<RggbChannelVector> COLOR_CORRECTION_GAINS=new Key<>();public static final Key<Rational[]> SENSOR_NEUTRAL_COLOR_POINT=new Key<>();
 private Map<Key<?>,Object> values=new HashMap<>();public <T>void put(Key<T>k,T v){values.put(k,v);}public <T>T get(Key<T>k){return (T)values.get(k);}}''',
'android/hardware/camera2/TotalCaptureResult.java':'''package android.hardware.camera2;import java.util.*;public class TotalCaptureResult extends CaptureResult {public Map<String,TotalCaptureResult> getPhysicalCameraResults(){return new HashMap<>();}}''',
'android/hardware/camera2/params/TonemapCurve.java':'''package android.hardware.camera2.params;import java.util.*;public class TonemapCurve {private float[][] c;
 public TonemapCurve(float[]r,float[]g,float[]b){c=new float[][]{r.clone(),g.clone(),b.clone()};}public int getPointCount(int i){return c[i].length/2;}public void copyColorCurve(int i,float[]d,int o){System.arraycopy(c[i],0,d,o,c[i].length);}public String toString(){return Arrays.deepToString(c);}}''',
'android/hardware/camera2/params/ColorSpaceTransform.java':'''package android.hardware.camera2.params;public class ColorSpaceTransform {public android.util.Rational getElement(int x,int y){return new android.util.Rational(){public double doubleValue(){return x==y?1:0;}};}public String toString(){return "identity";}}''',
'android/hardware/camera2/params/RggbChannelVector.java':'''package android.hardware.camera2.params;public class RggbChannelVector {public float getGreenEven(){return 1;}public float getGreenOdd(){return 1;}public float getRed(){return 1;}public float getBlue(){return 1;}public String toString(){return "ones";}}''',
'com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java':'''package com.particlesdevs.photoncamera.m9.render;public class M9R35Renderer {public static int calls;public static double[][] exportPreviewContext2A(Object a,Object b){calls++;return new double[][]{{1,0,0,0,1,0,0,0,1},{1,0,0,0,1,0,0,0,1},{1,1,1},{0}};}}'''
}
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);src=d/'src';out=d/'classes';out.mkdir()
 for rel,s in stubs.items():p=src/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
 for name in ['M9GpuPreview2A','M9PreviewMath2A']:shutil.copyfile(root/('app/src/main/java/com/particlesdevs/photoncamera/m9/preview/'+name+'.java'),src/(name+'.java'))
 shutil.copyfile(here/'ContractTest.java',src/'ContractTest.java')
 jar=d/'json.jar'
 if len(sys.argv)>2:shutil.copyfile(sys.argv[2],jar)
 else:urllib.request.urlretrieve('https://repo.maven.apache.org/maven2/org/json/json/20240303/json-20240303.jar',jar)
 assert hashlib.sha256(jar.read_bytes()).hexdigest()=='3cf6cd6892e32e2b4c1c39e0f52f5248a2f5b37646fdfbb79a66b46b618414ed'
 subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-cp',str(jar),'-d',str(out),*[str(p) for p in src.rglob('*.java')]],check=True)
 subprocess.run(['java','-ea','-cp',str(out)+':'+str(jar),'ContractTest',str(here/'telephoto_curve_samples.json')],check=True)
