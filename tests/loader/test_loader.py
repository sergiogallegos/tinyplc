"""Actual Rust packager -> C validator/staging, plus hostile package cases."""
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
import zlib
ROOT=Path(__file__).resolve().parents[2]

class Loader(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.out=Path(cls.temp.name)
        cls.exe=cls.out/'loader-test'
        subprocess.run([os.environ.get('CLANG','clang'),'-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
                        '-Icontract','-Iruntime/include','runtime/src/package.c','runtime/src/loader.c','tests/loader/loader_test.c','-o',str(cls.exe)],cwd=ROOT,check=True)
        cls.golden=bytes.fromhex((ROOT/'tests/wire/fixtures/package-b.hex').read_text())

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def validate(self,b,expected,base='0x20014000',policy='1'):
        path=self.out/'case.tplc';path.write_bytes(b)
        result=subprocess.run([str(self.exe),'validate',str(path),base,policy],capture_output=True,text=True,check=True)
        self.assertEqual(int(result.stdout),expected)

    def fixed(self,b,schema=False):
        b=bytearray(b)
        if schema:
            offset=struct.unpack_from('<I',b,48)[0]
            struct.pack_into('<I',b,60,zlib.crc32(b[offset:]))
        struct.pack_into('<I',b,64,0);struct.pack_into('<I',b,64,zlib.crc32(b));return b

    def test_all_header_requirements(self):
        self.validate(self.golden,0)
        self.validate(self.golden,4,policy='0')
        self.validate(self.golden,4,base='0x20010000')
        self.validate(self.golden,4,base='0x08010000')
        # Every policy/identity/resource/reserved field, independently re-CRC'd.
        for at,width,value in [(0,'I',0),(4,'H',2),(6,'H',79),(8,'I',203),(12,'H',2),(14,'H',2),
            (16,'H',1),(18,'H',2),(20,'H',1),(22,'H',1),(24,'I',0x08010000),(28,'I',0xffffffff),
            (32,'I',0xffffffff),(32,'I',0),(32,'I',3),(36,'I',0xfffffffe),(36,'I',1),
            (40,'I',0),(40,'I',3),(40,'I',0xfffffffe),(44,'I',1),(44,'I',4),(48,'I',80),
            (48,'I',0xffffffff),(52,'H',0),(52,'H',65),(54,'H',39),(56,'H',8),(58,'H',1024),
            (60,'I',0),(68,'I',1),(72,'I',1),(76,'I',1)]:
            with self.subTest(offset=at,value=value):
                b=bytearray(self.golden);struct.pack_into('<'+width,b,at,value);self.validate(self.fixed(b),4)
        self.validate(self.golden+b'\0',4)
        for n in (0,1,79,80,83,203):self.validate(self.golden[:n],4)
        b=bytearray(self.golden);b[80]^=1;self.validate(b,2)

    def test_schema_rejections(self):
        # Schema and package CRCs recomputed, so rejection must be semantic.
        for at,value in [(84,ord('b')),(84,ord('9')),(84,0),(88,1),(116,3),(117,4),(118,9),
                         (120,1),(156,2),(157,1),(158,1),(198,1)]:
            b=bytearray(self.golden);b[at]=value;self.validate(self.fixed(b,True),4)
        b=bytearray(self.golden);b[84:116]=b'A'*32;self.validate(self.fixed(b,True),4)
        b=bytearray(self.golden);b[124:156]=b[84:116];self.validate(self.fixed(b,True),4)
        b=bytearray(self.golden);b[157]=1;b[158]=1;self.validate(self.fixed(b,True),4)  # duplicate input binding, distinct names

    def test_staging(self):
        p=self.out/'golden.tplc';p.write_bytes(self.golden)
        subprocess.run([str(self.exe),'stage',str(p)],check=True)

    def test_maximum_package(self):
        tags=bytearray(self.golden[84:])
        for i in range(3,64):
            tags+=struct.pack('<32sBBHI',f'VAR_{i}'.encode(),2,3,0,0)
        b=bytearray(self.golden[:80])+bytearray(16384)+tags
        struct.pack_into('<I',b,8,len(b));struct.pack_into('<I',b,32,16384)
        struct.pack_into('<I',b,48,80+16384);struct.pack_into('<H',b,52,64)
        self.assertEqual(len(b),19024)
        fixed=self.fixed(b,True)
        self.validate(fixed,0)
        path=self.out/'maximum.tplc';path.write_bytes(fixed)
        subprocess.run([str(self.exe),'maximum',str(path)],check=True)
        self.validate(b+b'\0',4)

    def test_freestanding_memory(self):
        cc=os.environ.get('CLANG','clang')
        obj=self.out/'memory.o';exe=self.out/'memory-test'
        flags=['-Wall','-Wextra','-Werror','-fsanitize=address,undefined']
        subprocess.run([cc,*flags,'-ffreestanding','-fno-builtin','-Dmemcpy=plc_memcpy','-Dmemset=plc_memset',
                        '-Dmemmove=plc_memmove','-Dmemcmp=plc_memcmp','-c','port/nucleo_f446re/native/memory.c','-o',str(obj)],cwd=ROOT,check=True)
        subprocess.run([cc,*flags,'tests/loader/memory_test.c',str(obj),'-o',str(exe)],cwd=ROOT,check=True)
        subprocess.run([str(exe)],check=True)

    def test_ton_package_and_clock_binding(self):
        p=self.out/'ton.tplc'
        subprocess.run([str(ROOT/'target/debug/plcpack'),str(ROOT/'examples/ton_led.st'),
                        '--slot','B','-o',str(p),'--clang',os.environ.get('CLANG','clang'),
                        '--ld',os.environ.get('ARM_LD','arm-none-eabi-ld')],check=True)
        b=p.read_bytes();self.validate(b,0)
        offset=struct.unpack_from('<I',b,48)[0]
        records=[b[i:i+40] for i in range(offset,len(b),40)]
        self.assertEqual(len(records),8)
        self.assertEqual([r[33] for r in records],[1,2,4,4,4,4,4,1])
        self.assertEqual(struct.unpack_from('<BBH',records[-1],32),(2,1,3))
        for index,field,value in [(7,32,1),(7,34,4),(2,34,3),(2,33,5),(3,32,4)]:
            bad=bytearray(b);bad[offset+40*index+field]=value
            self.validate(self.fixed(bad,True),4)
        # Duplicate clock bindings cannot alias the frozen input image.
        bad=bytearray(b);bad[offset+32]=2;bad[offset+34]=3
        self.validate(self.fixed(bad,True),4)

    def test_real_packager(self):
        ld=os.environ.get('ARM_LD','arm-none-eabi-ld')
        self.assertTrue(shutil.which(ld), 'Set ARM_LD to pinned arm-none-eabi-ld; this test must not silently skip')
        for slot,base in [('A','0x20010000'),('B','0x20014000')]:
            p=self.out/f'{slot}.tplc'
            command=[str(ROOT/'target/debug/plcpack'),str(ROOT/'examples/button_led.st'),'--slot',slot,'-o',str(p),
                     '--clang',os.environ.get('CLANG','clang'),'--ld',ld]
            subprocess.run(command,check=True)
            package=p.read_bytes();self.validate(package,0,base=base)
            self.assertEqual(struct.unpack_from('<H',package,52)[0],3)
            tags=struct.unpack_from('<I',package,48)[0]
            self.assertEqual(package[tags:],self.golden[84:])
            if slot=='B':subprocess.run([str(self.exe),'stage',str(p)],check=True)
            subprocess.run(command,check=True);self.assertEqual(package,p.read_bytes())
        custom=self.out/'custom.st'
        custom.write_text('PROGRAM X VAR VALUE : DINT; FLAG : BOOL; END_VAR VALUE := 42; FLAG := TRUE; END_PROGRAM')
        custom_out=self.out/'custom.tplc'
        subprocess.run([str(ROOT/'target/debug/plcpack'),str(custom),'--slot','B','-o',str(custom_out),
                        '--clang',os.environ.get('CLANG','clang'),'--ld',ld],check=True)
        package=custom_out.read_bytes();self.validate(package,0)
        at=struct.unpack_from('<I',package,48)[0]
        self.assertEqual(struct.unpack_from('<H',package,52)[0],2)
        self.assertEqual(package[at:at+6],b'VALUE\0')
        self.assertEqual(package[at+32:at+36],bytes([2,3,0,0]))
        self.assertEqual(package[at+40:at+45],b'FLAG\0')
        bad=self.out/'bad.st';bad.write_text('PROGRAM X VAR N : DINT; END_VAR N := TRUE; END_PROGRAM')
        p=self.out/'unchanged.tplc';p.write_bytes(b'old')
        result=subprocess.run([str(ROOT/'target/debug/plcpack'),str(bad),'--slot','A','-o',str(p)],capture_output=True)
        self.assertNotEqual(result.returncode,0);self.assertEqual(p.read_bytes(),b'old')

if __name__=='__main__':unittest.main()
