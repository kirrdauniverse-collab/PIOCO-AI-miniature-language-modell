# -*- coding: utf-8 -*-
"""PIOCO AI — zvaloditest.py: a .P fájl tesztelése VALÓDI emulátorban
(ZEsarUX, headless, ZRCP távvezérelt).

Futás:  python3 eszkozok/zvaloditest.py [pfile] [--tape]

Alapértelmezés: --snap út (a fájl memóriakép-betöltése), majd RUN + ENTER
billentyű-injektálás ZRCP-n keresztül, a PC és a képernyő (D_FILE)
kiolvasása. A --tape út a ROM-os szalagbetöltést gyakorolja
(--fastautoload). Kimenet: a regiszterek, a D_FILE-mutató és a képernyő
dekódolt szövege.
"""
import os
import socket
import subprocess
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZESARUX = "/tmp/zesarux/src/zesarux"
PORT = 12123

# a bevált dekódoló a szimfuttatasból (a motor ASCTBL-jével ellenőrzött)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import szimfuttatas as _szim                # noqa: E402
ZX2TXT = _szim.ZX2TXT


def recv_until(sock, tag="OK", timeout=6.0):
    sock.settimeout(timeout)
    buf = b""
    end = time.time() + timeout
    while time.time() < end:
        try:
            d = sock.recv(65536)
            if not d:
                break
            buf += d
            tail = buf[-200:].decode("utf-8", "replace")
            if tail.rstrip().endswith(tag) or "ERROR" in tail:
                break
        except socket.timeout:
            break
    return buf.decode("utf-8", "replace")


def send(sock, cmd):
    sock.sendall((cmd + "\n").encode())
    return recv_until(sock)


def main():
    pfile = os.path.join(BASE, "kazetta", "pioco-0.6.p")
    tape_mode = "--tape" in sys.argv
    for a in sys.argv[1:]:
        if a.endswith(".p"):
            pfile = a
    if not os.path.exists(ZESARUX):
        print(f"HIÁNYZIK: {ZESARUX} — előbb fel kell építeni!")
        return 1

    args = [ZESARUX, "--noconfigfile", "--ao", "null", "--vo", "null",
            "--machine", "ZX81", "--cpuspeed", "400",
            "--enable-remoteprotocol", "--remoteprotocol-port", str(PORT),
            "--exit-after", "120"]
    if tape_mode:
        args += ["--realtape", pfile, "--fastautoload"]
    else:
        args += ["--snap", pfile]
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    sock = None
    for _ in range(60):
        time.sleep(0.3)
        try:
            sock = socket.create_connection(("127.0.0.1", PORT), timeout=2)
            break
        except OSError:
            continue
    if sock is None:
        print("Nem jött létre a ZRCP-kapcsolat!")
        proc.kill()
        return 1
    print("ZRCP kapcsolat OK")
    send(sock, "get-version")

    if not tape_mode:
        print("\n--- RAMTOP (0x4004) ---")
        hd = send(sock, "hexdump 0x4004 2")
        for ln in hd.splitlines():
            if "4004" in ln or "4004H" in ln:
                print(" ", ln.strip())
        print("\n--- billentyűk: ENTER, R (=RUN kulcsszó K-módban), ENTER ---")
        send(sock, "send-keys-ascii 60 13")
        send(sock, "send-keys-string 60 R")
        send(sock, "send-keys-ascii 60 13")

    time.sleep(4)          # ~16 s gépidő a 400%-os sebességgel

    print("\n--- regiszterek ---")
    regs = send(sock, "get-registers")
    for ln in regs.splitlines():
        if any(k in ln for k in ("PC", "SP", "I", "R")):
            print(" ", ln.strip())

    print("\n--- D_FILE-mutató (0x400C) ---")
    hd = send(sock, "hexdump 0x400C 4")
    for ln in hd.splitlines():
        if "400C" in ln or "400c" in ln:
            print(" ", ln.strip())

    # a D_FILE-ból olvassuk ki a képernyő címét, és ott dumpoljunk
    dfile = 0x4200
    hd = send(sock, "hexdump 0x400C 2").splitlines()
    for ln in hd:
        if "400C" in ln or "400c" in ln:
            body = ln.split(":", 1)[1].split("|")[0].split() if ":" in ln else []
            if len(body) >= 2:
                try:
                    dfile = int(body[0], 16) | (int(body[1], 16) << 8)
                except ValueError:
                    pass
    print(f"\n--- képernyő (D_FILE=0x{dfile:04X}, 826 B) ---")
    hd = send(sock, f"hexdump 0x{dfile:04X} 826")
    raw = bytearray()
    for ln in hd.splitlines():
        # a hexdump sorai: "cím: hh hh ... |ascii|"
        body = ln.split(":", 1)[1] if ":" in ln else ln
        for tok in body.split("|")[0].split():
            if len(tok) == 2 and all(ch in "0123456789ABCDEFabcdef" for ch in tok):
                try:
                    raw.append(int(tok, 16))
                except ValueError:
                    pass
    print(f"  beolvasott bájtok: {len(raw)}")
    if len(raw) >= 826:
        for row in range(25):
            line = raw[row * 33:row * 33 + 32]
            txt = "".join(ZX2TXT.get(b & 0x3F, "#") for b in line)
            print("  |" + txt + "|")

    sock.close()
    proc.terminate()
    proc.wait()
    return 0


if __name__ == "__main__":
    sys.exit(main())
