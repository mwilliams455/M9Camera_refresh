package com.particlesdevs.photoncamera.m9.preview;

import android.opengl.GLES30;
import android.os.SystemClock;
import com.particlesdevs.photoncamera.m9.M9ExposurePlan1A;
import com.particlesdevs.photoncamera.util.Log;
import java.nio.Buffer;
import java.nio.ByteBuffer;

/**
 * Paired preview evidence plus preview-only negative TC20 prediction.
 * Never feeds Auto, capture allocation or the still renderer.
 */
public final class M9PreviewEvidence2E {
    public static final String LEGACY_EVIDENCE_REVISION="M9LIVEGL2E_PAIREDPIXELS";
    private static final long INTERVAL_NS=250000000L;
    private static final long FRESH_NS=1000000000L;
    private static final long RESULT_MATCH_NS=500000000L;
    private static final int W=32,H=24;
    private static final int STEPS=4,BYTES=W*H*STEPS*4;
    private static final int TC20_PANEL=3;

    private int framebuffer,texture,pbo;
    private long fence,lastProbeNs,pendingNs,pendingTextureNs;
    private M9PreviewFrameState1W pending;
    private boolean disabled;
    private int pendingDataSpace=-1;
    private float pendingReferenceScale;
    private volatile Evidence latest;
    private volatile String unavailableReason="awaiting_gpu_evidence";
    private long consumedTc20SampleNs=-1;
    private double appliedTc20Ev;
    private volatile float appliedTc20Gain=1.0f;

    /**
     * GL-thread call before the normal draw. Poll any finished probe, validate it
     * against the current camera/mode/result, then slew at most 0.25 EV/sample.
     */
    public float predictedTc20Gain(M9PreviewFrameState1W frame) {
        long now=SystemClock.elapsedRealtimeNanos();
        poll(now);
        Evidence e=latest;
        double target=0.0;
        boolean fresh=e!=null&&e.tc20.valid&&frame!=null&&frame.plan!=null
                &&e.state!=null&&e.state.plan!=null
                &&e.state.source2A!=null&&e.state.source2A.ready
                &&frame.plan.cameraId.equals(e.state.plan.cameraId)
                &&frame.plan.mode.equals(e.state.plan.mode)
                &&now>=e.submittedNs&&now-e.submittedNs<=FRESH_NS
                &&frame.resultTimestampNs>0&&e.state.resultTimestampNs>0
                &&Math.abs(frame.resultTimestampNs-e.state.resultTimestampNs)<=RESULT_MATCH_NS;
        if(fresh) {
            target=e.tc20.boundedEv;
            if(consumedTc20SampleNs!=e.submittedNs) {
                appliedTc20Ev=M9PreviewTc20Math1A.slewEv(appliedTc20Ev,target);
                consumedTc20SampleNs=e.submittedNs;
            }
        } else {
            // Fail open to unity; do not hold a darkening decision across stale or foreign frames.
            appliedTc20Ev=0.0;
            consumedTc20SampleNs=-1;
        }
        appliedTc20Gain=(float)Math.pow(2.0,appliedTc20Ev);
        return appliedTc20Gain;
    }

