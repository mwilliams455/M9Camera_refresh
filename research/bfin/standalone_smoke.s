/*
 * BFINORACLE1A simulator bootstrap.
 *
 * Purpose: prove that the pinned GNU Blackfin assembler/linker/simulator
 * can execute a completely standalone program before Leica firmware bytes
 * are introduced.  No DejaGNU/testutils.inc/libgloss dependency.
 *
 * GNU sim/bfin treats HLT as a simulator exit(0) and ABORT as exit(1).
 */

    .section .text
    .global _start
    .type _start, STT_FUNC

_start:
    /* Deterministic register arithmetic. */
    R0.H = 0x1234;
    R0.L = 0x5678;
    R1.H = 0x1111;
    R1.L = 0x1111;
    R2 = R0 + R1;

    R3.H = 0x2345;
    R3.L = 0x6789;
    CC = R2 == R3;
    IF !CC JUMP .Lfail;

    /* Deterministic memory round-trip in low simulator RAM. */
    P0.H = 0x0000;
    P0.L = 0x1000;
    [P0] = R2;
    R4 = [P0];
    CC = R4 == R3;
    IF !CC JUMP .Lfail;

    HLT;

.Lfail:
    ABORT;

    .size _start, .-_start
