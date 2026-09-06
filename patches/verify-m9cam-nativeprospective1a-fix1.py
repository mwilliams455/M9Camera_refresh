#!/usr/bin/env python3
from pathlib import Path

here = Path(__file__).resolve().parent
source = here / 'verify-m9cam-nativeprospective1a.py'
if not source.exists():
    raise SystemExit('NATIVEPROSPECTIVE1A FIX1 missing original verifier')
text = source.read_text()

old = '''def extract_method(text, marker):
    start = text.find(marker)
    if start < 0:
        raise SystemExit('verifier method marker missing: ' + marker)
    brace = text.find('{', start)
    depth = 0
    i = brace
    in_string = False
    quote = ''
    escape = False
    while i < len(text):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == '\\\\':
                escape = True
            elif ch == quote:
                in_string = False
        else:
            if ch in ('"', "'"):
                in_string = True
                quote = ch
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
        i += 1
    raise SystemExit('verifier unterminated method')
'''
new = '''def extract_method(text, marker):
    start = text.find(marker)
    if start < 0:
        raise SystemExit('verifier method marker missing: ' + marker)
    end = text.find('\\n    private static ', start + len(marker))
    if end < 0:
        raise SystemExit('verifier next top-level method marker missing after: ' + marker)
    return text[start:end]
'''
if old not in text:
    raise SystemExit('NATIVEPROSPECTIVE1A verifier FIX1 original extractor anchor missing')
text = text.replace(old, new, 1)

code = compile(text, str(source), 'exec')
g = {'__name__': '__main__', '__file__': str(source)}
exec(code, g, g)
