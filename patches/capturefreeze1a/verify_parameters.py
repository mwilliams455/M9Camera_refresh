#!/usr/bin/env python3
"""Run real Parameters/Converter/NoiseModeler against deterministic Camera2 adapters."""
from pathlib import Path
import json,re,subprocess,sys
HERE=Path(__file__).resolve().parent
root,out=map(lambda p:Path(p).resolve(),sys.argv[1:3]);out.mkdir(parents=True,exist_ok=True)
src=root/'app/src/main/java/com/particlesdevs/photoncamera';stub=out/'stubs';classes=out/'classes';classes.mkdir(exist_ok=True)
s={}
def put(name,body): s[name.replace('.','/')+'.java']=body
def simple(name,body):
 package,cls=name.rsplit('.',1);put(name,'package '+package+'; public class '+cls+' {'+body+'}')
for name in ['androidx.annotation.NonNull','android.annotation.SuppressLint']:
 package,cls=name.rsplit('.',1);put(name,'package '+package+'; public @interface '+cls+' {String[] value() default {};}')
simple('android.graphics.Point','public int x,y;public Point(int x,int y){this.x=x;this.y=y;}public Point(Point p){this(p.x,p.y);}')
simple('android.graphics.Rect','public int left,top,right,bottom;public Rect(int a,int b,int c,int d){left=a;top=b;right=c;bottom=d;}public Rect(Rect r){this(r.left,r.top,r.right,r.bottom);}')
simple('android.util.SizeF','float w,h;public SizeF(float w,float h){this.w=w;this.h=h;}public float getWidth(){return w;}public float getHeight(){return h;}')
simple('android.util.Rational','float v;public Rational(int n,int d){v=(float)n/d;}public float floatValue(){return v;}public double doubleValue(){return v;}')
put('android.util.Pair','package android.util;public class Pair<A,B>{public final A first;public final B second;public Pair(A a,B b){first=a;second=b;}}')
simple('android.util.SparseIntArray','java.util.Map<Integer,Integer> m=new java.util.HashMap<>();public void append(int k,int v){m.put(k,v);}public int get(int k){return m.getOrDefault(k,0);}public int get(int k,int d){return m.getOrDefault(k,d);}')
simple('android.os.Build','public static String BRAND="Test";')
simple('android.os.Environment','public static java.io.File getExternalStorageDirectory(){return new java.io.File("/nonexistent-m9-test");}')
simple('android.hardware.camera2.params.BlackLevelPattern','int[] a;public BlackLevelPattern(int[] a){this.a=a;}public void copyTo(int[] b,int o){System.arraycopy(a,0,b,o,4);}')
simple('android.hardware.camera2.params.ColorSpaceTransform','android.util.Rational[] a;public ColorSpaceTransform(android.util.Rational[] a){this.a=a.clone();}public android.util.Rational getElement(int c,int r){return a[r*3+c];}public void copyElements(android.util.Rational[] b,int o){System.arraycopy(a,0,b,o,9);}')
simple('android.hardware.camera2.params.RggbChannelVector','public float getGreenEven(){return 1;}public float getGreenOdd(){return 1;}public float getRed(){return 1;}public float getBlue(){return 1;}')
simple('android.hardware.camera2.params.LensShadingMap','public int getGainFactorCount(){return 4;}public int getColumnCount(){return 1;}public int getRowCount(){return 1;}public void copyGainFactors(float[] a,int o){java.util.Arrays.fill(a,1);}')
keys={
 'CameraCharacteristics':{'Integer':'SENSOR_MAX_ANALOG_SENSITIVITY SENSOR_INFO_COLOR_FILTER_ARRANGEMENT SENSOR_INFO_WHITE_LEVEL LENS_FACING SENSOR_REFERENCE_ILLUMINANT1','Byte':'SENSOR_REFERENCE_ILLUMINANT2','float[]':'LENS_INFO_AVAILABLE_FOCAL_LENGTHS LENS_INFO_AVAILABLE_APERTURES','android.util.SizeF':'SENSOR_INFO_PHYSICAL_SIZE','android.graphics.Rect':'SENSOR_INFO_ACTIVE_ARRAY_SIZE','android.hardware.camera2.params.BlackLevelPattern':'SENSOR_BLACK_LEVEL_PATTERN','android.hardware.camera2.params.ColorSpaceTransform':'SENSOR_CALIBRATION_TRANSFORM1 SENSOR_CALIBRATION_TRANSFORM2 SENSOR_COLOR_TRANSFORM1 SENSOR_COLOR_TRANSFORM2 SENSOR_FORWARD_MATRIX1 SENSOR_FORWARD_MATRIX2'},
 'CaptureResult':{'Integer':'SENSOR_SENSITIVITY SENSOR_DYNAMIC_WHITE_LEVEL','Long':'SENSOR_EXPOSURE_TIME','Float':'LENS_APERTURE LENS_FOCAL_LENGTH','float[]':'SENSOR_DYNAMIC_BLACK_LEVEL','android.util.Pair<Double,Double>[]':'SENSOR_NOISE_PROFILE','android.hardware.camera2.params.LensShadingMap':'STATISTICS_LENS_SHADING_CORRECTION_MAP','android.graphics.Point[]':'STATISTICS_HOT_PIXEL_MAP','android.util.Rational[]':'SENSOR_NEUTRAL_COLOR_POINT','android.hardware.camera2.params.ColorSpaceTransform':'COLOR_CORRECTION_TRANSFORM'},
 'CaptureRequest':{'Integer':'SENSOR_SENSITIVITY CONTROL_AWB_MODE','Long':'SENSOR_EXPOSURE_TIME','Float':'LENS_APERTURE LENS_FOCAL_LENGTH','android.hardware.camera2.params.RggbChannelVector':'COLOR_CORRECTION_GAINS'}}
