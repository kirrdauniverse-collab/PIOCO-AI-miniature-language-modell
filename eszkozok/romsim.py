# -*- coding: utf-8 -*-
"""PIOCO AI — romsim.py: ZX81 ROM-SZINTŰ virtuális gép (teljes Z80 mag).

A C/6, majd a C/F080 + "száguldozó pixelek" tapasztalatok tanulsága: a
PC-s réteg nem látja, mit tesz a VALÓDI ROM a betöltés/RUN/NMI-tüzek
során. Ez az eszköz a valódi 8 KB-os ZX81 ROM-et futtatja a saját Z80
magunkon, a felhasználóéval azonos úton:

  reset → ROM init → tétlen fókuszciklus → .P "betöltése" (0x4009-től)
  → (billentyű-utánzás:) R U N NEWLINE → RUN: CLS → 1 REM → 2 RAND USR
  16514 → a mi bootunk → motor → MWAIT, közben soronként NMI-t kap a
  ROM (a valódi 0x0066-os kód fut, saját veremkezeléssel).

NEM buszszintű emulátor: a videó-trükk (LD R,A / EI / JP (HL)) jeljeleit
nem állítjuk elő — a képet a D_FILE/DF_CC/DF_SZ állapotból a ROM
szabályai szerint számoljuk (a vizsgált hibák state-szintűek).
A szalag-pulzusokat nem modellezzük: a .P bájtjai a 0x4009-től kerülnek
a memóriába (a LOAD olvasó oldala), a RUN billentyű-utánítással fut.

Memóriatükörzés: 0x0000-0x1FFF ROM (írásvédett), 0x2000-0x3FFF és
0x8000 fölött nem leképezett (írás eldobva, olvasás 0xFF) — a RAM-
detektálás így 16 KB-on megáll (RAMTOP=0x7FFF), ahogy a valódi gépen.

Használat:
  python3 romsim.py                          # boot-önteszt: reset → fókusz
  python3 romsim.py --p ../kazetta/pioco-0.1.p --keys RUN
  Opciók: --max-t (alap 30e6), --frames (képkocka-utasítás a RUN után),
          --trace (képkockánkénti sysvar-követés), --rom ../..../zx81.rom
"""
import sys, os, argparse, time
from collections import Counter

FS, FZ, F5, FH, F3, FPV, FN, FC = 0x80, 0x40, 0x20, 0x10, 0x08, 0x04, 0x02, 0x01
SPAR = [bin(i).count("1") & 1 == 0 for i in range(256)]      # páros paritás
LINE_T = 208          # soridő T-állapotokban — az NMI-kadencia
DEFAULT_ROM = "/home/z/my-project/research/zx81-refs/zx81.rom"

class Halt(Exception):
    pass

