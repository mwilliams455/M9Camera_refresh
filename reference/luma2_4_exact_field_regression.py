#!/usr/bin/env python3
from math import isclose

def clamp(v): return max(0.,min(1.,v))
def smooth(v,lo,hi):
    t=clamp((v-lo)/(hi-lo)); return t*t*(3-2*t)

def spatial(dark,q95,bright,axis_norm,low_ratio):
    vals=(smooth(dark,.28,.35),smooth(q95,135,175),smooth(bright,.008,.035),smooth(axis_norm,.30,.48),1-smooth(low_ratio,.28,.40))
    p=1
    for v in vals:p*=v
    return p**.2 if p>0 else 0

cases={
 '065330_positive':dict(dark=.32320601851851855,q95=189,bright=.04123263888888889,axis=101/189,low=38/189,expect=True),
 '065403_positive':dict(dark=.48451967592592593,q95=191,bright=.04586226851851852,axis=114/191,low=24/191,expect=True),
 '072515_negative':dict(dark=.49464699074074076,q95=118,bright=.00043402777777777775,axis=28/118,low=47/118,expect=False),
 # 065131 is retained as a conservative structural control: its dark-body
 # occupancy is below the spatial-branch floor, so bright-window geometry alone
 # does not establish a positive.
 '065131_bright_window_control':dict(dark=.2494212962962963,q95=197,bright=.07146990740740741,axis=109/197,low=53/197,expect=False),
}
for name,c in cases.items():
    s=spatial(c['dark'],c['q95'],c['bright'],c['axis'],c['low']); got=s>=.5
    print(name, 'score', round(s,6), 'apply', got)
    assert got==c['expect'], (name,s,c['expect'])
print('LUMA2.4 exact-field spatial branch regression: PASS')
