v0.6.4 - A FEKETE KEPERNYO ES AZ EGYSZERI TORLES JAVITVA
  - A LANC-TOLTES (interju -> ENTER -> az alap modell betoltese)
    mostmar MUKODIK a valodi emulatoron: negy rejtett hibat talaltunk
    es javitottunk (a szalagnev kodolasa, a blokkvegi csonkolas, az
    E_LINE inkonzisztencia es az automatikus inditas hianya). A
    teljes lancot szimulacional vegigteszteltuk: betoltes, interju,
    ENTER-kapu, a "RTBASE16" nev illesztve, a "TINYLLM V0.6.4" banner
    es a chat "you>" proparancs.
  - A TORLES (SHIFT+0) a kerdeseknal: EGY BAJTOS hiba volt a v0.6.2
    stubjaban (rossz veremcim-szamitas) - a sorhossz sosem rovidult,
    csak a kepernyo hamisitott. Javitva es bizonyitva: harom torles
    eseten 5 karakterbol 2 maradt.
  - A model blobok charset-igazitasa (a regi motor binary elvarasa).
  - HASZNALAT: toltsd be a GLM_v064_RT16_TOPICS.t81 kazettat az
    emulatoredba (tape/kazetta kent!), majd LOAD "" es RUN. A
    kovetkezo blokkok (RTBASE16, a temak) nevre keresese a szalagon
    megy - a .p fajlok kozvetlen gyorsbetoltesre valnak.
  - Tudott hatar: a /topic valtas meg nem tolti az uj temat (a futasi
    ideju nev-atiras hibaja - kovetkezo kor), es a CHAT-ben (a motor
    sajat bekero soraiban) meg nincs torsel. A SHIFT+0 torles a BOOT
    kerdesekben mukodik.
