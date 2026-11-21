# -*- coding: utf-8 -*-
"""PIOCO AI — z80sim.py: Z80-szimulátor a motor binárisainak végpont-tesztjéhez.

NEM teljes ZX81-emulátor: nincs NMI/képernyő-generálás/szalag-pulzus —
az utasításkészlet azon része, amit a z80asm ki tud adni, az van implementálva
(regiszterek: AF BC DE HL SP PC; flagekből Z és C), plusz:
  - CALL-hookok (pl. ROM IN-BYTE 0x034C → Pythonból táplált bájtsor),
  - IN A,(C) port-olvasás hook (billentyűzet-szkripteléshez),
  - írás-követés (mely címtartományok íródtak — zóna-ellenőrzéshez),
  - önugrás-detektálás (MWAIT: JR önmagára) és lépéslimit.

A szimulátor helyességét a --test önteszt (z80asm-mal összeállított
mintaprogramok) és a végpont-teszt (szimfuttatas.py) együtt igazolják.
"""
import sys

FZ, FC = 0x80, 0x01  # Z és C jelzőbit (a többi jelzőbit nem szükséges a motorhoz)

class SimError(Exception):
    pass

class Z80Sim:
    def __init__(self):
        self.mem = bytearray(65536)
        self.A = self.B = self.C = self.D = self.E = self.H = self.L = 0
        self.F = 0
        self.SP = 0
        self.PC = 0
        self.halted = None            # leállás oka (None = fut)
        self.hooks = {}               # cím -> fn(sim): CALL ide hook, nincs stack
        self.in_hook = None           # fn(bc) -> bájt; None → 0xFF (nincs lenyomva)
        self.writes = []              # (cím, érték) lista — zóna-ellenőrzéshez
        self.max_steps = 20_000_000

    # --- 8 bites regiszterek név szerint ---
    def r8(self, i):
        return [self.B, self.C, self.D, self.E, self.H, self.L,
                self.mem[(self.H << 8) | self.L], self.A][i]

    def w8(self, i, v):
        v &= 0xFF
        if i == 6:
            self.store((self.H << 8) | self.L, v)
        elif i == 0: self.B = v
        elif i == 1: self.C = v
        elif i == 2: self.D = v
        elif i == 3: self.E = v
        elif i == 4: self.H = v
        elif i == 5: self.L = v
        else: self.A = v

    # --- memória írás írás-követéssel ---
    def store(self, a, v):
        self.mem[a & 0xFFFF] = v & 0xFF
        self.writes.append((a & 0xFFFF, v & 0xFF))

    def store16(self, a, v):
        self.store(a, v & 0xFF)
        self.store((a + 1) & 0xFFFF, (v >> 8) & 0xFF)

    def load16(self, a):
        return self.mem[a & 0xFFFF] | (self.mem[(a + 1) & 0xFFFF] << 8)

    @property
    def HL(self): return (self.H << 8) | self.L
    @HL.setter
    def HL(self, v): self.H, self.L = (v >> 8) & 0xFF, v & 0xFF
    @property
    def BC(self): return (self.B << 8) | self.C
    @BC.setter
    def BC(self, v): self.B, self.C = (v >> 8) & 0xFF, v & 0xFF
    @property
    def DE(self): return (self.D << 8) | self.E
    @DE.setter
    def DE(self, v): self.D, self.E = (v >> 8) & 0xFF, v & 0xFF

    def push(self, v):
        self.SP = (self.SP - 2) & 0xFFFF
        self.store16(self.SP, v)

    def pop(self):
        v = self.load16(self.SP)
        self.SP = (self.SP + 2) & 0xFFFF
        return v

    # --- flagek ---
    def setZ(self, v): self.F = (self.F & ~FZ) | (FZ if (v & 0xFF) == 0 else 0)
    def setC(self, c): self.F = (self.F & ~FC) | (FC if c else 0)
    def cond(self, cc):
        z, c = bool(self.F & FZ), bool(self.F & FC)
        return [not z, z, not c, c][cc]  # NZ, Z, NC, C

    def alu(self, op, x):
        a = self.A
        if op == 0:   # ADD
            r = a + x; self.setC(r > 0xFF); self.A = r & 0xFF
        elif op == 1: # ADC
            r = a + x + (1 if self.F & FC else 0); self.setC(r > 0xFF); self.A = r & 0xFF
        elif op == 2: # SUB
            self.setC(a < x); self.A = (a - x) & 0xFF
        elif op == 3: # SBC
            r = a - x - (1 if self.F & FC else 0); self.setC(r < 0); self.A = r & 0xFF
        elif op == 4: self.A = a & x; self.setC(False)   # AND
        elif op == 5: self.A = a ^ x; self.setC(False)   # XOR
        elif op == 6: self.A = a | x; self.setC(False)   # OR
        else:         # CP
            self.setC(a < x); self.setZ(a - x)
            return
        self.setZ(self.A)

    def fetch(self):
        b = self.mem[self.PC & 0xFFFF]
        self.PC = (self.PC + 1) & 0xFFFF
        return b

    def fetchs(self):
        b = self.fetch()
        return b - 256 if b >= 128 else b

    def _dd(self, i):
        return [self.BC, self.DE, self.HL, self.SP][i]

    def _wdd(self, i, v):
        if i == 0: self.BC = v
        elif i == 1: self.DE = v
        elif i == 2: self.HL = v
        else: self.SP = v & 0xFFFF

    def step(self):
        if self.halted:
            return False
        pc0 = self.PC
        op = self.fetch()
        if op == 0x00:
            pass
        elif op == 0x76:
            self.halted = "HALT"
        elif op == 0x10:  # DJNZ
            d = self.fetchs()
            self.B = (self.B - 1) & 0xFF
            if self.B:
                self.PC = (self.PC + d) & 0xFFFF
        elif op == 0x18:  # JR
            d = self.fetchs()
            tgt = (self.PC + d) & 0xFFFF
            if tgt == pc0:
                self.halted = f"önugrás @ 0x{pc0:04X} (várakozó ciklus)"
            else:
                self.PC = tgt
        elif 0x20 <= op <= 0x38 and op % 8 == 0:  # JR cc
            cc = (op >> 3) & 3
            d = self.fetchs()
            if self.cond(cc):
                self.PC = (self.PC + d) & 0xFFFF
        elif op in (0x01, 0x11, 0x21, 0x31):  # LD dd,nn
            self._wdd((op >> 4) & 3, self.fetch() | (self.fetch() << 8))
        elif op == 0x2A:
            self.HL = self.load16(self.fetch() | (self.fetch() << 8))
        elif op == 0x22:
            self.store16(self.fetch() | (self.fetch() << 8), self.HL)
        elif op == 0x32:
            self.store(self.fetch() | (self.fetch() << 8), self.A)
        elif op == 0x3A:
            self.A = self.mem[self.fetch() | (self.fetch() << 8)]
        elif op == 0x02:
            self.store(self.BC, self.A)
        elif op == 0x12:
            self.store(self.DE, self.A)
        elif op == 0x0A:
            self.A = self.mem[self.BC]
        elif op == 0x1A:
            self.A = self.mem[self.DE]
        elif op in (0x06, 0x0E, 0x16, 0x1E, 0x26, 0x2E, 0x3E):  # LD r,n
            self.w8((op >> 3) & 7, self.fetch())
        elif op == 0x36:
            self.store(self.HL, self.fetch())
        elif op in (0x03, 0x13, 0x23, 0x33):  # INC dd (flagenként)
            self._wdd((op >> 4) & 3, (self._dd((op >> 4) & 3) + 1) & 0xFFFF)
        elif op in (0x0B, 0x1B, 0x2B, 0x3B):  # DEC dd (flagenként)
            self._wdd((op >> 4) & 3, (self._dd((op >> 4) & 3) - 1) & 0xFFFF)
        elif op in (0x09, 0x19, 0x29, 0x39):  # ADD HL,dd
            i = (op >> 4) & 3
            s = self.HL + self._dd(i)
            self.setC(s > 0xFFFF)
            self.HL = s & 0xFFFF
        elif 0x40 <= op <= 0x7F and op != 0x76:  # LD r,r'
            self.w8((op >> 3) & 7, self.r8(op & 7))
        elif 0x80 <= op <= 0xBF:  # ALU r/(HL)
            self.alu((op >> 3) & 7, self.r8(op & 7))
        elif op in (0xC6, 0xCE, 0xD6, 0xDE, 0xE6, 0xEE, 0xF6, 0xFE):  # ALU n
            self.alu((op >> 3) & 7, self.fetch())
        elif op in (0x04, 0x0C, 0x14, 0x1C, 0x24, 0x2C, 0x3C):  # INC r
            i = (op >> 3) & 7
            self.w8(i, (self.r8(i) + 1) & 0xFF)
            self.setZ(self.r8(i))
        elif op in (0x05, 0x0D, 0x15, 0x1D, 0x25, 0x2D, 0x3D):  # DEC r
            i = (op >> 3) & 7
            self.w8(i, (self.r8(i) - 1) & 0xFF)
            self.setZ(self.r8(i))
        elif op == 0x34:
            a = self.HL; self.store(a, (self.mem[a] + 1) & 0xFF); self.setZ(self.mem[a])
        elif op == 0x35:
            a = self.HL; self.store(a, (self.mem[a] - 1) & 0xFF); self.setZ(self.mem[a])
        elif op == 0xC3:  # JP nn
            self.PC = self.fetch() | (self.fetch() << 8)
        elif op in (0xC2, 0xCA, 0xD2, 0xDA, 0xE2, 0xEA, 0xF2, 0xFA):  # JP cc
            n = self.fetch() | (self.fetch() << 8)
            if self.cond((op >> 3) & 3):
                self.PC = n
        elif op == 0xCD or op in (0xC4, 0xCC, 0xD4, 0xDC, 0xE4, 0xEC, 0xF4, 0xFC):  # CALL
            n = self.fetch() | (self.fetch() << 8)
            cond = True
            if op != 0xCD:
                cond = self.cond((op >> 3) & 3)
            if cond:
                if n in self.hooks:
                    self.hooks[n](self)   # hook: nincs stack-nyomás, fut tovább
                else:
                    self.push((self.PC) & 0xFFFF)
                    self.PC = n
        elif op == 0xC9:  # RET
            self.PC = self.pop()
            if self.PC == 0:
                self.halted = "RET a 0 sentinelhez"
        elif op in (0xC0, 0xC8, 0xD0, 0xD8, 0xE0, 0xE8, 0xF0, 0xF8):  # RET cc
            if self.cond((op >> 3) & 3):
                self.PC = self.pop()
                if self.PC == 0:
                    self.halted = "RET a 0 sentinelhez"
        elif op in (0xC5, 0xD5, 0xE5, 0xF5):  # PUSH
            v = [self.BC, self.DE, self.HL, (self.A << 8) | self.F][(op >> 4) & 3]
            self.push(v)
        elif op in (0xC1, 0xD1, 0xE1, 0xF1):  # POP
            v = self.pop()
            i = (op >> 4) & 3
            if i == 0: self.BC = v
            elif i == 1: self.DE = v
            elif i == 2: self.HL = v
            else: self.A, self.F = (v >> 8) & 0xFF, v & 0xFF
        elif op == 0xCB:  # forgatások: CB 00-07 = RLC r, CB 10-17 = RL r
            sub = self.fetch()
            r = sub & 7
            v = self.r8(r)
            if sub < 0x08:    # RLC: forgatás balra, bit7 visszahordozva
                c = v >> 7; nv = ((v << 1) | c) & 0xFF; self.setC(c != 0)
            elif 0x10 <= sub < 0x18:  # RL: forgatás a carry-n keresztül
                c = v >> 7; nv = ((v << 1) | (1 if self.F & FC else 0)) & 0xFF; self.setC(c != 0)
            else:
                raise SimError(f"nem támogatott CB utasítás: CB {sub:02X} @ 0x{pc0:04X}")
            self.w8(r, nv); self.setZ(nv)
        elif op == 0xED:
            sub = self.fetch()
            if sub in (0xA0,):    # LDI
                self.store(self.DE, self.mem[self.HL])
                self.DE = (self.DE + 1) & 0xFFFF
                self.HL = (self.HL + 1) & 0xFFFF
                self.BC = (self.BC - 1) & 0xFFFF
            elif sub == 0xB0:     # LDIR
                while self.BC:
                    self.store(self.DE, self.mem[self.HL])
                    self.DE = (self.DE + 1) & 0xFFFF
                    self.HL = (self.HL + 1) & 0xFFFF
                    self.BC = (self.BC - 1) & 0xFFFF
            elif 0x40 <= sub <= 0x78 and (sub & 7) != 6 and (sub & 0xC7) == 0x40:  # IN r,(C)
                r = (sub >> 3) & 7
                bcv = self.BC
                v = self.in_hook(bcv) if self.in_hook else 0xFF
                self.w8(r, v); self.setZ(v)
            elif (sub & 0xC7) == 0x41 and (sub & 7) != 6:  # OUT (C),r — nincs kimenet
                pass
            elif sub in (0x42, 0x52, 0x62, 0x72):  # SBC HL,dd
                i = (sub >> 4) & 3
                r = self.HL - self._dd(i) - (1 if self.F & FC else 0)
                self.setC(r < 0); self.HL = r & 0xFFFF; self.setZ(self.HL)
            elif sub in (0x4A, 0x5A, 0x6A, 0x7A):  # ADC HL,dd
                i = (sub >> 4) & 3
                r = self.HL + self._dd(i) + (1 if self.F & FC else 0)
                self.setC(r > 0xFFFF); self.HL = r & 0xFFFF; self.setZ(self.HL)
            else:
                raise SimError(f"nem támogatott ED utasítás: ED {sub:02X} @ 0x{pc0:04X}")
        elif op == 0xEB:  # EX DE,HL
            self.DE, self.HL = self.HL, self.DE
        elif op == 0xE3:  # EX (SP),HL
            v = self.load16(self.SP); self.store16(self.SP, self.HL); self.HL = v
        elif op == 0x07:  # RLCA
            c = self.A >> 7; self.A = ((self.A << 1) | c) & 0xFF; self.setC(c != 0)
        elif op == 0x17:  # RLA
            c = self.A >> 7; self.A = ((self.A << 1) | (1 if self.F & FC else 0)) & 0xFF; self.setC(c != 0)
        elif op == 0x0F:  # RRCA
            c = self.A & 1; self.A = (self.A >> 1) | (c << 7); self.setC(c != 0)
        elif op == 0x1F:  # RRA
            c = self.A & 1; self.A = (self.A >> 1) | ((1 if self.F & FC else 0) << 7); self.setC(c != 0)
        elif op == 0x2F:  # CPL
            self.A ^= 0xFF
        elif op == 0x37:  # SCF
            self.setC(True)
        elif op == 0x3F:  # CCF
            self.setC(not (self.F & FC))
        elif op in (0xF3, 0xFB):  # DI/EI — itt nincs megszakításkezelés
            pass
        else:
            raise SimError(f"nem dekódolható opcode: {op:02X} @ 0x{pc0:04X}")
        return True

    def run(self):
        n = 0
        while not self.halted and n < self.max_steps:
            self.step()
            n += 1
        if not self.halted:
            self.halted = "lépéslimit"
        return n

