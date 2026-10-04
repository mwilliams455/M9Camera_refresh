package com.particlesdevs.photoncamera.m9.preview;

import android.graphics.Bitmap;
import android.hardware.camera2.CaptureResult;
import android.hardware.camera2.TotalCaptureResult;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.view.View;
import androidx.exifinterface.media.ExifInterface;
import com.particlesdevs.photoncamera.m9.M9DiagnosticBurstSpool;
import com.particlesdevs.photoncamera.m9.M9DiagnosticSidecarIO;
import com.particlesdevs.photoncamera.util.FileManager;
import com.particlesdevs.photoncamera.util.Log;
import org.json.JSONArray;
import org.json.JSONObject;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.lang.ref.WeakReference;
import java.util.LinkedHashMap;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;

/** Diagnostic-only capture ledger. All joins are exact, queues and retained captures are bounded. */
public final class M9ShutterTrace1A {
    public static final String REVISION="M9SHUTTERTRACE1B";
    private static final M9TraceLedger1A LEDGER=new M9TraceLedger1A(4);
    private static final LinkedHashMap<String,Session> SESSIONS=new LinkedHashMap<>();
    private static final Handler MAIN=new Handler(Looper.getMainLooper());
    private static final AtomicLong DROPPED=new AtomicLong();
    private static final ThreadPoolExecutor IO=new ThreadPoolExecutor(1,1,0,TimeUnit.MILLISECONDS,
        new ArrayBlockingQueue<>(24),r->{Thread t=new Thread(()->{android.os.Process.setThreadPriority(android.os.Process.THREAD_PRIORITY_BACKGROUND);r.run();},"M9ShutterTraceIO");t.setDaemon(true);return t;});
    private static volatile M9RootCausePixels1A pixels;
    private static volatile M9PreviewFrameState1W.Draw latestDraw;
    public static void draw(M9PreviewFrameState1W.Draw d){latestDraw=d;}
    public static JSONObject drawSnapshot(){try{M9PreviewFrameState1W.Draw d=latestDraw;return d==null?new JSONObject():new JSONObject(d.snapshot(SystemClock.elapsedRealtimeNanos(),d.state.plan));}catch(Exception e){return error(e);}}
    public static void surfacePixels(String id,JSONObject evidence,M9ShutterRgb1A.Samples pixels,M9ShutterRgb1A.Samples expected) {
        submit(()->{try{evidence.put("rgb",M9ShutterRgb1A.json(pixels));
            if(expected!=null)evidence.put("softwareViewRgb",M9ShutterRgb1A.json(expected)).put("softwareVsWindowDelta",M9ShutterRgb1A.compare(expected,pixels));
            surface(id,evidence);
        }catch(Exception e){surface(id,error(e));}});
    }
    public static void thumbnail(android.content.Context context,android.net.Uri uri,Bitmap b) {
        try {
            final long called=SystemClock.elapsedRealtimeNanos();
            M9ShutterRgb1A.Samples copied=M9ShutterRgb1A.capture(b);
            submit(()->{try {
                String name=M9TracePolicy1B.localFilename(uri.getScheme(),uri.getPath());
                if("content".equals(uri.getScheme()))try(android.database.Cursor c=context.getContentResolver().query(uri,new String[]{android.provider.OpenableColumns.DISPLAY_NAME},null,null,null)) {
                    if(c!=null&&c.moveToFirst())name=c.getString(0);
                }
                Session s=session(LEDGER.byRelatedFilename(name));if(s==null){Log.w(REVISION,"unjoined thumbnail source "+name);return;}
                String role=M9TracePolicy1B.role(name);
                JSONObject record=new JSONObject().put("rgb",M9ShutterRgb1A.json(copied)).put("sourceUri",uri.toString()).put("sourceFilename",name).put("sourceRole",role).put("callbackElapsedNs",called);
                JSONArray history=s.root.optJSONArray("thumbnails");if(history==null){history=new JSONArray();s.root.put("thumbnails",history);}if(history.length()<8)history.put(record);
                if("jpeg".equals(role))s.root.put("thumbnailDecode",record.getJSONObject("rgb")).put("thumbnailSourceUri",uri.toString());
                persist(s,"thumbnail_decode");
            }catch(Exception e){Log.w(REVISION,"thumbnail probe: "+e);}});
        }catch(Throwable t){Log.w(REVISION,"thumbnail copy: "+t);}
    }
    private static final class Session {
        final M9TraceLedger1A.Entry join;
        final JSONObject root=new JSONObject();
        final WeakReference<View> view;
        volatile M9ShutterRgb1A.Samples before;
        volatile M9JpegSignature1A.Result payload;
        int sequence;
        Session(M9TraceLedger1A.Entry e,View v){join=e;view=new WeakReference<>(v);}
    }
    private M9ShutterTrace1A(){}
    public static void registerPixels(M9RootCausePixels1A p){pixels=p;}
    public static boolean sampling(){return LEDGER.sampling(SystemClock.elapsedRealtimeNanos());}
    private static synchronized Session session(M9TraceLedger1A.Entry e){return e==null?null:SESSIONS.get(e.id);}
    private static void submit(Runnable r){try{IO.execute(()->{try{r.run();}catch(Throwable t){Log.w(REVISION,"diagnostic task failed: "+t);}});}catch(RejectedExecutionException e){DROPPED.incrementAndGet();Log.w(REVISION,"diagnostic queue full");}}
    private static long timestamp(CaptureResult r){Long n=r==null?null:r.get(CaptureResult.SENSOR_TIMESTAMP);return n==null?-1:n;}
    private static JSONObject error(Throwable t){try{return new JSONObject().put("available",false).put("error",t.toString());}catch(Exception e){return new JSONObject();}}
    private static JSONObject signature(M9JpegSignature1A.Result s)throws Exception {
        return new JSONObject().put("codingSha256",s.codingSha256).put("codingBytes",s.codingBytes).put("digestProviderUpdates",s.digestUpdates)
            .put("iccSegments",s.iccSegments).put("iccSegmentOrderSha256",s.iccSha256==null?JSONObject.NULL:s.iccSha256)
            .put("width",s.width).put("height",s.height).put("sofSampling",s.sampling);
    }
    public static void begin(JSONObject preview,View view) {
        try {
            String id=preview.getString("pairId"),camera=preview.getString("cameraId");long ns=preview.getLong("shutterPressElapsedRealtimeNs");
            M9TraceLedger1A.Entry e=LEDGER.begin(id,camera,ns);
            if(e==null){DROPPED.incrementAndGet();Log.w(REVISION,"capture ledger full or duplicate ID");return;}
            Session s=new Session(e,view);JSONObject snapshot=new JSONObject(preview.toString());
            synchronized(M9ShutterTrace1A.class){
                SESSIONS.entrySet().removeIf(x->LEDGER.get(x.getKey())==null);SESSIONS.put(id,s);
            }
            submit(()->{try {
                s.root.put("schema","m9cam.shuttertrace.v1b").put("revision",REVISION).put("captureId",id)
                    .put("cameraId",camera).put("shutterElapsedNs",ns).put("shutterSnapshot",snapshot)
                    .put("photographicPolicyChanged",false).put("physicalDisplayAppearanceVerified",false);
                s.root.put("preMetadata",M9RootCauseTrace1A.range(ns-3000000000L,ns,camera));
                M9RootCausePixels1A p=pixels;
                if(p!=null)s.root.put("prePreview",p.range(ns-3000000000L,ns,camera));
                persist(s,"armed");
            }catch(Exception t){Log.w(REVISION,t.toString());}});
            MAIN.post(()->M9ShutterSurface1A.preview(s.view.get(),id,"shutter"));
            MAIN.postDelayed(()->{
                if(!e.closed){long end=SystemClock.elapsedRealtimeNanos();LEDGER.close(id);submit(()->{try{temporal(s,"capture_observation_timeout",end);}catch(Exception t){Log.w(REVISION,t.toString());}});}
            },60000);
        }catch(Throwable t){Log.w(REVISION,"begin failed: "+t);}
    }
    /** Called synchronously at Camera2 completion, before either renderer or asynchronous sidecar can race. */
    public static void completed(JSONObject preview,TotalCaptureResult result,String physicalId) {
        try {
            String id=preview.getString("pairId");long now=SystemClock.elapsedRealtimeNanos();
            CaptureResult physical=null;
            if(android.os.Build.VERSION.SDK_INT>=28&&physicalId!=null)physical=result.getPhysicalCameraResults().get(physicalId);
            M9TraceLedger1A.Entry e=LEDGER.complete(id,timestamp(result),timestamp(physical),now);Session s=session(e);if(s==null)return;
            submit(()->{try{s.root.put("stillCompletedElapsedNs",now).put("logicalSensorTimestampNs",e.logicalNs)
                .put("physicalSensorTimestampNs",e.physicalNs);persist(s,"still_result");}catch(Exception t){Log.w(REVISION,t.toString());}});
            for(int delay:new int[]{250,1000,3000,5500})MAIN.postDelayed(()->M9ShutterSurface1A.preview(s.view.get(),id,"resumed_preview"),delay);
            MAIN.postDelayed(()->{long end=SystemClock.elapsedRealtimeNanos();submit(()->{try{
                temporal(s,"initial_post_capture_window",end);
                s.root.put("initialPostPreview",s.root.optJSONObject("postPreview")).put("initialPostMetadata",s.root.optJSONObject("postMetadata"));
                persist(s,"initial_window_preserved");
            }catch(Exception t){Log.w(REVISION,t.toString());}});},6500);
        }catch(Throwable t){Log.w(REVISION,"completed failed: "+t);}
    }
    private static void temporal(Session s,String reason,long now)throws Exception {
        s.root.put("temporalSerializedElapsedNs",SystemClock.elapsedRealtimeNanos()).put("observationCloseReason",reason);
        s.root.put("postJpegObservationNs",s.join.jpegCompletedNs<0?0:Math.max(0,now-s.join.jpegCompletedNs));
        s.root.put("temporalEndElapsedNs",now).put("postMetadata",M9RootCauseTrace1A.range(s.join.shutterNs,now,s.join.camera));
        M9RootCausePixels1A p=pixels;
        if(p!=null)s.root.put("postPreview",p.range(s.join.shutterNs,now,s.join.camera));
        else s.root.put("postPreview",new JSONObject().put("available",false).put("reason","no_GL_collector"));
        persist(s,reason);
    }
    public static void beforeEncode(Path path,Bitmap bitmap,CaptureResult result) {
        try {
            Session s=session(LEDGER.bySensor(timestamp(result)));
            if(s==null){Log.w(REVISION,"unjoined final bitmap timestamp="+timestamp(result));return;}
            long started=SystemClock.elapsedRealtimeNanos();
            M9ShutterRgb1A.Samples copied=M9ShutterRgb1A.capture(bitmap);s.before=copied;
            LEDGER.bindFilename(s.join,path.getFileName().toString());
            long copyNs=SystemClock.elapsedRealtimeNanos()-started;
            submit(()->{try{s.root.put("jpegFilename",path.getFileName().toString()).put("bitmapCopyNs",copyNs).put("beforeEncodeCallbackElapsedNs",started)
                .put("preEncodeRgb",M9ShutterRgb1A.json(copied));persist(s,"before_encode");}catch(Exception t){Log.w(REVISION,t.toString());}});
        }catch(Throwable t){Log.w(REVISION,"beforeEncode failed: "+t);}
    }
    /** Synchronous small streaming digest: must finish before the EXIF worker is allowed to rewrite the file. */
    public static void payloadWritten(Path path) {
        Session s=session(LEDGER.byFilename(path.getFileName().toString()));if(s==null)return;
        long started=SystemClock.elapsedRealtimeNanos();
        try {s.payload=M9JpegSignature1A.read(path.toFile());long elapsed=SystemClock.elapsedRealtimeNanos()-started;
            submit(()->{try{s.root.put("encodedBeforeExif",signature(s.payload)).put("payloadDigestNs",elapsed);persist(s,"encoded");}catch(Exception t){Log.w(REVISION,t.toString());}});
        }catch(Throwable t){submit(()->{try{s.root.put("encodedBeforeExif",error(t));persist(s,"encode_probe_failed");}catch(Exception ignored){}});}
    }
    public static void finalized(Path path,boolean success) {
        Session s=session(LEDGER.byFilename(path.getFileName().toString()));if(s==null)return;
        long called=SystemClock.elapsedRealtimeNanos();
        LEDGER.jpegComplete(s.join.id,called);
        for(int delay:new int[]{250,1000,3000,7500})MAIN.postDelayed(()->{
            if(!s.join.closed)M9ShutterSurface1A.preview(s.view.get(),s.join.id,"post_jpeg_preview");
        },delay);
        MAIN.postDelayed(()->{if(!s.join.closed){long end=SystemClock.elapsedRealtimeNanos();LEDGER.close(s.join.id);
            submit(()->{try{temporal(s,"post_jpeg_window_complete",end);}catch(Exception t){Log.w(REVISION,t.toString());}});
        }},8000);
        submit(()->{try {
            s.root.put("jpegFinalizedElapsedNs",called).put("jpegFinalizeSuccess",success);
            if(success) {
                M9JpegSignature1A.Result after=M9JpegSignature1A.read(path.toFile());s.root.put("encodedAfterExif",signature(after));
                s.root.put("codingBytesPreservedAcrossExif",s.payload==null?JSONObject.NULL:s.payload.codingSha256.equals(after.codingSha256));
                ExifInterface exif=new ExifInterface(path.toString());
                s.root.put("savedExif",new JSONObject().put("available",true).put("colorSpace",exif.getAttribute(ExifInterface.TAG_COLOR_SPACE)==null?JSONObject.NULL:exif.getAttribute(ExifInterface.TAG_COLOR_SPACE))
                    .put("orientation",exif.getAttribute(ExifInterface.TAG_ORIENTATION)).put("software",exif.getAttribute(ExifInterface.TAG_SOFTWARE)));
                if(s.before!=null) {
                    M9ShutterRgb1A.Samples decoded=M9ShutterRgb1A.decode(path.toString(),s.before);
                    s.root.put("jpegDecodedRgb",M9ShutterRgb1A.json(decoded)).put("encodingDelta",M9ShutterRgb1A.compare(s.before,decoded));
                }
            }
            persist(s,"jpeg_finalized");
        }catch(Throwable t){try{s.root.put("jpegEndpointError",error(t));persist(s,"jpeg_probe_failed");}catch(Exception ignored){}}});
    }
    public static String captureForFilename(String name){M9TraceLedger1A.Entry e=LEDGER.byFilename(name);return e==null?null:e.id;}
    public static void surface(String id,JSONObject evidence) {
        Session s=session(LEDGER.get(id));if(s==null)return;
        submit(()->{try {
            JSONArray a=s.root.optJSONArray("surfaces");if(a==null){a=new JSONArray();s.root.put("surfaces",a);}
            if(a.length()<36)a.put(evidence);else s.root.put("surfaceSamplesTruncated",true);
            persist(s,"surface_sample");
        }catch(Exception t){Log.w(REVISION,t.toString());}});
    }
    private static void persist(Session s,String event)throws Exception {
        s.root.put("lastEvent",event).put("lastUpdateElapsedNs",SystemClock.elapsedRealtimeNanos())
            .put("sequence",++s.sequence).put("droppedDiagnosticTasks",DROPPED.get());
        JSONObject coverage=new JSONObject().put("preEncode",s.root.has("preEncodeRgb")).put("jpegDecoded",s.root.has("jpegDecodedRgb"))
            .put("thumbnailDecoded",s.root.has("thumbnailDecode")).put("jpegMetadataRead",s.root.has("savedExif"));
        JSONObject metadata=s.root.optJSONObject("postMetadata");coverage.put("postMetadata",metadata!=null&&metadata.optBoolean("available"));
        JSONObject post=s.root.optJSONObject("postPreview");coverage.put("postPreview",post!=null&&post.optBoolean("available"));
        JSONArray surfaces=s.root.optJSONArray("surfaces");boolean gallery=false,preview=false;
        if(surfaces!=null)for(int i=0;i<surfaces.length();i++){JSONObject f=surfaces.optJSONObject(i);if(f!=null&&f.optInt("pixelCopyResult",-1)==0){gallery|="gallery".equals(f.optString("kind"))&&f.optBoolean("correspondenceVerified");preview|="preview".equals(f.optString("kind"));}}
        boolean afterJpeg=false;JSONArray frames=post==null?null:post.optJSONArray("frames");
        if(frames!=null&&s.join.jpegCompletedNs>0)for(int i=0;i<frames.length();i++) {
            JSONObject f=frames.optJSONObject(i);if(f!=null&&f.optLong("submittedElapsedNs",0)>s.join.jpegCompletedNs)afterJpeg=true;
        }
        coverage.put("postJpegPreview",afterJpeg);
        coverage.put("postJpegWindow",s.root.optLong("postJpegObservationNs",0)>=M9TracePolicy1B.POST_JPEG_NS);
        coverage.put("galleryWindow",gallery).put("previewSurface",preview).put("allEndpointKindsRecorded",coverage.optBoolean("preEncode")&&coverage.optBoolean("jpegDecoded")&&coverage.optBoolean("postPreview")&&coverage.optBoolean("postMetadata")&&coverage.optBoolean("thumbnailDecoded")&&coverage.optBoolean("jpegMetadataRead")&&gallery&&preview&&coverage.optBoolean("postJpegWindow")&&afterJpeg);
        s.root.put("coverage",coverage).put("causalDiagnosisComplete",false);
        Path out=FileManager.sDCIM_CAMERA.toPath().resolve("M9_SHUTTERTRACE_"+s.join.id+".json");
        byte[] bytes=s.root.toString().getBytes(StandardCharsets.UTF_8);
        if(!M9DiagnosticBurstSpool.stage(out,bytes,"shutter_trace"))M9DiagnosticSidecarIO.persist(out,bytes,"shutter_trace_fallback");
    }
}
