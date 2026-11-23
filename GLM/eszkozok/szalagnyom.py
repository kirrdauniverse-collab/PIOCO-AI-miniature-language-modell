# -*- coding: utf-8 -*-
"""A szalag-út kisodródásának mélynyomkövetése: PC-nyom + írás-napló a
0x4600-as motor-zónára + a fejléc-olvasások követeése."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from z80sim import Z80Sim, SimError        # noqa: E402
from csomaggen import parse_and_verify     # noqa: E402
import szimfuttatas as sz                  # noqa: E402


def main():
    boot = open(os.path.join(sz.ADAT, "boot.bin"), "rb").read()
    motor0 = open(os.path.join(sz.ADAT, "motor0.bin"), "rb").read()
    tape = open(sz.TAPE, "rb").read()
    blocks = parse_and_verify(tape)
    assert blocks[0][0] == 1
    stream = bytearray()
    for (ttype, ver, n, crc, _) in blocks[1:]:
        stream += sz.tape_chunk(tape, ttype, n)
    print(f"stream: {len(stream)} B; blokkok: {[b[0] for b in blocks]}")

    pos = [0]
    hdr_log = []

    def inbyte(sim_):
        if pos[0] >= len(stream):
            raise RuntimeError("szalag-kimerülés")
        sim_.C = stream[pos[0]]
        if pos[0] % 2000 == 0 or pos[0] < 8:
            hdr_log.append((pos[0], sim_.C, f"SP=0x{sim_.SP:04X} PC=0x{sim_.PC:04X}"))
        pos[0] += 1

    sim = Z80Sim()
    sim.mem[0x4082:0x4082 + len(boot)] = boot
    sim.SP = 0x7FFE
    sim.push(0)
    sim.PC = 0x4082
    sim.hooks[0x034C] = inbyte

    hist = []
    m0_writes = []                     # (sor, cím, érték) a 0x4600-0x469F-be
    try:
        while not sim.halted and len(hist) < 400000:
            hist.append(sim.PC)
            pc0 = sim.PC
            sim.step()
            for a, v in sim.writes[-4:]:
                if 0x4600 <= a <= 0x469F:
                    m0_writes.append((len(hist), a, v, pc0))
        print("futás vége:", sim.halted, "lépések:", len(hist))
    except SimError as e:
        print(f"SimError: {e}")
    print(f"szalag-pozíció: {pos[0]}/{len(stream)}")
    print("PC-nyom (utolsó 60):", " ".join(f"{p:04X}" for p in hist[-60:]))
    print("fejléc-log (első 12):", hdr_log[:12])
    print(f"írások a motor-zónába (első 12 / {len(m0_writes)}):")
    for row, a, v, pc0 in m0_writes[:12]:
        print(f"  lépés {row}: [0x{a:04X}] = 0x{v:02X} (PC=0x{pc0:04X})")
    print("mem 0x4600-0x4621:", " ".join(f"{b:02X}" for b in sim.mem[0x4600:0x4622]))
    print("motor0.ref      :", " ".join(f"{b:02X}" for b in motor0[:34]))


if __name__ == "__main__":
    main()
