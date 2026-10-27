package com.particlesdevs.photoncamera.ui.camera;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.RectF;
import com.google.mediapipe.framework.image.BitmapImageBuilder;
import com.google.mediapipe.framework.image.MPImage;
import com.google.mediapipe.tasks.core.BaseOptions;
import com.google.mediapipe.tasks.components.containers.Category;
import com.google.mediapipe.tasks.components.containers.Detection;
import com.google.mediapipe.tasks.vision.core.RunningMode;
import com.google.mediapipe.tasks.vision.objectdetector.ObjectDetector;
import com.google.mediapipe.tasks.vision.objectdetector.ObjectDetectorResult;
import com.particlesdevs.photoncamera.control.tracking.SubjectAnchorPolicy;
import java.util.ArrayList;
import java.util.List;

/**
 * Optional identity anchor for arbitrary tap-to-track. Reuses the app's existing
 * pinned COCO EfficientDet-Lite0 asset and MediaPipe dependency. No network or
 * additional model is required, and no inference may run on UI/camera threads.
 *
 * Only the single tracking worker owns this object and the inference bitmap.
 */
final class TrackingSemanticDetector implements AutoCloseable {
    private final ObjectDetector detector;
    private boolean closed;
    TrackingSemanticDetector(Context appContext){
        ObjectDetector.ObjectDetectorOptions options=ObjectDetector.ObjectDetectorOptions.builder()
            .setBaseOptions(BaseOptions.builder().setModelAssetPath("efficientdet-lite0.tflite").build())
            .setRunningMode(RunningMode.IMAGE)
            .setScoreThreshold(.16f)
            .setMaxResults(25)
            .build();
        detector=ObjectDetector.createFromOptions(appContext,options);
    }
    List<SubjectAnchorPolicy.Candidate> detect(Bitmap frame){
        List<SubjectAnchorPolicy.Candidate> candidates=new ArrayList<>();
        if(closed||frame==null||frame.isRecycled())return candidates;
        // IMPORTANT: MPImage.close() recycles the bitmap. Isolate MediaPipe's
        // ownership from PixelCopy and the patch tracker (3.03 fix retained).
        Bitmap modelBitmap=frame.copy(Bitmap.Config.ARGB_8888,false);
        if(modelBitmap==null)throw new IllegalStateException("tracking model frame copy failed");
        MPImage image;
        try{image=new BitmapImageBuilder(modelBitmap).build();}
        catch(RuntimeException e){if(!modelBitmap.isRecycled())modelBitmap.recycle();throw e;}
        try{
            ObjectDetectorResult result=detector.detect(image);
            for(Detection detection:result.detections()){
                RectF b=detection.boundingBox();if(b==null)continue;
                for(Category c:detection.categories()){
                    if(c==null||SubjectAnchorPolicy.classify(c.categoryName())==null)continue;
                    candidates.add(new SubjectAnchorPolicy.Candidate(c.categoryName(),c.score(),
                        clamp(b.left/frame.getWidth()),clamp(b.top/frame.getHeight()),
                        clamp(b.right/frame.getWidth()),clamp(b.bottom/frame.getHeight())));
                }
            }
        }finally{image.close();}
        if(frame.isRecycled())throw new IllegalStateException("shared tracking frame recycled");
        return candidates;
    }
    private static float clamp(float x){return Math.max(0f,Math.min(1f,x));}
    @Override public void close(){if(!closed){closed=true;detector.close();}}
}

