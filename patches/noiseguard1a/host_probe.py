"""JDK17 numeric checks against actual helpers and verbatim old/new boundary methods.
Log, Pair, settings storage and data containers are explicit host stubs; this does
not simulate Android SharedPreferences, Camera2 or OpenGL. Android CI runs the
same 22 guard cases plus nine real-boundary Robolectric tests.
"""
from pathlib import Path
import subprocess,sys,tempfile,re
source,parent=map(lambda x:Path(x).resolve(),sys.argv[1:])
pkg='com/particlesdevs/photoncamera/'
def body(text,signature):
 start=text.index(signature);i=text.index('{',start)+1;depth=1
 while depth:depth+=(text[i]=='{')-(text[i]=='}');i+=1
 return text[start:i]
files={
'android/util/Pair.java':'package android.util; public class Pair<A,B>{public final A first; public final B second;public Pair(A a,B b){first=a;second=b;}}',
'org/junit/Test.java':'package org.junit; @java.lang.annotation.Retention(java.lang.annotation.RetentionPolicy.RUNTIME) public @interface Test {}',
'org/junit/Assert.java':'''package org.junit; public class Assert {
public static void fail(String s){throw new AssertionError(s);}public static void assertTrue(boolean b){if(!b)fail("false");}
public static void assertSame(Object a,Object b){if(a!=b)fail("changed reference");}
public static void assertEquals(Object a,Object b){if(!java.util.Objects.equals(a,b))fail(a+" != "+b);}
public static void assertEquals(double a,double b,double d){if(Double.compare(a,b)!=0&&!(Math.abs(a-b)<=d))fail(a+" != "+b);}}
''',
pkg+'util/Log.java':'package com.particlesdevs.photoncamera.util; public class Log {public static void d(String t,String m){}public static void w(String t,String m){}}',
pkg+'api/Settings.java':'package com.particlesdevs.photoncamera.api; public class Settings{public double noiseRstr;}',
pkg+'processing/render/NoiseModeler.java':'package com.particlesdevs.photoncamera.processing.render; import android.util.Pair; public class NoiseModeler{public Pair<Double,Double>[] computeModel;}',
pkg+'processing/render/Parameters.java':'package com.particlesdevs.photoncamera.processing.render; public class Parameters {public NoiseModeler noiseModeler;}',
pkg+'settings/PreferenceKeys.java':'package com.particlesdevs.photoncamera.settings;public class PreferenceKeys{public enum Key{KEY_NOISESTR_SEEKBAR,KEY_MERGE_SEEKBAR}}',
}
for name in ['settings/NoiseStrength1A.java','processing/render/NoiseCoefficients1A.java']:
 files[pkg+name]=(source/'app/src/main/java'/pkg/name).read_text()
