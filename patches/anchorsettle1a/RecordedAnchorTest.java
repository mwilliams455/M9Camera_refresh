package com.particlesdevs.photoncamera.m9.preview;
import java.lang.reflect.Field;
import java.util.*;
import org.json.*;
import com.particlesdevs.photoncamera.m9.preview.M9AutoExposure2D.*;

public final class RecordedAnchorTest {
 static long now=40_000_000_000L;static String mode="PHOTO",camera="anchor-room";
 static int checks;static boolean candidate;
 static void eq(double a,double b,String why){checks++;if(Math.abs(a-b)>1e-8)throw new AssertionError(why+": "+a+" != "+b);}
 static void yes(boolean b,String why){checks++;if(!b)throw new AssertionError(why);}
 static Decision read(){return M9AutoExposure2D.decide(camera,mode,now+1,3885882273.0,0,0,0,0,true);}
 static Decision step(Stats[] s){now+=250_000_000L;M9AutoExposure2D.publish(new Sample(camera,mode,now,now,now,3885882273.0,s));return read();}
 static void set(String key,Object v)throws Exception{Field f=M9AutoExposure2D.class.getDeclaredField(key);f.setAccessible(true);f.set(null,v);}
 static void seed(boolean anchor)throws Exception{
  M9AutoExposure2D.reset();read();
  // Restore the recorded latch; its preceding full probes are not available.
  set("latchedBodyMask",1840);set("latchedBodyTargetMedian",45);set("latchedBodyTargetQ25",22);
  set("latchedBodySeverity",.8565279927173418);
  double v=0;for(int i=0;i<12;i++)v=step(anchor?RecordedAnchorFixture.recorded():RecordedAnchorFixture.noAnchor()).appliedEv;
  eq(v,anchor?.25:.5,"stable scene retains existing photographic placement");
 }
 public static void main(String[] args)throws Exception{
  candidate=Boolean.parseBoolean(args[0]);
  yes(M9AutoExposure2D.protectedOpenAnchorMask(RecordedAnchorFixture.recorded()[0])==49152,"actual anchor is fields 14/15");
  yes(M9AutoExposure2D.protectedOpenAnchorMask(RecordedAnchorFixture.noAnchor()[0])==0,"three-code threshold perturbation removes anchor");
  for(String m:new String[]{"PHOTO","MOTION"}){
   mode=m;camera="anchor-room";seed(false);
   List<Double> out=new ArrayList<>();
   for(int i=0;i<12;i++){
    double v=step(i%4>=2?RecordedAnchorFixture.noAnchor():RecordedAnchorFixture.recorded()).appliedEv;out.add(v);
    if(candidate)eq(v,.5,"brief TV-like anchor cannot pulse the stable scene");
    else eq(v,i%4==3?.5:.25,"parent threshold pulse reproduced");
    for(int k=0;k<5;k++)eq(read().appliedEv,v,"duplicate reads preserve exposure");
   }
   System.out.println(mode+" threshold trajectory="+out);
   seed(false);out.clear();
   for(int i=0;i<8;i++)out.add(step(RecordedAnchorFixture.recorded()).appliedEv);
   double[] expected=candidate?new double[]{.5,.5,.5,.5,.25,.25,.25,.25}:new double[]{.25,.25,.25,.25,.25,.25,.25,.25};
   for(int i=0;i<8;i++)eq(out.get(i),expected[i],"sustained appearance confirms and settles");
   System.out.println(mode+" sustained anchor="+out);
   out.clear();for(int i=0;i<6;i++)out.add(step(RecordedAnchorFixture.noAnchor()).appliedEv);
   for(int i=0;i<6;i++)eq(out.get(i),candidate&&i<3?.25:.5,"sustained disappearance releases without permanent lock");
   System.out.println(mode+" sustained absence="+out);
   seed(false);set("heldAutoEv",.75);
   // The trace records .75 immediately before activation; the earlier complete bracket is missing.
   eq(step(RecordedAnchorFixture.recorded()).appliedEv,candidate?.75:.25,"recorded held value no longer loses half a stop immediately");
   if(candidate)eq(step(RecordedAnchorFixture.recorded()).appliedEv,.5,"changed body target still settles by quarter stop");
   seed(false);set("heldAutoEv",1.5);
   Decision clip=step(SubjectHeadroomTest.scene(2));yes(clip.appliedEv<=.5,"real headroom loss cuts immediately");
   seed(true);eq(step(RecordedAnchorFixture.recorded()).appliedEv,.25,"initial anchor keeps conservative cap");
   if(candidate){
    JSONObject d=new JSONObject(read().diagnostics);
    eq(d.getDouble("protectedOpenAnchorLiftCapEv"),.25,"raw anchor diagnostic");
    eq(d.getDouble("qualifiedOpenAnchorCapEv"),.25,"qualified anchor diagnostic");
    yes(d.getDouble("hardPositiveLimitEv")>.25,"semantic anchor excluded from hard limit");
    seed(false);step(RecordedAnchorFixture.recorded());step(RecordedAnchorFixture.recorded());
    M9AutoExposure2D.decide(camera,mode,now+2,3885882273.0,1,0,0,0,true);
    eq(step(RecordedAnchorFixture.recorded()).appliedEv,.5,"manual EV reset reacquires current anchor and confirms ordinary descent");
    eq(step(RecordedAnchorFixture.recorded()).appliedEv,.25,"manual EV exit uses new evidence");
    seed(false);step(RecordedAnchorFixture.recorded());
    M9AutoExposure2D.decide(camera,mode,now+2,3885882273.0,0,1000,0,0,true);
    eq(step(RecordedAnchorFixture.recorded()).appliedEv,.25,"manual shutter exit discards former allowance");
    seed(false);step(RecordedAnchorFixture.recorded());
    M9AutoExposure2D.decide(camera,mode,now+2,3885882273.0,0,0,0,0,false);
    eq(step(RecordedAnchorFixture.recorded()).appliedEv,.25,"ineligible mode clears allowance");
    seed(false);step(RecordedAnchorFixture.recorded());
    M9AutoExposure2D.invalidate("host_gap");read();
    eq(step(RecordedAnchorFixture.recorded()).appliedEv,.25,"unavailable fallback clears allowance");
    seed(false);
    for(int i=0;i<3;i++)step(RecordedAnchorFixture.recorded());
    Decision bridge=M9AutoExposure2D.decide(camera,mode,now+50_000_000L,3885882273.0*Math.pow(2,.3),0,0,0,0,true);
    yes(bridge.reason.equals("rendered_meter_reference_transition_hold"),"reference change enters existing bridge");
    JSONObject resumed=new JSONObject(step(RecordedAnchorFixture.recorded()).diagnostics);
    eq(resumed.getDouble("qualifiedOpenAnchorCapEv"),2.5,"bridge retains cap without completing interrupted confirmation");
    eq(resumed.getInt("openAnchorQualificationConfirmations"),1,"fresh evidence starts new anchor window after bridge");
    seed(false);step(RecordedAnchorFixture.recorded());
    M9TapMeter1A.configure(camera,mode,now,320,240,new int[]{0,0,320,240},new float[]{1,0,0,1},false);
    yes(M9TapMeter1A.choose(160,120,now),"tap accepted");M9TapMeter1A.clear("anchor epoch test");
    JSONObject tapped=new JSONObject(step(RecordedAnchorFixture.recorded()).diagnostics);
    eq(tapped.getDouble("qualifiedOpenAnchorCapEv"),.25,"tap epoch reacquires anchor without former allowance");
    seed(false);camera="new-camera";
    eq(step(RecordedAnchorFixture.recorded()).appliedEv,.25,"lens switch has no former allowance");
    camera="anchor-room";seed(false);mode=m.equals("PHOTO")?"MOTION":"PHOTO";
    eq(step(RecordedAnchorFixture.recorded()).appliedEv,.25,"mode switch has no former allowance");
   }
  }
  System.out.println("RECORDED_ANCHOR_ASSERTIONS "+checks+" PASS");
 }
}
