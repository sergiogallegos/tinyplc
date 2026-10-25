"""Shared SVG/PDF layout helpers; no online rendering service required."""
import base64
import html
from pathlib import Path
import subprocess
import textwrap

ROOT=Path(__file__).resolve().parents[1]
INK='#202c34';MUTED='#586872';ACCENT='#236d76';PALE='#edf2f2'

class Page:
    def __init__(self,title,kicker='tinyPLC / A1',number=1,background='white'):
        self.number=number
        self.s=['<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="297mm" height="210mm" viewBox="0 0 297 210">',
                '<defs><marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6Z" fill="#236d76"/></marker></defs>',
                '<style>text{font-family:Inter,Arial,sans-serif;fill:#202c34}</style>',
                f'<rect width="297" height="210" fill="{background}"/>']
        self.text(14,13,kicker,2.9,ACCENT,True)
        self.text(14,28,title,6.5,INK,True)
        self.line(14,198,283,198,'#d8e1e3',0.3)
        self.text(14,204,'A1 prototype • CAD renders • not a fabrication release • 2026-10-24',2.3,MUTED)
        self.text(283,204,f'{number:02}',2.8,MUTED,anchor='end')

    def text(self,x,y,body,size=3.3,color=INK,bold=False,anchor='start',rotation=0):
        self.s.append(f'<text x="{x}" y="{y}" font-size="{size}" style="fill:{color}" font-weight="{700 if bold else 400}" text-anchor="{anchor}" transform="rotate({rotation} {x} {y})">{html.escape(str(body))}</text>')

    def para(self,x,y,body,width=80,size=3.3,color=INK,bold=False):
        lines=textwrap.wrap(body,max(12,int(width/(size*0.52))))
        for i,line in enumerate(lines):self.text(x,y+i*size*1.5,line,size,color,bold)
        return y+len(lines)*size*1.5

    def rect(self,x,y,w,h,color=PALE,r=0,stroke=None):
        self.s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{color}"'+(f' stroke="{stroke}" stroke-width=".3"' if stroke else '')+'/>')

    def circle(self,x,y,r,color='none',stroke=INK):
        self.s.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}" stroke="{stroke}" stroke-width=".3"/>')

    def line(self,x1,y1,x2,y2,color=ACCENT,width=.65,arrow=False,dashed=False):
        self.s.append(f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round"'+(' marker-end="url(#arrow)"' if arrow else '')+(' stroke-dasharray="1.5 1"' if dashed else '')+'/>')

    def image(self,name,x,y,w,h):
        path=Path(name)
        if not path.exists():path=ROOT/'renders'/(name+'.png')
        data=base64.b64encode(path.read_bytes()).decode()
        self.s.append(f'<image x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="xMidYMid meet" xlink:href="data:image/png;base64,{data}"/>')

    def block(self,x,y,w,h,title,body,color=PALE):
        self.rect(x,y,w,h,color,2)
        self.text(x+4,y+9,title,3.5,INK,True)
        self.para(x+4,y+17,body,w-8,3)

    def hdim(self,x1,x2,y,label):
        self.line(x1,y,x2,y,MUTED,.3)
        for x in [x1,x2]:self.line(x,y-2,x,y+2,MUTED,.3)
        self.text((x1+x2)/2,y-2,label,2.7,MUTED,anchor='middle')

    def vdim(self,x,y1,y2,label):
        self.line(x,y1,x,y2,MUTED,.3)
        for y in [y1,y2]:self.line(x-2,y,x+2,y,MUTED,.3)
        self.text(x-2,(y1+y2)/2,label,2.7,MUTED,rotation=-90,anchor='middle')

    def save(self,path):
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        path.with_suffix('.svg').write_text('\n'.join(self.s+['</svg>'])+'\n')
        subprocess.run(['rsvg-convert','--format=pdf','--output',str(path.with_suffix('.pdf')),str(path.with_suffix('.svg'))],check=True)
        return path.with_suffix('.pdf')

def bundle(paths,out):
    subprocess.run(['pdfunite',*[str(p) for p in paths],str(out)],check=True)
