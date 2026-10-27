package com.particlesdevs.photoncamera.ui.camera;

import android.graphics.Canvas;
import android.graphics.ColorFilter;
import android.graphics.Paint;
import android.graphics.PixelFormat;
import android.graphics.drawable.Drawable;
import android.view.View;

/**
 * Labels HAL autofocus separately from subject recognition. The Camera2 HAL
 * reports its belief about focus; this is NOT proof that the eye is sharp.
 */
final class FocusAfStatusBadge extends Drawable {
    private final View host;
    private final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);
    private String label="AF: unknown";
    FocusAfStatusBadge(View host){this.host=host;}
    void update(String message){
        label=message==null?"AF: unknown":message;
        setBounds(0,0,host.getWidth(),host.getHeight());
        invalidateSelf();
    }
    @Override public void draw(Canvas canvas){
        if(host.getWidth()<=0||host.getHeight()<=0)return;
        float d=host.getResources().getDisplayMetrics().density;
        paint.setStyle(Paint.Style.FILL);paint.setTextSize(12*d);
        String text=label.length()>62?label.substring(0,62):label;
        float width=paint.measureText(text),x=13*d;
        float y=Math.max(25*d,Math.min(host.getHeight()*.24f,78*d));
        paint.setColor(0xdb000000);
        canvas.drawRoundRect(x-5*d,y-16*d,
                Math.min(host.getWidth()-4*d,x+width+6*d),y+5*d,5*d,5*d,paint);
        paint.setColor(0xffffffff);
        canvas.drawText(text,x,y,paint);
    }
    @Override public void setAlpha(int value){}
    @Override public void setColorFilter(ColorFilter filter){}
    @Override public int getOpacity(){return PixelFormat.TRANSLUCENT;}
}
