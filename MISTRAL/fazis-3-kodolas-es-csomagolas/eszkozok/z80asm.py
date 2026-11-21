"""Teljesen saját, kétmenetes Z80-összeállító.

Cél: a PIOCO motor forrását a 3. kötetes eszközök nélkül, a projekt
önállóságáért ide írt, kis méretű assemblelővel tudjuk építeni.
Támogatott utasításkészlet: a motor által használt részhalmaz
(ld / add / inc / dec / cp / jr / jp / djnz / call / ret / push / pop /
ex de,hl / logikai / in/out / ldir / ld a,r / stb.).
"""
import re
import sys

R8 = {"B": 0, "C": 1, "D": 2, "E": 3, "H": 4, "L": 5, "(HL)": 6, "A": 7}
RP = {"BC": 0, "DE": 1, "HL": 2, "SP": 3}
RP2 = {"BC": 0xC5, "DE": 0xD5, "HL": 0xE5, "AF": 0xF5}
POP = {"BC": 0xC1, "DE": 0xD1, "HL": 0xE1, "AF": 0xF1}
COND_JR = {"NZ": 0x20, "Z": 0x28, "NC": 0x30, "C": 0x38}
COND_JP = {"NZ": 0xC2, "Z": 0xCA, "NC": 0xD2, "C": 0xDA}
ALU = {"ADD": 0x80, "ADC": 0x88, "SUB": 0x90, "SBC": 0x98,
       "AND": 0xA0, "XOR": 0xA8, "OR": 0xB0, "CP": 0xB8}
ALU_N = {"ADD": 0xC6, "ADC": 0xCE, "SUB": 0xD6, "SBC": 0xDE,
         "AND": 0xE6, "XOR": 0xEE, "OR": 0xF6, "CP": 0xFE}




def split_args(s):
    """Vessző-felbontás idézett szövegkészletek védelmével."""
    out, cur, q = [], "", False
    for ch in s:
        if ch == '"':
            q = not q
            cur += ch
        elif ch == "," and not q:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


class AsmError(Exception):
    pass


def clean(line):
    i = line.find(";")
    if i >= 0:
        line = line[:i]
    return line.strip()


def matches(tok):
    t = tok.upper().replace(" ", "")
    return t


