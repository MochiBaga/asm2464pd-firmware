/*
 * timer.h - Timer driver declarations
 */
#ifndef _TIMER_H_
#define _TIMER_H_

#include "../types.h"

/* Timer ISR and control */
void timer0_isr(void) __interrupt(1) __using(0);
void timer0_csr_ack(void);
void timer0_wait_done(void);
void timer1_check_and_ack(void);

/* Timer event handlers */
void timer_idle_timeout_handler(void);
void timer_uart_debug_output(void);
void timer_pcie_link_event(void);
void timer_pcie_async_event(void);
void timer_system_event_stub(void);
void timer_pcie_error_handler(void);
void timer_nvme_completion(void);
void timer_link_status_handler(void);

/* System handlers */
void system_interrupt_handler(void);
void system_timer_handler(void);

/* Timer configuration */
void timer_wait(uint8_t timeout_lo, uint8_t timeout_hi, uint8_t mode);
void timer_config_trampoline(uint8_t p1, uint8_t p2, uint8_t p3);
void timer_event_init(void);
void timer_trigger_e726(void);
void timer_phy_config_e57d(uint8_t param);

/* Delay functions */
void delay_loop_adb0(void);

#endif /* _TIMER_H_ */
