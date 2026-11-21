"""Fej nélküli ZX81 szimulátor — valódi 8K ROM-mal tesztel.

Cél: a PIOCO.T81 betöltési útjának végponttól végpontig valódi
ellenőrzése: ROM LOAD rutin (0x0347, D=0x80 null-név) + saját
szalag-protokoll az EAR vonalon.

A ZX81 ROM bináris (szerzői jogvédett) NEM kerül a repóba; a sim a
környezet változóiban megadott helyen várja (pl. /tmp/zx81.rom).
A kosarev/z80 Python-emulátort használja (pip install z80).

Szalag-protokoll (a ROM saját OUT-BYTE karakterisztikája alapján):
  - impulzus: ~150 us magas + ~150 us mély (a ROM B=$23 / B=$1E késleltetései)
  - 0-bit: 4 impulzus, 1-bit: 9 impulzus, bit után ~1 ms mély (DELAY-4)
  - bájt = 8 bit, felülről lefelé sorban (a ROM RL C-vel alulról tölti,
    így az előbb jövő bit kerül feljebb — MSB-first lejátszás)
  - blokk előtt hosszú csend (>= 5.2 ms kell a ROM TIMEOUT-hoz,
    gyakorlatilag 22 ms), a csend alatt EAR = alacsony

Olvasási részletek (Wearmouth listázás):
  - IN ($FE): 0-4. bitek = billentyűoszlopok (lenyomva = 0),
    5-6 = felhúzott (1), 7. bit = EAR szalagjel
  - BREAK-3 a $7FFE porttal a SPACE sort olvassa (0. oszlop)

Használat:
    sim = ZX81Sim("/tmp/zx81.rom", tape_bytes)
    sim.boot()
    ...
"""

CLOCK = 3_250_000          # ZX81 órajel (Hz)

PULSE_HALF_US = 150        # ROM: B=$23 magas, B=$1E mély félidő
BIT_GAP_US = 1030          # ROM: DELAY-4 (DJNZ 256 x 13 ciklus)
LEAD_IN_US = 22_000        # csend a blokk elején (a ROM TIMEOUT-hoz elég)
LEAD_OUT_US = 22_000       # csend a blokk végén


def us_to_ticks(us):
    return int(us * CLOCK / 1_000_000)


