/*
 * dma.h - DMA Engine Driver
 *
 * The DMA engine provides high-speed data transfer between USB endpoints,
 * NVMe buffers, and internal SRAM without CPU intervention. It supports
 * both scatter-gather operations and contiguous transfers.
 *
 * DMA ARCHITECTURE:
 *   USB Endpoint Buffers <---> DMA Engine <---> NVMe Data Buffers
 *                                  ↓
 *                          SCSI Data Buffers
 *
 * CHANNEL CONFIGURATION:
 *   - Multiple DMA channels for concurrent operations
 *   - Per-channel source/destination addressing
 *   - Configurable transfer sizes and burst modes
 *   - Interrupt on completion support
 *
 * TRANSFER MODES:
 *   - USB RX: Host → USB Controller → DMA → Internal Buffer
 *   - USB TX: Internal Buffer → DMA → USB Controller → Host
 *   - NVMe: PCIe TLP data ↔ Internal buffers
 *
 * KEY REGISTERS (0xCE00-0xCEFF):
 *   0xCE6E: SCSI DMA control register
 *   0xCE96: DMA status/completion flags
 *
 * SCSI BUFFER MANAGEMENT:
 *   The DMA engine maintains SCSI command/data buffers used during
 *   USB Mass Storage operations. Buffer addresses are calculated
 *   dynamically based on endpoint configuration.
 *
 * ADDRESS SPACES:
 *   0x0000-0x00FF: Endpoint queue descriptors
 *   0x0100-0x01FF: Transfer work areas
 *   0x0400-0x04FF: DMA configuration tables
 *   0x0A00-0x0AFF: SCSI buffer management
 *
 * USAGE:
 *   1. dma_config_channel() - Configure DMA channel parameters
 *   2. dma_setup_transfer() - Set source, dest, length
 *   3. dma_start_transfer() - Begin DMA operation
 *   4. dma_wait_complete() or dma_poll_complete() - Wait for completion
 */
#ifndef _DMA_H_
#define _DMA_H_

#include "../types.h"

/* DMA control */
void dma_clear_status(void);                    /* 0x1bcb-0x1bd4 */
void dma_set_scsi_param3(void);                 /* 0x16f3-0x16fe */
void dma_set_scsi_param1(void);                 /* 0x1709-0x1712 */
uint8_t dma_reg_wait_bit(__xdata uint8_t *ptr); /* 0x1713-0x171c */
void dma_load_transfer_params(void);            /* 0x16ff-0x1708 */

/* DMA channel configuration */
void dma_config_channel(uint8_t channel, uint8_t r4_param);     /* 0x171d-0x172b */
void dma_setup_transfer(uint8_t r7_mode, uint8_t r5_param, uint8_t r3_param);  /* 0x4a57-0x4a93 */
void dma_init_channel_b8(void);                 /* 0x523c-0x525f */
void dma_init_channel_with_config(uint8_t config);              /* 0x5260-0x5283 */
void dma_config_channel_0x10(void);             /* 0x1795-0x179c */

/* DMA status */
uint8_t dma_check_scsi_status(uint8_t mode);    /* 0x17a9-0x17b4 */
void dma_clear_state_counters(void);            /* 0x17b5-0x17c0 */
void dma_init_ep_queue(void);                   /* 0x172c-0x173a */
uint8_t scsi_get_tag_count_status(void);        /* 0x173b-0x1742 */
uint8_t dma_check_state_counter(void);          /* 0x17c1-0x17cc */
uint8_t scsi_get_queue_status(void);            /* 0x17cd-0x17d7 */
uint8_t dma_shift_and_check(uint8_t val);       /* 0x4a94-0x4abe */

/* DMA transfer */
void dma_start_transfer(uint8_t aux0, uint8_t aux1, uint8_t count_hi, uint8_t count_lo);  /* 0x1787-0x178d */
void dma_set_error_flag(void);                  /* 0x1743-0x1751 */
void dma_setup_usb_rx(uint16_t len);            /* 0x1752-0x175c */
void dma_setup_usb_tx(uint16_t len);            /* 0x175d-0x176a */
void dma_wait_complete(void);                   /* 0x176b-0x1778 */

/* DMA address calculation */
uint8_t dma_get_config_offset_05a8(void);       /* 0x1779-0x1786 */
__xdata uint8_t *dma_calc_offset_0059(uint8_t offset);          /* 0x17f3-0x17fc */
__xdata uint8_t *dma_calc_addr_0478(uint8_t index);             /* 0x178e-0x1794 */
__xdata uint8_t *dma_calc_addr_0479(uint8_t index);             /* 0x179d-0x17a8 */
__xdata uint8_t *dma_calc_addr_00c2(void);      /* 0x180d-0x1819 */
__xdata uint8_t *dma_calc_ep_config_ptr(void);  /* 0x1602-0x1619 */
__xdata uint8_t *dma_calc_addr_046x(uint8_t offset);            /* 0x161a-0x1639 */
__xdata uint8_t *dma_calc_addr_0466(uint8_t offset);            /* 0x163a-0x1645 */
__xdata uint8_t *dma_calc_addr_0456(uint8_t offset);            /* 0x1646-0x1657 */
uint16_t dma_calc_addr_002c(uint8_t offset, uint8_t high);      /* 0x16ae-0x16b6 */

/* DMA SCSI operations */
uint8_t dma_shift_rrc2_mask(uint8_t val);       /* 0x16b7-0x16c2 */
void dma_store_to_0a7d(uint8_t val);            /* 0x16de-0x16e8 */
void dma_calc_scsi_index(void);                 /* 0x16e9-0x16f2 */
uint8_t dma_write_to_scsi_ce96(void);           /* 0x17d8-0x17e2 */
void dma_write_to_scsi_ce6e(void);              /* 0x17e3-0x17ec */
void dma_write_idata_to_dptr(__xdata uint8_t *ptr);             /* 0x17ed-0x17f2 */
void dma_read_0461(void);                       /* 0x17fd-0x1803 */
void dma_store_and_dispatch(uint8_t val);       /* 0x180d-0x181d */
void dma_clear_dword(__xdata uint8_t *ptr);     /* 0x173b-0x1742 */

/* Transfer functions */
uint16_t transfer_set_dptr_0464_offset(void);   /* 0x1659-0x1667 */
uint16_t transfer_calc_work43_offset(__xdata uint8_t *dptr);    /* 0x1668-0x1676 */
uint16_t transfer_calc_work53_offset(void);     /* 0x1677-0x1686 */
uint16_t transfer_get_ep_queue_addr(void);      /* 0x1687-0x1695 */
uint16_t transfer_calc_work55_offset(void);     /* 0x1696-0x16a1 */
void transfer_func_16b0(uint8_t param);         /* 0x16b0-0x16b6 */
void transfer_func_1633(uint16_t addr);         /* 0x1633-0x1639 */

/* DMA handlers */
void dma_interrupt_handler(void);               /* 0x2608-0x2809 */
void dma_transfer_handler(uint8_t param);       /* 0xce23-0xce76 */
void transfer_continuation_d996(void);          /* 0xd996-0xda8e */
void dma_poll_complete(void);                   /* 0xceab-0xcece */
void dma_buffer_store_result_e68f(void);        /* 0xe68f-0xe6fb (Bank 1) */
void dma_poll_link_ready(void);                 /* 0xe6fc-0xe725 (Bank 1) */

#endif /* _DMA_H_ */
