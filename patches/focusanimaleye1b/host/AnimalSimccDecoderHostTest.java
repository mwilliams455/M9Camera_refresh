import com.particlesdevs.photoncamera.control.subject.AnimalSimccDecoder;
import com.particlesdevs.photoncamera.control.subject.AnimalEyeTargetPolicy;

public final class AnimalSimccDecoderHostTest {
    private static void check(boolean ok,String msg){if(!ok)throw new AssertionError(msg);}
    private static final int K=17,B=512;
    private static void spike(float[] x,float[] y,int kp,int xi,int yi,float xc,float yc) {
        x[kp*B+xi]=xc;y[kp*B+yi]=yc;
    }
    public static void main(String[] ignored) {
        float[] x=new float[K*B],y=new float[K*B];
        java.util.Arrays.fill(x,-.01f);
        java.util.Arrays.fill(y,-.01f);
        spike(x,y,0,240,300,.85f,.68f);
        AnimalEyeTargetPolicy.Point eye=AnimalSimccDecoder.decode(x,y,0,
                50f,20f,200f,400,400);
        check(eye.valid(.38f),"raw SimCC peak should qualify against eye threshold");
        check(Math.abs(eye.score-.68f)<.00001f,"MMPose min(max X,max Y) response required");
        check(Math.abs(eye.x-(50f+120f*200f/256f)/400f)<.00001f,
                "x bin and pet crop mapping");
        check(Math.abs(eye.y-(20f+150f*200f/256f)/400f)<.00001f,
                "y bin and pet crop mapping");
        // Wrong approach: applying normalized softmax across 512 logits
        // turns a legitimate 0.68 response into roughly ~0.004.
        double denomX=511*Math.exp(-.01)+Math.exp(.85);
        double denomY=511*Math.exp(-.01)+Math.exp(.68);
        check(Math.sqrt(Math.exp(.85)/denomX*Math.exp(.68)/denomY)<.02,
                "Old 3.02 confidence decoder was not raw SimCC");
        check(!AnimalSimccDecoder.decode(x,y,1,50,20,200,400,400).valid(.38f),
                "Missing eye cannot be hallucinated from background bins");
        float[] bad=x.clone();bad[240]=Float.NaN;
        check(!AnimalSimccDecoder.decode(bad,y,0,50,20,200,400,400).valid(.38f),
                "non-finite raw result cannot become confidence");
        check(!AnimalSimccDecoder.decode(x,y,17,50,20,200,400,400).valid(.38f),
                "invalid keypoint number");
        check(!AnimalSimccDecoder.decode(x,y,0,50,20,200,0,400).valid(.38f),
                "zero width");
        System.out.println("PASS: AnimalSimccDecoderHostTest (raw peak confidence, coordinates, absent/NaN)");
    }
}