    public void sample(M9PreviewFrameState1W frame,long textureNs,android.graphics.SurfaceTexture surface,
            int exposureUniform,int peakUniform,int peakValue,int evidenceUniform,
            int tc20Uniform,float displayTc20Gain) {
        if(disabled)return;
        long now=SystemClock.elapsedRealtimeNanos();
        poll(now);
        M9ExposurePlan1A plan=frame.plan;
        if(disabled||fence!=0||now-lastProbeNs<INTERVAL_NS||plan==null
                ||!M9ExposurePlan1A.supportsMode1B(plan.mode)||textureNs<=0)return;
        double ratio=M9ExposurePlan1A.energy(plan.referenceIso,plan.referenceExposureNs)
                /M9ExposurePlan1A.energy(plan.observedIso,plan.observedExposureNs);
        if(!Double.isFinite(ratio)||ratio<=0)return;
        float referenceScale=(float)Math.max(.0625,Math.min(16,ratio));
        lastProbeNs=now;
        int[] viewport=new int[4],draw=new int[1],read=new int[1],pack=new int[1],active=new int[1],tex=new int[1];
        GLES30.glGetIntegerv(GLES30.GL_VIEWPORT,viewport,0);
        GLES30.glGetIntegerv(GLES30.GL_DRAW_FRAMEBUFFER_BINDING,draw,0);
        GLES30.glGetIntegerv(GLES30.GL_READ_FRAMEBUFFER_BINDING,read,0);
        GLES30.glGetIntegerv(GLES30.GL_PIXEL_PACK_BUFFER_BINDING,pack,0);
        GLES30.glGetIntegerv(GLES30.GL_ACTIVE_TEXTURE,active,0);
        GLES30.glActiveTexture(GLES30.GL_TEXTURE3);
        GLES30.glGetIntegerv(GLES30.GL_TEXTURE_BINDING_2D,tex,0);
        boolean scissor=GLES30.glIsEnabled(GLES30.GL_SCISSOR_TEST);
        try {
            for(int drain=0;drain<8&&GLES30.glGetError()!=GLES30.GL_NO_ERROR;drain++){}
            if(framebuffer==0)initialize();
            GLES30.glBindFramebuffer(GLES30.GL_FRAMEBUFFER,framebuffer);
            if(GLES30.glCheckFramebufferStatus(GLES30.GL_FRAMEBUFFER)!=GLES30.GL_FRAMEBUFFER_COMPLETE)
                throw new IllegalStateException("meter framebuffer incomplete");
            GLES30.glDisable(GLES30.GL_SCISSOR_TEST);
            GLES30.glUniform1i(peakUniform,0);
            for(int i=0;i<STEPS;i++){
                GLES30.glViewport(i*W,0,W,H);
                GLES30.glUniform1i(evidenceUniform,i==0?1:(i==TC20_PANEL?2:0));
                GLES30.glUniform1f(exposureUniform,i==1?referenceScale:frame.exposureScale);
                // Preserve old reference evidence at unity. Only the actual display panel
                // includes the current preview TC20 estimate. The TC20 probe is pre-curve.
                GLES30.glUniform1f(tc20Uniform,i==2?displayTc20Gain:1.0f);
                GLES30.glDrawArrays(GLES30.GL_TRIANGLE_STRIP,0,4);
            }
            GLES30.glBindBuffer(GLES30.GL_PIXEL_PACK_BUFFER,pbo);
            GLES30.glReadPixels(0,0,W*STEPS,H,GLES30.GL_RGBA,GLES30.GL_UNSIGNED_BYTE,0);
            fence=GLES30.glFenceSync(GLES30.GL_SYNC_GPU_COMMANDS_COMPLETE,0);
            if(fence==0||GLES30.glGetError()!=GLES30.GL_NO_ERROR)
                throw new IllegalStateException("meter readback failed");
            pending=frame;pendingNs=now;pendingTextureNs=textureNs;
            pendingReferenceScale=referenceScale;pendingDataSpace=-1;
            if(android.os.Build.VERSION.SDK_INT>=33&&surface!=null){
                try{pendingDataSpace=surface.getDataSpace();}catch(RuntimeException ignored){}
            }
            GLES30.glFlush();
        } catch(RuntimeException e){fail(e);}
        finally{
            GLES30.glBindFramebuffer(GLES30.GL_DRAW_FRAMEBUFFER,draw[0]);
            GLES30.glBindFramebuffer(GLES30.GL_READ_FRAMEBUFFER,read[0]);
            GLES30.glBindBuffer(GLES30.GL_PIXEL_PACK_BUFFER,pack[0]);
            GLES30.glBindTexture(GLES30.GL_TEXTURE_2D,tex[0]);
            GLES30.glActiveTexture(active[0]);
            GLES30.glViewport(viewport[0],viewport[1],viewport[2],viewport[3]);
            if(scissor)GLES30.glEnable(GLES30.GL_SCISSOR_TEST);
            GLES30.glUniform1i(evidenceUniform,0);
            GLES30.glUniform1f(exposureUniform,frame.exposureScale);
            GLES30.glUniform1f(tc20Uniform,displayTc20Gain);
            GLES30.glUniform1i(peakUniform,peakValue);
        }
    }

    private void initialize(){
        int[] id=new int[1];
        GLES30.glGenTextures(1,id,0);texture=id[0];
        GLES30.glBindTexture(GLES30.GL_TEXTURE_2D,texture);
        GLES30.glTexParameteri(GLES30.GL_TEXTURE_2D,GLES30.GL_TEXTURE_MIN_FILTER,GLES30.GL_NEAREST);
        GLES30.glTexParameteri(GLES30.GL_TEXTURE_2D,GLES30.GL_TEXTURE_MAG_FILTER,GLES30.GL_NEAREST);
        GLES30.glTexImage2D(GLES30.GL_TEXTURE_2D,0,GLES30.GL_RGBA8,W*STEPS,H,0,
                GLES30.GL_RGBA,GLES30.GL_UNSIGNED_BYTE,null);
        GLES30.glGenFramebuffers(1,id,0);framebuffer=id[0];
        GLES30.glBindFramebuffer(GLES30.GL_FRAMEBUFFER,framebuffer);
        GLES30.glFramebufferTexture2D(GLES30.GL_FRAMEBUFFER,GLES30.GL_COLOR_ATTACHMENT0,
                GLES30.GL_TEXTURE_2D,texture,0);
        GLES30.glGenBuffers(1,id,0);pbo=id[0];
        GLES30.glBindBuffer(GLES30.GL_PIXEL_PACK_BUFFER,pbo);
        GLES30.glBufferData(GLES30.GL_PIXEL_PACK_BUFFER,BYTES,null,GLES30.GL_STREAM_READ);
    }

