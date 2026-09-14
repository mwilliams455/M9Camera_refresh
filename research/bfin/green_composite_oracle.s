/* GREENORACLE6F end-to-end oracle for Leica M9 GreenInterpolationWithCo.
 * STRIDE, HEIGHT, SHIFTVAL and PHASEINIT supplied with --defsym.
 *
 * Leica routines are linked at their original BF561 virtual addresses because
 * GreenInterpolationWithCo contains already-encoded direct CALL displacements.
 * Four 1024-halfword planes are dumped in full after the call.  No scratch or
 * guard addresses inside those planes are excluded from parity.
 */

    .section .text.start,"ax"
    .global _start
_start:
    SP.H=0; SP.L=0xe800; SP += -0x24;

    /* Live Green ABI: R0=A, R1=B, R2=C. */
    R0.H=0; R0.L=0x4200;
    R1.H=0; R1.L=0x6200;
    R2.H=0; R2.L=0x8200;

    /* Green FP+0x14 .. FP+0x24 after its LINK 4. */
    R3.H=0; R3.L=0xa200; [SP+0x0c]=R3;
    R3=STRIDE (Z); [SP+0x10]=R3;
    R3=HEIGHT (Z); [SP+0x14]=R3;
    R3=SHIFTVAL (Z); [SP+0x18]=R3;
    R3.H=0; R3.L=0xc000; [SP+0x1c]=R3;

    /* Incoming sixth home-space word is dead in this firmware body. */
    R3.H=0xdead; R3.L=0xbeef; [SP+0x20]=R3;

    CALL leica_green;
    SP += 0x24;

    /* First DBG value is the mutable phase/counter word. */
    P0.H=0; P0.L=0xc000; R0=[P0]; DBG R0;

    /* Then 512 dwords = 1024 halfwords from each complete plane. */
    P0.H=0; P0.L=0x4000;
    .rept 512
      R0=[P0++]; DBG R0;
    .endr
    P0.H=0; P0.L=0x6000;
    .rept 512
      R0=[P0++]; DBG R0;
    .endr
    P0.H=0; P0.L=0x8000;
    .rept 512
      R0=[P0++]; DBG R0;
    .endr
    P0.H=0; P0.L=0xa000;
    .rept 512
      R0=[P0++]; DBG R0;
    .endr
    HLT;

    .section .planeA,"aw"; .balign 4
    .include "plane_a.inc"
    .section .planeB,"aw"; .balign 4
    .include "plane_b.inc"
    .section .planeC,"aw"; .balign 4
    .include "plane_c.inc"
    .section .planeD,"aw"; .balign 4
    .include "plane_d.inc"

    .section .phase,"aw"; .balign 4
    .long PHASEINIT

    .section .stack,"aw"; .balign 4
    .space 0x2000

    .section .differ,"ax"; .balign 2
leica_differ:
    .incbin "ASMRedBlueAndGreenDiffer.bin"

    .section .f101040,"ax"; .balign 2
leica_f101040:
    .incbin "ASMFilter_101_040_101_An.bin"

    .section .f101000,"ax"; .balign 2
leica_f101000:
    .incbin "ASMFilter_101_000_101_2.bin"

    .section .f010,"ax"; .balign 2
leica_f010:
    .incbin "ASMFilter_010_101_010_2.bin"

    .section .green,"ax"; .balign 2
leica_green:
    .incbin "GreenInterpolationWithCo.bin"
