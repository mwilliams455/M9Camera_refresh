from pathlib import Path
import tempfile,subprocess,urllib.request,hashlib
root=Path(__file__).resolve().parents[3]
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);out=d/'classes';out.mkdir()
 stubs={
 'Bitmap':'''package android.graphics;public class Bitmap {public enum Config{ARGB_8888}public int w,h;public int[] p;public Bitmap(int w,int h,int[] p){this.w=w;this.h=h;this.p=p;}public int getWidth(){return w;}public int getHeight(){return h;}public String getColorSpace(){return "sRGB";}public Config getConfig(){return Config.ARGB_8888;}public void recycle(){p=null;}public void getPixels(int[] o,int off,int stride,int x,int y,int width,int height){for(int j=0;j<height;j++)System.arraycopy(p,(y+j)*w+x,o,off+j*stride,width);}}''',
 'BitmapFactory':'package android.graphics;public class BitmapFactory{public static class Options{public Bitmap.Config inPreferredConfig;public int inSampleSize;public boolean inScaled;}}',
 'BitmapRegionDecoder':'package android.graphics;public class BitmapRegionDecoder{public static BitmapRegionDecoder newInstance(String p,boolean s){throw new UnsupportedOperationException();}public int getWidth(){return 0;}public int getHeight(){return 0;}public Bitmap decodeRegion(Rect r,BitmapFactory.Options o){return null;}public void recycle(){}}',
 'Rect':'package android.graphics;public class Rect{public Rect(int a,int b,int c,int d){}}',
 'Base64':'package android.util;public class Base64{public static int NO_WRAP=2;public static String encodeToString(byte[] b,int n){return java.util.Base64.getEncoder().encodeToString(b);}}',
 'RgbTest':'''package com.particlesdevs.photoncamera.m9.preview;
 import android.graphics.Bitmap;import org.json.*;import java.util.*;import java.io.*;import java.util.zip.*;
 public class RgbTest {static int n;static void check(boolean v,String s){n++;if(!v)throw new AssertionError(s);}
 public static void main(String[] a)throws Exception{
  int w=513,h=317;int[] p=new int[w*h];for(int y=0;y<h;y++)for(int x=0;x<w;x++)p[y*w+x]=0xff000000|((x%250)<<16)|((y%250)<<8)|((x+y)%250);
  Bitmap b=new Bitmap(w,h,p);M9ShutterRgb1A.Samples s=M9ShutterRgb1A.capture(b);b.recycle();
  check(s.pixels.length==5,"five spatial samples");
  for(int k=0;k<5;k++){int[] r=s.rects[k];check(r[2]==96&&r[3]==96,"unscaled patches");for(int y=0;y<96;y++)for(int x=0;x<96;x++)if(s.pixels[k][y*96+x]!=p[(y+r[1])*w+x+r[0]])throw new AssertionError("wrong pixel geometry");}
  JSONObject j=M9ShutterRgb1A.json(s);JSONArray regions=j.getJSONArray("regions");
  for(int k=0;k<5;k++){byte[] rgb=new InflaterInputStream(new ByteArrayInputStream(Base64.getDecoder().decode(regions.getJSONObject(k).getString("rgbZlibBase64")))).readAllBytes();check(rgb.length==96*96*3,"lossless payload size");for(int x=0;x<s.pixels[k].length;x++)for(int c=0;c<3;c++)if((rgb[3*x+c]&255)!=((s.pixels[k][x]>>(16-c*8))&255))throw new AssertionError("RGB serialization loss");}
  JSONArray identity=M9ShutterRgb1A.compare(s,s);check(identity.getJSONObject(0).getInt("changedPixels")==0,"identity exactly zero");
  int[][] changed=new int[5][];for(int k=0;k<5;k++){changed[k]=s.pixels[k].clone();for(int x=0;x<changed[k].length;x++)changed[k][x]+=0x10000;}
  M9ShutterRgb1A.Samples t=new M9ShutterRgb1A.Samples(w,h,s.rects,changed,"sRGB","ARGB_8888");JSONObject delta=M9ShutterRgb1A.compare(s,t).getJSONObject(0);
  check(delta.getJSONArray("meanRgbDelta").getDouble(0)==1&&delta.getJSONArray("meanRgbDelta").getDouble(1)==0,"known red code shift measured");
  check(Math.abs(delta.getDouble("rmsChannelCodes")-Math.sqrt(1.0/3))<1e-12,"RMS denominator");
  int[][] wrong=s.rects.clone();wrong[0]=new int[]{1,2,96,96};try{M9ShutterRgb1A.compare(s,new M9ShutterRgb1A.Samples(w,h,wrong,changed,"sRGB","ARGB_8888"));throw new AssertionError("unregistered patches accepted");}catch(IllegalArgumentException expected){}
  System.out.println("M9SHUTTERTRACE1A RGB PASS: "+n+" assertions; 46080 crop pixels and 138240 serialized channels checked; Android JPEG decoder not emulated");
 }}'''
 }
 for name,code in stubs.items():(d/(name+'.java')).write_text(code)
 jar=d/'json.jar';urllib.request.urlretrieve('https://repo.maven.apache.org/maven2/org/json/json/20240303/json-20240303.jar',jar)
 assert hashlib.sha256(jar.read_bytes()).hexdigest()=='3cf6cd6892e32e2b4c1c39e0f52f5248a2f5b37646fdfbb79a66b46b618414ed'
 files=list(d.glob('*.java'))+[root/'patches/shuttertrace1a/M9ShutterRgb1A.java']
 subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-cp',str(jar),'-d',str(out),*map(str,files)],check=True)
 subprocess.run(['java','-ea','-cp',str(out)+':'+str(jar),'com.particlesdevs.photoncamera.m9.preview.RgbTest'],check=True)
