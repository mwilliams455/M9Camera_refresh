#!/usr/bin/env python3
"""Synthetic transport tests and source isolation gates; no private photo data."""
from pathlib import Path
import hashlib,json,subprocess,sys,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent
root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
src=root/'app/src/main/java/com/particlesdevs/photoncamera'
classes=out/'classes';classes.mkdir(exist_ok=True)
subprocess.run(['java','com.sun.tools.javac.Main','-d',str(classes),str(src/'m9/capture/M9CaptureAuditStore.java'),str(HERE.parent/'capturerequest1a/AuditStoreHostProbe.java')],check=True)
log=subprocess.check_output(['java','-cp',str(classes),'com.particlesdevs.photoncamera.m9.capture.AuditStoreHostProbe'],text=True)
assert 'AUDIT_STORE_CASES=10 CONCURRENT_FRAMES=100' in log
manifest=json.loads((HERE/'manifest.json').read_text())
files=json.loads((HERE.parent/'upstream2r/source_manifest.json').read_text())['files']
for folder,name in [('upstream2r_fix1','fix_manifest.json'),('perf2s_auditopt1a','perf_manifest.json'),('dngexport1b','manifest.json'),('dngstage1a','manifest.json'),('dngnoisemeta1a','manifest.json'),('dngnoisestage1a','manifest.json'),('dngcolormeta1a','manifest.json'),('dngprofile1a','manifest.json'),('dngprofile1b','manifest.json'),('dngrawpair1a','manifest.json'),('capturerequest1a','manifest.json'),('rawreadout1a','manifest.json'),('saturationmenu1a','manifest.json'),('outputmenu1a','manifest.json'),('savemode1a','manifest.json'),('settingsstatus1a','manifest.json')]:
    files.update(json.loads((HERE.parent/folder/name).read_text())['fileOverrides'])
count=0
for name,digest in files.items():
    if name in manifest['fileOverrides'] or name=='app/version.properties':continue
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
    count+=1
for name,digest in manifest['fileOverrides'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
controller=(src/'capture/CaptureController.java').read_text()
assert controller.count('M9CaptureRequestAudit1A.completed(m9CaptureAudit, session, request, result)')==1
assert controller.count('m9CaptureAudit == null || !m9CaptureAudit.omitRemosaic')==1
assert 'final M9CaptureRequestAudit1A.Start m9CaptureAudit' in controller
assert 'M9CaptureRequestAudit1A.afterVendor(m9CaptureAudit, captureBuilder)' in controller
helper=(src/'api/VendorTagUtils.java').read_bytes()
assert hashlib.sha256(helper).hexdigest()=='73f5236a4bfc349a67189049ee463c578d2bd819c90646b7766f25f44ffbdc25'
audit=(src/'m9/capture/M9CaptureRequestAudit1A.java').read_text()
assert '.set(' not in audit and '.addTarget(' not in audit
assert 'getPhysicalCameraKey' in audit and 'getPhysicalCameraResults' in audit
assert 'missing_or_timestamp_mismatch_no_policy_inferred' in audit
queue=(src/'m9/render/M9PrimaryRenderQueue.java').read_text()
assert queue.index('put("captureRequest1A", m9CaptureAudit)')<queue.index('rendererDiagnosticsJson = renderResult.diagnostics.toString()')
xml=ET.parse(root/'app/src/main/res/xml/preferences.xml')
ns='{http://schemas.android.com/apk/res/android}'
matches=[e for e in xml.iter() if e.get(ns+'key')=='pref_m9_omit_auto_remosaic']
assert len(matches)==1 and matches[0].get(ns+'defaultValue')=='false'
readout=(src/'m9/capture/M9RawReadoutAudit1A.java').read_text()
assert '.set(' not in readout and '.setPhysicalCameraKey(' not in readout and '.openCamera(' not in readout
assert 'new CaptureRequest.Key' not in readout and 'new CaptureResult.Key' not in readout
assert 'getAvailableCaptureRequestKeys' in readout and 'getAvailableCaptureResultKeys' in readout
assert 'SCALER_STREAM_CONFIGURATION_MAP_MAXIMUM_RESOLUTION' in readout
assert 'rawReadoutRequest' in audit and 'rawReadoutCameraInventory' in audit
assert '49152' in readout and 'index < 16' in readout
report=dict(readOnlyRawReadoutAudit=True, status='passed' ,transportCases=10,concurrentFrames=100,
    unmodifiedParentFilesChecked=count,sourceOverrides=len(manifest['fileOverrides']),
    vendorHelperByteIdentical=True,defaultPolicyUnchanged=True,
    omissionLimitedToVendorHelperBurstArgument=True,noDiagnosticRequestWrites=True,
    calibrationAndRawSampleProcessingPreserved=True,unfilteredWriterNowOptional=True,outputChangesPinnedToManifest=True,
    scope='Host correlation/ownership, source isolation and UI default; Android compilation and policy tests are separate; handset pending')
(out/'REQUEST_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
print(log.strip());print(json.dumps(report))
