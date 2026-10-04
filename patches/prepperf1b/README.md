# M9 PREPPERF1B — PERSISTENT8 exact preparation

Parent: **1.91 M9PHASENOISEPERF1B SYMTILE EXACT**.

Phone validation of 1.91 reduced phase noise to about 781 ms. The latest capture
showed pre-SAT preparation at about 406 ms. PREPPERF1A still creates two
std::thread worker teams for every 128-row band: one for camera->M9 and one for
partial chroma. A 3072-row frame therefore creates 48 worker teams.

PREPPERF1B keeps the exact 128-row in-place halo model and creates one OpenMP
8-thread team for the entire frame. Implicit barriers preserve the same stage
ordering:

1. restore the previous two transformed halo rows;
2. exact camera->M9 transform on disjoint rows;
3. preserve the next two transformed halo rows;
4. exact memcpy seed of the corrected band;
5. exact 0.25 partial-chroma arithmetic on disjoint rows;
6. commit the finished central rows in place.

No camera transform coefficient, HSM/SAT behavior, chroma amount, luma
coefficient, rounding operation, band size, exposure, TC20, AMaZE, phase-noise
or NOISECANCEL behavior changes.

Hard gates:
- byte-exact versus frozen scalar preparation;
- byte-exact versus PREPPERF1A;
- varied dimensions and band boundaries;
- full 4096x3072 parity at production bandRows=128;
- same-run host timing against PREPPERF1A.

Version: **1.92-m9prepperf1b-persistent8-phasenoiseperf1b-tg1**.
