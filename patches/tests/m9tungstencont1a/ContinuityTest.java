import com.particlesdevs.photoncamera.m9.preview.*;

public class ContinuityTest {
    static int n;
    static void check(boolean v,String m){n++;if(!v)throw new AssertionError(m);}
    static M9GpuPreview2A.Frame good(String id){return M9GpuPreview2A.Frame.good(id);}
    static M9GpuPreview2A.Frame bad(String why){return M9GpuPreview2A.Frame.fallback(why);}

    public static void main(String[] args){
        M9PreviewSourceContinuity1A.reset();
        check(!M9PreviewSourceContinuity1A.resolve(bad("cold_start"),"4",0).ready,
                "no synthetic good source at cold start");

        M9GpuPreview2A.Frame g=good("4");
        check(M9PreviewSourceContinuity1A.resolve(g,"4",1_000_000_000L)==g,
                "good source passes through");

        M9GpuPreview2A.Frame held=M9PreviewSourceContinuity1A.resolve(
                bad("controlled_curve_not_reported"),"4",1_500_000_000L);
        check(held.ready,"same-camera transient held");
        check(held.continuityHeld,"held flag");
        check(held.reason.equals("held_last_valid_source"),"held reason");
        check(held.continuityContractReason.equals("controlled_curve_not_reported"),"raw failure retained");
        check(held.continuityLastGoodAgeMs==500,"age recorded");

        check(M9PreviewSourceContinuity1A.resolve(
                bad("incomplete_source_contract"),"4",2_000_000_000L).ready,
                "one-second boundary included");
        check(!M9PreviewSourceContinuity1A.resolve(
                bad("incomplete_source_contract"),"4",2_000_000_001L).ready,
                "hold expires after one second");

        M9PreviewSourceContinuity1A.resolve(good("4"),"4",3_000_000_000L);
        check(!M9PreviewSourceContinuity1A.resolve(
                bad("physical_result_unavailable"),"7",3_100_000_000L).ready,
                "never hold across camera switch");

        M9PreviewSourceContinuity1A.reset();
        check(!M9PreviewSourceContinuity1A.resolve(bad("after_reset"),"4",4_000_000_000L).ready,
                "reset clears authority");
        System.out.println("M9TUNGSTENCONT1A continuity PASS: "+n+" assertions");
    }
}
