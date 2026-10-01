/* No user-controlled address is dereferenced by these exception veneers.
 * C validates the basic exception frame before reading it. No FP user ABI. */
.syntax unified
.cpu cortex-m4
.thumb
.section .text.plc_handlers,"ax",%progbits
.global plc_svc_handler
.type plc_svc_handler,%function
.thumb_func
plc_svc_handler:
    mrs r2, control
    tst r2, #1
    beq vPortSVCHandler
    mrs r0, psp
    mov r1, lr
    b guard_svc
.size plc_svc_handler, .-plc_svc_handler
.macro FRAME_HANDLER name, target
.global \name
.type \name,%function
.thumb_func
\name:
    tst lr, #4
    ite eq
    mrseq r0, msp
    mrsne r0, psp
    mov r1, lr
    mrs r2, control
    b \target
.size \name, .-\name
.endm
FRAME_HANDLER plc_fault_handler, guard_fault
FRAME_HANDLER plc_timer_handler, guard_timer

/* This immutable trampoline is the sole permitted user service. It exposes no
 * RTOS handles, privileged pointers or I/O service. Arguments use ABI 2. */
.section .user_gate,"ax",%progbits
.balign 4
.global plc_worker
.type plc_worker,%function
.thumb_func
plc_worker:
    ldr r0, =0x20018000
    ldr r1, =0x20018200
    ldr r12, =0x20018100 /* supervisor-owned input-region descriptor */
    ldr r2, [r12, #4]
    ldr r3, =0x20018300
    /* Firmware flash and SRAM are beyond a direct Thumb BL displacement. */
    ldr r12, [r12]
    blx r12
.global plc_return_svc
plc_return_svc:
    svc #200
    b plc_worker
.global plc_abort_loop
.type plc_abort_loop,%function
.thumb_func
plc_abort_loop:
    b plc_abort_loop
.ltorg
.size plc_worker, .-plc_worker
.section .note.GNU-stack,"",%progbits
