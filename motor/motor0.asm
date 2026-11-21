; ============================================================
; PIOCO AI — motor/motor0.asm — 2. szakasz (MOTOR kezdete, 0x4600)
; A stage-1 betöltő tölti ide (típus 2), majd átugrik ide.
; Feladata ebben a szeletben: hátralévő blokkok (SZÓTÁR, ALAPMAG,
; CSOMAG) betöltése a stage-1 LOADBLK-jének hívásával, splash,
; és egy várakozó főciklus-váz (2. szelet: INPUT + Agent-kör).
;
; NYÍLT TÉTELEK: ASCTBL tartalma (ROM-karaktertábla), INPUT-rutin
; választás (ROM INPUT vs KSCAN) — emulátor-ellenőrzés után.
; ============================================================

STG1LOAD EQU 0x0000        ; @EPITES@ — a stage-1 LOADBLK tényleges címe (epites.py tölti)
DFILE   EQU 0x4200

        ORG 0x4600
MOT0:
        CALL STG1LOAD           ; PIOCOSZO  → 0x5400
        CALL STG1LOAD           ; PIOCOALAP → 0x6300
        CALL STG1LOAD           ; PIOCOPACK → 0x6B00
        LD HL,SPLASH
        LD BC,DFILE + 2*33 + 5
        CALL PRINTAT
        LD HL,SPLASH2
        LD BC,DFILE + 7*33 + 9
        CALL PRINTAT
MWAIT:  JR MWAIT                ; főciklus-váz (2. szelet: INPUT + Agent-kör)

; ---- nyomtatás: HL = 0-végű szöveg, BC = cél a 32 karos soron belül ----
PRINTAT:
        LD A,(HL)
        OR A
        RET Z
        PUSH HL
        PUSH BC
        CALL FUNNEL
        POP BC
        LD (BC),A
        INC BC
        POP HL
        INC HL
        JR PRINTAT

; ---- print-tölcsér (fázis-2 5.3): 0x76 sosem kerül a képernyőre ----
FUNNEL:
        CP 0x20
        JR C,FUNOK
        CP 0x5B
        JR NC,FUNBAD
        PUSH HL
        PUSH DE
        PUSH BC
        LD HL,ASCTBL - 0x20
        LD D,0
        LD E,A
        ADD HL,DE
        LD A,(HL)
        POP BC
        POP DE
        POP HL
        RET
FUNBAD: LD A,0
FUNOK:  RET

ASCTBL: DB 0,0,0,0,0,0,0,0,0,0        ; ASCII 0x20..0x5A → ZX81 kód
        DB 0,0,0,0,0,0,0,0,0,0        ; TARTALOM NYÍLT TÉTEL (ROM-táblából);
        DB 0,0,0,0,0,0,0,0,0,0        ; minden 0 = szóköz — így is 0x76-biztos
        DB 0,0,0,0,0,0,0,0,0,0
        DB 0,0,0,0,0,0,0,0,0,0
        DB 0,0,0,0,0,0,0,0,0,0
SPLASH: DB "PIOCO AI",0
SPLASH2: DB "16K  PIOCO  0.1",0
