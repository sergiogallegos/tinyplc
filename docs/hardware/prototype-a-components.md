# A0 component-by-component register

Generated from the same component records as the KiCad draft and BOM.
Every row identifies an individual item, its function and an official source.
Candidate MPNs require a final package/availability review. Capacitors list a
required specification and an official manufacturer family reference while
their exact ordering codes remain open. A family page is not an exact-part
approval. See the [circuit explanation](prototype-a-electronics.md) for
calculations, limits and interactions between these items.

## Power

| Reference | Value / candidate part | What it does and why it is present | Official reference |
| --- | --- | --- | --- |
| J1 | 24V IN / GND; 1715721 | 24V IN / GND | [Manufacturer / design reference](https://www.phoenixcontact.com/en-us/products/pcb-terminal-block-mkds-15-2-508-1715721) |
| F1 | 500mA / 60V; MF-R050 | Resettable input fuse; slow overload protection | [Manufacturer / design reference](https://www.bourns.com/docs/product-datasheets/mf-r.pdf) |
| D1 | SS16; SS16 | Series reverse-polarity diode | [Manufacturer / design reference](https://www.diodes.com/datasheet/download/ds13003.pdf) |
| U2 | TSR 1-2433; TSR 1-2433 | 24 V to 3.3 V switching supply | [Manufacturer / design reference](https://www.tracopower.com/tsr1-datasheet) |
| C1 | 22uF / 50V; Panasonic EEU-FR1H220 | Input reservoir; polarity matters | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDF0000/ABA0000C1015.pdf) |
| C2 | 100nF / 50V; TDK C2012 family; exact MPN pending | High-frequency input bypass | [Manufacturer / design reference](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |
| C3 | 10uF / 10V; TDK C2012 family; exact MPN pending | 3V3 reservoir | [Manufacturer / design reference](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |

## MCU

| Reference | Value / candidate part | What it does and why it is present | Official reference |
| --- | --- | --- | --- |
| U1 | STM32F446RET6; STM32F446RET6 | Native ST processor; internal regulator ON | [Manufacturer / design reference](https://www.st.com/resource/en/datasheet/stm32f446re.pdf) |
| C4 | 100nF / 50V; TDK C2012 family; exact MPN pending | One local bypass per VDD pin | [Manufacturer / design reference](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |
| C5 | 100nF / 50V; TDK C2012 family; exact MPN pending | One local bypass per VDD pin | [Manufacturer / design reference](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |
| C6 | 100nF / 50V; TDK C2012 family; exact MPN pending | One local bypass per VDD pin | [Manufacturer / design reference](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |
| C7 | 100nF / 50V; TDK C2012 family; exact MPN pending | One local bypass per VDD pin | [Manufacturer / design reference](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |
| C8 | 4.7uF / 10V; TDK C2012 family; exact MPN pending | Single VCAP package requires 4.7uF low ESR; never a power output | [Manufacturer / design reference](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |
| C9 | 4.7uF / 10V; TDK C2012 family; exact MPN pending | MCU local bulk capacitance | [Manufacturer / design reference](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |
| R1 | 22; ERJ-6ENF22R0V | Analog supply RC filter; verify VDDA drop | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf) |
| C10 | 100nF / 50V; TDK C2012 family; exact MPN pending | VDDA high-frequency bypass | [Manufacturer / design reference](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |
| C11 | 1uF / 10V; TDK C2012 family; exact MPN pending | VDDA low-frequency bypass | [Manufacturer / design reference](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |
| R2 | 10k; ERJ-6ENF1002V | Reset pull-up | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf) |
| C12 | 100nF / 50V; TDK C2012 family; exact MPN pending | Reset noise filter | [Manufacturer / design reference](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |
| R3 | 10k; ERJ-6ENF1002V | Normal boot from user flash | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf) |
| R4 | 10k; ERJ-6ENF1002V | Bootloader mode selection pull-down | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf) |
| J2 | BOOT: 1=3V3 2=BOOT0 3=GND; Samtec TSW-103-07-G-S | Momentary shunt 1-2 only for ROM recovery | [Manufacturer / design reference](https://www.samtec.com/products/tsw) |
| J3 | SWD: 3V3 GND DIO CLK NRST SWO; Samtec TSW-106-07-G-S | Custom 2.54mm SWD header; pin 6 unconnected | [Manufacturer / design reference](https://www.samtec.com/products/tsw) |
| J4 | UART: GND TX RX; Samtec TSW-103-07-G-S | 3.3V UART recovery and existing engineering transport | [Manufacturer / design reference](https://www.samtec.com/products/tsw) |
| Y1 | 8MHz CL18pF; ABM3-8.000MHZ-B2-T | Independent HSE; Nucleo ST-LINK clock is absent | [Manufacturer / design reference](https://abracon.com/Resonators/abm3.pdf) |
| C13 | 27pF C0G / 50V; TDK C2012 family; exact MPN pending | Provisional crystal loading; tune using parasitics | [Manufacturer / design reference](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |
| C14 | 27pF C0G / 50V; TDK C2012 family; exact MPN pending | Provisional crystal loading; tune using parasitics | [Manufacturer / design reference](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |
| SW1 | RESET; Omron B3F-1000 | Reset button under service lid | [Manufacturer / design reference](https://components.omron.com/sites/default/files/datasheet_pdf/A070-E1.pdf) |
| SW2 | USER; Omron B3F-1000 | Active-low user input under service lid | [Manufacturer / design reference](https://components.omron.com/sites/default/files/datasheet_pdf/A070-E1.pdf) |
| R5 | 10k; ERJ-6ENF1002V | User button pull-up | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf) |
| D2 | GREEN; Kingbright KP-2012SGC | PA5 status LED; preserves existing output test concept | [Manufacturer / design reference](https://www.kingbrightusa.com/images/catalog/SPEC/KP-2012SGC.pdf) |
| R6 | 1k; ERJ-6ENF1001V | Approximately 1mA LED current | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf) |

## Input 1

| Reference | Value / candidate part | What it does and why it is present | Official reference |
| --- | --- | --- | --- |
| J5 | DI1 / GND; 1715721 | DI1 / GND | [Manufacturer / design reference](https://www.phoenixcontact.com/en-us/products/pcb-terminal-block-mkds-15-2-508-1715721) |
| R10 | 2.2k; ERJ-6ENF2201V | First half of input LED current limiter | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf) |
| R11 | 2.2k; ERJ-6ENF2201V | Second half of input limiter; shares dissipation | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf) |
| U4 | VO617A-3; VO617A-3 | 24V-present signal becomes active-low 3V3 GPIO | [Manufacturer / design reference](https://www.vishay.com/docs/83430/vo617a.pdf) |
| D11 | 1N4148W; 1N4148W | Antiparallel diode protects optocoupler LED against reverse input | [Manufacturer / design reference](https://assets.nexperia.com/documents/data-sheet/1N4148W_1N4448W.pdf) |
| R12 | 10k; ERJ-6ENF1002V | Collector pull-up sets GPIO HIGH when input is off | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf) |
| C21 | 10nF / 50V; TDK C2012 family; exact MPN pending | About 100us release filter with 10k pull-up | [Manufacturer / design reference](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |

## Input 2

| Reference | Value / candidate part | What it does and why it is present | Official reference |
| --- | --- | --- | --- |
| J6 | DI2 / GND; 1715721 | DI2 / GND | [Manufacturer / design reference](https://www.phoenixcontact.com/en-us/products/pcb-terminal-block-mkds-15-2-508-1715721) |
| R20 | 2.2k; ERJ-6ENF2201V | First half of input LED current limiter | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf) |
| R21 | 2.2k; ERJ-6ENF2201V | Second half of input limiter; shares dissipation | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf) |
| U5 | VO617A-3; VO617A-3 | 24V-present signal becomes active-low 3V3 GPIO | [Manufacturer / design reference](https://www.vishay.com/docs/83430/vo617a.pdf) |
| D12 | 1N4148W; 1N4148W | Antiparallel diode protects optocoupler LED against reverse input | [Manufacturer / design reference](https://assets.nexperia.com/documents/data-sheet/1N4148W_1N4448W.pdf) |
| R22 | 10k; ERJ-6ENF1002V | Collector pull-up sets GPIO HIGH when input is off | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf) |
| C22 | 10nF / 50V; TDK C2012 family; exact MPN pending | About 100us release filter with 10k pull-up | [Manufacturer / design reference](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |

## Input 3

| Reference | Value / candidate part | What it does and why it is present | Official reference |
| --- | --- | --- | --- |
| J7 | DI3 / GND; 1715721 | DI3 / GND | [Manufacturer / design reference](https://www.phoenixcontact.com/en-us/products/pcb-terminal-block-mkds-15-2-508-1715721) |
| R30 | 2.2k; ERJ-6ENF2201V | First half of input LED current limiter | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf) |
| R31 | 2.2k; ERJ-6ENF2201V | Second half of input limiter; shares dissipation | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf) |
| U6 | VO617A-3; VO617A-3 | 24V-present signal becomes active-low 3V3 GPIO | [Manufacturer / design reference](https://www.vishay.com/docs/83430/vo617a.pdf) |
| D13 | 1N4148W; 1N4148W | Antiparallel diode protects optocoupler LED against reverse input | [Manufacturer / design reference](https://assets.nexperia.com/documents/data-sheet/1N4148W_1N4448W.pdf) |
| R32 | 10k; ERJ-6ENF1002V | Collector pull-up sets GPIO HIGH when input is off | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf) |
| C23 | 10nF / 50V; TDK C2012 family; exact MPN pending | About 100us release filter with 10k pull-up | [Manufacturer / design reference](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |

## Input 4

| Reference | Value / candidate part | What it does and why it is present | Official reference |
| --- | --- | --- | --- |
| J8 | DI4 / GND; 1715721 | DI4 / GND | [Manufacturer / design reference](https://www.phoenixcontact.com/en-us/products/pcb-terminal-block-mkds-15-2-508-1715721) |
| R40 | 2.2k; ERJ-6ENF2201V | First half of input LED current limiter | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf) |
| R41 | 2.2k; ERJ-6ENF2201V | Second half of input limiter; shares dissipation | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf) |
| U7 | VO617A-3; VO617A-3 | 24V-present signal becomes active-low 3V3 GPIO | [Manufacturer / design reference](https://www.vishay.com/docs/83430/vo617a.pdf) |
| D14 | 1N4148W; 1N4148W | Antiparallel diode protects optocoupler LED against reverse input | [Manufacturer / design reference](https://assets.nexperia.com/documents/data-sheet/1N4148W_1N4448W.pdf) |
| R42 | 10k; ERJ-6ENF1002V | Collector pull-up sets GPIO HIGH when input is off | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf) |
| C24 | 10nF / 50V; TDK C2012 family; exact MPN pending | About 100us release filter with 10k pull-up | [Manufacturer / design reference](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |

## Outputs

| Reference | Value / candidate part | What it does and why it is present | Official reference |
| --- | --- | --- | --- |
| U3 | TPL7407LDR; TPL7407LDR | Four 3.3V-compatible low-side drivers; 3 unused channels | [Manufacturer / design reference](https://www.ti.com/lit/ds/symlink/tpl7407l.pdf) |
| C30 | 100nF / 50V; TDK C2012 family; exact MPN pending | Driver COM decoupling; clamp return must be short | [Manufacturer / design reference](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |
| J9 | +24 / Q1 sink; 1715721 | +24 / Q1 sink | [Manufacturer / design reference](https://www.phoenixcontact.com/en-us/products/pcb-terminal-block-mkds-15-2-508-1715721) |
| R51 | 100k; ERJ-6ENF1003V | External pull-down keeps driver input low during MCU reset | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf) |
| J10 | +24 / Q2 sink; 1715721 | +24 / Q2 sink | [Manufacturer / design reference](https://www.phoenixcontact.com/en-us/products/pcb-terminal-block-mkds-15-2-508-1715721) |
| R52 | 100k; ERJ-6ENF1003V | External pull-down keeps driver input low during MCU reset | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf) |
| J11 | +24 / Q3 sink; 1715721 | +24 / Q3 sink | [Manufacturer / design reference](https://www.phoenixcontact.com/en-us/products/pcb-terminal-block-mkds-15-2-508-1715721) |
| R53 | 100k; ERJ-6ENF1003V | External pull-down keeps driver input low during MCU reset | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf) |
| J12 | +24 / Q4 sink; 1715721 | +24 / Q4 sink | [Manufacturer / design reference](https://www.phoenixcontact.com/en-us/products/pcb-terminal-block-mkds-15-2-508-1715721) |
| R54 | 100k; ERJ-6ENF1003V | External pull-down keeps driver input low during MCU reset | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf) |

## USB

| Reference | Value / candidate part | What it does and why it is present | Official reference |
| --- | --- | --- | --- |
| J13 | USB-C DEVICE; USB4105-GF-A-120 | USB2 device only; VBUS never powers board | [Manufacturer / design reference](https://gct.co/files/drawings/usb4105.pdf) |
| R60 | 5.1k; ERJ-6ENF5101V | USB-C Rd advertises a sink/device on CC1 | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf) |
| R61 | 5.1k; ERJ-6ENF5101V | Independent Rd on CC2 supports either cable orientation | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf) |
| R62 | 22; ERJ-6ENF22R0V | Provisional USB D- source-series damping | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf) |
| R63 | 22; ERJ-6ENF22R0V | Provisional USB D+ source-series damping | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf) |
| R64 | 68k; ERJ-6ENF6802V | VBUS divider upper resistor; limits sense voltage | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf) |
| R65 | 100k; ERJ-6ENF1003V | VBUS divider lower resistor; no back-power rail connection | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf) |
| U8 | USBLC6-2SC6; USBLC6-2SC6 | Low-capacitance USB connector ESD protection | [Manufacturer / design reference](https://www.st.com/resource/en/datasheet/usblc6-2.pdf) |
| C31 | 100nF / 50V; TDK C2012 family; exact MPN pending | ESD supply-reference bypass | [Manufacturer / design reference](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |

## Expansion

| Reference | Value / candidate part | What it does and why it is present | Official reference |
| --- | --- | --- | --- |
| J14 | SPI: 3V3 GND SCK MISO MOSI CS; Samtec TSW-106-07-G-S | Cabled SPI2 expansion; NOT a WIZ850io direct-plug footprint | [Manufacturer / design reference](https://www.samtec.com/products/tsw) |
| J15 | ETH: GND RST INT; Samtec TSW-103-07-G-S | Ethernet reset and interrupt expansion | [Manufacturer / design reference](https://www.samtec.com/products/tsw) |
| R70 | 10k; ERJ-6ENF1002V | Deselected SPI device during boot | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf) |
| R71 | 10k; ERJ-6ENF1002V | Keep optional Ethernet module reset until firmware releases it | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf) |
| R72 | 10k; ERJ-6ENF1002V | Optional interrupt pull-up | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf) |
| J16 | OLED: 3V3 GND SCL SDA; Samtec TSW-104-07-G-S | Cabled 3.3V I2C display; custom pin order | [Manufacturer / design reference](https://www.samtec.com/products/tsw) |
| R73 | 4.7k; ERJ-6ENF4701V | I2C clock pull-up; review module parallel pull-ups | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf) |
| R74 | 4.7k; ERJ-6ENF4701V | I2C data pull-up; review module parallel pull-ups | [Manufacturer / design reference](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C307.pdf) |

## Test points

| Reference | Value / candidate part | What it does and why it is present | Official reference |
| --- | --- | --- | --- |
| TP1 | GND; Bare PCB test pad | Probe GND | [Manufacturer / design reference](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html) |
| TP2 | +3V3; Bare PCB test pad | Probe +3V3 | [Manufacturer / design reference](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html) |
| TP3 | V24; Bare PCB test pad | Probe V24 | [Manufacturer / design reference](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html) |
| TP4 | VCAP1; Bare PCB test pad | Probe VCAP1 | [Manufacturer / design reference](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html) |

## Mounting

| Reference | Value / candidate part | What it does and why it is present | Official reference |
| --- | --- | --- | --- |
| H1 | M3 NPTH; No purchased component | Board mounting; 3.2mm non-plated hole | [Manufacturer / design reference](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html) |
| H2 | M3 NPTH; No purchased component | Board mounting; 3.2mm non-plated hole | [Manufacturer / design reference](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html) |
| H3 | M3 NPTH; No purchased component | Board mounting; 3.2mm non-plated hole | [Manufacturer / design reference](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html) |
| H4 | M3 NPTH; No purchased component | Board mounting; 3.2mm non-plated hole | [Manufacturer / design reference](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html) |

