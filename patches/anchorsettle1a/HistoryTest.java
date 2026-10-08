package com.particlesdevs.photoncamera.m9.preview;
import org.json.*;
import com.particlesdevs.photoncamera.m9.preview.M9AutoExposure2D.*;
public final class HistoryTest {
 static int checks;
 static void yes(boolean b,String message){checks++;if(!b)throw new AssertionError(message);}
 static JSONObject stream(String key,long start,long end,String camera)throws Exception{
  // Exercise actual serialization and parse, including null for non-finite evidence.
  return new JSONObject(M9MeterDecisionHistory1A.range(start,end,camera).toString()).getJSONObject(key);
 }
 public static void main(String[] args)throws Exception{
  long n=30_000_000_000L;Stats[] scene=RecordedAnchorFixture.recorded();
  M9AutoExposure2D.reset();
  M9AutoExposure2D.publish(new Sample("integration","PHOTO",n,n,n,1,scene));
  for(int i=0;i<100;i++)M9AutoExposure2D.decide("integration","PHOTO",n+1+i,1,0,0,0,0,true);
  yes(stream("auto",n,n+1000,"integration").getInt("rowCount")==1,"one accepted probe, not one row per callback");
  JSONObject auto=stream("auto",n,n+1000,"integration").getJSONArray("rows").getJSONObject(0);
  yes(auto.getDouble("openAnchorLimitEv")==.25&&auto.getDouble("qualifiedOpenAnchorCapEv")==.25,"raw and qualified anchor caps have separate columns");
  yes(auto.getInt("rawOpenAnchorMask")==49152&&auto.getInt("qualifiedOpenAnchorMask")==49152,"anchor masks serialize from production decision");
  yes(auto.getInt("openAnchorQualificationConfirmations")==0,"anchor confirmation column maps correctly");
  yes(auto.getString("reason").contains("anchor_acquired_current_body"),"history explains anchor qualification state");
  for(int i=0;i<100;i++)M9AutoExposure2D.decide("integration","PHOTO",n+1001+i,1,0,1000,0,0,true);
  yes(stream("auto",n,n+2000,"integration").getInt("rowCount")==2,"manual transition recorded once despite unconsumed probe");
  for(int i=0;i<100;i++)M9AutoExposure2D.decide("integration","PHOTO",n+2_000_000_000L+i,1,0,0,0,0,true);
  yes(stream("auto",n,n+3_000_000_000L,"integration").getInt("rowCount")==3,"unavailable transition recorded once");
  for(int i=0;i<1000;i++) {
   double[] values=new double[26];values[0]=i;values[1]=Double.NaN;
   M9MeterDecisionHistory1A.auto(i%2==0?"A":"B","PHOTO",i,i-1,i-2,i-3,"scalar_fixture",values);
   M9MeterDecisionHistory1A.tone("A","PHOTO",i,i-1,i-2,i-3,"fresh_neutral_probe",0,1,.99,.125,.125,.04);
  }
  JSONObject all=stream("auto",0,2000,"A"),tone=stream("tone",0,2000,"A");
  yes(all.getInt("capacity")==128&&all.getInt("rowCount")==64,"bounded Auto history and exact camera filter");
  yes(all.getLong("evictedRowsLifetime")==875,"history reports evictions, including three controller rows");
  JSONArray rows=all.getJSONArray("rows");
  yes(rows.getJSONObject(0).getLong("decisionElapsedNs")==872,"oldest retained sample after ring wrap");
  yes(rows.getJSONObject(63).getLong("decisionElapsedNs")==998,"newest retained Auto sample");
  yes(rows.getJSONObject(0).isNull("rawBackgroundCapEv"),"non-finite scalar serialized as JSON null");
  yes(rows.getJSONObject(0).getDouble("backgroundScore")==872,"column mapping retains scalar values");
  yes(stream("auto",900,910,"A").getInt("rowCount")==6,"inclusive exact temporal window");
  yes(!stream("auto",0,2000,"foreign").getBoolean("available"),"foreign camera excluded");
  yes(tone.getInt("rowCount")==128&&tone.getLong("evictedRowsLifetime")==872,"tone history independently bounded");
  JSONObject last=tone.getJSONArray("rows").getJSONObject(127);
  yes(last.getLong("sampleSubmittedNs")==998&&last.getDouble("appliedEv")==.125,"tone rows preserve provenance and actual applied gain in EV");
  System.out.println("HISTORY_ASSERTIONS "+checks+" PASS");
 }
}
