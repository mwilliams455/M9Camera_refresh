import android.hardware.camera2.CameraCharacteristics;
import com.particlesdevs.photoncamera.processing.render.Parameters;
public class ParametersBaselineProbe extends ParameterFixtures {
 public static void main(String[] args){
  CameraCharacteristics a=lens(64,1),b=lens(512,1.7f);
  select("0",a,0);Parameters immediate=fill(a,false);
  select("0-2",b,2);Parameters delayed=fill(a,false);
  check(immediate.blackLevel[0]==64,"baseline fixture");
  check(delayed.blackLevel[0]==512,"must reproduce other lens black level");
  check(delayed.cameraID.equals("0-2")&&delayed.sensorSpecifics.id==2,"must reproduce other lens identity");
  check(!java.util.Arrays.equals(immediate.sensorToProPhoto,delayed.sensorToProPhoto),"must reproduce other lens colour calibration");
  System.out.println("REPRODUCED: queued lens A uses lens B identity, black level (64 -> 512), and colour calibration after switch.");
 }
}
