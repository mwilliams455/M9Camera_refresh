package com.particlesdevs.photoncamera.m9.preview;

public final class OpenAnchorQualificationTest {
 static int checks;
 static void eq(double a,double b,String why){checks++;if(Math.abs(a-b)>1e-9)throw new AssertionError(why+": "+a+" != "+b);}
 static void yes(boolean b,String why){checks++;if(!b)throw new AssertionError(why);}
 public static void main(String[] args){
  M9OpenAnchorQualification1A q=new M9OpenAnchorQualification1A();
  long n=10_000_000_000L;int anchor=(1<<14)|(1<<15),other=(1<<7)|(1<<8),body=1840;
  eq(q.update(2.5,0,body,n,true),2.5,"initial no-anchor evidence");
  for(int c=0;c<10;c++)for(int m:new int[]{anchor,anchor,0}){
   n+=250_000_000L;eq(q.update(m==0?2.5:.25,m,body,n,true),2.5,"brief appearance held");
   for(int i=0;i<5;i++)eq(q.update(.25,anchor,body,n,false),2.5,"callbacks do not vote");
  }
  for(int i=0;i<3;i++){n+=250_000_000L;eq(q.update(.25,anchor,body,n,true),2.5,"three fresh probes insufficient");}
  eq(q.update(.25,anchor,body,n+1_000_000_000L,false),2.5,"wall time without evidence insufficient");
  n+=250_000_000L;eq(q.update(.25,anchor,body,n,true),.25,"sustained appearance qualifies");
  yes(q.mask()==anchor,"qualified mask recorded");
  for(int c=0;c<8;c++)for(int m:new int[]{0,0,anchor}){
   n+=250_000_000L;eq(q.update(m==0?2.5:.25,m,body,n,true),.25,"brief disappearance held");
  }
  for(int i=0;i<3;i++){n+=250_000_000L;eq(q.update(2.5,0,body,n,true),.25,"release needs confirmation");}
  n+=250_000_000L;eq(q.update(2.5,0,body,n,true),2.5,"sustained absence releases");
  yes(q.mask()==0,"absence clears qualified mask");
  for(int i=0;i<8;i++){n+=250_000_000L;eq(q.update(.25,i%2==0?anchor:other,body,n,true),2.5,"different regions cannot confirm each other");}
  q.breakWindow();
  for(int i=0;i<4;i++){n+=10_000_000L;eq(q.update(.25,anchor,body,n,true),2.5,"rapid probes lack elapsed evidence");}
  n+=750_000_000L;eq(q.update(.25,anchor,body,n,true),.25,"fresh probe completes elapsed window");
  for(int i=0;i<3;i++){n+=250_000_000L;q.update(.5,anchor,body,n,true);}
  q.breakWindow();n+=250_000_000L;eq(q.update(.5,anchor,body,n,true),.25,"bridge breaks votes but retains cap");
  n+=1_300_000_000L;eq(q.update(.5,anchor,body,n,true),.25,"long gap cannot complete previous window");
  for(int i=0;i<3;i++){n+=250_000_000L;q.update(.5,anchor,body,n,true);}
  eq(q.capEv(),.5,"sustained tier change qualifies");
  for(int i=0;i<10;i++)eq(q.update(2.5,0,99,n-i,true),.5,"out-of-order body change ignored");
  n+=250_000_000L;eq(q.update(.75,other,99,n,true),.75,"new body acquires its own current cap");
  q.reset();n++;eq(q.update(.25,anchor,0,n,true),.25,"initial anchor retained even without body");
  for(int i=0;i<4;i++){n+=250_000_000L;q.update(2.5,0,0,n,true);}
  eq(q.capEv(),2.5,"body-free scene can confirm disappearance");
  n+=250_000_000L;q.update(.25,anchor,0,n,true);
  n+=250_000_000L;q.update(.5,anchor,0,n,true);
  n+=250_000_000L;q.update(.25,anchor|(1<<16),0,n,true);
  n+=250_000_000L;eq(q.update(.5,anchor,0,n,true),.5,"least reduction supported by all probes");
  yes(q.mask()==anchor,"common region persists through boundary jitter");
  System.out.println("OPEN_ANCHOR_QUALIFICATION_ASSERTIONS "+checks+" PASS");
 }
}
