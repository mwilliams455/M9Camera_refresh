#!/usr/bin/env python3
from pathlib import Path
import sys

here = Path(__file__).resolve().parent
source = here / 'apply-m9cam-nativeprospective1a.py'
if not source.exists():
    raise SystemExit('NATIVEPROSPECTIVE1A FIX1 missing original apply harness')
text = source.read_text()

old = '''def extract_method(text, marker):
    start = text.find(marker)
    if start < 0:
        raise SystemExit('NATIVEPROSPECTIVE1A method marker missing: ' + marker)
    brace = text.find('{', start)
    if brace < 0:
        raise SystemExit('NATIVEPROSPECTIVE1A method opening brace missing')
    depth = 0
    i = brace
    in_string = False
    string_quote = ''
    escape = False
    while i < len(text):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == '\\\\':
                escape = True
            elif ch == string_quote:
                in_string = False
        else:
            if ch in ('"', "'"):
                in_string = True
                string_quote = ch
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return start, i + 1, text[start:i + 1]
        i += 1
    raise SystemExit('NATIVEPROSPECTIVE1A unterminated method')
'''

new = '''def extract_method(text, marker):
    start = text.find(marker)
    if start < 0:
        raise SystemExit('NATIVEPROSPECTIVE1A method marker missing: ' + marker)
    brace = text.find('{', start)
    if brace < 0:
        raise SystemExit('NATIVEPROSPECTIVE1A method opening brace missing')

    # Parse the exact Java method body. The original extractor counted braces inside
    # comments; the previous FIX1 used the next top-level member as a boundary, which
    # was too broad for a byte-for-byte frozen-method hash. Keep the safety check strict
    # while ignoring braces that cannot affect Java block structure.
    depth = 0
    i = brace
    state = 'code'
    quote = ''
    escape = False
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ''

        if state == 'line_comment':
            if ch == '\\n':
                state = 'code'
            i += 1
            continue

        if state == 'block_comment':
            if ch == '*' and nxt == '/':
                state = 'code'
                i += 2
            else:
                i += 1
            continue

        if state == 'quoted':
            if escape:
                escape = False
            elif ch == '\\\\':
                escape = True
            elif ch == quote:
                state = 'code'
            i += 1
            continue

        if ch == '/' and nxt == '/':
            state = 'line_comment'
            i += 2
            continue
        if ch == '/' and nxt == '*':
            state = 'block_comment'
            i += 2
            continue
        if ch in ('"', "'"):
            state = 'quoted'
            quote = ch
            escape = False
            i += 1
            continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return start, i + 1, text[start:i + 1]
        i += 1

    raise SystemExit('NATIVEPROSPECTIVE1A unterminated method')
'''

if old not in text:
    raise SystemExit('NATIVEPROSPECTIVE1A FIX1 original extractor anchor missing')
text = text.replace(old, new, 1)

code = compile(text, str(source), 'exec')
g = {'__name__': '__main__', '__file__': str(source)}
exec(code, g, g)
