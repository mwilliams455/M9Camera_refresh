/* GREENORACLE6D observation harness for Leica M9 ASMFilter_010_101_010_2.
 * INNER, OUTER, STRIDE, SRCBASE, DESTBASE and MODE supplied with --defsym.
 * Dumps the entire 256-halfword destination observation window as 128 DBG dwords.
 */
    .section .text.start,"ax"
    .global _start
_start:
    SP.H=0; SP.L=0xb800; SP += -0x18;
    R0.H=0; R0.L=SRCBASE;
    R1.H=0; R1.L=DESTBASE;
    R2=INNER (Z);
    R3=OUTER (Z); [SP+0x0c]=R3;
    R3=STRIDE (Z); [SP+0x10]=R3;
    R3=MODE (Z); [SP+0x14]=R3;
    CALL leica_filter;
    SP += 0x18;

    P0.H=0; P0.L=0x7000;
    .rept 128
      R0=[P0++]; DBG R0;
    .endr
    HLT;

    .balign 4
leica_filter:
    .incbin "ASMFilter_010_101_010_2.bin"

    .section .source,"aw"; .balign 4
    .include "source_data.inc"

    .section .dest,"aw"; .balign 4
    .rept 256
      .short 0x5a5a
    .endr

    .section .stack,"aw"; .balign 4
    .space 0x2000
