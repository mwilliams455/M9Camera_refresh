import com.particlesdevs.photoncamera.control.tracking.SubjectAnchorPolicy;
import com.particlesdevs.photoncamera.control.tracking.SubjectAppearanceDescriptor;
import com.particlesdevs.photoncamera.control.tracking.SubjectAnchorPolicy.Candidate;
import com.particlesdevs.photoncamera.control.tracking.SubjectAnchorPolicy.State;
import java.util.Arrays;
import java.util.Collections;

public final class SubjectIdentityPolicyTest {
  static int checks;
  static void ok(boolean value,String message){checks++;if(!value)throw new AssertionError(message);}
  static SubjectAppearanceDescriptor colour(int r,int g,int b){
    int[] argb=new int[128*128];Arrays.fill(argb,0xff000000|(r<<16)|(g<<8)|b);
    return SubjectAppearanceDescriptor.sample(argb,128,128,.1f,.1f,.8f,.9f);
  }
  static Candidate c(String label,float conf,float l,float t,float r,float b,SubjectAppearanceDescriptor sig){
    return new Candidate(label,conf,l,t,r,b,sig);
  }
  static void crossingDifferentClothes(){
    SubjectAppearanceDescriptor blue=colour(20,80,210),red=colour(200,45,20);
    SubjectAnchorPolicy p=new SubjectAnchorPolicy();p.begin(1,.25f,.3f,1000);p.useAppearance(true);
    Candidate a=c("person",.75f,.12f,.15f,.40f,.92f,blue);
    Candidate b=c("person",.91f,.56f,.12f,.84f,.9f,red);
    ok(p.observe(1,1010,1040,Arrays.asList(a,b)).state==State.WAITING,"tap selects original");
    ok(p.observe(1,1190,1240,Arrays.asList(a,b)).canMoveAf(),"two detections confirm original");
    Candidate movedA=c("person",.70f,.28f,.13f,.58f,.88f,blue);
    Candidate movedB=c("person",.98f,.30f,.14f,.59f,.86f,red);
    SubjectAnchorPolicy.Decision d=p.observe(1,1420,1460,Arrays.asList(movedB,movedA));
    ok(d.canMoveAf(),"selected subject survives close crossing");
    ok(Math.abs(d.x-.43f)<.16f,"follows original not different-looking interloper");
    // Selected person hidden by another person: cannot steal the stronger result.
    d=p.observe(1,1650,1680,Arrays.asList(movedB));
    ok(d.state==State.HOLD,"wrong person cannot steal after occlusion");
    d=p.observe(1,1830,1850,Arrays.asList(c("person",.89f,.34f,.10f,.65f,.9f,blue),movedB));
    ok(d.state==State.HOLD,"first reappearance still holds AF");
    d=p.observe(1,2010,2040,Arrays.asList(c("person",.85f,.35f,.10f,.65f,.90f,blue),movedB));
    ok(d.canMoveAf(),"second confirmed appearance recovers AF");
  }
  static void similarPeopleAmbiguous(){
    SubjectAppearanceDescriptor same=colour(24,95,206);
    SubjectAnchorPolicy p=new SubjectAnchorPolicy();p.begin(2,.3f,.38f,0);p.useAppearance(true);
    Candidate original=c("person",.81f,.16f,.10f,.45f,.87f,same);
    p.observe(2,30,50,Collections.singletonList(original));
    ok(p.observe(2,210,240,Collections.singletonList(original)).canMoveAf(),"initial lock");
    Candidate x=c("person",.88f,.26f,.12f,.54f,.88f,same);
    Candidate y=c("person",.87f,.30f,.12f,.58f,.88f,same);
    ok(p.observe(2,400,440,Arrays.asList(x,y)).state==State.HOLD,
            "similar appearance near overlapping people is ambiguous");
  }
  static void lifecycleAndNoFalseReid(){
    SubjectAppearanceDescriptor blue=colour(20,70,210),red=colour(220,45,25);
    SubjectAnchorPolicy p=new SubjectAnchorPolicy();p.begin(9,.30f,.40f,0);p.useAppearance(true);
    Candidate a=c("person",.85f,.15f,.12f,.50f,.90f,blue);
    p.observe(9,30,70,Collections.singletonList(a));
    p.observe(9,230,270,Collections.singletonList(a));
    ok(p.observe(9,410,450,Collections.emptyList()).state==State.HOLD,"missing holds");
    Candidate stranger=c("person",.99f,.19f,.12f,.52f,.9f,red);
    ok(p.observe(9,600,650,Collections.singletonList(stranger)).state==State.HOLD,"stranger rejected");
    ok(p.observe(9,800,850,Collections.singletonList(stranger)).state==State.HOLD,"repeated wrong subject rejected");
    ok(p.observe(9,1700,1750,Collections.emptyList()).state==State.RETIRED,"retire after finite loss");
    ok(!p.observe(9,1820,1870,Collections.singletonList(a)).canMoveAf(),"retired cannot auto reacquire");
    p.begin(10,.30f,.40f,2000);p.useAppearance(true);
    ok(!p.observe(9,2210,2240,Collections.singletonList(a)).canMoveAf(),"old camera epoch rejected");
    ok(p.observe(10,2180,2200,Collections.singletonList(a)).state==State.WAITING,"new tap requires new selection");
    ok(p.observe(10,2180,2210,Collections.singletonList(a)).state==State.WAITING,"duplicate frame cannot confirm");
  }
  static void defaultLegacyCompatibility(){
    SubjectAnchorPolicy p=new SubjectAnchorPolicy();p.begin(14,.34f,.36f,0);
    Candidate subject=c("person",.8f,.20f,.10f,.56f,.88f,null);
    p.observe(14,50,80,Collections.singletonList(subject));
    ok(p.observe(14,220,240,Collections.singletonList(subject)).canMoveAf(),"3.08 old signature-free behaviour");
    ok(p.observe(14,410,430,Collections.emptyList()).state==State.HOLD,"3.08 hold unchanged");
    ok(p.observe(14,580,630,Collections.singletonList(subject)).canMoveAf(),
            "3.08 immediate reacquisition unchanged when opt-in off");
  }
  public static void main(String[] args){
    crossingDifferentClothes();similarPeopleAmbiguous();lifecycleAndNoFalseReid();defaultLegacyCompatibility();
    System.out.println("PASS " + checks + " persistent identity tests");
  }
}
