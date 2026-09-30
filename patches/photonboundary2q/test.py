#!/usr/bin/env python3
"""Run the real logger against deterministic host camera stubs and byte corruption."""
from pathlib import Path
import hashlib, json, subprocess, sys

HERE = Path(__file__).resolve().parent
out = Path(sys.argv[1]).resolve(); out.mkdir(parents=True, exist_ok=True)
jar = Path(sys.argv[2]).resolve()
sources = {
'android/hardware/camera2/CaptureResult.java': '''package android.hardware.camera2;
public class CaptureResult {
 public static final Object SENSOR_TIMESTAMP=new Object();
 public Long timestamp; public long frameNumber=7;
 public CaptureResult(Long timestamp){this.timestamp=timestamp;}
 @SuppressWarnings("unchecked") public <T>T get(Object key){return (T)timestamp;}
 public long getFrameNumber(){return frameNumber;}
}''',
'android/media/Image.java': '''package android.media;
import java.nio.ByteBuffer;
public class Image {
 public long timestamp; public int width,height,format=32,stride,pixelStride=2;
 public ByteBuffer buffer;
 public long getTimestamp(){return timestamp;}
 public int getWidth(){return width;} public int getHeight(){return height;}
 public int getFormat(){return format;}
 public Plane[] getPlanes(){return new Plane[]{new Plane()};}
 public class Plane {
  public ByteBuffer getBuffer(){return buffer;}
  public int getRowStride(){return stride;} public int getPixelStride(){return pixelStride;}
 }
}''',
'com/particlesdevs/photoncamera/processing/ImageFrame.java': '''package com.particlesdevs.photoncamera.processing;
import java.nio.ByteBuffer;
import com.particlesdevs.photoncamera.m9.render.M9PhotonBoundary2Q;
public class ImageFrame {
 public ByteBuffer buffer; public long timestamp;
 public M9PhotonBoundary2Q.Trace m9PhotonBoundary2Q;
}''',
'com/particlesdevs/photoncamera/m9/render/M9PhysicalCaptureResult1A.java': '''package com.particlesdevs.photoncamera.m9.render;
import android.hardware.camera2.CaptureResult;
public class M9PhysicalCaptureResult1A {
 public static String resultCameraId(CaptureResult r){return "2";}
}''',
'BoundaryTest.java': r'''import android.media.Image;
import android.hardware.camera2.CaptureResult;
import com.particlesdevs.photoncamera.processing.ImageFrame;
import com.particlesdevs.photoncamera.m9.render.M9PhotonBoundary2Q;
import java.nio.*; import java.util.*; import java.security.*; import org.json.*;
public class BoundaryTest {
 static int checks=0;
 static void check(boolean ok,String why){if(!ok)throw new AssertionError(why);checks++;}
 static Image image(int offset){
  Image i=new Image();i.timestamp=9007199254740997L;i.width=8;i.height=5;i.stride=16;
  i.buffer=ByteBuffer.allocateDirect(80+offset+6).order(ByteOrder.LITTLE_ENDIAN);
  for(int k=0;k<i.buffer.capacity();k++)i.buffer.put(k,(byte)(k*37+5));
  i.buffer.position(3);i.buffer.mark();i.buffer.limit(7);return i;
 }
 static ImageFrame copied(Image i,int offset,boolean binning){
  ImageFrame f=new ImageFrame();f.timestamp=i.timestamp;
  f.m9PhotonBoundary2Q=M9PhotonBoundary2Q.beforeCopy(i,8,5,offset,80,binning);
  f.buffer=ByteBuffer.allocateDirect(80);
  ByteBuffer d=i.buffer.duplicate();d.clear();d.position(offset);d.limit(offset+80);f.buffer.put(d);f.buffer.clear();
  M9PhotonBoundary2Q.frame(f,"photonOwnedAfterCopy",null,null);return f;
 }
 static JSONObject finish(ImageFrame f,Long timestamp){
  CaptureResult r=new CaptureResult(timestamp);
  for(String s:new String[]{"rendererEntry","dngWriterInput","dngWriterReturn"})M9PhotonBoundary2Q.frame(f,s,r,"2");
  return M9PhotonBoundary2Q.finish(f,true);
 }
 public static void main(String[] args)throws Exception{
  Image i=image(4);ImageFrame f=copied(i,4,false);JSONObject ok=finish(f,i.timestamp);
  check(ok.getBoolean("allRawBytesEqual"),"offset copy byte match");
  check(ok.getBoolean("allImageResultTimestampsEqual"),"exact integer timestamp");
  check(ok.getString("status").equals("buffer_handoffs_match_saved_DNG_decode_pending"),"success scope");
  check(!ok.getBoolean("savedDngDecodedPixelsCompared"),"does not claim saved DNG decode");
  check(i.buffer.position()==3&&i.buffer.limit()==7&&i.buffer.order()==ByteOrder.LITTLE_ENDIAN,"camera buffer cursor/order unchanged");
  i.buffer.reset();check(i.buffer.position()==3,"camera mark preserved");
  check(f.buffer.position()==0&&f.buffer.limit()==80,"owned cursor unchanged");
  check(ok.getJSONObject("acquisition").getLong("imageTimestampNs")==9007199254740997L,"timestamp never rounded through double");
  f=copied(i,4,false);f.buffer.put(39,(byte)(f.buffer.get(39)^1));
  check(finish(f,i.timestamp).getString("status").equals("raw_bytes_changed"),"detect single-bit mutation");
  f=copied(i,4,false);check(finish(f,i.timestamp+1).getString("status").equals("frame_result_timestamp_mismatch"),"detect one-ns mismatch");
  f=copied(i,4,false);f.timestamp++;
  check(finish(f,i.timestamp).getString("status").equals("frame_result_timestamp_mismatch"),"detect rewritten frame identity");
  f=copied(i,4,false);check(finish(f,null).getString("status").equals("incomplete"),"missing result timestamp");
  f=copied(i,4,false);check(M9PhotonBoundary2Q.finish(f,true).getString("status").equals("incomplete"),"missing stage");
  f=copied(i,4,false);finish(f,i.timestamp);
  check(M9PhotonBoundary2Q.finish(f,false).getString("status").equals("incomplete"),"failed save");
  f=copied(i,4,true);check(finish(f,i.timestamp).getString("status").equals("unsupported_copy_layout"),"binning is not ordinary copy");
  check(M9PhotonBoundary2Q.finish(new ImageFrame(),true).getString("status").equals("incomplete_no_acquisition_trace"),"missing acquisition trace");
  // Same timestamp does not key or merge two separate frames.
  Image a=image(0),b=image(0);b.buffer.duplicate().clear().put(7,(byte)9);
  ImageFrame af=copied(a,0,false),bf=copied(b,0,false);
  check(finish(af,a.timestamp).getBoolean("allRawBytesEqual")&&finish(bf,b.timestamp).getBoolean("allRawBytesEqual"),"per-frame trace isolation");
  for(int[] window:new int[][]{{-1,1},{0,0},{79,2},{Integer.MAX_VALUE,1}}){
   boolean threw=false;try{M9PhotonBoundary2Q.hashWindow(ByteBuffer.allocate(80),window[0],window[1]);}catch(IllegalArgumentException expected){threw=true;}
   check(threw,"reject invalid window "+Arrays.toString(window));
  }
  byte[] bytes=new byte[4096*3072*2];new Random(29).nextBytes(bytes);
  String expected=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
  check(M9PhotonBoundary2Q.hashWindow(ByteBuffer.wrap(bytes).asReadOnlyBuffer(),0,bytes.length).equals(expected),"full 12MP independent MessageDigest oracle");
  System.out.println(new JSONObject().put("status","passed").put("checks",checks).put("fullRawBytes",bytes.length).put("fullRawSha256",expected).put("androidDeviceTest",false));
 }
}'''
}
for name, source in sources.items():
    p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(source)
source=HERE/'M9PhotonBoundary2Q.java'
subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-cp',str(jar),'-d',str(out),str(source)]+[str(out/n) for n in sources],check=True)
result=subprocess.check_output(['java','-cp',str(out)+':'+str(jar),'BoundaryTest'],text=True)
proof=json.loads(result);proof['helperSha256']=hashlib.sha256(source.read_bytes()).hexdigest()
(out/'HOST_TESTS.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof,indent=2))
