package com.particlesdevs.photoncamera.m9.preview;

import android.hardware.camera2.CaptureRequest;
import android.hardware.camera2.CaptureResult;
import android.hardware.camera2.TotalCaptureResult;
import android.hardware.camera2.params.RggbChannelVector;
import android.os.Build;
import android.os.SystemClock;
import android.util.Rational;
import org.json.JSONArray;
import org.json.JSONObject;
import java.util.ArrayDeque;
import java.util.ArrayList;

/**
 * Read-only, bounded metadata history.
 *
 * M9PREVIEWHEAP1A keeps the per-frame scalar metadata join but removes the old
 * per-frame full TONEMAP_CURVE JSON payload. The old diagnostic could retain
 * three copied colour curves for every preview result for up to 30 seconds.
 * That is diagnostic state only; it never participates in exposure or rendering.
 */
public final class M9RootCauseTrace1A {
    public static final String REVISION="M9ROOTCAUSE1A";
    public static final String MEMORY_REVISION="M9PREVIEWHEAP1A";
    private static final int CAPACITY=1800;
    private static final long WINDOW_NS=30000000000L;
    private static final long CONTEXT_PERIOD_NS=500000000L;
    private static final ArrayDeque<Row> rows=new ArrayDeque<>();
    private static String activeCamera="";
    private static String lastCompactContext="{}";
    private static long lastContextElapsed=-1;
    private static long unavailable,duplicates,memoryDrops,lastTimestamp=-1;
    private static final String[] FIELDS={
        "elapsedNs","sensorTimestampNs","frameNumber","iso","exposureNs",
        "focusDiopters","lensState","afMode","afState","awbMode","awbState",
        "awbLock","aeMode","aeState","aeCompensation","postRawBoost",
        "edgeMode","noiseReductionMode","tonemapMode","neutralR","neutralG","neutralB",
        "wbGainR","wbGainGe","wbGainGo","wbGainB","requestAfMode","requestAfTrigger",
        "requestFocusDiopters","requestAwbMode","requestAwbLock","requestAeMode",
        "requestAeCompensation","userEv","focalLengthMm"};
    private M9RootCauseTrace1A() {}
    private static double number(Number v){return v==null?Double.NaN:v.doubleValue();}
    private static double flag(Boolean v){return v==null?Double.NaN:v?1:0;}
    private static final class Row {
        final long elapsed,timestamp,frame;
        final double[] values;
        final String context;
        Row(long e,long t,long f,double[] v,String c){
            elapsed=e;timestamp=t;frame=f;values=v;context=c;
        }
    }

    public static void observe(CaptureRequest request,TotalCaptureResult logical,String cameraId,double userEv) {
        if(request==null||logical==null||cameraId==null)return;
        try {
            CaptureResult result=logical;
            String[] ids=cameraId.split("-");
            if(ids.length==2&&!ids[0].equals(ids[1])) {
                if(Build.VERSION.SDK_INT<28){miss();return;}
                result=logical.getPhysicalCameraResults().get(ids[1]);
                if(result==null){miss();return;}
            }
            Long timestamp=result.get(CaptureResult.SENSOR_TIMESTAMP);
            if(timestamp==null){miss();return;}
            long now=SystemClock.elapsedRealtimeNanos();
            Rational[] n=result.get(CaptureResult.SENSOR_NEUTRAL_COLOR_POINT);
            RggbChannelVector g=result.get(CaptureResult.COLOR_CORRECTION_GAINS);
            double[] v={0,0,0,
                number(result.get(CaptureResult.SENSOR_SENSITIVITY)),number(result.get(CaptureResult.SENSOR_EXPOSURE_TIME)),
                number(result.get(CaptureResult.LENS_FOCUS_DISTANCE)),number(result.get(CaptureResult.LENS_STATE)),
                number(result.get(CaptureResult.CONTROL_AF_MODE)),number(result.get(CaptureResult.CONTROL_AF_STATE)),
                number(result.get(CaptureResult.CONTROL_AWB_MODE)),number(result.get(CaptureResult.CONTROL_AWB_STATE)),flag(result.get(CaptureResult.CONTROL_AWB_LOCK)),
                number(result.get(CaptureResult.CONTROL_AE_MODE)),number(result.get(CaptureResult.CONTROL_AE_STATE)),
                number(result.get(CaptureResult.CONTROL_AE_EXPOSURE_COMPENSATION)),number(result.get(CaptureResult.CONTROL_POST_RAW_SENSITIVITY_BOOST)),
                number(result.get(CaptureResult.EDGE_MODE)),number(result.get(CaptureResult.NOISE_REDUCTION_MODE)),number(result.get(CaptureResult.TONEMAP_MODE)),
                n!=null&&n.length==3?number(n[0]):Double.NaN,n!=null&&n.length==3?number(n[1]):Double.NaN,n!=null&&n.length==3?number(n[2]):Double.NaN,
                g==null?Double.NaN:g.getRed(),g==null?Double.NaN:g.getGreenEven(),g==null?Double.NaN:g.getGreenOdd(),g==null?Double.NaN:g.getBlue(),
                number(request.get(CaptureRequest.CONTROL_AF_MODE)),number(request.get(CaptureRequest.CONTROL_AF_TRIGGER)),number(request.get(CaptureRequest.LENS_FOCUS_DISTANCE)),
                number(request.get(CaptureRequest.CONTROL_AWB_MODE)),flag(request.get(CaptureRequest.CONTROL_AWB_LOCK)),number(request.get(CaptureRequest.CONTROL_AE_MODE)),
                number(request.get(CaptureRequest.CONTROL_AE_EXPOSURE_COMPENSATION)),userEv,number(result.get(CaptureResult.LENS_FOCAL_LENGTH))};

            synchronized(M9RootCauseTrace1A.class) {
                if(!cameraId.equals(activeCamera)){
                    rows.clear();
                    activeCamera=cameraId;
                    lastTimestamp=-1;
                    unavailable=duplicates=memoryDrops=0;
                    lastCompactContext="{}";
                    lastContextElapsed=-1;
                }
                if(timestamp==lastTimestamp){duplicates++;return;}
                lastTimestamp=timestamp;

                // Context is diagnostic only. Sample it at 2 Hz and share the immutable
                // String between intervening Rows instead of rebuilding/retaining it at
                // camera-result cadence.
                if(lastContextElapsed<0||now-lastContextElapsed>=CONTEXT_PERIOD_NS){
                    lastCompactContext=compactContext(result,ids.length==2?ids[1]:cameraId);
                    lastContextElapsed=now;
                }

                while(!rows.isEmpty()&&(rows.size()>=CAPACITY||now-rows.peekFirst().elapsed>WINDOW_NS))
                    rows.removeFirst();
                rows.addLast(new Row(now,timestamp,result.getFrameNumber(),v,lastCompactContext));
            }
        }catch(OutOfMemoryError e){
            // This recorder is optional diagnostics. If its own allocation is ever the
            // failing allocation, immediately release retained history rather than let
            // diagnostic evidence kill the camera process.
            dropForMemory();
        }catch(RuntimeException e){
            miss();
        }
    }

