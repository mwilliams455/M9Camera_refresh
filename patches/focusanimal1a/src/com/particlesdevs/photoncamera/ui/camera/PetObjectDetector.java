package com.particlesdevs.photoncamera.ui.camera;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.RectF;
import com.particlesdevs.photoncamera.control.subject.PetTargetPolicy;
import org.tensorflow.lite.support.image.TensorImage;
import org.tensorflow.lite.support.label.Category;
import org.tensorflow.lite.task.core.BaseOptions;
import org.tensorflow.lite.task.vision.detector.Detection;
import org.tensorflow.lite.task.vision.detector.ObjectDetector;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

/**
 * Self-contained offline COCO cat/dog detector.
 * Never makes network requests. The model is bundled at build-time and
 * inspected by SHA-256. Only category labels literally cat/dog are accepted;
 * no generic object-tracker confidence is sufficient.
 *
 * This class and TFLite Task Vision are owned exclusively by the inference
 * worker thread. The caller guarantees one outstanding inference at a time.
 */
final class PetObjectDetector implements AutoCloseable {
    static final String MODEL="efficientdet-lite0.tflite";
    private final ObjectDetector detector;
    private boolean closed;

    PetObjectDetector(Context appContext) throws IOException {
        ObjectDetector.ObjectDetectorOptions options =
            ObjectDetector.ObjectDetectorOptions.builder()
                .setBaseOptions(BaseOptions.builder().setNumThreads(2).build())
                .setScoreThreshold(.60f)
                .setMaxResults(8)
                .setLabelAllowList(Arrays.asList("cat", "dog"))
                .build();
        detector=ObjectDetector.createFromFileAndOptions(appContext,MODEL,options);
    }
    List<PetTargetPolicy.Candidate> detect(Bitmap image) {
        if(closed || image==null || image.isRecycled())return Collections.emptyList();
        ArrayList<PetTargetPolicy.Candidate> animals=new ArrayList<>();
        for(Detection detection:detector.detect(TensorImage.fromBitmap(image))) {
            RectF box=detection.getBoundingBox();
            if(box==null)continue;
            for(Category category:detection.getCategories()) {
                if(category==null || PetTargetPolicy.speciesFor(category.getLabel())==null)continue;
                animals.add(new PetTargetPolicy.Candidate(
                    category.getLabel(),category.getScore(),
                    clamp(box.left/image.getWidth()),
                    clamp(box.top/image.getHeight()),
                    clamp(box.right/image.getWidth()),
                    clamp(box.bottom/image.getHeight())));
            }
        }
        return animals;
    }
    private static float clamp(float x) {return Math.max(0f,Math.min(1f,x));}
    @Override public void close() {
        if(!closed) {
            closed=true;
            detector.close();
        }
    }
}