class ZX81Sim:
    """ZX81 gép: 8K ROM saját 0x0000-től, 16K RAM 0x4000-től."""

    def __init__(self, rom_path):
        import z80

        rom = open(rom_path, "rb").read()
        assert len(rom) == 0x2000, f"ROM méret: {len(rom)} (0x2000 kell)"

        self.m = z80.Z80Machine()
        self.m.set_get_int_vector_callback(lambda: 0x0038)

        mem = self.m.memory
        mem[0x0000:0x2000] = rom
        mem[0x2000:0x4000] = b"\xff" * 0x2000   # itt nincs RAM (olvasva 0xFF)
        mem[0x4000:0x8000] = b"\x00" * 0x4000   # 16K RAM

        self.pressed = set()      # {(sorbájt, oszlopbit), pl. (0x7F, 0x01)}
        self.keylog = []
        self.ear_level = 0
        self.ear_timeline = [(-1, 0)]   # [(váltás-tick, szint)]
        self._ear_idx = 0
        self._last_frame = 0
        self.ticks = 0
        self.io_in = 0            # IN ($FE) hívások száma

        self.m.set_input_callback(self._input)
        self.m.set_output_callback(self._output)

    # ---- I/O ----

    def _input(self, port):
        if (port & 0xFF) == 0xFE:
            self.io_in += 1
            row = (port >> 8) & 0xFF
            val = 0x1F
            if self.pressed and (row & 0x1E == 0):
                for r, cb in self.pressed:
                    if r == row:
                        val &= ~cb & 0xFF
            if self.ear_level:
                val |= 0x80
            return val | 0x60
        return 0xFF

    def _output(self, port, value):
        # OUT ($FD)/($FE): NMI-generátor, OUT ($FF): képernyőport —
        # a betöltés-teszthez nem játszik szerepet
        pass

    # ---- EAR szalag ----

    def ear_at(self, tick):
        """EAR-szint az adott tickpillanatban (kurzorral, monotón futáshoz)."""
        tv = self.ear_timeline
        i, n = self._ear_idx, len(tv)
        while i + 1 < n and tv[i + 1][0] <= tick:
            i += 1
        self._ear_idx = i
        return tv[i][1]

    def add_ear_segment(self, us, level):
        """Új EAR-darab hozzáadása a szalag jelenlegi végéhez."""
        self.ear_timeline.append((self.ticks + us_to_ticks(us), level))

    # ---- futtatás ----

    def _advance(self):
        ft = self.m.frame_tick
        delta = (ft - self._last_frame) % 100_000
        self._last_frame = ft
        self.ticks += delta

    def run_for(self, us, stop_pc=None):
        """Futtat legfeljebb us mikroszekundumot; korábban megáll,
        ha stop_pc-re ért. Visszatérés: True, ha stop_pc eltalálva.

        A csoportméret ~36 us: az EAR-szint ennyi pontossággal követi a
        szalagot, ami bőven a 150 us-os impulzusok alatti felbontás."""
        hatar = self.ticks + us_to_ticks(us)
        group = 120
        while self.ticks < hatar:
            self.m.ticks_to_stop = min(group, hatar - self.ticks)
            self.m.run()
            self._advance()
            self.ear_level = self.ear_at(self.ticks)
            if self.m.halted and self.m.iff1:
                self.m.on_handle_active_int()
            if stop_pc is not None and self.m.pc == stop_pc:
                return True
        return False

    def boot(self, ticks=40_000_000):
        """Reset (0x0000) + RAM-CHECK + INITIAL. Az utolsó PC-vel tér vissza.

        A SLOW módban várakozó gépet INT-tel ébresztgeti (FRAMES számol)."""
        self.m.pc = 0x0000
        stop = self.ticks + ticks
        while self.ticks < stop:
            self.m.ticks_to_stop = 200
            self.m.run()
            self._advance()
            self.ear_level = self.ear_at(self.ticks)
            if self.m.halted and self.m.iff1:
                self.m.on_handle_active_int()
        return self.m.pc

    # ---- segédek ----

    def word(self, addr):
        return self.m.memory[addr] | (self.m.memory[addr + 1] << 8)

    def set_word(self, addr, value):
        mem = self.m.memory
        mem[addr] = value & 0xFF
        mem[addr + 1] = (value >> 8) & 0xFF

    def dump_state(self):
        mem = self.m.memory
        return {
            "pc": hex(self.m.pc), "sp": hex(self.m.sp),
            "halted": self.m.halted, "iff1": self.m.iff1,
            "ticks": self.ticks,
            "VERSN": hex(mem[0x4009]),
            "E_PPC": hex(self.word(0x400A)),
            "D_FILE": hex(self.word(0x400C)),
            "DF_CC": hex(self.word(0x400E)),
            "VARS": hex(self.word(0x4010)),
            "DEST": hex(self.word(0x4012)),
            "E_LINE": hex(self.word(0x4014)),
            "X_PTR": hex(self.word(0x4016)),
            "STKBOT": hex(self.word(0x4018)),
            "STKEND": hex(self.word(0x401A)),
            "FLAGS": hex(mem[0x401F]),
            "FRAMES": hex(self.word(0x4020)),
            "CDFLAG": hex(mem[0x403B]),
            "RAMTOP": hex(self.word(0x4004)),
        }


# ---- szalag-kodolo (bitprotokoll, tick-domaint hasznal) ----

def stream_to_ear(stream, pulse_half=487, bit_gap=2000,
                  lead_in=25_000, lead_out=2000):
    """EAR atmenetsor keszitese bajsorból: [(tick, szint)].

    A szint alapertelmezésen 0 (csend). Bit = 4 (0) vagy 9 (1) db
    impulzus, mindegyik pulse_half magas + pulse_half mely; bit után
    bit_gap csend. Szinkronizálás: MSB megy eloszor."""
    transitions = [(0, 0)]
    t = lead_in
    for byte in stream:
        for i in range(7, -1, -1):
            n = 9 if (byte >> i) & 1 else 4
            for _ in range(n):
                transitions.append((t, 1)); t += pulse_half
                transitions.append((t, 0)); t += pulse_half
            t += bit_gap
    transitions.append((t, 0))
    return transitions


def set_tape(sim, transitions):
    """Az atmenetsort a szimulátor jelenlegi tickjére illeszti."""
    off = sim.ticks
    sim.ear_timeline = [(-1, 0)] + [(t + off, l) for t, l in transitions]
    sim._ear_idx = 0
    sim.ear_level = 0
