#!/usr/bin/env python3
"""Export native KiCad inspection drawings and two 3D PCB views."""
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
board=ROOT/'electronics/tinyplc-a1.kicad_pcb'
subprocess.run(['kicad-cli','pcb','export','pdf','--layers','F.Cu,B.Cu,F.Fab',
    '--common-layers','Edge.Cuts','--mode-multipage','--sketch-pads-on-fab-layers',
    '--exclude-value','--output',str(ROOT/'electronics/tinyplc-a1-layout.pdf'),str(board)],check=True)
for side,rotation in [('top','35,0,25'),('bottom','25,0,25')]:
    subprocess.run(['kicad-cli','pcb','render','--width','1800','--height','1300',
        '--quality','high','--background','opaque','--side',side,'--rotate',rotation,
        '--output',str(ROOT/'renders'/f'pcb-routed-{side}.png'),str(board)],check=True)
