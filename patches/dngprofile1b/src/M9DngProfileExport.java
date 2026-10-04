package com.particlesdevs.photoncamera.processing;

import android.util.Log;
import com.particlesdevs.photoncamera.m9.render.M9TargetFirmwareCalibration;
import org.json.JSONArray;
import org.json.JSONObject;
import java.nio.file.Path;
import java.util.UUID;

/** One capture's frozen renderer result -> embedded editable look, before publication.
 * Serialized to bound heap use even when the existing DNG queue takes its sync fallback.
 * This does not change JPEG pixels, sensor characterization, or the live preview.
 */
public final class M9DngProfileExport {
    private M9DngProfileExport() {}
    public static synchronized JSONObject embed(Path path,String frozenRenderer,boolean jpegRendered) {
        long start=System.nanoTime();JSONObject report=new JSONObject();
        try {
            report.put("revision","M9DNGPROFILE1B");
            report.put("physicalCalibrationPreserved",true);
            report.put("storagePolicy","same_directory_dng_staging_atomic_replace");
            report.put("crossLensExperimentalOverride",false);
            if(!jpegRendered||frozenRenderer==null) throw new IllegalStateException("No successful capture renderer result");
            JSONObject renderer=new JSONObject(frozenRenderer);
            if(renderer.getInt("nativeSaturationBankActuallySelected")!=2||!renderer.getBoolean("identityHsmApplied"))
                throw new IllegalStateException("Unsupported rendering mode");
            JSONObject target=renderer.getJSONObject("targetDomainTrace1A");
            JSONArray rows=target.getJSONArray("currentPpToM9Composed");
            if(rows.length()!=3) throw new IllegalArgumentException("Invalid target matrix rows");
            double[] matrix=new double[9];
            for(int r=0;r<3;r++) {
                JSONArray row=rows.getJSONArray(r);if(row.length()!=3) throw new IllegalArgumentException("Invalid matrix columns");
                for(int c=0;c<3;c++) matrix[r*3+c]=row.getDouble(c);
            }
            M9DngProfile profile=new M9DngProfile(matrix,target.getDouble("effectiveRenderGain"),M9TargetFirmwareCalibration.get().curve02);
            String name="M9 App1B "+UUID.randomUUID().toString().replace("-","").substring(0,16);
            M9DngProfileWriter.Result result=M9DngProfileWriter.embed(path,profile,name);
            report.put("status","embedded");report.put("profileName",result.name);report.put("profileDigest",result.digest);
            report.put("generationElapsedMs",profile.elapsedMs);report.put("addedBytes",result.addedBytes);
            report.put("renderGain",profile.gain);report.put("source","capture_owned_common_scene_to_m9");
            report.put("lightroomSelection","named_profile_digest_neutral_settings");
            report.put("detailPolicy","zero_lightroom_sharpening_and_noise_reduction");
            report.put("jpegSpatialShadingMayDiffer",true);
        } catch(Exception|OutOfMemoryError error) {
            Log.e("M9DNGPROFILE1B","Profile export bypassed; retaining saved RAW",error);
            try { report.put("status","bypassed_original_raw_preserved");report.put("reason",error.toString()); }
            catch(Exception ignored) { /* retain the primary RAW even if diagnostic allocation fails */ }
        }
        try { report.put("elapsedMs",(System.nanoTime()-start)/1_000_000L); } catch(Exception ignored) {}
        return report;
    }
}