class Asm:
    def __init__(self):
        self.symbols = {}
        self.out = []
        self.org = 0

    def toks(self, line, first=False):
        """KI (alacsony bájt) / KI magas címekhez (KIM-módszer)"""
        if first:
            m = re.match(r"^([A-Za-z_][\w]*)\s*:\s*(.*)$", line)
        else:
            m = None
        label, rest = (m.group(1), m.group(2)) if m else ("", line)
        return label, rest.strip()

    def eval_expr(self, e):
        e = e.strip()
        sign = 1
        while e.startswith("+-"):
            e = e[1:]
        if e.startswith("-"):
            sign = -1
            e = e[1:]
        if e.startswith("$"):
            return sign * int(e[1:], 16)
        if re.fullmatch(r"0[xX][0-9A-Fa-f]+", e):
            return sign * int(e, 16)
        if re.fullmatch(r"[0-7][0-9A-Fa-fH]", e) and e.upper().endswith("H"):
            return sign * int(e[:-1].replace("H", ""), 16)
        if e.startswith("'") and e.endswith("'"):
            return sign * ord(e[1])
        if e in self.symbols:
            return sign * self.symbols[e]
        if re.fullmatch(r"\d+", e):
            return sign * int(e)
        m = re.fullmatch(r"([\w]+)\s*([+\-])\s*(\w+)", e)
        if m:
            left = self.eval_expr(m.group(1))
            right = self.eval_expr(m.group(3))
            return left + right if m.group(2) == "+" else left - right
        if getattr(self, "passno", 2) == 1:
            return 0
        raise AsmError(f"nem értelmezhető kifejezés: '{e}'")

    def parse_int(self, tok):
        return self.eval_expr(tok) & 0xFFFF

    def emit(self, *bs):
        self.out.extend(b & 0xFF for b in bs)

    def here(self):
        return self.org + len(self.out)

    def reg8(self, tok):
        t = tok.upper().replace(" ", "")
        if t not in R8:
            raise AsmError(f"nem 8 bites regiszter: {tok}")
        return R8[t]

    def rep(self, tok):
        t = tok.upper().replace(" ", "")
        if t not in RP:
            raise AsmError(f"nem regiszterpár: {tok}")
        return RP[t]

    def is_mem(self, tok):
        return tok.strip().upper().startswith("(")

    def mem_addr(self, tok):
        inner = tok.strip()[1:-1].strip()
        if inner.upper() in ("BC", "DE", "HL", "C", "SP", "AF"):
            return inner.upper()
        return ("NUM", self.eval_expr(inner))

    # --- utasítások ---
    def do_line(self, line, passno):
        base = clean(line)
        if not base:
            return
        label, rest = self.toks(base, first=True)
        if label:
            if passno == 1:
                if label in self.symbols:
                    raise AsmError(f"dupla címke: {label}")
                self.symbols[label] = self.here()
            rest = rest.strip()
        if not rest:
            return
        if label:
            m2 = re.match(r"^EQU\s+(.*)$", rest, re.I)
            if m2:
                if passno == 1:
                    self.symbols[label] = self.eval_expr(m2.group(1))
                return
        m = re.match(r"^([A-Za-z_][\w]*)\s+EQU\s+(.*)$", rest, re.I)
        if m:
            if passno == 1:
                self.symbols[m.group(1)] = self.eval_expr(m.group(2))
            return
        parts = rest.split(None, 1)
        op = parts[0].upper()
        args = split_args(parts[1]) if len(parts) > 1 else []

        if op == "ORG":
            if passno == 1:
                self.org = self.eval_expr(args[0])
                self.out = []
            return
        if op == "DB":
            for a in args:
                if a.startswith('"') and a.endswith('"'):
                    for ch in a[1:-1]:
                        self.emit(ord(ch) & 0xFF)
                else:
                    v = self.eval_expr(a)
                    self.emit(v & 0xFF)
            return
        if op == "DW":
            for a in args:
                v = self.eval_expr(a)
                self.emit(v & 0xFF, (v >> 8) & 0xFF)
            return
        if op == "DS":
            v = self.eval_expr(args[0])
            self.out.extend([0] * v)
            return
        if op == "END":
            return

        self.instr(op, args, passno)

    def jr_rel(self, target, cond_len=2):
        delta = target - (self.here() + cond_len)
        if not (-128 <= delta <= 127):
            raise AsmError(f"JR túl messze: {delta}")
        return delta & 0xFF

    def instr(self, op, a, passno):
        am = [x.upper().replace(" ", "") for x in a]
        if op == "NOP":
            return self.emit(0x00)
        if op == "HALT":
            return self.emit(0x76)
        if op == "CPL":
            return self.emit(0x2F)
        if op == "SCF":
            return self.emit(0x37)
        if op == "EX" and am == ["DE", "HL"]:
            return self.emit(0xEB)
        if op in ("LDI", "LDIR"):
            return self.emit(0xED, 0xA0 if op == "LDI" else 0xB0)
        if op == "RET":
            if not a:
                return self.emit(0xC9)
            c = am[0]
            if c in COND_JP:
                return self.emit(COND_JP[c] + 0x08)
        if op in ("JP", "CALL"):
            cond = None
            tgt = ""
            if op == "JP" and am[0] == "(HL)":
                return self.emit(0xE9)
            if len(am) == 2:
                cond = am[0]
                tgt = am[1]
            else:
                tgt = am[0]
            t = self.eval_expr(tgt)
            if op == "JP":
                if cond is not None:
                    cc = {"NZ": 0xC2, "Z": 0xCA, "NC": 0xD2, "C": 0xDA}[cond]
                    return self.emit(cc, t & 0xFF, (t >> 8) & 0xFF)
                return self.emit(0xC3, t & 0xFF, (t >> 8) & 0xFF)
            if cond is not None:
                cc = {"NZ": 0xC4, "Z": 0xCC, "NC": 0xD4, "C": 0xDC}[cond]
                return self.emit(cc, t & 0xFF, (t >> 8) & 0xFF)
            return self.emit(0xCD, t & 0xFF, (t >> 8) & 0xFF)
        if op == "JR":
            if len(am) == 2:
                code = COND_JR[am[0]]
                m = self.symbols.get(am[1], 0) if passno == 1 else self.eval_expr(am[1])
                if passno == 1:
                    m = 0
                return self.emit(code, 0 if passno == 1 else self.jr_rel(m))
            t = self.symbols.get(am[0], 0) if passno == 1 else self.eval_expr(am[0])
            return self.emit(0x18, 0 if passno == 1 else self.jr_rel(t))
        if op == "DJNZ":
            t = self.symbols.get(am[0], 0) if passno == 1 else self.eval_expr(am[0])
            return self.emit(0x10, 0 if passno == 1 else self.jr_rel(t))
        if op == "PUSH":
            return self.emit(RP2[am[0].replace("(", "").replace(")", "")])
        if op == "POP":
            return self.emit(POP[am[0]])
        if op == "LD":
            return self.do_ld(am)
        if op == "ADD" and len(am) >= 2 and am[0] in RP:
            return self.emit(0x09 | RP[am[1]] << 4)
        if op in ALU:
            if len(am) == 2:
                alu_prev = am[0]
                if alu_prev in ("A",):
                    am = am[1:]
                else:
                    raise AsmError(f"{op} formátum: {a}")
            x = am[0]
            if x in R8:
                return self.emit(ALU[op] | R8[x])
            if x.startswith("("):
                inner = x[1:-1]
                if inner.upper() == "HL":
                    return self.emit(ALU[op] | 6)
                raise AsmError(f"{op} (mem) csak (HL): {a}")
            return self.emit(ALU_N[op], self.parse_int(x) & 0xFF)
        if op in ("INC", "DEC"):
            x = am[0]
            base = 0x04 if op == "INC" else 0x05
            if x in R8:
                return self.emit(base | R8[x] << 3)
            if x.startswith("(HL)"):
                return self.emit(base + 0x30)
            basep = 0x03 if op == "INC" else 0x0B
            if x in RP:
                return self.emit(basep | RP[x] << 4)
        if op == "ADD" and len(am) >= 2:
            x = am[0]
            y = am[1]
            if x in RP:
                return self.emit(0x09 | RP[y] << 4)
        if op == "RRA":
            return self.emit(0x1F)
        if op == "RLCA":
            return self.emit(0x07)
        if op == "RRCA":
            return self.emit(0x0F)
        if op == "IN" and len(am) >= 2:
            inner = a[1].strip()
            if inner.upper() == "(C)":
                return self.emit(0xED, 0x78)
            self.emit(0xDB, self.eval_expr(inner.strip("()")) & 0xFF)
            return
        if op == "OUT" and len(am) >= 2:
            inner = a[0].strip()
            self.emit(0xD3, self.eval_expr(inner.strip("()")) & 0xFF)
            return
        raise AsmError(f"ismeretlen utasítás: {op} {a}")


