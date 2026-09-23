package com.particlesdevs.photoncamera.m9.render;
import java.io.*;import java.nio.*;import java.nio.file.*;import java.util.*;
import android.graphics.Bitmap;import android.util.Pair;import android.hardware.camera2.CaptureResult;
import android.hardware.camera2.params.LensShadingMap;import org.json.JSONObject;
public class TrialJniCheck {
 static native long address(ByteBuffer b);
 static ByteBuffer buffer(int size){return ByteBuffer.allocateDirect(size).order(ByteOrder.nativeOrder());}
 static void check(boolean b,String s){if(!b)throw new AssertionError(s);}
 @SuppressWarnings("unchecked") public static void main(String[] args)throws Exception{
  System.load(args[0]);int cases=0;long samples=0;
  for(int f=2;f<args.length;f++)try(DataInputStream in=new DataInputStream(new BufferedInputStream(new FileInputStream(args[f])))){
   int w=in.readInt(),h=in.readInt(),cfa=in.readInt(),ox=in.readInt(),oy=in.readInt(),n=w*h;
   float[] black=new float[4],neutral=new float[3],grid=new float[24];
   for(int k=0;k<4;k++)black[k]=in.readFloat();for(int k=0;k<3;k++)neutral[k]=in.readFloat();
   Pair<Double,Double>[] pairs=new Pair[4];for(int k=0;k<4;k++)pairs[k]=new Pair<>(in.readDouble(),in.readDouble());
   for(int k=0;k<24;k++)grid[k]=in.readFloat();double scale=in.readDouble();
   short[] norm=new short[n];ByteBuffer sensor=buffer(n*2),rgb=buffer(n*6);
   for(int k=0;k<n;k++)norm[k]=in.readShort();for(int k=0;k<n;k++)sensor.putShort(k*2,in.readShort());
   CaptureResult capture=new CaptureResult();capture.pairs=pairs;LensShadingMap map=new LensShadingMap(grid,2,3);
   JSONObject d=M9ColourTrial1C.apply(norm,sensor,rgb,w,h,cfa,ox,oy,black,65535,neutral,map,.5,scale,capture,4);
   check(Boolean.TRUE.equals(d.get("rawNoiseApplied")),"noise must run");
   for(int k=0;k<n*3;k++)check(rgb.getShort(k*2)==in.readShort(),"JNI RAW/profile/gain mapping "+k);
   d=M9ColourTrial1C.apply(norm,sensor,rgb,w,h,cfa,ox,oy,black,65535,neutral,map,.5,scale,null,1);
   check(Boolean.FALSE.equals(d.get("rawNoiseApplied")),"missing profile must bypass");
   short[] expectedFallback=new short[n*3];
   for(int k=0;k<n*3;k++){expectedFallback[k]=in.readShort();check(rgb.getShort(k*2)==expectedFallback[k],"AMaZE fallback "+k);}
   pairs[cfa]=new Pair<>(Double.NaN,0.);
   d=M9ColourTrial1C.apply(norm,sensor,rgb,w,h,cfa,ox,oy,black,65535,neutral,map,.5,scale,capture,4);
   check(Boolean.FALSE.equals(d.get("rawNoiseApplied")),"invalid profile must bypass");
   for(int k=0;k<n*3;k++)check(rgb.getShort(k*2)==expectedFallback[k],"invalid profile exact fallback");
   boolean rejected=false;try{M9ColourTrial1C.apply(norm,sensor,buffer(6),w,h,cfa,ox,oy,black,65535,neutral,map,.5,scale,null,1);}catch(IllegalStateException good){rejected=true;}
   check(rejected,"undersized RGB buffer");cases++;samples+=n*3;
  }
  byte[] curve=Files.readAllBytes(Paths.get(args[1]));double[] eye={1,0,0,0,1,0,0,0,1},mat={1.1,-.06,-.04,-.07,1.11,-.04,-.03,-.07,1.10},cw={1,1,1},hsm={0,1,1,0,1,1,0,1,1,0,1,1};
  int renderCases=0;Random rng=new Random(19323);
  for(int w:new int[]{129,130}){int h=259,n=w*h;ByteBuffer cam=buffer(n*6);for(int i=0;i<n*3;i++)cam.putShort(i*2,(short)rng.nextInt(65536));
   for(int mode:new int[]{9,0,10}){long ctx=M9NativeColorCore.createContext(cw,mat,hsm,eye,eye,eye,eye,curve,2,2,mode);
    try{ByteBuffer expected=M9ColourTrial1C.prepareFrame(ctx,address(cam),w,h,Math.sqrt(2));
     ByteBuffer q=M9ColourTrial1C.prepareFrameInPlace(ctx,address(cam),w,h,Math.sqrt(2));
     check(q.equals(expected),"in-place JNI differs from separate preparation");
     for(int rotation:new int[]{0,90,180,270})for(int workers:new int[]{1,4,8}){
      int ow=rotation%180==0?w:h,oh=rotation%180==0?h:w;Bitmap bitmap=new Bitmap(ow,oh);int[] composed=new int[n];
      for(int y0=0;y0<h;y0+=128){int rows=Math.min(128,h-y0),pixels=rows*w;int[] argb=new int[pixels];long[] stats=new long[12];
       M9ColourTrial1C.renderBlockParallelDirect(ctx,address(cam)+y0*w*6L,pixels,w,argb,Math.sqrt(2),.8,.9,rotation,workers,stats,q,y0,h);
       check(M9ColourTrial1C.renderBlockParallelDirectBitmap(ctx,address(cam)+y0*w*6L,pixels,w,bitmap,y0,h,Math.sqrt(2),.8,.9,rotation,workers,stats,q),"Bitmap path failed");
       int rw=rotation%180==0?w:rows,rh=rotation%180==0?rows:w;
       int dx=rotation==90?h-y0-rows:rotation==270?y0:0,dy=rotation==180?h-y0-rows:rotation==0?y0:0;
       for(int y=0;y<rh;y++)for(int x=0;x<rw;x++)composed[(y+dy)*ow+x+dx]=argb[y*rw+x];
      }
      for(int i=0;i<n;i++){int got=bitmap.pixels.getInt(i*4);int rgbaToArgb=0xff000000|((got&255)<<16)|(got&65280)|((got>>16)&255);check(rgbaToArgb==composed[i],"Bitmap orientation/blocks");}
      bitmap.invalid=true;byte[] before=new byte[n*4];bitmap.pixels.position(0);bitmap.pixels.get(before);
      check(!M9ColourTrial1C.renderBlockParallelDirectBitmap(ctx,address(cam),w,w,bitmap,0,h,1,.8,.9,rotation,workers,new long[12],q),"invalid Bitmap must return false");
      byte[] after=new byte[n*4];bitmap.pixels.position(0);bitmap.pixels.get(after);check(Arrays.equals(before,after),"rejected Bitmap modified pixels");
      renderCases++;
     }
     // Existing diagnostic path still delegates exactly with null prepared buffer.
     int[] a=new int[n],b=new int[n];M9NativeColorCore.renderBlockParallelDirect(ctx,address(cam),n,w,a,1,.8,.9,0,4,new long[12]);
     M9ColourTrial1C.renderBlockParallelDirect(ctx,address(cam),n,w,b,1,.8,.9,0,4,new long[12],null,0,h);check(Arrays.equals(a,b),"legacy delegate");
    }finally{M9NativeColorCore.destroyContext(ctx);}
   }
  }
  System.out.println("PASS JNI: "+cases+" CFA/origin/profile cases, "+samples+" RGB samples; "+renderCases+" SAT/rotation/thread/Bitmap cases; invalid buffer and missing-profile checks");
 }
}
