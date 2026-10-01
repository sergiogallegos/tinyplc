use std::{
    env, fs,
    path::{Path, PathBuf},
    process::{Command, ExitCode},
};
use tinyplc_contract::generated::{SLOT_A_BASE, SLOT_B_BASE};
struct Temp(PathBuf);
impl Drop for Temp {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}
fn temporary() -> Result<Temp, String> {
    for i in 0..1000 {
        let p = env::temp_dir().join(format!("tinyplc-pack-{}-{i}", std::process::id()));
        match fs::create_dir(&p) {
            Ok(()) => return Ok(Temp(p)),
            Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => {}
            Err(e) => return Err(e.to_string()),
        }
    }
    Err("cannot reserve temporary directory".into())
}
fn run_tool(tool: &str, args: &[&str], dir: &Path) -> Result<(), String> {
    let result = Command::new(tool)
        .args(args)
        .current_dir(dir)
        .output()
        .map_err(|e| format!("{tool}: {e}"))?;
    if !result.status.success() {
        return Err(format!(
            "{tool} failed: {}",
            String::from_utf8_lossy(&result.stderr)
        ));
    }
    Ok(())
}
fn run() -> Result<(), String> {
    let mut args = env::args().skip(1);
    let mut source = None;
    let mut output = None;
    let mut base = None;
    let mut clang = "clang".to_owned();
    let mut ld = "arm-none-eabi-ld".to_owned();
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--help" | "-h" => {
                println!("plcpack SOURCE.st --slot A|B -o OUTPUT.tplc [--clang TOOL] [--ld TOOL]\nBuilds unsigned lab ABI-2 native package on PC; never uploads or flashes.");
                return Ok(());
            }
            "--slot" => {
                if base.is_some() {
                    return Err("duplicate slot".into());
                }
                base = Some(match args.next().as_deref() {
                    Some("A") => SLOT_A_BASE,
                    Some("B") => SLOT_B_BASE,
                    _ => return Err("--slot requires A or B".into()),
                });
            }
            "-o" => {
                if output.is_some() {
                    return Err("duplicate output".into());
                }
                output = Some(PathBuf::from(args.next().ok_or("missing output")?));
            }
            "--clang" => clang = args.next().ok_or("missing clang")?,
            "--ld" => ld = args.next().ok_or("missing linker")?,
            _ if arg.starts_with('-') => return Err(format!("unknown option {arg}")),
            _ => {
                if source.is_some() {
                    return Err("expected one ST source".into());
                }
                source = Some(PathBuf::from(arg));
            }
        }
    }
    let source = source.ok_or("missing ST source (see --help)")?;
    let output = output.ok_or("missing -o OUTPUT.tplc")?;
    let base = base.ok_or("missing --slot")?;
    if source == output
        || (output.exists() && fs::canonicalize(&source).ok() == fs::canonicalize(&output).ok())
    {
        return Err("output must differ from source".into());
    }
    let source = fs::read_to_string(source).map_err(|e| e.to_string())?;
    let ir = tinyplc_compiler::compile_with_abi(
        &source,
        &tinyplc_compiler::nucleo_f446re(),
        tinyplc_compiler::Abi::NativeV2,
    )
    .map_err(|e| e.to_string())?;
    let temp = temporary()?;
    fs::write(temp.0.join("program.ll"), ir).map_err(|e| e.to_string())?;
    fs::write(
        temp.0.join("program.ld"),
        include_str!("../../port/nucleo_f446re/native/program.ld"),
    )
    .map_err(|e| e.to_string())?;
    run_tool(
        &clang,
        &[
            "--target=thumbv7em-none-eabi",
            "-mcpu=cortex-m4",
            "-mthumb",
            "-mfloat-abi=soft",
            "-ffreestanding",
            "-O2",
            "-c",
            "program.ll",
            "-o",
            "program.o",
        ],
        &temp.0,
    )?;
    run_tool(
        &ld,
        &[
            "--no-undefined",
            "--fatal-warnings",
            &format!("--defsym=TINYPLC_CODE_BASE={base}"),
            "-T",
            "program.ld",
            "program.o",
            "-o",
            "program.elf",
        ],
        &temp.0,
    )?;
    let elf = fs::read(temp.0.join("program.elf")).map_err(|e| e.to_string())?;
    let package = tinyplc_packager::package_elf(&elf, base)?;
    fs::write(&output, &package).map_err(|e| e.to_string())?;
    println!(
        "{}: {} bytes, slot base {base:#010x}, unsigned lab",
        output.display(),
        package.len()
    );
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
