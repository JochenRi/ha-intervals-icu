"""Ein Wert je Block: Ablesung, Regelkreis, Belegung. Lauf: python3 tests/test_blocks.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu"))

import blocks  # noqa: E402
import derive  # noqa: E402
from const import (  # noqa: E402
    BLOCK_CORRIDORS, BLOCK_MIN_FOR_TREND, BLOCK_MIN_POINTS,
    BLOCK_STEP_FAR_PCT, BLOCK_STEP_NEAR_PCT, BLOCK_WARMUP_DISCARD_S,
)

failures = []
CHECKS = 0


def check(label, got, expected):
    global CHECKS
    CHECKS += 1
    ok_ = got == expected
    print(f"{'PASS' if ok_ else 'FAIL'}  {label}: {got!r}" + ("" if ok_ else f"  (erwartet {expected!r})"))
    if not ok_:
        failures.append(label)


def ok(label, condition):
    check(label, bool(condition), True)


# --- der echte Median ---------------------------------------------------------
print("=== der Median, der bei gerader Anzahl nicht den oberen Wert nimmt ===")
check("ungerade: der mittlere Wert", derive._median([0.4, 0.5, 0.9]), 0.5)
check("gerade: das Mittel der beiden mittleren", derive._median([0.65, 0.86]), 0.755)
# GEGENPROBE, GEZAEHLT UND BENANNT: die fehlerhafte Bildung haette hier den
# OBEREN Wert geliefert. Der Fehler taeuscht sich nach der Datenlage - bei
# ungerader Anzahl faellt er nie auf, bei gerader immer.
check("Gegenprobe: die fehlerhafte Bildung haette 0,86 geliefert",
      sorted([0.65, 0.86])[2 // 2], 0.86)
ok("und sie unterscheidet sich vom echten Median",
   sorted([0.65, 0.86])[1] != derive._median([0.65, 0.86]))
check("leer bleibt leer", derive._median([]), None)


# --- die Ablesung je Block ----------------------------------------------------
print("\n=== der Anlauf wird verworfen, nicht mitgemittelt ===")


def strom(anlauf, danach, sekunden=600, anlauf_s=120):
    dfa, w, hr = [], [], []
    for t in range(sekunden):
        dfa.append(anlauf if t < anlauf_s else danach)
        w.append(250)
        hr.append(175)
    return dfa, w, hr


LAP = [{"label": "WORK", "start_index": 0, "end_index": 600, "moving_time": 600}]
dfa, w, hr = strom(1.60, 0.45)
b = derive.dfa_blocks(dfa, w, hr, LAP, 1)[0]
check("der Blockwert ist der eingeschwungene", b["alpha"], 0.45)
check("und nicht der gemischte", b["alpha"] != round(sum(dfa) / len(dfa), 3), True)
check("die verworfene Zeit steht dabei", b["discarded_s"], BLOCK_WARMUP_DISCARD_S)
check("die Belegung NACH dem Verwerfen", b["points"], 600 - BLOCK_WARMUP_DISCARD_S)
ok("die Streuung ist die des eingeschwungenen Teils", b["alpha_sd"] == 0.0)

# DIE GEGENPROBE, am REALISTISCHEN Fall: bei einem 4-Minuten-Block ist der
# Anlauf genau die Haelfte, und dort kippt auch der Median. Beim langen Block
# ist er robust - deshalb faellt der Fehler ausgerechnet bei VO2max auf und
# bei SweetSpot nicht.
kurz_dfa, kurz_w, kurz_hr = strom(1.60, 0.45, sekunden=240)
VIER = [{"label": "WORK", "start_index": 0, "end_index": 240, "moving_time": 240}]
mit = derive.dfa_blocks(kurz_dfa, kurz_w, kurz_hr, VIER, 1)[0]["alpha"]
ohne = derive._median(kurz_dfa)
check("4-min-Block, verworfen: der eingeschwungene Wert", mit, 0.45)
ok("Gegenprobe: ohne Verwerfen kippt derselbe Block", abs(ohne - mit) > 0.5)
# und beim LANGEN Block ist der Median robust - der Unterschied ist die
# Blocklaenge, nicht die Regel
ok("beim langen Block faellt es nicht auf - genau deshalb ist es gefaehrlich",
   abs(derive._median(dfa) - b["alpha"]) < 0.01)

# Nur Arbeitsabschnitte, und nur lange genug.
kurz = [{"label": "WORK", "start_index": 0, "end_index": 140, "moving_time": 140}]
check("ein zu kurzer Block traegt nichts", derive.dfa_blocks(dfa, w, hr, kurz, 1), [])
knapp = [{"label": "WORK", "start_index": 0, "end_index": 300, "moving_time": 300}]
check("ein Block mit zu wenigen Punkten nach dem Verwerfen faellt raus",
      len(derive.dfa_blocks(dfa[:300], w[:300], hr[:300],
                            [{"label": "WORK", "start_index": 0, "end_index": 135,
                              "moving_time": 155}], 1)), 0)
ok("ein ausreichend langer Block bleibt", len(derive.dfa_blocks(dfa, w, hr, knapp, 1)) == 1)
check("ohne Laps gibt es keine Bloecke", derive.dfa_blocks(dfa, w, hr, [], 1), [])


# --- DIE PHYSIK-GEGENPROBE, die den Fehler aus 0.48.0 gefunden hat ----------
print("\n=== ein Arbeitsabschnitt traegt mehr Leistung als die Pause daneben ===")

# Die Einheit vom 01.09.2026, mit den ECHTEN Lap-Grenzen: die Indizes zaehlen
# im Strom, die Sekunden auf der Uhr - bei dieser Fahrt liegen 114 Stellen
# dazwischen (2859 Indizes gegen 2973 Sekunden, genau die Standzeit).
ECHT = [
    {"label": "RECOVERY", "start_index": 0, "end_index": 875, "start_s": 0, "end_s": 989,
     "moving_time": 874, "dfa_a1": 1.44},
    {"label": "WORK", "start_index": 875, "end_index": 1112, "start_s": 989, "end_s": 1226,
     "moving_time": 237, "dfa_a1": 0.853},
    {"label": "RECOVERY", "start_index": 1112, "end_index": 1297, "start_s": 1226, "end_s": 1411,
     "moving_time": 185, "dfa_a1": 0.970},
    {"label": "WORK", "start_index": 1297, "end_index": 1532, "start_s": 1411, "end_s": 1646,
     "moving_time": 235, "dfa_a1": 0.774},
]
# Ein Strom, der die Abschnitte NACH INDEX traegt: Arbeit 250 W, Pause 90 W.
strom_dfa, strom_w = [], []
for i in range(1600):
    arbeit = (875 <= i < 1112) or (1297 <= i < 1532)
    strom_dfa.append(0.45 if arbeit else 1.30)
    strom_w.append(250 if arbeit else 90)
got = derive.dfa_blocks(strom_dfa, strom_w, [170] * 1600, ECHT, 1)
arbeit = [b for b in got if b["label"] == "WORK"]
pause = [b for b in got if b["label"] == "RECOVERY"]
ok("Arbeitsabschnitte gefunden", len(arbeit) == 2)
for b in arbeit:
    check(f"WORK bei Index {b['start_index']} traegt Arbeitsleistung", b["watts"], 250)
for b in pause:
    ok(f"RECOVERY bei Index {b['start_index']} traegt Pausenleistung", b["watts"] == 90)
# DIE REGEL, allgemein: kein Arbeitsabschnitt darf weniger tragen als die
# Pause daneben. Genau das stand in 0.48.0 im Archiv - 88 W Arbeit gegen
# 253 W Pause - und war in den Daten sofort sichtbar.
for i in range(len(got) - 1):
    if got[i]["label"] == "WORK" and got[i + 1]["label"] == "RECOVERY":
        ok(f"Arbeit vor Pause: {got[i]['watts']} > {got[i + 1]['watts']}",
           got[i]["watts"] > got[i + 1]["watts"])

# GEGENPROBE, GEZAEHLT UND BENANNT: mit den SEKUNDEN statt den Indizes kippt
# es - das ist der Fehler aus 0.48.0, nachgebaut.
falsch = [{**lap, "start_index": lap["start_s"], "end_index": lap["end_s"]} for lap in ECHT]
kaputt = derive.dfa_blocks(strom_dfa, strom_w, [170] * 1600, falsch, 1)
kaputt_work = [b for b in kaputt if b["label"] == "WORK"]
ok("Gegenprobe: ueber die Sekunden zugeordnet traegt die Arbeit die Pausenleistung",
   any(b["watts"] == 90 for b in kaputt_work))

# Die FREMDE Gegenprobe: Intervals' eigener Abschnittswert liegt hoeher (Mittel
# ueber den ganzen Block), muss aber DIESELBE Richtung zeigen.
d = {"activities": {"x": {"name": "VO2max-Intervalle", "start_date_local": "2026-09-01T10:00"}},
     "dfa": {"x": {"blocks": [
         {"label": "WORK", "alpha": 0.49, "watts": 260, "lap_alpha": 0.853},
         {"label": "WORK", "alpha": 0.40, "watts": 250, "lap_alpha": 0.774},
         {"label": "WORK", "alpha": 0.37, "watts": 250, "lap_alpha": 0.640}]}}}
f = blocks.series(d)["families"]["vo2max"]
check("fremde Quelle: die Reihenfolge stimmt", f["points"][0]["order_ok"], True)
check("und es gibt nichts zu melden", f["order_conflicts"], [])
# Gegenprobe: laeuft sie auseinander, wird es GEZAEHLT UND BENANNT.
d2 = {"activities": {"x": {"name": "VO2max-Intervalle", "start_date_local": "2026-09-01T10:00"}},
      "dfa": {"x": {"blocks": [
          {"label": "WORK", "alpha": 0.49, "watts": 260, "lap_alpha": 0.60},
          {"label": "WORK", "alpha": 0.40, "watts": 250, "lap_alpha": 0.90}]}}}
f2 = blocks.series(d2)["families"]["vo2max"]
check("Gegenprobe: gegenlaeufige Reihenfolge wird erkannt", f2["points"][0]["order_ok"], False)
check("und in der Payload gemeldet", f2["order_conflicts"], ["2026-09-01"])

# --- 0.49.1: als Arbeit etikettierte Einroll-Abschnitte ----------------------
print("\n=== ein lockerer Abschnitt mit WORK-Etikett faellt raus ===")
TEMPO = [{"label": "WORK", "alpha": 1.529, "watts": 164},
         {"label": "WORK", "alpha": 0.974, "watts": 183},
         {"label": "WORK", "alpha": 0.852, "watts": 176},
         {"label": "WORK", "alpha": 0.872, "watts": 165}]
t = derive.drop_warmup_blocks(TEMPO)
check("Tempo 13.09.: der lockere Abschnitt verliert sein Arbeits-Etikett",
      t[0]["label"], "WARMUP_LABELLED_WORK")
check("und die Leitzahl ist danach ein echter Block",
      [b["watts"] for b in t if b["label"] == "WORK"][0], 183)
# DIE WATT-GEGENPROBE, GEZAEHLT UND BENANNT: der verworfene Abschnitt traegt
# 164 W, der ECHTE vierte Block 165 W. Eine Wattschwelle kann das nicht
# trennen - deshalb entscheidet alpha.
ok("Gegenprobe: der echte Block mit 165 W bleibt, obwohl er nur 1 W staerker ist",
   t[3]["label"] == "WORK")
ok("Gegenprobe: 164 gegen 165 W waere ueber die Leistung nicht trennbar",
   abs(TEMPO[0]["watts"] - TEMPO[3]["watts"]) <= 1)
# Denselben Fall gibt es auch bei VO2max - es war nie ein Tempo-Problem.
VO_WARM = [{"label": "WORK", "alpha": 1.336, "watts": 206},
           {"label": "WORK", "alpha": 0.828, "watts": 250},
           {"label": "WORK", "alpha": 0.522, "watts": 251},
           {"label": "WORK", "alpha": 0.360, "watts": 251}]
check("VO2max 02.08.: derselbe Fall, dieselbe Regel",
      derive.drop_warmup_blocks(VO_WARM)[0]["label"], "WARMUP_LABELLED_WORK")

print("\n=== DIE 11.08.-ZUSICHERUNG: ein echter Block ueber dem staerksten ===")
# Am 11.08.2026 traegt der VIERTE Block alpha 0,431 und liegt damit UEBER dem
# staerksten Block (0,426) - er ist trotzdem echt. Das ist der schaerfste Test
# des Umbaus: eine Regel ohne Abstandsmass wirft ihn raus.
ELF = [{"label": "WORK", "alpha": 0.426, "watts": 260},
       {"label": "WORK", "alpha": 0.399, "watts": 251},
       {"label": "WORK", "alpha": 0.338, "watts": 236},
       {"label": "WORK", "alpha": 0.431, "watts": 230}]
elf = derive.drop_warmup_blocks(ELF)
check("11.08.: alle vier Bloecke bleiben Arbeit",
      [b["label"] for b in elf], ["WORK"] * 4)
check("und die Leitzahl bleibt unveraendert", elf[0]["watts"], 260)
# GEGENPROBE, GEZAEHLT UND BENANNT: OHNE Abstandsmass - also mit der blossen
# Bedingung "alpha hoeher als der staerkste Block, Leistung niedriger" - fiele
# genau dieser Block raus. Die drei Streuungen sind nicht schmueckend.
ohne_abstand = [b for b in ELF if not (b["alpha"] > ELF[0]["alpha"] and b["watts"] < 260)]
ok("Gegenprobe: ohne Abstandsmass verloere die Einheit einen echten Block",
   len(ohne_abstand) < len(ELF))
check("und zwar genau den vierten", len(ELF) - len(ohne_abstand), 1)

# SweetSpot ist strukturell unberuehrt: zwei Bloecke ergeben keine Streuung
# der "uebrigen", die Regel greift dort nie.
SS = [{"label": "WORK", "alpha": 0.869, "watts": 198},
      {"label": "WORK", "alpha": 0.658, "watts": 194}]
check("SweetSpot mit zwei Bloecken bleibt unberuehrt",
      [b["label"] for b in derive.drop_warmup_blocks(SS)], ["WORK", "WORK"])
# Und die Physik-Pruefung aus 0.48.1 greift weiter: Pausen bleiben Pausen.
MIT_PAUSE = TEMPO + [{"label": "RECOVERY", "alpha": 1.2, "watts": 106}]
check("Pausen behalten ihr Etikett",
      [b["label"] for b in derive.drop_warmup_blocks(MIT_PAUSE)][-1], "RECOVERY")

# --- 0.49.2: die Toleranz der fremden Gegenprobe ----------------------------
print("\n=== ein Schritt unter der Versatzschwankung sagt nichts aus ===")


def zwei(a1, a2, f1, f2):
    return blocks.series({"activities": {"x": {"name": "VO2max",
                                               "start_date_local": "2026-09-01T10:00"}},
                          "dfa": {"x": {"blocks": [
                              {"label": "WORK", "alpha": a1, "watts": 250, "lap_alpha": f1},
                              {"label": "WORK", "alpha": a2, "watts": 250, "lap_alpha": f2},
                          ]}}})["families"]["vo2max"]


# Die ECHTEN Paare vom 01.09. und 13.09.: unser Schritt 0,024 bzw. 0,020, der
# fremde laeuft dagegen. Unter der Toleranz - keine Meldung mehr.
check("01.09.: Schritt 0,024 liegt unter der Toleranz",
      zwei(0.381, 0.405, 0.640, 0.592)["order_conflicts"], [])
check("13.09.: Schritt 0,020 ebenso", zwei(0.852, 0.872, 0.964, 0.900)["order_conflicts"], [])
# GEGENPROBE, GEZAEHLT UND BENANNT: der 03.06. hatte einen ECHTEN Schritt von
# 0,206 gegen eine fremde Reihe, die nicht folgte. Der MUSS weiter melden -
# sonst ist die Toleranz zu weit.
check("03.06.: ein echter Schritt von 0,206 meldet weiterhin",
      zwei(0.500, 0.706, 0.800, 0.788)["order_conflicts"], ["2026-09-01"])
# Und der Grenzfall vom 25.07. (-0,079) bleibt stehen: lieber eine Meldung zu
# viel als eine zu wenig, solange die Karte sagt, dass es ein Hinweis ist.
check("25.07.: der Grenzfall mit 0,079 bleibt eine Meldung",
      zwei(0.800, 0.721, 0.900, 0.901)["order_conflicts"], ["2026-09-01"])

# NACHGEBAUT, KEINE MESSUNG: der Stand VOR 0.49.1, als ein als Arbeit
# etikettierter Einrollblock die Reihe anfuehrte. Diese Konstellation gibt es
# im lebenden Bestand nicht mehr - die Neuberechnung hat sie geloescht
# (PROJEKTSTAND §7). Die Fixture belegt, dass die Regel bei ihr anschlaegt,
# und NICHT, dass sie heute noch vorkommt.
VOR_0491 = {"activities": {"y": {"name": "VO2max", "start_date_local": "2026-07-10T10:00"}},
            "dfa": {"y": {"blocks": [
                {"label": "WORK", "alpha": 1.136, "watts": 257, "lap_alpha": 1.267},
                {"label": "WORK", "alpha": 0.742, "watts": 268, "lap_alpha": 1.190},
                {"label": "WORK", "alpha": 0.468, "watts": 262, "lap_alpha": 0.935},
                {"label": "WORK", "alpha": 0.580, "watts": 258, "lap_alpha": 0.763}]}}}
alt = blocks.series(VOR_0491)["families"]["vo2max"]
check("Fixture vom Stand vor 0.49.1: die Regel schlaegt an",
      alt["order_conflicts"], ["2026-07-10"])
ok("und der Einrollblock waere heute aussortiert",
   derive.drop_warmup_blocks(VOR_0491["dfa"]["y"]["blocks"])[0]["label"]
   == "WARMUP_LABELLED_WORK")

# --- der Regelkreis -----------------------------------------------------------
print("\n=== der Regelkreis: Vorschlag nach oben wie nach unten ===")
KORR = BLOCK_CORRIDORS["vo2max"]
check("im Korridor: kein Schritt", blocks.suggest_step(0.41, KORR, 0.08)["pct"], 0)
check("knapp darueber: der kleine Schritt",
      blocks.suggest_step(0.55, KORR, 0.08)["pct"], BLOCK_STEP_NEAR_PCT)
check("weit darueber: der grosse Schritt",
      blocks.suggest_step(0.65, KORR, 0.08)["pct"], BLOCK_STEP_FAR_PCT)
check("knapp darunter: nach unten",
      blocks.suggest_step(0.16, KORR, 0.08)["pct"], -BLOCK_STEP_NEAR_PCT)
check("weit darunter: gross nach unten",
      blocks.suggest_step(0.05, KORR, 0.08)["pct"], -BLOCK_STEP_FAR_PCT)
# DIE GRENZE FOLGT DER STREUUNG DER FAMILIE, sie ist nicht gesetzt: dieselbe
# Abweichung ist bei der einen Familie "weit" und bei der anderen "knapp".
check("dieselbe Abweichung, enge Streuung: weit",
      blocks.suggest_step(0.60, KORR, 0.05)["pct"], BLOCK_STEP_FAR_PCT)
check("dieselbe Abweichung, breite Streuung: knapp",
      blocks.suggest_step(0.60, KORR, 0.20)["pct"], BLOCK_STEP_NEAR_PCT)


# --- der Verlauf je Familie ---------------------------------------------------
print("\n=== Steuergroesse Median, Verlaufsgroesse erster Block ===")


def bestand(eintraege):
    data = {"activities": {}, "dfa": {}}
    for i, (name, tag, bl) in enumerate(eintraege):
        key = f"a{i}"
        data["activities"][key] = {"name": name, "start_date_local": f"{tag}T17:00:00"}
        data["dfa"][key] = {"blocks": [
            {"label": "WORK", "alpha": a, "watts": wv, "points": 60, "minutes": 4.0}
            for a, wv in bl]}
    return data


# Die echten SweetSpot-Einheiten: zwei Bloecke, der erste systematisch hoeher.
ss = bestand([
    ("SweetSpot 2x20Min", "2026-08-05", [(0.80, 192), (0.685, 192)]),
    ("SweetSpot 2x20Min", "2026-08-14", [(0.73, 192), (0.68, 192)]),
    ("volumen + SweetSpot 2x15Min", "2026-08-20", [(0.91, 194), (0.70, 194)]),
    ("SweetSpot 2x20Min", "2026-08-24", [(0.86, 196), (0.65, 196)]),
])
s = blocks.series(ss)["families"]["sweetspot"]
check("vier Einheiten erkannt", s["sessions"], 4)
check("die Steuergroesse ist der Median der Bloecke",
      [p["median_alpha"] for p in s["points"]], [0.743, 0.705, 0.805, 0.755])
check("die Verlaufsgroesse ist der erste Block",
      [p["first_alpha"] for p in s["points"]], [0.8, 0.73, 0.91, 0.86])
ok("beide sind verschieden - sonst waere die Trennung folgenlos",
   any(p["median_alpha"] != p["first_alpha"] for p in s["points"]))
check("die Schritte auf der Steuergroesse",
      [p["step_pct"] for p in s["points"]], [0, 0, 10, 5])
# DIE GEGENPROBE ZUR TRENNUNG: auf dem ERSTEN Block gerechnet wuerde dieselbe
# Reihe nach oben driften - genau der Fehler, den die Trennung verhindert.
erste = [blocks.suggest_step(p["first_alpha"], BLOCK_CORRIDORS["sweetspot"],
                             s["spread"])["pct"] for p in s["points"]]
ok("Gegenprobe: auf dem ersten Block schlaegt die Regel oefter zu",
   sum(1 for x in erste if x) > sum(1 for p in s["points"] if p["step_pct"]))
check("und der letzte Vorschlag laege hoeher",
      round(s["points"][-1]["median_watts"] * (1 + erste[-1] / 100.0))
      > s["points"][-1]["suggested_watts"], True)

# Die Einzelwerte reisen mit, damit die Karte zeigen kann, worauf sie ruht.
check("die Blockwerte der letzten Einheit", s["latest"]["block_alphas"], [0.86, 0.65])
check("und ihre Spanne", s["latest"]["alpha_span"], 0.21)


# --- Belegung: nichts wird geglaettet ----------------------------------------
print("\n=== die Belegung entscheidet, ob eine Linie gezeichnet wird ===")
wenig = bestand([("VO2max-Intervalle 3x4min", f"2026-08-{d:02d}", [(0.41, 250)])
                 for d in range(1, BLOCK_MIN_FOR_TREND)])
check(f"unter {BLOCK_MIN_FOR_TREND} Einheiten: keine Linie",
      blocks.series(wenig)["families"]["vo2max"]["trend"], False)
genug = bestand([("VO2max-Intervalle 3x4min", f"2026-08-{d:02d}", [(0.41, 250)])
                 for d in range(1, BLOCK_MIN_FOR_TREND + 1)])
check(f"ab {BLOCK_MIN_FOR_TREND} Einheiten: Linie",
      blocks.series(genug)["families"]["vo2max"]["trend"], True)

# Der Geltungsbereich steht in der Payload - dieselbe Familie draussen ist eine
# andere Messung (40-W-Befund).
check("der Geltungsbereich reist mit", blocks.series(genug)["scope"], "rolle")
check("eine Einheit ohne Familie zaehlt nicht",
      blocks.series(bestand([("volumen", "2026-08-01", [(0.9, 150)])]))["families"], {})
check("eine Einheit ohne Bloecke zaehlt nicht",
      blocks.series({"activities": {"x": {"name": "SweetSpot", "start_date_local": "2026-08-01"}},
                     "dfa": {"x": {}}})["families"], {})

print(f"\ntest_blocks: {CHECKS} Prüfungen, {len(failures)} Fehler")
print("FEHLER:", failures if failures else "keine")
sys.exit(1 if failures else 0)
