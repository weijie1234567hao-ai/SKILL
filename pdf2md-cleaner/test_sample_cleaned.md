# STM32F103 Reference Manual

## `GPIO` registers

### `GPIO` port control register (GPIOx_CRH)

Page 45/200
| Bit | Name | Type | Reset | Description |
|---|---|---|---|---|
| 31:16 | RESERVED | - | - | Reserved |
| 15:12 | CNF[1:0] | R/W | 0x0 | Configuration bits |
| 11:8 | MODE[1:0] | R/W | 0x0 | Mode bits |
| 7:4 | CNF[1:0] | R/W | 0x0 | Configuration bits |
| 3:0 | MODE[1:0] | R/W | 0x0 | Mode bits |
Address: `0x40010804`

The GPIOx_CRH register is located at `0x40010804` and controls the high 8 bits of the port.

Page 46/200

Table 1. `GPIO` register map
| Register | Address | Reset Value |
|---|---|---|
| GPIOx_CRL | `0x40010800` | `0x44444444` |
| GPIOx_CRH | `0x40010804` | `0x44444444` |
| GPIOx_IDR | `0x40010808` | 0x0000xxxx |
| GPIOx_ODR | `0x4001080C` | `0x00000000` |
