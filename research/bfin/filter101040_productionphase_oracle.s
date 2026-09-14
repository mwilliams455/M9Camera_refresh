/* GREENORACLE6N: exact physical-write oracle for the production phase pairs
 * used by GreenInterpolationWithCo's second ASMFilter_101_040_101_An call.
 * SRCBASE/OUT1BASE/OUT2BASE/INNER/OUTER/STRIDE supplied by --defsym.
 * Source and output windows are random-data includes so packed neighbour
 * preservation/permutation remains observable; whole windows are dumped.
 */
    .section .text.start,"ax"
    .global _start
_start:
    SP.H=0; SP.L=0xb800; SP += -0x18;
    R0.H=0; R0.L=SRCBASE;
    R1.H=0; R1.L=OUT1BASE;
    R2.H=0; R2.L=OUT2BASE;
    R3=INNER (Z); [SP+0x0c]=R3;
    R3=OUTER (Z); [SP+0x10]=R3;
    R3=STRIDE (Z); [SP+0x14]=R3;
    CALL leica_filter;
    SP += 0x18;

    P0.H=0; P0.L=0x7000;
    .rept 256
      R0=[P0++]; DBG R0;
    .endr
    P0.H=0; P0.L=0x8000;
    .rept 256
      R0=[P0++]; DBG R0;
    .endr
    HLT;

    .section .source,"aw"; .balign 4
    .include "source_data.inc"
    .section .out1,"aw"; .balign 4
    .include "out1_data.inc"
    .section .out2,"aw"; .balign 4
    .include "out2_data.inc"
    .section .stack,"aw"; .balign 4
    .space 0x2000

    .section .filter,"ax"; .balign 2
leica_filter:
    .incbin "ASMFilter_101_040_101_An.bin"
