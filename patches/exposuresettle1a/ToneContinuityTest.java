package com.particlesdevs.photoncamera.m9.preview;
public final class ToneContinuityTest {
 static int checks;static long n=10_000_000_000L;
 static void eq(double a,double b,String why){checks++;if(Math.abs(a-b)>1e-9)throw new AssertionError(why+": "+a+" != "+b);}
 static void yes(boolean b,String why){checks++;if(!b)throw new AssertionError(why);}
 static double step(M9PreviewToneContinuity1A c,double request,double auto){
  n+=250_000_000;return c.update("2|PHOTO",n+1,n,1.99e9,auto,0,request,true,true);
 }
 static M9PreviewToneContinuity1A settled(double target){
  M9PreviewToneContinuity1A c=new M9PreviewToneContinuity1A();
  for(int i=0;i<12;i++)step(c,target,.75);
  eq(c.appliedEv(),target,"steady tone converges");return c;
 }
 public static void main(String[] args){
  M9PreviewToneContinuity1A c=new M9PreviewToneContinuity1A();
  for(int i=0;i<3;i++)eq(step(c,.5,.75),0,"initial lift needs fresh sustained support");
  eq(step(c,.5,.75),.125,"confirmed lift uses existing eighth-stop slew");
  for(int i=0;i<100;i++)eq(c.update("2|PHOTO",n+20,n,1.99e9,.75,0,.5,true,true),.125,"duplicate cannot advance tone");
  eq(step(c,.5,.75),.25,"approved lift continues at bounded slew");
  eq(step(c,.5,.5),.25,"Auto cut interrupts tone rise");
  eq(step(c,.5,.5),.25,"tone cannot immediately compensate Auto cut");
  eq(step(c,.5,.5),.25,"third Auto-stable probe held");
  eq(step(c,.5,.5),.375,"new stable Auto window permits tone rise");
  c=settled(.3);long trusted=n;
  for(long delta:new long[]{20_000_000,250_000_000,500_000_000,830_000_000,1_000_000_000}){
   eq(c.update("2|PHOTO",trusted+delta,trusted+delta/2,1.99e9,.75,0,.4,true,false),.3,"brief metadata gap holds qualified gain");
   yes(c.reason().equals("held_tone_metadata_gap"),"gap reason explicit");
  }
  eq(c.update("2|PHOTO",trusted+1_000_000_001L,trusted,1.99e9,.75,0,.4,true,false),0,"metadata hold has strict lifetime");
  c=settled(.3);eq(c.update("2|PHOTO",n+10,n+1,1.99e9*Math.pow(2,.251),.75,0,.4,true,false),0,"hold rejected across energy change");
  c=settled(.3);eq(c.update("2|PHOTO",n+10,n,1.99e9,.75,0,.3,false,false),0,"invalid/stale source cannot hold");
  c=settled(.3);eq(c.update("other|PHOTO",n+10,n+1,1.99e9,.75,0,.3,true,false),0,"lens owner cannot inherit tone");
  c=settled(.3);eq(c.update("2|MOTION",n+10,n+1,1.99e9,.75,0,.3,true,false),0,"mode owner cannot inherit tone");
  c=settled(.3);eq(step(c,0,.75),.175,"trusted darker target takes existing bounded step immediately");
  eq(step(c,0,.75),.05,"darkening is not delayed by rise confirmation");
  eq(step(c,0,.75),0,"darkening converges");
  c=settled(-.3);eq(c.update("2|PHOTO",n+400_000_000,n+1,1.99e9,.75,0,-.4,true,false),-.3,"negative tone is also continuous through short gap");
  eq(step(c,.3,.75),-.3,"negative to positive rise confirms");
  c=settled(.125);
  for(int cycle=0;cycle<12;cycle++){
   for(int i=0;i<3;i++)eq(step(c,.4,.75),.125,"short tail-derived rise cannot pump gain");
   eq(step(c,.125,.75),.125,"base target breaks rise window");
  }
  c=settled(.125);step(c,.4,.75);step(c,.4,.75);step(c,.4,.75);
  eq(c.update("2|PHOTO",n+1,n,1.99e9,.75,1,.4,true,true),.125,"user EV change interrupts pending tone lift");
  eq(step(c,.4,.75),.125,"returning EV starts fresh confirmation");
  c.reset();eq(c.appliedEv(),0,"surface reset clears tone");
  System.out.println("TONE_CONTINUITY_ASSERTIONS "+checks+" PASS");
 }
}
