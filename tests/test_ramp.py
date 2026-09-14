"""Stufentest: Segment, Gerade, drei Zahlen, Erholung. Lauf: python3 tests/test_ramp.py"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu"))

import ramp  # noqa: E402
from const import (  # noqa: E402
    RAMP_FLAT_S, RAMP_MIN_POINTS, RAMP_READ_WINDOW_S, RAMP_RECOVERY_WINDOW_S, RAMP_SMOOTH_S,
)
from derive import DFA_AEROBIC, DFA_ANAEROBIC  # noqa: E402

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


def at(node, key):
    """Feldzugriff ueber .get(), nie ueber []. Ein fehlendes Feld ist genau
    das, was eine Mutation herstellt - mit [] stuerzt der Test dann ab und
    ueberspringt alles Folgende, und am Ende steht "0 Fehler" (§9)."""
    return (node or {}).get(key)


def near(label, got, expected, tol):
    global CHECKS
    CHECKS += 1
    ok_ = got is not None and abs(got - expected) <= tol
    print(f"{'PASS' if ok_ else 'FAIL'}  {label}: {got!r}" + ("" if ok_ else f"  (erwartet {expected!r} ± {tol})"))
    if not ok_:
        failures.append(label)


# --- ein Stufentest, wie er aussieht -----------------------------------------
# Aufbau: Einrollen flach oben, dann ein linearer Abfall, dann flach unten,
# dann das Ausrollen, in dem die Kurve zurueckkommt. Sekundenweise, wie der
# ungeduennte Strom.
WARMUP_S = 600
DROP_S = 1200
FLAT_S = 240
COOL_S = 600
PEAK = 1.40
BOTTOM = 0.30
START_W = 150.0
RAMP_W_PER_S = 0.1          # entspricht 6 W/min - reine Fixture-Groesse


def ride(peak=PEAK, bottom=BOTTOM, warmup_s=WARMUP_S, drop_s=DROP_S,
         flat_s=FLAT_S, cool_s=COOL_S, cool_to=0.95):
    dfa, watts, hr = [], [], []
    for t in range(warmup_s):
        dfa.append(peak)
        watts.append(START_W)
        hr.append(110.0)
    for t in range(drop_s):
        dfa.append(peak + (bottom - peak) * (t / max(1, drop_s - 1)))
        watts.append(START_W + RAMP_W_PER_S * t)
        hr.append(110.0 + 0.05 * t)
    for t in range(flat_s):
        dfa.append(bottom)
        watts.append(START_W + RAMP_W_PER_S * drop_s)
        hr.append(170.0)
    for t in range(cool_s):
        dfa.append(bottom + (cool_to - bottom) * (t / max(1, cool_s - 1)))
        watts.append(START_W)
        hr.append(170.0 - 0.08 * t)
    return dfa, watts, hr


DFA, WATTS, HR = ride()

# Erwartungswerte aus der Fixture selbst gerechnet, nicht abgeschrieben: der
# Abfall ist eine Gerade von PEAK auf BOTTOM ueber DROP_S Sekunden, also liegt
# alpha=a bei WARMUP_S + (PEAK-a)/(PEAK-BOTTOM) * (DROP_S-1) Sekunden.
def t_at(alpha):
    return WARMUP_S + (PEAK - alpha) / (PEAK - BOTTOM) * (DROP_S - 1)


def w_at(alpha):
    return START_W + RAMP_W_PER_S * (t_at(alpha) - WARMUP_S)


# ── 1 Segment: eine Bestimmung, zwei Ergebnisse ──────────────────────────────
seg = ramp.segment(DFA)
ok("Segment: gar keins gefunden", seg is not None)
near("Segment: Anfang liegt am Ende des Einrollens", seg["start_index"], WARMUP_S - 1, 20)
near("Segment: Ende liegt am Fuss des Abfalls", seg["end_index"],
     t_at(DFA_ANAEROBIC), RAMP_SMOOTH_S)
check("Segment: der Hochpunkt ist zugleich max_alpha_start", seg["max_alpha_start"], PEAK)
ok("Segment: der Boden gilt als erreicht", seg["reached_anaerobic"])

# Der Anfang ist der LETZTE Hochpunkt, nicht der erste. Bei einem Plateau von
# 600 Sekunden ist das ein Unterschied von zehn Minuten - und mit dem ersten
# stuende die Gerade ueber eine flache Strecke, die gar nicht faellt.
ok("Segment Fixture-Beweis: das Plateau ist laenger als die Glaettung - "
   "sonst waere erster und letzter Hochpunkt dasselbe", WARMUP_S > 2 * RAMP_SMOOTH_S)
ok("Segment: der Anfang ist der ERSTE Hochpunkt statt des letzten",
   seg["start_index"] > WARMUP_S // 2)

# ── 2 Die Gerade, und dass sie GEFITTET und nicht abgelesen wird ─────────────
res = ramp.evaluate(DFA, WATTS, HR)
ok("Auswertung: nichts herausgekommen", res is not None)
near("HRVT1: Zeitpunkt", at(res["hrvt1"], "seconds"), t_at(DFA_AEROBIC), 15)
near("HRVT1: Leistung", at(res["hrvt1"], "watts"), w_at(DFA_AEROBIC), 3)
near("HRVT2: Zeitpunkt", at(res["hrvt2"], "seconds"), t_at(DFA_ANAEROBIC), 15)
near("HRVT2: Leistung", at(res["hrvt2"], "watts"), w_at(DFA_ANAEROBIC), 3)
ok("HRVT2 liegt ueber HRVT1 - sonst faellt die Kurve verkehrt herum",
   (at(res["hrvt2"], "watts") or 0) > (at(res["hrvt1"], "watts") or 0))
near("Gerade: Bestimmtheitsmass am sauberen Abfall", res["segment"]["r2"], 1.0, 0.01)
ok("Gerade: die Steigung ist nicht negativ", res["segment"]["slope_per_min"] < 0)

# GEGENPROBE, gezaehlt und benannt: ein Ausreisser unter 0,75 VOR dem Abfall
# darf die Schwelle nicht verschieben. Genau hier trennt sich "gefittet" von
# "abgelesen" - ein Ableser haette den Ausreisser genommen.
spike = list(DFA)
SPIKE_AT = 300
spike[SPIKE_AT] = 0.40
ok("Ausreisser Trefferzusicherung: der Wert wurde wirklich veraendert",
   spike[SPIKE_AT] != DFA[SPIKE_AT])
res_spike = ramp.evaluate(spike, WATTS, HR)
ok("Ausreisser: die Auswertung faellt ganz aus", res_spike is not None)
near("Ausreisser: HRVT1 verschiebt sich trotzdem",
     at(res_spike["hrvt1"], "seconds"), at(res["hrvt1"], "seconds"), 15)
ok("Ausreisser Gegenprobe: ein Ableser haette ihn genommen - der Ausreisser "
   "liegt weit vor der Schwelle", SPIKE_AT < t_at(DFA_AEROBIC) - 300)

# ── 3 Die dritte Zahl, aus zweiter Hand ─────────────────────────────────────
check("dritte Zahl: der personalisierte alpha-Wert", res["pers_alpha"],
      round((PEAK + DFA_ANAEROBIC) / 2, 3))
ok("dritte Zahl: sie ist nicht berechnet", res["hrvt1_pers"] is not None)
ok("dritte Zahl liegt UNTER HRVT1 - der Hochpunkt liegt ueber 1,0, also "
   "greift sie frueher", (at(res["hrvt1_pers"], "watts") or 0) < (at(res["hrvt1"], "watts") or 0))
# Fixture-Beweis: mit einem Hochpunkt von genau 1,0 waeren beide gleich - dann
# pruefte die Zeile darueber gar nichts.
ok("dritte Zahl Fixture-Beweis: der Hochpunkt liegt nicht bei 1,0",
   abs(PEAK - 1.0) > 0.05)
flat_peak = ramp.evaluate(*ride(peak=1.0))
check("dritte Zahl: bei Hochpunkt 1,0 faellt sie mit HRVT1 zusammen",
      at(flat_peak, "pers_alpha"), DFA_AEROBIC)

# ── 4 Nicht hochrechnen: wer bei 0,6 abbricht, hat keine HRVT2 ──────────────
abgebrochen = ramp.evaluate(*ride(bottom=0.62, cool_to=1.0))
ok("Abbruch: die Auswertung faellt ganz aus", abgebrochen is not None)
ok("Abbruch Fixture-Beweis: der Boden liegt ueber 0,5 - sonst waere der Fall "
   "nicht pruefbar", 0.62 > DFA_ANAEROBIC)
check("Abbruch: der Boden gilt trotzdem als erreicht",
      at(abgebrochen, "reached_anaerobic"), False)
check("Abbruch: HRVT2 wird trotzdem genannt", at(abgebrochen, "hrvt2"), None)
ok("Abbruch: HRVT1 faellt mit weg, obwohl sie im Abfall liegt",
   at(abgebrochen, "hrvt1") is not None)

# ── 5 Erholung: gemessen, ohne Studienlage ──────────────────────────────────
rec = res["recovery"]
ok("Erholung: nicht gemessen", rec is not None)
check("Erholung: das Fenster kommt nicht aus der Konstante",
      at(rec, "window_s"), RAMP_RECOVERY_WINDOW_S)
ok("Erholung: der Wert am Ende liegt nicht ueber dem Boden",
   (at(rec, "alpha_end") or 0) > BOTTOM)
ok("Erholung: die Rueckkehr ueber 0,5 wird nicht gemeldet",
   at(rec, "back_above_s") is not None)
# GEGENPROBE: eine Fahrt, die unten BLEIBT, hat keine Rueckkehr.
unten = ride(cool_to=0.35)
ok("Erholung Trefferzusicherung: das Ausrollen endet wirklich tiefer",
   unten[0][-1] < DFA[-1])
res_unten = ramp.evaluate(*unten)
check("Erholung Gegenprobe: die Rueckkehr wird auch ohne Rueckkehr gemeldet",
      at(res_unten["recovery"], "back_above_s"), None)

# ── 6 Was KEIN Stufentest ist, gibt auch keinen ─────────────────────────────
check("gewoehnliche Fahrt: eine Schwelle wird erfunden",
      ramp.evaluate([0.9] * 3600, [180.0] * 3600, [140.0] * 3600), None)
check("leerer Strom", ramp.evaluate(None), None)
check("nur Artefakte", ramp.evaluate([0.0] * 600 + [None] * 600), None)
def treppe(plateau_s, drop_s, bottom=0.30, flat_s=200):
    """Dieselbe Form in beliebiger Laenge - so ist die Punktzahl im Abfall die
    EINZIGE Groesse, die sich zwischen den beiden Faellen unterscheidet."""
    return ([1.2] * plateau_s
            + [1.2 + (bottom - 1.2) * (t / max(1, drop_s - 1)) for t in range(drop_s)]
            + [bottom] * flat_s)


kurz_seg = ramp.segment(treppe(120, 40))
ok("zu kurzer Abfall Fixture-Beweis: die kurze Form traegt wirklich weniger "
   "Punkte als die Mindestzahl",
   kurz_seg is None or at(kurz_seg, "points") < RAMP_MIN_POINTS)
check("zu kurzer Abfall: unter der Mindestzahl wird trotzdem gerechnet",
      ramp.evaluate(treppe(120, 40)), None)
lang_seg = ramp.segment(treppe(120, 400))
ok("zu kurzer Abfall Gegenprobe: dieselbe Form mit LANGEM Abfall wird "
   "ausgewertet - sonst prueft die Zeile darueber nur, dass nie etwas kommt",
   ramp.evaluate(treppe(120, 400)) is not None)
ok("zu kurzer Abfall Fixture-Beweis: der lange Fall liegt wirklich ueber der "
   "Mindestzahl", (at(lang_seg, "points") or 0) >= RAMP_MIN_POINTS)

# ── 7 Artefakte verschieben die Zeitachse nicht ─────────────────────────────
loecher = list(DFA)
for i in range(WARMUP_S + 100, WARMUP_S + 160):
    loecher[i] = None
ok("Loecher Trefferzusicherung: es wurden wirklich Werte entfernt",
   sum(1 for v in loecher if v is None) == 60)
res_loch = ramp.evaluate(loecher, WATTS, HR)
near("Loecher: die Schwelle wandert mit dem Loch",
     at(res_loch["hrvt1"], "seconds"), at(res["hrvt1"], "seconds"), 15)
ok("Loecher: die Punktzahl im Segment sinkt nicht",
   (at(res_loch["segment"], "points") or 0) < (at(res["segment"], "points") or 0))

# ── 8 Der geduennte Strom: sample_secs traegt den Unterschied ───────────────
STEP = 10
duenn = DFA[::STEP]
duenn_w = WATTS[::STEP]
res_duenn = ramp.evaluate(duenn, duenn_w, None, sample_secs=STEP)
ok("geduennt: gar keine Auswertung", res_duenn is not None)
near("geduennt: die Schwelle liegt an derselben SEKUNDE, nicht an derselben "
     "Stelle", at(res_duenn["hrvt1"], "seconds"), at(res["hrvt1"], "seconds"), 3 * STEP)
ok("geduennt Fixture-Beweis: der Strom ist wirklich kuerzer",
   len(duenn) < len(DFA) // 2)

# ── 9 Die Schwellen kommen aus derive, nicht aus diesem Modul ───────────────
src = (Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu"
       / "ramp.py").read_text(encoding="utf-8")
body = src.split('"""', 2)[2] if src.count('"""') >= 2 else src
for zahl in ["0.75", "0,75"]:
    ok(f"Waechter: die aerobe Schwelle steht als {zahl} im Quelltext",
       zahl not in body)
ok("Waechter Gegenprobe: eine eingebaute 0.75 wuerde gefunden",
   "0.75" in "if value > 0.75: pass")
ok("Waechter: DFA_AEROBIC wird gar nicht benutzt", "DFA_AEROBIC" in body)
ok("Waechter: DFA_ANAEROBIC wird gar nicht benutzt", "DFA_ANAEROBIC" in body)
for name in ["RAMP_SMOOTH_S", "RAMP_FLAT_S", "RAMP_READ_WINDOW_S",
             "RAMP_MIN_POINTS", "RAMP_RECOVERY_WINDOW_S"]:
    ok(f"Waechter: {name} kommt nicht aus const", name in body)

# ── 10 Die Karte braucht die Setzungen, also liefert die Payload sie ────────
for key in ["smooth_s", "flat_s", "read_window_s"]:
    ok(f"Payload: {key} fehlt - der Erklaertext muesste die Zahl erfinden",
       res.get(key) is not None)
check("Payload: die Glaettung wird gemeldet", res["smooth_s"], RAMP_SMOOTH_S)
check("Payload: die Ablesebreite wird gemeldet", res["read_window_s"], RAMP_READ_WINDOW_S)
check("Payload: die Flachstrecke wird gemeldet", res["flat_s"], RAMP_FLAT_S)
ok("Payload: das Segment nennt seine Grenzen nicht",
   res["segment"]["from_s"] < res["segment"]["to_s"])
ok("Payload: das Segment nennt seine Punktzahl nicht",
   res["segment"]["points"] > 0)

# (f) ABGELESEN WIRD DER MEDIAN EINES FENSTERS, nicht ein einzelner Wert.
#     Ein Zacken im Leistungsstrom - eine Boe, ein Antritt, ein Aussetzer des
#     Messgeraets - darf die Schwellenleistung nicht bestimmen.
ZACKEN = 900.0
zack_w = list(WATTS)
_i = int(t_at(DFA_AEROBIC)) - RAMP_READ_WINDOW_S // 2 + 1
zack_w[_i] = ZACKEN
ok("Zacken Trefferzusicherung: der Wert steht wirklich im Strom",
   zack_w[_i] != WATTS[_i])
ok("Zacken Fixture-Beweis: er liegt weit ueber der Schwellenleistung",
   ZACKEN > w_at(DFA_AEROBIC) * 2)
res_zack = ramp.evaluate(DFA, zack_w, HR)
near("Zacken: ein einzelner Ausschlag bestimmt die Schwellenleistung",
     at(res_zack["hrvt1"], "watts"), w_at(DFA_AEROBIC), 3)

# ── 11 Die Setzungen einzeln bissfest ───────────────────────────────────────
# Jede der folgenden Fixtures ist dafuer gebaut, GENAU EINE Regel zu treffen.
# Ohne sie bestehen die Regeln nur, weil der saubere Fall sie nie beansprucht.

# (a) NICHT HOCHRECHNEN: liegt eine Schwelle vor dem Segment, gibt es sie nicht.
tief = ramp.evaluate(*ride(peak=0.70))
ok("kein Hochrechnen: die Auswertung faellt ganz aus", tief is not None)
ok("kein Hochrechnen Fixture-Beweis: der Hochpunkt liegt wirklich unter der "
   "aeroben Schwelle - sonst laege sie im Segment", 0.70 < DFA_AEROBIC)
check("kein Hochrechnen: HRVT1 wird ueber den Hochpunkt hinaus erfunden",
      at(tief, "hrvt1"), None)
ok("kein Hochrechnen Gegenprobe: HRVT2 liegt IM Segment und wird genannt - "
   "sonst prueft die Zeile darueber nur, dass gar nichts kommt",
   at(tief, "hrvt2") is not None)

# (b) DIE GERADE DARF NICHT WEITER FALLEN ALS DIE MESSUNG.
#     Ein KONVEXER Abfall - steil, dann flach - endet bei 0,55; die Daten
#     kommen nie unter 0,5. Die Ausgleichsgerade schon, und zwar MITTEN im
#     Segment. Genau dafuer gibt es die Bedingung: HRVT2 nur, wenn der Boden
#     auch gemessen wurde. Ohne sie stuende hier eine Schwelle, die der
#     Athlet nie gefahren ist.
BODEN = 0.55
konvex = ([1.40] * 600
          + [BODEN + 0.85 * math.exp(-t / 260) for t in range(1200)]
          + [BODEN] * 120)
ok("konvexer Abfall Fixture-Beweis: die Daten kommen nie unter 0,5",
   min(konvex) >= DFA_ANAEROBIC)
res_konvex = ramp.evaluate(konvex)
ok("konvexer Abfall: die Auswertung faellt ganz aus", res_konvex is not None)
check("konvexer Abfall: der Boden gilt als erreicht",
      at(res_konvex, "reached_anaerobic"), False)
# Fixture-Beweis, ohne den die Zeile darunter nichts prueft: die GERADE
# schneidet 0,5 innerhalb des Segments - nur die Bedingung haelt sie auf.
_v = ramp._clean(konvex)
_seg = at(res_konvex, "segment")
_f = ramp._fit(_v, at(_seg, "from_s"), at(_seg, "to_s"), 1)
_cross = (DFA_ANAEROBIC - _f["intercept"]) / _f["slope"]
ok("konvexer Abfall Fixture-Beweis: die Gerade schneidet 0,5 IM Segment - "
   "sonst faellt HRVT2 schon an der Segmentgrenze weg",
   at(_seg, "from_s") <= _cross <= at(_seg, "to_s"))
check("konvexer Abfall: HRVT2 wird trotzdem genannt", at(res_konvex, "hrvt2"), None)
ok("konvexer Abfall Gegenprobe: HRVT1 liegt in der Messung und wird genannt",
   at(res_konvex, "hrvt1") is not None)

# (c) DIE GLAETTUNG SUCHT DIE GRENZEN: ein einzelner hoher Ausreisser im
#     Einrollen darf den Hochpunkt nicht an sich reissen.
AUSREISSER_AT = 60
AUSREISSER = 1.90
hoch = list(DFA)
hoch[AUSREISSER_AT] = AUSREISSER
ok("Glaettung Trefferzusicherung: der Ausreisser steht wirklich im Strom",
   hoch[AUSREISSER_AT] != DFA[AUSREISSER_AT])
ok("Glaettung Fixture-Beweis: er liegt ueber dem echten Hochpunkt - sonst "
   "aenderte er nichts", AUSREISSER > PEAK)
seg_hoch = ramp.segment(hoch)
check("Glaettung: der Ausreisser wird der Hochpunkt",
      at(seg_hoch, "max_alpha_start"), PEAK)
near("Glaettung: und zieht den Segmentanfang an sich",
     at(seg_hoch, "start_index"), WARMUP_S - 1, 20)

# (d) EIN EINZELNER EINBRUCH BEENDET DEN ABFALL NICHT.
EINBRUCH_S = 40
loch_von = WARMUP_S + 400
einbruch = list(DFA)
for i in range(loch_von, loch_von + EINBRUCH_S):
    einbruch[i] = 0.40
ok("Einbruch Fixture-Beweis: er ist kuerzer als die geforderte Flachstrecke",
   EINBRUCH_S < RAMP_FLAT_S)
ok("Einbruch Fixture-Beweis: er liegt wirklich unter 0,5", 0.40 < DFA_ANAEROBIC)
seg_einbruch = ramp.segment(einbruch)
near("Einbruch: der Abfall endet schon am Einbruch",
     at(seg_einbruch, "end_index"), at(seg, "end_index"), RAMP_SMOOTH_S)

# (e) DIE RUECKKEHR MUSS AUCH GEHALTEN WERDEN.
BLIP_S = 20
blip_dfa, blip_w, blip_hr = ride(cool_to=0.35)
blip_von = len(DFA) - COOL_S + 30
for i in range(blip_von, blip_von + BLIP_S):
    blip_dfa[i] = 0.60
ok("Blip Fixture-Beweis: er haelt kuerzer als gefordert", BLIP_S < RAMP_FLAT_S)
ok("Blip Fixture-Beweis: er liegt wirklich ueber 0,5", 0.60 >= DFA_ANAEROBIC)
res_blip = ramp.evaluate(blip_dfa, blip_w, blip_hr)
check("Blip: ein Zucken nach oben gilt als Rueckkehr",
      at(at(res_blip, "recovery"), "back_above_s"), None)


print(f"\ntest_ramp: {CHECKS} Prüfungen, {len(failures)} Fehler")
print("FEHLER:", failures if failures else "keine")
sys.exit(1 if failures else 0)
