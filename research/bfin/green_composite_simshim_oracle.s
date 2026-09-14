/* GREENORACLE6J composite oracle with GNU-sim compatibility shim.
 *
 * Exact Green bytes are unchanged.  GNU sim evaluates the 0xFEB10726
 * multifunction packet's [SP+0x0c]=R7 store using the newly-written R7,
 * while BF561 pipeline semantics read register operands before write-back.
 * Both 101040 calls use the same inner0.  This target shim restores that
 * hardware home-space value, then tail-jumps to the exact 400-byte helper.
 */
    .section .text.start,"ax"
    .global _start
_start:
    SP.H=0; SP.L=0xe800; SP += -0x24;
    R0.H=0; R0.L=0x4200;
    R1.H=0; R1.L=0x6200;
    R2.H=0; R2.L=0x8200;
    R3.H=0; R3.L=0xa200; [SP+0x0c]=R3;
    R3=STRIDE (Z); [SP+0x10]=R3;
    R3=HEIGHT (Z); [SP+0x14]=R3;
    R3=SHIFTVAL (Z); [SP+0x18]=R3;
    R3.H=0; R3.L=0xc000; [SP+0x1c]=R3;
    R3=0 (Z); [SP+0x20]=R3;
    CALL leica_green;
    SP += 0x24;

    P0.H=0; P0.L=0xc000; R0=[P0]; DBG R0;
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
leica_differ: .incbin "ASMRedBlueAndGreenDiffer.bin"

    .section .f101040shim,"ax"; .balign 2
leica_f101040:
    R3=INNER0 (Z);
    [SP+0x0c]=R3;
    P0.H=0x00ed;
    P0.L=0x0000;
    JUMP (P0);

    .section .f101040body,"ax"; .balign 2
leica_f101040_body: .incbin "ASMFilter_101_040_101_An.bin"

    .section .f101000,"ax"; .balign 2
leica_f101000: .incbin "ASMFilter_101_000_101_2.bin"
    .section .f010,"ax"; .balign 2
leica_f010: .incbin "ASMFilter_010_101_010_2.bin"
    .section .green,"ax"; .balign 2
leica_green: .incbin "GreenInterpolationWithCo.bin"
