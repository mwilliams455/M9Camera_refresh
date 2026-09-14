/* BFINORACLE4B observation harness for ASMFilter_101_000_101_2.
 * INNER, OUTER, STRIDE supplied with --defsym.
 * Recovered ABI from the Leica body:
 *   R0 = source center
 *   R1 = destination stream (+4 before routine's -4)
 *   R2 = inner width/count
 *   [entry SP+0x0c] = outer row count
 *   [entry SP+0x10] = source stride in 16-bit samples
 *
 * The source is centered at halfword 512 (0x4400).  Destination is
 * sentinel-filled so preserved/copied lanes remain visible in DBG output.
 */
    .section .text.start,"ax"
    .global _start
_start:
    SP.H=0; SP.L=0xb800; SP += -0x18;
    R0.H=0; R0.L=0x4400;
    R1.H=0; R1.L=0x7044;
    R2=INNER (Z);
    R3=OUTER (Z); [SP+0x0c]=R3;
    R3=STRIDE (Z); [SP+0x10]=R3;
    CALL leica_filter;
    SP += 0x18;

    P0.H=0; P0.L=0x7040;
    .rept 64
      R0=[P0++]; DBG R0;
    .endr
    HLT;

    .balign 4
leica_filter:
    .incbin "ASMFilter_101_000_101_2.bin"

    .section .source,"aw"; .balign 4
    .include "source_data.inc"

    .section .out,"aw"; .balign 4
    .space 0x40
    .rept 256
      .short 0x1357
    .endr
    .space 0x40

    .section .stack,"aw"; .balign 4
    .space 0x2000
