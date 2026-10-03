//! Package our host-linked ELF, including its compiler-exported tag metadata.
//! This small ELF reader is a host build tool, never part of the MCU loader.
use std::collections::BTreeMap;
use tinyplc_contract::generated::*;
use tinyplc_contract::{crc32, read_u16, read_u32};
type Result<T> = std::result::Result<T, String>;
fn bytes(b: &[u8], at: u32, len: u32) -> Result<&[u8]> {
    let range = tinyplc_contract::range(b.len(), at, len).ok_or("ELF range outside file")?;
    Ok(&b[range])
}
fn u(b: &[u8], at: usize) -> Result<u32> {
    read_u32(b, at).ok_or("truncated ELF word".into())
}
fn h(b: &[u8], at: usize) -> Result<u16> {
    read_u16(b, at).ok_or("truncated ELF halfword".into())
}
fn string(b: &[u8], at: u32) -> Result<&str> {
    let tail = b.get(at as usize..).ok_or("string index out of bounds")?;
    let n = tail
        .iter()
        .position(|&x| x == 0)
        .ok_or("unterminated ELF string")?;
    std::str::from_utf8(&tail[..n]).map_err(|_| "non-UTF8 ELF string".into())
}
#[derive(Clone)]
struct Section {
    name: u32,
    kind: u32,
    flags: u32,
    addr: u32,
    offset: u32,
    size: u32,
    link: u32,
    stride: u32,
}
fn put32(b: &mut [u8], at: u32, value: u32) {
    b[at as usize..at as usize + 4].copy_from_slice(&value.to_le_bytes());
}
fn put16(b: &mut [u8], at: u32, value: u32) {
    b[at as usize..at as usize + 2].copy_from_slice(&(value as u16).to_le_bytes());
}

