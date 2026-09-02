#!/usr/bin/env python3
"""Confirm v0.7L preserves frozen LUMA2.2 decisions on 12 field metric rows."""
import json
from pathlib import Path
from luma2_2_backlight_scorer_reference import score
HERE=Path(__file__).resolve().parent
ROWS=json.loads((HERE/'luma2_3_k_field_inputs.json').read_text())
EXPECTED={
 '180145':(False,0.0),'180202':(True,0.75),'180216':(True,0.41935670457692387),
 '180236':(True,0.5474369682478378),'180311':(True,0.75),'181706':(False,0.0),
 '182446':(False,0.0),'182457':(True,0.75),'185844':(True,0.75),
 '190029':(False,0.0),'191721':(True,0.75),'191728':(True,0.75),
}
def minimal(r):
 return {'photonExposureDecision':{'preview':{'exposureEnergyIsoSeconds':r['energy']}},
  'subjectMotion':{'previewLuma':{'global':{'median':r['median'],'q95':r['q95'],'q99':r['q99'],
  'darkFractionLE64':r['dark64'],'brightFractionGE192':r['bright192'],'q95MinusMedian':r['sep']},
  'center50':{'medianMinusGlobalMedian':r['centerDelta']}}}}
for r in ROWS:
 got=score(minimal(r)); wa,we=EXPECTED[r['frame']]
 assert got['wouldApply']==wa,(r['frame'],got)
 assert abs(got['recommendedExposureCorrectionEv']-we)<1e-9,(r['frame'],got)
print('LUMA2.3-SPATIAL1 frozen LUMA2.2 12-frame decision regression: PASS')
print('Known 191721 false positive intentionally remains for spatial measurement.')
