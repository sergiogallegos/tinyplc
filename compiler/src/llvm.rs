//! Lower typed PLC IR to textual LLVM IR, without LLVM bindings. Working tag values commit only on success; division guards preserve PLC semantics under optimization.
//! Normative backend reference: https://llvm.org/docs/LangRef.html
//! In particular, sdiv requires guards for zero and signed overflow; PLC wrapping
//! arithmetic must not acquire LLVM nsw/nuw promises. See docs/references.md.

use crate::{ir::*, Abi, Span};
use std::fmt::Write;

struct Emitter<'a> {
    program: &'a Program,
    abi: Abi,
    text: String,
    next: usize,
}
impl Emitter<'_> {
    fn line(&mut self, line: impl AsRef<str>) {
        writeln!(self.text, "  {}", line.as_ref()).unwrap();
    }
    fn label(&mut self, label: &str) {
        writeln!(self.text, "{label}:").unwrap();
    }
    fn fresh(&mut self) -> usize {
        let id = self.next;
        self.next += 1;
        id
    }
    fn value(&mut self, instruction: impl AsRef<str>) -> String {
        let name = format!("%v{}", self.fresh());
        self.line(format!("{name} = {}", instruction.as_ref()));
        name
    }
    fn fault(&mut self, code: u32, span: Span) {
        self.line(format!("store i32 {}, ptr %diag, align 4", span.line));
        self.line(format!("store i32 {}, ptr %diag_col, align 4", span.column));
        for (index, tag) in self.program.tags.iter().enumerate() {
            if self.abi == Abi::ResearchV1 && tag.kind == Class::Output {
                self.line(format!("store i32 0, ptr %p{index}, align 4"));
            }
        }
        self.line(format!("ret i32 {code}"));
    }
    fn expression(&mut self, root: usize) -> String {
        let mut pending = vec![(root, false)];
        let mut values: Vec<String> = Vec::new();
        while let Some((id, visited)) = pending.pop() {
            let expr = &self.program.expressions[id];
            if !visited {
                match expr.kind {
                    ExprKind::Unary(_, child) => {
                        pending.push((id, true));
                        pending.push((child, false));
                        continue;
                    }
                    ExprKind::Binary(_, left, right) => {
                        pending.push((id, true));
                        pending.push((right, false));
                        pending.push((left, false));
                        continue;
                    }
                    _ => {}
                }
            }
            let result = match expr.kind {
                ExprKind::Constant(bits) => (bits as i32).to_string(),
                ExprKind::Load(index) => self.value(format!("load i32, ptr %w{index}, align 4")),
                ExprKind::Unary(op, _) => {
                    let value = values.pop().unwrap();
                    match op {
                        Unary::Plus => value,
                        Unary::Neg => self.value(format!("sub i32 0, {value}")),
                        Unary::Not => self.value(format!("xor i32 {value}, 1")),
                    }
                }
                ExprKind::Binary(op, _, _) => {
                    let right = values.pop().unwrap();
                    let left = values.pop().unwrap();
                    match op {
                        Binary::Div => {
                            let zero = self.value(format!("icmp eq i32 {right}, 0"));
                            let block = self.fresh();
                            self.line(format!(
                                "br i1 {zero}, label %div_fault{block}, label %div_ok{block}"
                            ));
                            self.label(&format!("div_fault{block}"));
                            self.fault(5, expr.span);
                            self.label(&format!("div_ok{block}"));
                            // Never execute LLVM sdiv with INT_MIN/-1: its overflow is UB.
                            let min = self.value(format!("icmp eq i32 {left}, -2147483648"));
                            let neg = self.value(format!("icmp eq i32 {right}, -1"));
                            let overflow = self.value(format!("and i1 {min}, {neg}"));
                            let divisor =
                                self.value(format!("select i1 {overflow}, i32 1, i32 {right}"));
                            self.value(format!("sdiv i32 {left}, {divisor}"))
                        }
                        Binary::Eq
                        | Binary::Ne
                        | Binary::Lt
                        | Binary::Gt
                        | Binary::Le
                        | Binary::Ge => {
                            let predicate = match op {
                                Binary::Eq => "eq",
                                Binary::Ne => "ne",
                                Binary::Lt => "slt",
                                Binary::Gt => "sgt",
                                Binary::Le => "sle",
                                _ => "sge",
                            };
                            let boolean =
                                self.value(format!("icmp {predicate} i32 {left}, {right}"));
                            self.value(format!("zext i1 {boolean} to i32"))
                        }
                        _ => {
                            let instruction = match op {
                                Binary::Add => "add",
                                Binary::Sub => "sub",
                                Binary::Mul => "mul",
                                Binary::And => "and",
                                Binary::Or => "or",
                                Binary::Xor => "xor",
                                _ => unreachable!(),
                            };
                            self.value(format!("{instruction} i32 {left}, {right}"))
                        }
                    }
                }
            };
            values.push(result);
        }
        values.pop().unwrap()
    }
    fn body(&mut self, statements: &[Statement]) {
        for statement in statements {
            match statement {
                Statement::Ton {
                    base,
                    clock,
                    input,
                    preset,
                } => {
                    let input = self.expression(*input);
                    let preset = self.expression(*preset);
                    let now = self.value(format!("load i32, ptr %w{clock}, align 4"));
                    let run = self.value(format!("load i32, ptr %w{}, align 4", base + 2));
                    let last = self.value(format!("load i32, ptr %w{}, align 4", base + 3));
                    let age = self.value(format!("load i32, ptr %w{}, align 4", base + 4));
                    let delta = self.value(format!("sub i32 {now}, {last}"));
                    let remaining = self.value(format!("sub i32 2147483647, {age}"));
                    let overflow = self.value(format!("icmp uge i32 {delta}, {remaining}"));
                    let sum = self.value(format!("add i32 {age}, {delta}"));
                    let sum =
                        self.value(format!("select i1 {overflow}, i32 2147483647, i32 {sum}"));
                    let running = self.value(format!("icmp ne i32 {run}, 0"));
                    let age = self.value(format!("select i1 {running}, i32 {sum}, i32 0"));
                    let enabled = self.value(format!("icmp ne i32 {input}, 0"));
                    let age = self.value(format!("select i1 {enabled}, i32 {age}, i32 0"));
                    let done = self.value(format!("icmp uge i32 {age}, {preset}"));
                    let elapsed = self.value(format!("select i1 {done}, i32 {preset}, i32 {age}"));
                    let q = self.value(format!("and i1 {enabled}, {done}"));
                    let q = self.value(format!("zext i1 {q} to i32"));
                    for (offset, value) in [(0, q), (1, elapsed), (2, input), (3, now), (4, age)] {
                        self.line(format!(
                            "store i32 {value}, ptr %w{}, align 4",
                            base + offset
                        ));
                    }
                }
                Statement::Assign { tag, expression } => {
                    let value = self.expression(*expression);
                    self.line(format!("store i32 {value}, ptr %w{tag}, align 4"));
                }
                Statement::If {
                    branches,
                    otherwise,
                } => {
                    let end = self.fresh();
                    for (condition, body) in branches {
                        let value = self.expression(*condition);
                        let boolean = self.value(format!("icmp ne i32 {value}, 0"));
                        let block = self.fresh();
                        self.line(format!(
                            "br i1 {boolean}, label %then{block}, label %else{block}"
                        ));
                        self.label(&format!("then{block}"));
                        self.body(body);
                        self.line(format!("br label %end{end}"));
                        self.label(&format!("else{block}"));
                    }
                    self.body(otherwise);
                    self.line(format!("br label %end{end}"));
                    self.label(&format!("end{end}"));
                }
            }
        }
    }
}

