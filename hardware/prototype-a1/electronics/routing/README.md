# A1 routing sources

`seed.kicad_pcb` retains the exact pre-routed critical connections and keepouts.
`tinyplc-a1.dsn` is the local router exchange input; `tinyplc-a1.ses` is its saved
output, with the corrected C1 package identifier. The import/fill script applies
reviewed finishing changes and enforces the board minimum trace width.

[Routing decisions](../../../../docs/hardware/prototype-a1-routing.md) explain
reproduction and limits. [Final native checks](../../reports/verification.md)
apply to the finished board, not to the intermediate autorouter output.
`manifest.json` records the external tool and file hashes. No router executable
or third-party runtime is redistributed here.
