/* GREENORACLE6K: observe every helper ABI from exact GreenInterpolationWithCo.
 *
 * The production 810-byte Green body is unchanged. Each exact helper CALL lands
 * on a diagnostic trampoline at the uniformly-relocated firmware target. The
 * trampoline logs R0/R1/R2 plus original caller stack words +0x0c..+0x20,
 * restores all scratch state, and tail-jumps to the exact helper body moved to
 * a simulator-safe island. Only the 101040 trampoline corrects caller [SP+0x0c]
 * to INNER0, compensating the already-proven GNU-sim vs BF561 packet semantic at
 * firmware 0xFEB10786 (R7 write in parallel with old-R7 stack store).
 */

    .macro LOG_AND_TAIL markhi, marklo, bodyhi, bodylo, fixinner=0
      [--SP]=R3;
      [--SP]=R7;
      R7.H=\markhi; R7.L=\marklo; DBG R7;
      DBG R0; DBG R1; DBG R2;
      /* Two pushes mean original S+0x0c is now SP+0x14. */
      R3=[SP+0x14]; DBG R3;
      R3=[SP+0x18]; DBG R3;
      R3=[SP+0x1c]; DBG R3;
      R3=[SP+0x20]; DBG R3;
      R3=[SP+0x24]; DBG R3;
      R7=[SP++];
      R3=[SP++];
      .if \fixinner
        R3=INNER0 (Z);
        [SP+0x0c]=R3;
      .endif
      P0.H=\bodyhi;
      P0.L=\bodylo;
      JUMP (P0);
    .endm

    .section .text.start,"ax"
    .global _start
_start:
    SP.H=0; SP.L=0xe800; SP += -0x24;
    R0.H=0; R0.L=0x4200;
    R1.H=0; R1.L=0x6200;
    R2.H=0; R2.L=0x8200;
    R3.H=0; R3.L=0xa200; [SP+0x0c]=R3;
    R3=STRIDE (Z); [SP+0x10]=R3;
    R3=HEIGHT (Z); [SP+0x14]=R3;
    R3=SHIFTVAL (Z); [SP+0x18]=R3;
    R3.H=0; R3.L=0xc000; [SP+0x1c]=R3;
    R3=0 (Z); [SP+0x20]=R3;
    R7.H=0x6b00; R7.L=0x0001; DBG R7;
    CALL leica_green;
    R7.H=0x6b00; R7.L=0x0002; DBG R7;
    SP += 0x24;
    HLT;

    .section .planeA,"aw"; .balign 4
    .include "plane_a.inc"
    .section .planeB,"aw"; .balign 4
    .include "plane_b.inc"
    .section .planeC,"aw"; .balign 4
    .include "plane_c.inc"
    .section .planeD,"aw"; .balign 4
    .include "plane_d.inc"
    .section .phase,"aw"; .balign 4
    .long PHASEINIT
    .section .stack,"aw"; .balign 4
    .space 0x2000

    /* Uniformly relocated exact CALL targets become trampoline islands. */
    .section .differ_shim,"ax"; .balign 2
leica_differ:
    LOG_AND_TAIL 0x6b02, 0x0001, 0x00ea, 0x0000, 0

    .section .f101040_shim,"ax"; .balign 2
leica_f101040:
    LOG_AND_TAIL 0x6b03, 0x0001, 0x00e9, 0x0000, 1

    .section .f101000_shim,"ax"; .balign 2
leica_f101000:
    LOG_AND_TAIL 0x6b04, 0x0001, 0x00eb, 0x0000, 0

    .section .f010_shim,"ax"; .balign 2
leica_f010:
    LOG_AND_TAIL 0x6b01, 0x0001, 0x00e8, 0x0000, 0

    /* Exact helper bodies, byte-identical to canonical firmware. */
    .section .f010_body,"ax"; .balign 2
leica_f010_body: .incbin "ASMFilter_010_101_010_2.bin"
    .section .f101040_body,"ax"; .balign 2
leica_f101040_body: .incbin "ASMFilter_101_040_101_An.bin"
    .section .differ_body,"ax"; .balign 2
leica_differ_body: .incbin "ASMRedBlueAndGreenDiffer.bin"
    .section .f101000_body,"ax"; .balign 2
leica_f101000_body: .incbin "ASMFilter_101_000_101_2.bin"

    .section .green,"ax"; .balign 2
leica_green: .incbin "GreenInterpolationWithCo.bin"