pub(crate) fn emit(program: &Program, abi: Abi) -> String {
    let count = program.tags.len();
    let mut e = Emitter { program, abi, text: format!("; tinyplc Rust frontend: PROGRAM {}\n; Research scan ABI v1; target selected by the LLVM driver.\n", program.name), next: 0 };
    if abi == Abi::NativeV2 {
        e.text = format!("; tinyplc Rust frontend: PROGRAM {}\n; Native scan ABI v2; separate input and working state.\n", program.name);
    }
    let version = if abi == Abi::NativeV2 { 2 } else { 1 };
    writeln!(
        e.text,
        "@tinyplc_abi_version = constant i32 {version}\n@tinyplc_tag_count = constant i32 {count}"
    )
    .unwrap();
    for (global, data) in [
        (
            "types",
            program.tags.iter().map(|t| t.ty as u8).collect::<Vec<_>>(),
        ),
        (
            "classes",
            program.tags.iter().map(|t| t.kind as u8).collect(),
        ),
    ] {
        let initializer = if data.is_empty() {
            "zeroinitializer".into()
        } else {
            format!(
                "[{}]",
                data.iter()
                    .map(|v| format!("i8 {v}"))
                    .collect::<Vec<_>>()
                    .join(", ")
            )
        };
        writeln!(
            e.text,
            "@tinyplc_tag_{global} = constant [{count} x i8] {initializer}"
        )
        .unwrap();
    }
    let names = program
        .tags
        .iter()
        .map(|tag| {
            let mut name = tag.name.clone();
            name.push_str(&"\\00".repeat(32 - tag.name.len()));
            format!("[32 x i8] c\"{name}\"")
        })
        .collect::<Vec<_>>();
    let names = if names.is_empty() {
        "zeroinitializer".into()
    } else {
        format!("[{}]", names.join(", "))
    };
    writeln!(
        e.text,
        "@tinyplc_tag_names = constant [{count} x [32 x i8]] {names}\n"
    )
    .unwrap();
    if abi == Abi::NativeV2 {
        e.text.push_str(
            "define i32 @tinyplc_scan(ptr %inputs, ptr %cells, i32 %count, ptr %diag) {\nentry:\n",
        );
    } else {
        e.text
            .push_str("define i32 @tinyplc_scan(ptr %cells, i32 %count, ptr %diag) {\nentry:\n");
    }
    e.line("%diag_col = getelementptr i32, ptr %diag, i32 1");
    e.line("store i32 0, ptr %diag, align 4");
    e.line("store i32 0, ptr %diag_col, align 4");
    let predicate = if abi == Abi::NativeV2 { "eq" } else { "uge" };
    let valid = e.value(format!("icmp {predicate} i32 %count, {count}"));
    e.line(format!("br i1 {valid}, label %prepare, label %bad_count"));
    e.label("bad_count");
    e.line("ret i32 4");
    e.label("prepare");
    // All pointers dominate every fault path. State is never committed early.
    for index in 0..count {
        let base = if abi == Abi::NativeV2 && program.tags[index].kind == Class::Input {
            "%inputs"
        } else {
            "%cells"
        };
        e.line(format!(
            "%p{index} = getelementptr i32, ptr {base}, i32 {index}"
        ));
        e.line(format!("%w{index} = alloca i32, align 4"));
        e.line(format!(
            "%initial{index} = load i32, ptr %p{index}, align 4"
        ));
        e.line(format!("store i32 %initial{index}, ptr %w{index}, align 4"));
    }
    for (index, tag) in program.tags.iter().enumerate() {
        if matches!(tag.ty, Type::Bool | Type::Time) {
            let maximum = if tag.ty == Type::Bool { 1 } else { i32::MAX };
            let valid = e.value(format!("icmp ule i32 %initial{index}, {maximum}"));
            e.line(format!(
                "br i1 {valid}, label %bool_ok{index}, label %bool_fault{index}"
            ));
            e.label(&format!("bool_fault{index}"));
            e.fault(if tag.ty == Type::Bool { 8 } else { 9 }, tag.span);
            e.label(&format!("bool_ok{index}"));
        }
    }
    e.body(&program.statements);
    for (index, tag) in program.tags.iter().enumerate() {
        if tag.kind != Class::Input {
            let value = e.value(format!("load i32, ptr %w{index}, align 4"));
            e.line(format!("store i32 {value}, ptr %p{index}, align 4"));
        }
    }
    e.line("ret i32 0");
    e.text.push_str("}\n");
    e.text
}
