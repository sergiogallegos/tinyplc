//! Local-lab POSIX serial CLI. std + system stty; no serial/JSON crates.
use std::{
    env,
    fs::{self, File, OpenOptions},
    io::{Read, Write},
    process::{Command, ExitCode},
    time::{Duration, Instant},
};
use tinyplc_contract::generated::*;
use tinyplc_contract::{crc16, crc32, read_u16, read_u32, read_u64};
type Result<T> = std::result::Result<T, String>;
fn u(b: &[u8], at: u32) -> u32 {
    read_u32(b, at as usize).unwrap()
}
fn h(b: &[u8], at: u32) -> u32 {
    u32::from(read_u16(b, at as usize).unwrap())
}
fn wide(b: &[u8], at: u32) -> u64 {
    read_u64(b, at as usize).unwrap()
}
fn stty(device: &str, args: &[&str]) -> Result<String> {
    let flag = if cfg!(target_os = "macos") {
        "-f"
    } else {
        "-F"
    };
    let output = Command::new("stty")
        .args([flag, device])
        .args(args)
        .output()
        .map_err(|e| e.to_string())?;
    if !output.status.success() {
        return Err(String::from_utf8_lossy(&output.stderr).into());
    }
    Ok(String::from_utf8_lossy(&output.stdout).trim().into())
}
struct Serial {
    file: File,
    device: String,
    saved: String,
    buffer: Vec<u8>,
}
impl Drop for Serial {
    fn drop(&mut self) {
        let _ = stty(&self.device, &[&self.saved]);
    }
}
impl Serial {
    fn open(device: &str) -> Result<Self> {
        // Keep an open descriptor while stty configures the device. macOS can
        // reset tty settings on last close; configuring before open can leave
        // read() in canonical/blocking mode on a real USB port (unlike a PTY).
        let file = OpenOptions::new()
            .read(true)
            .write(true)
            .open(device)
            .map_err(|e| e.to_string())?;
        let saved = stty(device, &["-g"])?;
        let mut serial = Self {
            file,
            device: device.into(),
            saved,
            buffer: Vec::new(),
        };
        stty(
            device,
            &[
                "115200", "raw", "-echo", "cs8", "-parenb", "-cstopb", "-ixon", "-ixoff",
                "-crtscts", "min", "0", "time", "1",
            ],
        )?;
        // Discard old transport input before establishing this single-host session.
        let deadline = Instant::now() + Duration::from_millis(500);
        let mut junk = [0; 262];
        while Instant::now() < deadline {
            if serial.file.read(&mut junk).map_err(|e| e.to_string())? == 0 {
                break;
            }
        }
        Ok(serial)
    }
    fn send(&mut self, cmd: u8, p: &[u8]) -> Result<()> {
        if p.len() > 256 {
            return Err("payload exceeds frame".into());
        }
        let mut b = vec![FRAME_START as u8];
        b.extend_from_slice(&((p.len() + 1) as u16).to_le_bytes());
        b.push(cmd);
        b.extend_from_slice(p);
        b.extend_from_slice(&crc16(&b[1..]).to_le_bytes());
        self.file.write_all(&b).map_err(|e| e.to_string())
    }
    fn response(&mut self, cmd: u8, expected: usize, next: Option<u32>) -> Result<Vec<u8>> {
        let end = Instant::now() + Duration::from_secs(2);
        while Instant::now() < end {
            while self.buffer.len() >= 3 {
                if self.buffer[0] != FRAME_START as u8 {
                    self.buffer.remove(0);
                    continue;
                }
                let len = read_u16(&self.buffer, 1).unwrap() as usize;
                if !(1..=FRAME_LENGTH_MAX as usize).contains(&len) {
                    self.buffer.remove(0);
                    continue;
                }
                if self.buffer.len() < len + 5 {
                    break;
                }
                if read_u16(&self.buffer, len + 3) != Some(crc16(&self.buffer[1..len + 3])) {
                    self.buffer.remove(0);
                    continue;
                }
                let got = self.buffer[3];
                let payload = self.buffer[4..len + 3].to_vec();
                self.buffer.drain(..len + 5);
                if got != cmd | 0x80 {
                    continue;
                }
                if payload.is_empty() {
                    return Err("empty response".into());
                }
                if payload[0] != 0 {
                    if payload.len() != 1 {
                        return Err("malformed error response".into());
                    }
                    return Err(format!("device status {} for command {cmd}", payload[0]));
                }
                if expected != 0 && payload.len() != expected {
                    return Err(format!("wrong response width for command {cmd}"));
                }
                // A delayed duplicate chunk ACK must not acknowledge a later chunk.
                if next.is_some_and(|n| u(&payload, 1) != n) {
                    continue;
                }
                return Ok(payload);
            }
            let mut b = [0; 262];
            let n = self.file.read(&mut b).map_err(|e| e.to_string())?;
            if n == 0 {
                self.buffer.clear();
                continue;
            }
            self.buffer.extend_from_slice(&b[..n]);
            if self.buffer.len() > 524 {
                self.buffer.clear();
            }
        }
        Err("timeout: outcome uncertain; reconcile info/status before retrying a mutation".into())
    }
    fn request(&mut self, cmd: u32, p: &[u8], width: u32) -> Result<Vec<u8>> {
        self.send(cmd as u8, p)?;
        self.response(cmd as u8, width as usize, None)
    }
    fn info(&mut self) -> Result<Vec<u8>> {
        let b = self.request(CMD_INFO, &[], INFO_RESPONSE_BYTES)?;
        if h(&b, INFO_RESPONSE_PROTOCOL_OFFSET) != PROTOCOL_VERSION
            || h(&b, INFO_RESPONSE_PACKAGE_VERSION_OFFSET) != PACKAGE_VERSION
            || h(&b, INFO_RESPONSE_TARGET_OFFSET) != TARGET_F446
            || h(&b, INFO_RESPONSE_NATIVE_ABI_OFFSET) != NATIVE_ABI
            || h(&b, INFO_RESPONSE_RUNTIME_CONTRACT_OFFSET) != RUNTIME_CONTRACT
        {
            return Err("incompatible controller contract".into());
        }
        Ok(b)
    }
}
fn show_info(b: &[u8]) {
    println!("{{\"protocol\":{},\"capabilities\":{},\"commands\":{},\"transfer_id\":{},\"next_offset\":{},\"remaining_ms\":{},\"slots\":[{{\"base\":{},\"state\":{},\"generation\":{}}},{{\"base\":{},\"state\":{},\"generation\":{}}}]}}",
        h(b,INFO_RESPONSE_PROTOCOL_OFFSET),u(b,INFO_RESPONSE_CAPABILITIES_OFFSET),u(b,INFO_RESPONSE_COMMAND_MASK_OFFSET),u(b,INFO_RESPONSE_TRANSFER_ID_OFFSET),u(b,INFO_RESPONSE_NEXT_OFFSET_OFFSET),u(b,INFO_RESPONSE_TRANSFER_REMAINING_MS_OFFSET),
        u(b,INFO_RESPONSE_SLOT_A_OFFSET),b[(INFO_RESPONSE_SLOT_A_OFFSET+SLOT_STATE_OFFSET) as usize],u(b,INFO_RESPONSE_SLOT_A_OFFSET+SLOT_GENERATION_OFFSET),
        u(b,INFO_RESPONSE_SLOT_B_OFFSET),b[(INFO_RESPONSE_SLOT_B_OFFSET+SLOT_STATE_OFFSET) as usize],u(b,INFO_RESPONSE_SLOT_B_OFFSET+SLOT_GENERATION_OFFSET));
}
fn show_status(b: &[u8]) {
    println!("{{\"active_generation\":{},\"scan\":{},\"execution\":{},\"outcome\":{},\"requested_generation\":{},\"pending_generation\":{},\"fault\":{},\"last_scan_us\":{},\"max_scan_us\":{},\"jitter_us\":{},\"missed_releases\":{}}}",
        u(b,1),wide(b,5),b[13],b[14],u(b,17),u(b,21),u(b,25),u(b,29),u(b,33),u(b,37) as i32,wide(b,41));
}
fn monitor(serial: &mut Serial, info: &[u8]) -> Result<()> {
    if u(info, INFO_RESPONSE_COMMAND_MASK_OFFSET) & (1 << (CMD_READ_TAGS - 1)) == 0 {
        return Err("controller does not support tag snapshots".into());
    }
    let mut generation = 0u32;
    let mut scan = 0u64;
    let mut first = 0u8;
    let mut total = None;
    let mut records = Vec::new();
    loop {
        let mut request = generation.to_le_bytes().to_vec();
        request.extend_from_slice(&scan.to_le_bytes());
        request.extend_from_slice(&[first, TAG_PAGE_LIMIT as u8]);
        let b = serial.request(CMD_READ_TAGS, &request, 0)?;
        if b.len() < READ_TAGS_RESPONSE_BYTES as usize {
            return Err("short tag response".into());
        }
        let count = b[14];
        if count == 0
            || count > TAG_PAGE_LIMIT as u8
            || b[13] != first
            || b[15] > TAG_LIMIT as u8
            || first as u16 + count as u16 > b[15] as u16
            || b.len()
                != READ_TAGS_RESPONSE_BYTES as usize + count as usize * TAG_VALUE_BYTES as usize
            || u(&b, 1) == 0
            || wide(&b, 5) == 0
            || (scan != 0 && (u(&b, 1) != generation || wide(&b, 5) != scan))
            || total.is_some_and(|n| n != b[15])
        {
            return Err("inconsistent tag snapshot".into());
        }
        generation = u(&b, 1);
        scan = wide(&b, 5);
        total = Some(b[15]);
        for tag in b[16..].chunks_exact(TAG_VALUE_BYTES as usize) {
            let end = tag[..32]
                .iter()
                .position(|&c| c == 0)
                .ok_or("invalid tag name")?;
            if end == 0
                || !tag[..end].iter().enumerate().all(|(i, c)| {
                    c.is_ascii_alphabetic() || *c == b'_' || (i > 0 && c.is_ascii_digit())
                })
                || tag[end..32].iter().any(|&c| c != 0)
                || ![TYPE_BOOL as u8, TYPE_DINT as u8].contains(&tag[32])
                || !(1..=3).contains(&tag[33])
            {
                return Err("invalid tag metadata".into());
            }
            let value = u(tag, TAG_VALUE_VALUE_OFFSET);
            let value = if tag[32] == TYPE_BOOL as u8 {
                if value > 1 {
                    return Err("invalid BOOL value".into());
                }
                (value != 0).to_string()
            } else {
                (value as i32).to_string()
            };
            records.push(format!(
                "{{\"name\":\"{}\",\"type\":{},\"class\":{},\"binding\":{},\"value\":{}}}",
                std::str::from_utf8(&tag[..end]).map_err(|_| "invalid tag name")?,
                tag[32],
                tag[33],
                h(tag, 34),
                value
            ));
        }
        first += count;
        if first == b[15] {
            break;
        }
    }
    println!(
        "{{\"generation\":{generation},\"scan\":{scan},\"tags\":[{}]}}",
        records.join(",")
    );
    Ok(())
}
fn run() -> Result<()> {
    let args: Vec<_> = env::args().skip(1).collect();
    if args.first().is_some_and(|s| s == "--help") {
        println!("plctool DEVICE info|status|update-status|monitor|rollback|download PACKAGE.tplc|activate GENERATION\n115200 8N1 local serial. Download ends at READY; activate is explicit.");
        return Ok(());
    }
    if args.len() < 2 {
        return Err(
            "usage: plctool DEVICE info|status|update-status|monitor|rollback|download FILE|activate GENERATION".into(),
        );
    }
    let command = args[1].as_str();
    let expected = if ["info", "status", "monitor", "rollback", "update-status"].contains(&command)
    {
        2
    } else if ["download", "activate"].contains(&command) {
        3
    } else {
        return Err("unknown command".into());
    };
    if args.len() != expected {
        return Err("wrong argument count".into());
    }
    // Validate the local file before touching a controller.
    let package = if command == "download" {
        let b = fs::read(&args[2]).map_err(|e| e.to_string())?;
        if b.len() < PACKAGE_BYTES as usize
            || b.len() > PACKAGE_BYTES_MAX as usize
            || u(&b, PACKAGE_MAGIC_OFFSET) != PACKAGE_MAGIC
            || u(&b, PACKAGE_TOTAL_BYTES_OFFSET) as usize != b.len()
            || u(&b, PACKAGE_PACKAGE_CRC_OFFSET) != crc32(&b, 64..68)
        {
            return Err("invalid package length/magic/CRC".into());
        }
        Some(b)
    } else {
        None
    };
    let mut serial = Serial::open(&args[0])?;
    let info = serial.info()?;
    match command {
        "info" => show_info(&info),
        "update-status" => {
            let b = serial.request(CMD_GET_UPDATE_STATUS, &[], GET_UPDATE_STATUS_RESPONSE_BYTES)?;
            println!("{{\"kind\":{},\"phase\":{},\"outcome\":{},\"source_generation\":{},\"requested_generation\":{},\"failed_generation\":{},\"first_fault\":{},\"recovery_fault\":{},\"line\":{},\"column\":{},\"failed_scan\":{},\"completed_generation\":{},\"completed_scan\":{}}}",
                b[1],b[2],b[3],u(&b,5),u(&b,9),u(&b,13),u(&b,17),u(&b,21),u(&b,25),u(&b,29),wide(&b,33),u(&b,41),wide(&b,45));
        }
        "monitor" => monitor(&mut serial, &info)?,
        "status" => show_status(&serial.request(CMD_GET_STATUS, &[], GET_STATUS_RESPONSE_BYTES)?),
        "download" => {
            if u(&info, INFO_RESPONSE_CAPABILITIES_OFFSET) & CAP_UNSIGNED_LAB == 0 {
                return Err("controller disallows unsigned lab images".into());
            }
            if u(&info, INFO_RESPONSE_TRANSFER_ID_OFFSET) != 0 {
                return Err(
                    "transfer already in progress; inspect info and wait for expiry".into(),
                );
            }
            let b = package.unwrap();
            let base = u(&b, PACKAGE_LINK_BASE_OFFSET);
            let mut chosen = None;
            for at in [INFO_RESPONSE_SLOT_A_OFFSET, INFO_RESPONSE_SLOT_B_OFFSET] {
                let state = u32::from(info[(at + SLOT_STATE_OFFSET) as usize]);
                if state == SLOT_PENDING {
                    return Err("activation pending".into());
                }
                if state == SLOT_EMPTY {
                    chosen = Some(u(&info, at));
                    break;
                }
                if [SLOT_READY, SLOT_PREVIOUS].contains(&state) {
                    chosen = Some(u(&info, at));
                }
            }
            if chosen != Some(base) {
                return Err(format!("package is for {base:#x}; available slot is {chosen:?}. Build for that slot first."));
            }
            let begin = serial.request(
                CMD_DOWNLOAD_BEGIN,
                &(b.len() as u32).to_le_bytes(),
                DOWNLOAD_BEGIN_RESPONSE_BYTES,
            )?;
            let id = u(&begin, 1);
            if u(&begin, 5) != base {
                return Err("reservation changed; transfer left to expire".into());
            }
            for (i, chunk) in b.chunks(CHUNK_BYTES_MAX as usize).enumerate() {
                let offset = i * CHUNK_BYTES_MAX as usize;
                let mut p = id.to_le_bytes().to_vec();
                p.extend_from_slice(&(offset as u32).to_le_bytes());
                p.extend_from_slice(chunk);
                let mut success = false;
                for attempt in 0..3 {
                    serial.send(CMD_DOWNLOAD_CHUNK as u8, &p)?;
                    match serial.response(
                        CMD_DOWNLOAD_CHUNK as u8,
                        DOWNLOAD_CHUNK_RESPONSE_BYTES as usize,
                        Some((offset + chunk.len()) as u32),
                    ) {
                        Ok(_) => {
                            success = true;
                            break;
                        }
                        Err(e) if e.starts_with("timeout") && attempt < 2 => {}
                        Err(e) => return Err(e),
                    }
                }
                if !success {
                    return Err("chunk not acknowledged".into());
                }
            }
            let end = serial.request(
                CMD_DOWNLOAD_END,
                &id.to_le_bytes(),
                DOWNLOAD_END_RESPONSE_BYTES,
            )?;
            println!(
                "{{\"ready_generation\":{},\"base\":{},\"bytes\":{}}}",
                u(&end, 1),
                base,
                b.len()
            );
        }
        "activate" | "rollback" => {
            let generation = if command == "activate" {
                let generation: u32 = args[2].parse().map_err(|_| "invalid generation")?;
                if ![INFO_RESPONSE_SLOT_A_OFFSET, INFO_RESPONSE_SLOT_B_OFFSET]
                    .iter()
                    .any(|&at| {
                        u(&info, at + SLOT_GENERATION_OFFSET) == generation
                            && info[(at + SLOT_STATE_OFFSET) as usize] == SLOT_READY as u8
                    })
                {
                    return Err("generation is not READY in current session".into());
                }
                serial.request(
                    CMD_ACTIVATE,
                    &generation.to_le_bytes(),
                    ACTIVATE_RESPONSE_BYTES,
                )?;
                generation
            } else {
                if u(&info, INFO_RESPONSE_CAPABILITIES_OFFSET) & CAP_ROLLBACK == 0 {
                    return Err("controller does not support rollback".into());
                }
                u(
                    &serial.request(CMD_ROLLBACK, &[], ROLLBACK_RESPONSE_BYTES)?,
                    1,
                )
            };
            let deadline = Instant::now() + Duration::from_secs(3);
            loop {
                let s = serial.request(CMD_GET_STATUS, &[], GET_STATUS_RESPONSE_BYTES)?;
                if u(&s, 17) == generation && u(&s, 21) == 0 && s[14] != OUTCOME_PENDING as u8 {
                    show_status(&s);
                    if u(&s, 1) != generation
                        || s[14] != OUTCOME_RUNNING as u8
                        || s[13] != EXEC_RUNNING as u8
                    {
                        return Err(
                            "update failed or automatically rolled back; inspect update-status"
                                .into(),
                        );
                    }
                    break;
                }
                if Instant::now() >= deadline {
                    return Err("activation outcome uncertain; inspect status".into());
                }
                std::thread::sleep(Duration::from_millis(10));
            }
        }
        _ => unreachable!(),
    }
    Ok(())
}
fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("{e}");
            ExitCode::FAILURE
        }
    }
}
