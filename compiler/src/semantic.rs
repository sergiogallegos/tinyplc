//! Resolve names and check types before LLVM emission. This pass produces tag indices and typed expressions; code generation never guesses source types.
//! Related-work reading: matiec's ordered semantic passes and RuSTy's validation
//! stages; see docs/education.md. Our two-type subset uses its own smaller pass.

use crate::{
    ir::*,
    parser::{Ast, AstExprKind, AstStatement},
    Binding, Error,
};
use std::collections::HashMap;

pub(crate) fn analyze(ast: Ast, bindings: &[Binding]) -> Result<Program, Error> {
    let mut symbols = HashMap::new();
    for (index, tag) in ast.tags.iter().enumerate() {
        if symbols.insert(tag.name.clone(), index).is_some() {
            return Err(Error::new(tag.span, format!("duplicate tag {}", tag.name)));
        }
        if tag.kind != Class::Var
            && !bindings.iter().any(|b| {
                b.name.eq_ignore_ascii_case(&tag.name) && b.ty == tag.ty && b.kind == tag.kind
            })
        {
            return Err(Error::new(
                tag.span,
                format!("unsupported I/O binding {}", tag.name),
            ));
        }
    }
    let mut expressions: Vec<Expr> = Vec::new();
    for expression in ast.expressions {
        let span = expression.token.span;
        let mismatch = || {
            Error::new(
                span,
                format!("{} operand type mismatch", expression.token.text),
            )
        };
        let (kind, ty) = match expression.kind {
            AstExprKind::Constant(ty, bits) => (ExprKind::Constant(bits), ty),
            AstExprKind::Name(name) => {
                let index = *symbols
                    .get(&name)
                    .ok_or_else(|| Error::new(span, format!("unknown tag {name}")))?;
                (ExprKind::Load(index), ast.tags[index].ty)
            }
            AstExprKind::Unary(op, child) => {
                let expected = if op == Unary::Not {
                    Type::Bool
                } else {
                    Type::Dint
                };
                if expressions[child].ty != expected {
                    return Err(mismatch());
                }
                (ExprKind::Unary(op, child), expected)
            }
            AstExprKind::Binary(op, left, right) => {
                let lt = expressions[left].ty;
                if lt != expressions[right].ty {
                    return Err(mismatch());
                }
                let result = match op {
                    Binary::Eq | Binary::Ne => Type::Bool,
                    Binary::And | Binary::Or | Binary::Xor => {
                        if lt != Type::Bool {
                            return Err(mismatch());
                        }
                        Type::Bool
                    }
                    _ => {
                        if lt != Type::Dint {
                            return Err(mismatch());
                        }
                        if matches!(op, Binary::Lt | Binary::Gt | Binary::Le | Binary::Ge) {
                            Type::Bool
                        } else {
                            Type::Dint
                        }
                    }
                };
                (ExprKind::Binary(op, left, right), result)
            }
        };
        expressions.push(Expr { kind, ty, span });
    }
    fn body(
        statements: Vec<AstStatement>,
        tags: &[Tag],
        expressions: &[Expr],
        symbols: &HashMap<String, usize>,
    ) -> Result<Vec<Statement>, Error> {
        statements
            .into_iter()
            .map(|statement| {
                Ok(match statement {
                    AstStatement::Assign(name, expression) => {
                        let tag = *symbols.get(&name.text).ok_or_else(|| {
                            Error::new(name.span, format!("unknown tag {}", name.text))
                        })?;
                        if tags[tag].kind == Class::Input {
                            return Err(Error::new(name.span, "cannot assign to input"));
                        }
                        if tags[tag].ty != expressions[expression].ty {
                            return Err(Error::new(name.span, "assignment type mismatch"));
                        }
                        Statement::Assign { tag, expression }
                    }
                    AstStatement::If(branches, otherwise) => {
                        let mut checked = Vec::new();
                        for (condition, statements) in branches {
                            if expressions[condition].ty != Type::Bool {
                                return Err(Error::new(
                                    expressions[condition].span,
                                    "IF condition must be BOOL",
                                ));
                            }
                            checked
                                .push((condition, body(statements, tags, expressions, symbols)?));
                        }
                        Statement::If {
                            branches: checked,
                            otherwise: body(otherwise, tags, expressions, symbols)?,
                        }
                    }
                })
            })
            .collect()
    }
    let statements = body(ast.statements, &ast.tags, &expressions, &symbols)?;
    Ok(Program {
        name: ast.name,
        tags: ast.tags,
        expressions,
        statements,
    })
}