# --- önteszt: z80asm-mal összeállított mintaprogramok futtatása ---
def _selftest():
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from z80asm import assemble

    def run(src, org=0x8000):
        code, _ = assemble(src, org)
        s = Z80Sim()
        s.mem[org:org + len(code)] = code
        s.SP = 0xFFFE
        s.push(0)          # RET-sentinel
        s.PC = org
        s.run()
        return s

    s = run("LD A,2\n ADD A,3\n LD (0x7000),A\n RET")
    assert s.mem[0x7000] == 5, "ALU hiba"

    s = run("LD B,5\n LD A,0\nL1: ADD A,B\n DJNZ L1\n LD (0x7001),A\n RET")
    assert s.mem[0x7001] == 15, "DJNZ hiba"

    s = run("SCF\n LD A,1\n RL A\n LD (0x7002),A\n PUSH AF\n POP BC\n LD A,C\n LD (0x7003),A\n RET")
    assert s.mem[0x7002] == 3, "RL hiba"          # 1 << 1 | carry=1 → 3
    assert s.mem[0x7003] & 0x01 == 0, "carry törölve (RL után C=0)"

    s = run("LD HL,0x1234\n LD (0x7004),HL\n LD HL,(0x7004)\n LD A,H\n LD (0x7005),A\n LD A,L\n LD (0x7008),A\n RET")
    assert s.mem[0x7005] == 0x12 and s.mem[0x7008] == 0x34, "16 bites LD round-trip hiba"

    # CALL-hook: a 0x034C-ra hívást Python függvény szolgálja ki
    src = "LD B,7\n CALL 0x034C\n LD A,C\n LD (0x7006),A\n RET"
    code, _ = assemble(src, 0x8000)
    s = Z80Sim()
    s.mem[0x8000:0x8000 + len(code)] = code
    s.SP = 0xFFFE; s.push(0); s.PC = 0x8000
    s.hooks[0x034C] = lambda sim: setattr(sim, "C", 0x42)
    s.run()
    assert s.mem[0x7006] == 0x42, "CALL-hook hiba"

    # JR cc: Z állítás CP-vel
    s = run("LD A,5\n CP 5\n JR NZ,BAD\n LD (0x7007),A\n RET\nBAD: XOR A\n LD (0x7007),A\n RET")
    assert s.mem[0x7007] == 5, "CP/JR Z hiba"

    print("Z80-szimulátor önteszt OK (6 mintaprogram)")

if __name__ == "__main__":
    _selftest()
