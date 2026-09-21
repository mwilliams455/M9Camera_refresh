#!/usr/bin/env python3
"""Execute the shipped Java helper through real JVM JNI into the shipped C++."""
from pathlib import Path
import sys,subprocess,shutil,struct,json,os
import numpy as np
repo=Path(__file__).resolve().parents[3];sys.path.insert(0,str(repo/'research/detail1a'))
from detail1h import TiledDetail

STUBS={
'android/util/Pair.java':'''package android.util; public class Pair<F,S>{public final F first;public final S second;public Pair(F f,S s){first=f;second=s;}}''',
'android/hardware/camera2/CaptureResult.java':'''package android.hardware.camera2;import android.util.Pair;public class CaptureResult{
 public static class Key<T>{} public static final Key<Pair<Double,Double>[]> SENSOR_NOISE_PROFILE=new Key<>();
 public static final Key<Integer> SENSOR_SENSITIVITY=new Key<>();public static final Key<Long> SENSOR_EXPOSURE_TIME=new Key<>(),SENSOR_TIMESTAMP=new Key<>();
 public Pair<Double,Double>[] pairs; @SuppressWarnings("unchecked") public <T>T get(Key<T> key){return key==SENSOR_NOISE_PROFILE?(T)pairs:null;}}''',
'android/hardware/camera2/params/LensShadingMap.java':'''package android.hardware.camera2.params;public class LensShadingMap{
 private final float[] data;private final int rows,cols;public LensShadingMap(float[] d,int r,int c){data=d;rows=r;cols=c;}
 public int getColumnCount(){return cols;}public int getRowCount(){return rows;}public int getGainFactorCount(){return data.length;}
 public void copyGainFactors(float[] dst,int off){System.arraycopy(data,0,dst,off,data.length);}}''',
'org/json/JSONArray.java':'''package org.json;public class JSONArray{public JSONArray(){}public JSONArray(Object a){}public JSONArray put(Object v){return this;}}''',
'org/json/JSONObject.java':'''package org.json;import java.util.*;public class JSONObject{public static final Object NULL=new Object();
 public Map<String,Object> values=new HashMap<>();public JSONObject put(String k,Object v){values.put(k,v);return this;}public Object get(String k){return values.get(k);}}''',
'com/particlesdevs/photoncamera/m9/render/DetailJniCheck.java':'''package com.particlesdevs.photoncamera.m9.render;
import java.io.*;import java.nio.*;import android.util.Pair;import android.hardware.camera2.CaptureResult;import android.hardware.camera2.params.LensShadingMap;import org.json.JSONObject;
public class DetailJniCheck {
 @SuppressWarnings("unchecked") public static void main(String[] args)throws Exception{
  System.load(args[0]);long samples=0;int cases=0;
  for(int f=1;f<args.length;f++)try(DataInputStream in=new DataInputStream(new BufferedInputStream(new FileInputStream(args[f])))){
   int w=in.readInt(),h=in.readInt(),cfa=in.readInt(),ox=in.readInt(),oy=in.readInt(),n=w*h;
   float[] black=new float[4],neutral=new float[3],src=new float[24];for(int k=0;k<4;k++)black[k]=in.readFloat();for(int k=0;k<3;k++)neutral[k]=in.readFloat();
   Pair<Double,Double>[] pairs=new Pair[4];for(int k=0;k<4;k++)pairs[k]=new Pair<>(in.readDouble(),in.readDouble());
   for(int k=0;k<src.length;k++)src[k]=in.readFloat();double scale=in.readDouble();
   double[] profile=M9Detail1H.packRgb(pairs,cfa);for(int k=0;k<6;k++)if(profile[k]!=in.readDouble())throw new AssertionError("CFA profile mapping");
   short[] norm=new short[n];ByteBuffer raw=ByteBuffer.allocateDirect(n*2).order(ByteOrder.nativeOrder()),rgb=ByteBuffer.allocateDirect(n*6).order(ByteOrder.nativeOrder());
   for(int k=0;k<n;k++)norm[k]=in.readShort();for(int k=0;k<n;k++)raw.putShort(k*2,in.readShort());
   short[] base=new short[n*3];for(int k=0;k<n*3;k++){base[k]=in.readShort();rgb.putShort(k*2,base[k]);}
   CaptureResult capture=new CaptureResult();capture.pairs=pairs;LensShadingMap map=new LensShadingMap(src,2,3);
   JSONObject diag=M9Detail1H.apply(norm,raw,rgb,w,h,cfa,ox,oy,black,65535,neutral,map,.5,scale,capture);
   if(!Boolean.TRUE.equals(diag.get("guardApplied")))throw new AssertionError("guard inactive");
   for(int k=0;k<n*3;k++){if(rgb.getShort(k*2)!=in.readShort())throw new AssertionError("JNI guard output "+k);if(k%3==1&&rgb.getShort(k*2)!=base[k])throw new AssertionError("green");}
   short[] fallback=new short[n*3];for(int k=0;k<n*3;k++)fallback[k]=in.readShort();
   // Starting from the already modified RGB proves full D reconstruction does
   // not need a retained frame-sized R/B backup.
   diag=M9Detail1H.apply(norm,raw,rgb,w,h,cfa,ox,oy,black,65535,neutral,map,.5,scale,null);
   if(!Boolean.FALSE.equals(diag.get("guardApplied")))throw new AssertionError("missing-profile fallback");
   for(int k=0;k<n*3;k++)if(rgb.getShort(k*2)!=fallback[k])throw new AssertionError("JNI fallback output");
   pairs[cfa]=new Pair<>(Double.NaN,1.);if(M9Detail1H.packRgb(pairs,cfa)!=null)throw new AssertionError("invalid profile");
   if(M9Detail1H.decompose(src,.5,scale*2)!=null)throw new AssertionError("scale mismatch");
   samples+=n*3;cases++;
  }
  System.out.println("DETAIL1H JVM/JNI PASS: "+cases+" CFA/origin cases, "+samples+" RGB samples, exact D fallback");
 }
}'''
}