for cls,types in keys.items():
 body='public static final int LENS_FACING_FRONT=0,CONTROL_AWB_MODE_OFF=0;public static class Key<T>{}private final java.util.Map<Object,Object> values=new java.util.HashMap<>();public <T>T get(Key<T> k){return (T)values.get(k);}public <T>void set(Key<T> k,T v){values.put(k,v);}'
 for t,names in types.items():
  for n in names.split():body+='public static final Key<'+t+'> '+n+'=new Key<>();'
 simple('android.hardware.camera2.'+cls,body)
constants=sorted(set(re.findall(r'CameraMetadata\.(\w+)',(src/'processing/render/Converter.java').read_text())))
simple('android.hardware.camera2.CameraMetadata',''.join('public static final int '+n+'='+str(i+1)+';' for i,n in enumerate(constants)))
simple('com.particlesdevs.photoncamera.util.Log','public static void d(String a,String b){}public static void e(String a,String b){}public static void w(String a,String b){}public static String getStackTraceString(Throwable t){return t.toString();}')
simple('com.particlesdevs.photoncamera.util.Allocator','public static boolean binning;')
simple('com.particlesdevs.photoncamera.api.VendorTagUtils','public static class TunableKey {}')
simple('com.particlesdevs.photoncamera.processing.M9DngColorMetadata','')
simple('com.particlesdevs.photoncamera.capture.CaptureController','public static android.hardware.camera2.CameraCharacteristics mCameraCharacteristics;')
simple('com.particlesdevs.photoncamera.processing.parameters.ExposureIndex','public static double time2sec(long n){return n/1e9;}')
simple('com.particlesdevs.photoncamera.processing.parameters.FrameNumberSelector','public static int frameCount=1;')
simple('com.particlesdevs.photoncamera.processing.render.Const','public static float[] gainMap={1,1,1,1};public static android.graphics.Point mapSize=new android.graphics.Point(1,1);')
simple('com.particlesdevs.photoncamera.settings.PreferenceKeys','public enum Key{KEY_NOISESTR_SEEKBAR}public static float getSharpnessValue(){return 1;}public static float getSaturationValue(){return 1;}public static float getContrastValue(){return 1;}public static float getFloat(Key k){return 1;}')
simple('com.particlesdevs.photoncamera.app.PhotonCamera','''
 public static boolean DEBUG=false;
 public static class Settings {public String mCameraID="0";public double compressor=1.4,exposureCompensation,mergeStrength,shadows;public int cfaPattern=-1,colorMethod,alignAlgorithm,previewFormat;public boolean hdrxNR;}
 public static class Sensor {public com.particlesdevs.photoncamera.processing.render.SpecificSettingSensor selectedSensorSpecifics=new com.particlesdevs.photoncamera.processing.render.SpecificSettingSensor();}
 public static class Specific {public Specific specificSetting=this;public boolean isRawColorCorrection;}
 public static final Settings settings=new Settings();public static final Sensor sensor=new Sensor();public static final Specific specific=new Specific();
 public static Settings getSettings(){return settings;}public static Sensor getSpecificSensor(){return sensor;}public static Specific getSpecific(){return specific;}public static String getVersion(){return "host";}
''')
simple('com.particlesdevs.photoncamera.settings.TunableInjector','''public static void inject(Object o){set(o,"useDynamicBlackLevel",false);set(o,"useDynamicWhiteLevel",true);set(o,"disableMirror",false);}public static void set(Object o,String n,Object v){try{java.lang.reflect.Field f=o.getClass().getDeclaredField(n);f.setAccessible(true);f.set(o,v);}catch(Exception e){throw new AssertionError(e);}}''')
simple('com.particlesdevs.photoncamera.settings.SensorConfigInjector','public static void applyToSensor(String id,Object o){TunableInjector.set(o,"whiteLevelOverride",-1);TunableInjector.set(o,"blackLevelOverride",-1f);}')
for n,body in s.items():
 p=stub/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body)
prod=[src/('processing/render/'+n+'.java') for n in ['Parameters','SpecificSettingSensor','Converter','NoiseModeler','ColorCorrectionTransform','ColorCorrectionCube']]
prod += list((src/'settings/annotations').glob('*.java'))
frozen=src/'processing/render/M9CaptureParameters.java'
if frozen.exists():prod.append(frozen)
probe=HERE/('ParametersBaselineProbe.java' if '--baseline' in sys.argv else 'ParametersFreezeProbe.java')
subprocess.run(['java','com.sun.tools.javac.Main','-d',str(classes),*map(str,stub.rglob('*.java')),*map(str,prod),str(HERE/'ParameterFixtures.java'),str(probe)],check=True)
log=subprocess.check_output(['java','-ea','-cp',str(classes),probe.stem],text=True)
(out/'PARAMETERS_VERIFICATION.json').write_text(json.dumps({'status':'passed','productionClasses':[p.name for p in prod],'evidence':log},indent=2)+'\n')
print(log)
