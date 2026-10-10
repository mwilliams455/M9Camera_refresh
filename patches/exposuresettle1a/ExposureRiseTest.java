package com.particlesdevs.photoncamera.m9.preview;
public final class ExposureRiseTest {
 static int checks;
 static void eq(double a,double b,String why){checks++;if(Math.abs(a-b)>1e-9)throw new AssertionError(why+": "+a+" != "+b);}
 public static void main(String[] args){
  M9ExposureRise1A r=new M9ExposureRise1A(1e-9);
  long n=10_000_000_000L;
  for(int cycle=0;cycle<20;cycle++){
   for(int i=0;i<3;i++){n+=250_000_000;eq(r.limit(.5,1,n,true),.5,"short rise held");}
   n+=250_000_000;eq(r.limit(.5,.5,n,true),.5,"return to baseline resets votes");
  }
  r.reset();
  for(int i=0;i<4;i++)eq(r.limit(.5,1,n+i*10_000_000,true),.5,"four rapid probes are insufficient");
  for(int i=0;i<100;i++)eq(r.limit(.5,1,n+30_000_000,false),.5,"duplicate wall time cannot vote");
  eq(r.limit(.5,1,n+750_000_000,true),1,"fresh sustained request qualified");
  eq(r.limit(.75,.25,n+800_000_000,true),.25,"lower limit immediate even after approval");
  r.reset();
  eq(r.limit(.5,1,n,true),.5,"first vote");
  eq(r.limit(.5,.75,n+250_000_000,true),.5,"lower common support");
  eq(r.limit(.5,1,n+500_000_000,true),.5,"third vote");
  eq(r.limit(.5,1,n+750_000_000,true),.75,"only level supported throughout approved");
  eq(r.limit(.75,1,n+1_000_000_000,true),.75,"higher level starts another window");
  eq(r.limit(.75,1,n+2_300_000_000L,true),.75,"long gap starts another window");
  eq(r.confirmations(),1,"gap cannot preserve votes");
  r.breakWindow();eq(r.limit(.75,1,n+2_300_000_000L,true),.75,"same probe cannot vote after interruption");
  eq(r.confirmations(),0,"interrupted duplicate count");
  r.reset();eq(r.limit(.5,1,n,true),.5,"reset discards approval");
  eq(r.limit(.5,1,n-1,true),.5,"out-of-order evidence cannot vote");
  eq(r.confirmations(),1,"out-of-order count unchanged");
  System.out.println("EXPOSURE_RISE_ASSERTIONS "+checks+" PASS");
 }
}
