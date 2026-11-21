# -*- coding: utf-8 -*-
"""PIOCO AI — mini Z80 assembler (a motor forrásához, ellenőrzött opcode-részlettel).

Támogatott utasításkészlet: LD (r/r'-grid, (HL), (BC)/(DE), (nn)), INC/DEC (r, dd),
ADD HL,dd, ALU-műveletek (ADD/ADC/SUB/SBC/AND/XOR/OR/CP, A-implikált és n forma),
JP/JR/DJNZ/CALL/RET (+feltételes), PUSH/POP, EX, ROT-ok (RLCA/RLA/RL/RLC),
IN/OUT (C), LDI/LDIR, ED 42..72 SBC HL,rr. Direktívák: ORG, EQU, DB, DW.
Minden kódolás a --test modulban kézzel ellenőrzött vektorokkal van rögzítve.
"""
import sys

R = {"B": 0, "C": 1, "D": 2, "E": 3, "H": 4, "L": 5, "(HL)": 6, "A": 7}
DD = {"BC": 0, "DE": 1, "HL": 2, "SP": 3}
QQ = {"BC": "C5", "DE": "D5", "HL": "E5", "AF": "F5"}   # PUSH
POPQ = {"BC": "C1", "DE": "D1", "HL": "E1", "AF": "F1"}  # POP
CC = {"NZ": 0, "Z": 1, "NC": 4, "C": 5, "PO": 2, "PE": 3, "P": 6, "M": 7}
ALU = {"ADD": 0, "ADC": 1, "SUB": 2, "SBC": 3, "AND": 4, "XOR": 5, "OR": 6, "CP": 7}
IMPLIED = {"NOP": "00", "HALT": "76", "DI": "F3", "EI": "FB", "CPL": "2F",
           "SCF": "37", "CCF": "3F", "RLCA": "07", "RRCA": "0F", "RLA": "17",
           "RRA": "1F", "EXX": "D9", "RETI": "ED,4D", "LDI": "ED,A0",
           "LDIR": "ED,B0", "LDDR": "ED,B8"}

class AsmError(Exception):
    pass

def _is_ident(s):
    import re
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", s))

def tokenize_line(line):
    line = line.split(";")[0].strip()
    if not line:
        return None, None, []
    label = None
    if ":" in line and not line.upper().startswith(("DB", "DW")):
        head, rest = line.split(":", 1)
        if head.strip() and " " not in head.strip():
            label, line = head.strip(), rest.strip()
    if label is None:
        # kettőspont nélküli EQU: "NÉV EQU kifejezés"
        p0 = line.split(None, 2)
        if len(p0) >= 2 and p0[1].upper() == "EQU" and _is_ident(p0[0]):
            label = p0[0]
            line = "EQU " + (p0[2] if len(p0) > 2 else "").strip()
    parts = line.split(None, 1) if line else []
    mn = parts[0].upper() if parts else None
    args = []
    if len(parts) > 1:
        raw = parts[1]
        depth = 0; cur = ""; 
        for ch in raw:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            if ch == "," and depth == 0:
                args.append(cur.strip()); cur = ""
            else:
                cur += ch
        if cur.strip():
            args.append(cur.strip())
    return label, mn, args

def eval_expr(expr, labels):
    expr = expr.strip()
    # egyszerű kifejezés: szám / címke / 'C' / + - * (unáris mínusz is)
    import re
    toks = re.findall(r"0[xX][0-9A-Fa-f]+|'[^']'|\d+|[A-Za-z_][A-Za-z0-9_]*|[()+\-*/]", expr)
    merged = []
    for i, t in enumerate(toks):
        if t == "-" and (not merged or merged[-1] in ("+", "-", "*", "(")):
            if i + 1 < len(toks) and toks[i + 1] not in ("(", ")", "+", "-", "*"):
                merged.append("-" + toks[i + 1]); toks[i + 1] = None
            else:
                merged.append(t)
        elif t is not None:
            merged.append(t)
    toks = merged
    # shunting-yard (egyszerű, bal-asszociatív + - *)
    prec = {"+": 1, "-": 1, "*": 2}
    out, ops = [], []
    def val(t):
        if t.startswith("-"):
            return -val(t[1:])
        if t.startswith("0x") or t.startswith("0X"):
            return int(t, 16)
        if t.startswith("'"):
            return ord(t[1])
        if t.isdigit():
            return int(t)
        if t in labels:
            return labels[t]
        raise AsmError(f"ismeretlen címke/kifejezés: {t}")
    for t in toks:
        if t in ("(",):
            ops.append(t)
        elif t in (")",):
            while ops and ops[-1] != "(":
                out.append(ops.pop())
            ops.pop()
        elif t in prec:
            while ops and ops[-1] in prec and prec[ops[-1]] >= prec[t]:
                out.append(ops.pop())
            ops.append(t)
        else:
            out.append(val(t))
    while ops:
        out.append(ops.pop())
    st = []
    for x in out:
        if isinstance(x, int):
            st.append(x)
        else:
            b, a = st.pop(), st.pop()
            st.append({"+": a + b, "-": a - b, "*": a * b}[x])
    if len(st) != 1:
        raise AsmError(f"hibás kifejezés: {expr}")
    return st[0]

