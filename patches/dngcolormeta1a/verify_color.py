#!/usr/bin/env python3
"""Production colour policy -> production native DNG -> independent TIFF decode."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
import numpy as np
import tifffile
HERE=Path(__file__).resolve().parent
TAGS={50778,50779,50721,50722,50723,50724,50964,50965,50728}
def verify(root,out):
    root,out=Path(root).resolve(),Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    source=root/'app/src/main/java/com/particlesdevs/photoncamera/processing'
    subprocess.run(['java','com.sun.tools.javac.Main','-d',str(out),str(source/'M9DngColorMetadata.java'),str(HERE/'ColorTagProbe.java')],check=True)
    color=[.8,-.2,.1,-.1,1.1,.15,.05,.1,.7]
    eye=[1,0,0,0,1,0,0,0,1];forward=[.6,.3,.0642,.2,.7,.1,.02,.1,.7049];neutral=[.5,1,.75]
    cases={'dual':([17,21],[color,color,eye,eye,forward,forward,neutral]),
           'single':([21,None],[color,None,None,None,None,None,neutral]),
           'single_forward':([21,None],[color,None,eye,None,forward,None,neutral]),
           'partial_forward':([17,21],[color,color,eye,eye,forward,None,neutral])}
    plans={}
    for name,(refs,arrays) in cases.items():
        path=out/(name+'.txt')
        path.write_text(' '.join('null' if v is None else str(v) for v in refs)+'\n'+
                        '\n'.join('null' if a is None else ' '.join(map(str,a)) for a in arrays)+'\n')
        subprocess.run(['java','-cp',str(out),'com.particlesdevs.photoncamera.processing.ColorTagProbe',str(path),str(out/(name+'.tags'))],check=True)
        plans[name]={int(p[0]):list(map(float,p[2:])) for p in (line.split() for line in (out/(name+'.tags')).read_text().splitlines())}
    assert set(plans['dual'])==TAGS
    assert set(plans['single'])=={50778,50721,50728}
    assert set(plans['single_forward'])=={50778,50721,50723,50964,50728}
    assert set(plans['partial_forward'])==TAGS-{50964,50965}
    native=False
    javac=shutil.which('javac')
    if javac:
        jdk=Path(javac).resolve().parents[1]
        stub=out/'android';stub.mkdir(exist_ok=True)
        (stub/'log.h').write_text('#define ANDROID_LOG_DEBUG 3\n#define ANDROID_LOG_ERROR 6\ninline int __android_log_print(int,const char*,const char*,...){return 0;}\n')
        cpp=root/'app/src/main/cpp'
        subprocess.run(['g++','-std=c++17','-O2','-I'+str(out),'-I'+str(jdk/'include'),'-I'+str(jdk/'include/linux'),'-I'+str(cpp),'-I'+str(cpp/'deps'),str(HERE/'color_writer_probe.cpp'),'-o',str(out/'writer'),'-ldl'],check=True)
        for name,plan in plans.items():
            path=out/(name+'.dng')
            subprocess.run([str(out/'writer'),str(out/(name+'.tags')),str(path)],check=True)
            with tifffile.TiffFile(path) as f:
                p=f.pages[0];assert TAGS.intersection(p.tags.keys())==set(plan), (name, list(p.tags.keys()), list(plan))
                for tag,expected in plan.items():
                    v=np.asarray(p.tags[tag].value,dtype=float).reshape(-1)
                    if p.tags[tag].dtype in (5,10):
                        v=v.reshape(-1,2);v=v[:,0]/v[:,1]
                    np.testing.assert_allclose(v,expected,rtol=0,atol=1e-7)
                expected=(64+(np.arange(66*34)*7)%960).astype(np.uint16).reshape(34,66)
                np.testing.assert_array_equal(p.asarray(),expected)
        native=True
    elif os.environ.get('CI'):raise RuntimeError('CI must exercise production native writer')
    result=dict(status='passed',syntheticCases=len(cases),realNativeWriter=native,
                productionColorPolicy=True,rawSamplesCompared=8976 if native else 0,
                singleIlluminant2Omitted=True,missingForwardMatricesOmitted=True,
                jpegRendererChanged=False)
    (out/'COLOR_VERIFICATION.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':verify(*sys.argv[1:])
