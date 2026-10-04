import android.graphics.Point;
import android.hardware.camera2.*;
import android.hardware.camera2.params.*;
import android.util.*;
import com.particlesdevs.photoncamera.app.PhotonCamera;
import com.particlesdevs.photoncamera.capture.CaptureController;
import com.particlesdevs.photoncamera.processing.render.*;
import com.particlesdevs.photoncamera.util.Allocator;

class ParameterFixtures {
 static CameraCharacteristics lens(int black,float scale){
  CameraCharacteristics c=new CameraCharacteristics();
  c.set(CameraCharacteristics.SENSOR_MAX_ANALOG_SENSITIVITY,800);
  c.set(CameraCharacteristics.SENSOR_INFO_COLOR_FILTER_ARRANGEMENT,0);
  c.set(CameraCharacteristics.SENSOR_INFO_WHITE_LEVEL,4095);
  c.set(CameraCharacteristics.SENSOR_INFO_PHYSICAL_SIZE,new SizeF(8,6));
  c.set(CameraCharacteristics.LENS_INFO_AVAILABLE_FOCAL_LENGTHS,new float[]{5});
  c.set(CameraCharacteristics.LENS_INFO_AVAILABLE_APERTURES,new float[]{1.8f});
  c.set(CameraCharacteristics.LENS_FACING,1);
  c.set(CameraCharacteristics.SENSOR_BLACK_LEVEL_PATTERN,new BlackLevelPattern(new int[]{black,black+1,black+2,black+3}));
  c.set(CameraCharacteristics.SENSOR_REFERENCE_ILLUMINANT1,CameraMetadata.SENSOR_REFERENCE_ILLUMINANT1_DAYLIGHT);
  c.set(CameraCharacteristics.SENSOR_CALIBRATION_TRANSFORM1,matrix(1));c.set(CameraCharacteristics.SENSOR_CALIBRATION_TRANSFORM2,matrix(1));
  c.set(CameraCharacteristics.SENSOR_COLOR_TRANSFORM1,matrix(1));c.set(CameraCharacteristics.SENSOR_COLOR_TRANSFORM2,matrix(1));
  c.set(CameraCharacteristics.SENSOR_FORWARD_MATRIX1,matrix(scale));c.set(CameraCharacteristics.SENSOR_FORWARD_MATRIX2,matrix(scale));return c;
 }
 static ColorSpaceTransform matrix(float red){return new ColorSpaceTransform(new Rational[]{new Rational((int)(red*1000),1000),new Rational(0,1),new Rational(0,1),new Rational(0,1),new Rational(1,1),new Rational(0,1),new Rational(0,1),new Rational(0,1),new Rational(1,1)});}
 static CaptureResult result(){CaptureResult r=new CaptureResult();r.set(CaptureResult.SENSOR_SENSITIVITY,100);r.set(CaptureResult.SENSOR_EXPOSURE_TIME,10000000L);r.set(CaptureResult.LENS_APERTURE,1.8f);r.set(CaptureResult.LENS_FOCAL_LENGTH,5f);r.set(CaptureResult.SENSOR_NEUTRAL_COLOR_POINT,new Rational[]{new Rational(1,1),new Rational(1,1),new Rational(1,1)});return r;}
 static void select(String id,CameraCharacteristics c,int sensor){PhotonCamera.settings.mCameraID=id;CaptureController.mCameraCharacteristics=c;SpecificSettingSensor s=new SpecificSettingSensor();s.id=sensor;s.NoiseModelerArr[0][0]=sensor+.25;PhotonCamera.sensor.selectedSensorSpecifics=s;PhotonCamera.settings.compressor=1.4;PhotonCamera.settings.cfaPattern=-1;PhotonCamera.settings.colorMethod=0;PhotonCamera.specific.isRawColorCorrection=false;Allocator.binning=false;}
 static Parameters fill(CameraCharacteristics c,boolean raw){Parameters p=new Parameters();p.FillConstParameters(c,new Point(100,80));if(raw)p.FillDynamicParametersForSingleRaw(result(),null,100);else p.FillDynamicParameters(result(),new CaptureRequest(),100);return p;}
 static void check(boolean b,String message){if(!b)throw new AssertionError(message);}
 static String fingerprint(Parameters p){return p.cameraID+"|"+p.sensorSpecifics.id+"|"+p.cfaPattern+"|"+p.whiteLevel+"|"+p.tonemapStrength+"|"+java.util.Arrays.toString(p.blackLevel)+"|"+java.util.Arrays.toString(p.sensorToProPhoto)+"|"+java.util.Arrays.toString(p.proPhotoToSRGB)+"|"+p.sensorSpecifics.NoiseModelerArr[0][0];}
}