    private void poll(long now){
        if(fence==0)return;
        int status=GLES30.glClientWaitSync(fence,0,0L);
        if(status==GLES30.GL_TIMEOUT_EXPIRED&&now-pendingNs<=2500000000L)return;
        if(status!=GLES30.GL_ALREADY_SIGNALED&&status!=GLES30.GL_CONDITION_SATISFIED){
            fail(new IllegalStateException("meter fence stale or failed"));return;
        }
        int[] pack=new int[1];GLES30.glGetIntegerv(GLES30.GL_PIXEL_PACK_BUFFER_BINDING,pack,0);
        boolean mapped=false;
        try{
            GLES30.glBindBuffer(GLES30.GL_PIXEL_PACK_BUFFER,pbo);
            Buffer buffer=GLES30.glMapBufferRange(GLES30.GL_PIXEL_PACK_BUFFER,0,BYTES,GLES30.GL_MAP_READ_BIT);
            if(!(buffer instanceof ByteBuffer))throw new IllegalStateException("meter mapping unavailable");
            mapped=true;
            byte[] pixels=new byte[BYTES];
            ByteBuffer copy=((ByteBuffer)buffer).duplicate();copy.position(0);copy.get(pixels);
            boolean intact=GLES30.glUnmapBuffer(GLES30.GL_PIXEL_PACK_BUFFER);
            mapped=false;
            if(!intact)throw new IllegalStateException("meter mapping invalid");
            if(now-pendingNs<=2500000000L){
                M9PreviewTc20Math1A.Result tc20=M9PreviewTc20Math1A.analyzePackedPanel(
                        pixels,W,H,STEPS,TC20_PANEL);
                latest=new Evidence(pending,pendingNs,pendingTextureNs,pendingDataSpace,
                        pendingReferenceScale,pixels,tc20);
            }
        }catch(RuntimeException e){fail(e);}
        finally{
            if(mapped)GLES30.glUnmapBuffer(GLES30.GL_PIXEL_PACK_BUFFER);
            GLES30.glBindBuffer(GLES30.GL_PIXEL_PACK_BUFFER,pack[0]);
            if(fence!=0)GLES30.glDeleteSync(fence);
            fence=0;pending=null;
        }
    }

    private void fail(RuntimeException error){
        disabled=true;latest=null;unavailableReason=error.getMessage();
        appliedTc20Ev=0;appliedTc20Gain=1;consumedTc20SampleNs=-1;
        if(fence!=0)GLES30.glDeleteSync(fence);
        fence=0;pending=null;
        Log.w("M9PreviewEvidence2E","Paired preview evidence disabled for this surface: "+error);
    }

    private static final class Evidence {
        final M9PreviewFrameState1W state;
        final long submittedNs,textureNs;
        final int dataSpace;
        final float referenceScale;
        final byte[] rgba;
        final M9PreviewTc20Math1A.Result tc20;
        Evidence(M9PreviewFrameState1W state,long submitted,long texture,int space,
                float reference,byte[] pixels,M9PreviewTc20Math1A.Result tc20){
            this.state=state;submittedNs=submitted;textureNs=texture;dataSpace=space;
            referenceScale=reference;rgba=pixels.clone();this.tc20=tc20;
        }
    }

