import com.particlesdevs.photoncamera.control.tracking.SubjectAppearanceDescriptor;
public class SubjectAppearanceDescriptorTest {
    static int checks=0;
    static void yes(boolean v,String s){checks++;if(!v)throw new AssertionError(s);}
    static int argb(int r,int g,int b){return 0xff000000|r<<16|g<<8|b;}
    static int[] frame(int color,int width,int height){int[] a=new int[width*height];java.util.Arrays.fill(a,color);return a;}
    public static void main(String[] args){
        int w=120,h=120;
        SubjectAppearanceDescriptor blue=SubjectAppearanceDescriptor.sample(frame(argb(25,80,210),w,h),w,h,.1f,.1f,.8f,.95f);
        SubjectAppearanceDescriptor blueLight=SubjectAppearanceDescriptor.sample(frame(argb(40,120,244),w,h),w,h,.1f,.1f,.8f,.95f);
        SubjectAppearanceDescriptor red=SubjectAppearanceDescriptor.sample(frame(argb(220,40,25),w,h),w,h,.1f,.1f,.8f,.95f);
        SubjectAppearanceDescriptor gray=SubjectAppearanceDescriptor.sample(frame(argb(100,105,109),w,h),w,h,.1f,.1f,.8f,.95f);
        yes(blue!=null&&blue.informative(),"blue informative");
        yes(red!=null&&red.informative(),"red informative");
        yes(gray!=null&&!gray.informative(),"gray not reliable for identity");
        yes(blue.similarity(blueLight)>.90f,"brightness adjustment keeps hue");
        yes(blue.similarity(red)<.30f,"different shirts distinguishable");
        yes(Float.isNaN(blue.similarity(gray)),"weak signature cannot steal subject");
        yes(blue.blend(red,.05f).similarity(blue)>.90f,"reference update bounded");
        yes(SubjectAppearanceDescriptor.sample(null,w,h,.1f,.1f,.8f,.95f)==null,"null safe");
        yes(SubjectAppearanceDescriptor.sample(new int[10],w,h,.1f,.1f,.8f,.95f)==null,"short buffer safe");
        yes(SubjectAppearanceDescriptor.sample(frame(argb(1,2,3),w,h),w,h,Float.NaN,.1f,.8f,.95f)==null,"nan rejected");
        yes(SubjectAppearanceDescriptor.sample(frame(argb(1,2,3),w,h),w,h,.1f,.1f,1.1f,.95f)==null,"out of bound rejected");
        // Background of opposite colour outside the inner ROI must not dominate.
        int[] clutter=frame(argb(220,30,15),w,h);
        for(int y=30;y<100;y++)for(int x=33;x<89;x++)clutter[y*w+x]=argb(25,80,210);
        SubjectAppearanceDescriptor centre=SubjectAppearanceDescriptor.sample(clutter,w,h,.2f,.05f,.9f,.96f);
        yes(centre!=null&&centre.informative(),"usable inner ROI");
        yes(blue.similarity(centre)>.70f,"inner ROI excludes most background");
        System.out.println("PASS " + checks + " appearance safety checks");
    }
}
