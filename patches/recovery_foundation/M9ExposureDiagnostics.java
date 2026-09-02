package com.particlesdevs.photoncamera.m9;

import org.json.JSONObject;

/** Recovered diagnostic contract used by the M9 bootstrap. Photographic arithmetic does not depend on this class. */
public final class M9ExposureDiagnostics {
    private static JSONObject root = new JSONObject();
    private static long curveInputExposureNs;
    private static int curveInputIso;
    private static long curveCapStartNs, curveCapEndNs;
    private static int curveRampStops;
    private M9ExposureDiagnostics() {}

    public static synchronized void begin(int previewIso, long previewShutterNs, int isoLow, int isoHigh,
            int maxAnalogIso, long exposureLowNs, long exposureHighNs, double compensationFactor,
            String mode, boolean tripod) {
        JSONObject r=new JSONObject();
        try {
            r.put("schema","m9cam.photon.exposure.v3");
            JSONObject p=new JSONObject();
            p.put("iso",previewIso); p.put("shutterNs",previewShutterNs);
            p.put("exposureEnergyIsoSeconds", ((double)previewIso*(double)previewShutterNs)/1.0e9);
            p.put("exposureCompensationFactor",compensationFactor); p.put("mode",mode); r.put("preview",p);
            JSONObject l=new JSONObject();
            l.put("isoLow",isoLow); l.put("isoHigh",isoHigh); l.put("maxAnalogIso",maxAnalogIso);
            l.put("exposureLowNs",exposureLowNs); l.put("exposureHighNs",exposureHighNs); r.put("sensorLimits",l);
            JSONObject d=new JSONObject(); d.put("tripod",tripod); r.put("dynamicScaling",d);
        } catch(Exception ignored) {}
        root=r;
    }
    public static synchronized void recordNormalizedTarget(int iso,long shutter) { try {
        JSONObject n=new JSONObject(); n.put("normalizedPreviewIso",iso); n.put("normalizedTargetShutterNs",shutter);
        n.put("normalizedTargetEnergy",(double)iso*(double)shutter); root.put("normalization",n);
    } catch(Exception ignored){} }
    public static synchronized void recordPhotonCurrentReference(int iso,long shutter,long capStart,long capEnd) { try {
        JSONObject o=new JSONObject(); o.put("normalizedIso",iso);o.put("shutterNs",shutter);o.put("capStartNs",capStart);o.put("capEndNs",capEnd);o.put("energyNsIso",(double)iso*(double)shutter);root.put("photonCurrentReference",o);
    } catch(Exception ignored){} }
    public static synchronized void recordCaps(long nominalStart,long nominalEnd,double dynamicFactor,int gyro,
            long scaledStart,long scaledEnd,long modeStart,long modeEnd) { try {
        JSONObject d=root.optJSONObject("dynamicScaling"); if(d==null)d=new JSONObject(); d.put("dynamicFactor",dynamicFactor);d.put("gyroFilteredShakiness",gyro);root.put("dynamicScaling",d);
        JSONObject o=new JSONObject();o.put("nominalCapStartNs",nominalStart);o.put("nominalCapEndNs",nominalEnd);o.put("scaledCapStartNs",scaledStart);o.put("scaledCapEndNs",scaledEnd);o.put("modeClampedCapStartNs",modeStart);o.put("modeClampedCapEndNs",modeEnd);root.put("shutterCaps",o);
    } catch(Exception ignored){} }
    public static synchronized void recordCurveInput(long exposure,int iso,long capStart,long capEnd,int rampStops){curveInputExposureNs=exposure;curveInputIso=iso;curveCapStartNs=capStart;curveCapEndNs=capEnd;curveRampStops=rampStops;}
    public static synchronized void recordCurveOutput(int iso,long shutter){try{
        JSONObject o=new JSONObject(); double total=(double)curveInputIso*(double)curveInputExposureNs;
        o.put("totalTargetEnergyNsIso",total);o.put("energyAtCapStartNsIso",(double)curveInputIso*(double)curveCapStartNs);o.put("rampStops",curveRampStops);o.put("effectiveCapNs",curveCapEndNs);o.put("curveFinalNormalizedIso",iso);o.put("curveFinalShutterNs",shutter);o.put("finalShutterNearCap",Math.abs(shutter-curveCapEndNs)<=Math.max(100000L,curveCapEndNs/100L));root.put("shutterPriorityCurve",o);
    }catch(Exception ignored){}}
    public static synchronized void recordFinalNormalized(int iso,long shutter,boolean isoLimited,boolean shutterLimited,boolean isoManual,boolean shutterManual){try{JSONObject o=new JSONObject();o.put("normalizedIso",iso);o.put("shutterNs",shutter);o.put("isIsoLimited",isoLimited);o.put("isShutterLimited",shutterLimited);o.put("isIsoManualOverLimit",isoManual);o.put("isShutterManualOverLimit",shutterManual);root.put("finalNormalized",o);}catch(Exception ignored){}}
    public static synchronized void recordFinalSystem(int iso,long shutter){try{JSONObject o=new JSONObject();o.put("iso",iso);o.put("shutterNs",shutter);o.put("exposureEnergyIsoSeconds",((double)iso*(double)shutter)/1.0e9);root.put("finalDecision",o);}catch(Exception ignored){}}
    public static synchronized JSONObject snapshotJson(){try{return new JSONObject(root.toString());}catch(Exception e){return new JSONObject();}}
}
