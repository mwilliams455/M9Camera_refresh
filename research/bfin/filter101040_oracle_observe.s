/* BFINORACLE3A observation harness for ASMFilter_101_040_101_An.
 * INNER, OUTER, STRIDE supplied with --defsym.
 * R0 source center, R1 output stream 1 (+2 before routine's -2),
 * R2 output stream 2 (+4 before routine's -4).
 */
    .section .text.start,"ax"
    .global _start
_start:
    SP.H=0; SP.L=0xb800; SP += -0x18;
    R0.H=0; R0.L=0x4400;
    R1.H=0; R1.L=0x7042;
    R2.H=0; R2.L=0x8044;
    R3=INNER (Z); [SP+0x0c]=R3;
    R3=OUTER (Z); [SP+0x10]=R3;
    R3=STRIDE (Z); [SP+0x14]=R3;
    CALL leica_filter;
    SP += 0x18;
    P0.H=0; P0.L=0x7040;
    .rept 64
      R0=[P0++]; DBG R0;
    .endr
    P0.H=0; P0.L=0x8040;
    .rept 64
      R0=[P0++]; DBG R0;
    .endr
    HLT;
    .balign 4
leica_filter:
    .incbin "ASMFilter_101_040_101_An.bin"

    .section .source,"aw"; .balign 4
    .include "source_data.inc"

    .section .out1,"aw"; .balign 4
    .space 0x40
    .rept 256
      .short 0x1357
    .endr
    .space 0x40

    .section .out2,"aw"; .balign 4
    .space 0x40
    .rept 256
      .short 0x2468
    .endr
    .space 0x40

    .section .stack,"aw"; .balign 4
    .space 0x2000
