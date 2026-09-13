/* Parametric geometry harness for ASMRedBlueAndGreenDiffer.
 * INNER, OUTER, STRIDE, SHIFTVAL supplied with --defsym.
 * Inputs/output are one halfword lane in 32-bit cells.
 */
    .section .text.start,"ax"
    .global _start
_start:
    SP.H=0; SP.L=0x9800; SP += -0x20;
    R0.H=0; R0.L=0x4040;
    R1.H=0; R1.L=0x5040;
    R2.H=0; R2.L=0x6040;
    R3.H=0; R3.L=0x7040; [SP+0x0c]=R3;
    R3=INNER (Z); [SP+0x10]=R3;
    R3=OUTER (Z); [SP+0x14]=R3;
    R3=STRIDE (Z); [SP+0x18]=R3;
    R3=SHIFTVAL (Z); [SP+0x1c]=R3;
    CALL leica_differ;
    SP += 0x20;
    P0.H=0; P0.L=0x7040;
    .rept 128
      R0=[P0++]; DBG R0;
    .endr
    HLT;
    .balign 4
leica_differ:
    .incbin "ASMRedBlueAndGreenDiffer.bin"

    .section .plane0,"aw"; .balign 4; .space 0x40
    .include "plane0_data.inc"
    .space 0x40
    .section .plane1,"aw"; .balign 4; .space 0x40
    .include "plane1_data.inc"
    .space 0x40
    .section .threshold,"aw"; .balign 4; .space 0x40
    .include "threshold_data.inc"
    .space 0x40
    .section .output,"aw"; .balign 4; .space 0x40
    .rept 256
      .short 0x1357
      .short 0x5a5a
    .endr
    .space 0x40
    .section .stack,"aw"; .balign 4; .space 0x1000
