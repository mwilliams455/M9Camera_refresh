import android.opengl.GLES30;
import android.os.SystemClock;
import com.particlesdevs.photoncamera.m9.M9ExposurePlan1A;
import com.particlesdevs.photoncamera.m9.preview.*;
public class MeterTest {
 static int n;static void check(boolean b,String s){n++;if(!b)throw new AssertionError(s);}
 static M9PreviewFrameState1W frame(double ev,String camera,boolean ready) {
  M9ExposurePlan1A p=new M9ExposurePlan1A(1,1000,1000000000L,camera,"PHOTO",100,10000000L,100,10000000L,100,10000000L,ev,0,"test",0,0,100);
  return new M9PreviewFrameState1W(p,new M9GpuPreview2A.Frame(ready,camera),1000000000L,1.25f);
 }
 public static void main(String[] a) {
  M9AutoExposure2D.reset();M9PreviewMeter2D meter=new M9PreviewMeter2D();
  M9PreviewFrameState1W f=frame(0,"0",true);SystemClock.now=1000000000L;
  GLES30.uniforms.put(10,1.25f);GLES30.peaking=1;String state=GLES30.snapshot();
  meter.sample(f,1000000000L,10,11,1);
  check(GLES30.draws==7 && GLES30.reads==1,"one small seven-EV atlas");
  check(GLES30.maps==0,"no synchronous mapping after submission");
  check(state.equals(GLES30.snapshot()),"all display GL state restored after probe");
  SystemClock.now+=10000000;meter.sample(f,1000000000L,10,11,1);
  check(GLES30.maps==0 && GLES30.draws==7,"unsignalled fence neither waits nor resubmits");
  GLES30.signalled=true;SystemClock.now+=10000000;meter.sample(f,1000000000L,10,11,1);
  check(GLES30.maps==1 && GLES30.draws==7,"later ready fence mapped once, probes throttled");
  check(state.equals(GLES30.snapshot()),"pack binding restored after map");
  check(M9AutoExposure2D.decide("0","PHOTO",SystemClock.now,1e9,0,0,0,0).appliedEv==.25,"actual readback reaches placement decision");
  SystemClock.now+=300000000;meter.sample(frame(1,"0",true),1000000000L,10,11,1);
  check(GLES30.draws==7,"manual EV submits no new Auto probes");
  meter.sample(frame(0,"0",false),1000000000L,10,11,1);
  check(GLES30.draws==7,"unverified colour fallback excluded from M9 meter");
  meter.sample(f,1200000000L,10,11,1);
  check(GLES30.draws==7,"texture/result mismatch excluded");
  M9PreviewFrameState1W mismatch=frame(0,"0",true);mismatch.source2A=new M9GpuPreview2A.Frame(true,"1");
  meter.sample(mismatch,1000000000L,10,11,1);check(GLES30.draws==7,"camera context mismatch excluded");
  M9PreviewMeter2D failing=new M9PreviewMeter2D();GLES30.complete=false;
  failing.sample(f,1000000000L,10,11,1);check(state.equals(GLES30.snapshot()),"display restored after failure");
  check(M9AutoExposure2D.decide("0","PHOTO",SystemClock.now,1e9,0,0,0,0).appliedEv==0,"failed probe invalidates previous Auto measurement");
  GLES30.complete=true;failing.sample(f,1000000000L,10,11,1);check(GLES30.draws==7,"failed meter disabled for surface");
  System.out.println("GL2D meter PASS: "+n+" assertions; actual meter methods, zero-timeout fence, restored GL state and failure fallback");
 }
}
