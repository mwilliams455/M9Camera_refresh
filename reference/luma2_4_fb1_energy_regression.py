#!/usr/bin/env python3
from math import pow, log2
cases={
 "074858_positive":dict(pre=810657500.0,score=0.9626037199461038,would=True),
 "075124_negative":dict(pre=34995402918.0,score=0.0,would=False),
}
def clamp(v): return max(0.,min(1.,v))
def smooth(v,lo,hi):
 t=clamp((v-lo)/(hi-lo)); return t*t*(3-2*t)
for name,c in cases.items():
 rec=.75*smooth(c['score'],.35,.85)
 applied=rec if c['would'] else 0.0
 factor=pow(2.,applied); post=c['pre']*factor
 print(name,'rec_ev',round(rec,6),'factor',round(factor,6),'post_energy',round(post,3))
 if c['would']:
  assert abs(applied-.75)<1e-12 and abs(log2(factor)-.75)<1e-12
 else:
  assert applied==0 and factor==1 and post==c['pre']
print('LUMA2.4 FB1 target-energy arithmetic regression: PASS')
