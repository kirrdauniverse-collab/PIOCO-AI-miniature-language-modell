; ============================================================
; PIOCO AI — motor/boot.asm — 1. szakasz (karcsú BOOT-betöltő)
; Belépés: RAND USR 16514 (0x4082) — REM-sori gépi kód
; KORLÁT: a kódnak a 0x4200-as D_FILE-zóna ELŐTT kell véget érnie
;         (max 0x4200-0x4082 = 382 B) — ezt az epites.py érvényesíti
;
; Forrás-anchors (hitelesítve, l. FEJLESZTESI-NAPLO.md):
;   - ROM IN-BYTE: 0x034C (a bájt a C regiszterben) — ZX81 ROM listing
;   - gépi kód belépési cím: 16514 = 0x4082 (REM sor) — andrivet
;   - saját D_FILE UI: 0x4200, ROM-standard 25×33 + 1 = 826 B — 5.2 (D-3.4)
;   - PERSIST: 0x7E00, mágia 'P','C', verzió, CRC-16 (0x1021, 0xFFFF) — D-3.8
;
; NYÍLT TÉTELEK (emulátor-ellenőrzés):
;   - IN-BYTE szinkron/pilot-kezelés blokkhatárokon (szalag mód)
;   - IN-BYTE regiszter-megőrzése (HL/DE feltételezett; AF felülírása biztos)
;
; Menet: veremváltás (LD SP,0x5400 — D-3.5: a ROM vereme a RAM tetején
;   áll, a PERSIST-init nullázása összeomlasztaná; a saját verem a
;   MOTOR zóna tetején fut, bőven a kód fölött) → PERSIST init →
;   üzemmód (BOOTMODE):
;   0 = SZALAG: következő blokk (típus 2, MOTOR) betöltése 0x4600-ra;
;   1 = REZIDENS (.P terjesztés): a .P adatterületének (a program után,
;   az összezsugorított képernyő előtt) másolása a végleges címekre
;   (RESCOPY) — szalagolvasás nélkül.
; → képernyő-nullázás (ROM-standard 25 sor + záró 0x76 = 826 B) →
;   D_FILE/DF_CC sysvar-mutatók a saját képernyőre (címek hitelesítve a
;   zmakebas ZX81 fejléc-receptjéből: D_FILE @0x400C, DF_CC @0x400E) →
;   átugrás a 0x4600-ra.
;
; REM-HORDOZÁSI KORLÁT (D-3.6, a C/6-os hibajelentés utómunkálata):
;   a boot az 1. soros REM-testben utazik, a 0x76 bájt a sorban
;   közvetlenül nem szerepelhet (a ROM sornak tekintené) — a kód
;   0x76-mentességét az epites.py is ellenőrzi; a képernyő 0x76-os
;   bájtjai ezért aritmetikailag állnak elő (0x3B + RLCA = 0x76).
; ============================================================

INBYTE  EQU 0x034C        ; ROM: bájt a szalagról → C
DFILE   EQU 0x4200
XORKEY  EQU 0x40           ; D-3.9: a .P adathordozó ezzel XOR-olt bájtokként
                          ; utazik — a 0x80 a .P fájlformátumban a VARS-záró,
                          ; ezért a fájltestben egyetlen 0x80 sem szerepelhet
                          ; (a pgen.py kapuja érvényesíti); a szalag-mód
                          ; blokkjai nyersen utaznak (nincs 0x80-korlát)
PERSIST EQU 0x7E00        ; D-3.8: a 0x7F00-ról ide költözött — a ROM listája
                          ; szerint a gép vereme (SP=0x7FFE), az ERR_SP
                          ; (0x7FFC) és a NMI képkockánkénti mentései
                          ; (0x7FF4-0x7FFB) a RAM legtetején élnek; a 0x7F00+
                          ; terület a ROM-é marad (voltaképpeni D-3.3 hiba)
STG2    EQU 0x4600

        ORG 0x4082
