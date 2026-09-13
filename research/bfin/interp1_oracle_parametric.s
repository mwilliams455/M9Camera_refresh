/* Parametric BFIN oracle harness for ASMRedBlueInterpolation1.
 * WIDTH, HEIGHT, SUPPORT_INIT, GREEN_PTR, OUTA_PTR, OUTB_PTR are supplied
 * with --defsym.  For even image widths the Leica caller must alternate the
 * green/output halfword phase with support_after parity so the routine's
 * 32-bit accesses remain word aligned.
 */
    .equ DUMP_WORDS, 128
    .section .text.start,"ax"
    .global _start
    .type _start, STT_FUNC
_start:
    SP.H = 0x0000; SP.L = 0x9800; SP += -0x1c;
    R0.H = 0x0000; R0.L = 0x4040;
    R1.H = 0x0000; R1.L = GREEN_PTR;
    R2.H = 0x0000; R2.L = OUTA_PTR;
    R3.H = 0x0000; R3.L = OUTB_PTR; [SP + 0x0c] = R3;
    R3 = WIDTH (Z); [SP + 0x10] = R3;
    R3 = HEIGHT (Z); [SP + 0x14] = R3;
    R3.H = 0x0000; R3.L = 0x8000; [SP + 0x18] = R3;
    CALL leica_interp1;
    SP += 0x1c;
    P0.H=0; P0.L=0x8000; R0=[P0]; DBG R0;
    P0.H=0; P0.L=0x6040;
    .rept DUMP_WORDS
      R0=[P0++]; DBG R0;
    .endr
    P0.H=0; P0.L=0x7040;
    .rept DUMP_WORDS
      R0=[P0++]; DBG R0;
    .endr
    HLT;
    .size _start, .-_start

    .balign 4
    .global leica_interp1
leica_interp1:
    .incbin "ASMRedBlueInterpolation1.bin"

    .section .oracle_diff,"aw"
    .balign 4
    .space 0x40
    .include "oracle_diff_data.inc"
    .space 0x40

    .section .oracle_green,"aw"
    .balign 4
    .space 0x40
    .include "oracle_green_data.inc"
    .space 0x40

    .section .oracle_outa,"aw"
    .balign 4
    .space 0x40
    .rept 512
      .short 0
    .endr
    .space 0x40

    .section .oracle_outb,"aw"
    .balign 4
    .space 0x40
    .rept 512
      .short 0
    .endr
    .space 0x40

    .section .oracle_border,"aw"
    .balign 4
    .long SUPPORT_INIT

    .section .oracle_stack,"aw"
    .balign 4
    .space 0x1000
