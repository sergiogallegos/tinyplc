//! Positioned, handwritten lexer for the small ST subset. Resource limits keep malformed source bounded.

use crate::{Error, Span};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Kind {
    Ident,
    Number,
    Other,
    Eof,
}
#[derive(Clone, Debug)]
pub(crate) struct Token {
    pub text: String,
    pub kind: Kind,
    pub span: Span,
}
const KEYWORDS: &[&str] = &[
    "PROGRAM",
    "END_PROGRAM",
    "VAR_INPUT",
    "VAR_OUTPUT",
    "VAR",
    "END_VAR",
    "BOOL",
    "DINT",
    "IF",
    "THEN",
    "ELSIF",
    "ELSE",
    "END_IF",
    "TRUE",
    "FALSE",
    "AND",
    "OR",
    "XOR",
    "NOT",
];

pub(crate) fn lex(source: &str) -> Result<Vec<Token>, Error> {
    if source.len() > 1024 * 1024 {
        return Err(Error::new(
            Span { line: 1, column: 1 },
            "source exceeds 1 MiB",
        ));
    }
    let chars: Vec<char> = source.chars().collect();
    let (mut pos, mut line, mut column) = (0, 1, 1);
    let mut tokens = Vec::new();
    while pos < chars.len() {
        let span = Span { line, column };
        let start = pos;
        let c = chars[pos];
        if c == '(' && chars.get(pos + 1) == Some(&'*') {
            pos += 2;
            loop {
                if pos + 1 >= chars.len() {
                    return Err(Error::new(span, "unterminated comment"));
                }
                if chars[pos] == '(' && chars[pos + 1] == '*' {
                    return Err(Error::new(span, "nested comments are unsupported"));
                }
                if chars[pos] == '*' && chars[pos + 1] == ')' {
                    pos += 2;
                    break;
                }
                pos += 1;
            }
        } else if " \t\r\n".contains(c) {
            pos += 1;
        } else {
            let kind = if c.is_ascii_alphabetic() || c == '_' {
                pos += 1;
                while pos < chars.len() && (chars[pos].is_ascii_alphanumeric() || chars[pos] == '_')
                {
                    pos += 1;
                }
                if pos - start > 31 {
                    return Err(Error::new(span, "identifier exceeds 31 characters"));
                }
                Kind::Ident
            } else if c.is_ascii_digit() {
                pos += 1;
                while pos < chars.len() && chars[pos].is_ascii_digit() {
                    pos += 1;
                }
                Kind::Number
            } else if ";:()+*/=<>-".contains(c) {
                pos += 1;
                if pos < chars.len()
                    && matches!(
                        (c, chars[pos]),
                        (':', '=') | ('<', '>') | ('<', '=') | ('>', '=')
                    )
                {
                    pos += 1;
                }
                Kind::Other
            } else {
                return Err(Error::new(span, format!("unexpected character {c:?}")));
            };
            let text: String = chars[start..pos]
                .iter()
                .collect::<String>()
                .to_ascii_uppercase();
            let kind = if KEYWORDS.contains(&text.as_str()) {
                Kind::Other
            } else {
                kind
            };
            tokens.push(Token { text, kind, span });
            if tokens.len() > 65536 {
                return Err(Error::new(span, "token capacity exceeded"));
            }
        }
        for &ch in &chars[start..pos] {
            if ch == '\n' {
                line += 1;
                column = 1;
            } else {
                column += 1;
            }
        }
    }
    tokens.push(Token {
        text: "end of file".into(),
        kind: Kind::Eof,
        span: Span { line, column },
    });
    Ok(tokens)
}
