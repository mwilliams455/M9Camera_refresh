import android.opengl.GLES30;
import android.os.SystemClock;
import com.particlesdevs.photoncamera.m9.M9ExposurePlan1A;
import com.particlesdevs.photoncamera.m9.preview.*;
import org.json.*;
public class EvidenceTest {
 static int n;static void check(boolean b,String s){n++;if(!b)throw new AssertionError(s);}
 static M9PreviewFrameState1W frame(String camera) {
  M9ExposurePlan1A p=new M9ExposurePlan1A(1,1000,1000000000L,camera,"PHOTO",100,10000000L,100,10000000L,100,10000000L,2,0,"test",0,0,100);
  return new M9PreviewFrameState1W(p,new M9GpuPreview2A.Frame(true,camera),1000000000L,1.25f);
 }
 public static void main(String[] args)throws Exception {
  M9RootCausePixels1A p=new M9RootCausePixels1A();M9PreviewFrameState1W f=frame("4");SystemClock.now=1000000000L;
  GLES30.uniforms.put(10,1.25f);String state=GLES30.snapshot();
  p.sample(f,1000000000L,null,10,11,1,12);
  check(GLES30.maps==0,"asynchronous submission");check(state.equals(GLES30.snapshot()),"all GL state restored including scissor box");
  check(GLES30.crops.get(0).equals("[-492, -912, 1080, 1920]|[0, 0, 96, 96]"),"native viewport crop, not resized full image");
  check(GLES30.crops.get(2).equals("[-300, -912, 1080, 1920]|[192, 0, 96, 96]"),"third panel placement and isolation");
  check(GLES30.stages.toString().equals("[1, 0, 0]"),"actual source/reference/display stages");
  SystemClock.now+=10000000;p.sample(f,1000000000L,null,10,11,1,12);check(GLES30.maps==0,"unsignalled fence never blocks");
  GLES30.signalled=true;SystemClock.now+=10000000;p.sample(f,1000000000L,null,10,11,1,12);
  check(GLES30.maps==1&&GLES30.draws==3,"readback later; one Hz throttle");
  JSONObject snap=p.snapshot(SystemClock.now,f.plan);check(snap.getBoolean("available"),"published");
  JSONObject first=snap.getJSONArray("frames").getJSONObject(0);
  check(first.getBoolean("textureMatchesResult"),"timestamp join exact");
  for(int i=0;i<3;i++) {
   JSONObject panel=first.getJSONObject("panels").getJSONObject(new String[]{"incomingOes","referenceRender","displayRender"}[i]);
   byte[] packed=java.util.Base64.getDecoder().decode(panel.getString("rgbZlibBase64"));
   byte[] rgb=new java.util.zip.InflaterInputStream(new java.io.ByteArrayInputStream(packed)).readAllBytes();
   check(rgb.length==96*96*3,"lossless RGB payload length");
   for(byte v:rgb)if((v&255)!=10+i*30)throw new AssertionError("atlas channel layout");
  }
  check(!p.snapshot(SystemClock.now,frame("5").plan).getBoolean("available"),"wrong camera excluded");
  check(!p.snapshot(0,f.plan).getBoolean("available"),"future samples excluded");
  check(!p.snapshot(SystemClock.now+21000000000L,f.plan).getBoolean("available"),"old history excluded");
  for(int i=0;i<27;i++){SystemClock.now+=1100000000L;p.sample(f,2000000000L+i,null,10,11,1,12);SystemClock.now+=10000000;p.sample(f,2000000000L+i,null,10,11,1,12);}
  check(p.snapshot(SystemClock.now,f.plan).getJSONArray("frames").length()<=20,"bounded history");
  check(state.equals(GLES30.snapshot()),"history collection restores display state");
  M9RootCausePixels1A failed=new M9RootCausePixels1A();GLES30.complete=false;SystemClock.now+=1100000000L;
  failed.sample(f,1,null,10,11,1,12);check(state.equals(GLES30.snapshot()),"failure restores GL state");
  check(failed.snapshot(SystemClock.now,f.plan).getBoolean("disabled"),"failed probe disabled");
  TraceTest.run();System.out.println("M9ROOTCAUSE1A PASS: "+n+" GPU-collector checks plus metadata checks");
 }
}
