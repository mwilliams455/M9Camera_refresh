"""Build the M9 confirmed exposure settling refinement with an already provisioned Android SDK."""
import argparse, os, subprocess, tempfile
from pathlib import Path
p = argparse.ArgumentParser()
p.add_argument('source', type=Path)
p.add_argument('--sdk', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--offline', action='store_true')
a = p.parse_args()
env = os.environ.copy()
env['ANDROID_HOME'] = str(a.sdk.resolve())
env['ANDROID_SDK_ROOT'] = env['ANDROID_HOME']
if not env.get('JAVA_HOME') and (a.sdk/'jdk_path.txt').exists():
    env['JAVA_HOME'] = (a.sdk/'jdk_path.txt').read_text().strip()
if env.get('JAVA_HOME'):
    env['PATH'] = env['JAVA_HOME']+'/bin:'+env['PATH']
with tempfile.NamedTemporaryFile('w', suffix='.gradle') as init:
    init.write('gradle.beforeProject { p -> p.layout.buildDirectory.set(new File('+repr(str(a.output.resolve()))+',p.name)) }\n')
    init.flush()
    args = ['bash', 'gradlew', ':app:assembleDebug', '--no-daemon', '--max-workers=2', '--init-script', init.name]
    if a.offline:
        args.append('--offline')
    subprocess.run(args, cwd=a.source.resolve(), env=env, check=True)
