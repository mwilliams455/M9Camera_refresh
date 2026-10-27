import com.particlesdevs.photoncamera.control.subject.AutoEyeFocusPolicy;

public final class AutoEyeFocusPolicyHostTest {
    static int assertions;
    static void eq(boolean actual,boolean expected,String label){
        assertions++;
        if(actual!=expected)throw new AssertionError(label+" expected "+expected+" got "+actual);
    }
    public static void main(String[] args){
        for(int flags=0;flags<32;flags++) {
            boolean enable=(flags&1)!=0,photo=(flags&2)!=0,continuous=(flags&4)!=0;
            boolean wide=(flags&8)!=0,pet=(flags&16)!=0;
            eq(AutoEyeFocusPolicy.allowed(enable,photo,continuous,wide,pet),
                    enable&&photo&&continuous&&wide&&!pet,"matrix"+flags);
        }
        for(int flags=0;flags<8;flags++) {
            boolean enabled=(flags&1)!=0,tap=(flags&2)!=0,object=(flags&4)!=0;
            eq(AutoEyeFocusPolicy.mayOwnRegion(enabled,tap,object),enabled&&!tap&&!object,
                    "focus ownership"+flags);
        }
        System.out.println("PASS: "+assertions+" default automatic eye AF eligibility and ownership checks");
    }
}