BOOT:
        LD SP,0x5400           ; D-3.5: saját verem a MOTOR zóna tetején
        CALL PERSISTINIT
        LD A,(BOOTMODE)
        OR A
        JR Z,BTAPE
        CALL RESCOPY           ; rezidens mód: .P adatterület → végleges címek
        CALL SCRFILL
        JR BDFSET
BTAPE:  CALL LOADBLK           ; szalag mód: PIOCOTIP2 → 0x4600
        CALL SCRFILL
BDFSET: LD HL,0x400D           ; D_FILE ← 0x4200 (felső bájt először, hogy a
        LD (HL),0x42           ; NMI felfeslett mutatót ne lásson)
        DEC HL
        LD (HL),0x00
        LD HL,0x400F           ; DF_CC ← 0x4201 (ugyanígy)
        LD (HL),0x42
        DEC HL
        LD (HL),0x01
        JP STG2

; ---- képernyő: ROM-standard 25 sor × (32×0x00 + 0x76) + záró 0x76 = 826 B ----
; (24 tartalmi sor + 1 alsó sor; a záró 0x76 @0x4539 a megjelenítő
;  leállító-bájtja — nélküle a NMI átfutna a 0x76-mentes scratch-en)
; KORLÁT (D-3.6): 0x76 közvetlen bájtként nem szerepelhet a kódban
; (REM-hordozás) — ezért állítjuk elő aritmetikailag: 0x3B + RLCA = 0x76
SCRFILL:
        LD HL,DFILE
        LD A,0x3B
        RLCA                   ; A = 0x76 (0x3B balra forgatva)
        LD D,A                 ; D = sorzáró bájt
        LD B,25
SCRL:   LD C,32
SCRC:   LD (HL),0
        INC HL
        DEC C
        JR NZ,SCRC
        LD (HL),D
        INC HL
        DJNZ SCRL
        LD (HL),D              ; záró stop-bájt
        INC HL
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
PZL:    LD (HL),0            ; azonnali 0 — a számláló-teszt nem bántja
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

; ---- rezidens mód: a .P adatterületének másolása a végleges címekre ----
; a MOTOR, SZÓTÁR, ALAPMAG és CSOMAG a .P-ben a program UTÁN, az össze-
; zsugorított képernyő ELŐTT, egyben helyezkedik el — bármilyen bájtot
; tartalmazhatnak (a sorkiértékelés nem érinti őket; a REM-hordozás
; 0x76-os korlátja itt nem áll fenn — ezért költöztek ki a REM-sorokból,
; l. D-3.6).
; sorrend-KÉNYSZER: ALAPMAG → PACK → SZÓTÁR → MOTOR (a MOTOR célja,
; 0x4600, a hordozott adatok közepébe esik — csak utoljára jöhet).
; a @PG*@ immediate-eket a pgen.py patcheli; BLKCPY: HL = forrás,
; DE = cél, BC = hossz
RESCOPY:
SRC_ALAP: LD HL,0x0000         ; @PGALAP@ — ALAPMAG REM-test címe
        LD DE,0x6300
        LD BC,0x0800           ; 2048 B
        CALL BLKCPY
SRC_PACK: LD HL,0x0000         ; @PGPACK@ — CSOMAG REM-test címe
        LD DE,0x6B00
        LD BC,0x0040           ; 64 B
        CALL BLKCPY
SRC_SZO: LD HL,0x0000          ; @PGSZO@ — SZÓTÁR REM-test címe
        LD DE,0x5400
        LD BC,0x0900           ; 2304 B
        CALL BLKCPY
SRC_MOT: LD HL,0x0000          ; @PGMOT@ — MOTOR REM-test címe
        LD DE,0x4600
SRC_MOTN: LD BC,0x0000         ; @PGMOTN@ — motor0.bin hossza
        CALL BLKCPY
        RET

BLKCPY: LD A,(HL)
        XOR XORKEY             ; D-3.9: hordozó-visszakódolás másolás közben
        LD (DE),A
        INC HL
        INC DE
        DEC BC
        LD A,B
        OR C
        JR NZ,BLKCPY
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
BOOTMODE: DB 0                ; 0 = szalag mód, 1 = rezidens (.P) mód