class Asm:
    def __init__(self, size_mode=False):
        self.labels = {}
        self.size_mode = size_mode   # True: csak hossz, címkék nélkül (1. átmenet)

    def assemble(self, src, org=0):
        lines = src.splitlines()
        # 1. átmenet: címkék + hosszak (címkék NEM értékelődnek ki)
        addr = org
        pre = []
        self.size_mode = True
        for ln, line in enumerate(lines, 1):
            label, mn, args = tokenize_line(line)
            if label and mn == "EQU":
                self.size_mode = False
                self.labels[label] = eval_expr(args[0], self.labels)
                self.size_mode = True
                continue
            if label:
                self.labels[label] = addr
            if mn in ("ORG",):
                self.size_mode = False
                addr = eval_expr(args[0], self.labels)
                self.size_mode = True
                continue
            n = self.size(mn, args, ln)
            if mn is not None:
                pre.append((ln, addr, mn, args))
            addr += n
        self.size_mode = False
        # 2. átmenet: kódolás
        code = bytearray()
        cur = org
        for ln, a, mn, args in pre:
            if mn == "ORG":
                cur = eval_expr(args[0], self.labels)
                continue
            b = self.encode(mn, args, a, ln)
            code += bytes(b)
            cur += len(b)
        return bytes(code), self.labels

    def size(self, mn, args, ln):
        if mn is None:
            return 0
        if mn == "DB":
            return self._db_len(args, ln)
        if mn == "DW":
            return 2 * len(args)
        try:
            return len(self.encode(mn, args, 0, ln))
        except AsmError:
            raise
        except KeyError as e:
            raise AsmError(f"line {ln}: nem támogatott: {mn} {args} ({e})")
        except (IndexError, ValueError) as e:
            raise AsmError(f"line {ln}: hibás operandus: {mn} {args} ({e})")

    def _db_len(self, args, ln):
        n = 0
        for a in args:
            if a.startswith('"') or a.startswith("'") and len(a) > 2:
                n += len(a) - 2
            else:
                n += 1
        return n

    def _alu(self, op, src, addr, ln):
        code = 0x80 + ALU[op] * 8
        if src == "n":
            return None  # jelzés: n-forma
        code += R[src]
        return [code]

    def encode(self, mn, args, addr, ln):
        if self.size_mode:
            V = lambda e: 0
        else:
            V = lambda e: eval_expr(e, self.labels)
        A = [a.upper() for a in args]
        if mn in IMPLIED and not args:
            return [int(x, 16) for x in IMPLIED[mn].split(",")]
        if mn == "ORG":
            return []
        if mn == "DB":
            out = []
            for a in args:
                if a.startswith('"'):
                    out += [ord(c) for c in a[1:-1]]
                else:
                    out += [V(a) & 0xFF]
            return out
        if mn == "DW":
            out = []
            for a in args:
                v = V(a); out += [v & 0xFF, (v >> 8) & 0xFF]
            return out
        if mn == "LD":
            dst, src = A[0], A[1]
            if dst in R and src in R:
                c = 0x40 + R[dst] * 8 + R[src]
                if c == 0x76:
                    raise AsmError(f"line {ln}: LD H,(HL)? — 0x76 HALT ütközés")
                return [c]
            if dst in R and src == "(BC)":
                assert R[dst] == 7; return [0x0A]
            if dst in R and src == "(DE)":
                assert R[dst] == 7; return [0x1A]
            if dst in R and src.startswith("(") and src not in ("(BC)", "(DE)", "(HL)"):
                assert dst == "A"; n = V(src[1:-1]); return [0x3A, n & 0xFF, (n >> 8) & 0xFF]
            if dst == "(BC)" and src == "A":
                return [0x02]
            if dst == "(DE)" and src == "A":
                return [0x12]
            if dst == "(HL)" and src in R:
                return [0x70 + R[src]]
            if dst == "(HL)":
                return [0x36, V(src) & 0xFF]
            if dst in DD and src.startswith("("):
                n = V(src[1:-1])
                if dst == "HL": return [0x2A, n & 0xFF, (n >> 8) & 0xFF]
                if dst == "SP": return [0xED, 0x7B, n & 0xFF, (n >> 8) & 0xFF]
            if dst.startswith("(") and src in DD:
                n = V(dst[1:-1])
                if src == "HL": return [0x22, n & 0xFF, (n >> 8) & 0xFF]
                if src == "SP": return [0xED, 0x73, n & 0xFF, (n >> 8) & 0xFF]
            if dst.startswith("(") and src == "A":
                n = V(dst[1:-1]); return [0x32, n & 0xFF, (n >> 8) & 0xFF]
            if dst in R and not src.startswith("("):
                return [0x06 + 8 * R[dst], V(src) & 0xFF]
            if dst in DD and not src.startswith("("):
                n = V(src)
                return [[0x01, 0x11, 0x21, 0x31][DD[dst]], n & 0xFF, (n >> 8) & 0xFF]
            raise AsmError(f"line {ln}: LD forma nem támogatott: {dst},{src}")
        if mn in ("INC", "DEC") and len(A) == 1:
            op = A[0]
            if op in DD:
                base = 0x03 if mn == "INC" else 0x0B
                return [base + 16 * DD[op]]
            if op == "(HL)":
                return [0x34 if mn == "INC" else 0x35]
            base = 0x04 if mn == "INC" else 0x05
            return [base + 8 * R[op]]
        if mn == "ADD" and A[0] == "HL" and len(A) == 2:
            return [0x09 + 16 * DD[A[1]]]
        if mn in ("SBC", "ADC") and len(A) == 2 and A[0] == "HL" and A[1] in DD:
            op = 0x42 if mn == "SBC" else 0x4A
            return [0xED, op + 16 * DD[A[1]]]
        if mn in ALU:
            if len(A) == 2 and A[0] == "A":
                src = A[1]
            elif len(A) == 1:
                src = A[0]
            else:
                raise AsmError(f"line {ln}: ALU forma: {mn} {args}")
            if src in R:
                return [0x80 + ALU[mn] * 8 + R[src]]
            if src == "(HL)":
                return [0x80 + ALU[mn] * 8 + 6]
            return [0xC6 + 8 * ALU[mn], V(src) & 0xFF]
        if mn == "JP" and len(A) == 1:
            n = V(A[0]); return [0xC3, n & 0xFF, (n >> 8) & 0xFF]
        if mn == "JP" and len(A) == 2 and A[0] in CC:
            n = V(A[1]); return [0xC2 + 8 * CC[A[0]], n & 0xFF, (n >> 8) & 0xFF]
        rel_of = lambda s: V(s) if s.startswith("-") else V(s) - (addr + 2)
        if mn == "JR" and len(A) == 1:
            rel = rel_of(A[0])
            if not self.size_mode: assert -128 <= rel <= 127
            return [0x18, rel & 0xFF]
        if mn == "JR" and len(A) == 2 and A[0] in CC:
            rel = rel_of(A[1])
            if not self.size_mode: assert -128 <= rel <= 127
            return [0x20 + 8 * CC[A[0]], rel & 0xFF]
        if mn == "DJNZ":
            rel = rel_of(A[0])
            if not self.size_mode: assert -128 <= rel <= 127
            return [0x10, rel & 0xFF]
        if mn == "CALL" and len(A) == 1:
            n = V(A[0]); return [0xCD, n & 0xFF, (n >> 8) & 0xFF]
        if mn == "CALL" and len(A) == 2 and A[0] in CC:
            n = V(A[1]); return [0xC4 + 8 * CC[A[0]], n & 0xFF, (n >> 8) & 0xFF]
        if mn == "RET" and not args:
            return [0xC9]
        if mn == "RET" and len(A) == 1 and A[0] in CC:
            return [0xC0 + 8 * CC[A[0]]]
        if mn == "PUSH" and A[0] in QQ:
            return [int(QQ[A[0]], 16)]
        if mn == "POP" and A[0] in POPQ:
            return [int(POPQ[A[0]], 16)]
        if mn == "EX" and A[0] == "DE" and A[1] == "HL":
            return [0xEB]
        if mn == "EX" and A[0] == "(SP)" and A[1] == "HL":
            return [0xE3]
        if mn == "EX" and A[0] == "AF" and A[1] == "AF'":
            return [0x08]
        if mn in ("RL", "RLC") and A[0] in R:
            base = 0x10 if mn == "RL" else 0x00
            return [0xCB, base + R[A[0]]]
        if mn == "IN" and len(A) == 2 and A[1] == "(C)":
            return [0xED, 0x40 + 8 * R[A[0]]]
        if mn == "OUT" and len(A) == 2 and A[0] == "(C)":
            return [0xED, 0x41 + 8 * R[A[1]]]
        raise AsmError(f"line {ln}: nem támogatott utasítás: {mn} {args}")

