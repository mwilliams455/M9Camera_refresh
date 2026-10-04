#!/usr/bin/env python3
"""Verify restored orientation against phone-accepted 2.33 and reject the 2.34 rotation regression."""
from pathlib import Path
import runpy,sys,json
import numpy as np
here=Path(__file__).resolve().parent
root,out,parent,bad=map(Path,sys.argv[1:5]);out.mkdir(parents=True,exist_ok=True)
sys.argv=[str(here.parent/'previewbrightness1a/verify_preview.py'),str(root),str(out),str(parent)]
g=runpy.run_path(sys.argv[0]);gl=g['gl'];C=g['C'];P=g['P'];I=g['I'];U=g['U'];F=g['F'];shader=g['shader']
assets='app/src/main/assets/shaders/preview/'
for name in ['main_vs.glsl','blur_oes_fs.glsl']:
 shader(0x8b31 if name.endswith('_vs.glsl') else 0x8b30,'#version 300 es\n'+(root/assets/name).read_text())
def program(tree,blur=False):
 vertex=(tree/assets/('quad_vs.glsl' if blur else 'main_vs.glsl')).read_text()
 frag=(tree/assets/('blur_oes_fs.glsl' if blur else 'main_fs.glsl')).read_text()
 frag=frag.replace('#extension GL_OES_EGL_image_external_essl3 : require','').replace('samplerExternalOES','sampler2D')
 pr=gl('glCreateProgram',U)()
 for kind,src in [(0x8b31,vertex),(0x8b30,frag)]:gl('glAttachShader',None,U,U)(pr,shader(kind,'#version 300 es\n'+src))
 gl('glLinkProgram',None,U)(pr);ok=I();gl('glGetProgramiv',None,U,U,P)(pr,0x8b82,C.byref(ok));assert ok.value
 return pr
