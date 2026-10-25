#!/usr/bin/env python3
"""Check printed page counts, text bounds, local links and saved FreeCAD solids."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[1]
files={
    'brochure': ('brochure/tinyplc-a1-brochure.pdf',8),
    'assembly': ('mechanical/drawings/assembly-guide.pdf',13),
    'drawings': ('mechanical/drawings/tinyplc-a1-drawings.pdf',4),
    'technical': ('mechanical/drawings/technical-assembly-reference.pdf',2),
    'pcb_layers': ('electronics/tinyplc-a1-layout.pdf',3),
}
report={'checked_utc':datetime.now(timezone.utc).isoformat()}
for name,(relative,count) in files.items():
    result=subprocess.run(['pdftotext','-bbox',str(ROOT/relative),'-'],
        check=True,text=True,capture_output=True)
    tree=ET.fromstring(result.stdout)
    pages=tree.findall('.//{*}page')
    assert len(pages)==count,(name,len(pages))
    for page in pages:
        w,h=float(page.attrib['width']),float(page.attrib['height'])
        for word in page.findall('.//{*}word'):
            box=[float(word.attrib[k]) for k in ['xMin','yMin','xMax','yMax']]
            assert 0<=box[0]<box[2]<=w and 0<=box[1]<box[3]<=h,(name,word.text,box)
    report[name]={'pages':count,'text_within_page':True}

docs=[REPO/'README.md',ROOT/'README.md',ROOT/'reports/verification.md',
      ROOT/'brochure/README.md',ROOT/'mechanical/drawings/README.md']
docs+=list((REPO/'docs/hardware').glob('prototype-a1-*.md'))
for path in docs:
    for target in re.findall(r'\]\(([^)]+)\)',path.read_text()):
        if not re.match(r'https?://|#',target):
            assert (path.parent/target.split('#')[0]).exists(),(path,target)
report['local_links']='all resolved'

sys.path.append('/usr/lib/freecad/lib')
import FreeCAD as App
doc=App.openDocument(str(ROOT/'mechanical/tinyplc-a1.FCStd'))
shapes=[obj for obj in doc.Objects if getattr(obj,'Visibility',False)
        and hasattr(obj,'Shape') and not obj.Shape.isNull()]
assert all(obj.Shape.isValid() for obj in shapes)
report['native_freecad']={'visible_valid_shapes':len(shapes),'objects':len(doc.Objects)}
App.closeDocument(doc.Name)
(ROOT/'reports/publication-checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
