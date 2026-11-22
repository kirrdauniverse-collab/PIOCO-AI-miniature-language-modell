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
BOOTMODE EQU 0x0000        ; @EPITES@ — a stage-1 BOOTMODE címe (epites.py tölti)
DFILE   EQU 0x4200

        ORG 0x4600
MOT0:
        LD A,(BOOTMODE)
        OR A
        JR NZ,MSKIP             ; rezidens módban már a helyükön vannak
        CALL STG1LOAD           ; PIOCOSZO  → 0x5400
        CALL STG1LOAD           ; PIOCOALAP → 0x6300
        CALL STG1LOAD           ; PIOCOPACK → 0x6B00
MSKIP:  LD HL,SPLASH
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

; ASCII 0x20..0x5A → ZX81 kód (59 bejegyzés) — FORRÁS-HITELESÍTVE:
; Wikipedia „ZX81 character set”: szóköz=0x00, számok 0x1C-0x25, A-Z=0x26-0x3F,
; „=0x0B $=0x0D :=0x0E ?=0x0F (=0x10 )=0x11 >=0x12 <=0x13 ==0x14 +=0x15
; -=0x16 *=0x17 /=0x18 ;=0x19 ,=0x1A .=0x1B; aposztróf és ! nincs a készletben → szóköz
ASCTBL: DB 0x00,0x00,0x0B,0x00,0x0D,0x00,0x00,0x00   ; 20-27  (sp ! " # $ % & ')
        DB 0x10,0x11,0x17,0x15,0x1A,0x16,0x1B,0x18   ; 28-2F  ( * + , - . / )
        DB 0x1C,0x1D,0x1E,0x1F,0x20,0x21,0x22,0x23   ; 30-37  (0-7)
        DB 0x24,0x25,0x0E,0x19,0x13,0x14,0x12,0x0F   ; 38-3F  (8 9 : ; < = > ?)
        DB 0x00,0x26,0x27,0x28,0x29,0x2A,0x2B,0x2C   ; 40-47  (@ A B C D E F G)
        DB 0x2D,0x2E,0x2F,0x30,0x31,0x32,0x33,0x34   ; 48-4F  (H I J K L M N O)
        DB 0x35,0x36,0x37,0x38,0x39,0x3A,0x3B,0x3C   ; 50-57  (P Q R S T U V W)
        DB 0x3D,0x3E,0x3F                            ; 58-5A  (X Y Z)
SPLASH: DB "PIOCO AI",0
SPLASH2: DB "16K  PIOCO  0.5",0
