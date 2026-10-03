//! Recursive-descent syntax parser. Expressions live in an arena: children precede parents, avoiding recursive destruction of long expression chains.

use crate::{
    ir::{Binary, Class, Tag, Type, Unary},
    lexer::{Kind, Token},
    Error,
};

pub(crate) enum AstExprKind {
    Constant(Type, u32),
    Name(String),
    Unary(Unary, usize),
    Binary(Binary, usize, usize),
}
pub(crate) struct AstExpr {
    pub kind: AstExprKind,
    pub token: Token,
}
pub(crate) enum AstStatement {
    Assign(Token, usize),
    Ton(Token, usize, usize),
    If(Vec<(usize, Vec<AstStatement>)>, Vec<AstStatement>),
}
pub(crate) struct Ast {
    pub name: String,
    pub tags: Vec<Tag>,
    pub timers: Vec<(Token, usize)>,
    pub expressions: Vec<AstExpr>,
    pub statements: Vec<AstStatement>,
}
struct Parser {
    tokens: Vec<Token>,
    pos: usize,
    expressions: Vec<AstExpr>,
    statements: usize,
}
impl Parser {
    fn token(&self) -> &Token {
        &self.tokens[self.pos]
    }
    fn bump(&mut self) -> Token {
        let t = self.token().clone();
        if t.kind != Kind::Eof {
            self.pos += 1;
        }
        t
    }
    fn take(&mut self, text: &str) -> Result<Token, Error> {
        if self.token().text != text {
            return Err(Error::new(
                self.token().span,
                format!("expected {text}, found {}", self.token().text),
            ));
        }
        Ok(self.bump())
    }
    fn ident(&mut self) -> Result<Token, Error> {
        if self.token().kind != Kind::Ident {
            return Err(Error::new(self.token().span, "expected identifier"));
        }
        Ok(self.bump())
    }
    fn accept(&mut self, text: &str) -> bool {
        if self.token().text == text {
            self.bump();
            true
        } else {
            false
        }
    }
    fn depth(&self, depth: usize) -> Result<(), Error> {
        if depth > 64 {
            Err(Error::new(self.token().span, "nesting exceeds 64 levels"))
        } else {
            Ok(())
        }
    }
    fn node(&mut self, kind: AstExprKind, token: Token) -> Result<usize, Error> {
        if self.expressions.len() >= 4096 {
            return Err(Error::new(token.span, "expression capacity exceeded"));
        }
        let id = self.expressions.len();
        self.expressions.push(AstExpr { kind, token });
        Ok(id)
    }
    fn expression(&mut self, minimum: u8, depth: usize) -> Result<usize, Error> {
        self.depth(depth)?;
        let token = self.bump();
        let mut left = match token.text.as_str() {
            "+" | "-" | "NOT" => {
                if token.text == "-"
                    && self.token().kind == Kind::Number
                    && self.token().text.trim_start_matches('0') == "2147483648"
                {
                    self.bump();
                    self.node(AstExprKind::Constant(Type::Dint, 0x80000000), token)?
                } else {
                    let op = match token.text.as_str() {
                        "+" => Unary::Plus,
                        "-" => Unary::Neg,
                        _ => Unary::Not,
                    };
                    let child = self.expression(8, depth + 1)?;
                    self.node(AstExprKind::Unary(op, child), token)?
                }
            }
            "(" => {
                let expr = self.expression(1, depth + 1)?;
                self.take(")")?;
                expr
            }
            "TRUE" | "FALSE" => {
                let value = u32::from(token.text == "TRUE");
                self.node(AstExprKind::Constant(Type::Bool, value), token)?
            }
            "T" | "TIME" if self.accept("#") => {
                let number = self.bump();
                let amount = number
                    .text
                    .parse::<u64>()
                    .ok()
                    .filter(|_| number.kind == Kind::Number)
                    .ok_or_else(|| Error::new(number.span, "expected nonnegative TIME integer"))?;
                let unit = self.bump();
                let scale = match unit.text.as_str() {
                    "MS" => 1,
                    "S" => 1000,
                    "M" => 60_000,
                    "H" => 3_600_000,
                    _ => return Err(Error::new(unit.span, "TIME unit must be ms, s, m, or h")),
                };
                let value = amount
                    .checked_mul(scale)
                    .filter(|v| *v <= i32::MAX as u64)
                    .ok_or_else(|| Error::new(token.span, "TIME literal out of range"))?;
                self.node(AstExprKind::Constant(Type::Time, value as u32), token)?
            }
            _ if token.kind == Kind::Number => {
                let digits = token.text.trim_start_matches('0');
                let value = if digits.is_empty() {
                    Some(0)
                } else {
                    digits.parse::<u32>().ok()
                };
                let value = value
                    .filter(|&v| v <= i32::MAX as u32)
                    .ok_or_else(|| Error::new(token.span, "DINT literal out of range"))?;
                self.node(AstExprKind::Constant(Type::Dint, value), token)?
            }
            _ if token.kind == Kind::Ident => {
                let mut name = token.text.clone();
                if self.accept(".") {
                    name.push('.');
                    name.push_str(&self.ident()?.text);
                }
                self.node(AstExprKind::Name(name), token)?
            }
            _ => return Err(Error::new(token.span, "expected expression")),
        };
        while let Some((op, precedence)) = Binary::parse(&self.token().text) {
            if precedence < minimum {
                break;
            }
            let token = self.bump();
            let right = self.expression(precedence + 1, depth + 1)?;
            left = self.node(AstExprKind::Binary(op, left, right), token)?;
        }
        Ok(left)
    }
    fn body(&mut self, depth: usize) -> Result<Vec<AstStatement>, Error> {
        self.depth(depth)?;
        let mut body = Vec::new();
        while self.token().kind != Kind::Eof
            && !["ELSIF", "ELSE", "END_IF", "END_PROGRAM"].contains(&self.token().text.as_str())
        {
            self.statements += 1;
            if self.statements > 4096 {
                return Err(Error::new(self.token().span, "statement capacity exceeded"));
            }
            if self.accept("IF") {
                let mut branches = Vec::new();
                loop {
                    let condition = self.expression(1, 0)?;
                    self.take("THEN")?;
                    branches.push((condition, self.body(depth + 1)?));
                    if !self.accept("ELSIF") {
                        break;
                    }
                }
                let otherwise = if self.accept("ELSE") {
                    self.body(depth + 1)?
                } else {
                    Vec::new()
                };
                self.take("END_IF")?;
                self.take(";")?;
                body.push(AstStatement::If(branches, otherwise));
            } else {
                let name = self.ident()?;
                if self.accept("(") {
                    let mut input = None;
                    let mut preset = None;
                    loop {
                        let parameter = self.ident()?;
                        self.take(":=")?;
                        let value = self.expression(1, 0)?;
                        let field = match parameter.text.as_str() {
                            "IN" => &mut input,
                            "PT" => &mut preset,
                            _ => {
                                return Err(Error::new(
                                    parameter.span,
                                    "TON parameter must be IN or PT",
                                ))
                            }
                        };
                        if field.replace(value).is_some() {
                            return Err(Error::new(parameter.span, "duplicate TON parameter"));
                        }
                        if !self.accept(",") {
                            break;
                        }
                    }
                    self.take(")")?;
                    self.take(";")?;
                    body.push(AstStatement::Ton(
                        name.clone(),
                        input.ok_or_else(|| Error::new(name.span, "TON requires IN"))?,
                        preset.ok_or_else(|| Error::new(name.span, "TON requires PT"))?,
                    ));
                    continue;
                }
                self.take(":=")?;
                let expression = self.expression(1, 0)?;
                self.take(";")?;
                body.push(AstStatement::Assign(name, expression));
            }
        }
        Ok(body)
    }
}
pub(crate) fn parse(tokens: Vec<Token>) -> Result<Ast, Error> {
    let mut p = Parser {
        tokens,
        pos: 0,
        expressions: Vec::new(),
        statements: 0,
    };
    p.take("PROGRAM")?;
    let name = p.ident()?.text;
    let mut tags = Vec::new();
    let mut timers = Vec::new();
    while ["VAR", "VAR_INPUT", "VAR_OUTPUT"].contains(&p.token().text.as_str()) {
        let kind = match p.bump().text.as_str() {
            "VAR_INPUT" => Class::Input,
            "VAR_OUTPUT" => Class::Output,
            _ => Class::Var,
        };
        while p.token().text != "END_VAR" {
            let name = p.ident()?;
            if name.text.starts_with("__") {
                return Err(Error::new(name.span, "names beginning __ are reserved"));
            }
            if tags.iter().any(|t: &Tag| t.name == name.text)
                || timers
                    .iter()
                    .any(|(t, _): &(Token, usize)| t.text == name.text)
            {
                return Err(Error::new(
                    name.span,
                    format!("duplicate tag {}", name.text),
                ));
            }
            if tags.len() >= 64 {
                return Err(Error::new(name.span, "tag capacity exceeded"));
            }
            p.take(":")?;
            let type_token = p.bump();
            if type_token.text == "TON" {
                if kind != Class::Var || name.text.len() > 20 {
                    return Err(Error::new(
                        name.span,
                        "TON requires VAR and an instance name of at most 20 characters",
                    ));
                }
                p.take(";")?;
                timers.push((name.clone(), tags.len()));
                for (field, ty) in [
                    ("Q", Type::Bool),
                    ("ET", Type::Time),
                    ("RUN", Type::Bool),
                    ("LAST", Type::Dint),
                    ("AGE", Type::Time),
                ] {
                    tags.push(Tag {
                        name: format!("__T_{}_{}", name.text, field),
                        ty,
                        kind: Class::Timer,
                        span: name.span,
                    });
                }
                continue;
            }
            let ty = match type_token.text.as_str() {
                "BOOL" => Type::Bool,
                "DINT" => Type::Dint,
                "TIME" => Type::Time,
                _ => {
                    return Err(Error::new(
                        type_token.span,
                        "expected BOOL, DINT, TIME, or TON",
                    ))
                }
            };
            p.take(";")?;
            tags.push(Tag {
                name: name.text,
                ty,
                kind,
                span: name.span,
            });
        }
        p.take("END_VAR")?;
    }
    if let Some((timer, _)) = timers.first() {
        tags.push(Tag {
            name: "__CLOCK_MS".into(),
            ty: Type::Dint,
            kind: Class::Input,
            span: timer.span,
        });
    }
    if tags.len() > 64 {
        return Err(Error::new(
            p.token().span,
            "expanded tag capacity exceeded (64 cells)",
        ));
    }
    let statements = p.body(0)?;
    p.take("END_PROGRAM")?;
    if p.token().kind != Kind::Eof {
        return Err(Error::new(p.token().span, "expected end of file"));
    }
    Ok(Ast {
        name,
        tags,
        timers,
        expressions: p.expressions,
        statements,
    })
}
