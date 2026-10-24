package com.particlesdevs.photoncamera.ui.camera;

import android.graphics.Canvas;
import android.graphics.ColorFilter;
import android.graphics.Paint;
import android.graphics.PixelFormat;
import android.graphics.drawable.Drawable;
import android.view.View;

/** Opt-in pet AF test-only status, shown only while the feature is enabled. */
final class PetAfStatusBadge extends Drawable {
    private final View host;
    private final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);
    private String status="Pet AF: starting";
    PetAfStatusBadge(View host){this.host=host;}
    void status(String text) {
        status=text==null?"Pet AF: unknown":text;
        setBounds(0,0,host.getWidth(),host.getHeight());
        invalidateSelf();
    }
    @Override public void draw(Canvas canvas) {
        if(host.getWidth()<=0||host.getHeight()<=0)return;
        float d=host.getResources().getDisplayMetrics().density;
        paint.setTextSize(11*d);
        paint.setStyle(Paint.Style.FILL);
        String shown=status.length()>58?status.substring(0,58):status;
        float x=12*d,y=Math.min(host.getHeight()-45*d,115*d);
        float textWidth=paint.measureText(shown);
        paint.setColor(0xd6000000);
        canvas.drawRoundRect(x-6*d,y-16*d,
                Math.min(host.getWidth()-5*d,x+textWidth+7*d),y+5*d,4*d,4*d,paint);
        paint.setColor(0xffeeeeee);
        canvas.drawText(shown,x,y,paint);
    }
    @Override public void setAlpha(int alpha){}
    @Override public void setColorFilter(ColorFilter filter){}
    @Override public int getOpacity(){return PixelFormat.TRANSLUCENT;}
}
