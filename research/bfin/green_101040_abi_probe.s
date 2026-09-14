/* GREENORACLE6I diagnostic-only Green/101040 ABI probe.
 * Green remains exact. Its embedded CALL target remains 0xEFFA5E.
 * At that address this trampoline prints the three register args and the
 * three 101040 home-space args, then tail-jumps to an exact helper copy.
 */
    .section .text.start,"ax"
    .global _start
_start:
    SP.H=0; SP.L=0xe800; SP += -0x24;
    R0.H=0; R0.L=0x4200;
    R1.H=0; R1.L=0x6200;
    R2.H=0; R2.L=0x8200;
    R3.H=0; R3.L=0xa200; [SP+0x0c]=R3;
    R3=16 (Z); [SP+0x10]=R3;
    R3=12 (Z); [SP+0x14]=R3;
    R3=2 (Z); [SP+0x18]=R3;
    R3.H=0; R3.L=0xc000; [SP+0x1c]=R3;
    R3=0 (Z); [SP+0x20]=R3;
    CALL leica_green;
    R7.H=0x6f6f; R7.L=0x6002; DBG R7;
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
    .long 0
    .section .stack,"aw"; .balign 4
    .space 0x2000

    .section .differ,"ax"; .balign 2
leica_differ: .incbin "ASMRedBlueAndGreenDiffer.bin"

    .section .f101040tramp,"ax"; .balign 2
leica_f101040:
    DBG R0;
    DBG R1;
    DBG R2;
    R3=[SP+0x0c]; DBG R3;
    R3=[SP+0x10]; DBG R3;
    R3=[SP+0x14]; DBG R3;
    P0.H=0x00ed; P0.L=0x0000;
    JUMP (P0);

    .section .f101040body,"ax"; .balign 2
leica_f101040_body: .incbin "ASMFilter_101_040_101_An.bin"

    .section .f101000,"ax"; .balign 2
leica_f101000: .incbin "ASMFilter_101_000_101_2.bin"
    .section .f010,"ax"; .balign 2
leica_f010: .incbin "ASMFilter_010_101_010_2.bin"
    .section .green,"ax"; .balign 2
leica_green: .incbin "GreenInterpolationWithCo.bin"
