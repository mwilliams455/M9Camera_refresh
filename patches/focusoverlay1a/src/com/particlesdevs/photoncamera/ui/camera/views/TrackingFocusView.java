package com.particlesdevs.photoncamera.ui.camera.views;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.util.AttributeSet;
import android.view.View;
import com.particlesdevs.photoncamera.R;

/** Tracking confidence is deliberately not represented as a green focus-lock indicator. */
public final class TrackingFocusView extends View {
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final float[] ticks = new float[32];
    private float x, y, halfX, halfY;
    private boolean lost, holding, pending;
    public TrackingFocusView(Context context, AttributeSet attrs) { super(context, attrs); }
    public void show(float x, float y, float halfX, float halfY, boolean lost) {
        this.x = x; this.y = y; this.halfX = halfX; this.halfY = halfY;
        this.lost = lost; this.holding = false; this.pending = false;
        setVisibility(VISIBLE);
        setContentDescription(getContext().getString(lost ? R.string.focus_tracking_lost : R.string.focus_tracking_active));
        invalidate();
    }
    /** Read-only amber hold indication, never a claimed focused/locked state. */
    public void showHolding(float x, float y, float halfX, float halfY) {
        this.x = x; this.y = y; this.halfX = halfX; this.halfY = halfY;
        lost = false; holding = true; pending = false;
        setVisibility(VISIBLE);
        setContentDescription(getContext().getString(R.string.focus_tracking_hold3a));
        invalidate();
    }
    /** Amber but explicitly labels pending recognition, not occlusion. */
    public void showPending(float x,float y,float halfX,float halfY){
        this.x=x;this.y=y;this.halfX=halfX;this.halfY=halfY;
        lost=false;holding=false;pending=true;
        setVisibility(VISIBLE);
        setContentDescription(getContext().getString(R.string.focus_tracking_pending3b));
        invalidate();
    }
    // Existing show/showHolding/showPending calls own exactly the same AF target.
    @Override protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        float density = getResources().getDisplayMetrics().density;
        if (!FocusTickGeometry.populate(x, y, halfX, halfY,
                getWidth(), getHeight(), density, ticks)) return;
        boolean uncertain = holding || pending || lost;
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeCap(Paint.Cap.ROUND);
        // Dual stroke is reliable on hardware Canvas; unlike an animated/glowing
        // shadow it needs no extra layer and stays readable on bright backgrounds.
        paint.setColor(0x99000000);
        paint.setStrokeWidth(3f * density);
        canvas.drawLines(ticks, paint);
        paint.setColor(uncertain ? 0xffffba59 : 0xfffcfcf8);
        paint.setStrokeWidth(1.5f * density);
        canvas.drawLines(ticks, paint);

        // Active tracking has NO persistent text plaque. Important amber states
        // remain visually distinguishable and accessible by original description.
        if (uncertain) {
            paint.setStyle(Paint.Style.FILL);
            paint.setTextSize(11f * density);
            String label = getContext().getString(pending ? R.string.focus_tracking_pending3b :
                    holding ? R.string.focus_tracking_hold3a : R.string.focus_tracking_lost);
            float textX = Math.max(4f * density,
                    Math.min(getWidth() - paint.measureText(label) - 4f * density, x - halfX));
            paint.setShadowLayer(2f * density, 0f, 0f, 0xff000000);
            canvas.drawText(label, textX, Math.max(16f * density,
                    y - halfY - 6f * density), paint);
            paint.clearShadowLayer();
        }
    }
}
