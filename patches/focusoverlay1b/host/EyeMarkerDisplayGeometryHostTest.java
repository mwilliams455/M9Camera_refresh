import com.particlesdevs.photoncamera.ui.camera.views.FocusTickGeometry;

/** Pure Java: the selected optical AF target and size must never be rewritten. */
public final class EyeMarkerDisplayGeometryHostTest {
    private static int checks;
    private static void near(float actual,float expected,String label) {
        checks++;
        if(Math.abs(actual-expected)>.001f) throw new AssertionError(label+": "+actual+" != "+expected);
    }
    private static void yes(boolean value,String label) {
        checks++;
        if(!value) throw new AssertionError(label);
    }
    public static void main(String[] args) {
        near(FocusTickGeometry.eyeDisplayHalfWidth(80f,1f),17f,"wide eye limit");
        near(FocusTickGeometry.eyeDisplayHalfHeight(80f,1f),13f,"short eye limit");
        near(FocusTickGeometry.eyeDisplayHalfWidth(180f,3f),51f,"3x width");
        near(FocusTickGeometry.eyeDisplayHalfHeight(180f,3f),39f,"3x height");
        near(FocusTickGeometry.eyeDisplayHalfWidth(8f,1f),8f,"small eye width retained");
        near(FocusTickGeometry.eyeDisplayHalfHeight(8f,1f),8f,"small eye height retained");
        near(FocusTickGeometry.eyeDisplayHalfWidth(Float.NaN,1f),0f,"NaN safe");
        near(FocusTickGeometry.eyeDisplayHalfHeight(Float.POSITIVE_INFINITY,1f),0f,"infinity safe");
        near(FocusTickGeometry.eyeDisplayHalfWidth(40f,0f),0f,"invalid density");
        near(FocusTickGeometry.eyeDisplayHalfHeight(-4f,1f),0f,"invalid AF half height");
        float[] visible=new float[32];
        float originalAfHalfWidth=80f, originalAfHalfHeight=80f;
        float x=400f, y=300f;
        float width=FocusTickGeometry.eyeDisplayHalfWidth(originalAfHalfWidth,3f);
        float height=FocusTickGeometry.eyeDisplayHalfHeight(originalAfHalfHeight,3f);
        yes(FocusTickGeometry.populate(x,y,width,height,800f,700f,3f,visible),"render compact");
        near(visible[0],x-51f,"display left");
        near(visible[1],y-39f,"display top");
        near(visible[10],x+51f,"display right");
        near(visible[31],y+39f,"display bottom");
        near(originalAfHalfWidth,80f,"AF region width untouched");
        near(originalAfHalfHeight,80f,"AF region height untouched");
        yes((visible[10]-visible[0])<2*originalAfHalfWidth,"compact compared with AF region");
        near((visible[10]+visible[0])*.5f,x,"center x unchanged");
        near((visible[31]+visible[1])*.5f,y,"center y unchanged");
        System.out.println("PASS EyeMarkerDisplayGeometryHostTest: "+checks+" checks");
    }
}
