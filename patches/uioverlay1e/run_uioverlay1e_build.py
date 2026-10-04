import os,urllib.parse,subprocess
from pathlib import Path
p=urllib.parse.urlsplit(os.environ['HTTPS_PROXY']);opts=f'-Dhttps.proxyHost={p.hostname} -Dhttps.proxyPort={p.port or 80} -Dhttp.proxyHost={p.hostname} -Dhttp.proxyPort={p.port or 80} -Djavax.net.ssl.trustStore=/etc/ssl/certs/java/cacerts'
env=os.environ.copy();env['GRADLE_OPTS']=opts;env['JAVA_TOOL_OPTIONS']=opts;env['ANDROID_HOME']='/workspace/scratch/6951c59f14de/android_sdk_contrast';env['ANDROID_SDK_ROOT']=env['ANDROID_HOME'];env['JAVA_HOME']=Path(env['ANDROID_HOME']+'/jdk_path.txt').read_text().strip();env['PATH']=env['JAVA_HOME']+'/bin:'+env['PATH']
args=['bash','gradlew',':app:assembleDebug',':app:testDebugUnitTest','--offline','--max-workers=2','--init-script','/workspace/scratch/0bfa8111e4af/uioverlay1e_test_runtime.gradle']
for test in ['M9LinearManualLifecycleTest','M9LinearRulerSelectionTest','M9OverlayPolicyTest','M9BracketTest','M9AeLockTest','M9SelfTimerTest','M9LeicaEvTest','M9SaveSelectionTest']:args+=['--tests','*'+test]
args+=['--stacktrace']
with open('/workspace/scratch/0bfa8111e4af/uioverlay1e_build.log','w') as f:r=subprocess.run(args,cwd='/workspace/scratch/0bfa8111e4af/PhotonCamera_uioverlay1e',env=env,stdout=f,stderr=subprocess.STDOUT)
print('Build exit:',r.returncode)
raise SystemExit(r.returncode)
