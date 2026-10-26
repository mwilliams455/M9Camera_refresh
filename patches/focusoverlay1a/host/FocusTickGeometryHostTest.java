import com.particlesdevs.photoncamera.ui.camera.views.FocusTickGeometry;

public final class FocusTickGeometryHostTest {
    private static int checks;
    private static final float EPS = 0.001f;
    private static void ok(boolean b, String why) {
        checks++;
        if (!b) throw new AssertionError(why);
    }
    private static void near(float a, float b, String why) {
        ok(Math.abs(a-b) < EPS, why + " expected " + b + " got " + a);
    }
    private static float[] make(float x, float y, float halfX, float halfY,
                                float w, float h, float d) {
        float[] a = new float[32];
        ok(FocusTickGeometry.populate(x,y,halfX,halfY,w,h,d,a), "valid geometry");
        return a;
    }
    private static void bounds(float[] p, float w, float h) {
        for (int i=0; i<32; i+=2) {
            ok(p[i] >= 0f && p[i] <= w, "clipped x " + i);
            ok(p[i+1] >= 0f && p[i+1] <= h, "clipped y " + i);
        }
    }
    public static void main(String[] args) {
        float[] a = make(150,100,25,20,300,200,1);
        // Exactly four open 90-degree brackets in original input coordinates.
        near(a[0],125,"TL left"); near(a[1],80,"TL top");
        near(a[4],125,"TL vertical"); near(a[8+2],175,"TR right");
        near(a[12],175,"TR vertical"); near(a[16],125,"BL left");
        near(a[17],120,"BL bottom"); near(a[26],175,"BR right");
        near(a[29],120,"BR bottom");
        for (int i=0; i<32; i+=4) {
            float dx=Math.abs(a[i+2]-a[i]);
            float dy=Math.abs(a[i+3]-a[i+1]);
            ok((dx>0&&dy==0)||(dx==0&&dy>0), "straight independent segment " + i);
            ok(Math.max(dx,dy) >= 6f && Math.max(dx,dy) <= 11f,"balanced leg bounds");
        }
        float[] b=make(180,135,25,20,300,200,1);
        near(b[0]-a[0],30,"translation x");
        near(b[1]-a[1],35,"translation y");
        float[] small=make(100,100,1,1,200,200,1);
        near(small[0],90,"eye visual minimum not AF resize");
        near(small[1],90,"eye visual min Y");
        float[] dense=make(150,100,50,40,300,200,2);
        near(dense[0],100,"preserve supplied halfX when larger than min");
        near(dense[1],60,"preserve supplied halfY when larger than min");
        bounds(dense,300,200);
        bounds(make(7,9,15,15,200,200,2),200,200);
        bounds(make(194,193,15,15,200,200,2),200,200);
        float[] tiny = new float[32];
        ok(!FocusTickGeometry.populate(-50,20,4,4,100,100,1,tiny),"fully outside frame");
        ok(!FocusTickGeometry.populate(Float.NaN,20,4,4,100,100,1,tiny),"NaN rejected");
        ok(!FocusTickGeometry.populate(20,Float.POSITIVE_INFINITY,4,4,100,100,1,tiny),"Inf rejected");
        ok(!FocusTickGeometry.populate(20,20,-1,4,100,100,1,tiny),"negative halfX rejected");
        ok(!FocusTickGeometry.populate(20,20,4,4,100,100,0,tiny),"bad density rejected");
        ok(!FocusTickGeometry.populate(20,20,4,4,0,100,1,tiny),"bad viewport rejected");
        try {
            FocusTickGeometry.populate(20,20,4,4,100,100,1,new float[31]);
            throw new AssertionError("undersized array accepted");
        } catch (IllegalArgumentException expected) { checks++; }
        System.out.println("PASS FocusTickGeometryHostTest: " + checks + " geometry assertions");
    }
}
