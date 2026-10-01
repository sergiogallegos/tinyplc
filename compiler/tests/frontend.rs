use tinyplc_compiler::{
    analyze, compile,
    ir::{Class, ExprKind, Type},
    nucleo_f446re,
};

fn source(body: &str) -> String {
    format!("PROGRAM Main\nVAR x : DINT; y : DINT; b : BOOL; END_VAR\n{body}\nEND_PROGRAM")
}
#[test]
fn typed_ir_and_canonical_tags() {
    let p = analyze(&source("x := 2 + 3 * 4; b := x = 14;"), &[]).unwrap();
    assert_eq!(
        p.tags.iter().map(|t| t.name.as_str()).collect::<Vec<_>>(),
        ["X", "Y", "B"]
    );
    assert_eq!(p.tags[2].ty, Type::Bool);
    assert_eq!(p.tags[0].kind, Class::Var);
    assert_eq!(p.expressions.last().unwrap().ty, Type::Bool);
    assert!(matches!(p.expressions[0].kind, ExprKind::Constant(2)));
}
#[test]
fn positioned_errors() {
    let e = compile(&source("  missing := 1;"), &[]).unwrap_err();
    assert_eq!((e.span.line, e.span.column), (3, 3));
    assert!(e.message.contains("unknown tag MISSING"));
    let e = compile(
        "PROGRAM Main\n(* first\nsecond *)\nVAR x : DINT; END_VAR\nx := @; END_PROGRAM",
        &[],
    )
    .unwrap_err();
    assert_eq!((e.span.line, e.span.column), (5, 6));
}
#[test]
fn semantic_rejections() {
    for body in [
        "x := TRUE;",
        "b := 1 AND 2;",
        "b := TRUE < FALSE;",
        "b := TRUE = 1;",
        "x := NOT 1;",
        "b := +TRUE;",
        "IF x THEN END_IF;",
        "x := missing;",
    ] {
        assert!(compile(&source(body), &[]).is_err(), "{body}");
    }
    for declarations in [
        "VAR x: BOOL; X: DINT; END_VAR",
        "VAR_INPUT LED: BOOL; END_VAR",
        "VAR_OUTPUT LED: DINT; END_VAR",
        "VAR_INPUT OTHER: BOOL; END_VAR",
    ] {
        assert!(compile(
            &format!("PROGRAM Main {declarations} END_PROGRAM"),
            &nucleo_f446re()
        )
        .is_err());
    }
    assert!(compile(
        "PROGRAM Main VAR_INPUT BTN: BOOL; END_VAR BTN := FALSE; END_PROGRAM",
        &nucleo_f446re()
    )
    .unwrap_err()
    .message
    .contains("input"));
}
#[test]
fn syntax_rejections() {
    for text in [
        source("x := 1"),
        source("IF TRUE THEN x := 1;"),
        source("WHILE TRUE DO END_WHILE;"),
        source("x := 1.5;"),
        source("x := 1;") + " junk",
        "PROGRAM Main (* missing".into(),
        "PROGRAM Main (* (* *) END_PROGRAM".into(),
        "PROGRAM Main VAR café: BOOL; END_VAR END_PROGRAM".into(),
        "PROGRAM Main VAR x: REAL; END_VAR END_PROGRAM".into(),
    ] {
        assert!(compile(&text, &[]).is_err(), "{text}");
    }
}
#[test]
fn literal_limits() {
    assert!(compile(&source("x := -2147483648; y := - -2147483648;"), &[]).is_ok());
    for literal in ["2147483648".into(), "-2147483649".into(), "9".repeat(5000)] {
        assert!(compile(&source(&format!("x := {literal};")), &[])
            .unwrap_err()
            .message
            .contains("out of range"));
    }
    assert!(compile(&source(&format!("x := {}1;", "0".repeat(5000))), &[]).is_ok());
}
#[test]
fn resource_limits() {
    let declarations = (0..64).map(|i| format!("v{i}: DINT;")).collect::<String>();
    assert!(compile(
        &format!("PROGRAM Main VAR {declarations} END_VAR END_PROGRAM"),
        &[]
    )
    .is_ok());
    assert!(compile(
        &format!("PROGRAM Main VAR {declarations} extra: DINT; END_VAR END_PROGRAM"),
        &[]
    )
    .unwrap_err()
    .message
    .contains("tag capacity"));
    assert!(compile(
        &source(&format!("x := {}1{};", "(".repeat(70), ")".repeat(70))),
        &[]
    )
    .unwrap_err()
    .message
    .contains("nesting"));
    assert!(compile(
        &source(&format!(
            "{}{}",
            "IF TRUE THEN ".repeat(70),
            "END_IF;".repeat(70)
        )),
        &[]
    )
    .unwrap_err()
    .message
    .contains("nesting"));
    assert!(compile(&" ".repeat(1024 * 1024 + 1), &[])
        .unwrap_err()
        .message
        .contains("1 MiB"));
    assert!(compile(
        &source(&format!("x := {};", vec!["1"; 2000].join("+"))),
        &[]
    )
    .is_ok());
    assert!(compile(
        &source(&format!("x := {};", vec!["1"; 3000].join("+"))),
        &[]
    )
    .unwrap_err()
    .message
    .contains("expression capacity"));
}
#[test]
fn nested_control_flow_and_comments() {
    let text = "program main (* comment *) var x: dint; end_var IF x = 0 THEN IF TRUE THEN x := 2; ELSE END_IF; ELSIF x = 1 THEN ELSE x := 3; END_IF; end_program";
    assert!(compile(text, &[]).is_ok());
    assert!(compile("PROGRAM Empty END_PROGRAM", &[]).is_ok());
}
#[test]
fn wrapping_and_guarded_division_ir() {
    let ir = compile(&source("x := x + y; x := -x; x := x / y;"), &[]).unwrap();
    assert!(!ir.contains(" nsw "));
    assert!(!ir.contains(" nuw "));
    assert!(ir.contains("sdiv i32"));
    assert!(ir.contains("select i1"));
    assert!(ir.contains("div_fault"));
    assert!(ir.contains("ret i32 5"));
    assert!(!ir.contains("target triple"));
}
#[test]
fn golden_button_ir() {
    let text = include_str!("../../examples/button_led.st");
    assert_eq!(
        compile(text, &nucleo_f446re()).unwrap(),
        include_str!("button_led.ll")
    );
}
