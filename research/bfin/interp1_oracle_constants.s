/*
 * BFINORACLE1B — parameterized constant-vector harness for Leica
 * ASMRedBlueInterpolation1.
 *
 * The Leica routine body is reconstructed and SHA-gated in CI; no firmware
 * bytes are stored here.  ORACLE_DIFF_VALUE and ORACLE_GREEN_VALUE may be
 * supplied with GNU as --defsym.  Defaults reproduce the frozen zero vector.
 *
 * Recovered ABI phase property: green/output base pointers are 2 mod 4 so
 * the routine's +18/+34-byte 32-bit accesses are naturally word aligned.
 */

    .ifndef ORACLE_DIFF_VALUE
    .set ORACLE_DIFF_VALUE, 0
    .endif
    .ifndef ORACLE_GREEN_VALUE
    .set ORACLE_GREEN_VALUE, 1000
    .endif

    .equ DIFF_BASE,   0x00004040
    .equ GREEN_BASE,  0x00005042
    .equ OUTA_BASE,   0x00006042
    .equ OUTB_BASE,   0x00007042
    .equ BORDER_ADDR, 0x00008000
    .equ STACK_TOP,   0x00009800
    .equ WIDTH,       8
    .equ HEIGHT,      8
    .equ DUMP_WORDS,  64

    .section .text.start,"ax"
    .global _start
    .type _start, STT_FUNC
_start:
    SP.H = 0x0000;
    SP.L = 0x9800;
    SP += -0x1c;

    R0.H = 0x0000;
    R0.L = 0x4040;
    R1.H = 0x0000;
    R1.L = 0x5042;
    R2.H = 0x0000;
    R2.L = 0x6042;

    R3.H = 0x0000;
    R3.L = 0x7042;
    [SP + 0x0c] = R3;
    R3 = WIDTH (Z);
    [SP + 0x10] = R3;
    R3 = HEIGHT (Z);
    [SP + 0x14] = R3;
    R3.H = 0x0000;
    R3.L = 0x8000;
    [SP + 0x18] = R3;

    CALL leica_interp1;
    SP += 0x1c;

    P0.H = 0x0000;
    P0.L = 0x8000;
    R0 = [P0];
    DBG R0;

    /* Aligned dump boundary immediately before the +2 output ABI base. */
    P0.H = 0x0000;
    P0.L = 0x6040;
    .rept DUMP_WORDS
        R0 = [P0++];
        DBG R0;
    .endr

    P0.H = 0x0000;
    P0.L = 0x7040;
    .rept DUMP_WORDS
        R0 = [P0++];
        DBG R0;
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
    .rept 256
        .short ORACLE_DIFF_VALUE
    .endr
    .space 0x40

    .section .oracle_green,"aw"
    .balign 4
    .space 0x40
    .rept 256
        .short ORACLE_GREEN_VALUE
    .endr
    .space 0x40

    .section .oracle_outa,"aw"
    .balign 4
    .space 0x40
    .rept 256
        .short 0
    .endr
    .space 0x40

    .section .oracle_outb,"aw"
    .balign 4
    .space 0x40
    .rept 256
        .short 0
    .endr
    .space 0x40

    .section .oracle_border,"aw"
    .balign 4
    .long 0

    .section .oracle_stack,"aw"
    .balign 4
    .space 0x1000