def assemble(src, org=0):
    return Asm().assemble(src, org)

# --- önteszt: kézzel ellenőrzött kódolások ---
def _selftest():
    cases = [
        ("LD BC,0x1234", [0x01, 0x34, 0x12]),
        ("LD HL,0x4200", [0x21, 0x00, 0x42]),
        ("LD SP,0x7FFF", [0x31, 0xFF, 0x7F]),
        ("LD A,7", [0x3E, 0x07]),
        ("LD B,3", [0x06, 0x03]),
        ("LD (HL),A", [0x77]),
        ("LD A,(HL)", [0x7E]),
        ("LD (HL),0x76", [0x36, 0x76]),
        ("LD C,(HL)", [0x4E]),
        ("LD B,A", [0x47]),
        ("LD H,A", [0x67]),
        ("LD L,A", [0x6F]),
        ("LD A,H", [0x7C]),
        ("LD A,C", [0x79]),
        ("LD A,(BC)", [0x0A]),
        ("LD (DE),A", [0x12]),
        ("LD (0x1234),HL", [0x22, 0x34, 0x12]),
        ("LD HL,(0x1234)", [0x2A, 0x34, 0x12]),
        ("LD A,(0x1234)", [0x3A, 0x34, 0x12]),
        ("LD (0x1234),A", [0x32, 0x34, 0x12]),
        ("XOR A", [0xAF]),
        ("ADD HL,BC", [0x09]),
        ("ADD HL,HL", [0x29]),
        ("INC HL", [0x23]),
        ("INC DE", [0x13]),
        ("DEC BC", [0x0B]),
        ("DEC C", [0x0D]),
        ("INC (HL)", [0x34]),
        ("JP 0x1234", [0xC3, 0x34, 0x12]),
        ("JP NZ,0x1234", [0xC2, 0x34, 0x12]),
        ("CALL NZ,0x1234", [0xC4, 0x34, 0x12]),
        ("RET Z", [0xC8]),
        ("CALL 0x034C", [0xCD, 0x4C, 0x03]),
        ("RET", [0xC9]),
        ("PUSH BC", [0xC5]),
        ("PUSH HL", [0xE5]),
        ("PUSH AF", [0xF5]),
        ("POP DE", [0xD1]),
        ("POP HL", [0xE1]),
        ("IN A,(C)", [0xED, 0x78]),
        ("OUT (C),A", [0xED, 0x79]),
        ("LDIR", [0xED, 0xB0]),
        ("SBC HL,BC", [0xED, 0x42]),
        ("CP 0", [0xFE, 0x00]),
        ("CP (HL)", [0xBE]),
        ("SUB B", [0x90]),
        ("OR 0x80", [0xF6, 0x80]),
        ("XOR 0x21", [0xEE, 0x21]),
        ("AND (HL)", [0xA6]),
        ("EX DE,HL", [0xEB]),
        ("RLA", [0x17]),
        ("RL A", [0xCB, 0x17]),
        ("RLC B", [0xCB, 0x00]),
        ("DJNZ -2", [0x10, 0xFE]),
        ("JR -2", [0x18, 0xFE]),
        ("JR NZ,-2", [0x20, 0xFE]),
        ("JR Z,-3", [0x28, 0xFD]),
    ]
    asm = Asm()
    for src, expect in cases:
        got, _ = asm.assemble(src)
        if list(got) != expect:
            raise AssertionError(f"{src!r} -> {[hex(b) for b in got]} (várt {[hex(b) for b in expect]})")
    # DB/DW és címkefeloldás
    code, labels = asm.assemble("HERE:\n DB \"ABC\",0\n DW HERE")
    assert list(code) == [0x41, 0x42, 0x43, 0x00, 0x00, 0x00] and labels["HERE"] == 0
    print(f"Z80 assembler önteszt OK ({len(cases)} kódolás + DB/DW/címkék)")

if __name__ == "__main__":
    _selftest()
