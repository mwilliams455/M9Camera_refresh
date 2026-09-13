/*
 * BFINORACLE1A — first executable Leica ASMRedBlueInterpolation1 oracle.
 *
 * The Leica body is not stored in git. CI reconstructs the canonical M9
 * BF561 image, extracts exactly 0x248 bytes from 0xFFA03410, verifies its
 * SHA-256, places it next to this source as ASMRedBlueInterpolation1.bin,
 * and assembles this harness around it.
 *
 * ABI recovered from the routine prologue:
 *   arg0 R0  : signed 16-bit difference plane
 *   arg1 R1  : 14-bit green plane (packed as adjacent u16 samples)
 *   arg2 R2  : reconstructed output plane A
 *   arg3 stk : reconstructed output plane B
 *   arg4 stk : width-like extent
 *   arg5 stk : height-like extent
 *   arg6 stk : pointer to mutable support/border integer
 *
 * R0/R1/R2 still receive caller home slots at SP+0/+4/+8, while args 3..6
 * occupy SP+0x0c..SP+0x18.  This harness deliberately preserves that ABI.
 */

    .equ DIFF_BASE,   0x00004040
    .equ GREEN_BASE,  0x00005040
    .equ OUTA_BASE,   0x00006040
    .equ OUTB_BASE,   0x00007040
    .equ BORDER_ADDR, 0x00008000
    .equ STACK_TOP,   0x00009800
    .equ WIDTH,       8
    .equ HEIGHT,      8
    .equ DUMP_WORDS,  64

    .section .text.start,"ax"
    .global _start
    .type _start, STT_FUNC

_start:
    /* Give the Leica routine a deterministic writable stack. */
    SP.H = 0x0000;
    SP.L = 0x9800;

    /* Caller argument-home area: 3 register homes + 4 stack arguments. */
    SP += -0x1c;

    R0.H = 0x0000;
    R0.L = 0x4040;
    R1.H = 0x0000;
    R1.L = 0x5040;
    R2.H = 0x0000;
    R2.L = 0x6040;

    R3.H = 0x0000;
    R3.L = 0x7040;
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

    /* First DBG word is the post-call support/border value. */
    P0.H = 0x0000;
    P0.L = 0x8000;
    R0 = [P0];
    DBG R0;

    /* Then DUMP_WORDS packed 32-bit words from output A. */
    P0.H = 0x0000;
    P0.L = 0x6040;
    .rept DUMP_WORDS
        R0 = [P0++];
        DBG R0;
    .endr

    /* Then DUMP_WORDS packed 32-bit words from output B. */
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

    /*
     * Guarded synthetic planes.  The base pointer is +0x40 from each section
     * start so the routine's complementary checkerboard phase may walk
     * backwards without leaving mapped memory.
     */
    .section .oracle_diff,"aw"
    .balign 4
    .space 0x40
    .rept 256
        .short 0
    .endr
    .space 0x40

    .section .oracle_green,"aw"
    .balign 4
    .space 0x40
    .rept 256
        .short 1000
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
