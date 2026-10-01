// Independent test-only envelope consumer. Not a production package validator.
#[allow(dead_code)]
#[path = "../../contract/src/generated.rs"]
mod generated;
#[allow(dead_code)]
#[path = "../../contract/src/primitives.rs"]
mod wire;
use generated::*;
use wire::*;
fn package(b: &[u8]) -> bool {
    if b.len() < PACKAGE_BYTES as usize || b.len() > PACKAGE_BYTES_MAX as usize {
        return false;
    }
    let u = |at| read_u32(b, at as usize).unwrap();
    let h = |at| u32::from(read_u16(b, at as usize).unwrap());
    if u(PACKAGE_MAGIC_OFFSET) != PACKAGE_MAGIC
        || h(PACKAGE_VERSION_OFFSET) != PACKAGE_VERSION
        || h(PACKAGE_HEADER_BYTES_OFFSET) != PACKAGE_BYTES
        || u(PACKAGE_TOTAL_BYTES_OFFSET) as usize != b.len()
    {
        return false;
    }
    let (po, pl) = (
        u(PACKAGE_PAYLOAD_OFFSET_OFFSET),
        u(PACKAGE_PAYLOAD_BYTES_OFFSET),
    );
    let (to, tl, en) = (
        u(PACKAGE_TEXT_OFFSET_OFFSET),
        u(PACKAGE_TEXT_BYTES_OFFSET),
        u(PACKAGE_ENTRY_OFFSET_OFFSET),
    );
    let (tags, count) = (u(PACKAGE_TAGS_OFFSET_OFFSET), h(PACKAGE_TAG_COUNT_OFFSET));
    if po != PACKAGE_BYTES
        || pl == 0
        || pl > CODE_CAPACITY
        || pl & 3 != 0
        || range(b.len(), po, pl).is_none()
    {
        return false;
    }
    if count == 0 || count > TAG_LIMIT || h(PACKAGE_TAG_RECORD_BYTES_OFFSET) != TAG_BYTES {
        return false;
    }
    if tags != po + pl
        || range(b.len(), tags, count * TAG_BYTES).is_none()
        || (tags + count * TAG_BYTES) as usize != b.len()
    {
        return false;
    }
    if to & 1 != 0
        || tl & 1 != 0
        || en & 1 != 0
        || tl < 2
        || range(pl as usize, to, tl).is_none()
        || en < to
        || en - to > tl - 2
    {
        return false;
    }
    u(PACKAGE_SCHEMA_CRC_OFFSET) == crc32(&b[tags as usize..], 0..0)
        && u(PACKAGE_PACKAGE_CRC_OFFSET)
            == crc32(
                b,
                PACKAGE_PACKAGE_CRC_OFFSET as usize..PACKAGE_PACKAGE_CRC_OFFSET as usize + 4,
            )
}
fn main() {
    assert_eq!(crc32(b"123456789", 0..0), 0xcbf43926);
    assert_eq!(crc16(b"123456789"), 0x29b1);
    assert!(range(80, u32::MAX, 2).is_none());
    assert!(range(80, 1, u32::MAX).is_none());
    assert!(read_u32(&[0; 4], usize::MAX).is_none());
    assert!(read_u64(&[0; 7], 0).is_none());
    let args: Vec<_> = std::env::args().collect();
    let b = std::fs::read(&args[2]).unwrap();
    let ok = if args[1] == "package" {
        package(&b)
    } else if args[1] == "dispatch" {
        if b.len() != DISPATCH_BYTES as usize {
            false
        } else {
            let entry = read_u32(&b, DISPATCH_ENTRY_OFFSET as usize).unwrap();
            let count = read_u32(&b, DISPATCH_TAG_COUNT_OFFSET as usize).unwrap();
            let pc = entry & !1;
            entry & 1 != 0
                && (1..=TAG_LIMIT).contains(&count)
                && read_u32(&b, DISPATCH_GENERATION_OFFSET as usize) != Some(0)
                && read_u32(&b, DISPATCH_RESERVED_OFFSET as usize) == Some(0)
                && ((SLOT_A_BASE..SLOT_A_BASE + CODE_CAPACITY).contains(&pc)
                    || (SLOT_B_BASE..SLOT_B_BASE + CODE_CAPACITY).contains(&pc))
        }
    } else if b.len() >= 6 && b.len() <= FRAME_BYTES_MAX as usize && b[0] == FRAME_START as u8 {
        let len = read_u16(&b, FRAME_PREFIX_LENGTH_OFFSET as usize).unwrap() as u32;
        (FRAME_LENGTH_MIN..=FRAME_LENGTH_MAX).contains(&len)
            && b.len() == len as usize + 5
            && read_u16(&b, b.len() - 2) == Some(crc16(&b[1..b.len() - 2]))
    } else {
        false
    };
    if !ok {
        std::process::exit(1);
    }
    println!("{:08x}", crc32(&b, 0..0));
}
