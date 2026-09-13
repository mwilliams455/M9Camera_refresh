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
 *
 * The routine performs 32-bit accesses at green/output positions reached
 * after adding an 18-byte first-pass phase offset (and 34-byte second-pass
 * offset).  Therefore the green/output argument bases must be 2 mod 4 so
 * those effective addresses are word-aligned.  Difference samples are read
 * as 16-bit words and remain on the aligned 0x4040 base.
 */

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
    /* Give the Leica routine a deterministic writable stack. */
    SP.H = 0x0000;
    SP.L = 0x9800;

    /* Caller argument-home area: 3 register homes + 4 stack arguments. */
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

    /* First DBG word is the post-call support/border value. */
    P0.H = 0x0000;
    P0.L = 0x8000;
    R0 = [P0];
    DBG R0;

    /*
     * Dump from the aligned section starts, not the +2 ABI pointers, so the
     * simulator's diagnostic 32-bit reads stay naturally aligned.  The first
     * u16 is thus a guard/sentinel preceding the routine's output base.
     */
    P0.H = 0x0000;
    P0.L = 0x6000;
    .rept DUMP_WORDS
        R0 = [P0++];
        DBG R0;
    .endr

    P0.H = 0x0000;
    P0.L = 0x7000;
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
     * Guarded synthetic planes.  The ABI pointers are inside the guard area
     * so the routine's complementary checkerboard phase can move in either
     * direction without leaving mapped memory.
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
