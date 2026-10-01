//! ST subset -> positioned AST -> typed PLC IR -> textual LLVM IR.
//! No LLVM bindings or third-party crates are needed to emit IR.
//! Design reading: RuSTy (https://github.com/PLC-lang/rusty) and matiec
//! (https://github.com/sm1820/matiec). This is an independent implementation;
//! no source from those projects is incorporated. See docs/education.md and
//! docs/references.md at the repository root for lessons and acknowledgments.
pub mod ir;
mod lexer;
mod llvm;
mod parser;
mod semantic;

use std::fmt;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Span {
    pub line: usize,
    pub column: usize,
}

#[derive(Debug, Clone)]
pub struct Error {
    pub span: Span,
    pub message: String,
}
impl Error {
    pub(crate) fn new(span: Span, message: impl Into<String>) -> Self {
        Self {
            span,
            message: message.into(),
        }
    }
}
impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "{}:{}: {}",
            self.span.line, self.span.column, self.message
        )
    }
}
impl std::error::Error for Error {}

#[derive(Clone, Debug)]
pub struct Binding {
    pub name: String,
    pub ty: ir::Type,
    pub kind: ir::Class,
}

/// Explicit logical I/O bindings. Pin configuration belongs to the board port.
pub fn nucleo_f446re() -> Vec<Binding> {
    vec![
        Binding {
            name: "BTN".into(),
            ty: ir::Type::Bool,
            kind: ir::Class::Input,
        },
        Binding {
            name: "LED".into(),
            ty: ir::Type::Bool,
            kind: ir::Class::Output,
        },
    ]
}

pub fn analyze(source: &str, bindings: &[Binding]) -> Result<ir::Program, Error> {
    semantic::analyze(parser::parse(lexer::lex(source)?)?, bindings)
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Abi {
    ResearchV1,
    NativeV2,
}

pub fn compile(source: &str, bindings: &[Binding]) -> Result<String, Error> {
    compile_with_abi(source, bindings, Abi::ResearchV1)
}

pub fn compile_with_abi(source: &str, bindings: &[Binding], abi: Abi) -> Result<String, Error> {
    Ok(llvm::emit(&analyze(source, bindings)?, abi))
}
