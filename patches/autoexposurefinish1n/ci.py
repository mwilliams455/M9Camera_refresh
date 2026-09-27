#!/usr/bin/env python3
"""Replay the pinned parent workflow's shell steps; no edits to inherited test bodies.
The outer workflow performs checkout/setup-java/artifact upload. All parent source
and test shell blocks run in their original order before the new AE overlay.
"""
from pathlib import Path
import hashlib,json,os,subprocess,sys,tempfile,time
ROOT=Path(__file__).resolve().parents[2]
PARENT=ROOT/'.github/workflows/build-m9cam-m9autoexposurefinish1m.yml'
PARENT_SHA256='05ffba1f8c00e4eb88d35803125be1fa2c6dedfffeb21ba804a2c7715bb78c5a'
if hashlib.sha256(PARENT.read_bytes()).hexdigest()!=PARENT_SHA256:
    raise SystemExit('Pinned parent workflow has changed')
lines=PARENT.read_text().splitlines();blocks=[];name=None
for i,line in enumerate(lines):
    if line.startswith('      - name: '):name=line.split(': ',1)[1]
    if line.strip()!='run: |':continue
    body=[]
    for following in lines[i+1:]:
        if following.startswith('      - '):break
        if following.startswith('          '):body.append(following[10:])
        elif not following.strip():body.append('')
        else:raise SystemExit('Unexpected parent run indentation: '+following)
    blocks.append((name,'\n'.join(body)+'\n'))
mode=sys.argv[1]
if mode=='source':
    selected=[]
    for name,body in blocks:
        if name.startswith('Build M9AUTOEXPOSUREFINISH1M'):break
        selected.append((name,body))
    if not selected or selected[-1][0]!='Apply and verify Auto-exposure finish 1M HIGHLIGHTGRANDFATHER1A':
        raise SystemExit('Parent source boundary mismatch')
elif mode=='checks':
    names={'Verify packaged preview and exposure contracts','Verify Android installation metadata, signing and alignment'}
    selected=[(n,b) for n,b in blocks if n in names]
    if len(selected)!=2:raise SystemExit('Parent APK check boundaries mismatch')
else:raise SystemExit('mode must be source or checks')
env=os.environ.copy();updates={};path_updates=[];receipt=[]
with tempfile.TemporaryDirectory(prefix='m9-ae1n-ci-') as tmp:
    tmp=Path(tmp)
    for index,(name,body) in enumerate(selected):
        if mode=='checks':
            body=body.replace('M9AUTOEXPOSUREFINISH1M_HIGHLIGHTGRANDFATHER1A','M9AUTOEXPOSUREFINISH1N_BODYQUAL1A_SUBJECTHEADROOM1A')
            body=body.replace('HIGHLIGHTRET1B_PREEXISTING_Q90','HIGHLIGHTRET1C_SUBJECTHEADROOM1A')
            body=body.replace('2.02-m9ae1m-hlgrand1a-anchorbal1a-perf3i','2.03-m9ae1n-bodyqual1a-subjecthl1a-perf3i')
            if name=='Verify packaged preview and exposure contracts':
                anchor="          assert b'M9SHUTTERTRACE1B'"
                # The run body is already de-indented; add exact new contract checks.
                anchor="assert b'M9SHUTTERTRACE1B'"
                if body.count(anchor)!=1:raise SystemExit('APK proof insertion anchor mismatch')
                body=body.replace(anchor,"assert b'BODYQUAL1A_QUALIFY_BEFORE_RANK' in dex\nassert b'subjectHighlightRetention' in dex\n"+anchor,1)
        script=tmp/f'{index}.sh';script.write_text(body)
        ef=tmp/f'{index}.env';pf=tmp/f'{index}.path'
        ef.touch();pf.touch();env['GITHUB_ENV']=str(ef);env['GITHUB_PATH']=str(pf)
        print('::group::'+name,flush=True);start=time.monotonic()
        r=subprocess.run(['bash','--noprofile','--norc','-e','-o','pipefail',str(script)],cwd=ROOT,env=env)
        print('::endgroup::',flush=True)
        receipt.append({'name':name,'returncode':r.returncode,'elapsedSeconds':round(time.monotonic()-start,3)})
        (ROOT/f'M9AE1N_PARENT_{mode.upper()}_REPLAY.json').write_text(json.dumps(receipt,indent=2)+'\n')
        if r.returncode:raise SystemExit(r.returncode)
        for line in ef.read_text().splitlines():
            if '=' not in line or '<<' in line:raise SystemExit('Unsupported environment record')
            k,v=line.split('=',1);env[k]=v;updates[k]=v
        for path in pf.read_text().splitlines():
            env['PATH']=path+os.pathsep+env.get('PATH','');path_updates.append(path)
for key,value in updates.items():
    with open(os.environ['GITHUB_ENV'],'a') as f:f.write(key+'='+value+'\n')
for path in path_updates:
    with open(os.environ['GITHUB_PATH'],'a') as f:f.write(path+'\n')
print('Pinned parent '+mode+' replay passed',flush=True)
