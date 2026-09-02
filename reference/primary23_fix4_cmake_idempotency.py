#!/usr/bin/env python3
import re

def apply(cm):
    if not cm.strip():
        raise ValueError("empty")
    target_re = re.compile(r"add_library\s*\(\s*m9color\b(?P<body>.*?)\)", re.IGNORECASE | re.DOTALL)
    m = target_re.search(cm)
    if m is not None:
        if "m9color_jni.cpp" not in m.group(0):
            raise ValueError("collision")
    else:
        if not cm.endswith("\n"):
            cm += "\n"
        cm += "\n# M9 PRIMARY2.3 JNI1 FIX6 additive native colour target\nadd_library(m9color SHARED ${CMAKE_CURRENT_SOURCE_DIR}/m9color_jni.cpp)\nset_target_properties(m9color PROPERTIES CXX_STANDARD 17 CXX_STANDARD_REQUIRED ON CXX_EXTENSIONS OFF)\n"
    if not ("target_compile_options(m9color" in cm and "-ffp-contract=off" in cm and "-fno-fast-math" in cm):
        cm += "\ntarget_compile_options(m9color PRIVATE -O3 -ffp-contract=off -fno-fast-math)\n"
    if "max-page-size=16384" not in cm:
        cm += 'set_property(TARGET m9color APPEND_STRING PROPERTY LINK_FLAGS " -Wl,-z,max-page-size=16384")\n'
    return cm

def count_target(cm):
    return len(re.findall(r"add_library\s*\(\s*m9color\b", cm, re.IGNORECASE))

# Fresh opaque upstream CMake: append exactly once.
base='cmake_minimum_required(VERSION 3.10)\nproject(Photon)\nadd_library(existing SHARED existing.cpp)\n'
a=apply(base)
assert a.startswith(base)
assert count_target(a)==1
assert 'm9color_jni.cpp' in a and '-ffp-contract=off' in a and '-fno-fast-math' in a and 'max-page-size=16384' in a
assert apply(a)==a

# Exact user failure class: m9color already exists, but no FIX6/FIX2 marker comment.
preexisting='cmake_minimum_required(VERSION 3.10)\nadd_library(m9color SHARED ${CMAKE_CURRENT_SOURCE_DIR}/m9color_jni.cpp)\ntarget_compile_options(m9color PRIVATE -O3 -ffp-contract=off -fno-fast-math)\nset_property(TARGET m9color APPEND_STRING PROPERTY LINK_FLAGS " -Wl,-z,max-page-size=16384")\n'
b=apply(preexisting)
assert b==preexisting
assert count_target(b)==1

# Self-heal an older valid target missing compile/link properties.
older='cmake_minimum_required(VERSION 3.10)\nadd_library( m9color\n SHARED\n ${CMAKE_CURRENT_SOURCE_DIR}/m9color_jni.cpp )\n'
c=apply(older)
assert count_target(c)==1
assert '-ffp-contract=off' in c and '-fno-fast-math' in c and 'max-page-size=16384' in c

# Refuse a target-name collision rather than silently hijacking it.
try:
    apply('add_library(m9color SHARED unrelated.cpp)\n')
except ValueError as e:
    assert str(e)=='collision'
else:
    raise AssertionError('collision not refused')

print('PRIMARY2.3 JNI1 FIX6 CMake idempotency regression PASS')
