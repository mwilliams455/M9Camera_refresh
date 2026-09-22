import android.hardware.camera2.*;
import android.os.SystemClock;
import com.particlesdevs.photoncamera.m9.preview.M9RootCauseTrace1A;
import org.json.*;
public class TraceTest {
 static void check(boolean v,String s){if(!v)throw new AssertionError(s);}
 public static void run()throws Exception {
  CaptureRequest request=new CaptureRequest();request.put(CaptureRequest.CONTROL_AF_TRIGGER,1);
  TotalCaptureResult logical=new TotalCaptureResult();logical.put(CaptureResult.SENSOR_TIMESTAMP,123L);logical.put(CaptureResult.SENSOR_SENSITIVITY,999);
  CaptureResult physical=new CaptureResult();physical.put(CaptureResult.SENSOR_TIMESTAMP,456L);physical.put(CaptureResult.SENSOR_SENSITIVITY,100);
  logical.physical.put("4",physical);SystemClock.now=1000000000L;
  M9RootCauseTrace1A.observe(request,logical,"0-4",2);
  JSONObject snap=M9RootCauseTrace1A.snapshot(SystemClock.now,"0-4");JSONArray row=snap.getJSONArray("rows").getJSONArray(0);
  check(row.getLong(1)==456&&row.getInt(3)==100,"physical result authority");check(row.isNull(5),"absent focus is null, not zero");
  check(row.length()==snap.getJSONArray("columns").length(),"columns match values");
  M9RootCauseTrace1A.observe(request,logical,"0-4",2);check(M9RootCauseTrace1A.snapshot(SystemClock.now,"0-4").getJSONArray("rows").length()==1,"duplicate excluded");
  check(!M9RootCauseTrace1A.snapshot(SystemClock.now,"5").getBoolean("available"),"camera isolation");
  check(!M9RootCauseTrace1A.snapshot(0,"0-4").getBoolean("available"),"no future metadata");
  for(int i=0;i<1900;i++){SystemClock.now+=1000000L;physical.put(CaptureResult.SENSOR_TIMESTAMP,500L+i);M9RootCauseTrace1A.observe(request,logical,"0-4",i%3);}
  check(M9RootCauseTrace1A.snapshot(SystemClock.now,"0-4").getJSONArray("rows").length()==1800,"capacity enforced");
  check(!M9RootCauseTrace1A.snapshot(SystemClock.now+31000000000L,"0-4").getBoolean("available"),"30 second window enforced");
  check(request.get(CaptureRequest.CONTROL_AF_TRIGGER)==1,"request untouched");
  M9RootCauseTrace1A.observe(request,logical,"7",0);check(M9RootCauseTrace1A.snapshot(SystemClock.now,"7").getJSONArray("rows").length()==1,"camera switch resets history");
  System.out.println("M9ROOTCAUSE1A metadata PASS: physical selection, nulls, timestamp filtering, bounds, camera isolation, read-only requests");
 }
}
