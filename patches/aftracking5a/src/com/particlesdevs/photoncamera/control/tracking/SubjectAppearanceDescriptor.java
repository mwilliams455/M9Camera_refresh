package com.particlesdevs.photoncamera.control.tracking;

/**
 * Local, intentionally weak appearance evidence for an already tapped subject.
 * It is NOT face recognition, a biometric embedding, or a persistent person ID.
 * 12-bin hue/neutral histogram uses only the centre of the selected detected
 * body to reduce background bleed. No image or descriptor is saved to disk.
 */
public final class SubjectAppearanceDescriptor {
    public static final int BINS = 12;
    private final float[] histogram;
    public final float chromaticFraction;
    private final boolean informative;
    private SubjectAppearanceDescriptor(float[] h, float chromaticFraction, boolean informative) {
        this.histogram=h; this.chromaticFraction=chromaticFraction; this.informative=informative;
    }
    /** Sample pre-copied upright PixelCopy ARGB pixels, never from a RAW/DNG. */
    public static SubjectAppearanceDescriptor sample(int[] pixels, int width, int height,
                                                     float left,float top,float right,float bottom) {
        if(pixels==null||width<32||height<32||pixels.length < (long)width*height||
                !ok(left)||!ok(top)||!ok(right)||!ok(bottom)||
                left<0||top<0||right>1||bottom>1||right-left<.07f||bottom-top<.09f)
            return null;
        float[] bins=new float[BINS];
        int samples=0,colorSamples=0;
        // Use central subject pixels, bias towards torso rather than faces,
        // and never sample arbitrary areas outside the detector's body box.
        for(int gy=0;gy<12;gy++){
            float fy=top+(bottom-top)*(.25f+(.66f*(gy+.5f)/12f));
            int py=Math.min(height-1,Math.max(0,(int)(fy*height)));
            for(int gx=0;gx<12;gx++){
                float fx=left+(right-left)*(.20f+.60f*(gx+.5f)/12f);
                int px=Math.min(width-1,Math.max(0,(int)(fx*width)));
                int argb=pixels[py*width+px];
                int r=(argb>>16)&255,g=(argb>>8)&255,b=argb&255;
                int max=Math.max(r,Math.max(g,b)),min=Math.min(r,Math.min(g,b));
                int delta=max-min;
                int bin;
                if(max<28)bin=8; // dark / no measurable colour
                else if(delta<25||delta*100<max*16) {
                    bin=max<96?9:max<192?10:11;
                } else {
                    colorSamples++;
                    // Standard piecewise HSV hue; quantized to eight circular bins.
                    float hue;
                    if(max==r)hue=60f*(g-b)/(float)delta;
                    else if(max==g)hue=120f+60f*(b-r)/(float)delta;
                    else hue=240f+60f*(r-g)/(float)delta;
                    if(hue<0)hue+=360f;
                    bin=Math.min(7,(int)((hue+22.5f)%360f/45f));
                }
                bins[bin] += 1f;
                samples++;
            }
        }
        if(samples<60)return null;
        for(int i=0;i<BINS;i++)bins[i]/=samples;
        float colorFraction=colorSamples/(float)samples;
        // A largely grey/black/white patch cannot reliably distinguish people.
        return new SubjectAppearanceDescriptor(bins,colorFraction,colorFraction>=.18f);
    }
    public boolean informative(){return informative;}
    public float similarity(SubjectAppearanceDescriptor other){
        if(other==null||!informative||!other.informative)return Float.NaN;
        float overlap=0;
        for(int i=0;i<BINS;i++)overlap+=Math.min(histogram[i],other.histogram[i]);
        return Math.min(1f,Math.max(0f,overlap));
    }
    public SubjectAppearanceDescriptor blend(SubjectAppearanceDescriptor next,float updateFraction){
        if(next==null||!informative||!next.informative||!Float.isFinite(updateFraction))return this;
        float k=Math.min(.10f,Math.max(0f,updateFraction));
        float[] out=new float[BINS];
        for(int i=0;i<BINS;i++)out[i]=histogram[i]*(1-k)+next.histogram[i]*k;
        return new SubjectAppearanceDescriptor(out,
                chromaticFraction*(1-k)+next.chromaticFraction*k,true);
    }
    private static boolean ok(float f){return Float.isFinite(f);}
}
