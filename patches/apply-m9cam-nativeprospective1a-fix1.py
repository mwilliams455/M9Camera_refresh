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
    # Renderer source is generated and has stable four-space top-level member indentation.
    # A lexical brace parser is fragile around Java comments/character literals; use the next
    # top-level private-static member declaration as the method boundary instead.
    end = text.find('\\n    private static ', start + len(marker))
    if end < 0:
        raise SystemExit('NATIVEPROSPECTIVE1A next top-level method marker missing after: ' + marker)
    return start, end, text[start:end]
'''
if old not in text:
    raise SystemExit('NATIVEPROSPECTIVE1A FIX1 original extractor anchor missing')
text = text.replace(old, new, 1)

code = compile(text, str(source), 'exec')
g = {'__name__': '__main__', '__file__': str(source)}
exec(code, g, g)
