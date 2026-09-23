package com.particlesdevs.photoncamera.m9.preview;

import android.app.Activity;
import android.content.Context;
import android.content.ContextWrapper;
import android.graphics.*;
import android.os.*;
import android.view.*;
import com.davemorrissey.labs.subscaleview.SubsamplingScaleImageView;
import org.json.*;

/** Small, unscaled surface/window crops. PixelCopy is a buffer readback, not a display calibration. */
public final class M9ShutterSurface1A {
    private static final Handler MAIN=new Handler(Looper.getMainLooper());
    private static int inFlight;
    private M9ShutterSurface1A(){}
    private static Activity activity(Context c){for(int i=0;i<12;i++){if(c instanceof Activity)return (Activity)c;if(!(c instanceof ContextWrapper))return null;c=((ContextWrapper)c).getBaseContext();}return null;}
    public static void preview(View view,String id,String event){copy(view,id,"preview",event,0);}
    public static void gallery(SubsamplingScaleImageView view,String filename) {
        String id=M9ShutterTrace1A.captureForFilename(filename);if(id==null)return;
        final boolean[] done={false};
        ViewTreeObserver.OnDrawListener listener=new ViewTreeObserver.OnDrawListener(){
            public void onDraw(){
                if(!done[0]&&view.isShown()&&view.isImageLoaded()) {
                    done[0]=true;
                    view.post(()->{if(view.getViewTreeObserver().isAlive())view.getViewTreeObserver().removeOnDrawListener(this);});
                    view.postDelayed(()->copy(view,id,"gallery",filename,0),500);
                }
            }
        };
        view.getViewTreeObserver().addOnDrawListener(listener);
        view.postDelayed(()->{if(!done[0]){done[0]=true;if(view.getViewTreeObserver().isAlive())view.getViewTreeObserver().removeOnDrawListener(listener);failure(id,"gallery",filename,"gallery_not_loaded_and_visible_within_15s");}},15000);
    }
    private static JSONObject geometry(View v)throws Exception {
        JSONObject o=new JSONObject().put("viewWidth",v.getWidth()).put("viewHeight",v.getHeight());
        int[] pos=new int[2];v.getLocationInWindow(pos);o.put("locationInWindow",new JSONArray(pos));
        if(v instanceof SubsamplingScaleImageView) {
            SubsamplingScaleImageView s=(SubsamplingScaleImageView)v;PointF c=s.getCenter();
            o.put("imageLoaded",s.isImageLoaded()).put("scale",s.getScale()).put("orientation",s.getAppliedOrientation())
                .put("sourceWidth",s.getSWidth()).put("sourceHeight",s.getSHeight());
            if(c!=null)o.put("center",new JSONArray(new float[]{c.x,c.y}));
        }
        return o;
    }
    private static void failure(String id,String kind,String event,String reason){try{M9ShutterTrace1A.surface(id,new JSONObject().put("kind",kind).put("event",event).put("pixelCopyResult",-1).put("reason",reason));}catch(Exception ignored){}}
    private static void copy(View v,String id,String kind,String event,int region) {
        if(v==null||!v.isAttachedToWindow()||!v.isShown()){failure(id,kind,event,"view_unavailable");return;}
        if(inFlight>=3){failure(id,kind,event,"bounded_readback_queue_full");return;}
        Bitmap dest=null,expected=null;
        try {
            boolean surface=v instanceof SurfaceView;
            if(kind.equals("preview")&&!surface){failure(id,kind,event,"preview_not_SurfaceView");return;}
            int w=v.getWidth(),h=v.getHeight();
            if(surface){Rect f=((SurfaceView)v).getHolder().getSurfaceFrame();w=f.width();h=f.height();}
            int size=Math.min(96,Math.min(w,h));if(size<=0)throw new IllegalStateException("empty view");
            int x=Math.max(0,Math.min(w-size,Math.round(w*(.25f+.25f*region)-size/2f))),y=(h-size)/2;
            Rect source=new Rect(x,y,x+size,y+size);
            JSONObject o=new JSONObject().put("kind",kind).put("event",event).put("region",region)
                .put("requestedElapsedNs",SystemClock.elapsedRealtimeNanos()).put("geometryBefore",geometry(v))
                .put("sourceRectXYWH",new JSONArray(new int[]{x,y,size,size})).put("sourceWidth",w).put("sourceHeight",h)
                .put("readbackDomain",surface?"latest_queued_SurfaceView_buffer":"latest_queued_Window_buffer")
                .put("physicalDisplayAppearanceVerified",false).put("sensorFrameJoinVerified",false)
                .put("lastSubmittedDrawBefore",M9ShutterTrace1A.drawSnapshot());
            dest=Bitmap.createBitmap(size,size,Bitmap.Config.ARGB_8888);
            M9ShutterRgb1A.Samples software=null;
            if(!surface) {
                if(v instanceof SubsamplingScaleImageView) {
                    PointF a=((SubsamplingScaleImageView)v).viewToSourceCoord(x,y),b=((SubsamplingScaleImageView)v).viewToSourceCoord(x+size,y+size);
                    if(a!=null&&b!=null)o.put("sourceImageBounds",new JSONArray(new float[]{a.x,a.y,b.x,b.y}));
                }
                expected=Bitmap.createBitmap(size,size,Bitmap.Config.ARGB_8888);Canvas c=new Canvas(expected);c.translate(-x,-y);v.draw(c);
                software=M9ShutterRgb1A.captureOne(expected);expected.recycle();expected=null;
            }
            final Bitmap target=dest;final M9ShutterRgb1A.Samples expectedPixels=software;
            Activity a=surface?null:activity(v.getContext());
            if(!surface&&a==null)throw new IllegalStateException("window unavailable");
            if(!surface){int[] pos=new int[2];v.getLocationInWindow(pos);source.offset(pos[0],pos[1]);
                View decor=a.getWindow().getDecorView();
                if(!new Rect(0,0,decor.getWidth(),decor.getHeight()).contains(source))throw new IllegalStateException("gallery_crop_outside_window");
            }
            PixelCopy.OnPixelCopyFinishedListener callback=code->{
                inFlight--;
                try {
                    o.put("pixelCopyResult",code).put("completedElapsedNs",SystemClock.elapsedRealtimeNanos())
                        .put("geometryAfter",geometry(v)).put("lastSubmittedDrawAfter",M9ShutterTrace1A.drawSnapshot());
                    o.put("geometryStable",o.getJSONObject("geometryBefore").toString().equals(o.getJSONObject("geometryAfter").toString()));
                    if(code==PixelCopy.SUCCESS)M9ShutterTrace1A.surfacePixels(id,o,M9ShutterRgb1A.captureOne(target),expectedPixels);
                    else M9ShutterTrace1A.surface(id,o);
                }catch(Throwable t){failure(id,kind,event,t.toString());}
                finally{target.recycle();}
                if(region<2)copy(v,id,kind,event,region+1);
            };
            inFlight++;
            try {if(surface)PixelCopy.request((SurfaceView)v,source,target,callback,MAIN);else PixelCopy.request(a.getWindow(),source,target,callback,MAIN);}
            catch(Throwable t){inFlight--;throw t;}
            dest=null;
        }catch(Throwable t){failure(id,kind,event,t.toString());}
        finally{if(dest!=null)dest.recycle();if(expected!=null)expected.recycle();}
    }
}
