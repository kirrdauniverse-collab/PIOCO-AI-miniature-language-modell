"""PIOCO.WAV — szalag-audio (kazetta-hang) gyártó, SZABVÁNYOS ZX81-időzítéssel.

Miért? A .P gyorstöltője nem minden emulátorban van jelen, de szalag-hangfájlt
(WAV) szinte mindegyik tud olvasni: EightyOne ("Open Tape Image" a WAV-ra is),
ZEsarUX cassette, és maga a valódi ZX81 is.

SZABVÁNYOS ZX81 szalag-protokoll (Wikipedia/PZX-spec, a valós ROM SAVE
kinézete):
  impulzus = ~150 us magas + ~150 us mely      (487 tick @ 3.25 MHz)
  bit '0'  = 4 impulzus
  bit '1'  = 9 impulzus
  bit UTÁN ~1300 us CSEND                      (4225 tick @ 3.25 MHz)
  MSB megy előre; bájt = 8 bit.

Változás (v2.6e): a korábbi bitközi csend 2000 tick = 615 us VOLT — ez a
szabvány felét se éri el, és pont ez okozhatta, hogy a EightyOne szalag-
beolvasója (valós v1 ROM-mal dolgozik) nem ismerte fel a biteket. Az új
alap a szabványos 1300 us. A ROM-alapú szalag_teszt ezzel az értékkel
fut újra, amint a /tmp/zx81.rom elérhető.

A generátor mellett SZIGORÚ WAV-DEKÓDOLÓ is van (wav_olvas): küszöbös
él-érzékeléssel visszaolvasza a b biteket, és a hívó bájtpontosan
összevetheti a szalag-streammel (roundtrip-igazolás).

Futtatás:
    python3 t81_wav.py <PIOCO.T81> <ki.WAV> [rate]
    python3 t81_wav.py --ellenoriz <PIOCO.T81> <PIOCO.WAV>

A kimenő fájl 8 bites mono WAV (22050 Hz), kb. 7 perc 15 868 bájtra.
"""

import sys
import wave

TICKS = 3_250_000          # ZX81 takt
PULSE_HALF = 487           # ~150 us fél-impulzus (487 tick @ 3.25 MHz)
BIT_GAP = 4225             # 1300 us bitközi csend (SZABVÁNY, v2.6e-től)
LEAD_IN = 2.0              # s — bő eleje-csend a szalagmotor szinkronhoz
LEAD_OUT = 2.0             # s — vége-csend (a ROM IN-BYTE timeout-a miatt)
MAGAS, MELY, KUSZOB = 200, 64, 128   # WAV-amplitúdók és él-érzékelő küszöb


def kontener_stream(path):
    with open(path, "rb") as f:
        kaz = f.read()
    assert kaz[:4] == b"EO81", "nem EO81 kontener"
    hossz = int(kaz[36:52].decode("ascii"))
    stream = kaz[52:52 + hossz]
    assert len(stream) == hossz, "blokk levágva"
    return stream


def stream_hossz_minta(stream, rate):
    """Előre kiszámolja a mintaszámot (ugyanazzal a tick-számlálással)."""
    ossz_tick = int(LEAD_IN * TICKS)
    for bajt in stream:
        for i in range(7, -1, -1):
            n = 9 if (bajt >> i) & 1 else 4
            ossz_tick += n * 2 * PULSE_HALF + BIT_GAP
    ossz_tick += int(LEAD_OUT * TICKS)
    return int(round(ossz_tick / TICKS * rate))


def wav_general(stream, rate):
    n_smp = stream_hossz_minta(stream, rate)
    smp = bytearray([MELY]) * n_smp

    t = LEAD_IN * TICKS
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


def wav_olvas(path, rate):
    """Szigorú dekódoló: a WAV-ból visszaolvasva a bájt-sorstreameket.

    Ugyanazokat az időzítés-konstansokat használja, mint a generátor:
    a mintavételi pontokat a várt T-időkből nyeri, így ez tényleges
    roundtrip-igazolás (ha akárcsak egy bit elcsúszna, itt elszállna).
    """
    with wave.open(path, "rb") as w:
        assert w.getnchannels() == 1 and w.getsampwidth() == 1, "nem 8-bit mono"
        fr = w.getframerate()
        smp = w.readframes(w.getnframes())
    assert fr == rate, f"mintavételezés {fr} != {rate}"
    hossz = len(smp)

    def szint(tick):
        i = int(round(tick / TICKS * rate))
        return 1 if i < hossz and smp[i] >= KUSZOB else 0

    ki = bytearray()
    t = LEAD_IN * TICKS
    while True:
        if int(t / TICKS * rate) >= hossz - 1000:
            break
        # bájt: 8 bit, MSB előre; mindegyik bit n impulzusból indul
        bajt = 0
        jo = True
        for i in range(7, -1, -1):
            # az impulzus a MAGAS fél szakaszban kezdődik
            if szint(t) == 0:
                jo = False
                break
            n = 0
            while n < 9:
                if szint(t + PULSE_HALF // 2):
                    n += 1
                    t += 2 * PULSE_HALF
                else:
                    break
            if n not in (4, 9):
                jo = False
                break
            bajt |= (1 if n == 9 else 0) << i
            t += BIT_GAP
        if not jo:
            break
        ki.append(bajt)
    return bytes(ki)


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--ellenoriz":
        stream = kontener_stream(sys.argv[2])
        vissza = wav_olvas(sys.argv[3], 22050)
        assert vissza == stream, (
            f"roundtrip HIBA: {len(vissza)} bájt / várt {len(stream)}")
        print(f"Roundtrip OK: {len(vissza)} bájt bájtpontosan visszakerült")
        return
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
    visszatest = wav_olvas(ki, rate)
    assert visszatest == stream, "roundtrip HIBA a most gyártott WAV-on"
    print(f"Dekódoló-igazolás OK: {len(visszatest)} bájt bájtpontosan visszamegy")


if __name__ == "__main__":
    main()
