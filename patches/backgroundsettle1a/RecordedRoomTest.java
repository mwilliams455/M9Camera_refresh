package com.particlesdevs.photoncamera.m9.preview;
import java.lang.reflect.Field;
import java.util.*;
import com.particlesdevs.photoncamera.m9.preview.M9AutoExposure2D.*;
public final class RecordedRoomTest {
 static long now=20_000_000_000L;
 static String mode="PHOTO";static int checks;static boolean candidate;
 static void eq(double a,double b,String why){checks++;if(Math.abs(a-b)>1e-8)throw new AssertionError(why+": "+a+" != "+b);}
 static void yes(boolean a,String why){checks++;if(!a)throw new AssertionError(why);}
 static double read(){return M9AutoExposure2D.decide("room",mode,now+1,7329032260.0,0,0,0,0,true).appliedEv;}
 static double step(Stats[] stats){now+=250_000_000L;M9AutoExposure2D.publish(new Sample("room",mode,now,now,now,7329032260.0,stats));return read();}
 static void set(String name,Object v)throws Exception{Field f=M9AutoExposure2D.class.getDeclaredField(name);f.setAccessible(true);f.set(null,v);}
 static void seed()throws Exception {
  M9AutoExposure2D.reset();read();
  // The trace has one bracket and a previously latched body; restore those recorded
  // latch values explicitly. Do not pretend missing earlier brackets were replayed.
  set("latchedBodyMask",8627136);set("latchedBodyTargetMedian",44);
  set("latchedBodyTargetQ25",15);set("latchedBodySeverity",1.0);
  double v=0;for(int i=0;i<12;i++)v=step(RecordedRoomFixture.recorded());
  eq(v,1.75,"recorded static room settles to its existing cap");
 }
 public static void main(String[] args)throws Exception{
  candidate=Boolean.parseBoolean(args[0]);
  for(String m:new String[]{"PHOTO","MOTION"}){
   mode=m;seed();
   List<Double> out=new ArrayList<>();
   for(int pixels:new int[]{18,11,14,19,18,11,14,19}){
    double v=step(RecordedRoomFixture.clipped(pixels));out.add(v);
    for(int i=0;i<10;i++)eq(read(),v,"duplicate probes do not advance exposure");
   }
   double[] expected=candidate?new double[]{1.75,1.75,1.75,1.75,1.75,1.75,1.75,1.75}
       :new double[]{1.5,1,1,1.25,1.5,1,1,1.25};
   for(int i=0;i<expected.length;i++)eq(out.get(i),expected[i],"transient recorded-room perturbation trajectory");
   System.out.println(mode+" transient-TV trajectory="+out);
   List<Double> sustained=new ArrayList<>();for(int i=0;i<10;i++)sustained.add(step(RecordedRoomFixture.clipped(11)));
   double[] steady=candidate?new double[]{1.75,1.75,1.75,1.75,1.5,1.25,1,1,1,1}
       :new double[]{1,1,1,1,1,1,1,1,1,1};
   for(int i=0;i<steady.length;i++)eq(sustained.get(i),steady[i],"sustained change is accepted and lower target settles");
   System.out.println(mode+" sustained lower qualification="+sustained);
   seed();double v=step(SubjectHeadroomTest.scene(2));yes(v<=.5,"real regional highlight loss still cuts immediately despite held background qualification");
  }
  System.out.println("RECORDED_ROOM_ASSERTIONS "+checks+" PASS");
 }
}
