"""Explicit destructive LAB-board test: flash, download/activate fault fixtures,
then restore the normal engineering firmware in finally. Never run implicitly.
Stdlib orchestration only; product transport is the Rust plctool binary.
"""
import argparse
import binascii
import hashlib
import json
import os
from pathlib import Path
import select
import struct
import subprocess
import termios
import time
import zlib
ROOT=Path(__file__).resolve().parents[1]

class Serial:
    def __init__(self,path):
        self.fd=os.open(path,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK)
        self.saved=termios.tcgetattr(self.fd)
        raw=termios.tcgetattr(self.fd);raw[0]=0;raw[1]=0;raw[2]=termios.CS8|termios.CREAD|termios.CLOCAL;raw[3]=0
        raw[4]=termios.B115200;raw[5]=termios.B115200;raw[6][termios.VMIN]=0;raw[6][termios.VTIME]=0
        termios.tcsetattr(self.fd,termios.TCSANOW,raw);termios.tcflush(self.fd,termios.TCIOFLUSH)
    def close(self):termios.tcsetattr(self.fd,termios.TCSANOW,self.saved);os.close(self.fd)
    @staticmethod
    def frame(cmd,p=b''):
        body=struct.pack('<HB',len(p)+1,cmd)+p
        return b'\xa5'+body+struct.pack('<H',binascii.crc_hqx(body,0xffff))
    def send(self,b):
        while b:
            _,ready,_=select.select([],[self.fd],[],2);assert ready,'serial write timeout'
            n=os.write(self.fd,b);b=b[n:]
    def read(self,timeout=2):
        b=bytearray();end=time.monotonic()+timeout
        while time.monotonic()<end:
            ready,_,_=select.select([self.fd],[],[],max(0,end-time.monotonic()))
            if not ready:break
            b+=os.read(self.fd,262)
            if len(b)>=3 and len(b)>=struct.unpack_from('<H',b,1)[0]+5:
                assert b[0]==0xa5 and struct.unpack_from('<H',b,len(b)-2)[0]==binascii.crc_hqx(b[1:-2],0xffff),b.hex()
                return bytes(b)
        return None
    def request(self,cmd,p=b''):
        self.send(self.frame(cmd,p));b=self.read();assert b is not None,'no response';assert b[3]==cmd|128;return b[4:-2]

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--device',required=True);ap.add_argument('--openocd',default='openocd');ap.add_argument('--gcc-prefix',default='arm-none-eabi-');ap.add_argument('--clang',default='clang')
    args=ap.parse_args();out=ROOT/'build/engineering-board';out.mkdir(parents=True,exist_ok=True)
    firmware=ROOT/'build/native/tinyplc-layout.elf'
    report={'firmware_sha256':hashlib.sha256(firmware.read_bytes()).hexdigest(),'events':[]}
    def record(name,**data):
        event=dict(name=name,**data);report['events'].append(event);print(json.dumps(event),flush=True)
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    def cli(*cmd,allow_fault=False):
        r=subprocess.run([str(ROOT/'target/debug/plctool'),args.device,*map(str,cmd)],capture_output=True,text=True,timeout=12)
        if r.returncode and not allow_fault:raise RuntimeError(r.stderr)
        value=json.loads(r.stdout) if r.stdout.strip() else None
        record('cli',command=list(map(str,cmd)),code=r.returncode,result=value,error=r.stderr.strip())
        return value
    def ocd(script,name):
        path=out/(name+'.tcl');path.write_text(script)
        r=subprocess.run([args.openocd,'-f','interface/stlink.cfg','-f','target/stm32f4x.cfg','-f',str(path)],capture_output=True,text=True,timeout=20)
        (out/(name+'.log')).write_text(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stdout+r.stderr)
        return r.stdout+r.stderr
    def flash(name):
        ocd(f'adapter speed 1000\nprogram {{{firmware}}} verify reset exit\n',name);time.sleep(.25)
    symbols={p[2]:int(p[0],16) for line in (ROOT/'build/native/symbols.txt').read_text().splitlines() if len(p:=line.split())==3}
    sample_number=0
    def sample(name):
        nonlocal sample_number
        fields={x:(symbols[x],1) for x in ['native_status','native_output','input_pressed','scan_cycles_max','missed_releases','uart_rx_errors','comms_stack_free_words','stack_free_words','worker_stack_free_words','guard_fault_cfsr','guard_fault_cycles','guard_safe_cycles','guard_last_elapsed']}
        fields.update(committed=(symbols['supervisor']+136,3),descriptor=(0x20018100,4),gpio=(0x40020014,1))
        script='adapter speed 1000\ninit\nhalt\n'+''.join(f'echo "DATA {key} [read_memory {at} 32 {count}]"\n' for key,(at,count) in fields.items())+'resume\nshutdown\n'
        log=ocd(script,f'sample-{sample_number}');sample_number+=1
        values={}
        for line in log.splitlines():
            if line.startswith('DATA '):
                p=line.split();values[p[1]]=[int(x,0) for x in p[2:]]
        assert len(values)==len(fields),log
        record(name,values=values);return values
    # Normal product packages use Rust/LLVM and its exported schema.
    packages={}
    for name,source in [('normal','examples/button_led.st'),('off','examples/download_led_off.st'),('divide','tests/scan/fault.st')]:
        for slot in ('A','B'):
            dest=out/f'{name}-{slot}.tplc'
            subprocess.run([str(ROOT/'target/debug/plcpack'),str(ROOT/source),'--slot',slot,'-o',str(dest),'--clang',args.clang,'--ld',args.gcc_prefix+'ld'],check=True)
            packages[name,slot]=dest
    # Native fault fixtures deliberately bypass ST, but use the same package
    # contract/loader. No bytecode, dynamic linker or device relocation involved.
    golden=bytes.fromhex((ROOT/'tests/wire/fixtures/package-a.hex').read_text())
    probes=[(1,259),(3,259),(7,260),(8,258),(9,261),(17,261),(18,259),(19,259),(20,259)]
    for probe,_ in probes:
        for slot,base in [('A',0x20010000),('B',0x20014000)]:
            obj=out/f'probe-{probe}-{slot}.o';elf=obj.with_suffix('.elf');binary=obj.with_suffix('.bin')
            subprocess.run([args.gcc_prefix+'gcc','-mcpu=cortex-m4','-mthumb',f'-DPROBE={probe}','-c',str(ROOT/'tests/target/probes.S'),'-o',str(obj)],check=True)
            subprocess.run([args.gcc_prefix+'ld',f'--defsym=TINYPLC_CODE_BASE={base}','-T',str(ROOT/'port/nucleo_f446re/native/program.ld'),str(obj),'-o',str(elf)],check=True)
            subprocess.run([args.gcc_prefix+'objcopy','-O','binary',str(elf),str(binary)],check=True)
            eb=elf.read_bytes();sh=struct.unpack_from('<I',eb,32)[0];count=struct.unpack_from('<H',eb,48)[0]
            sections=[struct.unpack_from('<10I',eb,sh+i*40) for i in range(count)]
            text=next(s for s in sections if s[2]&4 and s[5]);payload=binary.read_bytes();payload+=bytes((-len(payload))%4)
            b=bytearray(golden[:80])+payload+golden[84:]
            for at,value in [(8,len(b)),(24,base),(32,len(payload)),(36,text[3]-base),(40,text[5]),(44,(struct.unpack_from('<I',eb,24)[0]&~1)-base),(48,80+len(payload)),(64,0)]:struct.pack_into('<I',b,at,value)
            struct.pack_into('<I',b,64,zlib.crc32(b));dest=out/f'probe-{probe}-{slot}.tplc';dest.write_bytes(b);packages[f'probe-{probe}',slot]=dest
    maximum_source=out/'maximum-tags.st'
    maximum_source.write_text('PROGRAM Maximum\nVAR\n'+''.join(f'V{i:02d} : DINT;\n' for i in range(64))+'END_VAR\nV00 := V00 + 1;\nEND_PROGRAM\n')
    maximum=out/'maximum-tags-A.tplc'
    subprocess.run([str(ROOT/'target/debug/plcpack'),str(maximum_source),'--slot','A','-o',str(maximum),'--clang',args.clang,'--ld',args.gcc_prefix+'ld'],check=True)
    packages['maximum','A']=maximum
    report['packages']={f'{name}-{slot}':hashlib.sha256(path.read_bytes()).hexdigest() for (name,slot),path in packages.items()}
    try:
        flash('initial-flash');assert cli('status')['fault']==0
        serial=Serial(args.device)
        try:
            bad=bytearray(serial.frame(1));bad[-1]^=1;serial.send(bad);assert serial.read(.15) is None
            serial.send(serial.frame(1)[:3]);time.sleep(.15);assert serial.request(1)[0]==0
            assert serial.request(127)==b'\x08';assert serial.request(7)==b'\x08';assert serial.request(9,b'\0')==b'\x01'
            b=bytearray(packages['off','B'].read_bytes());b[80]^=1
            begin=serial.request(2,struct.pack('<I',len(b)));assert begin[0]==0;tid=struct.unpack_from('<I',begin,1)[0]
            assert serial.request(4,struct.pack('<I',tid))==b'\x01'
            offset=0
            for chunk in [b[i:i+240] for i in range(0,len(b),240)]:
                p=struct.pack('<II',tid,offset)+chunk
                response=serial.request(3,p);assert response[0]==0
                assert serial.request(3,p)==response # exact duplicate
                offset+=len(chunk)
            assert serial.request(4,struct.pack('<I',tid))==b'\x02'
            record('serial-negative-tests',crc_drop=True,partial_timeout=True,unsupported=True,partial_end=True,duplicate_chunk=True,corrupt_package_rejected=True)
        finally:serial.close()
        assert cli('status')['active_generation']==1
        ready=cli('download',packages['off','B'])['ready_generation'];assert cli('status')['active_generation']==1
        boot=sample('before-activation');assert bool(boot['gpio'][0]&32)==(not boot['input_pressed'][0])
        assert cli('activate',ready)['active_generation']==ready;time.sleep(.08)
        off=sample('reordered-tags-running');assert off['descriptor'][0]==0x20014001 and off['descriptor'][2]==ready
        assert off['committed'][0]>0 and bool(off['gpio'][0]&32)==bool(off['input_pressed'][0])
        # First-scan language fault, then fresh worker recovery with zero state.
        ready=cli('download',packages['divide','A'])['ready_generation'];cli('activate',ready,allow_fault=True)
        assert cli('status')['fault']==5
        fault=sample('division-fault');assert fault['native_output']==[0] and fault['committed'][2]==0
        ready=cli('download',packages['normal','B'])['ready_generation'];assert cli('activate',ready)['fault']==0
        ready=cli('download',packages['maximum','A'])['ready_generation']
        assert cli('activate',ready)['fault']==0;time.sleep(.08)
        maximum_observed=sample('maximum-tags-running')
        assert maximum_observed['descriptor'][1]==64 and maximum_observed['committed'][0]>0
        assert maximum_observed['native_output']==[0] and not maximum_observed['gpio'][0]&32
        ready=cli('download',packages['normal','B'])['ready_generation'];assert cli('activate',ready)['fault']==0
        for case_index,(probe,expected) in enumerate(probes):
            desired='A' if case_index%2==0 else 'B'
            info=cli('info')
            active='A' if info['slots'][0]['state']==1 else 'B'
            if active==desired:
                other='B' if active=='A' else 'A'
                ready=cli('download',packages['normal',other])['ready_generation']
                assert cli('activate',ready)['fault']==0
            info=cli('info');slot='B' if info['slots'][0]['state']==1 else 'A'
            assert slot==desired
            ready=cli('download',packages[f'probe-{probe}',slot])['ready_generation']
            cli('activate',ready,allow_fault=True);time.sleep(.7 if expected==261 else .08)
            status=cli('status');assert status['fault']==expected,(probe,status)
            observed=sample(f'probe-{probe}-contained');assert observed['native_output']==[0]
            if expected!=261:assert observed['committed'][2]==3
            info=cli('info');slot='B' if info['slots'][0]['state']==1 else 'A'
            ready=cli('download',packages['normal',slot])['ready_generation'];assert cli('activate',ready)['fault']==0
        record('hardware_matrix_pass',native_fault_cases=len(probes),division_case=True)
    finally:
        flash('restore-normal');record('normal_firmware_restored',status=cli('status'))

if __name__=='__main__':main()
