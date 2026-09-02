#!/usr/bin/env python3

def clamp(v): return max(0.,min(1.,v))
def smooth(v,lo,hi):
    t=clamp((v-lo)/(hi-lo)); return t*t*(3-2*t)
def guard(bright,top_share,heter):
    p=smooth(bright,.15,.20)*smooth(top_share,.72,.90)*smooth(heter,.28,.55)
    return p**(1/3) if p>0 else 0
cases={
 '191721_negative_DNG_proxy':(.1974826388888889,.89,.77,True),
 '191721_negative_parity_proxy':(.1974826388888889,.89,.85,True),
 '191728_positive_DNG_proxy':(.12818287037037038,.94,.15,False),
 '191728_positive_parity_proxy':(.12818287037037038,.94,.18,False),
}
for n,(b,t,h,protect) in cases.items():
    g=guard(b,t,h); got=g>=.5
    print(n,'guard',round(g,6),'protect',got)
    assert got==protect,(n,g,protect)
print('LUMA2.4 historical 191721/191728 proxy guard regression: PASS')
