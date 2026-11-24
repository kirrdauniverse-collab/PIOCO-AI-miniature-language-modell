"""PIOCO.WAV — szalag-audio (kazetta-hang) gyártó.

Miért? A .P gyorstöltője nem minden emulátorban van jelen, de
szalag-hangfájlt (WAV) szinte mindegyik tud olvasni: EightyOne
"Open Tape Image", ZEsarUX cassette, és maga a valódi ZX81 is.

A signal PONTOSAN az az idozítés, amit a tesztek/zx81sim.py stream_to_ear()
a valodic ZX81 ROM-mal bajtpontosan igazolt (szalag_teszt, kazetta_teszt):
  bit '1' = 9 darab impulzus; bit '0' = 4 darab impulzus;
  impulzus = 487 tick magas + 487 tick mely (@3.25 MHz, azaz 300 us/per)
  bitenkenti 2000 tick csend. MSB elore.
Elejere ~0.6 s, vegere ~1 s csend (a ROM IN-BYTE TIMEOUT --a miatt kotelezo).

Futtatas:
    python3 t81_wav.py <PIOCO.T81> <ki.WAV> [rate]

A kimeno fajl 8-bitos mono WAV (22050 Hz), kb. 5-6 perc 15921 bajtra.
"""

import sys
import wave

TICKS = 3_250_000          # ZX81 takt
PULSE_HALF = 487           # fél-impulzus tickje (300 us/per impulzus)
BIT_GAP = 2000             # bit utáni csend (tick)
SYNC_JEL = 0               # (a ROM nem var kulon sync-jet)
LEAD_IN = 0.6              # s
LEAD_OUT = 1.0             # s
MAGAS, MELY = 200, 64      # WAV-amplitudó


def kontener_stream(path):
    with open(path, "rb") as f:
        kaz = f.read()
    assert kaz[:4] == b"EO81", "nem EO81 kontener"
    hossz = int(kaz[36:52].decode("ascii"))
    stream = kaz[52:52 + hossz]
    assert len(stream) == hossz, "blokk levagva"
    return stream


def wav_general(stream, rate):
    # hossz tickben:
    ossz_tick = int(LEAD_IN * TICKS)
    for bajt in stream:
        for i in range(7, -1, -1):
            n = 9 if (bajt >> i) & 1 else 4
            ossz_tick += n * 2 * PULSE_HALF + BIT_GAP
    ossz_tick += int(LEAD_OUT * TICKS)
    n_smp = int(round(ossz_tick / TICKS * rate))
    smp = bytearray([MELY]) * n_smp

    hedge = LEAD_IN * TICKS
    t = hedge
    for bajt in stream:
        for i in range(7, -1, -1):
            n = 9 if (bajt >> i) & 1 else 4
            for _ in range(n):
                a = int(round(t / TICKS * rate))
                b = int(round((t + PULSE_HALF) / TICKS * rate))
                for j in range(a, min(b, n_smp)):
                    smp[j] = MAGAS
                t += PULSE_HALF
                a = int(round(t / TICKS * rate))
                b = int(round((t + PULSE_HALF) / TICKS * rate))
                for j in range(a, min(b, n_smp)):
                    smp[j] = MELY
                t += PULSE_HALF
            t += BIT_GAP
    return bytes(smp)


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    be, ki = sys.argv[1], sys.argv[2]
    rate = int(sys.argv[3]) if len(sys.argv) > 3 else 22050
    stream = kontener_stream(be)
    smp = wav_general(stream, rate)
    with wave.open(ki, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(1)
        w.setframerate(rate)
        w.writeframes(smp)
    import os
    print(f"WAV: {ki}: {len(smp)} minta, {os.path.getsize(ki)/1e6:.1f} MB, "
          f"{len(smp)/rate:.0f} s, {rate} Hz 8-bit mono")


if __name__ == "__main__":
    main()
