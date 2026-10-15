"""Execute actual Java colour classes and tests on JDK17 with Log/JUnit stubs.
Also compile the unmodified v2.89 arithmetic in a separate namespace for parity.
This is a host numeric probe, not an Android/device integration test.
"""
from pathlib import Path
import json,re,subprocess,sys,tempfile
source,parent=map(lambda p:Path(p).resolve(),sys.argv[1:])
pkg='com/particlesdevs/photoncamera/processing/render/'
log='com/particlesdevs/photoncamera/util/Log.java'
files={log:'package com.particlesdevs.photoncamera.util; public class Log {public static void d(String t,String m){} public static void w(String t,String m){}}',
'org/junit/Test.java':'package org.junit; @java.lang.annotation.Retention(java.lang.annotation.RetentionPolicy.RUNTIME) public @interface Test {}',
'org/junit/Assert.java':'''package org.junit; public class Assert {
public static void fail(String s){throw new AssertionError(s);} public static void assertNotSame(Object a,Object b){if(a==b)fail("alias");}
public static void assertEquals(Object a,Object b){if(!java.util.Objects.equals(a,b))fail(a+" != "+b);}
public static void assertEquals(double a,double b,double d){if(Double.compare(a,b)!=0 && !(Math.abs(a-b)<=d))fail(a+" != "+b);}
public static void assertArrayEquals(float[] a,float[] b,float d){if(a.length!=b.length)fail("length");for(int i=0;i<a.length;i++)assertEquals(a[i],b[i],d);}
}'''}
for name in ['ColorCorrectionTransform','ColorCorrectionCube']:
    files[pkg+name+'.java']=(source/'app/src/main/java'/pkg/(name+'.java')).read_text()
    old=(parent/'app/src/main/java'/pkg/(name+'.java')).read_text()
    files['legacy/'+name+'.java']=old.replace('package com.particlesdevs.photoncamera.processing.render;', 'package legacy;')
for name in ['ColorCorrectionTransformTest','CustomColorGuardTest']:
    files[pkg+name+'.java']=(source/'app/src/test/java'/pkg/(name+'.java')).read_text()
files['legacy/Bridge.java']='''package legacy; public class Bridge {
public static float[] matrix(float[] a,float[] b,float[] p,float[] q,float[] w){ColorCorrectionTransform t=new ColorCorrectionTransform();t.matrix=a;t.matrix2=b;t.point1=p;t.point2=q;return t.combineMatrix(w);}
public static float[][] cube(float[][] a,float[][] b,float p,float q,float[] w){ColorCorrectionCube t=new ColorCorrectionCube(),u=new ColorCorrectionCube();t.cube=a;u.cube=b;t.ColorRatio=p;u.ColorRatio=q;return t.Combine(u,w);}
}'''
files[pkg+'HostProbe.java']='''package com.particlesdevs.photoncamera.processing.render;
import java.util.*; import static org.junit.Assert.*;
public class HostProbe {
static void bits(float a,float b){assertEquals(Float.floatToIntBits(a),Float.floatToIntBits(b));}
public static void main(String[] args)throws Exception{
 int tests=0;
 for(Class<?> c:new Class[]{ColorCorrectionTransformTest.class,CustomColorGuardTest.class})
  for(java.lang.reflect.Method m:c.getDeclaredMethods())if(m.isAnnotationPresent(org.junit.Test.class)){
   try{m.invoke(c.getDeclaredConstructor().newInstance());tests++;}catch(java.lang.reflect.InvocationTargetException e){throw new AssertionError(m.getName(),e.getCause());}
  }
 Random r=new Random(290289);
 for(int sample=0;sample<100000;sample++){
  float[] p={r.nextFloat()+0.01f,r.nextFloat()+0.01f,r.nextFloat()+0.01f};
  float[] q={r.nextFloat()+0.01f,r.nextFloat()+0.01f,r.nextFloat()+0.01f};
  float x=(p[0]+p[1])/p[2],y=(q[0]+q[1])/q[2];
  if(Math.abs(x-y)<0.01f){sample--;continue;}
  float[] w={r.nextFloat()+0.01f,r.nextFloat()+0.01f,r.nextFloat()+0.01f};
  float[] before=w.clone();
  ColorCorrectionTransform t=new ColorCorrectionTransform();t.point1=p;t.point2=q;
  for(int i=0;i<9;i++){t.matrix[i]=r.nextFloat()*4-2;t.matrix2[i]=r.nextFloat()*4-2;}
  float[] expected=legacy.Bridge.matrix(t.matrix,t.matrix2,p,q,w.clone()),actual=t.combineMatrix(w);
  for(int i=0;i<9;i++)bits(expected[i],actual[i]);
  ColorCorrectionCube a=new ColorCorrectionCube(),b=new ColorCorrectionCube();a.ColorRatio=x;b.ColorRatio=y;
  for(int i=0;i<3;i++)for(int j=0;j<9;j++){a.cube[i][j]=r.nextFloat()*4-2;b.cube[i][j]=r.nextFloat()*4-2;}
  float[][] old=legacy.Bridge.cube(a.cube,b.cube,x,y,w.clone()),now=a.Combine(b,w),again=a.Combine(b,w);
  for(int i=0;i<3;i++)for(int j=0;j<9;j++){bits(old[i][j],now[i][j]);bits(now[i][j],again[i][j]);}
  for(int i=0;i<3;i++)bits(before[i],w[i]);
 }
 System.out.println("PASS: "+tests+" tests; 100000 matrix and 100000 cube comparisons against compiled v2.89; exact float bits; repeated cubes stable; white point unchanged");
}
}'''
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp)
    for name,content in files.items():
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content)
    subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-d',str(root/'classes')]+[str(root/n) for n in files],check=True)
    subprocess.run(['java','-cp',str(root/'classes'),'com.particlesdevs.photoncamera.processing.render.HostProbe'],check=True)
