#!/usr/bin/env python3
"""rtlbuild.py - v065: the RTLOAD01 shell loader as the FIRST tape block.

Pure-BASIC autostart block (no machine code), built on top of the verified
t81build16.py helpers. It runs on LOAD "" / RUN, introduces Pico AI, and on
ENTER chains unconditionally into RTBASE16 (the v0.6.4-verified ROM pattern:
a LOAD command inside a program line, tape-name matched).

Program (ZX81 char codes: space=0x00, letters=0x26+, digits=0x1C+, '-'=0x16,
strings delimited by 0x0B; keywords PRINT=0xF5 INPUT=0xEE LOAD=0xEF):
    1 REM PICO AI GLM SHELL LOADER
    2 PRINT "PICO AI V065-2 IS LOADING"
    3 PRINT "MINIATURE AI MODEL FOR 16K"
    4 PRINT "IT THINKS AND WRITES ANSWERS"
    5 PRINT "13 TOPIC PACKS RIDE THE TAPE"
    6 PRINT "PRESS PLAY THEN PRESS ENTER"
    7 PRINT "LOADING IS SLOW - STAY CALM"
    8 INPUT C
    9 LOAD "RTBASE16"

Every PRINT string is at most 30 characters: the ZX81 wraps at 32 columns
(no word logic), longer lines wrap mid-word, eat rows and scroll the screen
(observed on a real emulator after mounting v065 - keep under the limit).

The RAMTOP / upper-memory protection design (POKE 16422/16423 + NEW, the
engine-side LD SP at boot) is documented in docs/fazis-3-ramtop.md and is
planned for v066 with a z88dk rebuild - see that file for why SP is NOT
re-armed from RAMTOP by the ROM's NEW, and why v065 therefore leaves the
working chain layout untouched.
"""
import os
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)

import t81build16 as tb          # verified helpers: sysvars/zx_name/...

REMB, PRINT_, INPUT_, LOADB = 0xEA, 0xF5, 0xEE, 0xEF
NL, SPACE, QUOTE, HYPHEN = 0x76, 0x00, 0x0B, 0x16


def zx_text(s):
    """Plain text (space, A-Z, 0-9, '-') -> ZX81 char codes."""
    out = []
    for ch in s:
        if ch == " ":
            out.append(SPACE)
        elif "A" <= ch <= "Z":
            out.append(0x26 + ord(ch) - 65)
        elif "0" <= ch <= "9":
            out.append(0x1C + int(ch))
        elif ch == "-":
            out.append(HYPHEN)
        else:
            raise ValueError(f"loader text: unsafe char {ch!r}")
    return bytes(out)


def zx_quoted(s):
    """A BASIC string literal: 0x0B + chars + 0x0B."""
    return bytes([QUOTE]) + zx_text(s) + bytes([QUOTE])


def bnum(n):
    """Binary line number + LE length field."""
    return bytes(((n >> 8) & 0xFF, n & 0xFF))


def llen(body):
    """The ZX81 line length (incl. trailing newline)."""
    return bytes(((len(body) + 1) & 0xFF, ((len(body) + 1) >> 8) & 0xFF))


def build_loader_lines():
    lines = []

    def add(body):
        lines.append((bnum(len(lines) + 1), llen(body), body, bytes([NL])))

    add(bytes([REMB]) + zx_text("PICO AI GLM SHELL LOADER"))
    add(bytes([PRINT_]) + zx_quoted("PICO AI V065-2 IS LOADING"))
    add(bytes([PRINT_]) + zx_quoted("MINIATURE AI MODEL FOR 16K"))
    add(bytes([PRINT_]) + zx_quoted("IT THINKS AND WRITES ANSWERS"))
    add(bytes([PRINT_]) + zx_quoted("13 TOPIC PACKS RIDE THE TAPE"))
    add(bytes([PRINT_]) + zx_quoted("PRESS PLAY THEN PRESS ENTER"))
    add(bytes([PRINT_]) + zx_quoted("LOADING IS SLOW - STAY CALM"))
    # INPUT C (numeric variable C = 0x28)
    add(bytes([INPUT_, 0x28]))
    # LOAD "RTBASE16" - tape-name matched, verified in the v064 chain
    add(bytes([LOADB, QUOTE]) + tb.zx_name("RTBASE16") + bytes([QUOTE]))
    for _, _, body, _ in lines:
        if body[0] == PRINT_:
            assert body[1] == QUOTE and body[-1] == QUOTE
            txt = body[2:-1]
            assert len(txt) <= 30, "PRINT text > 30 chars wraps on 32 columns"
    prog = b"".join(h + l + b + n for h, l, b, n in lines) + bytes([NL])
    bodies = b"".join(b for _, _, b, _ in lines)
    return prog, bodies


def main():
    Z, PROG, DFILE = tb.Z, tb.PROG, tb.DFILE
    prog, bodies = build_loader_lines()

    # every byte inside a program line must be safe text or a known token
    text_codes = set(zx_text("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -"))
    allowed = set(text_codes) | {REMB, PRINT_, INPUT_, LOADB, NL, QUOTE,
                                 0x28} | set(range(0x26, 0x40))
    bad = [b for b in bodies if b not in allowed]
    assert not bad, "unsafe bytes in loader program: %r" % bad
    assert prog.count(bytes([NL])) == 10

    core = bytearray()
    core += tb.sysvars()
    assert len(core) == PROG - Z
    core += prog
    assert PROG - Z + len(prog) <= DFILE - Z
    img = tb.make_full(bytes(core))
    assert img[-1] == 0x80
    assert img[DFILE - Z] == 0x76  # the display file's leading newline
    assert img[DFILE - Z + 33] == 0x76  # row 0 ends with a newline
    # RAMTOP guard: sysvars() ships the proven quickload word 0x7FFD -
    # v065 deliberately does NOT change it (see fazis-3-ramtop.md)
    wt = img[29] | img[30] << 8
    assert wt == 0x7FFD, "RAMTOP sysvar moved: 0x%04x" % wt

    out_dir = os.path.join(TOOLS, "..", "zx81", "16k")
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    open(os.path.join(out_dir, "GLM_v065_rtload.p"), "wb").write(img)

    src_tape = os.path.join(out_dir, "GLM_v064_RT16_TOPICS.t81")
    base = open(src_tape, "rb").read()
    assert base[:4] == b"EO81"
    data = tb.zx_name_record("RTLOAD01") + img
    tape = b"EO81" + tb.wrap_eo81("RTLOAD01", data) + base[4:]
    out = os.path.join(out_dir, "GLM_v065_RT16_TOPICS.t81")
    open(out, "wb").write(tape)
    print(f"RTLOAD01: full image {len(img)} B "
          f"(prog {len(prog)} B @0x{PROG:04X}, RAMTOP guard 0x7FFD)")
    print(f"{os.path.basename(out)}: {len(tape)} B "
          f"(RTLOAD01 + the 15 v064 blocks re-used verbatim)")


if __name__ == "__main__":
    main()
