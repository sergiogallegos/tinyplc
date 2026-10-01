use std::{env, fs, path::PathBuf, process::ExitCode};

fn run() -> Result<(), String> {
    let mut args = env::args().skip(1);
    let mut source = None;
    let mut output = None;
    let mut abi = tinyplc_compiler::Abi::ResearchV1;
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "-h" | "--help" => {
                println!("plcc SOURCE.st [-o OUTPUT.ll] [--abi 1|2]\nRust ST frontend -> LLVM IR (BOOL/DINT subset).\nBuilt-in logical board profile: nucleo_f446re (BTN input, LED output).\nNo options compile or run native code automatically.");
                return Ok(());
            }
            "--abi" => {
                abi = match args.next().as_deref() {
                    Some("1") => tinyplc_compiler::Abi::ResearchV1,
                    Some("2") => tinyplc_compiler::Abi::NativeV2,
                    _ => return Err("--abi requires 1 or 2".into()),
                };
            }
            "-o" | "--output" => {
                if output.is_some() {
                    return Err("output specified more than once".into());
                }
                output = Some(PathBuf::from(args.next().ok_or("missing output path")?));
            }
            _ if arg.starts_with('-') => return Err(format!("unknown option {arg}")),
            _ => {
                if source.is_some() {
                    return Err("expected one ST source file".into());
                }
                source = Some(PathBuf::from(arg));
            }
        }
    }
    let source = source.ok_or("usage: plcc SOURCE.st [-o OUTPUT.ll] [--abi 1|2]")?;
    let output = output.unwrap_or_else(|| source.with_extension("ll"));
    if source == output
        || (output.exists() && fs::canonicalize(&source).ok() == fs::canonicalize(&output).ok())
    {
        return Err("output must differ from source".into());
    }
    let text = fs::read_to_string(&source).map_err(|e| format!("{}: {e}", source.display()))?;
    let ir = tinyplc_compiler::compile_with_abi(&text, &tinyplc_compiler::nucleo_f446re(), abi)
        .map_err(|e| format!("{}:{e}", source.display()))?;
    fs::write(&output, ir).map_err(|e| format!("{}: {e}", output.display()))?;
    println!("{}", output.display());
    Ok(())
}
fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("{message}");
            ExitCode::FAILURE
        }
    }
}