new,old,blur=program(root),program(parent),program(root,True)
W,H=64,48
# R/G encode source coordinates; B supplies high-contrast asymmetric geometry.
y,x=np.mgrid[:256,:256];chart=np.dstack([x,y,((x//32+2*(y//32))%3)*100,np.full_like(x,255)]).astype(np.uint8)
def texture(unit,w,h,data=None):
 t=U();gl('glGenTextures',None,I,P)(1,C.byref(t));gl('glActiveTexture',None,U)(0x84c0+unit);gl('glBindTexture',None,U,U)(0x0de1,t)
 for pname in [0x2800,0x2801]:gl('glTexParameteri',None,U,U,I)(0x0de1,pname,0x2600)
 for pname in [0x2802,0x2803]:gl('glTexParameteri',None,U,U,I)(0x0de1,pname,0x812f)
 gl('glTexImage2D',None,U,I,I,I,I,I,U,U,P)(0x0de1,0,0x8058,w,h,0,0x1908,0x1401,None if data is None else data.ctypes.data)
 return t
sourceTex=texture(0,256,256,chart);destination=texture(3,W,H)
fbo=U();gl('glGenFramebuffers',None,I,P)(1,C.byref(fbo));gl('glBindFramebuffer',None,U,U)(0x8d40,fbo)
gl('glFramebufferTexture2D',None,U,U,U,U,I)(0x8d40,0x8ce0,0x0de1,destination,0)
assert gl('glCheckFramebufferStatus',U,U)(0x8d40)==0x8cd5
gl('glActiveTexture',None,U)(0x84c0);gl('glBindTexture',None,U,U)(0x0de1,sourceTex)
positions=np.array([1,-1,-1,-1,1,1,-1,1],np.float32);coords=np.array([1,1,0,1,1,0,0,0],np.float32)
vbo=U();gl('glGenBuffers',None,I,P)(1,C.byref(vbo));gl('glBindBuffer',None,U,U)(0x8892,vbo)
vertices=np.c_[positions.reshape(4,2),coords.reshape(4,2)].astype(np.float32)
gl('glBufferData',None,U,C.c_ssize_t,P,U)(0x8892,vertices.nbytes,vertices.ctypes.data,0x88e4)
Fflip=np.diag([1,-1,1,1]).astype(np.float32);Fflip[1,3]=1
identity=np.eye(4,dtype=np.float32)
crop=np.diag([.75,.625,1,1]).astype(np.float32);crop[:2,3]=[.125,.1875]
producerRotation=identity.copy();producerRotation[:2,:2]=[[0,-1],[1,0]];producerRotation[0,3]=1
matrices=[Fflip,identity,crop@Fflip,producerRotation@Fflip]
def draw(pr,R,S,mirror,stage=1,isblur=False):
 gl('glUseProgram',None,U)(pr);loc=lambda n:gl('glGetUniformLocation',I,U,C.c_char_p)(pr,n.encode())
 for name,offset in [('vPosition',0),('vTexCoord',8)]:
  at=gl('glGetAttribLocation',I,U,C.c_char_p)(pr,name.encode())
  if at>=0:
   gl('glVertexAttribPointer',None,U,I,U,U,I,P)(at,2,0x1406,0,16,P(offset));gl('glEnableVertexAttribArray',None,U)(at)
 for name,value in [('sTexture',0),('uM9EvidenceStage2E',stage),('mirror',mirror),('enablePeak',0),('uM9Curve',1),('uM9Inverse2A',2)]:gl('glUniform1i',None,I,I)(loc(name),value)
 for name,m in [('uTexRotateMatrix',R),('uCameraSamplingMatrix',S@Fflip)]:
  column=np.ascontiguousarray(m.T);gl('glUniformMatrix4fv',None,I,I,U,P)(loc(name),1,0,column.ctypes.data)
 gl('glUniform1f',None,I,F)(loc('uCornerRadius'),0)
 for name,vals in [('uViewSize',(W,H)),('uFboSize',(W,H)),('uSharpSize',(W,H)),('uSharpOrigin',(0,0)),('uOffsetPx',(0,0))]:gl('glUniform2f',None,I,F,F)(loc(name),*vals)
 gl('glUniform1f',None,I,F)(loc('uCos'),R[0,0]);gl('glUniform1f',None,I,F)(loc('uSin'),R[1,0])
 gl('glViewport',None,I,I,I,I)(0,0,W,H);gl('glDrawArrays',None,U,I,I)(5,0,4)
 pixels=np.zeros((H,W,4),np.uint8);gl('glReadPixels',None,I,I,I,I,U,U,P)(0,0,W,H,0x1908,0x1401,pixels.ctypes.data)
 return pixels

# The app already has a working sensor-orientation path. A producer rotation
# must not add a second turn to the accepted displayed image.
broken=program(bad);oldBlur=program(parent,True)
checked=0;blurChecked=0;negative=0
for angle in range(4):
 R=identity.copy();R[:2,:2]=np.linalg.matrix_power(np.array([[0,-1],[1,0]]),angle)
 for mirrored in [0,1]:
  reference=draw(old,R,Fflip,mirrored)
  for S in matrices:
   actual=draw(new,R,S,mirrored)
   np.testing.assert_array_equal(actual,reference);checked+=W*H
   np.testing.assert_array_equal(draw(blur,R,S,mirrored),draw(oldBlur,R,Fflip,mirrored));blurChecked+=W*H
  wrong=draw(broken,R,producerRotation@Fflip,mirrored)
  assert not np.array_equal(wrong,reference),"Negative control must detect 2.34 extra rotation"
  negative+=1
assert gl('glGetError',U)()==0
report=dict(status='passed',reference='phone-accepted 2.33',
 sharpPixelsIdentical=checked,blurPixelsIdentical=blurChecked,
 rotations=[0,90,180,270],mirrorStates=[False,True],
 rejected234ExtraRotationCases=negative,phoneValidationPending=True,
 limitation='Synthetic buffer verification and byte-identical rollback to the accepted preview. Actual 2.34 producer matrix was not supplied; this is not a measured handset matrix reproduction.')
(out/'ORIENTATION_GPU_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
