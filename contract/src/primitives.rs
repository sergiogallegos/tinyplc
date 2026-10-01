//! Decode bytes explicitly; never cast untrusted bytes to a native struct.
use super::generated::{CRC16_INIT, CRC16_POLY, CRC32_INIT, CRC32_POLY_REFLECTED, CRC32_XOROUT};

pub fn range(total: usize, offset: u32, length: u32) -> Option<core::ops::Range<usize>> {
    let start = usize::try_from(offset).ok()?;
    let len = usize::try_from(length).ok()?;
    if start > total || len > total - start {
        return None;
    }
    Some(start..start + len)
}

pub fn read_u16(bytes: &[u8], offset: usize) -> Option<u16> {
    let end = offset.checked_add(2)?;
    Some(u16::from_le_bytes(bytes.get(offset..end)?.try_into().ok()?))
}
pub fn read_u32(bytes: &[u8], offset: usize) -> Option<u32> {
    let end = offset.checked_add(4)?;
    Some(u32::from_le_bytes(bytes.get(offset..end)?.try_into().ok()?))
}
pub fn read_u64(bytes: &[u8], offset: usize) -> Option<u64> {
    let end = offset.checked_add(8)?;
    Some(u64::from_le_bytes(bytes.get(offset..end)?.try_into().ok()?))
}

/// CRC-32/ISO-HDLC, optionally treating a field as zero (package CRC field).
pub fn crc32(bytes: &[u8], zero: core::ops::Range<usize>) -> u32 {
    let mut crc = CRC32_INIT;
    for (i, &byte) in bytes.iter().enumerate() {
        crc ^= if zero.contains(&i) {
            0
        } else {
            u32::from(byte)
        };
        for _ in 0..8 {
            crc = (crc >> 1) ^ (CRC32_POLY_REFLECTED & 0u32.wrapping_sub(crc & 1));
        }
    }
    crc ^ CRC32_XOROUT
}

/// CRC-16/CCITT-FALSE. Framing excludes start and trailing CRC bytes.
pub fn crc16(bytes: &[u8]) -> u16 {
    let mut crc = CRC16_INIT as u16;
    for &byte in bytes {
        crc ^= u16::from(byte) << 8;
        for _ in 0..8 {
            crc = (crc << 1)
                ^ if crc & 0x8000 != 0 {
                    CRC16_POLY as u16
                } else {
                    0
                };
        }
    }
    crc
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn bounds_and_checksums() {
        assert_eq!(crc32(b"123456789", 0..0), 0xcbf43926);
        assert_eq!(crc16(b"123456789"), 0x29b1);
        assert_eq!(range(80, 80, 0), Some(80..80));
        assert_eq!(range(80, u32::MAX, 2), None);
        assert_eq!(range(80, 1, u32::MAX), None);
        assert_eq!(read_u32(&[0; 4], usize::MAX), None);
        assert_eq!(read_u64(&[0; 7], 0), None);
        assert_eq!(read_u16(&[0x12, 0x34], 0), Some(0x3412));
    }
}
