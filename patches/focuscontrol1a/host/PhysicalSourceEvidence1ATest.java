import com.particlesdevs.photoncamera.m9.provenance.PhysicalSourceEvidence1A;
public final class PhysicalSourceEvidence1ATest {
    static void check(boolean yes,String why){if(!yes)throw new AssertionError(why);}
    static PhysicalSourceEvidence1A.Status result(boolean same,boolean physical,
            boolean characteristics,boolean calibration,boolean shading,
            boolean noError,boolean levels,boolean active) {
        return PhysicalSourceEvidence1A.classify(same,physical,characteristics,
                calibration,shading,noError,levels,active);
    }
    public static void main(String[] a) {
        var good=PhysicalSourceEvidence1A.Status.CAPTURE_SOURCE_PRESENT;
        var missing=PhysicalSourceEvidence1A.Status.INCOMPLETE_SOURCE_EVIDENCE;
        var wrong=PhysicalSourceEvidence1A.Status.PHYSICAL_ID_MISMATCH;
        check(result(true,true,true,true,true,true,true,true)==good,"complete evidence");
        for(int bit=1;bit<128;bit<<=1){
            boolean[] x={true,true,true,true,true,true,true};
            x[Integer.numberOfTrailingZeros(bit)]=false;
            check(result(true,x[0],x[1],x[2],x[3],x[4],x[5],x[6])==missing,
                    "every missing provenance component must fail closed");
        }
        check(result(false,true,true,true,true,true,true,true)==wrong,
                "mismatched physical source always wins");
        check(result(false,false,false,false,false,false,false,false)==wrong,
                "conflicting physical identity cannot be hidden by missing data");
        check(result(true,true,true,false,true,true,true,true)!=good,
                "cross-lens colour cannot be proven with missing Camera2 calibration");
        System.out.println("PASS PhysicalSourceEvidence1ATest "+
                "(complete, 7 incomplete dimensions, mismatch precedence)");
    }
}