tests=(source/'app/src/test/java'/pkg/'processing/render/NoiseGuardTest.java').read_text()
tests='\n'.join(line for line in tests.splitlines() if not any(x in line for x in ['import android.app.Application','import org.junit.runner.RunWith','import org.robolectric','@RunWith','@Config']))
files[pkg+'processing/render/NoiseGuardTest.java']=tests
for label,root in [('OldPipeline',parent),('NewPipeline',source)]:
 text=(root/'app/src/main/java'/pkg/'processing/opengl/postpipeline/PostPipeline.java').read_text()
 method=body(text,'    private void computeNoise(Parameters parameters)')
 files[pkg+'processing/render/'+label+'.java']='''package com.particlesdevs.photoncamera.processing.render;
import com.particlesdevs.photoncamera.api.Settings;import com.particlesdevs.photoncamera.util.Log;
public class '''+label+''' { public float noiseS,noiseO; public float constShift=0;public Settings mSettings=new Settings();
public void run(Parameters p){computeNoise(p);}
'''+method+'\n}\n'
s=(source/'app/src/main/java'/pkg/'settings/SettingsManager.java').read_text()
files[pkg+'settings/SettingsManager.java']='''package com.particlesdevs.photoncamera.settings;
import com.particlesdevs.photoncamera.util.Log;
public class SettingsManager { public Object stored;public static final String TAG="host";
public String getString(String scope,PreferenceKeys.Key key,String fallback){return stored==null?fallback:(String)stored;}
public float getFloatDefault(PreferenceKeys.Key key){return 0.f;}
'''+body(s,'    public Float getFloat(String scope, PreferenceKeys.Key key, Float defaultValue)')+'\n'+body(s,'    public Float getFloat(String scope, PreferenceKeys.Key key)')+'\n}'
files[pkg+'processing/render/HostProbe.java']='''package com.particlesdevs.photoncamera.processing.render;
import static org.junit.Assert.*;import java.util.*;import com.particlesdevs.photoncamera.settings.*;
public class HostProbe {
static void bits(float a,float b){assertEquals(Float.floatToRawIntBits(a),Float.floatToRawIntBits(b));}
public static void main(String[] args)throws Exception {
 int checks=0;
 for(java.lang.reflect.Method m:NoiseGuardTest.class.getDeclaredMethods())if(m.isAnnotationPresent(org.junit.Test.class)){
  try{m.invoke(new NoiseGuardTest());checks++;}catch(java.lang.reflect.InvocationTargetException e){throw new AssertionError(m.getName(),e.getCause());}
 }
 SettingsManager sm=new SettingsManager();PreferenceKeys.Key key=PreferenceKeys.Key.KEY_NOISESTR_SEEKBAR;
 for(String s:new String[]{"NaN","Infinity","140","-7","broken"}){sm.stored=s;bits(0,sm.getFloat("",key));}checks++;
 for(Object o:new Object[]{2.5f,true}){sm.stored=o;bits(0,sm.getFloat("",key));}checks++;
 sm.stored="-0.1234567";bits(-0.1234567f,sm.getFloat("",key));assertEquals("-0.1234567",sm.stored);checks++;
 sm.stored=null;bits(0,sm.getFloat("",key));checks++;
 sm.stored="bad";bits(1.25f,sm.getFloat("",key,1.25f));checks++;
 sm.stored="140";bits(140,sm.getFloat("",PreferenceKeys.Key.KEY_MERGE_SEEKBAR));checks++;
 Parameters p=new Parameters();p.noiseModeler=new NoiseModeler();p.noiseModeler.computeModel=NoiseGuardTest.model(0.125,0.25);
 NewPipeline now=new NewPipeline();now.mSettings.noiseRstr=4;now.run(p);bits(2,now.noiseS);bits(4,now.noiseO);checks++;
 p.noiseModeler.computeModel=NoiseGuardTest.model(0.125,Float.MAX_VALUE/4.0);now.noiseS=7;now.noiseO=9;
 try{now.run(p);fail("overflow accepted");}catch(IllegalArgumentException expected){}bits(7,now.noiseS);bits(9,now.noiseO);checks++;
 p.noiseModeler=null;try{now.run(p);fail("null accepted");}catch(IllegalArgumentException expected){}bits(7,now.noiseS);bits(9,now.noiseO);checks++;
 p.noiseModeler=new NoiseModeler();Random random=new Random(291290);OldPipeline old=new OldPipeline();
 for(int n=0;n<100000;n++){
  float strength=(float)(-6+10*random.nextDouble());String stored=Float.toString(strength);
  bits(Float.parseFloat(stored),NoiseStrength1A.parse(stored,0));
  p.noiseModeler.computeModel=NoiseGuardTest.model(0,0);
  for(int c=0;c<3;c++)p.noiseModeler.computeModel[c]=new android.util.Pair<>(Math.scalb(random.nextDouble()*2-1,random.nextInt(201)-100),Math.scalb(random.nextDouble()*2-1,random.nextInt(201)-100));
  now.mSettings.noiseRstr=old.mSettings.noiseRstr=strength;old.run(p);now.run(p);
  bits(old.noiseS,now.noiseS);bits(old.noiseO,now.noiseO);
 }
 System.out.println("PASS: "+checks+" host checks; 100000 exact-bit noise model comparisons against verbatim v2.90 computeNoise; 100000 valid stored-strength parity cases");
}
}'''
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp)
 for name,text in files.items():
  p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
 subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-d',str(root/'classes')]+[str(root/n) for n in files],check=True)
 subprocess.run(['java','-cp',str(root/'classes'),pkg.replace('/','.')+'processing.render.HostProbe'],check=True)
