export type TokenType =
  | 'keyword'
  | 'string'
  | 'comment'
  | 'number'
  | 'builtin'
  | 'function'
  | 'decorator'
  | 'operator'
  | 'plain'

export interface Token {
  type: TokenType
  value: string
}

const PY_KEYWORDS = new Set([
  'def', 'class', 'return', 'if', 'elif', 'else', 'for', 'while', 'in', 'not',
  'and', 'or', 'is', 'None', 'True', 'False', 'import', 'from', 'as', 'with',
  'try', 'except', 'finally', 'raise', 'await', 'async', 'yield', 'lambda',
  'pass', 'break', 'continue', 'del', 'global', 'nonlocal', 'assert', 'match', 'case',
])

const PY_BUILTINS = new Set([
  'print', 'len', 'range', 'str', 'int', 'float', 'dict', 'list', 'set', 'tuple',
  'type', 'isinstance', 'super', 'self', 'cls', 'Exception', 'Decimal', 'dataclass',
  'field', 'Any', 'Mapping', 'Sequence',
])

const PY_RE =
  /(#[^\n]*)|("""[\s\S]*?"""|'''[\s\S]*?'''|"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*')|(@[\w.]+)|(\b\d+(?:\.\d+)?\b)|(\b[A-Za-z_]\w*\b)|([^\sA-Za-z0-9_"']+)|(\s+)|(.)/g

function highlightPython(code: string): Token[] {
  const tokens: Token[] = []
  let m: RegExpExecArray | null
  PY_RE.lastIndex = 0
  while ((m = PY_RE.exec(code)) !== null) {
    const [full, comment, str, deco, num, word, op, ws] = m
    if (comment !== undefined) tokens.push({ type: 'comment', value: comment })
    else if (str !== undefined) tokens.push({ type: 'string', value: str })
    else if (deco !== undefined) tokens.push({ type: 'decorator', value: deco })
    else if (num !== undefined) tokens.push({ type: 'number', value: num })
    else if (word !== undefined) {
      if (PY_KEYWORDS.has(word)) tokens.push({ type: 'keyword', value: word })
      else if (PY_BUILTINS.has(word)) tokens.push({ type: 'builtin', value: word })
      else {
        // function call heuristic: word followed by (
        const rest = code.slice(PY_RE.lastIndex)
        if (rest.startsWith('(')) tokens.push({ type: 'function', value: word })
        else tokens.push({ type: 'plain', value: word })
      }
    } else if (op !== undefined) tokens.push({ type: 'operator', value: op })
    else if (ws !== undefined) tokens.push({ type: 'plain', value: ws })
    else tokens.push({ type: 'plain', value: full })
  }
  return tokens
}

const BASH_RE =
  /(#[^\n]*)|("(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*')|(\b[A-Z_][A-Z0-9_]*(?==))|(--?[a-zA-Z][\w-]*)|(\s+)|([^\s"']+)/g

function highlightBash(code: string): Token[] {
  const tokens: Token[] = []
  let m: RegExpExecArray | null
  BASH_RE.lastIndex = 0
  let lineStart = true
  while ((m = BASH_RE.exec(code)) !== null) {
    const [full, comment, str, envVar, flag, ws, word] = m
    void full
    if (comment !== undefined) {
      tokens.push({ type: 'comment', value: comment })
      lineStart = false
    } else if (str !== undefined) {
      tokens.push({ type: 'string', value: str })
      lineStart = false
    } else if (envVar !== undefined) {
      tokens.push({ type: 'builtin', value: envVar })
      lineStart = false
    } else if (flag !== undefined) {
      tokens.push({ type: 'keyword', value: flag })
      lineStart = false
    } else if (ws !== undefined) {
      tokens.push({ type: 'plain', value: ws })
      if (ws.includes('\n')) lineStart = true
    } else if (word !== undefined) {
      if (lineStart) tokens.push({ type: 'function', value: word })
      else if (/^\d/.test(word)) tokens.push({ type: 'number', value: word })
      else tokens.push({ type: 'plain', value: word })
      lineStart = false
    }
  }
  return tokens
}

export function highlight(code: string, lang: string): Token[] {
  if (lang === 'python' || lang === 'py') return highlightPython(code)
  if (lang === 'bash' || lang === 'sh' || lang === 'shell') return highlightBash(code)
  return [{ type: 'plain', value: code }]
}
