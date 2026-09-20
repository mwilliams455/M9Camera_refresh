import android.opengl.GLES30;
import android.os.SystemClock;
import android.graphics.SurfaceTexture;
import com.particlesdevs.photoncamera.m9.M9ExposurePlan1A;
import com.particlesdevs.photoncamera.m9.preview.*;
import org.json.*;
public class EvidenceTest {
 static int n;static void check(boolean b,String s){n++;if(!b)throw new AssertionError(s);}
 static M9PreviewFrameState1W frame(double ev,String camera,boolean ready) {
  M9ExposurePlan1A p=new M9ExposurePlan1A(1,1000,1000000000L,camera,"PHOTO",100,10000000L,100,10000000L,100,10000000L,ev,0,"test",0,0,100);
  return new M9PreviewFrameState1W(p,new M9GpuPreview2A.Frame(ready,camera),1000000000L,1.25f);
 }
 public static void main(String[] a)throws Exception {
  M9AutoExposure2D.reset();M9PreviewEvidence2E probe=new M9PreviewEvidence2E();
  M9PreviewFrameState1W f=frame(1,"4",false);SystemClock.now=1000000000L;
  GLES30.uniforms.put(10,1.25f);GLES30.peaking=1;String state=GLES30.snapshot();
  check(!probe.snapshot(SystemClock.now,f.plan).getBoolean("available"),"explicit unavailable before completion");
  probe.sample(f,1000000000L,new SurfaceTexture(),10,11,1,12);
  check(GLES30.draws==3 && GLES30.reads==1,"paired atlas collected even at manual EV and source fallback");
  check(GLES30.stages.toString().equals("[1, 0, 0]"),"OES only bypass; remaining panels actual render");
  check(GLES30.scales.toString().equals("[1.25, 1.0, 1.25]"),"neutral reference and displayed scale separate");
  check(GLES30.maps==0,"submission never maps immediately");
  check(state.equals(GLES30.snapshot()),"all GL state including diagnostic mode restored");
  SystemClock.now+=10000000;probe.sample(f,1000000000L,null,10,11,1,12);
  check(GLES30.maps==0 && GLES30.draws==3,"unsignalled fence zero wait");
  GLES30.signalled=true;SystemClock.now+=10000000;probe.sample(f,1000000000L,null,10,11,1,12);
  check(GLES30.maps==1 && GLES30.draws==3,"later readback and one Hz throttle");
  check(state.equals(GLES30.snapshot()),"readback restores pack binding");
  JSONObject snap=probe.snapshot(SystemClock.now,f.plan);check(snap.getBoolean("available"),"readback published");
  check(snap.getInt("textureDataSpace")==142671872,"dataspace from submitted texture");
  check(snap.getBoolean("textureMatchesResult"),"metadata correspondence recorded");
  check(!snap.getBoolean("sameFrameAsShutter") && !snap.getBoolean("displayPresentationVerified"),"does not assert unsupported identity");
  String[] names={"incomingOes","referenceRender","displayRender"};
  for(int i=0;i<3;i++) {
   JSONObject panel=snap.getJSONObject("panels").getJSONObject(names[i]);int value=10+i*30;
   check(panel.getInt("minLuma")==value && panel.getInt("medianLuma")==value && panel.getInt("q99Luma")==value,"correct atlas panel stats");
   String expected=String.format("%02x%02x%02x",value,value,value);
   check(panel.getString("rgbHex").length()==32*24*6 && panel.getString("rgbHex").startsWith(expected),"portable RGB samples retain input levels");
  }
  check(!probe.snapshot(SystemClock.now,frame(0,"0",true).plan).getBoolean("available"),"wrong camera rejected");
  check(probe.snapshot(SystemClock.now+3000000000L,f.plan).getString("reason").equals("stale_readback"),"stale sample explicitly rejected");
  check(probe.snapshot(0,f.plan).getString("reason").equals("stale_readback"),"future sample rejected");
  check(M9AutoExposure2D.decide("4","PHOTO",SystemClock.now,1e9,0,0,0,0).appliedEv==0,"diagnostic pixels never feed Auto");
  SystemClock.now+=1100000000;M9PreviewEvidence2E failed=new M9PreviewEvidence2E();GLES30.complete=false;
  failed.sample(f,1000000000L,null,10,11,1,12);
  check(state.equals(GLES30.snapshot()),"failure restores display state");
  check(!failed.snapshot(SystemClock.now,f.plan).getBoolean("available"),"failed readback not reported as pixels");
  GLES30.complete=true;failed.sample(f,1000000000L,null,10,11,1,12);
  check(GLES30.draws==3,"failed diagnostics disabled for surface");
  System.out.println("M9LIVEGL2E paired evidence PASS: "+n+" assertions; actual collector, RGB layout, timestamps, nonblocking GL and failure isolation");
 }
}
