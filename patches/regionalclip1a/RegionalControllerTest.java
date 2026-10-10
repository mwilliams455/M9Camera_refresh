package com.particlesdevs.photoncamera.m9.preview;
import org.json.*;
import com.particlesdevs.photoncamera.m9.preview.M9AutoExposure2D.*;

public final class RegionalControllerTest {
 static int checks;static long now=200_000_000_000L;
 static void yes(boolean b,String m){checks++;if(!b)throw new AssertionError(m);}
 static Decision next(Stats[] s,String camera,String mode,double energy,double ev,long shutter,int iso,boolean eligible){
  now+=250_000_000L;M9AutoExposure2D.publish(new Sample(camera,mode,now,now,now,energy,s));
  return M9AutoExposure2D.decide(camera,mode,now+1,energy,ev,shutter,iso,0,eligible);
 }
 static Decision next(Stats[] s){return next(s,"regional","PHOTO",1370000000,0,0,0,true);}
 public static void main(String[] args)throws Exception{
  boolean candidate=Boolean.parseBoolean(args[1]);RegionalFixture f=new RegionalFixture(args[0]);
  yes(M9AutoExposure2D.highlightRetentionLimit(f.boundary(false))==.5,"recorded before step accepted");
  yes(M9AutoExposure2D.highlightRetentionLimit(f.boundary(true))==.25,"recorded after step rejected");
  M9AutoExposure2D.reset();Decision d=null;
  for(int i=0;i<12;i++)d=next(f.boundary(false));
  yes(d.appliedEv==.5,"initial acquisition retained");
  int cuts=0,rises=0;double previous=d.appliedEv;
  for(int cycle=0;cycle<8;cycle++)for(int i=0;i<9;i++){
   d=next(f.boundary(i==0));if(d.appliedEv<previous)cuts++;if(d.appliedEv>previous)rises++;
   if(candidate)yes(d.appliedEv==.25,"borderline release cannot reopen same cut");previous=d.appliedEv;
  }
  yes(cuts==(candidate?1:8),"exact recurring-cut count");
  yes(rises==(candidate?0:8),"exact recurring-rise count");
  for(int i=0;i<12;i++)d=next(RegionalFixture.clear(f.boundary(false)));
  yes(d.appliedEv==.5,"genuinely clear evidence releases limit through existing rise policy");
  // The complete, unmodified shutter bracket keeps its established static cap.
  M9AutoExposure2D.reset();Stats[] actual=f.shutter();
  for(int i=0;i<12;i++)d=next(actual);
  JSONObject staticDiag=new JSONObject(d.diagnostics);
  yes(staticDiag.getDouble("highlightRetentionLimitEv")==M9AutoExposure2D.highlightRetentionLimit(actual),"recorded static headroom retained");
  double staticEv=d.appliedEv;
  if(candidate){
   for(int boundary=0;boundary<7;boundary++){
    M9AutoExposure2D.reset();for(int i=0;i<5;i++)next(f.boundary(true));
    switch(boundary){
     case 0:next(f.boundary(false),"regional","PHOTO",1370000000,.3,0,0,true);break;
     case 1:next(f.boundary(false),"regional","PHOTO",1370000000,0,10000000,0,true);break;
     case 2:next(f.boundary(false),"regional","PHOTO",1370000000,0,0,100,true);break;
     case 3:next(f.boundary(false),"regional","PHOTO",1370000000,0,0,0,false);break;
     case 4:M9AutoExposure2D.invalidate("test_surface_loss");break;
     case 5:next(f.boundary(false),"other_camera","PHOTO",1370000000,0,0,0,true);break;
     case 6:next(f.boundary(false),"regional","MOTION",1370000000,0,0,0,true);break;
    }
    d=next(f.boundary(false));JSONObject o=new JSONObject(d.diagnostics);
    yes(o.getDouble("qualifiedRegionalClipCapEv")>=.5,"boundary clears prior regional state "+boundary);
   }
   // Export includes immutable per-step masks and an independent raw cap.
   M9AutoExposure2D.reset();next(f.boundary(true));d=next(f.boundary(false));
   JSONObject row=M9MeterDecisionHistory1A.range(now,now+2,"regional").getJSONObject("auto").getJSONArray("rows").getJSONObject(0);
   JSONObject e=row.getJSONObject("highlightEvidence");
   yes(e.getDouble("safeEv")==.5&&e.getDouble("qualifiedRegionalClipCapEv")==.25,"raw and qualified caps distinguishable");
   yes(e.getJSONArray("regionalClipHeldMasksByStep").getInt(2)==((1<<9)|(1<<10)),"recorded offending fields retained");
   String frozen=e.toString();next(RegionalFixture.clear(f.boundary(false)));
   yes(M9MeterDecisionHistory1A.range(now-250000000L,now-250000000L+2,"regional").getJSONObject("auto").getJSONArray("rows").getJSONObject(0).getJSONObject("highlightEvidence").toString().equals(frozen),"history remains immutable after release");
  }
  System.out.println(new JSONObject().put("assertions",checks).put("candidate",candidate).put("cuts",cuts).put("rises",rises).put("unmodifiedShutterBracketAutoEv",staticEv).put("scope","recorded base/+0.50 pairs with explicitly synthetic other steps and repeated timing"));
 }
}
