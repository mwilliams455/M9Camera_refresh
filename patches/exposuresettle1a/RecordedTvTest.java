package com.particlesdevs.photoncamera.m9.preview;
import org.json.*;
import com.particlesdevs.photoncamera.m9.preview.M9AutoExposure2D.*;
public final class RecordedTvTest {
 static int checks;
 static void yes(boolean b,String why){checks++;if(!b)throw new AssertionError(why);}
 public static void main(String[] args)throws Exception{
  long n=100_000_000_000L;Stats[] s=RecordedTvFixture.recorded();
  for(String mode:new String[]{"PHOTO","MOTION"}){
   M9AutoExposure2D.reset();Decision d=null;
   for(int i=0;i<12;i++){
    n+=250_000_000;M9AutoExposure2D.publish(new Sample("TV",mode,n,n,n,1990000020,s));
    d=M9AutoExposure2D.decide("TV",mode,n+1,1990000020,0,0,0,.2963683992380817,true);
   }
   JSONObject diag=new JSONObject(d.diagnostics);
   yes(d.appliedEv==1,"recorded stable placement retained");
   yes(diag.getDouble("highlightRetentionLimitEv")==1,"recorded highlight allowance unchanged");
   JSONObject row=M9MeterDecisionHistory1A.range(n,n+2,"TV").getJSONObject("auto").getJSONArray("rows").getJSONObject(0);
   JSONObject h=row.getJSONObject("highlightEvidence");
   yes(h.getDouble("safeEv")==1&&h.getDouble("firstRejectedEv")==1.25,"first failed highlight step retained");
   yes(h.getString("stopReason").equals("regional_channel_clip_growth"),"exact stop reason retained");
   yes(!h.getBoolean("subjectHighlightEligible")&&h.getInt("proposedBodyMask")==0,"whole-scene ownership explained");
   JSONArray base=h.getJSONObject("base").getJSONArray("fieldClipFraction");
   JSONArray rejected=h.getJSONObject("firstRejected").getJSONArray("fieldClipFraction");
   yes(base.getDouble(11)==s[0].fieldClipped[11]&&rejected.getDouble(11)==s[5].fieldClipped[11],"regional evidence retained exactly");
   yes(base.getDouble(15)==s[0].fieldClipped[15]&&rejected.getDouble(15)==s[5].fieldClipped[15],"second implicated field retained exactly");
  }
  System.out.println("RECORDED_TV_ASSERTIONS "+checks+" PASS");
 }
}
