#!/usr/bin/env python3
"""Seed critical routes, exchange local Specctra routing, and fill ground copper.

Run generate_electronics.py first, then `route_pcb.py seed`. The saved SES is
the reviewed routing source; `route_pcb.py import` restores it without rerouting.
"""
import argparse
import json
from pathlib import Path
import pcbnew as p

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "electronics"
R = E / "routing"
R.mkdir(exist_ok=True)
PATH = E / "tinyplc-a1.kicad_pcb"
b = p.LoadBoard(str(PATH))
fps = {f.GetReference(): f for f in b.GetFootprints()}
nets = b.GetNetsByName()

def xy(x, y):
    return p.VECTOR2I(p.FromMM(x + 100), p.FromMM(y + 100))

def pad(ref, num):
    return next(a for a in fps[ref].Pads() if a.GetNumber() == str(num))

def at(ref, num):
    q = pad(ref, num).GetPosition()
    return (p.ToMM(q.x)-100, p.ToMM(q.y)-100)

def track(net, points, width=.25, layer=p.F_Cu):
    for start, end in zip(points, points[1:]):
        t = p.PCB_TRACK(b)
        t.SetStart(xy(*start)); t.SetEnd(xy(*end))
        t.SetWidth(p.FromMM(width)); t.SetLayer(layer)
        t.SetNet(nets['/'+net]); t.SetLocked(True)
        b.Add(t)

def via(net, point):
    v = p.PCB_VIA(b)
    v.SetPosition(xy(*point)); v.SetWidth(p.FromMM(.6))
    v.SetDrill(p.FromMM(.3)); v.SetViaType(p.VIATYPE_THROUGH)
    v.SetLayerPair(p.F_Cu,p.B_Cu); v.SetNet(nets['/'+net])
    v.SetLocked(True); b.Add(v)

def seed():
    assert len(b.GetTracks()) == 0, 'Seed requires freshly generated placement'
    # Short, via-free 8 MHz oscillator branches and capacitor connections.
    track('OSC_IN',[at('U1',5),(53,41.25),(51.4,39.65),at('Y1',1),at('C13',1)])
    track('OSC_OUT',[at('U1',6),(53,41.75),(51.4,43.35),at('Y1',2),at('C14',1)])
    for pin, cap, mids in [(64,'C4',[]),(19,'C5',[]),
                           (32,'C6',[(63.75,49.2)]),
                           (48,'C7',[(67,39.25),(68,38.25)])]:
        track('+3V3',[at('U1',pin),*mids,at(cap,1)])
    track('+3V3',[at('U1',1),(53.4,39.25),(52.95,38.8),at('C15',1)])
    track('VCAP1',[at('U1',30),at('C8',1)])
    track('VDDA',[at('U1',13),(53,45.25),(52.45,45.8),at('C10',1)])
    # VSS escapes inward, keeping the outward GPIO fanout clear.
    for pin, point in [(12,(55.8,44.75)),(18,(56.75,47.2)),
                       (31,(63.25,47.2)),(47,(64.2,39.75)),(63,(56.75,38.8))]:
        track('GND',[at('U1',pin),point]); via('GND',point)
    for ref, point in [('C15',(51.05,35.8)),('C4',(56.25,32.3)),('C5',(57.25,54)),
                       ('C6',(68.3,50.5)),('C7',(68,32.8)),
                       ('C8',(62.75,54.2)),('C13',(43.8,39.65)),
                       ('C14',(43.8,43.35)),('C10',(48.8,45.8))]:
        track('GND',[at(ref,2),point]); via('GND',point)
    # USB FS: source damping by the MCU; adjacent runs to the ESD device.
    track('USB_DM',[at('U1',44),at('R62',2)])
    track('USB_DP',[at('U1',45),(67.5,40.75),(70,38.25),at('R63',2)])
    track('USB_DP_CONN',[at('R63',1),(74.5,38.25),(76.5,40.25),
                         (105,40.25),(106.3,41.55),at('U8',4)])
    track('USB_DM_CONN',[at('R62',1),(75,41.25),(75.5,40.75),
                         (104.5,40.75),(107.2,43.45),at('U8',6)])
    # Bridge the two sides of each flow-through ESD channel on copper.
    track('USB_DP_CONN',[at('U8',4),at('U8',3)])
    track('USB_DM_CONN',[at('U8',6),at('U8',1)])
    # Ground pour will provide the low-inductance return; short local vias.
    track('GND',[at('U8',2),(110.6,42.5)]); via('GND',(110.6,42.5))
    # Reserve continuous bottom-layer return copper below USB and crystal.
    for points in [[(76,39.5),(105,39.5),(105,41.5),(76,41.5)],
                   [(44.5,38.5),(53,38.5),(53,44),(44.5,44)]]:
        z=p.ZONE(b); z.SetLayer(p.B_Cu); z.SetIsRuleArea(True)
        z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True)
        z.SetDoNotAllowZoneFills(False); z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
        outline=z.Outline(); outline.NewOutline()
        for point in points:
            q=xy(*point); outline.Append(q.x,q.y)
        b.Add(z)
    b.BuildConnectivity()
    p.SaveBoard(str(PATH),b)
    p.SaveBoard(str(R/'seed.kicad_pcb'),b)
    assert p.ExportSpecctraDSN(b,str(R/'tinyplc-a1.dsn'))
    dsn=R/'tinyplc-a1.dsn'; text=dsn.read_text()
    start=text.index('    (class '); end=text.index('  (wiring',start)
    section=text[start:end]
    power=['/VIN24','/VIN_FUSED','/VIN_SWITCHED','/V24']
    for name in power:
        import re
        section=re.sub(re.escape(name)+r'(?=\s)', '', section)
    pos=section.rfind('  )')
    section=section[:pos]+'    (class Power24 '+ ' '.join(power)+        ' (circuit (use_via "Via[0-1]_600:300_um")) (rule (width 800) (clearance 300)))\n'+section[pos:]
    dsn.write_text(text[:start]+section+text[end:])
    project=E/'tinyplc-a1.kicad_pro'; settings=json.loads(project.read_text())
    settings['net_settings']['classes'].append({'name':'Power24','clearance':.3,
        'track_width':.8,'via_diameter':.6,'via_drill':.3})
    settings['net_settings']['netclass_patterns']=[{'netclass':'Power24','pattern':n} for n in power]
    project.write_text(json.dumps(settings,indent=2)+'\n')

