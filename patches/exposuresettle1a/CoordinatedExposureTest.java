package com.particlesdevs.photoncamera.m9.preview;
import com.particlesdevs.photoncamera.m9.preview.M9AutoExposure2D.*;
public final class CoordinatedExposureTest {
 static int checks;static long n=80_000_000_000L;static String mode;
 static void eq(double a,double b,String why){checks++;if(Math.abs(a-b)>1e-8)throw new AssertionError(why+": "+a+" != "+b);}
 static Decision step(Stats[] s,double request){n+=250_000_000;M9AutoExposure2D.publish(new Sample("2",mode,n,n,n,1,s));return M9AutoExposure2D.decide("2",mode,n+1,1,0,0,0,request,true);}
 public static void main(String[] args){
  for(String m:new String[]{"PHOTO","MOTION"}){
   mode=m;M9AutoExposure2D.reset();M9PreviewToneContinuity1A tone=new M9PreviewToneContinuity1A();
   eq(step(RecoveryTest.ordinary(),.5).appliedEv,.5,"initial baseline unchanged");
   for(int i=0;i<12;i++)tone.update("2|"+mode,n+i*250_000_000L+1,n+i*250_000_000L,1,.5,0,.125,true,true);
   n+=3_000_000_000L;
   for(int cycle=0;cycle<12;cycle++){
    for(int i=0;i<4;i++){
     double request=i<3?.75:.5;
     double auto=step(RecoveryTest.ordinary(),request).appliedEv;
     double tc=tone.update("2|"+mode,n+1,n,1,auto,0,i<3?.4:.125,true,true);
     eq(auto,.5,"brief placement request cannot rebound");
     eq(auto+tc,.625,"brief placement and tone requests cannot compound");
    }
   }
   for(int i=0;i<4;i++){
    double auto=step(RecoveryTest.ordinary(),.75).appliedEv;
    double tc=tone.update("2|"+mode,n+1,n,1,auto,0,.4,true,true);
    eq(auto,i<3?.5:.75,"sustained placement rises after window");
    eq(tc,.125,"tone rise restarts when Auto actually changes");
   }
   eq(step(RecoveryTest.blocked(),1).appliedEv,0,"hard highlight loss still cuts on first probe");
  }
  System.out.println("COORDINATED_EXPOSURE_ASSERTIONS "+checks+" PASS");
 }
}
