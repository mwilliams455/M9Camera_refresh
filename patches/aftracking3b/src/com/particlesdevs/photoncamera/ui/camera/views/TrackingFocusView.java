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
    @Override protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        float density = getResources().getDisplayMetrics().density;
        paint.setColor(holding || pending || lost ? 0xffffba59 : 0xffffffff); paint.setStrokeWidth(2 * density);
        paint.setStyle(Paint.Style.STROKE);
        canvas.drawRect(x - halfX, y - halfY, x + halfX, y + halfY, paint);
        paint.setStyle(Paint.Style.FILL); paint.setTextSize(13 * density);
        paint.setShadowLayer(3 * density, 0, 0, 0xff000000);
        String label = getContext().getString(pending ? R.string.focus_tracking_pending3b :
                holding ? R.string.focus_tracking_hold3a :
                lost ? R.string.focus_tracking_lost : R.string.focus_tracking_active);
        float textX = Math.max(4 * density, Math.min(getWidth() - paint.measureText(label) - 4 * density, x - halfX));
        canvas.drawText(label, textX, Math.max(18 * density, y - halfY - 6 * density), paint);
        paint.clearShadowLayer();
    }
}

