import com.particlesdevs.photoncamera.control.subject.AutomaticSubjectSelection;
import com.particlesdevs.photoncamera.control.subject.AutomaticSubjectSelection.Box;
import com.particlesdevs.photoncamera.control.subject.PetDetailInput;
import com.particlesdevs.photoncamera.control.tracking.SubjectAnchorPolicy.Candidate;
import com.particlesdevs.photoncamera.control.tracking.SubjectAnchorPolicy.ClassId;
import java.util.Arrays;
import java.util.Collections;

public final class PetDetailInputTest {
    private static void check(boolean result, String message) {
        if (!result) throw new AssertionError(message);
    }

    private static Candidate inCrop(PetDetailInput crop, int w, int h, Candidate region, String label, float score) {
        return new Candidate(label, score, (region.left*w-crop.left)/crop.side,
                (region.top*h-crop.top)/crop.side, (region.right*w-crop.left)/crop.side,
                (region.bottom*h-crop.top)/crop.side);
    }

    private static void testRegion(int w, int h, Candidate weak) {
        check(Box.fromBody(weak)==null, "Weak evidence escaped primary gate");
        PetDetailInput crop=PetDetailInput.choose(w,h,Collections.singletonList(weak),null);
        check(crop!=null && crop.left>=0 && crop.top>=0 && crop.left+crop.side<=w
                && crop.top+crop.side<=h, "Crop outside the preview");
        Candidate detail=inCrop(crop,w,h,weak,"cat",.72f);
        Box box=crop.confirm(Collections.singletonList(detail));
        check(box!=null && box.type==ClassId.CAT && Math.abs(box.left-weak.left)<.001f
                && Math.abs(box.bottom-weak.bottom)<.001f, "Crop mapping or species");
        check(crop.confirm(Arrays.asList(detail,detail))==null, "Ambiguous detail");
        check(crop.confirm(Collections.singletonList(inCrop(crop,w,h,weak,"dog",.54f)))==null, "Weak detail");
        check(crop.confirm(Collections.singletonList(inCrop(crop,w,h,weak,"person",.95f)))==null, "Person in crop");
        check(crop.confirm(Collections.singletonList(new Candidate("cat",.88f,0f,0f,.15f,.16f)))==null,
                "Different animal in crop");
        AutomaticSubjectSelection policy=new AutomaticSubjectSelection();
        policy.observe(1L,1L,Collections.singletonList(box));
        check(!policy.mayAim(), "Single confirmed crop moved autofocus");
        policy.observe(200000001L,200000001L,Collections.singletonList(box));
        check(policy.mayAim(), "Two separate frames should confirm");
        check(!AutomaticSubjectSelection.needsPetDetail(box,Collections.singletonList(box)),
                "Redundant inference for an established subject");
        Candidate far=new Candidate("dog",.52f,.75f,.15f,.95f,.25f);
        check(PetDetailInput.choose(w,h,Collections.singletonList(far),box)==null, "Abandoned current pet");
    }

    public static void main(String[] args) {
        testRegion(540,720,new Candidate("dog",.38f,.39f,.56f,.63f,.64f));
        testRegion(720,540,new Candidate("cat",.34f,0f,.83f,.18f,.94f));
        check(PetDetailInput.choose(540,720,Arrays.asList(
                new Candidate("person",.9f,.4f,.4f,.6f,.6f),
                new Candidate("cat",Float.NaN,.2f,.3f,.4f,.4f),
                new Candidate("dog",.26f,.2f,.3f,.4f,.4f),
                new Candidate("dog",.6f,0f,0f,1f,1f)),null)==null, "Unsuitable primary request");
        System.out.println("PetDetailInputTest passed");
    }
}
