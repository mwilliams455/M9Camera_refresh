package com.particlesdevs.photoncamera.m9.preview;

import android.opengl.GLES30;
import android.os.SystemClock;
import com.particlesdevs.photoncamera.m9.M9ExposurePlan1A;
import com.particlesdevs.photoncamera.util.Log;
import java.nio.Buffer;
import java.nio.ByteBuffer;

/** Read-only 1:1 viewport crops; 1 Hz idle, 4 Hz capture window, 48 frames maximum. Never feeds Auto. */
public final class M9RootCausePixels1A {
    private static final long INTERVAL_NS=1000000000L;
    private static final int W=64, H=64;
    private static final int STEPS=9, BYTES=W*H*STEPS*4;
    private int framebuffer,texture,pbo;
    private long fence,lastProbeNs,pendingNs,pendingTextureNs;
    private M9PreviewFrameState1W pending;
    private boolean disabled;
    private int pendingDataSpace=-1;
    private float pendingReferenceScale;
    private int[] pendingViewport;
    private float[] transform=new float[16],pendingTransform;private boolean mirror,pendingMirror,enabled,pendingEnabled;
    public void geometry(float[] t,boolean m,boolean e){transform=t.clone();mirror=m;enabled=e;}
    private final java.util.ArrayDeque<Evidence> history=new java.util.ArrayDeque<>();
    private volatile Evidence latest;
    private volatile String unavailableReason="awaiting_gpu_evidence";

