#!/usr/bin/env python3
"""Exercise production paired-export storage/ownership with synthetic byte buffers."""
from pathlib import Path
import json,subprocess,sys
HERE=Path(__file__).resolve().parent
root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
src=root/'app/src/main/java/com/particlesdevs/photoncamera'
classes=out/'classes';classes.mkdir(exist_ok=True)
subprocess.run(['java','com.sun.tools.javac.Main','-d',str(classes),str(src/'processing/M9DngRawPair.java'),str(HERE.parent/'dngrawpair1a/RawPairHostProbe.java')],check=True)
work=out/'cases';assert not work.exists(),'Use new test destination'
log=subprocess.check_output(['java','-cp',str(classes),'com.particlesdevs.photoncamera.processing.RawPairHostProbe',str(work)],text=True)
assert 'RAWPAIR_CASES=13' in log,log
s=(src/'processing/ImageSaver.java').read_text()
assert s.index('final int rawPairWhite = parameters.whiteLevel') < s.index('noiseStage = M9DngNoiseStage.process')
assert s.index('boolean boundary2QSaved = saveSingleRaw') < s.index('M9DngRawPair.Result rawPair =')
assert 'boundary2QSaved, image.buffer, image.width, image.height' in s
assert 'control.setWhiteLevel(rawPairWhite)' in s and 'control.setBlackLevel(originalBlack)' in s
assert 'control.setParametersForM9Raw(parameters,' in s
assert "versionCode 27221" in (root/'app/build.gradle').read_text()
assert "versionName '2.21-m9rawreadout1a'" in (root/'app/build.gradle').read_text()
q=(src/'m9/render/M9PrimaryRenderQueue.java').read_text()
assert q.count('M9DngProfileExport.embed(')==1
assert q.index('M9DngProfileExport.embed(')<q.index('Path rawPairPath =')
result=dict(status='passed',storageOwnershipCases=13,normalCapturePreserved=True,
            originalBufferNoScaleNoFilter=True,metadataLevelSnapshotBeforeFilter=True,
            independentConcurrentFrames=True,sourceMutationDetected=True,
            controlProfileNotEmbedded=True,deviceValidationPending=True,
            scope='Production Java storage helper plus integration assertions; native serializer gates run separately')
(out/'PAIR_VERIFICATION.json').write_text(json.dumps(result,indent=2)+'\n')
print(log.strip());print(json.dumps(result))