# ============================================================ Z80 mag
class Z80:
    def __init__(self):
        self.mem = bytearray(0x10000)
        self.A = self.F = self.B = self.C = self.D = self.E = self.H = self.L = 0
        self.A_ = self.F_ = self.B_ = self.C_ = self.D_ = self.E_ = self.H_ = self.L_ = 0
        self.IX = self.IY = self.SP = self.PC = self.I = self.R = 0
        self.IFF1 = self.IFF2 = False
        self.halted = False
        self.t = 0
        self.nmis = 0
        self.port_in = None        # fn(port, hi) -> bájt
        self.port_out = None       # fn(port, hi, érték)
        self.rom_writes = Counter()
        self.unmapped = Counter()

    # --- memória: ZX81 A14-dekódolás ---
    # A14=1 → RAM: 0x4000-0x7FFF, ÉS a 0xC000-0xFFFF tükör ((a&0x3FFF)|0x4000;
    # a képernyő-generálás így éri el a megjelenítőt: D_FILE|0x8000). A14=0:
    # 0x0000-0x1FFF ROM (írásvédett), 0x2000-0x3FFF és 0x8000-0xBFFF nem
    # leképezett — a RAM-CHECK így áll meg 0x8000-nál (RAMTOP=0x8000, 16K-nál).
    def rd(self, a):
        a &= 0xFFFF
        if a & 0x4000:
            return self.mem[(a & 0x3FFF) | 0x4000]
        if a < 0x2000:
            return self.mem[a]
        return 0xFF

    def wr(self, a, v):
        a &= 0xFFFF
        if a & 0x4000:
            self.mem[(a & 0x3FFF) | 0x4000] = v & 0xFF
            return
        if a < 0x2000:
            self.rom_writes[a] += 1
            return
        self.unmapped[a] += 1

    def rd16(self, a):
        return self.rd(a) | (self.rd(a + 1) << 8)

    def wr16(self, a, v):
        self.wr(a, v & 0xFF)
        self.wr(a + 1, (v >> 8) & 0xFF)

    # --- regiszterek ---
    def r8(self, i):
        return (self.B, self.C, self.D, self.E, self.H, self.L, self.mem[self.HL] if self._hl_ok() else self.rd(self.HL), self.A)[i] \
            if False else (self.B, self.C, self.D, self.E, self.H, self.L, None, self.A)[i]

    def w8(self, i, v):
        v &= 0xFF
        if i == 0: self.B = v
        elif i == 1: self.C = v
        elif i == 2: self.D = v
        elif i == 3: self.E = v
        elif i == 4: self.H = v
        elif i == 5: self.L = v
        elif i == 7: self.A = v

    def dd(self, i):
        return (self.BC, self.DE, self.HL, self.SP)[i]

    def setdd(self, i, v):
        v &= 0xFFFF
        if i == 0: self.BC = v
        elif i == 1: self.DE = v
        elif i == 2: self.HL = v
        else: self.SP = v

    @property
    def BC(self): return (self.B << 8) | self.C
    @BC.setter
    def BC(self, v): self.B, self.C = (v >> 8) & 0xFF, v & 0xFF
    @property
    def DE(self): return (self.D << 8) | self.E
    @DE.setter
    def DE(self, v): self.D, self.E = (v >> 8) & 0xFF, v & 0xFF
    @property
    def HL(self): return (self.H << 8) | self.L
    @HL.setter
    def HL(self, v): self.H, self.L = (v >> 8) & 0xFF, v & 0xFF
    @property
    def AF(self): return (self.A << 8) | self.F
    @AF.setter
    def AF(self, v): self.A, self.F = (v >> 8) & 0xFF, v & 0xFF

    # --- flag-segédek ---
    def flg8(self, r, c=None, pv=None, h=None, n=None):
        r &= 0xFF
        f = (r & (FS | F5 | F3)) | (FZ if r == 0 else 0)
        if c is not None: f |= FC if c else 0
        if pv is not None: f |= FPV if pv else 0
        if h is not None: f |= FH if h else 0
        if n is not None: f |= FN if n else 0
        self.F = f

    def cond(self, cc):
        F = self.F
        return [(F & FZ) == 0, (F & FZ) != 0, (F & FC) == 0, (F & FC) != 0,
                (F & FPV) == 0, (F & FPV) != 0, (F & FS) == 0, (F & FS) != 0][cc]

    def daa(self):
        a, F = self.A, self.F
        corr = 0
        if (a & 0x0F) > 9 or F & FH: corr |= 0x06
        cf = F & FC
        if a > 0x99 or cf: corr |= 0x60; cf = FC
        r = (a - corr) if F & FN else (a + corr)
        r &= 0xFF
        self.A = r
        self.F = ((F & ~(FN | FH | FC | FZ | FS | FPV | F5 | F3)) |
                  (FZ if r == 0 else 0) | (FS if r & 0x80 else 0) |
                  (r & (F5 | F3)) | (FPV if SPAR[r] else 0) |
                  (FC if cf else 0) | (F & FN))

    def push(self, v):
        self.SP = (self.SP - 2) & 0xFFFF
        self.wr16(self.SP, v)

    def pop(self):
        v = self.rd16(self.SP)
        self.SP = (self.SP + 2) & 0xFFFF
        return v

    def fetch(self):
        b = self.rd(self.PC)          # rd() = a 0x8000+ tükörrel (megjelenítőfájl!)
        self.PC = (self.PC + 1) & 0xFFFF
        self.R = (self.R & 0x80) | ((self.R + 1) & 0x7F)
        return b

    def fetchs(self):
        b = self.fetch()
        return b - 256 if b >= 128 else b

    def fetch16(self):
        lo = self.fetch()
        return lo | (self.fetch() << 8)

    # --- ALU (op: 0 ADD, 1 ADC, 2 SUB, 3 SBC, 4 AND, 5 XOR, 6 OR, 7 CP) ---
    def alu(self, op, x):
        a, c0 = self.A, 1 if self.F & FC else 0
        if op == 0: r = a + x; self.flg8(r, r > 0xFF, pv=(((r ^ a) & (r ^ x)) & 0x80) != 0, h=(a ^ x ^ r) & 0x10 != 0, n=False); self.A = r & 0xFF
        elif op == 1: r = a + x + c0; self.flg8(r, r > 0xFF, pv=(((r ^ a) & (r ^ x)) & 0x80) != 0, h=(a ^ x ^ r ^ c0) & 0x10 != 0, n=False); self.A = r & 0xFF
        elif op == 2: r = a - x; self.flg8(r, a < x, pv=(((r ^ a) & (a ^ x)) & 0x80) != 0, h=(a ^ x ^ r) & 0x10 != 0, n=True); self.A = r & 0xFF
        elif op == 3: r = a - x - c0; self.flg8(r, a < x + c0, pv=(((r ^ a) & (a ^ x)) & 0x80) != 0, h=(a ^ x ^ r ^ c0) & 0x10 != 0, n=True); self.A = r & 0xFF
        elif op == 4: r = a & x; self.F = (r & (FS | FZ | F5 | F3)) | FH; self.A = r
        elif op == 5: r = a ^ x; self.F = r & (FS | FZ | F5 | F3); self.A = r
        elif op == 6: r = a | x; self.F = r & (FS | FZ | F5 | F3); self.A = r
        else:
            r = a - x
            self.F = ((FZ if (r & 0xFF) == 0 else 0) | (r & (FS | F5 | F3)) |
                      (FC if a < x else 0) |
                      (FPV if (((r ^ a) & (a ^ x)) & 0x80) else 0) |
                      (FH if (a ^ x ^ r) & 0x10 else 0) | FN)

    def inc8(self, v):
        r = (v + 1) & 0xFF
        self.F = (self.F & FC) | (r & (FS | F5 | F3)) | (FZ if r == 0 else 0) | \
                 (FPV if (r & 0x80) == (v & 0x80) else 0) | \
                 (FH if (v & 0x0F) == 0x0F else 0)
        return r

    def dec8(self, v):
        r = (v - 1) & 0xFF
        self.F = (self.F & FC) | (r & (FS | F5 | F3)) | (FZ if r == 0 else 0) | \
                 (FPV if (r & 0x80) != (v & 0x80) else 0) | \
                 (FH if (v & 0x0F) == 0 else 0) | FN
        return r

    # --- futtatás ---
    def step(self):
        pc0 = self.PC
        op = self.fetch()
        self.t += 4
        try:
            self.exec_op(op, pc0)
        except Halt:
            raise
        except Exception as e:
            raise Halt(f"{type(e).__name__}: {e} @0x{pc0:04X} op={op:02X}")

    def exec_op(self, op, pc0):
        # --- prefixek ---
        if op == 0xCB: return self.op_cb()
        if op == 0xED: return self.op_ed()
        if op in (0xDD, 0xFD): return self.op_ddfd(op)
        # --- gyakori egységes blokkok ---
        if 0x40 <= op <= 0xBF and op != 0x76:      # LD r,r' / ALU A,x
            s, d = op & 7, (op >> 3) & 7
            if op < 0x80:
                v = self.rd(self.HL) if s == 6 else self.r8(s)
                if s == 6: self.t += 3
                if d == 6:
                    self.wr(self.HL, v); self.t += 3
                else:
                    self.w8(d, v)
            else:
                self.alu(d, self.rd(self.HL) if s == 6 else self.r8(s))
                if s == 6: self.t += 3
            return
        xhi, xlo = op & 0xC0, op & 0x07
        if xhi == 0x40:                            # INC/DEC r, LD r,n csoport maradékai
            pass
        # 0x00-0x3F blokk
        if op in (0x01, 0x11, 0x21, 0x31):
            self.setdd(op >> 4, self.fetch16()); self.t += 6; return
        if op in (0x09, 0x19, 0x29, 0x39):
            a = self.dd(op >> 4); r = self.HL + a
            self.F = (self.F & ~(FH | FN | FC | F5 | F3)) | \
                     (FC if r > 0xFFFF else 0) | (FH if (self.HL ^ a ^ r) & 0x1000 else 0) | \
                     ((r >> 8) & (F5 | F3))
            self.HL = r & 0xFFFF; self.t += 7; return
        if op in (0x02, 0x12):
            self.wr(self.BC if op == 0x02 else self.DE, self.A); self.t += 3; return
        if op in (0x0A, 0x1A):
            self.A = self.rd(self.BC if op == 0x0A else self.DE); self.t += 3; return
        if op == 0x22: self.wr16(self.fetch16(), self.HL); self.t += 6; return
        if op == 0x2A: self.HL = self.rd16(self.fetch16()); self.t += 6; return
        if op == 0x32: self.wr(self.fetch16(), self.A); self.t += 6; return
        if op == 0x3A: self.A = self.rd(self.fetch16()); self.t += 6; return
        if op in (0x03, 0x13, 0x23, 0x33):
            self.setdd(op >> 4, self.dd(op >> 4) + 1); self.t += 2; return
        if op in (0x0B, 0x1B, 0x2B, 0x3B):
            self.setdd(op >> 4, self.dd(op >> 4) - 1); self.t += 2; return
        if (op & 0xC7) == 0x06:                     # LD r,n / LD (HL),n
            i = (op >> 3) & 7
            if i == 6:
                self.wr(self.HL, self.fetch()); self.t += 6
            else:
                self.w8(i, self.fetch()); self.t += 3
            return
        if (op & 0xC7) in (0x04, 0x0C, 0x14, 0x1C, 0x24, 0x2C, 0x34, 0x3C):   # INC r
            r = op & 0x3F
            i = [0, 1, 2, 3, 4, 5, 6, 7][(op >> 3) & 7]
            if i == 6:
                self.wr(self.HL, self.inc8(self.rd(self.HL))); self.t += 7
            else:
                self.w8(i, self.inc8(self.r8(i))); self.t += 0
            return
        if (op & 0xC7) in (0x05, 0x0D, 0x15, 0x1D, 0x25, 0x2D, 0x35, 0x3D):   # DEC r
            i = (op >> 3) & 7
            if i == 6:
                self.wr(self.HL, self.dec8(self.rd(self.HL))); self.t += 7
            else:
                self.w8(i, self.dec8(self.r8(i)))
            return
        if op == 0x00: return                       # NOP
        if op == 0x08:
            self.A, self.A_ = self.A_, self.A
            self.F, self.F_ = self.F_, self.F
            return
        if op == 0x10:                              # DJNZ
            d = self.fetchs(); self.t += 1
            self.B = (self.B - 1) & 0xFF
            if self.B:
                self.PC = (self.PC + d) & 0xFFFF; self.t += 4
            return
        if (op & 0xE7) == 0x20:                     # JR cc (feltétel: 2 bit!)
            d = self.fetchs(); self.t += 3
            if self.cond((op >> 3) & 3):
                self.PC = (self.PC + d) & 0xFFFF; self.t += 2
            return
        if op == 0x18:
            d = self.fetchs(); self.PC = (self.PC + d) & 0xFFFF; self.t += 4; return
        if op == 0x07 or op == 0x0F or op == 0x17 or op == 0x1F:   # RLCA/RRCA/RLA/RRA
            if op == 0x07:
                c = self.A >> 7; self.A = ((self.A << 1) | c) & 0xFF
            elif op == 0x0F:
                c = self.A & 1; self.A = (self.A >> 1) | (c << 7)
            elif op == 0x17:
                c = self.A >> 7; self.A = ((self.A << 1) | (1 if self.F & FC else 0)) & 0xFF
            else:
                c = self.A & 1; self.A = (self.A >> 1) | ((1 if self.F & FC else 0) << 7)
            self.F = (self.A & (FS | FZ | F5 | F3)) | (FC if c else 0)
            return
        if op == 0x27: self.daa(); return
        if op == 0x2F: self.A ^= 0xFF; self.F |= FH | FN; return
        if op == 0x37: self.F = (self.F & ~(FH | FN)) | FC; return
        if op == 0x3F: self.F ^= FC; self.F &= ~(FH | FN); return
        if op == 0x76: self.halted = True; return   # HALT — NMI-re ébred
        if op == 0xC9: self.PC = self.pop(); self.t += 6; return        # RET
        if op == 0xCD:                                                  # CALL nn
            a = self.fetch16(); self.push(self.PC); self.PC = a; self.t += 13; return
        if op == 0xF9: self.SP = self.HL; return                        # LD SP,HL
        if op == 0xD9:                              # EXX
            self.B, self.B_ = self.B_, self.B
            self.C, self.C_ = self.C_, self.C
            self.D, self.D_ = self.D_, self.D
            self.E, self.E_ = self.E_, self.E
            self.H, self.H_ = self.H_, self.H
            self.L, self.L_ = self.L_, self.L
            return
        if op == 0xE3:
            v = self.rd16(self.SP); self.wr16(self.SP, self.HL); self.HL = v; self.t += 15; return
        if op == 0xE9: self.PC = self.HL; return
        if op == 0xEB: self.DE, self.HL = self.HL, self.DE; return
        if op == 0xF3: self.IFF1 = self.IFF2 = False; return
        if op == 0xFB: self.IFF1 = self.IFF2 = True; return
        if op == 0xD3:
            n = self.fetch(); self.t += 3
            if self.port_out: self.port_out(n, self.A, self.A)
            return
        if op == 0xDB:
            n = self.fetch(); self.t += 3
            self.A = (self.port_in(n, self.A) if self.port_in else 0xFF) & 0xFF
            return
        # 0xC0+ utasításcsalád
        if op >= 0xC0:
            p = op & 0xC7
            if p == 0xC0:                           # RET cc
                self.t += 1
                if self.cond((op >> 3) & 7): self.PC = self.pop(); self.t += 5
                return
            if p == 0xC1:                           # POP
                v = self.pop(); self.t += 6
                i = (op >> 4) & 3
                if i == 3: self.AF = v
                else: self.setdd(i, v)
                return
            if p == 0xC2:                           # JP cc
                a = self.fetch16()
                if self.cond((op >> 3) & 7): self.PC = a; self.t += 4
                return
            if p == 0xC3: self.PC = self.fetch16(); self.t += 4; return
            if p == 0xC4:                           # CALL cc
                a = self.fetch16()
                if self.cond((op >> 3) & 7): self.push(self.PC); self.PC = a; self.t += 7
                return
            if p == 0xC5 and op in (0xC5, 0xD5, 0xE5, 0xF5):   # PUSH
                self.push(self.AF if ((op >> 4) & 3) == 3 else self.dd((op >> 4) & 3)); self.t += 7
                return
            if p == 0xC6: self.alu((op >> 3) & 7, self.fetch()); self.t += 3; return
            if p == 0xC7:
                self.push(self.PC); self.PC = op & 0x38; self.t += 3; return
        raise Halt(f"nem dekódolható opcode {op:02X} @0x{pc0:04X}")

    # --- CB ---
    def rot(self, kind, v):
        if kind == 0: c = v >> 7; v = ((v << 1) | c) & 0xFF            # RLC
        elif kind == 1: c = v & 1; v = (v >> 1) | (c << 7)             # RRC
        elif kind == 2: c = v >> 7; v = ((v << 1) | (1 if self.F & FC else 0)) & 0xFF  # RL
        elif kind == 3: c = v & 1; v = (v >> 1) | ((1 if self.F & FC else 0) << 7)    # RR
        elif kind == 4: c = v >> 7; v = (v << 1) & 0xFF                # SLA
        elif kind == 5: c = v >> 7; v = ((v << 1) | 1) & 0xFF          # SLL
        elif kind == 6: c = v & 1; v = (v >> 1) | (v & 0x80)           # SRA
        else: c = v & 1; v = v >> 1                                    # SRL
        self.F = (v & (FS | FZ | F5 | F3)) | (FC if c else 0)
        return v

    def op_cb(self):
        sub = self.fetch()
        r = sub & 7
        v = self.rd(self.HL) if r == 6 else self.r8(r)
        if r == 6: self.t += 3
        kind = sub >> 6
        if kind < 2:                                 # forgatás/eltolás
            v = self.rot(sub & 7 if kind == 0 else (sub & 7) + 8, v) if False else self.rot(sub & 0x07 if kind == 0 else (sub & 0x0F), v)
            if r == 6: self.wr(self.HL, v)
            else: self.w8(r, v)
        elif kind == 2:                              # BIT b,r
            b = (sub >> 3) & 7
            res = (v >> b) & 1
            if r == 6:
                self.F = (self.F & FC) | FH | (0 if res else FZ)
            else:
                self.F = (self.F & FC) | FH | (0 if res else FZ) | (((v << b) & 0x80) >> 5 & F3) | (((v << b) & 0x2000) >> 10 & F5)
        elif kind == 3:                              # RES b,r
            v &= ~(1 << ((sub >> 3) & 7))
            if r == 6: self.wr(self.HL, v)
            else: self.w8(r, v)
        else:                                        # SET b,r
            v |= 1 << ((sub >> 3) & 7)
            if r == 6: self.wr(self.HL, v)
            else: self.w8(r, v)

    # --- ED ---
    def op_ed(self):
        sub = self.fetch()
        pc0 = (self.PC - 2) & 0xFFFF
        if 0x40 <= sub <= 0x78 and (sub & 7) != 6 and (sub & 0xC7) in (0x40, 0x48, 0x50, 0x58, 0x60, 0x68, 0x70, 0x78):
            if sub & 0x08 == 0:                      # IN r,(C)
                v = (self.port_in(self.C, self.B) if self.port_in else 0xFF) & 0xFF
                self.w8((sub >> 3) & 7, v)
                self.F = (v & (FS | FZ | F5 | F3)) | (FPV if SPAR[v] else 0)
            else:                                    # OUT (C),r
                if self.port_out: self.port_out(self.C, self.B, self.r8((sub >> 3) & 7))
            self.t += 4
            return
        if sub in (0x42, 0x52, 0x62, 0x72):          # SBC HL,dd
            a = self.dd((sub >> 4) & 3); c = 1 if self.F & FC else 0
            r = self.HL - a - c
            self.F = (FC if self.HL < a + c else 0) | (FZ if (r & 0xFFFF) == 0 else 0) | \
                     (FS if r & 0x8000 else 0) | (FPV if (self.HL ^ a ^ r) & 0x8000 else 0) | \
                     (FH if (self.HL ^ a ^ r) & 0x1000 else 0) | FN | ((r >> 8) & (F5 | F3))
            self.HL = r & 0xFFFF; self.t += 7; return
        if sub in (0x4A, 0x5A, 0x6A, 0x7A):          # ADC HL,dd
            a = self.dd((sub >> 4) & 3); c = 1 if self.F & FC else 0
            r = self.HL + a + c
            self.F = (FC if r > 0xFFFF else 0) | (FZ if (r & 0xFFFF) == 0 else 0) | \
                     (FS if r & 0x8000 else 0) | (FPV if (self.HL ^ a ^ r) & 0x8000 else 0) | \
                     (FH if (self.HL ^ a ^ r) & 0x1000 else 0) | ((r >> 8) & (F5 | F3))
            self.HL = r & 0xFFFF; self.t += 7; return
        if sub == 0x44 or sub in (0x4C, 0x54, 0x5C, 0x6C, 0x74, 0x7C):   # NEG
            r = -self.A
            self.F = (FC if self.A else 0) | (FZ if (r & 0xFF) == 0 else 0) | (r & (FS | F5 | F3)) | \
                     (FPV if self.A == 0x80 else 0) | (FH if self.A & 0x0F else 0) | FN
            self.A = r & 0xFF; self.t += 4; return
        if sub in (0x45, 0x55, 0x5D, 0x65, 0x6D, 0x75, 0x7D):            # RETN/RETI
            self.IFF1 = self.IFF2
            self.PC = self.pop(); self.t += 10; return
        if (sub & 0xC7) == 0x46:                     # IM 0/1/2
            return
        if sub == 0x47: self.I = self.A; return
        if sub == 0x4F: self.R = self.A & 0x7F; return
        if sub == 0x57:
            self.A = self.I
            self.F = (FZ if self.A == 0 else 0) | (FPV if self.IFF2 else 0) | (self.A & (F5 | F3))
            return
        if sub == 0x5F:
            self.A = self.R & 0xFF
            self.F = (FZ if self.A == 0 else 0) | (FPV if self.IFF2 else 0) | (self.A & (F5 | F3))
            return
        if sub in (0x4B, 0x5B, 0x6B, 0x7B):          # LD dd,(nn)
            a = self.fetch16(); v = self.rd16(a)
            i = (sub >> 4) & 3
            if i == 3: self.SP = v
            else: self.setdd(i, v)
            self.t += 6; return
        if sub in (0x43, 0x53, 0x63, 0x73):          # LD (nn),dd
            a = self.fetch16()
            if sub == 0x73: self.wr16(a, self.SP)
            else: self.wr16(a, self.dd((sub >> 4) & 3))
            self.t += 6; return
        if sub == 0xA0:                              # LDI
            self.wr(self.DE, self.rd(self.HL))
            self.DE = (self.DE + 1) & 0xFFFF; self.HL = (self.HL + 1) & 0xFFFF
            self.BC = (self.BC - 1) & 0xFFFF
            self.F = (self.F & ~(FN | FPV | FH)) | (0 if self.BC else FPV) | \
                     ((self.A + self.mem[self.DE] if False else 0) & 0)
            return
        if sub == 0xA8:                              # LDD
            self.wr(self.DE, self.rd(self.HL))
            self.DE = (self.DE - 1) & 0xFFFF; self.HL = (self.HL - 1) & 0xFFFF
            self.BC = (self.BC - 1) & 0xFFFF
            self.F = (self.F & ~(FN | FPV | FH)) | (0 if self.BC else FPV)
            return
        if sub == 0xB0:                              # LDIR
            while self.BC:
                self.wr(self.DE, self.rd(self.HL))
                self.DE = (self.DE + 1) & 0xFFFF; self.HL = (self.HL + 1) & 0xFFFF
                self.BC = (self.BC - 1) & 0xFFFF
                self.t += 10
            self.F = (self.F & ~(FN | FPV | FH))
            return
        if sub == 0xB8:                              # LDDR
            while self.BC:
                self.wr(self.DE, self.rd(self.HL))
                self.DE = (self.DE - 1) & 0xFFFF; self.HL = (self.HL - 1) & 0xFFFF
                self.BC = (self.BC - 1) & 0xFFFF
                self.t += 10
            self.F = (self.F & ~(FN | FPV | FH))
            return
        if sub == 0xA1:                              # CPI
            x = self.rd(self.HL)
            self.HL = (self.HL + 1) & 0xFFFF; self.BC = (self.BC - 1) & 0xFFFF
            r = self.A - x
            self.F = (self.F & FC) | (FZ if (r & 0xFF) == 0 else 0) | FN | (r & (FS | F5 | F3)) | \
                     (FH if (self.A ^ x ^ r) & 0x10 else 0) | (0 if self.BC else FPV)
            self.t += 6; return
        if sub == 0xA9:                              # CPD
            x = self.rd(self.HL)
            self.HL = (self.HL - 1) & 0xFFFF; self.BC = (self.BC - 1) & 0xFFFF
            r = self.A - x
            self.F = (self.F & FC) | (FZ if (r & 0xFF) == 0 else 0) | FN | (r & (FS | F5 | F3)) | \
                     (FH if (self.A ^ x ^ r) & 0x10 else 0) | (0 if self.BC else FPV)
            self.t += 6; return
        if sub == 0xB1:                              # CPIR
            r = 0
            while self.BC:
                x = self.rd(self.HL)
                self.HL = (self.HL + 1) & 0xFFFF; self.BC = (self.BC - 1) & 0xFFFF
                r = self.A - x
                self.t += 10
                if (r & 0xFF) == 0: break
            self.F = (self.F & FC) | (FZ if (r & 0xFF) == 0 else 0) | FN | (r & (FS | F5 | F3)) | \
                     (FH if (self.A ^ x ^ r) & 0x10 else 0) | (0 if self.BC else FPV)
            return
        if sub in (0x67, 0x6F):                      # RRD/RLD
            hl = self.rd(self.HL)
            if sub == 0x67:
                self.wr(self.HL, ((self.A << 4) | (hl >> 4)) & 0xFF)
                self.A = (self.A & 0xF0) | (hl & 0x0F)
            else:
                self.wr(self.HL, ((hl << 4) | (self.A & 0x0F)) & 0xFF)
                self.A = (self.A & 0xF0) | (hl >> 4)
            a = self.A
            self.F = (a & (FS | FZ | F5 | F3))
            self.t += 10; return
        raise Halt(f"nem támogatott ED {sub:02X} @0x{pc0:04X}")

    # --- DD/FD ---
    def op_ddfd(self, pfx):
        op = self.fetch()
        pc0 = (self.PC - 2) & 0xFFFF
        xy = self.IX if pfx == 0xDD else self.IY
        def setxy(v):
            if pfx == 0xDD: self.IX = v & 0xFFFF
            else: self.IY = v & 0xFFFF
        if op == 0x21: setxy(self.fetch16()); self.t += 6; return
        if op == 0x22: self.wr16(self.fetch16(), xy); self.t += 6; return
        if op == 0x2A: setxy(self.rd16(self.fetch16())); self.t += 6; return
        if op in (0x09, 0x19, 0x29, 0x39):
            a = (self.BC, self.DE, xy, self.SP)[(op >> 4) & 3]
            r = xy + a
            self.F = (self.F & ~(FH | FC | F5 | F3)) | (FC if r > 0xFFFF else 0) | \
                     (FH if (xy ^ a ^ r) & 0x1000 else 0) | ((r >> 8) & (F5 | F3)) | (self.F & FN)
            setxy(r); self.t += 7; return
        if op == 0x23: setxy(xy + 1); self.t += 2; return
        if op == 0x2B: setxy(xy - 1); self.t += 2; return
        if op == 0xE5: self.push(xy); self.t += 7; return
        if op == 0xE1: setxy(self.pop()); self.t += 6; return
        if op == 0xE3:
            v = self.rd16(self.SP); self.wr16(self.SP, xy); setxy(v); self.t += 15; return
        if op == 0xE9: self.PC = xy; return
        if op == 0xCB:
            d = self.fetchs(); sub = self.fetch()
            a = (xy + d) & 0xFFFF
            v = self.rd(a)
            kind = sub >> 6
            if kind < 2:
                self.wr(a, self.rot(sub & 0x07, v))
            elif kind == 2:
                b = (sub >> 3) & 7
                res = (v >> b) & 1
                self.F = (self.F & FC) | FH | (0 if res else FZ)
            elif kind == 3:
                self.wr(a, v | (1 << ((sub >> 3) & 7)))
            else:
                self.wr(a, v & ~(1 << ((sub >> 3) & 7)))
            self.t += 19; return
        if op in (0x34, 0x35):
            d = self.fetchs(); a = (xy + d) & 0xFFFF
            self.wr(a, self.inc8(self.rd(a)) if op == 0x34 else self.dec8(self.rd(a)))
            self.t += 15; return
        if op == 0x36:                               # LD (IX+d),n
            d = self.fetchs()
            self.wr((xy + d) & 0xFFFF, self.fetch()); self.t += 14; return
        if 0x40 <= op <= 0xBF and op != 0x76:
            s, dst = op & 7, (op >> 3) & 7
            if op < 0x80:
                if s == 6 and dst != 6:              # LD r,(IX+d)
                    d = self.fetchs()
                    self.w8(dst, self.rd((xy + d) & 0xFFFF)); self.t += 11; return
                if dst == 6 and s != 6:              # LD (IX+d),r
                    d = self.fetchs()
                    self.wr((xy + d) & 0xFFFF, self.r8(s)); self.t += 11; return
            else:
                if s == 6:                           # ALU A,(IX+d)
                    d = self.fetchs()
                    self.alu(dst, self.rd((xy + d) & 0xFFFF)); self.t += 11; return
        # minden más: a prefix nem vonatkozik az utasításra — sima végrehajtás
        return self.exec_op(op, pc0)

    def nmi(self):
        self.nmis += 1
        self.push(self.PC)
        self.IFF2 = self.IFF1
        self.IFF1 = False
        self.PC = 0x0066
        self.t += 5

    def int38(self):
        """Maskable INT (IM 1): a 0x0038-as INTERRUPT rutin — a soralapú
        videó-generálás; a ROM EI-je és DI-je szabályozza, mikor fogadható."""
        if not self.IFF1:
            return False
        self.push(self.PC)
        self.IFF1 = self.IFF2 = False
        self.PC = 0x0038
        self.t += 7
        return True

