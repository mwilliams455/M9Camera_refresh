import com.particlesdevs.photoncamera.m9.preview.*;
import com.particlesdevs.photoncamera.m9.render.M9R35Renderer;
import android.hardware.camera2.*;
import android.hardware.camera2.params.*;
import org.json.*;
import java.nio.file.*;
public class ContractTest {
 static int n;
 static void check(boolean v,String m){n++;if(!v)throw new AssertionError(m);}
 static float[] floats(JSONArray a){float[] v=new float[a.length()];for(int i=0;i<v.length;i++)v[i]=(float)a.getDouble(i);return v;}
 static TonemapCurve curve(float[] c){return new TonemapCurve(c,c,c);}
 static CaptureResult result(float[] c){
  CaptureResult r=new CaptureResult();r.put(CaptureResult.TONEMAP_MODE,0);r.put(CaptureResult.TONEMAP_CURVE,curve(c));
  r.put(CaptureResult.COLOR_CORRECTION_TRANSFORM,new ColorSpaceTransform());r.put(CaptureResult.COLOR_CORRECTION_GAINS,new RggbChannelVector());
  r.put(CaptureResult.SENSOR_NEUTRAL_COLOR_POINT,new android.util.Rational[]{new android.util.Rational(),new android.util.Rational(),new android.util.Rational()});
  r.put(CaptureResult.CONTROL_POST_RAW_SENSITIVITY_BOOST,100);return r;
 }
 public static void main(String[] args)throws Exception {
  for(int count:new int[]{16,32,64}) {
   float[] c=M9PreviewMath2A.srgbCurve(count);check(M9PreviewMath2A.validCurve(c),"valid request");
   for(int i=0;i<count;i++){
    check(Math.abs(c[2*i]-(double)i/(count-1))<1e-7,"uniform input position");
    check(Math.abs(M9PreviewMath2A.decode(c[2*i+1])-c[2*i])<1e-7,"sRGB output at each knot");
   }
   float[] indexLut=c.clone();for(int i=0;i<count;i++)indexLut[2*i]=(float)i/(count-1);
   check(M9PreviewMath2A.curveOutputError(c,indexLut)==0,"index-only LUT retains request");
   float[] resampled=new float[2*(count*2-1)];
   for(int i=0;i<resampled.length/2;i++){resampled[2*i]=(float)i/(count*2-2);resampled[2*i+1]=(float)M9PreviewMath2A.curveOutput(c,resampled[2*i]);}
   check(M9PreviewMath2A.curveOutputError(c,resampled)<1e-6,"equivalent resampled curve accepted");
   check(M9PreviewMath2A.curveOutputError(c,new float[]{0,0,1,1})>.25,"identity is a material mismatch");
  }
  float[] expected=M9PreviewMath2A.srgbCurve(64);
  JSONObject fixture=new JSONObject(Files.readString(Path.of(args[0])));
  float[] observed=floats(fixture.getJSONObject("sourceContract").getJSONArray("reportedToneCurveRgb2E").getJSONArray(0));
  check(M9PreviewMath2A.curveOutputError(expected,observed)>.28,"recorded telephoto contradiction detected");
  CameraCharacteristics chars=new CameraCharacteristics();chars.put(CameraCharacteristics.TONEMAP_MAX_CURVE_POINTS,64);chars.put(CameraCharacteristics.TONEMAP_AVAILABLE_TONE_MAP_MODES,new int[]{0});
  CaptureRequest.Builder b=new CaptureRequest.Builder();M9GpuPreview2A.configure(b,chars);
  check(b.get(CaptureRequest.TONEMAP_MODE)==0,"controlled mode requested");
  float[] submitted=new float[128];b.get(CaptureRequest.TONEMAP_CURVE).copyColorCurve(0,submitted,0);
  check(java.util.Arrays.equals(submitted,expected),"production builder sends uniform-input curve");
  CaptureResult mismatch=result(observed);
  M9GpuPreview2A.Frame bad=M9GpuPreview2A.from(chars,mismatch,"4");
  check(!bad.ready,"recorded telephoto contract rejected");
  check(bad.reason.equals("reported_curve_disagrees_with_request"),"explicit rejection reason");
  check(M9R35Renderer.calls==0,"mismatch bypasses sensor-to-M9 reconstruction");
  check(bad.diagnostics().getJSONArray("reportedToneCurveRgb2E").length()==3,"bad curves retained for evidence");
  check(bad.diagnostics().getJSONArray("requestedToneCurve2F").length()==128,"request retained for evidence");
  check(bad.diagnostics().getDouble("toneCurveMaxOutputError2F")>.28,"diagnostic error recorded");
  check(bad==M9GpuPreview2A.from(chars,mismatch,"4"),"stable mismatch cached");
  CaptureResult good=result(expected);
  M9GpuPreview2A.Frame accepted=M9GpuPreview2A.from(chars,good,"4");
  check(accepted.ready,"contract recovers after agreeing result");check(M9R35Renderer.calls==1,"native source context retained");
  check(accepted.diagnostics().getBoolean("toneCurveAgreement2F"),"agreement recorded");
  byte[] inverse=accepted.inverseTexture();inverse[0]=99;check(accepted.inverseTexture()[0]==0,"immutable cached inverse");
  // One bad colour channel must reject the whole contract, not tint the scene.
  CaptureResult mixed=result(expected);mixed.put(CaptureResult.TONEMAP_CURVE,new TonemapCurve(expected,observed,expected));
  check(!M9GpuPreview2A.from(chars,mixed,"4").ready,"green-only mismatch rejected");
  // A same-shaped LUT with ordinary < 3 code quantization remains usable.
  float[] quantized=expected.clone();for(int i=1;i<64;i++)quantized[2*i+1]=Math.round(expected[2*i+1]*1023)/1023f;
  check(M9GpuPreview2A.from(chars,result(quantized),"4").ready,"quantized curve accepted");
  check(!M9GpuPreview2A.from(null,good,"4").ready,"missing metadata still fails closed");
  check(M9PreviewMath2A.curveOutputError(expected,new float[]{0,0,1,Float.NaN})==Double.POSITIVE_INFINITY,"invalid curve cannot pass agreement");
  System.out.println("GL2F curve contract PASS: "+n+" assertions; actual recorded telephoto mismatch rejected; uniform-input and recovery checked");
 }
}
