/* GREENORACLE6G diagnostic wrapper.
 * This does not alter Leica routine bytes. It adds wrapper checkpoints around
 * a direct call into the relocated exact GreenInterpolationWithCo body.
 */
    .section .text.start,"ax"
    .global _start
_start:
    SP.H=0; SP.L=0xe800; SP += -0x24;

    /* Pre-call checkpoint. */
    R7.H=0x6f6f; R7.L=0x0001; DBG R7;

    R0.H=0; R0.L=0x4200;
    R1.H=0; R1.L=0x6200;
    R2.H=0; R2.L=0x8200;
    R3.H=0; R3.L=0xa200; [SP+0x0c]=R3;
    R3=STRIDE (Z); [SP+0x10]=R3;
    R3=HEIGHT (Z); [SP+0x14]=R3;
    R3=SHIFTVAL (Z); [SP+0x18]=R3;
    R3.H=0; R3.L=0xc000; [SP+0x1c]=R3;
    R3.H=0xdead; R3.L=0xbeef; [SP+0x20]=R3;

    CALL leica_green;

    /* Post-call checkpoint: absence means Green never returned. */
    R7.H=0x6f6f; R7.L=0x0002; DBG R7;
    SP += 0x24;
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
leica_differ: .incbin "ASMRedBlueAndGreenDiffer.bin"
    .section .f101040,"ax"; .balign 2
leica_f101040: .incbin "ASMFilter_101_040_101_An.bin"
    .section .f101000,"ax"; .balign 2
leica_f101000: .incbin "ASMFilter_101_000_101_2.bin"
    .section .f010,"ax"; .balign 2
leica_f010: .incbin "ASMFilter_010_101_010_2.bin"
    .section .green,"ax"; .balign 2
leica_green: .incbin "GreenInterpolationWithCo.bin"
