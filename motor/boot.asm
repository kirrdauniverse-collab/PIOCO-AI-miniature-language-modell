; ============================================================
; PIOCO AI — motor/boot.asm — 1. szakasz (karcsú BOOT-betöltő)
; Belépés: RAND USR 16514 (0x4082) — REM-sori gépi kód
; KORLÁT: a kódnak a 0x4200-as D_FILE-zóna ELŐTT kell véget érnie
;         (max 0x4200-0x4082 = 382 B) — ezt az epites.py érvényesíti
;
; Forrás-anchors (hitelesítve, l. FEJLESZTESI-NAPLO.md):
;   - ROM IN-BYTE: 0x034C (a bájt a C regiszterben) — ZX81 ROM listing
;   - gépi kód belépési cím: 16514 = 0x4082 (REM sor) — andrivet
;   - saját D_FILE UI: 0x4200, 24 × (32 + 0x76) = 792 B — fázis-2 5.2
;   - PERSIST: 0x4100, mágia 'P','C', verzió, CRC-16 (0x1021, 0xFFFF)
;
; NYÍLT TÉTELEK (emulátor-ellenőrzés a következő körben):
;   - IN-BYTE szinkron/pilot-kezelés blokkhatárokon
;   - IN-BYTE regiszter-megőrzése (HL/DE feltételezett — a ROM-lista
;     szerint a bájt C-ben érkezik; AF felülírása biztos)
;   - a D_FILE rendszerváltozó-mutató beírása (sysvars-cím) — nem írjuk
;
; Menet: képernyő-nullázás → PERSIST init → következő blokk (típus 2,
; MOTOR) betöltése a 0x4600-ra → átugrás oda. A további blokkokat a
; stage-2 motor hívja be (CALL az itt rögzített LOADBLK címre).
; ============================================================

INBYTE  EQU 0x034C        ; ROM: bájt a szalagról → C
DFILE   EQU 0x4200
PERSIST EQU 0x4100
STG2    EQU 0x4600

        ORG 0x4082
BOOT:
        CALL SCRFILL
        CALL PERSISTINIT
        CALL LOADBLK           ; következő blokk = PIOCOTIP2 → 0x4600
        JP STG2

; ---- képernyő: 24 sor × (32 db 0x00 + 0x76) = 792 B ----
SCRFILL:
        LD HL,DFILE
        LD B,24
SCRL:   LD C,32
SCRC:   LD (HL),0
        INC HL
        DEC C
        JR NZ,SCRC
        LD (HL),0x76
        INC HL
        DJNZ SCRL
        RET

; ---- PERSIST init: mágia + verzió + nullázás + CRC-16 ----
PERSISTINIT:
        LD HL,PERSIST
        LD (HL),0x50          ; 'P'
        INC HL
        LD (HL),0x43          ; 'C'
        INC HL
        LD (HL),0x01          ; verzió
        INC HL
        LD BC,0x00FA          ; 0x04..0xFD nullázás (250 B)
        LD A,0
PZL:    LD (HL),A
        INC HL
        DEC BC
        LD A,B
        OR C
        JR NZ,PZL
        LD HL,PERSIST
        LD BC,0x00FC          ; CRC a 0x00..0xFB felett (252 B)
        CALL CRCGO
        LD HL,PERSIST + 0xFC
        LD A,E                ; CRC little-endian (lo, hi)
        LD (HL),A
        INC HL
        LD A,D
        LD (HL),A
        RET

; ---- CRC-16/CCITT (0x1021, init 0xFFFF) ----
; CRCGO: HL=ptr, BC=hossz → CRC a DE-ben; CRCUPD: DE futó CRC-vel folytat
; a bennfoglalási korlát miatt bitciklusos változat (a CRCN scratch-et használja)
CRCGO:
        LD DE,0xFFFF
CRCUPD:
CRCL:   LD A,(HL)
        XOR D
        LD D,A
        LD A,8
        LD (CRCN),A
CRCB:   RL E
        RL D
        JR NC,CRCA
        LD A,E
        XOR 0x21
        LD E,A
        LD A,D
        XOR 0x10
        LD D,A
CRCA:   LD A,(CRCN)
        DEC A
        JR Z,CRCNXT
        LD (CRCN),A
        JR CRCB
CRCNXT: INC HL
        DEC BC
        LD A,B
        OR C
        JR NZ,CRCL
        RET

; ---- blokk betöltése a szalagról (ROM IN-BYTE) ----
; fejléc 4 B: [típus][verzió][len_lo][len_hi] → célcím a TBL-ből → adat → CRC
; hibánál (ismeretlen típus / CRC) visszatérés nyomtatás nélkül
LOADBLK:
        LD HL,HDR
        CALL RD4
        LD A,(HDR)
        LD HL,TBL
        LD B,4
TBLF:   CP (HL)
        JR Z,TBLH
        INC HL
        INC HL
        INC HL
        DJNZ TBLF
        RET                   ; ismeretlen típus
TBLH:   INC HL
        LD D,(HL)
        INC HL
        LD E,(HL)
        LD A,D
        LD (TGT),A
        LD A,E
        LD (TGT + 1),A
        LD A,(HDR + 2)
        LD (LENW),A
        LD A,(HDR + 3)
        LD (LENW + 1),A
        LD HL,(LENW)
DRL:    CALL INBYTE
        LD A,C
        LD (DE),A
        INC DE
        DEC HL
        LD A,H
        OR L
        JR NZ,DRL
        LD HL,HDR
        LD BC,4
        CALL CRCGO
        LD HL,(TGT)
        LD A,(LENW)
        LD C,A
        LD A,(LENW + 1)
        LD B,A
        CALL CRCUPD
        CALL INBYTE
        LD A,C
        LD (CRCRX),A
        CALL INBYTE
        LD A,C
        LD (CRCRX + 1),A
        LD A,(CRCRX)
        CP E
        JR NZ,LBAD
        LD A,(CRCRX + 1)
        CP D
        JR NZ,LBAD
        RET
LBAD:   RET                   ; CRC-hiba (hibajelzés a stage-2-ben)

RD4:    LD B,4
RD4L:   CALL INBYTE
        LD A,C
        LD (HL),A
        INC HL
        DJNZ RD4L
        RET

; ---- adatterületek (a 0x4200 alatt maradnak) ----
TBL:    DB 2,0x46,0x00        ; típus 2 → 0x4600 (MOTOR)
        DB 3,0x54,0x00        ; típus 3 → 0x5400 (SZÓTÁR)
        DB 4,0x63,0x00        ; típus 4 → 0x6300 (ALAPMAG)
        DB 5,0x6B,0x00        ; típus 5 → 0x6B00 (CSOMAG)
HDR:    DB 0,0,0,0
TGT:    DB 0,0
LENW:   DB 0,0
CRCRX:  DB 0,0
CRCN:   DB 0
