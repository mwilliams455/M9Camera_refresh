# Partial directional chroma trial

`chroma.cpp` is an offline native candidate at the pre-SAT Q14 RGB boundary.
It finds the directional median chroma estimate requiring the smallest change,
then applies a caller-supplied fraction of that correction. Rec.709-weighted
luma is held before rounding and range limits. It contains no hue classifier,
ISO switch, sharpening or scene lookup. Tested strengths are 0.25 and 0.50.

Zero strength, flat colours, achromatic texture and connected straight colour
lines remain exact. Isolated genuine colour points can lose colour contrast;
partial strength limits but does not eliminate that tradeoff. This is not an
accepted colour fix and is not integrated in the application renderer.

The photographic harness and evidence are kept separately from this source branch.
The test reconstruction is pinned AMaZE without the old green graft or Sharp;
current reconstruction remains the control. No private images or measurements
are stored in this branch.
