/* GREENORACLE6M: random-data phase-1 physical-write oracle for
 * ASMFilter_101_040_101_An. INNER/OUTER/STRIDE supplied by --defsym.
 * Source is deliberately R0 mod4 == 2. Output windows include pre-pointer guard.
 */
    .section .text.start,"ax"
    .global _start
_start:
    SP.H=0; SP.L=0xb800; SP += -0x18;
    R0.H=0; R0.L=0x4402;
    R1.H=0; R1.L=0x7042;
    R2.H=0; R2.L=0x8044;
    R3=INNER (Z); [SP+0x0c]=R3;
    R3=OUTER (Z); [SP+0x10]=R3;
    R3=STRIDE (Z); [SP+0x14]=R3;
    CALL leica_filter;
    SP += 0x18;

    P0.H=0; P0.L=0x7000;
    .rept 96
      R0=[P0++]; DBG R0;
    .endr
    P0.H=0; P0.L=0x8000;
    .rept 96
      R0=[P0++]; DBG R0;
    .endr
    HLT;

    .section .source,"aw"; .balign 4
    .include "source_data.inc"
    .section .out1,"aw"; .balign 4
    .rept 512
      .short 0x1357
    .endr
    .section .out2,"aw"; .balign 4
    .rept 512
      .short 0x2468
    .endr
    .section .stack,"aw"; .balign 4
    .space 0x2000

    .section .filter,"ax"; .balign 2
leica_filter:
    .incbin "ASMFilter_101_040_101_An.bin"
