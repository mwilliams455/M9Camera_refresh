import android.opengl.GLES30;
import android.os.SystemClock;
import com.particlesdevs.photoncamera.m9.preview.*;

/** Executes real scheduling, sample, poll, tone eligibility and tone math. */
public class ProbeTest {
 static int checks;
 static void check(boolean b,String msg){checks++;if(!b)throw new AssertionError(msg);}
 static M9PreviewFrameState1W frame(long now){
  M9PreviewFrameState1W s=new M9PreviewFrameState1W();s.resultTimestampNs=now;return s;
 }
 static String scenario(String label,long frameMs,long latencyMs,boolean candidate,boolean manual){
  GLES30.reset(latencyMs*1000000L);
  M9AutoExposure2D.publications=0;
  M9PreviewMeter2D meter=new M9PreviewMeter2D();M9PreviewEvidence2E tone=new M9PreviewEvidence2E();
  float gain=1,maxGain=1;int unityAfterLift=0;M9PreviewFrameState1W f=null;
  for(int i=0;i<80;i++){
   SystemClock.now=1000000000L+i*frameMs*1000000L;f=frame(SystemClock.now);
   if(manual)f.plan.userEv=-.7;
   gain=ProductionSchedule.draw(meter,tone,f,SystemClock.now);
   if(maxGain>1&&gain==1)unityAfterLift++;
   maxGain=Math.max(maxGain,gain);
   check(GLES30.active()<=1,"readbacks overlap");
  }
  check(GLES30.maxInFlight==1,"at most one readback");
  boolean starvation=!manual&&(frameMs>=250||latencyMs>=250);
  if(starvation&&!candidate){check(GLES30.toneReads==0,"baseline starvation must reproduce");check(gain==1,"starved tone remains unity");}
  else {check(GLES30.toneReads>5,"tone must progress");
   if(frameMs<=250&&latencyMs<250)check(gain>1.3,"tone reaches unchanged target");
   else {check(maxGain>1,"fresh tone can apply");
    if(frameMs>250)check(unityAfterLift>0,"existing stale-evidence reset remains intact");}
  }
  if(!manual)check(M9AutoExposure2D.publications>5,"Auto must continue");
  else check(GLES30.autoReads==0,"manual EV still bypasses Auto probe");
  if(candidate||!starvation){
   float before=gain;
   for(int i=0;i<10;i++)check(tone.predictedTc20Gain(f)==before,"same sample cannot slew repeatedly");
   f=frame(SystemClock.now);
   f.plan.cameraId="other";check(tone.predictedTc20Gain(f)==1,"foreign camera resets tone");
   f.plan.cameraId="0";f.plan.mode="MOTION";check(tone.predictedTc20Gain(f)==1,"foreign mode resets tone");
   f.plan.mode="PHOTO";f.source2A.continuityHeld=true;
   check(tone.predictedTc20Gain(f)<=1,"held source cannot authorize positive gain");
   SystemClock.now+=3000000000L;f=frame(SystemClock.now);
   check(tone.predictedTc20Gain(f)==1,"stale evidence resets to unity");
  }
  return "{\"case\":\""+label+"\",\"autoSubmissions\":"+GLES30.autoReads+
    ",\"toneSubmissions\":"+GLES30.toneReads+",\"lastToneGain\":"+gain+
    ",\"maxToneGain\":"+maxGain+",\"staleUnityFramesAfterLift\":"+unityAfterLift+"}";
 }
 static void stalled(boolean badMap){
  GLES30.reset(badMap?0:3000000000L);
  M9PreviewMeter2D meter=new M9PreviewMeter2D();M9PreviewEvidence2E tone=new M9PreviewEvidence2E();
  SystemClock.now=1000000000L;ProductionSchedule.draw(meter,tone,frame(SystemClock.now),SystemClock.now);
  GLES30.invalidMap=badMap;
  for(int i=1;i<=20;i++){
   SystemClock.now=1000000000L+i*100000000L;
   ProductionSchedule.draw(meter,tone,frame(SystemClock.now),SystemClock.now);
   check(GLES30.active()<=1,"pending fence cannot overlap");
   if(!badMap&&i<=12)check(GLES30.toneReads==0,"pending fence blocks tone");
  }
  SystemClock.now=3700000000L;
  ProductionSchedule.draw(meter,tone,frame(SystemClock.now),SystemClock.now);
  check(GLES30.maxInFlight<=1,"failure cleanup does not overlap");
  check(GLES30.autoReads==1,"failed meter does not resubmit");
 }
 public static void main(String[] args){
  boolean c=args[0].equals("candidate");StringBuilder out=new StringBuilder("{\"scenarios\":[");
  out.append(scenario("30fps",33,0,c,false)).append(',');
  out.append(scenario("10fps",100,0,c,false)).append(',');
  out.append(scenario("4fps",250,0,c,false)).append(',');
  out.append(scenario("slow_350ms",350,0,c,false)).append(',');
  out.append(scenario("gpu_300ms",100,300,c,false)).append(',');
  out.append(scenario("manual_ev",250,0,c,true));
  stalled(false);stalled(true);
  System.out.println(out.append("],\"checks\":").append(checks).append('}'));
 }
}