    /** Camera-thread snapshot: no GL call or wait, reject a previous camera's evidence. */
    public org.json.JSONObject snapshot(long shutterNs,M9ExposurePlan1A capture){
        org.json.JSONObject o=new org.json.JSONObject();
        try{
            o.put("revision","M9PREVIEWTC20NEG1A").put("pairedEvidenceRevision",LEGACY_EVIDENCE_REVISION).put("available",false);
            Evidence e=latest;
            if(e==null)return o.put("reason",unavailableReason);
            if(capture==null||!e.state.plan.cameraId.equals(capture.cameraId)
                    ||!e.state.plan.mode.equals(capture.mode))
                return o.put("reason","different_camera_or_mode");
            double age=(shutterNs-e.submittedNs)/1e6;
            o.put("ageMs",age);
            if(age<0||age>2500)return o.put("reason","stale_readback");
            M9ExposurePlan1A p=e.state.plan;
            o.put("available",true).put("cameraId",p.cameraId).put("mode",p.mode);
            o.put("samplePlanId",p.id).put("capturePlanId",capture.id);
            o.put("sampleUserEv",p.userEv).put("sampleAutoEv",p.autoEv);
            o.put("captureUserEv",capture.userEv).put("captureAutoEv",capture.autoEv);
            o.put("submittedElapsedNs",e.submittedNs).put("textureTimestampNs",e.textureNs);
            o.put("stateResultTimestampNs",e.state.resultTimestampNs);
            o.put("textureMatchesResult",e.textureNs==e.state.resultTimestampNs);
            o.put("textureMinusResultNs",e.textureNs-e.state.resultTimestampNs);
            o.put("textureDataSpace",e.dataSpace);
            o.put("displayExposureScale",e.state.exposureScale).put("referenceExposureScale",e.referenceScale);
            o.put("observedIso",p.observedIso).put("observedExposureNs",p.observedExposureNs);
            o.put("referenceIso",p.referenceIso).put("referenceExposureNs",p.referenceExposureNs);
            o.put("sourceContract",e.state.source2A.diagnostics());
            o.put("sameTextureForAllPanels",true).put("sameFrameAsShutter",false);
            o.put("focusPeakingIncluded",false).put("displayPresentationVerified",false);
            o.put("width",W).put("height",H).put("rowOrder","GL_bottom_to_top");
            o.put("previewTc20NegativeOnly",true)
                    .put("previewTc20Target",M9PreviewTc20Math1A.METER_TARGET)
                    .put("previewTc20Valid",e.tc20.valid)
                    .put("previewTc20WeightedMedian",e.tc20.valid?e.tc20.weightedMedian:org.json.JSONObject.NULL)
                    .put("previewTc20RequestedGain",e.tc20.valid?e.tc20.requestedGain:org.json.JSONObject.NULL)
                    .put("previewTc20RequestedEv",e.tc20.valid?e.tc20.requestedEv:org.json.JSONObject.NULL)
                    .put("previewTc20BoundedGain",e.tc20.valid?e.tc20.boundedGain:org.json.JSONObject.NULL)
                    .put("previewTc20BoundedEv",e.tc20.valid?e.tc20.boundedEv:org.json.JSONObject.NULL)
                    .put("previewTc20AppliedGain",appliedTc20Gain)
                    .put("previewTc20AuthorityEv","[-0.5,0.0]")
                    .put("previewTc20PositiveReason","raw_tail_headroom_unavailable_live");
            String[] names={"incomingOes","referenceRender","displayRender"};
            org.json.JSONObject panels=new org.json.JSONObject();
            for(int i=0;i<3;i++)panels.put(names[i],panel(e.rgba,i));
            panels.put("tc20LinearProbe",tc20Panel(e.rgba,TC20_PANEL));
            o.put("panels",panels);
            return o;
        }catch(org.json.JSONException error){throw new IllegalStateException(error);}
    }

    private static org.json.JSONObject panel(byte[] rgba,int index)throws org.json.JSONException{
        int[] histogram=new int[256];int min=255,max=0;
        char[] hex=new char[W*H*6];char[] digits="0123456789abcdef".toCharArray();int pos=0;
        for(int y=0;y<H;y++)for(int x=0;x<W;x++){
            int offset=((y*W*STEPS)+(index*W)+x)*4;
            int r=rgba[offset]&255,g=rgba[offset+1]&255,b=rgba[offset+2]&255;
            int l=(77*r+150*g+29*b+128)>>8;histogram[l]++;min=Math.min(min,l);max=Math.max(max,l);
            for(int c=0;c<3;c++){int v=rgba[offset+c]&255;hex[pos++]=digits[v>>>4];hex[pos++]=digits[v&15];}
        }
        int sum=0,q01=-1,median=-1,q99=-1;
        for(int i=0;i<256;i++){sum+=histogram[i];if(q01<0&&sum>=Math.ceil(W*H*.01))q01=i;
            if(median<0&&sum>=W*H/2)median=i;if(q99<0&&sum>=Math.ceil(W*H*.99))q99=i;}
        return new org.json.JSONObject().put("rgbHex",new String(hex)).put("minLuma",min)
                .put("q01Luma",q01).put("medianLuma",median).put("q99Luma",q99).put("maxLuma",max);
    }

    private static org.json.JSONObject tc20Panel(byte[] rgba,int index)throws org.json.JSONException{
        int min=65535,max=0;long sum=0;
        for(int y=0;y<H;y++)for(int x=0;x<W;x++){
            int off=((y*W*STEPS)+(index*W)+x)*4;
            int q=((rgba[off]&255)<<8)|(rgba[off+1]&255);
            min=Math.min(min,q);max=Math.max(max,q);sum+=q;
        }
        return new org.json.JSONObject().put("encoding","linear_luma_u16_big_endian_RG")
                .put("min",min/65535.0).put("mean",(sum/(double)(W*H))/65535.0)
                .put("max",max/65535.0);
    }
}