    private static synchronized void miss(){unavailable++;}

    private static synchronized void dropForMemory(){
        rows.clear();
        lastCompactContext="{}";
        lastContextElapsed=-1;
        memoryDrops++;
    }

    /**
     * Compact live context. Full per-frame tone curves were the heap leak.
     * Keep CCM plus curve point counts; scalar TONEMAP_MODE remains in values[].
     */
    private static String compactContext(CaptureResult r,String physicalId) {
        try {
            JSONObject o=new JSONObject().put("selectedCameraId",physicalId)
                    .put("memoryRevision",MEMORY_REVISION);
            android.hardware.camera2.params.ColorSpaceTransform ccm=
                    r.get(CaptureResult.COLOR_CORRECTION_TRANSFORM);
            JSONArray matrix=new JSONArray();
            if(ccm!=null)
                for(int y=0;y<3;y++)for(int x=0;x<3;x++)
                    matrix.put(ccm.getElement(x,y).doubleValue());
            o.put("ccmRowMajor",matrix);

            android.hardware.camera2.params.TonemapCurve curve=
                    r.get(CaptureResult.TONEMAP_CURVE);
            JSONArray counts=new JSONArray();
            if(curve!=null)for(int c=0;c<3;c++)counts.put(curve.getPointCount(c));
            o.put("toneCurvePointCountsRgb",counts)
                    .put("toneCurvePayload","omitted_live_heap_guard");
            return o.toString();
        }catch(Exception e){
            return "{}";
        }
    }

    public static JSONObject snapshot(long shutterNs,String cameraId) {
        return range(shutterNs-WINDOW_NS,shutterNs,cameraId);
    }

    public static JSONObject range(long startNs,long endNs,String cameraId) {
        JSONObject o=new JSONObject();
        try {
            ArrayList<Row> copy;
            long missing,dupes,drops;
            synchronized(M9RootCauseTrace1A.class){
                o.put("revision",REVISION).put("memoryRevision",MEMORY_REVISION)
                        .put("cameraId",cameraId).put("available",false);
                if(!activeCamera.equals(cameraId))
                    return o.put("reason","no_history_for_camera");
                copy=new ArrayList<>(rows);
                missing=unavailable;
                dupes=duplicates;
                drops=memoryDrops;
            }
            JSONArray data=new JSONArray(),contexts=new JSONArray();
            for(Row r:copy) {
                if(r.elapsed<startNs||r.elapsed>endNs)continue;
                JSONArray a=new JSONArray();
                a.put(r.elapsed).put(r.timestamp).put(r.frame);
                for(int i=3;i<r.values.length;i++)
                    a.put(Double.isFinite(r.values[i])?r.values[i]:JSONObject.NULL);
                data.put(a);
                contexts.put(new JSONObject().put("sensorTimestampNs",r.timestamp)
                        .put("context",new JSONObject(r.context)));
            }
            return o.put("available",data.length()>0)
                    .put("columns",new JSONArray(FIELDS))
                    .put("rows",data)
                    .put("contexts",contexts)
                    .put("requestedStartNs",startNs)
                    .put("requestedEndNs",endNs)
                    .put("oldestRetainedElapsedNs",copy.isEmpty()?JSONObject.NULL:copy.get(0).elapsed)
                    .put("windowSeconds",30)
                    .put("capacity",CAPACITY)
                    .put("contextSamplePeriodMs",CONTEXT_PERIOD_NS/1000000L)
                    .put("toneCurvePayload","omitted_live_heap_guard")
                    .put("memoryDrops",drops)
                    .put("missingMetadataCallbacks",missing)
                    .put("duplicateTimestamps",dupes)
                    .put("timeJoin","sensorTimestampNs; no nearest-frame substitution")
                    .put("requestMutation",false);
        }catch(org.json.JSONException e){
            throw new IllegalStateException(e);
        }
    }
}