# ============================================================ ZX81 gép
class ZX81:
    # billentyűmátrix: sorbit -> 5 oszlop (bit0 = bal szélső kulcs)
    KBD_ROWS = [0b11110, 0b11101, 0b11011, 0b10111, 0b01111]

    def __init__(self, rom_path=DEFAULT_ROM):
        self.cpu = Z80()
        rom = open(rom_path, "rb").read()
        assert len(rom) == 8192, "a ROM nem 8 KB"
        self.cpu.mem[0:8192] = rom
        self.fd_writes = []
        self.in_reads = Counter()
        self.in_seq = []
        self.kbd = [0x1F] * 8          # soronként aktív-alacsony oszlopmaszk
        self.keys_pressed = 0
        self.next_nmi = LINE_T
        self.nmi_enabled = False       # D-4.0: reset után a valódi ULA NMI-kapuja
                                       # ZÁRVA — a ROM START rutinja OUT(FD),0-gyal
                                       # kapcsolja KI (biztos, ami biztos), és csak
                                       # SLOW-ra váltáskor OUT(FD),0x80-gyal BE.
                                       # Resetkor BE-állással az első NMI-k a
                                       # RAM-CHECK közben SP=0-val a ROM-ba tolják
                                       # az initet — pont az "azonnali restart".
        self.poke_guard = []
        self.cpu.port_in = self.pin
        self.cpu.port_out = self.pout
        self.pc_hist = Counter()
        self.pc_ring = []              # utolsó PC-k — a kisodródás lokalizálásához
        self.tripwire = True           # álljon-e le a PC a táblatartományba lépéskor
        self.watch = {}                # cím -> figyelt pont (regiszterek rögzítése)
        self.watch_hit = []
        self.stop_at = None            # ezen a címen álljon le a tick Halt-tal

    def pin(self, port, hi):
        if port & 1:                   # nem 0xFE — nincs eszköz
            return 0xFF
        self.in_reads[(port, hi)] += 1
        if len(self.in_seq) < 4000:
            self.in_seq.append((self.cpu.t, port, hi))
        v = 0x1F
        for i in range(8):
            if not (hi >> i) & 1:
                v &= self.kbd[i]
        return (v & 0x1F) | 0xE0       # bit6 = EAR: nincs szalagjel

    def pout(self, port, hi, val):
        if port == 0xFD:
            # FD bit7: az NMI-generátor kapuja (l. ROM-lista: START OUT(FD),0 = KI;
            # SLOW/FAST OUT(FD),0x80 = BE; NMI-CONT az generálás alatt KI kapcsolja).
            self.fd_writes.append((self.cpu.t, val))
            self.nmi_enabled = bool(val & 0x80)
        # 0xFE: kazetta-ki (OUT): nem modellezett

    def hard_reset(self):
        c = self.cpu
        c.A = c.F = c.BC = c.DE = c.HL = c.IX = c.IY = 0
        c.A_ = c.F_ = c.BC = c.DE = c.HL  # (árnyék is nulla)
        c.BC = c.DE = c.HL = 0
        c.PC = 0
        c.SP = 0
        c.halted = False
        c.t = 0
        self.next_nmi = LINE_T
        self.nmi_enabled = False       # D-4.0: reset → NMI-kapu zárva (l. __init__)

    def tick(self, duration):
        """`duration` T-állapotnyi futás a JELENLEGI időponttól (relatív)."""
        c = self.cpu
        limit = c.t + duration
        while c.t < limit:
            if c.halted:
                c.t += 4
            else:
                pc0 = c.PC
                if self.stop_at is not None and pc0 == self.stop_at:
                    raise Halt(f"STOP@0x{pc0:04X}")
                if self.watch and pc0 in self.watch:
                    self.watch_hit.append((c.t, pc0, c.HL, c.BC, c.DE, c.SP, c.A))
                    if len(self.watch_hit) > 40:
                        self.watch.pop(pc0, None)
                if self.tripwire and 0x007E <= pc0 < 0x0200:
                    ring = " ".join(f"{p:04X}" for p in self.pc_ring[-30:])
                    raise Halt(f"TRIPWIRE: PC=0x{pc0:04X} a táblatartományba lépett; gyűrű: {ring}")
                self.pc_ring.append(pc0)
                if len(self.pc_ring) > 48:
                    self.pc_ring.pop(0)
                if pc0 == 0x0044:
                    # D-4.0: a ZX81 videó-trükk (0041 LD R,A / 0043 EI /
                    # 0044 JP (HL)) — a valódi gépen az ULA ciklus-csenése
                    # (contended display line) miatt a kijelző-bájtok
                    # "végrehajtása" láthatatlan, és soronként a handler
                    # lép be újra. CPU-szinten a JP (HL)-t NEM hajtjuk végre:
                    # egy soridő elteltével a sor-NMI újra belép (0x0066),
                    # a ROM saját állapotgépe viszi tovább. Enélkül a JP (HL)
                    # szó szerint végrehajtódik → wild PC → RST 38 → az init
                    # összeomlik = az "azonnali restart" (a .P-út SLOW módban
                    # fut, ezért a szalag-úton nem látszott).
                    if self.nmi_enabled:
                        c.t += LINE_T
                        self.next_nmi = c.t + LINE_T
                        c.nmi()
                        c.halted = False
                        continue
                    # kapu zárva (a display-ciklusban elvileg nem fordul
                    # elő): normál lépés
                c.step()
                if c.nmis % 64 == 0:
                    self.pc_hist[pc0 >> 8] += 1
            if c.t >= self.next_nmi:
                self.next_nmi = c.t + LINE_T
                if self.nmi_enabled:
                    c.nmi()          # FD bit7=1: soralapú NMI — a valódi ULA
                                     # kijelző-generáló viselkedése
                    c.halted = False
                # FD bit7=0 (kapu zárva): a valódi ZX81 ULA SEMMILYEN
                # megszakítást nem generál (nincs soralapú INT!). A korábbi
                # int38()-csalás mesterséges megszakításvihar volt, ami a ROM
                # IM1 utáni initjét döngette szét 0x0038-on keresztül — ez volt
                # az "azonnali restart" gyökere (D-4.0).

    def press(self, row, col, frames):
        """row: 0-7 (A8..A15), col: 0-4 (bit0=bal) — lenyomva `frames` képkockán át."""
        self.kbd[row] &= ~(1 << col) & 0x1F
        self.tick(FRAME_T * frames)
        self.kbd[row] |= 1 << col
    def word(self, a):
        return self.cpu.rd16(a)

    def state(self):
        c = self.cpu
        return (f"T={c.t} NMI={c.nmis} PC=0x{c.PC:04X} SP=0x{c.SP:04X} "
                f"RAMTOP=0x{self.word(0x4004):04X} ERR_SP=0x{self.word(0x4002):04X} | "
                f"D_FILE=0x{self.word(0x400C):04X} DF_CC=0x{self.word(0x400E):04X} "
                f"DF_SZ={c.mem[0x4022]} VARS=0x{self.word(0x4010):04X} "
                f"E_LINE=0x{self.word(0x4014):04X} CH_ADD=0x{self.word(0x4016):04X} "
                f"CDFLAG=0x{c.mem[0x403B]:02X}")

    def render(self, rows=24):
        """Képernyő a ROM szabályai szerint: sorok 0x76-ig (max 32),
        a dupla 0x76 (stop-bájt) a képernyő végét jelzi."""
        c = self.cpu
        out, a = [], self.word(0x400E)
        stop = False
        for r in range(rows):
            if stop:
                out.append("")
                continue
            line = []
            for i in range(32):
                b = c.mem[a & 0xFFFF] if 0x4000 <= a < 0x8000 else 0x00
                a += 1
                if b == 0x76:
                    break
                line.append(b)
            else:
                pass  # 32 karakter elfogyott sorzáró nélkül is zárjuk
            out.append(line)
            if c.mem[a & 0xFFFF] == 0x76 and a != self.word(0x400E) - 1:
                if line and len(line) < 32:
                    pass
            # a sorzáró 0x76 elfogyasztása:
            if (a - 1) < 0x8000 and c.mem[a - 1 & 0xFFFF] == 0x76:
                pass
            if c.mem[a & 0xFFFF] == 0x76 and 0x4000 <= a < 0x8000:
                nxt = c.mem[a & 0xFFFF]
            if 0x4000 <= a < 0x8000 and c.mem[a & 0xFFFF] == 0x76:
                stop = True
                a += 1
        return out