def finish():
    global b,fps,nets
    # Always import into the exact seed board: repeated runs are idempotent.
    b=p.LoadBoard(str(R/'seed.kicad_pcb'))
    fps={f.GetReference():f for f in b.GetFootprints()}
    nets=b.GetNetsByName()
    seeds=[]
    for item in b.GetTracks():
        if not isinstance(item,p.PCB_VIA):
            seeds.append((item.GetNetname()[1:],
                [(p.ToMM(q.x)-100,p.ToMM(q.y)-100) for q in [item.GetStart(),item.GetEnd()]],
                p.ToMM(item.GetWidth()),item.GetLayer()))
    assert p.ImportSpecctraSES(b,str(R/'tinyplc-a1.ses'))
    # Keep fixed seed copper exactly once across KiCad importer versions.
    existing=set()
    for item in b.GetTracks():
        if not isinstance(item,p.PCB_VIA):
            existing.add((item.GetNetname(),item.GetLayer(),tuple(sorted(
                [(item.GetStart().x,item.GetStart().y),(item.GetEnd().x,item.GetEnd().y)]))))
    for net,points,width,layer in seeds:
        q=[xy(*point) for point in points]
        key=('/'+net,layer,tuple(sorted([(q[0].x,q[0].y),(q[1].x,q[1].y)])))
        if key not in existing: track(net,points,width,layer)
    # Enforce the board's manufacturable minimum after router pin neck-down.
    for item in b.GetTracks():
        if not isinstance(item,p.PCB_VIA) and item.GetWidth()<p.FromMM(.2):
            item.SetWidth(p.FromMM(.2))
    # Complete the ESD supply reference with an under-body via.
    track('VBUS_USB',[at('U8',5),(108.7,42.5)])
    via('VBUS_USB',(108.7,42.5))
    track('VBUS_USB',[(108.7,42.5),(108.7,43.9659),(108.1612,44.5047)],layer=p.B_Cu)
    # Remove unused fanout vias: all attached tracks remain on the front.
    unused={(131702300,159732300),(155627000,139750000),(157568100,138733900)}
    for item in list(b.GetTracks()):
        if isinstance(item,p.PCB_VIA) and (item.GetPosition().x,item.GetPosition().y) in unused:
            b.Remove(item)
    # Ground pour replaces this diagonal return, freeing the ESD supply via.
    for item in list(b.GetTracks()):
        if not isinstance(item,p.PCB_VIA) and item.GetNetname()=='/GND' and item.GetLayer()==p.B_Cu:
            endpoints=[(q.x,q.y) for q in [item.GetStart(),item.GetEnd()]]
            if (209450000,142500000) in endpoints and item.GetLength()>p.FromMM(5):
                b.Remove(item)
    # Restore standard KiCad package models for native 3D inspection.
    parts=json.loads((ROOT/'bom/components.json').read_text())
    for part in parts:
        lib,name=part['original_footprint'].split(':')
        library=Path('/usr/share/kicad/footprints')/(lib+'.pretty')
        if not library.exists(): continue
        original=p.FootprintLoad(str(library),name)
        if original:
            fp=fps[part['ref']]; fp.Models().clear()
            for model in original.Models(): fp.Models().push_back(model)
    b.BuildConnectivity()
    p.SaveBoard(str(PATH),b)

def fill():
    # Solid SMD ground connections avoid fragile thermals at fine-pitch pads.
    # Through-hole grounds retain thermal relief for hand soldering.
    for f in b.GetFootprints():
        for a in f.Pads():
            if a.GetAttribute()==p.PAD_ATTRIB_SMD and a.GetNetname()=='/GND':
                a.SetLocalZoneConnection(p.ZONE_CONNECTION_FULL)
    # Filled GND on both layers, disconnected islands removed by KiCad.
    existing={z.GetLayer() for z in b.Zones() if not z.GetIsRuleArea()}
    for layer in [p.F_Cu,p.B_Cu]:
        if layer in existing: continue
        z=p.ZONE(b); z.SetLayer(layer); z.SetNet(nets['/GND'])
        z.SetLocalClearance(p.FromMM(.25)); z.SetMinThickness(p.FromMM(.2))
        z.SetPadConnection(p.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(p.FromMM(.25)); z.SetThermalReliefSpokeWidth(p.FromMM(.3))
        z.SetIslandRemovalMode(p.ISLAND_REMOVAL_MODE_ALWAYS)
        outline=z.Outline(); outline.NewOutline()
        for point in [(0.5,0.5),(119.5,.5),(119.5,89.5),(.5,89.5)]:
            q=xy(*point); outline.Append(q.x,q.y)
        b.Add(z)
    b.BuildConnectivity()
    p.ZONE_FILLER(b).Fill(b.Zones())
    p.SaveBoard(str(PATH),b)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['seed','import','fill'])
    args=parser.parse_args()
    {'seed':seed,'import':finish,'fill':fill}[args.stage]()
    print(args.stage, 'complete:',len(b.GetTracks()),'tracks/vias')
