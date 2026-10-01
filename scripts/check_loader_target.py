"""Cross-build the portable loader and enforce its proposed RAM budget; no flash."""
import argparse
import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gcc-prefix',default='arm-none-eabi-')
    args=parser.parse_args()
    out=ROOT/'build/loader';out.mkdir(parents=True,exist_ok=True)
    objects=[]
    for name,source in [('package','runtime/src/package.c'),('loader','runtime/src/loader.c'),
                        ('budget','tests/loader/budget.c'),('memory','port/nucleo_f446re/native/memory.c')]:
        obj=out/(name+'.o');objects.append(str(obj))
        subprocess.run([args.gcc_prefix+'gcc','-mcpu=cortex-m4','-mthumb','-mfloat-abi=soft','-std=c11','-O2',
            '-Wall','-Wextra','-Werror','-ffreestanding','-fno-builtin','-fstack-usage','-Icontract','-Iruntime/include',
            '-c',source,'-o',str(obj)],cwd=ROOT,check=True)
    combined=out/'combined.o'
    subprocess.run([args.gcc_prefix+'ld','-r',*objects,'-o',str(combined)],check=True)
    undefined=subprocess.check_output([args.gcc_prefix+'nm','-u',str(combined)],text=True)
    assert not undefined.strip(),undefined
    sizes=subprocess.check_output([args.gcc_prefix+'size',str(combined)],text=True).splitlines()[1].split()
    text,data,bss=map(int,sizes[:3])
    assert data+bss<=24*1024
    stack=[]
    for name in ('package','loader','memory'):
        for line in (out/(name+'.su')).read_text().splitlines():
            location,size,kind=line.split('\t')
            assert kind=='static',line
            stack.append(dict(function=location.rsplit(':',1)[-1],bytes=int(size)))
    report=dict(compiler=subprocess.check_output([args.gcc_prefix+'gcc','-dumpfullversion'],text=True).strip(),
                text_bytes=text,data_bytes=data,bss_bytes=bss,ram_budget_bytes=24*1024,
                undefined_symbols=[],static_frames=stack,
                limitation='Relocatable ARM link only; no board MPU/transport integration or runtime stack measurement.')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
