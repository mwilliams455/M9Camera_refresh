import com.particlesdevs.photoncamera.m9.*;
import com.particlesdevs.photoncamera.m9.preview.*;
import org.json.*;

public class AtomicFrameTest {
    static int checks;
    static void check(boolean ok,String why){checks++;if(!ok)throw new AssertionError(why);}
    static void near(double a,double b,String why){check(Math.abs(a-b)<1e-6,why+" "+a+" "+b);}
    static M9ExposurePlan1A plan(long id,String camera,String mode,double ev){
        return new M9ExposurePlan1A(id,1000,900,camera,mode,50,2000000,
                50,2000000,50,4000000,ev,0,"neutral",0,0,100);
    }
    public static void main(String[] args)throws Exception {
        M9ExposurePlan1A p=plan(1,"2","PHOTO",1),q=plan(2,"2","PHOTO",2);
        float[] stats={10,88,250,255,148,.3f,.16f,.10f,1,0,88,250,255,148,.3f,.16f,.1f,0,15,187};
        M9PreviewFrameState1W a=new M9PreviewFrameState1W(p,900,950000000,2,.2f,.3f,-1.007f,0,1.211f,1,stats);
        M9PreviewFrameState1W b=new M9PreviewFrameState1W(q,1000,990000000,4,.8f,.7f,-.3f,.1f,1.12f,.2f,stats);
        RendererProbe r=new RendererProbe();
        check(!new JSONObject(r.snapshotM9DrawState1W(1000000000,p)).getBoolean("available"),"initial draw unavailable");
        r.setM9FrameState1W(a);
        // A camera callback publishes a full different state during actual glUniform calls.
        GLES20.hook=()->r.setM9FrameState1W(b);
        r.onDrawFrame(null);
        near(GLES20.uniforms.get(RendererProbe.uM9ExposureScale1B),2,"draw retains exposure");
        near(GLES20.uniforms.get(RendererProbe.uM9PreviewGainEv1F),a.gainEv,"draw retains gain");
        near(GLES20.uniforms.get(RendererProbe.uM9MidtoneGamma1F),a.gamma,"draw retains gamma");
        near(GLES20.uniforms.get(RendererProbe.uM9HighlightShoulder1F),1,"draw retains pair gate");
        near(GLES20.uniforms.get(RendererProbe.uM9IlluminantWeightA1D),.2,"draw retains illuminant");
        near(GLES20.uniforms.get(RendererProbe.uM9TungstenWeight1D),.3,"draw retains tungsten");
        check(r.mM9LastDraw1W.state==a,"record describes drawn state, not newly published state");
        stats[1]=255;
        String frozen=r.snapshotM9DrawState1W(1010000000,p);
        JSONObject s=new JSONObject(frozen);
        near(s.getJSONArray("toneInputStats").getDouble(1),88,"stats copied at publication");
        check(s.getBoolean("textureMatchesStateResult"),"exact timestamp match recorded");
        check(s.getBoolean("samePlanId")&&s.getBoolean("sameCameraAndMode"),"matching capture identity");
        near(s.getDouble("drawAgeMsAtShutter"),10,"monotonic age");
        check(s.getString("stage").contains("not_display_presentation_verified"),"no false presentation claim");
        check(!s.getBoolean("curve02Live")&&!s.getBoolean("sat2Live"),"actual GL colour boundary");
        M9ExposurePlan1A tagged=p.withShutterPreviewSnapshot1W(frozen);
        check(p.getShutterPreviewSnapshot1W()==null,"live plan unmodified");
        check(tagged.id==p.id&&tagged.iso==p.iso&&tagged.exposureNs==p.exposureNs,"tag preserves exposure identity");
        near(tagged.previewScale(),p.previewScale(),"preview scale unchanged");
        near(tagged.renderIntentScale(50,4000000),2,"render intent unchanged");
        check(tagged.matches("2","PHOTO",1100,1,0,0),"freshness unchanged");
        JSONObject out=M9ExposurePlanDiagnostics1A.toJson(tagged);
        check(out.getJSONObject("shutterPreview1W").getLong("statePlanId")==1,"main diagnostic includes snapshot");
        out.getJSONObject("shutterPreview1W").put("statePlanId",999);
        check(M9ExposurePlanDiagnostics1A.toJson(tagged).getJSONObject("shutterPreview1W").getLong("statePlanId")==1,"JSON consumers cannot mutate tag");
        r.onDrawFrame(null);
        near(GLES20.uniforms.get(RendererProbe.uM9ExposureScale1B),4,"next draw uses new exposure");
        near(GLES20.uniforms.get(RendererProbe.uM9MidtoneGamma1F),b.gamma,"next draw uses new gamma");
        check(!new JSONObject(r.snapshotM9DrawState1W(1010000000,q)).getBoolean("textureMatchesStateResult"),"timestamp mismatch is explicit");
        check(new JSONObject(tagged.getShutterPreviewSnapshot1W()).getLong("statePlanId")==1,"later draws cannot replace shutter evidence");
        check(!new JSONObject(r.snapshotM9DrawState1W(1010000000,p)).getBoolean("samePlanId"),"capture/preview plan mismatch visible");
        check(!new JSONObject(r.snapshotM9DrawState1W(1010000000,plan(9,"1","MOTION",0))).getBoolean("sameCameraAndMode"),"lens/mode mismatch visible");
        check(!new JSONObject(r.snapshotM9DrawState1W(4000000000L,q)).getBoolean("recentDraw"),"stale draw reported");
        check(!new JSONObject(r.snapshotM9DrawState1W(990000000,q)).getBoolean("recentDraw"),"draw newer than shutter not labelled current");
        r.mGLInit=false;long sequence=r.mM9LastDraw1W.sequence;r.onDrawFrame(null);
        check(r.mM9LastDraw1W.sequence==sequence,"no synthetic record without GL init");
        M9PreviewFrameState1W invalid=new M9PreviewFrameState1W(null,-1,-1,Float.NaN,Float.NaN,Float.NaN,Float.NaN,Float.NaN,Float.NaN,Float.NaN,new float[]{Float.NaN});
        near(invalid.exposureScale,1,"invalid exposure fallback");near(invalid.gainEv,-.3,"invalid gain fallback");
        near(invalid.gamma,1.12,"invalid gamma fallback");near(invalid.pairStrength,.2,"invalid pair fallback");
        check(new JSONObject(new M9PreviewFrameState1W.Draw(invalid,-1,1,1,false).snapshot(2,null)).getJSONArray("toneInputStats").isNull(0),"nonfinite stat becomes null");
        M9PreviewFrameState1W clamped=new M9PreviewFrameState1W(null,-1,-1,100,2,-2,-100,100,100,-1,null);
        near(clamped.exposureScale,16,"exposure bound");near(clamped.gainEv,-2.4,"gain bound");
        near(clamped.gamma,1.4,"gamma bound");near(clamped.shadowPlacement,.12,"shadow bound");
        near(clamped.pairStrength,0,"pair bound");near(clamped.weightA,1,"illuminant bound");
        near(clamped.tungstenWeight,0,"tungsten bound");
        check(!M9ExposurePlanDiagnostics1A.toJson(p.withShutterPreviewSnapshot1W("not JSON")).getJSONObject("shutterPreview1W").getBoolean("available"),"bad diagnostic cannot abort exposure JSON");
        System.out.println("M9LIVEGL1W: "+checks+" assertions PASS");
    }
}
