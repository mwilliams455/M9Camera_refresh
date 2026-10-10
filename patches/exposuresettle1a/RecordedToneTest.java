package com.particlesdevs.photoncamera.m9.preview;
import java.nio.file.*;
import org.json.*;
public final class RecordedToneTest {
 static int checks;
 static void yes(boolean b,String why){checks++;if(!b)throw new AssertionError(why);}
 public static void main(String[] args)throws Exception{
  JSONArray rows=new JSONArray(Files.readString(Path.of(args[0]))),out=new JSONArray();
  JSONObject first=rows.getJSONObject(0);long start=first.getLong("sample");
  M9PreviewToneContinuity1A c=new M9PreviewToneContinuity1A();
  // Explicit warm-up to observed initial tone. No claim that this missing prehistory occurred.
  for(int i=12;i>0;i--)c.update("2|PHOTO",start-i*250_000_000L+1,start-i*250_000_000L,
      first.getDouble("energy"),first.getDouble("auto"),0,first.getDouble("oldApplied"),true,true);
  double prior=c.appliedEv(),maxStep=0;int held=0;
  for(int i=0;i<rows.length();i++){
   JSONObject r=rows.getJSONObject(i);
   double v=c.update("2|PHOTO",r.getLong("now"),r.getLong("sample"),r.getDouble("energy"),
       r.getDouble("auto"),0,r.getDouble("requested"),true,r.getBoolean("paired"));
   maxStep=Math.max(maxStep,Math.abs(v-prior));
   if(!r.getBoolean("paired")){
    yes(c.reason().equals("held_tone_metadata_gap"),"recorded brief gap retains qualified tone");
    yes(Math.abs(v-prior)<1e-9,"recorded gap does not reset gain");held++;
   }
   yes(v>=-.5&&v<=.5,"tone remains bounded");
   out.put(new JSONObject().put("relativeMs",(r.getLong("now")-start)/1e6)
       .put("parentEv",r.getDouble("oldApplied")).put("candidateEv",v).put("reason",c.reason()));
   prior=v;
  }
  yes(held==4,"all four recorded metadata-gap transitions exercised");
  yes(maxStep<=.125000001,"recorded replay obeys existing maximum tone slew");
  System.out.println(new JSONObject().put("scope","tone-only replay with recorded parent Auto input and synthetic initial warm-up").put("heldGapRows",held).put("maximumStepEv",maxStep).put("rows",out));
  System.out.println("RECORDED_TONE_ASSERTIONS "+checks+" PASS");
 }
}
