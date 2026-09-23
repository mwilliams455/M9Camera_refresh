package com.particlesdevs.photoncamera.m9.render;

import android.app.ActivityManager;
import android.app.ApplicationExitInfo;
import android.content.Context;
import android.os.Build;
import android.os.Debug;
import android.os.Environment;
import android.os.Process;
import android.util.AtomicFile;
import android.util.Base64;
import com.particlesdevs.photoncamera.BuildConfig;
import com.particlesdevs.photoncamera.m9.M9DiagnosticBurstSpool;
import com.particlesdevs.photoncamera.util.Log;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.concurrent.atomic.AtomicBoolean;

/** Read-only durable failure evidence. Never changes pixels or crash handling policy. */
public final class M9RenderCrash1D {
    private static final String ID="M9RENDERCRASH1D";
    private static final int LIMIT=512*1024;
    private static volatile Context app;
    private static volatile JSONObject previous, previousJava, report;
    private static volatile boolean storageReady;
    private static final AtomicBoolean exported=new AtomicBoolean();
    private static final ThreadLocal<JSONObject> active=new ThreadLocal<>();
    private static volatile String summary="idle";
    private static volatile JSONObject lastState;
    private static final Object IO=new Object();
    private M9RenderCrash1D() {}
    public static synchronized void install(Context context) {
        if(app!=null)return;
        app=context.getApplicationContext();
        previous=read("m9-render-stage.json");previousJava=read("m9-render-java.json");
        Thread.UncaughtExceptionHandler parent=Thread.getDefaultUncaughtExceptionHandler();
        Thread.setDefaultUncaughtExceptionHandler((thread,error)->{
            try { JSONObject j=base();j.put("thread",thread.getName());j.put("error",error.toString());
                j.put("lastRender",lastState);j.put("stack",stack(error));persist("m9-render-java.json",j);
            }catch(Throwable ignored){}
            finally { if(parent!=null)parent.uncaughtException(thread,error);
                else { Process.killProcess(Process.myPid());System.exit(10); } }
        });
        Thread t=new Thread(M9RenderCrash1D::collect,"M9PreviousExitInfo");t.setDaemon(true);t.start();
    }
    private static JSONObject base() throws Exception {
        JSONObject j=new JSONObject();j.put("schema","m9cam.rendercrash.v1d");j.put("revision",ID);
        j.put("version",BuildConfig.VERSION_NAME);j.put("pid",Process.myPid());j.put("epochMs",System.currentTimeMillis());return j;
    }
    public static void begin(Path path) {
        try {JSONObject j=base();j.put("capture",path==null?JSONObject.NULL:path.getFileName().toString());
            j.put("thread",Thread.currentThread().getName());active.set(j);stage("setup");
        }catch(Throwable ignored){}
    }
    public static void stage(String stage) {
        JSONObject j=active.get();if(j==null||app==null)return;
        try {j.put("stage",stage);j.put("stageEpochMs",System.currentTimeMillis());
            Runtime r=Runtime.getRuntime();j.put("javaUsedBytes",r.totalMemory()-r.freeMemory());
            j.put("javaMaxBytes",r.maxMemory());j.put("nativeAllocatedBytes",Debug.getNativeHeapAllocatedSize());
            JSONObject copy=new JSONObject(j.toString());lastState=copy;persist("m9-render-stage.json",copy);
            summary="1D|"+Process.myPid()+"|"+j.getLong("epochMs")+"|"+stage;
            if(Build.VERSION.SDK_INT>=30){
                ActivityManager am=(ActivityManager)app.getSystemService(Context.ACTIVITY_SERVICE);
                // Only fixed stage names/process/time; never image contents or paths.
                if(am!=null)am.setProcessStateSummary(summary.getBytes(StandardCharsets.UTF_8));
            }
            Log.d(ID,copy.toString());
        }catch(Throwable ignored){}
    }
    public static void failure(Throwable t) {
        try {JSONObject j=active.get();if(j!=null){j.put("failedAt",j.optString("stage"));j.put("error",t.toString());j.put("stack",stack(t));stage("failed");
            Path dst=Environment.getExternalStorageDirectory().toPath().resolve("DCIM/PhotonCamera/M9_RENDER_FAILURE_"+j.getLong("epochMs")+".json");
            M9DiagnosticBurstSpool.stage(dst,j.toString(2).getBytes(StandardCharsets.UTF_8),ID);}
        }catch(Throwable ignored){}
    }
    public static void end(){active.remove();}
    public static void storageReady(){storageReady=true;export();}
    private static String stack(Throwable t){StringWriter w=new StringWriter();t.printStackTrace(new PrintWriter(w));String s=w.toString();return s.substring(0,Math.min(s.length(),32768));}
    private static JSONObject read(String name){
        try(InputStream in=new AtomicFile(new File(app.getFilesDir(),name)).openRead()){
            return new JSONObject(new String(bounded(in,2*1024*1024),StandardCharsets.UTF_8));
        }catch(Throwable ignored){return null;}
    }
    private static byte[] bounded(InputStream in,int limit)throws IOException {
        ByteArrayOutputStream b=new ByteArrayOutputStream();byte[] buf=new byte[8192];int n;
        while(b.size()<limit&&(n=in.read(buf,0,Math.min(buf.length,limit-b.size())))!=-1)b.write(buf,0,n);
        return b.toByteArray();
    }
    private static void persist(String name,JSONObject j){
        synchronized(IO){AtomicFile f=new AtomicFile(new File(app.getFilesDir(),name));FileOutputStream out=null;
            try{out=f.startWrite();out.write(j.toString().getBytes(StandardCharsets.UTF_8));f.finishWrite(out);}
            catch(Throwable e){if(out!=null)f.failWrite(out);}
        }
    }
    private static void collect(){
        try {JSONObject j=base();j.put("previousRenderCheckpoint",previous);j.put("previousJavaUncaught",previousJava);
            j.put("checkpointIsNotProofOfCrash",true);JSONArray exits=new JSONArray();
            if(Build.VERSION.SDK_INT>=30){
                ActivityManager am=(ActivityManager)app.getSystemService(Context.ACTIVITY_SERVICE);
                j.put("lowMemoryKillReportSupported",ActivityManager.isLowMemoryKillReportSupported());
                int traces=0;
                if(am!=null)for(ApplicationExitInfo e:am.getHistoricalProcessExitReasons(app.getPackageName(),0,8)){
                    JSONObject x=new JSONObject();x.put("pid",e.getPid());x.put("epochMs",e.getTimestamp());
                    x.put("reason",e.getReason());x.put("status",e.getStatus());x.put("description",e.getDescription());
                    x.put("process",e.getProcessName());x.put("pssSampleKb",e.getPss());x.put("rssSampleKb",e.getRss());
                    byte[] s=e.getProcessStateSummary();x.put("processState",s==null?JSONObject.NULL:new String(s,StandardCharsets.UTF_8));
                    if(traces<2&&(e.getReason()==ApplicationExitInfo.REASON_CRASH_NATIVE||e.getReason()==ApplicationExitInfo.REASON_ANR)){
                        try(InputStream in=e.getTraceInputStream()){
                            if(in!=null){byte[] bytes=bounded(in,LIMIT);x.put("traceBase64",Base64.encodeToString(bytes,Base64.NO_WRAP));
                                x.put("traceEncoding",e.getReason()==ApplicationExitInfo.REASON_CRASH_NATIVE&&Build.VERSION.SDK_INT>=31?"android_tombstone_protobuf":"system_trace");
                                x.put("traceTruncated",in.read()!=-1);traces++;}
                        }catch(Throwable t){x.put("traceError",t.toString());}
                    }
                    exits.put(x);
                }
            }else j.put("exitHistoryUnavailable","requires_API_30");
            j.put("exits",exits);report=j;persist("m9-render-exits.json",j);export();
        }catch(Throwable t){try{JSONObject j=base();j.put("collectionError",t.toString());j.put("previousRenderCheckpoint",previous);j.put("previousJavaUncaught",previousJava);report=j;persist("m9-render-exits.json",j);export();}catch(Throwable ignored){}}
    }
    private static void export(){
        JSONObject j=report;if(!storageReady||j==null||!exported.compareAndSet(false,true))return;
        Thread t=new Thread(()->{try{
            // Include the compact evidence in the usual exported log as well as a burst JSON.
            JSONObject compact=new JSONObject(j.toString());JSONArray exits=compact.optJSONArray("exits");
            if(exits!=null)for(int i=0;i<exits.length();i++)exits.getJSONObject(i).remove("traceBase64");
            Log.d(ID,compact.toString());
            Path dst=Environment.getExternalStorageDirectory().toPath().resolve("DCIM/PhotonCamera/M9_RENDER_EXIT_"+j.getLong("epochMs")+".json");
            if(!M9DiagnosticBurstSpool.stage(dst,j.toString(2).getBytes(StandardCharsets.UTF_8),ID))exported.set(false);
        }catch(Throwable ignored){exported.set(false);}},"M9ExitEvidenceExport");t.setDaemon(true);t.start();
    }
}