FRAME_T = 64896   # kb. 312 sor × 208 T

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rom", default=DEFAULT_ROM)
    ap.add_argument("--p", default=None)
    ap.add_argument("--keys", default="RUN")
    ap.add_argument("--max-t", type=int, default=40_000_000)
    ap.add_argument("--boot-frames", type=int, default=450)   # a valódi RAM-CHECK ~370 képkocka (~7 s)
    ap.add_argument("--frames", type=int, default=12)
    ap.add_argument("--trace", action="store_true")
    ap.add_argument("--watch", default="", help="vesszős tizenhatos címek: regiszter-rögzítés az első áthaladáskor")
    args = ap.parse_args()

    zx = ZX81(args.rom)
    if args.watch:
        for w in args.watch.split(","):
            zx.watch[int(w, 16)] = True
    zx.hard_reset()
    print("== reset — ROM init futtatása…")
    try:
        zx.tick(FRAME_T * args.boot_frames)
    except Halt as e:
        print(f"LEÁLLÁS a boot alatt: {e}")
        print("PC-gyűrű (utolsó 24):", " ".join(f"{p:04X}" for p in zx.pc_ring[-24:]))
        print("FD-írások:", zx.fd_writes[:10], "…")
        print("nem leképezett olvasások/írások:", dict(list(zx.cpu.unmapped.items())[:5]),
              "ROM-írások:", dict(list(zx.cpu.rom_writes.items())[:5]))
        raise SystemExit(1)
    print("boot után:", zx.state())
    if zx.watch_hit:
        for t, pc, hl, bc, de, sp, a in zx.watch_hit[:12]:
            print(f"  watch PC=0x{pc:04X} T={t}: HL=0x{hl:04X} BC=0x{bc:04X} DE=0x{de:04X} SP=0x{sp:04X} A=0x{a:02X}")
    print("PC-histogram (felső bájt):", zx.pc_hist.most_common(6))
    print("FD-írások (első 8):", zx.fd_writes[:8])
    print("IN-minták (első 8):", [(hex(p), hex(h), n) for (p, h), n in zx.in_reads.most_common(8)])

    if args.p:
        pf = open(args.p, "rb").read()
        zx.cpu.mem[0x4009:0x4009 + len(pf)] = pf
        print(f"\n== .P betöltve a 0x4009-től ({len(pf)} B)")
        print("betöltés után:", zx.state())

    print(f"\n== gépelés: {args.keys!r} + NEWLINE")
    # sorbit/oszlop a mátrix szerint: R=(2,3) U=(5,3) N=(7,3) NEWLINE=(6,0)
    MATRIX = {"R": (2, 3), "U": (5, 3), "N": (7, 3), "\n": (6, 0)}
    for ch in args.keys + "\n":
        row, col = MATRIX[ch]
        zx.press(row, col, frames=6)
        zx.tick(FRAME_T * 3)          # elengedés — billentyű-ismétlés nélkül
    print("gépelés után:", zx.state())
    el = zx.word(0x4014)
    ed = bytes(zx.cpu.mem[el:el + 24])
    print("E_LINE munkaterület:", ed.hex(" "), ">", ed[:20])

    print(f"\n== futás még {args.frames} képkockán át…")
    snaps = []
    try:
        for f in range(args.frames):
            zx.tick(FRAME_T)
            if args.trace:
                snaps.append((f, zx.word(0x400C), zx.word(0x400E), zx.cpu.mem[0x4022], zx.cpu.PC))
    except Halt as e:
        print(f"LEÁLLÁS futás közben: {e}")
    print("végső állapot:", zx.state())
    if args.trace:
        for f, dfile, dfcc, dfsz, pc in snaps:
            print(f"  képkocka {f}: D_FILE=0x{dfile:04X} DF_CC=0x{dfcc:04X} DF_SZ={dfsz} PC=0x{pc:04X}")
    print("ROM-írás kísérletek:", dict(zx.cpu.rom_writes) or "nincs")
    print("nem leképezett írások:", dict(list(zx.cpu.unmapped.items())[:8]) or "nincs")
    scr = zx.render()
    print("\n+ 32 karakter széles képernyő (kódok) — első 10 sor:")
    for i, row in enumerate(scr[:10]):
        print(f"  {i}: {' '.join(f'{b:02X}' for b in row)}")
    if zx.watch_hit:
        print("watch-találatok:")
        for t, pc, hl, bc, de, sp, a in zx.watch_hit[:16]:
            print(f"  PC=0x{pc:04X} T={t}: HL=0x{hl:04X} BC=0x{bc:04X} DE=0x{de:04X} SP=0x{sp:04X} A=0x{a:02X}")

if __name__ == "__main__":
    main()
