# A1 component-by-component register

Each row comes from the A1 schematic/BOM source. The custom controller is
routed; exact purchasing choices and physical performance still require review.
Off-board SW3/DS1 are shown in the schematic but are not fake PCB footprints.
Read the [A1 decisions](prototype-a1-design.md) and the [common circuit explanation](prototype-a-electronics.md).

## Power

| Ref | Candidate / value | Function and reason | Official reference |
| --- | --- | --- | --- |
| J1 | 1715721; 24V DC: 1=+ 2=0V/GND (-) | 24V DC: 1=+ 2=0V/GND (-) | [Source](https://www.phoenixcontact.com/en-us/products/pcb-terminal-block-mkds-15-2-508-1715721) |
| F1 | MF-R050; 500mA / 60V | Resettable input fuse; slow overload protection | [Source](https://www.bourns.com/docs/product-datasheets/mf-r.pdf) |
| D1 | SS16; SS16 | Series reverse-polarity diode | [Source](https://www.diodes.com/datasheet/download/ds13003.pdf) |
| U2 | TSR 1-2433; TSR 1-2433 | 24 V to 3.3 V switching supply | [Source](https://www.tracopower.com/tsr1-datasheet) |
| C1 | Panasonic EEU-FR1H220; 22uF / 50V | Input reservoir; polarity matters | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDF0000/ABA0000C1259.pdf) |
| C2 | TDK C2012 family; exact MPN pending; 100nF / 50V | High-frequency input bypass | [Source](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |
| C3 | TDK C2012 family; exact MPN pending; 10uF / 10V | 3V3 reservoir | [Source](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |
| D3 | Kingbright KP-2012SGC; PWR GREEN | Hardware 3V3 presence indication, independent of firmware | [Source](https://www.kingbrightusa.com/images/catalog/SPEC/KP-2012SGC.pdf) |
| R75 | ERJ-6ENF1001V; 1k | PWR LED limit: about 1.1mA at Vf=2.2V | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |
| J17 | 1715721; SWITCH LOOP: 1=fused supply 2=switched return; neither pin is GND | SWITCH LOOP: 1=fused supply 2=switched return; neither pin is GND | [Source](https://www.phoenixcontact.com/en-us/products/pcb-terminal-block-mkds-15-2-508-1715721) |
| SW3 | C&K D102J12S215HQA; POWER ON/OFF (external) | Maintained SPST switch in fused positive supply; OFF is not galvanic isolation | [Source](https://www.ckswitches.com/media/1439/d.pdf) |

## MCU

| Ref | Candidate / value | Function and reason | Official reference |
| --- | --- | --- | --- |
| U1 | STM32F446RET6; STM32F446RET6 | Native ST processor; internal regulator ON | [Source](https://www.st.com/resource/en/datasheet/stm32f446re.pdf) |
| C4 | TDK C2012 family; exact MPN pending; 100nF / 50V | One local bypass per VDD pin | [Source](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |
| C5 | TDK C2012 family; exact MPN pending; 100nF / 50V | One local bypass per VDD pin | [Source](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |
| C6 | TDK C2012 family; exact MPN pending; 100nF / 50V | One local bypass per VDD pin | [Source](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |
| C7 | TDK C2012 family; exact MPN pending; 100nF / 50V | One local bypass per VDD pin | [Source](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |
| C8 | TDK C2012 family; exact MPN pending; 4.7uF / 10V | Single VCAP package requires 4.7uF low ESR; never a power output | [Source](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |
| C9 | TDK C2012 family; exact MPN pending; 4.7uF / 10V | MCU local bulk capacitance | [Source](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |
| R1 | ERJ-6ENF22R0V; 22 | Analog supply RC filter; verify VDDA drop | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |
| C10 | TDK C2012 family; exact MPN pending; 100nF / 50V | VDDA high-frequency bypass | [Source](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |
| C11 | TDK C2012 family; exact MPN pending; 1uF / 10V | VDDA low-frequency bypass | [Source](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |
| R2 | ERJ-6ENF1002V; 10k | Reset pull-up | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |
| C12 | TDK C2012 family; exact MPN pending; 100nF / 50V | Reset noise filter | [Source](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |
| R3 | ERJ-6ENF1002V; 10k | Normal boot from user flash | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |
| R4 | ERJ-6ENF1002V; 10k | Bootloader mode selection pull-down | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |
| J2 | Samtec TSW-103-07-G-S; BOOT: 1=3V3 2=BOOT0 3=GND | Momentary shunt 1-2 only for ROM recovery | [Source](https://www.samtec.com/products/tsw) |
| J3 | Samtec TSW-106-07-G-S; SWD: 3V3 GND DIO CLK NRST SWO | Custom 2.54mm SWD header; pin 6 unconnected | [Source](https://www.samtec.com/products/tsw) |
| J4 | Samtec TSW-103-07-G-S; UART: GND TX RX | 3.3V UART recovery and existing engineering transport | [Source](https://www.samtec.com/products/tsw) |
| Y1 | ABM3-8.000MHZ-B2-T; 8MHz CL18pF | Independent HSE; Nucleo ST-LINK clock is absent | [Source](https://abracon.com/Resonators/abm3.pdf) |
| C13 | TDK C2012 family; exact MPN pending; 27pF C0G / 50V | Provisional crystal loading; tune using parasitics | [Source](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |
| C14 | TDK C2012 family; exact MPN pending; 27pF C0G / 50V | Provisional crystal loading; tune using parasitics | [Source](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |
| SW1 | Omron B3F-1000; RESET | Reset button under service lid | [Source](https://components.omron.com/us-en/datasheet_pdf/A070-E1.pdf) |
| SW2 | Omron B3F-1000; USER | Active-low user input under service lid | [Source](https://components.omron.com/us-en/datasheet_pdf/A070-E1.pdf) |
| R5 | ERJ-6ENF1002V; 10k | User button pull-up | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |
| D2 | Kingbright KP-2012SGC; GREEN | PA5 status LED; preserves existing output test concept | [Source](https://www.kingbrightusa.com/images/catalog/SPEC/KP-2012SGC.pdf) |
| R6 | ERJ-6ENF1001V; 1k | RUN heartbeat LED current limit; approximately 1mA | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |
| C15 | TDK C2012 family; exact MPN pending; 100nF / 50V | Local VBAT bypass; VBAT is tied to the main 3V3 supply | [Source](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |

## Input 1

| Ref | Candidate / value | Function and reason | Official reference |
| --- | --- | --- | --- |
| J5 | 1715721; DI1 / GND | DI1 / GND | [Source](https://www.phoenixcontact.com/en-us/products/pcb-terminal-block-mkds-15-2-508-1715721) |
| R10 | ERJ-6ENF2201V; 2.2k | First half of input LED current limiter | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |
| R11 | ERJ-6ENF2201V; 2.2k | Second half of input limiter; shares dissipation | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |
| U4 | VO617A-3; VO617A-3 | 24V-present signal becomes active-low 3V3 GPIO | [Source](https://www.vishay.com/docs/83430/vo617a.pdf) |
| D11 | 1N4148W; 1N4148W | Antiparallel diode protects optocoupler LED against reverse input | [Source](https://assets.nexperia.com/documents/data-sheet/1N4148W_1N4448W.pdf) |
| R12 | ERJ-6ENF1002V; 10k | Collector pull-up sets GPIO HIGH when input is off | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |
| C21 | TDK C2012 family; exact MPN pending; 10nF / 50V | About 100us release filter with 10k pull-up | [Source](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |

## Input 2

| Ref | Candidate / value | Function and reason | Official reference |
| --- | --- | --- | --- |
| J6 | 1715721; DI2 / GND | DI2 / GND | [Source](https://www.phoenixcontact.com/en-us/products/pcb-terminal-block-mkds-15-2-508-1715721) |
| R20 | ERJ-6ENF2201V; 2.2k | First half of input LED current limiter | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |
| R21 | ERJ-6ENF2201V; 2.2k | Second half of input limiter; shares dissipation | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |
| U5 | VO617A-3; VO617A-3 | 24V-present signal becomes active-low 3V3 GPIO | [Source](https://www.vishay.com/docs/83430/vo617a.pdf) |
| D12 | 1N4148W; 1N4148W | Antiparallel diode protects optocoupler LED against reverse input | [Source](https://assets.nexperia.com/documents/data-sheet/1N4148W_1N4448W.pdf) |
| R22 | ERJ-6ENF1002V; 10k | Collector pull-up sets GPIO HIGH when input is off | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |
| C22 | TDK C2012 family; exact MPN pending; 10nF / 50V | About 100us release filter with 10k pull-up | [Source](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |

## Input 3

| Ref | Candidate / value | Function and reason | Official reference |
| --- | --- | --- | --- |
| J7 | 1715721; DI3 / GND | DI3 / GND | [Source](https://www.phoenixcontact.com/en-us/products/pcb-terminal-block-mkds-15-2-508-1715721) |
| R30 | ERJ-6ENF2201V; 2.2k | First half of input LED current limiter | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |
| R31 | ERJ-6ENF2201V; 2.2k | Second half of input limiter; shares dissipation | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |
| U6 | VO617A-3; VO617A-3 | 24V-present signal becomes active-low 3V3 GPIO | [Source](https://www.vishay.com/docs/83430/vo617a.pdf) |
| D13 | 1N4148W; 1N4148W | Antiparallel diode protects optocoupler LED against reverse input | [Source](https://assets.nexperia.com/documents/data-sheet/1N4148W_1N4448W.pdf) |
| R32 | ERJ-6ENF1002V; 10k | Collector pull-up sets GPIO HIGH when input is off | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |
| C23 | TDK C2012 family; exact MPN pending; 10nF / 50V | About 100us release filter with 10k pull-up | [Source](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |

## Input 4

| Ref | Candidate / value | Function and reason | Official reference |
| --- | --- | --- | --- |
| J8 | 1715721; DI4 / GND | DI4 / GND | [Source](https://www.phoenixcontact.com/en-us/products/pcb-terminal-block-mkds-15-2-508-1715721) |
| R40 | ERJ-6ENF2201V; 2.2k | First half of input LED current limiter | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |
| R41 | ERJ-6ENF2201V; 2.2k | Second half of input limiter; shares dissipation | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |
| U7 | VO617A-3; VO617A-3 | 24V-present signal becomes active-low 3V3 GPIO | [Source](https://www.vishay.com/docs/83430/vo617a.pdf) |
| D14 | 1N4148W; 1N4148W | Antiparallel diode protects optocoupler LED against reverse input | [Source](https://assets.nexperia.com/documents/data-sheet/1N4148W_1N4448W.pdf) |
| R42 | ERJ-6ENF1002V; 10k | Collector pull-up sets GPIO HIGH when input is off | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |
| C24 | TDK C2012 family; exact MPN pending; 10nF / 50V | About 100us release filter with 10k pull-up | [Source](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |

## Outputs

| Ref | Candidate / value | Function and reason | Official reference |
| --- | --- | --- | --- |
| U3 | TPL7407LDR; TPL7407LDR | Four 3.3V-compatible low-side drivers; 3 unused channels | [Source](https://www.ti.com/lit/ds/symlink/tpl7407l.pdf) |
| C30 | TDK C2012 family; exact MPN pending; 100nF / 50V | Driver COM decoupling; clamp return must be short | [Source](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |
| J9 | 1715721; +24 / Q1 sink | +24 / Q1 sink | [Source](https://www.phoenixcontact.com/en-us/products/pcb-terminal-block-mkds-15-2-508-1715721) |
| R51 | ERJ-6ENF1003V; 100k | External pull-down keeps driver input low during MCU reset | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |
| J10 | 1715721; +24 / Q2 sink | +24 / Q2 sink | [Source](https://www.phoenixcontact.com/en-us/products/pcb-terminal-block-mkds-15-2-508-1715721) |
| R52 | ERJ-6ENF1003V; 100k | External pull-down keeps driver input low during MCU reset | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |
| J11 | 1715721; +24 / Q3 sink | +24 / Q3 sink | [Source](https://www.phoenixcontact.com/en-us/products/pcb-terminal-block-mkds-15-2-508-1715721) |
| R53 | ERJ-6ENF1003V; 100k | External pull-down keeps driver input low during MCU reset | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |
| J12 | 1715721; +24 / Q4 sink | +24 / Q4 sink | [Source](https://www.phoenixcontact.com/en-us/products/pcb-terminal-block-mkds-15-2-508-1715721) |
| R54 | ERJ-6ENF1003V; 100k | External pull-down keeps driver input low during MCU reset | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |

## USB

| Ref | Candidate / value | Function and reason | Official reference |
| --- | --- | --- | --- |
| J13 | USB4105-GF-A-120; USB-C DEVICE | USB2 device only; VBUS never powers board | [Source](https://gct.co/files/drawings/usb4105.pdf) |
| R60 | ERJ-6ENF5101V; 5.1k | USB-C Rd advertises a sink/device on CC1 | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |
| R61 | ERJ-6ENF5101V; 5.1k | Independent Rd on CC2 supports either cable orientation | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |
| R62 | ERJ-6ENF22R0V; 22 | Provisional USB D- source-series damping | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |
| R63 | ERJ-6ENF22R0V; 22 | Provisional USB D+ source-series damping | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |
| R64 | ERJ-6ENF6802V; 68k | VBUS divider upper resistor; limits sense voltage | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |
| R65 | ERJ-6ENF1003V; 100k | VBUS divider lower resistor; no back-power rail connection | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |
| U8 | USBLC6-2SC6; USBLC6-2SC6 | Low-capacitance USB connector ESD protection | [Source](https://www.st.com/resource/en/datasheet/usblc6-2.pdf) |
| C31 | TDK C2012 family; exact MPN pending; 100nF / 50V | ESD supply-reference bypass | [Source](https://product.tdk.com/en/products/capacitor/ceramic/mlcc/characteristic/) |

## Expansion

| Ref | Candidate / value | Function and reason | Official reference |
| --- | --- | --- | --- |
| J14 | Samtec TSW-106-07-G-S; SPI: 3V3 GND SCK MISO MOSI CS | Cabled SPI2 expansion; NOT a WIZ850io direct-plug footprint | [Source](https://www.samtec.com/products/tsw) |
| J15 | Samtec TSW-103-07-G-S; ETH: GND RST INT | Ethernet reset and interrupt expansion | [Source](https://www.samtec.com/products/tsw) |
| R70 | ERJ-6ENF1002V; 10k | Deselected SPI device during boot | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |
| R71 | ERJ-6ENF1002V; 10k | Keep optional Ethernet module reset until firmware releases it | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |
| R72 | ERJ-6ENF1002V; 10k | Optional interrupt pull-up | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |
| J16 | Samtec TSW-104-07-G-S; OLED: 3V3 GND SCL SDA | Cabled 3.3V I2C display; custom pin order | [Source](https://www.samtec.com/products/tsw) |
| R73 | ERJ-6ENF4701V; 4.7k | I2C clock pull-up; review module parallel pull-ups | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |
| R74 | ERJ-6ENF4701V; 4.7k | I2C data pull-up; review module parallel pull-ups | [Source](https://industrial.panasonic.com/cdbs/www-data/pdf/RDA0000/AOA0000C304.pdf) |
| DS1 | Adafruit 326; OLED 326 / STEMMA QT (external) | Adafruit 326 I2C status display, QT revision; 4-wire cable to J16 | [Source](https://www.adafruit.com/product/326) |

## Test points

| Ref | Candidate / value | Function and reason | Official reference |
| --- | --- | --- | --- |
| TP1 | Bare PCB test pad; GND | Probe GND | [Source](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html) |
| TP2 | Bare PCB test pad; +3V3 | Probe +3V3 | [Source](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html) |
| TP3 | Bare PCB test pad; V24 | Probe V24 | [Source](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html) |
| TP4 | Bare PCB test pad; VCAP1 | Probe VCAP1 | [Source](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html) |

## Mounting

| Ref | Candidate / value | Function and reason | Official reference |
| --- | --- | --- | --- |
| H1 | No purchased component; M3 NPTH | Board mounting; 3.2mm non-plated hole | [Source](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html) |
| H2 | No purchased component; M3 NPTH | Board mounting; 3.2mm non-plated hole | [Source](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html) |
| H3 | No purchased component; M3 NPTH | Board mounting; 3.2mm non-plated hole | [Source](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html) |
| H4 | No purchased component; M3 NPTH | Board mounting; 3.2mm non-plated hole | [Source](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html) |

## Mechanical and harness parts

See [mechanical-and-harness.csv](../../hardware/prototype-a1/bom/mechanical-and-harness.csv) for quantities, reasons and source references.
Generic supplier/family references do not resolve an exact purchasing SKU.
