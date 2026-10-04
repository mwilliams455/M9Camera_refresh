package com.particlesdevs.photoncamera.util;

import android.content.Context;
import android.os.Handler;
import android.os.HandlerThread;
import androidx.documentfile.provider.DocumentFile;
import com.anggrayudi.storage.file.DocumentFileCompat;
import com.anggrayudi.storage.file.DocumentFileType;
import com.anggrayudi.storage.file.StorageId;
import java.io.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

/** M9LOG1E: logging has no per-entry provider calls or persistent SAF descriptors. */
public class Log {
    private static volatile Context context;
    private static volatile M9LocalLog1E journal;
    private static volatile boolean visible,storageReady,logEnabled=true,stopped;
    private static final HandlerThread writeThread=new HandlerThread("LogWriterThread");
    private static final HandlerThread exportThread=new HandlerThread("LogExport1E");
    private static final Handler writeHandler,exportHandler;
    private static final AtomicInteger queuedChars=new AtomicInteger();
    private static final AtomicLong dropped=new AtomicLong();
    private static boolean flushPending;
    private static final Object exportLock=new Object();
    private static final int MAX_QUEUED_CHARS=1024*1024,MAX_ENTRY_CHARS=32768;
    static {writeThread.start();exportThread.start();writeHandler=new Handler(writeThread.getLooper());exportHandler=new Handler(exportThread.getLooper());}
    private static final Runnable FLUSH=()->{flushPending=false;try{M9LocalLog1E j=journal;if(j!=null)j.flush();}catch(Exception e){android.util.Log.w("M9LOG1E","private flush failed",e);}};
    private static final Runnable EXPORT=new Runnable(){public void run(){
        if(stopped||!visible||!storageReady)return;
        try{M9LocalLog1E j=journal;if(j!=null)j.exportOne(()->visible&&storageReady&&!stopped,Log::publish);}
        catch(Exception e){android.util.Log.w("M9LOG1E","public export deferred; private log retained",e);}
        synchronized(exportLock){exportHandler.removeCallbacks(this);if(visible&&storageReady&&!stopped)exportHandler.postDelayed(this,5000);}
    }};
    public static synchronized void initPrivate(Context c){
        if(context!=null||c==null)return;context=c.getApplicationContext();
        try{journal=new M9LocalLog1E(new File(context.getFilesDir(),"m9_logs"));}
        catch(Exception e){android.util.Log.e("M9LOG1E","private log initialization failed",e);}
    }
    public static void setAppVisible(boolean value){
        synchronized(exportLock){visible=value;exportHandler.removeCallbacks(EXPORT);
            if(value&&storageReady&&!stopped)exportHandler.postDelayed(EXPORT,1000);}
        writeHandler.post(()->{try{M9LocalLog1E j=journal;if(j!=null){j.flush();if(!value)j.close();}}catch(Exception e){android.util.Log.w("M9LOG1E","private lifecycle flush failed",e);}});
    }
    /** The camera has established storage access; public export is still visibility gated. */
    public static void setLogFolder(Context c){
        if(c!=null)initPrivate(c);
        synchronized(exportLock){storageReady=c!=null;exportHandler.removeCallbacks(EXPORT);
            if(visible&&storageReady&&!stopped)exportHandler.postDelayed(EXPORT,1000);}
        if(c!=null){com.particlesdevs.photoncamera.m9.render.M9RenderCrash1D.storageReady();
            writeHandler.post(()->{M9LocalLog1E j=journal;if(j!=null)j.cleanup(System.currentTimeMillis());});}
    }
    @Deprecated public static void setLogFile(File folder){
        storageReady=false;exportHandler.removeCallbacks(EXPORT);
        writeHandler.post(()->{try{if(journal!=null)journal.close();journal=folder==null?null:new M9LocalLog1E(folder);}catch(Exception e){android.util.Log.w("M9LOG1E","local log folder failed",e);}});
    }
    private static boolean publish(String filename,byte[] bytes)throws Exception {
        Context c=context;if(c==null||!visible||!storageReady)return false;
        // Resolution happens per bounded batch, never on a logging/camera caller.
        if(!SimpleStorageHelper.hasStorageAccess(c))return false;
        DocumentFile root=DocumentFileCompat.fromSimplePath(c,StorageId.PRIMARY,SimpleStorageHelper.PHOTON_CAMERA_RELATIVE_PATH,DocumentFileType.FOLDER,true);
        if(root==null||!visible)return false;
        DocumentFile folder=root.findFile("PhotonLog");if(folder==null)folder=root.createDirectory("PhotonLog");
        if(folder==null||!visible)return false;
        DocumentFile file=folder.findFile(filename);if(file==null)file=folder.createFile("text/plain",filename);
        if(file==null||!visible)return false;
        try(OutputStream out=c.getContentResolver().openOutputStream(file.getUri(),"wa")){
            if(out==null)return false;out.write(bytes);out.flush();
        }
        return true;
    }
    private static void writeToFile(String level,String tag,String text){
        if(!logEnabled||stopped||journal==null)return;
        String message=String.valueOf(text);if(message.length()>MAX_ENTRY_CHARS)message=message.substring(0,MAX_ENTRY_CHARS)+" [M9LOG1E entry truncated]";
        final String value=message;final int n=value.length()+String.valueOf(tag).length()+64;
        if(queuedChars.addAndGet(n)>MAX_QUEUED_CHARS){queuedChars.addAndGet(-n);dropped.incrementAndGet();return;}
        final long timestamp=System.currentTimeMillis();
        if(!writeHandler.post(()->{try{M9LocalLog1E j=journal;if(j!=null){
            long loss=dropped.getAndSet(0);if(loss>0)j.append(timestamp,"W","M9LOG1E","log queue overflow; dropped entries="+loss);
            j.append(timestamp,level,tag,value);if(!flushPending){flushPending=true;writeHandler.postDelayed(FLUSH,1000);}
        }}catch(Exception e){android.util.Log.w("M9LOG1E","private append failed",e);}finally{queuedChars.addAndGet(-n);}}))queuedChars.addAndGet(-n);
    }
    public static void d(String t,String m){if(logEnabled){android.util.Log.d(t,m);writeToFile("D",t,m);}}
    public static void i(String t,String m){if(logEnabled){android.util.Log.i(t,m);writeToFile("I",t,m);}}
    public static void v(String t,String m){if(logEnabled){android.util.Log.v(t,m);writeToFile("V",t,m);}}
    public static void w(String t,String m){if(logEnabled){android.util.Log.w(t,m);writeToFile("W",t,m);}}
    public static void w(String t,String m,Throwable e){if(logEnabled){android.util.Log.w(t,m,e);writeToFile("W",t,m+"\n"+android.util.Log.getStackTraceString(e));}}
    public static void e(String t,String m){if(logEnabled){android.util.Log.e(t,m);writeToFile("E",t,m);}}
    public static void e(String t,String m,Throwable e){if(logEnabled){android.util.Log.e(t,m,e);writeToFile("E",t,m+"\n"+android.util.Log.getStackTraceString(e));}}
    public static String getStackTraceString(Exception e){String s=android.util.Log.getStackTraceString(e);writeToFile("E","Exception",s);return s;}
    public static void setLogEnabled(boolean enabled){logEnabled=enabled;}
    public static void shutdown(){stopped=true;exportHandler.removeCallbacks(EXPORT);writeHandler.post(()->{try{if(journal!=null)journal.close();}catch(Exception ignored){}});writeThread.quitSafely();exportThread.quitSafely();}
}
