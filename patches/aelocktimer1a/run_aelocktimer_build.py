import os,urllib.parse,subprocess
from pathlib import Path
p=urllib.parse.urlsplit(os.environ['HTTPS_PROXY']);opts=f'-Dhttps.proxyHost={p.hostname} -Dhttps.proxyPort={p.port or 80} -Dhttp.proxyHost={p.hostname} -Dhttp.proxyPort={p.port or 80} -Djavax.net.ssl.trustStore=/etc/ssl/certs/java/cacerts'
env=os.environ.copy();env['GRADLE_OPTS']=opts;env['JAVA_TOOL_OPTIONS']=opts;env['ANDROID_HOME']=str(Path('/workspace/scratch/6951c59f14de/android_sdk_contrast').resolve());env['ANDROID_SDK_ROOT']=env['ANDROID_HOME'];env['JAVA_HOME']=Path('/workspace/scratch/6951c59f14de/android_sdk_contrast/jdk_path.txt').read_text().strip();env['PATH']=env['JAVA_HOME']+'/bin:'+env['PATH']
args=['bash','gradlew',':app:assembleDebug',':app:testDebugUnitTest','--max-workers=2','--init-script',str(Path('aelocktimer_test_runtime.gradle').resolve())]
for test in ['M9AeLockTest','M9SelfTimerTest','M9AutoIsoTest','M9LeicaEvTest','M9PreviewBrightnessTest','M9DisplayAidsTest','M9ShootingProfilesTest','M9SaveSelectionTest','M9OutputSettingsTest','M9SaturationSettingsTest','M9ContrastSettingsTest','M9SharpnessSettingsTest','M9SharpnessDiagnosticsTest','M9RawReadoutAuditTest','M9CaptureRequestPolicyTest','M9DngColorMetadataTest','M9DngNoiseProfileTest','M9DngNoiseStageTest','M9DngExportMetadataTest','M9RenderDiagnosticsTest','M9Upstream2RRawPackingTest']:args+=['--tests','*'+test]
args+=['--stacktrace']
with open('aelocktimer_build.log','w') as f:r=subprocess.run(args,cwd='PhotonCamera_aelocktimer1a',env=env,stdout=f,stderr=subprocess.STDOUT)
print('Build exit:',r.returncode)
