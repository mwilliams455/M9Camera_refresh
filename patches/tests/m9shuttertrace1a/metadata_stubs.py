"""Additional Camera2 API stubs for the actual metadata collector."""
trace=(d/'M9RootCauseTrace1A.java').read_text()
for cls in ['CaptureRequest','CaptureResult']:
    keys=sorted(set(re.findall(cls+r'\.(\w+)',trace)))
    longkeys={'SENSOR_TIMESTAMP','SENSOR_EXPOSURE_TIME'}
    floatkeys={'LENS_FOCUS_DISTANCE','LENS_FOCAL_LENGTH'}
    types={'SENSOR_NEUTRAL_COLOR_POINT':'android.util.Rational[]','COLOR_CORRECTION_GAINS':'android.hardware.camera2.params.RggbChannelVector','CONTROL_AWB_LOCK':'Boolean','COLOR_CORRECTION_TRANSFORM':'android.hardware.camera2.params.ColorSpaceTransform','TONEMAP_CURVE':'android.hardware.camera2.params.TonemapCurve'}
    code='package android.hardware.camera2; import java.util.*;public class '+cls+' { public static class Key<T>{}\n'
    for key in keys:
        typ=types.get(key,'Long' if key in longkeys else 'Float' if key in floatkeys else 'Integer')
        code+='public static final Key<'+typ+'> '+key+'=new Key<>();\n'
    code+='public final Map<Key<?>,Object> data=new HashMap<>();public <T> void put(Key<T> k,T v){data.put(k,v);}@SuppressWarnings("unchecked") public <T>T get(Key<T> k){return (T)data.get(k);}public long getFrameNumber(){return 42;} }'
    (d/(cls+'.java')).write_text(code)
(d/'TotalCaptureResult.java').write_text('package android.hardware.camera2;import java.util.*;public class TotalCaptureResult extends CaptureResult {public Map<String,CaptureResult> physical=new HashMap<>();public Map<String,CaptureResult>getPhysicalCameraResults(){return physical;}}')
(d/'RggbChannelVector.java').write_text('package android.hardware.camera2.params;public class RggbChannelVector {public float getRed(){return 2;}public float getGreenEven(){return 1;}public float getGreenOdd(){return 1;}public float getBlue(){return 1.5f;}}')
(d/'Rational.java').write_text('package android.util;public class Rational extends Number {final int n,d;public Rational(int a,int b){n=a;d=b;}public int intValue(){return n/d;}public long longValue(){return n/d;}public float floatValue(){return (float)n/d;}public double doubleValue(){return (double)n/d;}}')
(d/'Base64.java').write_text('package android.util;public class Base64 {public static final int NO_WRAP=2;public static String encodeToString(byte[] b,int f){return java.util.Base64.getEncoder().encodeToString(b);}}')
(d/'TraceTest.java').write_text((here/'TraceTest.java').read_text())

(d/'ColorSpaceTransform.java').write_text('package android.hardware.camera2.params;public class ColorSpaceTransform{public android.util.Rational getElement(int x,int y){return new android.util.Rational(x==y?1:0,1);}}')
(d/'TonemapCurve.java').write_text('package android.hardware.camera2.params;public class TonemapCurve{public int getPointCount(int c){return 2;}public void copyColorCurve(int c,float[] a,int o){float[] v={0,0,1,1};System.arraycopy(v,0,a,o,4);}}')
