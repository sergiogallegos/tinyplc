//! Typed PLC IR. Expression arenas avoid recursive storage for long expressions.
use crate::Span;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum Type {
    Bool = 1,
    Dint = 2,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum Class {
    Input = 1,
    Output = 2,
    Var = 3,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Unary {
    Plus,
    Neg,
    Not,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Binary {
    Add,
    Sub,
    Mul,
    Div,
    And,
    Or,
    Xor,
    Eq,
    Ne,
    Lt,
    Gt,
    Le,
    Ge,
}
impl Binary {
    pub(crate) fn parse(text: &str) -> Option<(Self, u8)> {
        Some(match text {
            "OR" => (Self::Or, 1),
            "XOR" => (Self::Xor, 2),
            "AND" => (Self::And, 3),
            "=" => (Self::Eq, 4),
            "<>" => (Self::Ne, 4),
            "<" => (Self::Lt, 5),
            ">" => (Self::Gt, 5),
            "<=" => (Self::Le, 5),
            ">=" => (Self::Ge, 5),
            "+" => (Self::Add, 6),
            "-" => (Self::Sub, 6),
            "*" => (Self::Mul, 7),
            "/" => (Self::Div, 7),
            _ => return None,
        })
    }
}
#[derive(Clone, Debug)]
pub struct Tag {
    pub name: String,
    pub ty: Type,
    pub kind: Class,
    pub span: Span,
}
#[derive(Clone, Debug)]
pub enum ExprKind {
    Constant(u32),
    Load(usize),
    Unary(Unary, usize),
    Binary(Binary, usize, usize),
}
#[derive(Clone, Debug)]
pub struct Expr {
    pub kind: ExprKind,
    pub ty: Type,
    pub span: Span,
}
#[derive(Clone, Debug)]
pub enum Statement {
    Assign {
        tag: usize,
        expression: usize,
    },
    If {
        branches: Vec<(usize, Vec<Statement>)>,
        otherwise: Vec<Statement>,
    },
}
#[derive(Clone, Debug)]
pub struct Program {
    pub name: String,
    pub tags: Vec<Tag>,
    pub expressions: Vec<Expr>,
    pub statements: Vec<Statement>,
}
