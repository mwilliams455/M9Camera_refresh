"""Summarize the supplied trace without embedding crop pixels or full colour matrices."""
from pathlib import Path
import argparse,collections,hashlib,json,math
p=argparse.ArgumentParser();p.add_argument('trace',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
j=json.loads(a.trace.read_text());t0=j['shutterElapsedNs']
frames=j['prePreview']['frames']+j['postPreview']['frames']
metadata={}
for name in ['preMetadata','postMetadata']:
 m=j[name];rows=[dict(zip(m['columns'],r))for r in m['rows']]
 metadata[name]=dict(rows=len(rows),exposureEnergyRangeEv=math.log2(max(r['iso']*r['exposureNs']for r in rows)/min(r['iso']*r['exposureNs']for r in rows)),
  values={k:dict(collections.Counter(str(r[k])for r in rows))for k in ['iso','exposureNs','focusDiopters','afMode','afState','requestAfTrigger']})
reduced=[]
for f in frames:
 reduced.append(dict(secondsAfterShutter=(f['submittedElapsedNs']-t0)/1e9,autoEv=f['autoEv'],observedIso=f['observedIso'],observedExposureNs=f['observedExposureNs'],displayExposureScale=f['displayExposureScale'],textureMatchesResult=f['textureMatchesResult'],sourceReady=f['sourceReady'],centerCropMedian={s:f['panels']['region1_'+s]['medianLuma']for s in ['incomingOes','referenceRender','displayRender']}))
pair=[min(reduced,key=lambda f:abs(f['secondsAfterShutter']-t))for t in [6.537,6.802]]
rs=[dict(zip(j['postMetadata']['columns'],r))for r in j['postMetadata']['rows'] if 5.9<(r[0]-t0)/1e9<7.4]
auto=j['shutterSnapshot']['exposurePlan1A']['renderedAutoPlacement2D']
report=dict(traceFilename=a.trace.name,sha256=hashlib.sha256(a.trace.read_bytes()).hexdigest(),captureId=j['captureId'],
 captureSoftware=j['savedExif'],metadata=metadata,previewFrames=reduced,
 keyPulse=dict(before=pair[0],after=pair[1],intervalMs=1000*(pair[1]['secondsAfterShutter']-pair[0]['secondsAfterShutter']),sensorEnergyChangeEv=math.log2(pair[1]['observedIso']*pair[1]['observedExposureNs']/(pair[0]['observedIso']*pair[0]['observedExposureNs'])),autoCorrectionChangeEv=pair[1]['autoEv']-pair[0]['autoEv'],focusWindowSeconds=[5.9,7.4],focusWindowValues={k:sorted(set(r[k]for r in rs))for k in ['focusDiopters','afState','lensState','requestAfTrigger']}),
 shutterAuto={k:v for k,v in auto.items()if not isinstance(v,(dict,list))},
 jpegFinalizeSuccess=j['jpegFinalizeSuccess'],codingBytesPreservedAcrossExif=j['codingBytesPreservedAcrossExif'],
 limits=[
 'One full Auto decision/bracket is available at shutter, not at every later correction change; exact binding cap for the 6.8-second reduction is not recorded.',
 'Crop appliedState.uniformPreviewToneGain defaults to unity in this build and is not valid evidence of actual tone gain. Surface draw snapshots do record actual tone gain.',
 'These are same-texture GPU crop measurements and command snapshots, not verified physical display presentation.',
 'Pre-shutter AF request CANCEL appears on all 90 callbacks and warrants a separate follow-up. Around the largest post-shutter pulse the trigger is IDLE, focus is fixed and lens state is stationary.',
 'The proposed recovery test uses synthetic probes demonstrating the same rebound mechanism, not a full replay of unavailable per-frame meter brackets.'
 ])
a.output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report['keyPulse'],indent=2))
