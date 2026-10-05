"""Run capture-snapshot, diagnostics and Monochrom profile/switch regressions."""
import argparse,os,subprocess,tempfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--sdk',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--offline',action='store_true');p.add_argument('--java-agent',type=Path);a=p.parse_args()
env=os.environ.copy();env['ANDROID_HOME']=str(a.sdk.resolve());env['ANDROID_SDK_ROOT']=env['ANDROID_HOME']
if not env.get('JAVA_HOME') and (a.sdk/'jdk_path.txt').exists():env['JAVA_HOME']=(a.sdk/'jdk_path.txt').read_text().strip()
if env.get('JAVA_HOME'):env['PATH']=env['JAVA_HOME']+'/bin:'+env['PATH']
classes=['ProfileCaptureTest','RendererSwitchLifecycleTest','MonoImageProfilesTest','MonoProfilesUiTest','M9RenderDiagnosticsTest','M9SharpnessDiagnosticsTest','M9OutputSettingsTest','M9SetupAuditGateTest']
with tempfile.NamedTemporaryFile('w',suffix='.gradle') as init:
 init.write('gradle.beforeProject { p -> p.layout.buildDirectory.set(new File('+repr(str(a.output.resolve()))+',p.name)) }\n')
 if a.java_agent:init.write('allprojects { tasks.withType(Test).configureEach { jvmArgs '+repr('-javaagent:'+str(a.java_agent.resolve()))+' } }\n')
 init.flush();args=['bash','gradlew',':app:testDebugUnitTest','--no-daemon','--max-workers=2','--init-script',init.name]
 if a.offline:args.append('--offline')
 for name in classes:args+=['--tests','*'+name]
 subprocess.run(args,cwd=a.source.resolve(),env=env,check=True)
