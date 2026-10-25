#!/usr/bin/env python3
"""Pixel-accurate OLED interface proposals, explicitly labelled DEMO."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
OUT=Path(__file__).resolve().parents[1]/'renders'
FONT='/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Regular.ttf'
def font(size):return ImageFont.truetype(FONT,size)
for state in ['run','fault','stop','off']:
    im=Image.new('RGB',(128,64),(2,3,4));d=ImageDraw.Draw(im)
    if state!='off':
        d.text((3,1),state.upper(),font=font(22 if state!='fault' else 19),fill='#f2f7f7')
        d.text((99,3),'DEMO',font=font(7),fill='#a8b6b9')
        d.line((4,30,124,30),fill='#54646a')
        d.text((4,35),'10 ms  /  A1' if state=='run' else 'OUTPUTS OFF',font=font(10),fill='#c9d8da')
        d.text((4,51),'I:0000 Q:0000' if state=='run' else 'CHECK STATUS',font=font(9),fill='#c9d8da')
    im.save(OUT/('status-'+state+'.png'))