    public void sample(M9PreviewFrameState1W frame,long textureNs,android.graphics.SurfaceTexture surface,int exposureUniform,
            int peakUniform,int peakValue,int evidenceUniform) {
        if(disabled)return;
        long now=SystemClock.elapsedRealtimeNanos();
        poll(now);
        M9ExposurePlan1A plan=frame.plan;
        if(disabled || fence!=0 || now-lastProbeNs<(M9ShutterTrace1A.sampling()?250000000L:INTERVAL_NS) || plan==null
                || !M9ExposurePlan1A.supportsMode1B(plan.mode) || textureNs<=0)return;
        double ratio=M9ExposurePlan1A.energy(plan.referenceIso,plan.referenceExposureNs)
                /M9ExposurePlan1A.energy(plan.observedIso,plan.observedExposureNs);
        if(!Double.isFinite(ratio) || ratio<=0)return;
        float referenceScale=(float)Math.max(.0625,Math.min(16,ratio));
        lastProbeNs=now;
        int[] scissorBox=new int[4]; GLES30.glGetIntegerv(GLES30.GL_SCISSOR_BOX,scissorBox,0);
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
            // Clear earlier renderer errors so a stale unrelated flag cannot accept/reject a probe.
            for(int drain=0;drain<8 && GLES30.glGetError()!=GLES30.GL_NO_ERROR;drain++) {}
            if(framebuffer==0)initialize();
            GLES30.glBindFramebuffer(GLES30.GL_FRAMEBUFFER,framebuffer);
            if(GLES30.glCheckFramebufferStatus(GLES30.GL_FRAMEBUFFER)!=GLES30.GL_FRAMEBUFFER_COMPLETE)
                throw new IllegalStateException("meter framebuffer incomplete");
            GLES30.glEnable(GLES30.GL_SCISSOR_TEST);
            GLES30.glUniform1i(peakUniform,0);
            for(int i=0;i<STEPS;i++) {
                GLES30.glScissor(i*W,0,W,H);
                int region=i/3,stage=i%3;
                int center=Math.round(viewport[2]*(.25f+.25f*region));
                GLES30.glViewport(i*W-center+W/2,-(viewport[3]-H)/2,viewport[2],viewport[3]);
                GLES30.glUniform1i(evidenceUniform,stage==0?1:0);
                GLES30.glUniform1f(exposureUniform,stage==1?referenceScale:frame.exposureScale);
                GLES30.glDrawArrays(GLES30.GL_TRIANGLE_STRIP,0,4);
            }
            GLES30.glBindBuffer(GLES30.GL_PIXEL_PACK_BUFFER,pbo);
            GLES30.glReadPixels(0,0,W*STEPS,H,GLES30.GL_RGBA,GLES30.GL_UNSIGNED_BYTE,0);
            fence=GLES30.glFenceSync(GLES30.GL_SYNC_GPU_COMMANDS_COMPLETE,0);
            if(fence==0 || GLES30.glGetError()!=GLES30.GL_NO_ERROR)throw new IllegalStateException("meter readback failed");
            pending=frame;pendingNs=now;pendingTextureNs=textureNs;
            pendingViewport=viewport.clone();pendingTransform=transform.clone();pendingMirror=mirror;pendingEnabled=enabled;
            pendingReferenceScale=referenceScale;
            pendingDataSpace=-1;
            if(android.os.Build.VERSION.SDK_INT>=33 && surface!=null) {
                try {pendingDataSpace=surface.getDataSpace();}catch(RuntimeException ignored) {}
            }
            GLES30.glFlush(); // Submit only; readback is mapped after a later zero-timeout fence poll.
        } catch(RuntimeException e) { fail(e); }
        finally {
            GLES30.glBindFramebuffer(GLES30.GL_DRAW_FRAMEBUFFER,draw[0]);
            GLES30.glBindFramebuffer(GLES30.GL_READ_FRAMEBUFFER,read[0]);
            GLES30.glBindBuffer(GLES30.GL_PIXEL_PACK_BUFFER,pack[0]);
            GLES30.glBindTexture(GLES30.GL_TEXTURE_2D,tex[0]);
            GLES30.glActiveTexture(active[0]);
            GLES30.glViewport(viewport[0],viewport[1],viewport[2],viewport[3]);
            GLES30.glScissor(scissorBox[0],scissorBox[1],scissorBox[2],scissorBox[3]);
            if(scissor)GLES30.glEnable(GLES30.GL_SCISSOR_TEST);else GLES30.glDisable(GLES30.GL_SCISSOR_TEST);
            GLES30.glUniform1i(evidenceUniform,0);
            GLES30.glUniform1f(exposureUniform,frame.exposureScale);
            GLES30.glUniform1i(peakUniform,peakValue);
        }
    }
    private void initialize() {
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
    private void poll(long now) {
        if(fence==0)return;
        int status=GLES30.glClientWaitSync(fence,0,0L);
        if(status==GLES30.GL_TIMEOUT_EXPIRED && now-pendingNs<=2500000000L)return;
        if(status!=GLES30.GL_ALREADY_SIGNALED && status!=GLES30.GL_CONDITION_SATISFIED) {
            fail(new IllegalStateException("meter fence stale or failed"));return;
        }
        int[] pack=new int[1];GLES30.glGetIntegerv(GLES30.GL_PIXEL_PACK_BUFFER_BINDING,pack,0);
        boolean mapped=false;
        try {
            GLES30.glBindBuffer(GLES30.GL_PIXEL_PACK_BUFFER,pbo);
            Buffer buffer=GLES30.glMapBufferRange(GLES30.GL_PIXEL_PACK_BUFFER,0,BYTES,GLES30.GL_MAP_READ_BIT);
            if(!(buffer instanceof ByteBuffer))throw new IllegalStateException("meter mapping unavailable");
            mapped=true;
            byte[] pixels=new byte[BYTES];
            ByteBuffer copy=((ByteBuffer)buffer).duplicate();copy.position(0);copy.get(pixels);
            boolean intact=GLES30.glUnmapBuffer(GLES30.GL_PIXEL_PACK_BUFFER);
            mapped=false;
            if(!intact)throw new IllegalStateException("meter mapping invalid");
            if(now-pendingNs<=2500000000L) {
                latest=new Evidence(pending,pendingNs,pendingTextureNs,pendingDataSpace,
                        pendingReferenceScale,pixels,pendingViewport,pendingTransform,pendingMirror,pendingEnabled);
                synchronized(history) {
                    while(!history.isEmpty()&&(history.size()>=48||now-history.peekFirst().submittedNs>30000000000L))history.removeFirst();
                    history.addLast(latest);
                }
            }
        } catch(RuntimeException e) {fail(e);}
        finally {
            if(mapped)GLES30.glUnmapBuffer(GLES30.GL_PIXEL_PACK_BUFFER);
            GLES30.glBindBuffer(GLES30.GL_PIXEL_PACK_BUFFER,pack[0]);
            if(fence!=0)GLES30.glDeleteSync(fence);
            fence=0;pending=null;
        }
    }
    private void fail(RuntimeException error) {
        disabled=true;latest=null;unavailableReason=error.getMessage();
        if(fence!=0)GLES30.glDeleteSync(fence);
        fence=0;pending=null;
        Log.w("M9RootCausePixels1A","Paired preview evidence disabled for this surface: "+error);
    }

    private static final class Evidence {
        final M9PreviewFrameState1W state;
        final long submittedNs,textureNs;
        final int dataSpace;
        final float referenceScale;
        final byte[] rgba; final int[] viewport;final float[] transform;final boolean mirror,enabled;
        Evidence(M9PreviewFrameState1W state,long submitted,long texture,int space,
                float reference,byte[] pixels,int[] viewport,float[] transform,boolean mirror,boolean enabled) {
            this.state=state;submittedNs=submitted;textureNs=texture;dataSpace=space;
            referenceScale=reference;rgba=pixels.clone();this.viewport=viewport.clone();this.transform=transform.clone();this.mirror=mirror;this.enabled=enabled;
        }
    }
    /** Bounded pre-shutter history. Both panel stages use exactly the same OES texture. */
    public org.json.JSONObject snapshot(long shutterNs,M9ExposurePlan1A capture) {
        return range(shutterNs-20000000000L,shutterNs,capture==null?"":capture.cameraId);
    }
    public org.json.JSONObject range(long startNs,long endNs,String cameraId) {
        org.json.JSONObject o=new org.json.JSONObject();
        try {
            o.put("revision","M9ROOTCAUSE1A").put("available",false).put("disabled",disabled);

            java.util.ArrayList<Evidence> copy;
            synchronized(history){copy=new java.util.ArrayList<>(history);}
            org.json.JSONArray frames=new org.json.JSONArray();
            for(Evidence e:copy) {
                if(!e.state.plan.cameraId.equals(cameraId))continue;
                if(e.submittedNs<startNs||e.submittedNs>endNs)continue;
                M9ExposurePlan1A p=e.state.plan;
                org.json.JSONObject f=new org.json.JSONObject();
                f.put("appliedState",new org.json.JSONObject(new M9PreviewFrameState1W.Draw(e.state,e.textureNs,e.submittedNs,0,e.enabled).snapshot(e.submittedNs,e.state.plan)))
                 .put("textureRotationMatrix",new org.json.JSONArray(e.transform)).put("mirror",e.mirror)
                 .put("submittedElapsedNs",e.submittedNs).put("textureTimestampNs",e.textureNs)
                 .put("stateResultTimestampNs",e.state.resultTimestampNs).put("textureMatchesResult",e.textureNs==e.state.resultTimestampNs)
                 .put("displayExposureScale",e.state.exposureScale).put("referenceExposureScale",e.referenceScale)
                 .put("userEv",p.userEv).put("autoEv",p.autoEv).put("observedIso",p.observedIso).put("observedExposureNs",p.observedExposureNs)
                 .put("sourceReady",e.state.source2A.ready).put("viewport",new org.json.JSONArray(e.viewport));
                org.json.JSONObject panels=new org.json.JSONObject();
                String[] names={"incomingOes","referenceRender","displayRender"};
                for(int i=0;i<STEPS;i++)panels.put("region"+(i/3)+"_"+names[i%3],panel(e.rgba,i));
                frames.put(f.put("panels",panels));
            }
            return o.put("available",frames.length()>0).put("reason",frames.length()>0?"history_available":unavailableReason)
                .put("frames",frames).put("width",W).put("height",H).put("capacity",48).put("idleIntervalMs",1000).put("activeIntervalMs",250)
                .put("requestedStartNs",startNs).put("requestedEndNs",endNs)
                .put("oldestRetainedSubmittedNs",copy.isEmpty()?org.json.JSONObject.NULL:copy.get(0).submittedNs)
                .put("crop","three_64x64_crops_at_viewport_x_0.25_0.5_0.75_y_0.5;_original_GL_pixel_scale_not_sensor_scale")
                .put("encoding","base64_zlib_RGB8_row_major_GL_bottom_to_top")
                .put("sameTextureForAllPanels",true).put("focusPeakingIncluded",false).put("displayPresentationVerified",false);
        }catch(org.json.JSONException error){throw new IllegalStateException(error);}
    }
    private static String encode(byte[] bytes) {
        try {
            java.io.ByteArrayOutputStream out=new java.io.ByteArrayOutputStream();
            java.util.zip.Deflater deflater=new java.util.zip.Deflater(1);
            try(java.util.zip.DeflaterOutputStream z=new java.util.zip.DeflaterOutputStream(out,deflater)){z.write(bytes);}
            finally{deflater.end();}
            return android.util.Base64.encodeToString(out.toByteArray(),android.util.Base64.NO_WRAP);
        }catch(java.io.IOException e){throw new IllegalStateException(e);}
    }
    private static org.json.JSONObject panel(byte[] rgba,int index) throws org.json.JSONException {
        int[] histogram=new int[256];int min=255,max=0;
        byte[] rgb=new byte[W*H*3];int pos=0;
        for(int y=0;y<H;y++)for(int x=0;x<W;x++) {
            int offset=((y*W*STEPS)+(index*W)+x)*4;
            int r=rgba[offset]&255,g=rgba[offset+1]&255,b=rgba[offset+2]&255;
            int l=(77*r+150*g+29*b+128)>>8;histogram[l]++;min=Math.min(min,l);max=Math.max(max,l);
            for(int c=0;c<3;c++)rgb[pos++]=rgba[offset+c];
        }
        int sum=0,q01=-1,median=-1,q99=-1;
        for(int i=0;i<256;i++){sum+=histogram[i];if(q01<0 && sum>=Math.ceil(W*H*.01))q01=i;
            if(median<0 && sum>=W*H/2)median=i;if(q99<0 && sum>=Math.ceil(W*H*.99))q99=i;}
        return new org.json.JSONObject().put("rgbZlibBase64",encode(rgb)).put("minLuma",min)
                .put("q01Luma",q01).put("medianLuma",median).put("q99Luma",q99).put("maxLuma",max);
    }
}
