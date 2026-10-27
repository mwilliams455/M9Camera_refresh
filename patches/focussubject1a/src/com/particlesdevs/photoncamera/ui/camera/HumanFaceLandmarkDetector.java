package com.particlesdevs.photoncamera.ui.camera;

import android.graphics.Bitmap;
import android.graphics.PointF;
import android.graphics.Rect;
import com.google.mlkit.vision.common.InputImage;
import com.google.mlkit.vision.face.Face;
import com.google.mlkit.vision.face.FaceDetection;
import com.google.mlkit.vision.face.FaceDetector;
import com.google.mlkit.vision.face.FaceDetectorOptions;
import com.google.mlkit.vision.face.FaceLandmark;
import com.particlesdevs.photoncamera.control.subject.SubjectFocusPolicy;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Consumer;

/**
 * Bundled/offline ML Kit face + eye-landmark detector. Inputs are PixelCopy
 * bitmaps of the already-upright displayed viewfinder, NOT RAW sensor images.
 * No network permission, face image storage, or background model download.
 *
 * Only one call may be outstanding; enforced by HumanSubjectFocusController.
 */
final class HumanFaceLandmarkDetector implements AutoCloseable {
    private final FaceDetector detector;
    private boolean closed;

    HumanFaceLandmarkDetector() {
        FaceDetectorOptions options = new FaceDetectorOptions.Builder()
                .setPerformanceMode(FaceDetectorOptions.PERFORMANCE_MODE_FAST)
                .setLandmarkMode(FaceDetectorOptions.LANDMARK_MODE_ALL)
                .setMinFaceSize(.12f)
                .enableTracking()
                .build();
        detector = FaceDetection.getClient(options);
    }

    void process(Bitmap preview, Consumer<List<SubjectFocusPolicy.Face>> success,
                 Consumer<Exception> failed) {
        if (closed) {
            failed.accept(new IllegalStateException("Face detector is closed"));
            return;
        }
        try {
            // PixelCopy source is the visible, rotated/mirrored preview viewport.
            // Applying the camera sensor rotation again would misplace the eyes.
            detector.process(InputImage.fromBitmap(preview, 0))
                    .addOnSuccessListener(faces -> {
                        ArrayList<SubjectFocusPolicy.Face> output = new ArrayList<>();
                        int fallbackId = -1;
                        for (Face face : faces) {
                            Rect box = face.getBoundingBox();
                            float l = clamp((float) box.left / preview.getWidth());
                            float t = clamp((float) box.top / preview.getHeight());
                            float r = clamp((float) box.right / preview.getWidth());
                            float b = clamp((float) box.bottom / preview.getHeight());
                            if (!(r > l && b > t)) continue;
                            Integer id = face.getTrackingId();
                            FaceLandmark left = face.getLandmark(FaceLandmark.LEFT_EYE);
                            FaceLandmark right = face.getLandmark(FaceLandmark.RIGHT_EYE);
                            FaceLandmark nose = face.getLandmark(FaceLandmark.NOSE_BASE);
                            FaceLandmark mouth = face.getLandmark(FaceLandmark.MOUTH_BOTTOM);
                            float lx = pointX(left, preview.getWidth());
                            float ly = pointY(left, preview.getHeight());
                            float rx = pointX(right, preview.getWidth());
                            float ry = pointY(right, preview.getHeight());
                            float nx = pointX(nose, preview.getWidth());
                            float ny = pointY(nose, preview.getHeight());
                            float mx = pointX(mouth, preview.getWidth());
                            float my = pointY(mouth, preview.getHeight());
                            output.add(new SubjectFocusPolicy.Face(
                                    id == null ? fallbackId-- : id,
                                    l, t, r, b, lx, ly, rx, ry,
                                    nx, ny, mx, my));
                        }
                        success.accept(output);
                    })
                    .addOnFailureListener(failed::accept);
        } catch (RuntimeException error) {
            failed.accept(error);
        }
    }

    private static float pointX(FaceLandmark eye, int width) {
        if (eye == null) return Float.NaN;
        PointF p = eye.getPosition();
        return p == null ? Float.NaN : p.x / width;
    }
    private static float pointY(FaceLandmark eye, int height) {
        if (eye == null) return Float.NaN;
        PointF p = eye.getPosition();
        return p == null ? Float.NaN : p.y / height;
    }
    private static float clamp(float value) {
        return Math.max(0f, Math.min(1f, value));
    }

    @Override public void close() {
        if (!closed) {
            closed = true;
            detector.close();
        }
    }
}