def main(out):
    out.mkdir(parents=True,exist_ok=True);src=out/'src';classes=out/'classes';classes.mkdir(exist_ok=True)
    for name,body in STUBS.items():p=src/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body)
    target=src/'com/particlesdevs/photoncamera/m9/render/M9Detail1H.java';shutil.copyfile(repo/'patches/m9detail1h/M9Detail1H.java',target)
    java=Path(shutil.which('javac') or shutil.which('java')).resolve().parents[1];so=out/'libdetail1h_jni.so'
    include=Path(os.environ.get('M9_DETAIL_JNI_INCLUDE',str(java/'include')))
    subprocess.run(['g++','-std=c++17','-O3','-Wall','-Wextra','-Werror','-ffp-contract=off','-fno-fast-math','-shared','-fPIC',
        '-I'+str(include),'-I'+str(include/'linux'),str(repo/'patches/m9detail1h/m9detail1h.cpp'),
        str(repo/'research/detail1a/rb_domain.cpp'),str(repo/'research/detail1a/noise2_guard_native.cpp'),'-o',str(so)],check=True)
    compiler=['javac'] if shutil.which('javac') else ['java','com.sun.tools.javac.Main']
    subprocess.run([*compiler,'-d',str(classes),*[str(p) for p in src.rglob('*.java')]],check=True)
    tile=TiledDetail(out/'native');rng=np.random.default_rng(92182);paths=[];w,h=257,259
    srcgrid=np.array([[[1.+.15*y+.2*x+.07*p for p in range(4)] for x in range(3)] for y in range(2)],np.float32)
    common=np.exp(np.log(srcgrid.astype(float)).sum(axis=2)*.25);grid=srcgrid/common[:,:,None]*np.exp(.5*np.log(common))[:,:,None];scale=float(grid.max())
    neutral=np.array([.37,1.,.61],np.float32);nr=float(neutral[0]);nb=float(neutral[2]);black=np.array([64]*4,np.float32)
    for cfa in range(4):
        pairs=np.zeros((4,2));pairs[cfa]=[.0002,.000001];pairs[3-cfa]=[.00025,.0000012]
        pairs[cfa^1]=[.00015,.0000008];pairs[(3-cfa)^1]=[.00016,.0000009]
        profile=np.r_[pairs[cfa],pairs[cfa^1]*.5+pairs[(3-cfa)^1]*.5,pairs[3-cfa]]
        for oy in range(2):
            for ox in range(2):
                phase=((cfa&1)^ox)+2*((cfa>>1)^oy);yy,xx=np.indices((h,w));factor=np.where((xx%2==phase%2)&(yy%2==phase//2),nr,np.where((xx%2!=phase%2)&(yy%2!=phase//2),nb,1.))
                sensor=np.clip(np.rint((9000+rng.normal(size=(h,w))*140)*factor+64),0,65535).astype(np.uint16)
                norm=np.rint((sensor.astype(float)-64)/(65535-64)*65535).astype(np.uint16);base=rng.integers(0,65536,(h,w,3),dtype=np.uint16)
                expected,_=tile.apply(norm,sensor,base,phase,nr,nb,black,65535,profile,grid,scale,origin_y=oy)
                fallback,_=tile.apply(norm,sensor,base,phase,nr,nb,black,65535,profile,grid,scale,guard=False,origin_y=oy)
                p=out/f'case_{cfa}_{ox}_{oy}.bin'
                with p.open('wb') as f:
                    f.write(struct.pack('>5i',w,h,cfa,ox,oy));f.write(black.astype('>f4').tobytes());f.write(neutral.astype('>f4').tobytes());f.write(pairs.astype('>f8').tobytes());f.write(srcgrid.astype('>f4').tobytes());f.write(struct.pack('>d',scale));f.write(profile.astype('>f8').tobytes())
                    for z in [norm,sensor,base,expected,fallback]:f.write(z.astype('>u2').tobytes())
                paths.append(str(p))
    r=subprocess.run(['java','-cp',str(classes),'com.particlesdevs.photoncamera.m9.render.DetailJniCheck',str(so.resolve()),*paths],check=True,capture_output=True,text=True)
    print(r.stdout);(out/'jni_checks.json').write_text(json.dumps(dict(cases=16,rgb_samples=w*h*3*16,source='actual Java helper and C++ JNI with host Camera2/JSON stubs',result=r.stdout.strip()),indent=2)+'\n')

if __name__=='__main__':main(Path(sys.argv[1]))
