import com.particlesdevs.photoncamera.m9.M9ExposurePlan1A;
import com.particlesdevs.photoncamera.m9.preview.*;
import java.lang.reflect.Field;
import java.util.concurrent.atomic.AtomicReference;

public class FrameHistoryTest {
    static int checks;
    static final long T=1_000_000_000L;
    static void check(boolean value,String message) {
        checks++; if(!value) throw new AssertionError(message);
    }
    static M9ExposurePlan1A plan(long ts,int iso,long time,int intendedIso,long intendedTime) {
        return new M9ExposurePlan1A(ts,1000,ts,"0","MOTION",iso,time,100,10_000_000L,
                intendedIso,intendedTime,0,0,"test",0,0,100)
                .withAutoIsoControls("cap3200").withAeLockState(1,0);
    }
    static M9PreviewFrameState1W state(M9ExposurePlan1A p,boolean ready,boolean held,String camera) {
        return new M9PreviewFrameState1W(p,p.sensorTimestampNs,0,(float)p.previewScale(),
                0,0,0,0,1,0,null,new M9GpuPreview2A.Frame(ready,held,camera));
    }
    static M9PreviewFrameState1W state(long ts,int iso) {
        return state(plan(ts,iso,10_000_000L,800,10_000_000L),true,false,"0");
    }
    static M9ExposurePlan1A control(M9ExposurePlan1A p,int change) {
        return new M9ExposurePlan1A(p.id,p.createdMs,p.sensorTimestampNs,
                change==0?"1":p.cameraId,change==1?"PHOTO":change==8?"NIGHT":p.mode,
                p.observedIso,p.observedExposureNs,p.referenceIso,p.referenceExposureNs,
                p.iso,p.exposureNs,change==2?-.7:p.userEv,p.autoEv,p.autoReason,
                change==3?20_000_000L:p.manualExposureNs,change==4?400:p.manualIso,100)
                .withAutoIsoControls(change==5?"cap1200":p.getAutoIsoControlsIdentity())
                .withAeLockState(change==6?2:p.aeLockGeneration,change==7?123:p.aeLockSourcePlanId);
    }
    static void boundaries() throws Exception {
        M9PreviewFrameHistory1A h=new M9PreviewFrameHistory1A();
        check(h.forTexture(T,T).plan==null,"empty has no capture authority");
        M9PreviewFrameState1W old=state(T,100), latest=state(T+50_000_000L,200);
        h.publish(old,T);h.publish(latest,T+50_000_000L);
        check(h.forTexture(T,T+50_000_000L)==old,"exact history paired");
        check(h.forTexture(latest.resultTimestampNs,T+50_000_000L)==latest,"latest exact unchanged");
        check(h.forTexture(T+1,T+50_000_000L)==latest,"no nearest-neighbour guess");
        check(h.forTexture(0,T+50_000_000L)==latest,"unknown texture preserves fallback");
        check(h.forTexture(T,T+150_000_000L)==old,"150ms boundary");
        check(h.forTexture(T,T+150_000_001L)==latest,"expired history refused");
        check(h.forTexture(T,T-1)==latest,"clock reversal refused");
        h.publish(state(T+150_000_001L,400),T+50_000_001L);
        check(h.forTexture(T,T+60_000_000L)!=old,"sensor lag is independently bounded");
        h.clear();h.publish(latest,T);h.publish(old,T+1);
        check(h.forTexture(latest.resultTimestampNs,T+2)==old,"future metadata refused");
        h.clear();h.publish(old,T);h.publish(latest,T+1);
        M9PreviewFrameState1W duplicate=state(T,400);
        h.publish(duplicate,T+2);h.publish(latest,T+3);
        check(h.forTexture(T,T+4)==duplicate,"newest matching publication wins");
        h.publish(null,T+5);
        check(h.forTexture(T,T+6)==duplicate,"null publication no change");
        h.publish(M9PreviewFrameState1W.defaults(),T+7);
        check(h.forTexture(T,T+8).plan==null,"null plan clears history");
        h.publish(old,T);h.clear();
        check(h.forTexture(T,T+1).plan==null,"surface reset removes capture authority");
        for(int i=0;i<40;i++)h.publish(state(T+i,100+i),T+i);
        check(h.forTexture(T,T+41).resultTimestampNs==T+39,"capacity evicts old frames");
        Field f=M9PreviewFrameHistory1A.class.getDeclaredField("frames");f.setAccessible(true);
        check(((Object[])f.get(h)).length==16,"bounded retention");
    }
    static void contexts() {
        for(int change=0;change<9;change++) {
            M9PreviewFrameHistory1A h=new M9PreviewFrameHistory1A();
            M9PreviewFrameState1W old=state(T,100);
            M9ExposurePlan1A current=control(plan(T+1,200,10_000_000L,800,10_000_000L),change);
            M9PreviewFrameState1W latest=state(current,true,false,current.cameraId);
            h.publish(old,T);h.publish(latest,T+1);
            check(h.forTexture(T,T+2)==latest,"control transition "+change);
            M9PreviewFrameState1W back=state(T+3,300);h.publish(back,T+3);
            check(h.forTexture(T,T+4)==back,"returning context cannot resurrect old state "+change);
        }
        for(int change=0;change<3;change++) {
            M9PreviewFrameHistory1A h=new M9PreviewFrameHistory1A();
            M9PreviewFrameState1W old=state(T,100), latest=state(
                    plan(T+1,200,10_000_000L,800,10_000_000L),change!=0,change==1,change==2?"1":"0");
            h.publish(old,T);h.publish(latest,T+1);
            check(h.forTexture(T,T+2)==latest,"current source guard retained "+change);
        }
        M9PreviewFrameHistory1A h=new M9PreviewFrameHistory1A();
        M9PreviewFrameState1W old=state(control(plan(T,100,10_000_000L,800,10_000_000L),8),true,false,"0");
        M9PreviewFrameState1W latest=state(control(plan(T+1,200,10_000_000L,800,10_000_000L),8),true,false,"0");
        h.publish(old,T);h.publish(latest,T+1);
        check(h.forTexture(T,T+2)==latest,"unsupported modes keep existing selection");
    }
    static void brightness() {
        double worstParentError=0,worstCandidateError=0;
        int cases=0;
        for(String mode:new String[]{"PHOTO","MOTION"})
        for(int iso:new int[]{100,200,400,800})
        for(long time:new long[]{5_000_000L,10_000_000L,20_000_000L})
        for(double ratio:new double[]{.25,.5,1,2,4}) {
            M9ExposurePlan1A a=plan(T,iso,time,800,10_000_000L);
            M9ExposurePlan1A b=plan(T+50_000_000L,(int)(iso*ratio),time,800,10_000_000L);
            if(mode.equals("PHOTO")){a=control(a,1);b=control(b,1);}
            M9PreviewFrameState1W old=state(a,true,false,"0"), latest=state(b,true,false,"0");
            M9PreviewFrameHistory1A h=new M9PreviewFrameHistory1A();h.publish(old,T);h.publish(latest,T+50_000_000L);
            M9PreviewFrameState1W selected=h.forTexture(T,T+60_000_000L);
            double expected=M9ExposurePlan1A.energy(a.iso,a.exposureNs);
            double sample=M9ExposurePlan1A.energy(a.observedIso,a.observedExposureNs);
            // Isolated linear exposure stage, not a JPEG/colour rendering simulation.
            double parentError=Math.abs(Math.log(sample*latest.exposureScale/expected)/Math.log(2));
            double candidateError=Math.abs(Math.log(sample*selected.exposureScale/expected)/Math.log(2));
            // Ignore clamped test combinations; the pairing must still be exact.
            check(selected==old,"same source and exposure state for both modes");
            if(a.previewScale()>=.0625&&a.previewScale()<=16&&b.previewScale()>=.0625&&b.previewScale()<=16){
                check(candidateError<1e-6,"no false exposure jump");cases++;
                worstParentError=Math.max(worstParentError,parentError);
                worstCandidateError=Math.max(worstCandidateError,candidateError);
            }
        }
        check(worstParentError>=1.99,"parent mismatch visibly reproduces");
        System.out.println("{\"linearExposureCases\":"+cases+",\"worstParentMismatchEv\":"+worstParentError+
                ",\"worstCandidateMismatchEv\":"+worstCandidateError+"}");
    }
    static void concurrent() throws Exception {
        M9PreviewFrameHistory1A h=new M9PreviewFrameHistory1A();
        AtomicReference<Throwable> failure=new AtomicReference<>();
        Runnable publish=()->{try{for(int i=0;i<5000;i++)h.publish(state(T+i,100+i%100),T+i);}catch(Throwable e){failure.set(e);}};
        Runnable draw=()->{try{for(int i=0;i<5000;i++){
            M9PreviewFrameState1W s=h.forTexture(T+i,T+i+1);
            if(s==null || (s.plan!=null&&s.plan.sensorTimestampNs!=s.resultTimestampNs))throw new AssertionError("torn frame");
        }}catch(Throwable e){failure.set(e);}};
        Thread a=new Thread(publish),b=new Thread(draw);a.start();b.start();a.join();b.join();
        check(failure.get()==null,"concurrent publication/selection remains atomic: "+failure.get());
    }
    public static void main(String[] args) throws Exception {
        boundaries();contexts();brightness();concurrent();
        System.out.println("{\"assertions\":"+checks+",\"status\":\"PASS\"}");
    }
}