def kw(self, a):
    return a[0].upper().replace(" ", "")


def do_ld_wrapper(self, am):
    return self.do_ld(am)


def _patch(AsmCls):
    def do_ld(self, am, out_extent=None):
        dst, src = am[0], am[1]
        if dst in R8 and src in R8:
            return self.emit(0x40 | R8[dst] << 3 | R8[src])
        if dst in R8 and src.startswith("("):
            if src == "(HL)":
                return self.emit(0x46 | R8[dst] << 3)
            if dst == "A":
                if src == "(BC)":
                    return self.emit(0x0A)
                if src == "(DE)":
                    return self.emit(0x1A)
                v = self.eval_expr(src.strip("()"))
                return self.emit(0x3A, v & 0xFF, (v >> 8) & 0xFF)
            raise AsmError(f"mem-ből csak A/HL olvasható: {am}")
        if dst in R8 and src in ("R", "I"):
            return self.emit(0x5F if src == "R" else 0x57)
        if dst in R8:
            v = self.eval_expr(src)
            return self.emit(0x06 | R8[dst] << 3, v & 0xFF)
        if dst.startswith("(BC)"):
            return self.emit(0x02)
        if dst.startswith("(DE)"):
            return self.emit(0x12)
        if dst.startswith("(HL)") and len(am) >= 2:
            if src in R8:
                return self.emit(0x70 | R8[src])
            return self.emit(0x36, self.eval_expr(src) & 0xFF)
        if dst in RP and src.startswith("("):
            inner = src.strip("()").upper()
            if inner in ("BC", "DE", "HL", "SP"):
                raise AsmError(f"nem támogatott LD: {am}")
            v = self.eval_expr(src.strip("()"))
            if dst == "HL":
                return self.emit(0x2A, v & 0xFF, (v >> 8) & 0xFF)
            op2 = 0x5B if dst == "DE" else 0x4B
            return self.emit(0xED, op2, v & 0xFF, (v >> 8) & 0xFF)
        if dst in RP:
            v = self.eval_expr(src)
            return self.emit(0x01 | RP[dst] << 4, v & 0xFF, (v >> 8) & 0xFF)
        if dst == "SP" and len(am) >= 2:
            v = self.eval_expr(am[1])
            return self.emit(0x31, v & 0xFF, (v >> 8) & 0xFF)
        if dst == "A":
            s = src
            if s.startswith("(BC)"):
                return self.emit(0x0A)
            if s.startswith("(DE)"):
                return self.emit(0x1A)
            if s.startswith("("):
                v = self.eval_expr(s.strip("()"))
                return self.emit(0x3A, v & 0xFF, (v >> 8) & 0xFF)
            if s in ("R", "I"):
                return self.emit(0x5F if s == "R" else 0x57)
        if len(am) == 2 and dst.startswith("(") and am[1] in ("A", "HL"):
            v = self.eval_expr(dst.strip("()"))
            if am[1] == "A":
                return self.emit(0x32, v & 0xFF, (v >> 8) & 0xFF)
            return self.emit(0x22, v & 0xFF, (v >> 8) & 0xFF)
        if len(am) >= 2 and dst in ("HL",) and am[1].startswith("("):
            v = self.eval_expr(am[1].strip("()"))
            return self.emit(0x2A, v & 0xFF, (v >> 8) & 0xFF)
        raise AsmError(f"ismeretlen LD: {am}")
    AsmCls.do_ld = do_ld
    return AsmCls


def assemble(text):
    a = _patch(Asm)()
    for p in (1, 2):
        a.out = []
        a.passno = p
        # EQU sorok elsőnek, sorrendtől függetlenül meglegyenek a 2. menetben
        if p == 2:
            for line in text.splitlines():
                c = clean(line)
                m = re.match(r"^([A-Za-z_][\w]*)\s*:?\s*EQU\s+(.*)$", c, re.I)
                if m and m.group(1) not in a.symbols:
                    a.symbols[m.group(1)] = a.eval_expr(m.group(2))
        for line in text.splitlines():
            a.do_line(line, p)
    return bytes(a.out), a.symbols


def main():
    src, out = sys.argv[1], sys.argv[2]
    data, syms = assemble(open(src, encoding="utf-8").read())
    with open(out, "wb") as f:
        f.write(data)
    print(f"OK: {len(data)} bájt -> {out}")


if __name__ == "__main__":
    main()