/// Accept only the exact fixed-slot ELF emitted by the local build pipeline.
/// Metadata is extracted from exported symbols, not a separate tag JSON file.
pub fn package_elf(elf: &[u8], base: u32) -> Result<Vec<u8>> {
    if ![SLOT_A_BASE, SLOT_B_BASE].contains(&base) {
        return Err("unsupported slot".into());
    }
    if elf.get(..7) != Some(b"\x7fELF\x01\x01\x01")
        || h(elf, 16)? != 2
        || h(elf, 18)? != 40
        || u(elf, 20)? != 1
        || h(elf, 40)? != 52
        || h(elf, 46)? != 40
        || u(elf, 36)? & 0x400 != 0
        || u(elf, 36)? & 0xff000000 != 0x05000000
    {
        return Err("expected little-endian ARM ELF32 EXEC, soft-float".into());
    }
    let shoff = u(elf, 32)?;
    let count = h(elf, 48)? as u32;
    if count == 0 {
        return Err("missing section table".into());
    }
    let table = bytes(elf, shoff, count * 40)?;
    let mut sections = Vec::new();
    for b in table.chunks_exact(40) {
        sections.push(Section {
            name: u(b, 0)?,
            kind: u(b, 4)?,
            flags: u(b, 8)?,
            addr: u(b, 12)?,
            offset: u(b, 16)?,
            size: u(b, 20)?,
            link: u(b, 24)?,
            stride: u(b, 36)?,
        });
    }
    let names = sections
        .get(h(elf, 50)? as usize)
        .ok_or("missing section names")?;
    let names = bytes(elf, names.offset, names.size)?;
    let mut payload = vec![0; CODE_CAPACITY as usize];
    let mut ranges = Vec::new();
    let mut text = None;
    let mut end = 0;
    let mut symbols = BTreeMap::new();
    for s in &sections {
        if (s.kind == 4 || s.kind == 9) && s.size != 0 {
            return Err("unresolved relocations".into());
        }
        if s.flags & 2 != 0 && s.size != 0 {
            if s.flags & 1 != 0 || s.kind == 8 {
                return Err("writable/zero-fill module section".into());
            }
            let offset = s.addr.checked_sub(base).ok_or("section precedes slot")?;
            let r = tinyplc_contract::range(payload.len(), offset, s.size)
                .ok_or("section exceeds slot")?;
            if ranges
                .iter()
                .any(|old: &std::ops::Range<usize>| old.start < r.end && r.start < old.end)
            {
                return Err("overlapping ELF sections".into());
            }
            if s.flags & 4 != 0 {
                if text.is_some() || string(names, s.name)? != ".text" {
                    return Err("expected one text section".into());
                }
                text = Some((offset, s.size));
            }
            payload[r.clone()].copy_from_slice(bytes(elf, s.offset, s.size)?);
            end = end.max(r.end);
            ranges.push(r);
        }
        if s.kind == 2 {
            if s.stride != 16 || s.size % 16 != 0 {
                return Err("invalid symbol table".into());
            }
            let strings = sections
                .get(s.link as usize)
                .ok_or("invalid symbol strings")?;
            let strings = bytes(elf, strings.offset, strings.size)?;
            for sym in bytes(elf, s.offset, s.size)?.chunks_exact(16) {
                let bind = sym[12] >> 4;
                if (bind == 1 || bind == 2) && h(sym, 14)? == 0 {
                    return Err("undefined import (including weak)".into());
                }
                let name = string(strings, u(sym, 0)?)?;
                if name.starts_with("tinyplc_")
                    && symbols
                        .insert(name.to_owned(), (u(sym, 4)?, u(sym, 8)?, sym[12] & 15))
                        .is_some()
                {
                    return Err("duplicate exported metadata symbol".into());
                }
            }
        }
    }
    let (text_offset, text_bytes) = text.ok_or("missing executable text")?;
    let entry = u(elf, 24)?;
    let entry_offset = (entry & !1).checked_sub(base).ok_or("entry before slot")?;
    let scan = symbols.get("tinyplc_scan").ok_or("missing scan entry")?;
    if entry & 1 == 0
        || scan.0 != entry
        || scan.2 != 2
        || text_offset & 1 != 0
        || text_bytes < 2
        || text_bytes & 1 != 0
        || entry_offset < text_offset
        || entry_offset - text_offset > text_bytes - 2
    {
        return Err("invalid Thumb entry/text".into());
    }
    let symbol = |name: &str, size: u32| -> Result<&[u8]> {
        let &(address, actual, kind) =
            symbols.get(name).ok_or_else(|| format!("missing {name}"))?;
        if actual != size || kind != 1 {
            return Err(format!("invalid metadata symbol {name}"));
        }
        let offset = address.checked_sub(base).ok_or("metadata before slot")?;
        let r =
            tinyplc_contract::range(payload.len(), offset, size).ok_or("metadata outside slot")?;
        if !ranges.iter().any(|s| r.start >= s.start && r.end <= s.end) {
            return Err("metadata outside allocated section".into());
        }
        Ok(&payload[r])
    };
    if u(symbol("tinyplc_abi_version", 4)?, 0)? != NATIVE_ABI {
        return Err("compiler ABI mismatch".into());
    }
    let count = u(symbol("tinyplc_tag_count", 4)?, 0)?;
    if !(1..=TAG_LIMIT).contains(&count) {
        return Err("package requires 1..64 tags".into());
    }
    let names = symbol("tinyplc_tag_names", count * 32)?;
    let types = symbol("tinyplc_tag_types", count)?;
    let classes = symbol("tinyplc_tag_classes", count)?;
    let mut tags = vec![0; count as usize * TAG_BYTES as usize];
    let mut seen = std::collections::BTreeSet::new();
    let mut bindings = 0u32;
    for i in 0..count as usize {
        let name = &names[i * 32..i * 32 + 32];
        let n = name
            .iter()
            .position(|&x| x == 0)
            .ok_or("unterminated tag name")?;
        if n == 0
            || name[n..].iter().any(|&x| x != 0)
            || !name[..n]
                .iter()
                .enumerate()
                .all(|(j, &c)| c.is_ascii_uppercase() || c == b'_' || (j > 0 && c.is_ascii_digit()))
            || !seen.insert(name)
        {
            return Err("noncanonical/duplicate tag name".into());
        }
        let ty = u32::from(types[i]);
        let class = u32::from(classes[i]);
        let binding = match (class, ty, &name[..n]) {
            (CLASS_INPUT, TYPE_BOOL, b"BTN") => BINDING_BTN_PC13,
            (CLASS_OUTPUT, TYPE_BOOL, b"LED") => BINDING_LED_PA5,
            (CLASS_INPUT, TYPE_DINT, b"__CLOCK_MS") => BINDING_CLOCK_MS,
            (CLASS_VAR | CLASS_TIMER, TYPE_BOOL | TYPE_DINT | TYPE_TIME, _) => BINDING_NONE,
            _ => return Err("unsupported compiler board binding/type".into()),
        };
        if binding != 0 {
            if bindings & (1 << binding) != 0 {
                return Err("duplicate board binding".into());
            }
            bindings |= 1 << binding;
        }
        let record = &mut tags[i * TAG_BYTES as usize..(i + 1) * TAG_BYTES as usize];
        record[..32].copy_from_slice(name);
        record[TAG_TYPE_OFFSET as usize] = types[i];
        record[TAG_CLASS_OFFSET as usize] = classes[i];
        put16(record, TAG_BINDING_OFFSET, binding);
    }
    let padded = (end + 3) & !3;
    payload.truncate(padded);
    let total = PACKAGE_BYTES as usize + payload.len() + tags.len();
    let mut result = vec![0; total];
    for (at, value) in [
        (PACKAGE_MAGIC_OFFSET, PACKAGE_MAGIC),
        (PACKAGE_TOTAL_BYTES_OFFSET, total as u32),
        (PACKAGE_LINK_BASE_OFFSET, base),
        (PACKAGE_PAYLOAD_OFFSET_OFFSET, PACKAGE_BYTES),
        (PACKAGE_PAYLOAD_BYTES_OFFSET, payload.len() as u32),
        (PACKAGE_TEXT_OFFSET_OFFSET, text_offset),
        (PACKAGE_TEXT_BYTES_OFFSET, text_bytes),
        (PACKAGE_ENTRY_OFFSET_OFFSET, entry_offset),
        (
            PACKAGE_TAGS_OFFSET_OFFSET,
            PACKAGE_BYTES + payload.len() as u32,
        ),
        (PACKAGE_SCHEMA_CRC_OFFSET, crc32(&tags, 0..0)),
    ] {
        put32(&mut result, at, value);
    }
    for (at, value) in [
        (PACKAGE_VERSION_OFFSET, PACKAGE_VERSION),
        (PACKAGE_HEADER_BYTES_OFFSET, PACKAGE_BYTES),
        (PACKAGE_KIND_OFFSET, IMAGE_NATIVE),
        (PACKAGE_TARGET_OFFSET, TARGET_F446),
        (PACKAGE_NATIVE_ABI_OFFSET, NATIVE_ABI),
        (PACKAGE_RUNTIME_CONTRACT_OFFSET, RUNTIME_CONTRACT),
        (PACKAGE_AUTH_OFFSET, AUTH_UNSIGNED_LAB),
        (PACKAGE_TAG_COUNT_OFFSET, count),
        (PACKAGE_TAG_RECORD_BYTES_OFFSET, TAG_BYTES),
        (PACKAGE_CELL_BYTES_OFFSET, CELL_BYTES),
        (PACKAGE_STACK_BYTES_OFFSET, WORKER_STACK_BYTES),
    ] {
        put16(&mut result, at, value);
    }
    result[PACKAGE_BYTES as usize..PACKAGE_BYTES as usize + payload.len()]
        .copy_from_slice(&payload);
    result[PACKAGE_BYTES as usize + payload.len()..].copy_from_slice(&tags);
    let crc = crc32(
        &result,
        PACKAGE_PACKAGE_CRC_OFFSET as usize..PACKAGE_PACKAGE_CRC_OFFSET as usize + 4,
    );
    put32(&mut result, PACKAGE_PACKAGE_CRC_OFFSET, crc);
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;
    // Independent miniature ELF with compiler-shaped exports; not executable test code.
    fn fixture() -> Vec<u8> {
        let base = SLOT_A_BASE;
        let names = b"\0.text\0.rodata\0.symtab\0.strtab\0.shstrtab\0";
        let strings=b"\0tinyplc_scan\0tinyplc_abi_version\0tinyplc_tag_count\0tinyplc_tag_types\0tinyplc_tag_classes\0tinyplc_tag_names\0";
        let mut b = vec![0; 52 + 6 * 40];
        b[..7].copy_from_slice(b"\x7fELF\x01\x01\x01");
        put16(&mut b, 16, 2);
        put16(&mut b, 18, 40);
        put32(&mut b, 20, 1);
        put32(&mut b, 24, base | 1);
        put32(&mut b, 32, 52);
        put32(&mut b, 36, 0x05000000);
        put16(&mut b, 40, 52);
        put16(&mut b, 46, 40);
        put16(&mut b, 48, 6);
        put16(&mut b, 50, 5);
        let text = b.len() as u32;
        b.extend_from_slice(&[0, 0x20, 0x70, 0x47]);
        let ro = b.len() as u32;
        b.extend_from_slice(&2u32.to_le_bytes());
        b.extend_from_slice(&1u32.to_le_bytes());
        b.extend_from_slice(&[2, 3, b'N']);
        b.extend_from_slice(&[0; 33]);
        let sym = b.len() as u32;
        b.extend_from_slice(&[0; 16]);
        for (name, address, size, kind, index) in [
            ("tinyplc_scan", base | 1, 4, 2, 1),
            ("tinyplc_abi_version", base + 4, 4, 1, 2),
            ("tinyplc_tag_count", base + 8, 4, 1, 2),
            ("tinyplc_tag_types", base + 12, 1, 1, 2),
            ("tinyplc_tag_classes", base + 13, 1, 1, 2),
            ("tinyplc_tag_names", base + 14, 32, 1, 2),
        ] {
            let offset = strings
                .windows(name.len())
                .position(|x| x == name.as_bytes())
                .unwrap() as u32;
            let mut record = [0; 16];
            put32(&mut record, 0, offset);
            put32(&mut record, 4, address);
            put32(&mut record, 8, size);
            record[12] = 0x10 | kind;
            put16(&mut record, 14, index);
            b.extend_from_slice(&record);
        }
        let str_at = b.len() as u32;
        b.extend_from_slice(strings);
        let name_at = b.len() as u32;
        b.extend_from_slice(names);
        for (i, name, kind, flags, addr, offset, size, link, stride) in [
            (1, 1, 1, 6, base, text, 4, 0, 0),
            (2, 7, 1, 2, base + 4, ro, 44, 0, 0),
            (3, 15, 2, 0, 0, sym, 112, 4, 16),
            (4, 23, 3, 0, 0, str_at, strings.len() as u32, 0, 0),
            (5, 31, 3, 0, 0, name_at, names.len() as u32, 0, 0),
        ] {
            let at = 52 + i * 40;
            for (delta, value) in [
                (0, name),
                (4, kind),
                (8, flags),
                (12, addr),
                (16, offset),
                (20, size),
                (24, link),
                (36, stride),
            ] {
                put32(&mut b, at + delta, value);
            }
        }
        b
    }
    #[test]
    fn elf_metadata_and_rejections() {
        let original = fixture();
        let p = package_elf(&original, SLOT_A_BASE).unwrap();
        assert_eq!(p.len(), 168);
        assert_eq!(p[128], b'N');
        assert_eq!(&p[160..164], &[2, 3, 0, 0]);
        assert_eq!(u(&p, 64).unwrap(), crc32(&p, 64..68));
        assert!(package_elf(&original, SLOT_B_BASE).is_err());
        for (at, value) in [
            (24, SLOT_A_BASE),
            (32, u32::MAX),
            (36, 0x05000400),
            (52 + 40 + 8, 7),
            (52 + 40 + 12, 0x08010000),
            (52 + 40 + 20, 20000),
            (52 + 80 + 12, SLOT_A_BASE),
            (52 + 80 + 4, 8),
            (52 + 120 + 4, 9),
            (52 + 120 + 24, 99),
            (52 + 120 + 36, 8),
        ] {
            let mut b = original.clone();
            put32(&mut b, at, value);
            assert!(package_elf(&b, SLOT_A_BASE).is_err(), "offset {at}");
        }
        let sym = u(&original, 52 + 120 + 16).unwrap() as usize;
        let ro = u(&original, 52 + 80 + 16).unwrap() as usize;
        for (at, value) in [
            (sym + 16 + 14, 0),
            (sym + 32 + 8, 3),
            (ro, 1),
            (ro + 10, b'n'),
            (ro + 9, 1),
        ] {
            let mut b = original.clone();
            b[at] = value;
            assert!(package_elf(&b, SLOT_A_BASE).is_err(), "byte {at}");
        }
        // Every file truncation must fail cleanly, and arbitrary mutations must never panic.
        for n in 0..original.len() {
            assert!(package_elf(&original[..n], SLOT_A_BASE).is_err());
        }
        let mut seed = 42u32;
        for _ in 0..2000 {
            let mut b = original.clone();
            seed = seed.wrapping_mul(1664525).wrapping_add(1013904223);
            let at = seed as usize % b.len();
            b[at] ^= 1 << (seed % 8);
            let _ = package_elf(&b, SLOT_A_BASE);
        }
    }
}
