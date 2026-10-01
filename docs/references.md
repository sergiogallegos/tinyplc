# References and acknowledgments

Reference register established 2026-09-30. tinyplc is an independent educational
project: a small ST subset, a project-owned Rust frontend and C supervisor,
and explicit native compilation, loading and monitoring contracts. We thank
the authors and contributors below for making their work available to study.
Acknowledgment does not imply affiliation or endorsement.

## Related work and educational inspiration

| ID | Work and authors/community | What it contributes to our study |
| --- | --- | --- |
| RUSTY | [RuSTy — PLC-lang contributors](https://github.com/PLC-lang/rusty); [technical overview](https://plc-lang.github.io/rusty/technical/overview.html) | ST frontend stages, semantic validation, LLVM generation and compiler/runtime metadata boundaries |
| OPENPLC | [OpenPLC Runtime — Autonomy Logic and contributors](https://github.com/Autonomy-Logic/openplc-runtime) | Runtime lifecycle, process images, generated-program interfaces and engineering access; its hosted design differs from our MCU target |
| MATIEC | [matiec — Mario de Sousa and contributors; sm1820 repository](https://github.com/sm1820/matiec) | IEC semantic passes and generated-C variable access support; useful historical language implementation reference |
| MICROGRAD | [micrograd — Andrej Karpathy and contributors](https://github.com/karpathy/micrograd) | Educational inspiration: expose a core mechanism in a small, readable implementation |
| NANOGPT | [nanoGPT — Andrej Karpathy and contributors](https://github.com/karpathy/nanoGPT) | Educational inspiration: make an end-to-end system understandable through executable code |
| CODESYS | [CODESYS Runtime brochure](https://assets.ctfassets.net/qp8rp917jhxs/3Dn3l9I8dKZDdAlX6twLRw/9d0355f429f162805b155f0670ff39e9/CODESYS-Runtime-en.pdf) | Commercial context for native PLC compilation; not a source for proprietary implementation details |

The [education study](education.md) links the specific upstream files examined
and explains our conclusions and differences. These are design references,
not incorporated source dependencies. No implementation code from the five
open-source projects above has been incorporated in this work. Their authors
retain credit for their work; tinyplc's choices, subset, implementation and
tests are project-specific. Shared compiler/PLC concepts are established ideas,
not claims of research novelty.

## Languages, standards and toolchain

| ID | Official documentation/repository | Role in tinyplc |
| --- | --- | --- |
| RUST | [Rust Book](https://doc.rust-lang.org/book/), [Reference](https://doc.rust-lang.org/reference/), [standard library](https://doc.rust-lang.org/std/), [Cargo](https://doc.rust-lang.org/cargo/), [source](https://github.com/rust-lang/rust) | Implemented frontend and CLI; no third-party Rust crates |
| C11 | [WG14](https://www.open-std.org/jtc1/sc22/wg14/), [N1570 C11 committee draft](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf) | C runtime/harness language, fixed-width values and ownership primitives; N1570 is a public draft, not the purchased final ISO publication |
| IEC | [IEC 61131-3 public scope](https://webstore.iec.ch/en/publication/68533) | Language context; our [explicit subset](language.md) does not claim full conformance |
| LLVM | [LLVM documentation](https://llvm.org/docs/), [LangRef](https://llvm.org/docs/LangRef.html), [source](https://github.com/llvm/llvm-project) | External PC-side IR verification, optimization and native code generation |
| CLANG | [Clang documentation](https://clang.llvm.org/docs/), [cross compilation](https://clang.llvm.org/docs/CrossCompilation.html) | Host AOT and Cortex-M object generation; target ABI still needs validation |
| ARM-ABI | [Arm ABI specifications](https://github.com/ARM-software/abi-aa) | Target calling convention, object and relocation contract reference for R2 |
| FREERTOS | [FreeRTOS documentation](https://www.freertos.org/Documentation/00-Overview), [kernel source](https://github.com/FreeRTOS/FreeRTOS-Kernel) | Planned scheduler dependency; not integrated in R1; select and pin an MPU-aware port in R2 |

## Board and processor references

| ID | STMicroelectronics reference | Used for |
| --- | --- | --- |
| BOARD | [NUCLEO-F446RE product page](https://www.st.com/en/evaluation-tools/nucleo-f446re.html), [UM1724 board manual](https://www.st.com/resource/en/user_manual/dm00105823.pdf) | Board resources, ST-LINK, LED/button and serial connections |
| MCU | [STM32F446 datasheet, DS10693](https://www.st.com/resource/en/datasheet/stm32f446re.pdf) | Memory capacity, processor features and memory map |
| CORTEX-M4 | [PM0214 programming manual](https://www.st.com/resource/en/programming_manual/dm00046982-stm32-cortexm4-mcus-and-mpus-programming-manual-stmicroelectronics.pdf) | Privilege, exceptions, MPU and memory-system behavior |
| SCHEMATIC | [MB1136 C04 schematic](https://www.st.com.cn/resource/en/schematic_pack/mb1136-default-c04_schematic.pdf) | Physical connectivity; verify against the actual board revision |

## Supporting development tools

| Official reference | Role |
| --- | --- |
| [Python documentation](https://docs.python.org/3/) | Standard-library test runner and historical semantic oracle; not the primary ST compiler |
| [CMake documentation](https://cmake.org/documentation/) | Historical C builds and board bring-up builds |
| [GNU Make manual](https://www.gnu.org/software/make/manual/) | Top-level build and test commands |
| [Arm GNU Toolchain](https://developer.arm.com/Tools%20and%20Software/GNU%20Toolchain) | Existing standalone blink target |
| [OpenOCD documentation](https://openocd.org/documentation/) | Existing explicit board-flash command |
| [Mermaid documentation](https://mermaid.js.org/intro/) | Editable architecture diagrams rendered by compatible Markdown viewers |

[Setup](setup.md) and [R1 evidence](R1-report.md) record observed tool versions.
Links to upstream default branches and live manuals are reading references,
not reproducible version pins. Future integration must record exact revisions,
manual revisions and applicable licenses with the corresponding stage report.

## How to credit future work

- Cite a source beside the design claim it supports; add it to this register
  and describe what we learned, changed, or deliberately left out.
- Add a short source comment where a design reference helps a reader understand
  an implementation decision. Do not imply a reference supplied code it did not.
- If code is ever copied, adapted or vendored, record the upstream path and
  revision, identify modifications, and retain required copyright/license
  notices. A bibliography is not a substitute for those notices.
- Keep project-original code under the root [MIT license](../LICENSE).
  External tools and any future vendored components retain their own licenses.
- Keep implementation status and evidence separate from plans. A cited project
  does not establish our own correctness, timing, isolation or certification.
