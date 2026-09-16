"""Stufentest nach Rechenweg e1: Protokoll, Segment, Gerade, drei Zahlen, Erholung. Lauf: python3 tests/test_ramp.py"""

import json
import math
import sys
from pathlib import Path

import coldcache  # noqa: F401,E402  - MUSS vor jedem Bauteil-Import stehen (§9)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu"))

import ramp  # noqa: E402
from const import (  # noqa: E402
    RAMP_COOLDOWN_MAX_SHARE, RAMP_COOLDOWN_MIN, RAMP_END_CHECK_GAP_S, RAMP_END_CHECK_WINDOW_S,
    RAMP_FLAT_S, RAMP_MIN_POINTS, RAMP_PROTOCOL_SLOPE_SHARE, RAMP_READ_WINDOW_S,
    RAMP_RECOVERY_WINDOW_S, RAMP_SMOOTH_S, RAMP_STEP_W_PER_MIN, RAMP_WARMUP_MIN,
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
    return (node or {}).get(key) if isinstance(node, dict) or node is None else None


def near(label, got, expected, tol):
    global CHECKS
    CHECKS += 1
    ok_ = got is not None and expected is not None and abs(got - expected) <= tol
    print(f"{'PASS' if ok_ else 'FAIL'}  {label}: {got!r}" + ("" if ok_ else f"  (erwartet {expected!r} ± {tol})"))
    if not ok_:
        failures.append(label)


# --- ein Stufentest nach PROTOKOLL -------------------------------------------
# Einrollen flach (RAMP_WARMUP_MIN), Rampe mit steigender Leistung, Ausrollen
# (RAMP_COOLDOWN_MIN). In der Rampe: alpha bleibt erst oben (Plateau AM
# RAMPENBEGINN), faellt dann linear bis GENAU zum Lastende. Im Einrollen steht
# alpha HOEHER als am Rampenbeginn - wie am echten Test; sonst koennte keine
# Prüfung die Grenze Rampenbeginn von "ab Sekunde 0" unterscheiden (§7, Fall 28).
WARMUP_S = RAMP_WARMUP_MIN * 60
COOL_S = RAMP_COOLDOWN_MIN * 60
PLATEAU_S = 300
DROP_S = 1200
PEAK = 1.40
BOTTOM = 0.30
WARM_ALPHA = 1.60
START_W = 120.0
RAMP_W_PER_S = 0.1          # entspricht 6 W/min - reine Fixture-Groesse
LIMIT_W_PER_MIN = RAMP_PROTOCOL_SLOPE_SHARE * RAMP_STEP_W_PER_MIN


def ride(peak=PEAK, bottom=BOTTOM, warmup_s=WARMUP_S, plateau_s=PLATEAU_S, drop_s=DROP_S,
         cool_s=COOL_S, cool_to=0.95, warm_alpha=WARM_ALPHA):
    dfa, watts, hr = [], [], []
    for t in range(warmup_s):
        dfa.append(warm_alpha)
        watts.append(START_W)
        hr.append(110.0)
    for t in range(plateau_s + drop_s):
        if t < plateau_s:
            dfa.append(peak)
        else:
            dfa.append(peak + (bottom - peak) * ((t - plateau_s) / max(1, drop_s - 1)))
        watts.append(START_W + RAMP_W_PER_S * t)
        hr.append(110.0 + 0.04 * t)
    for t in range(cool_s):
        dfa.append(bottom + (cool_to - bottom) * (t / max(1, cool_s - 1)))
        watts.append(START_W)
        hr.append(170.0 - 0.08 * t)
    return dfa, watts, hr


DFA, WATTS, HR = ride()
P0 = WARMUP_S + PLATEAU_S                      # erste Sekunde des Abfalls
LOAD_END = WARMUP_S + PLATEAU_S + DROP_S - 1   # letzte Sekunde unter Last


# Erwartungswerte aus der Fixture selbst gerechnet, nicht abgeschrieben: der
# Abfall ist eine Gerade von PEAK bei P0 auf BOTTOM am Lastende.
def t_at(alpha):
    return P0 + (PEAK - alpha) / (PEAK - BOTTOM) * (DROP_S - 1)


def w_at(alpha):
    return START_W + RAMP_W_PER_S * (t_at(alpha) - WARMUP_S)


def first_run_below(values, needed):
    """Die ALTE Endregel, im Test nachgebaut: erster Lauf der geglaetteten
    Kurve unter 0,5, der `needed` Punkte haelt. Nur fuer Fixture-Beweise."""
    smooth = ramp._smooth(ramp._clean(values), RAMP_SMOOTH_S)
    run, first = 0, None
    for index, value in enumerate(smooth):
        if value is not None and value < DFA_ANAEROBIC:
            first = index if first is None else first
            run += 1
            if run >= needed:
                return first
        elif value is not None:
            run, first = 0, None
    return None


# ── 0 Die Fixture traegt das Protokoll ───────────────────────────────────────
proto = ramp.protocol(len(DFA), WATTS)
check("Protokoll: die saubere Fixture wird abgelehnt", at(proto, "code"), None)
check("Protokoll: der Rampenbeginn kommt nicht aus RAMP_WARMUP_MIN",
      at(proto, "ramp_start_index"), WARMUP_S)
check("Protokoll: das Lastende ist nicht Laenge minus RAMP_COOLDOWN_MIN",
      at(proto, "load_end_index"), LOAD_END)
near("Protokoll: das Einrollen misst nicht flach", at(proto, "warmup_w_per_min"), 0.0, 0.01)
near("Protokoll: die Rampe misst nicht 6 W/min", at(proto, "ramp_w_per_min"),
     RAMP_W_PER_S * 60, 0.05)
ok("Protokoll Fixture-Beweis: die Fixture-Rampe liegt ueber der Grenze, das "
   "Einrollen darunter", RAMP_W_PER_S * 60 >= LIMIT_W_PER_MIN > 0.0)
ok("Protokoll: nach dem Lastende liegt nicht beim Anteil unter davor",
   (at(proto, "after_w") or 1e9) <= RAMP_COOLDOWN_MAX_SHARE * (at(proto, "before_w") or 0))
ok("Fixture-Beweis: im Einrollen steht ein HOEHERER Wert als am Rampenbeginn - "
   "sonst prueft die Grenze Rampenbeginn nichts", max(DFA[:WARMUP_S]) > PEAK)

# ── 1 Segment e1: Rampenbeginn bis Lastende ─────────────────────────────────
seg = ramp.segment(DFA, WARMUP_S, LOAD_END)
ok("Segment: gar keins gefunden", seg is not None)
near("Segment: Anfang liegt nicht am Ende des Plateaus am Rampenbeginn",
     at(seg, "start_index"), P0, 2)
check("Segment: das Ende sitzt nicht am Lastende", at(seg, "end_index"), LOAD_END)
check("Segment: der Hochpunkt ist zugleich max_alpha_start", at(seg, "max_alpha_start"), PEAK)
ok("Segment: der Boden gilt nicht als erreicht", at(seg, "reached_anaerobic"))
ok("Segment: der Hochpunkt kommt aus dem Einrollen",
   (at(seg, "start_index") or 0) >= WARMUP_S)

# Der Anfang ist der LETZTE Hochpunkt, nicht der erste - jetzt am PLATEAU AM
# RAMPENBEGINN (vorher im Einrollen, das e1 gar nicht mehr ansieht).
ok("Segment Fixture-Beweis: das Plateau am Rampenbeginn ist laenger als die "
   "Glaettung - sonst waere erster und letzter Hochpunkt dasselbe",
   PLATEAU_S > 2 * RAMP_SMOOTH_S)
ok("Segment: der Anfang ist der ERSTE Hochpunkt statt des letzten",
   (at(seg, "start_index") or 0) > WARMUP_S + PLATEAU_S // 2)

# Das Ende ist das LASTENDE, nicht der erste Lauf unter 0,5.
_dip = first_run_below(DFA, RAMP_FLAT_S)
ok("Ende Fixture-Beweis: der erste Lauf unter 0,5 liegt deutlich VOR dem Lastende - "
   "sonst waeren alte und neue Endregel dieselbe", _dip is not None and _dip < LOAD_END - 2 * RAMP_FLAT_S)

# ── 2 Die Gerade, und dass sie GEFITTET und nicht abgelesen wird ─────────────
res = ramp.evaluate(DFA, WATTS, HR)
ok("Auswertung: nichts herausgekommen", res is not None)
near("HRVT1: Zeitpunkt", at(at(res, "hrvt1"), "seconds"), t_at(DFA_AEROBIC), 15)
near("HRVT1: Leistung", at(at(res, "hrvt1"), "watts"), w_at(DFA_AEROBIC), 3)
near("HRVT2: Zeitpunkt", at(at(res, "hrvt2"), "seconds"), t_at(DFA_ANAEROBIC), 15)
near("HRVT2: Leistung", at(at(res, "hrvt2"), "watts"), w_at(DFA_ANAEROBIC), 3)
ok("HRVT2 liegt ueber HRVT1 - sonst faellt die Kurve verkehrt herum",
   (at(at(res, "hrvt2"), "watts") or 0) > (at(at(res, "hrvt1"), "watts") or 0))
near("Gerade: Bestimmtheitsmass am sauberen Abfall", at(at(res, "segment"), "r2"), 1.0, 0.01)
near("Gerade: die Steigung ist nicht die des Abfalls (gegen die Zeit)",
     at(at(res, "segment"), "slope_per_min"), (BOTTOM - PEAK) / (DROP_S - 1) * 60, 0.001)

# GEGENPROBE, gezaehlt und benannt: ein Ausreisser unter 0,75 NACH dem
# Rampenbeginn, aber vor dem Abfall, darf die Schwelle nicht verschieben. Ein
# Ableser ("erster Punkt unter 0,75") haette ihn genommen.
spike = list(DFA)
SPIKE_AT = P0 - 150
spike[SPIKE_AT] = 0.40
ok("Ausreisser Trefferzusicherung: der Wert wurde wirklich veraendert",
   spike[SPIKE_AT] != DFA[SPIKE_AT])
ok("Ausreisser Fixture-Beweis: er liegt HINTER dem Rampenbeginn - die Grenze "
   "blendet ihn nicht schon aus", SPIKE_AT >= WARMUP_S)
res_spike = ramp.evaluate(spike, WATTS, HR)
ok("Ausreisser: die Auswertung faellt ganz aus", res_spike is not None)
near("Ausreisser: HRVT1 verschiebt sich trotzdem",
     at(at(res_spike, "hrvt1"), "seconds"), at(at(res, "hrvt1"), "seconds"), 15)
ok("Ausreisser Gegenprobe: ein Ableser haette ihn genommen - der Ausreisser "
   "liegt weit vor der Schwelle", SPIKE_AT < t_at(DFA_AEROBIC) - 300)

# ── 3 Die dritte Zahl, aus zweiter Hand ─────────────────────────────────────
check("dritte Zahl: der personalisierte alpha-Wert", at(res, "pers_alpha"),
      round((PEAK + DFA_ANAEROBIC) / 2, 3))
ok("dritte Zahl: sie ist nicht berechnet", at(res, "hrvt1_pers") is not None)
ok("dritte Zahl liegt UNTER HRVT1 - der Hochpunkt liegt ueber 1,0, also "
   "greift sie frueher", (at(at(res, "hrvt1_pers"), "watts") or 0) < (at(at(res, "hrvt1"), "watts") or 0))
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

# ── 5 Erholung: ab dem LASTENDE gemessen ────────────────────────────────────
rec = at(res, "recovery")
ok("Erholung: nicht gemessen", rec is not None)
check("Erholung: das Fenster kommt nicht aus der Konstante",
      at(rec, "window_s"), RAMP_RECOVERY_WINDOW_S)
ok("Erholung: der Wert am Ende liegt nicht ueber dem Boden",
   (at(rec, "alpha_end") or 0) > BOTTOM)
# back_above_s zaehlt seit e1 AB DEM LASTENDE. Erwartung aus der Fixture: die
# erste Sekunde nach dem Lastende, ab der alpha ueber 0,5 liegt (die Kurve
# steigt dort monoton, also haelt sie).
_back = next(i for i in range(LOAD_END, len(DFA)) if DFA[i] >= DFA_ANAEROBIC)
check("Erholung: back_above_s zaehlt nicht ab dem Lastende",
      at(rec, "back_above_s"), _back - LOAD_END)
ok("Erholung Fixture-Beweis: ab dem ersten Lauf unter 0,5 gezaehlt kaeme eine "
   "andere Zahl heraus - sonst prueft die Zeile darueber den Bezugspunkt nicht",
   _dip is not None and _back - _dip != _back - LOAD_END)
# GEGENPROBE: eine Fahrt, die unten BLEIBT, hat keine Rueckkehr.
unten = ride(cool_to=0.35)
ok("Erholung Trefferzusicherung: das Ausrollen endet wirklich tiefer",
   unten[0][-1] < DFA[-1])
res_unten = ramp.evaluate(*unten)
ok("Erholung Gegenprobe: die Fahrt, die unten bleibt, wird gar nicht ausgewertet",
   res_unten is not None)
check("Erholung Gegenprobe: die Rueckkehr wird auch ohne Rueckkehr gemeldet",
      at(at(res_unten, "recovery"), "back_above_s"), None)

# ── 6 Die Protokollpruefung: je Fall ein eigener Grund ──────────────────────
# Jeder Fall: der Code, dass KEINE Zahl herauskommt, und eine
# Trefferzusicherung, dass die Fixture den Fall wirklich herstellt.
REASONS = {}


def refused(label, streams, code, proof, proof_label, sample_secs=1):
    dfa, watts, hr = streams
    out = ramp.measure(dfa, watts, hr, sample_secs)
    ok(f"{label} Trefferzusicherung: {proof_label}", proof)
    check(f"{label}: falscher Grund", at(out, "code"), code)
    check(f"{label}: trotzdem ein Ergebnis", at(out, "result"), None)
    ok(f"{label}: kein Satz zum Grund", isinstance(at(out, "reason"), str) and len(at(out, "reason")) > 20)
    REASONS[code] = at(out, "reason")
    return out


_cst = [0.9] * 3600, [180.0] * 3600, [140.0] * 3600
refused("gewoehnliche Fahrt", _cst, ramp.RAMP_NOT_RISING,
        len(set(_cst[1])) == 1, "die Leistung ist wirklich konstant")
check("leerer Strom: eine Schwelle wird erfunden", ramp.evaluate(None), None)

_noalpha = ([0.0] * len(DFA), WATTS, HR)
refused("nur Artefakte", _noalpha, ramp.NO_ALPHA,
        at(ramp.protocol(len(DFA), WATTS), "code") is None and all(v == 0.0 for v in _noalpha[0]),
        "der Leistungsstrom traegt das Protokoll, alpha ist ueberall 0")

_ohne_ein = ride(warmup_s=0)
refused("ohne Einrollen", _ohne_ein, ramp.WARMUP_NOT_FLAT,
        (_ohne_ein[1][WARMUP_S - 1] - _ohne_ein[1][0]) > LIMIT_W_PER_MIN * RAMP_WARMUP_MIN,
        "die Leistung steigt in den ersten Minuten schneller als die Grenze")

_ein_null = (DFA, [0.0] * WARMUP_S + WATTS[WARMUP_S:], HR)
refused("Einrollen ohne Leistung", _ein_null, ramp.WARMUP_NO_WATTS,
        all(v == 0 for v in _ein_null[1][:WARMUP_S]) and any(v > 0 for v in _ein_null[1][WARMUP_S:]),
        "im Einrollen steht nur 0 W, danach Leistung")

_ohne_aus = ride(cool_s=0)
refused("ohne Ausrollen", _ohne_aus, ramp.COOLDOWN_MISSING,
        len(_ohne_aus[1]) == LOAD_END + 1 and _ohne_aus[1][-1] == max(_ohne_aus[1]),
        "die Fahrt endet am Lastende, auf der hoechsten Leistung")

_kurz_aus = ride(cool_s=COOL_S // 2)
refused("zu kurzes Ausrollen", _kurz_aus, ramp.COOLDOWN_TOO_SHORT,
        COOL_S - COOL_S // 2 > RAMP_END_CHECK_GAP_S,
        "das Ausrollen fehlt um mehr als die Toleranz")

_lang_aus = ride(cool_s=COOL_S + COOL_S // 2)
refused("zu langes Ausrollen", _lang_aus, ramp.COOLDOWN_TOO_LONG,
        COOL_S // 2 > RAMP_END_CHECK_GAP_S,
        "das Ausrollen ist um mehr als die Toleranz laenger")

# Die TOLERANZ ist eine Setzung, und sie gilt wirklich: ein um die halbe
# Luecke verschobenes Lastende faellt der Pruefung NICHT auf.
_tol = ride(cool_s=COOL_S + RAMP_END_CHECK_GAP_S // 2)
check("Toleranz: ein um weniger als RAMP_END_CHECK_GAP_S verschobenes Lastende wird abgelehnt",
      at(ramp.measure(*_tol), "code"), None)

refused("ohne Watt", (DFA, None, HR), ramp.NO_WATTS,
        at(ramp.protocol(len(DFA), WATTS), "code") is None,
        "dieselbe Fahrt MIT Leistung traegt das Protokoll")
refused("Watt nur Null", (DFA, [0.0] * len(DFA), HR), ramp.NO_WATTS,
        len(DFA) > WARMUP_S + COOL_S, "die Fahrt ist lang genug, nur die Leistung fehlt")
refused("Stroeme verschieden lang", (DFA, WATTS[:-1], HR), ramp.LENGTH_MISMATCH,
        len(WATTS[:-1]) == len(DFA) - 1, "der Leistungsstrom ist eine Sekunde kuerzer")

_kurz = ride(plateau_s=0, drop_s=0, cool_s=WARMUP_S // 2 + 50)
refused("zu kurze Fahrt", _kurz, ramp.TOO_SHORT,
        len(_kurz[0]) < WARMUP_S + COOL_S, "die Fahrt ist kuerzer als Einrollen plus Ausrollen")

_steigt = list(DFA)
for _i in range(WARMUP_S, LOAD_END + 1):
    _steigt[_i] = 0.5 + (_i - WARMUP_S) / (LOAD_END - WARMUP_S)
refused("kein Abfall", (_steigt, WATTS, HR), ramp.NO_FALL,
        max(_steigt[WARMUP_S:LOAD_END + 1]) == _steigt[LOAD_END],
        "alpha steigt ueber die Rampe, der hoechste Wert liegt am Lastende")

KURZ_DROP = 40
refused("zu kurzer Abfall", ride(plateau_s=PLATEAU_S + DROP_S - KURZ_DROP, drop_s=KURZ_DROP),
        ramp.TOO_FEW_POINTS, KURZ_DROP < RAMP_MIN_POINTS,
        "der Abfall ist kuerzer als die Mindestzahl")
_lang = ramp.evaluate(*ride(plateau_s=PLATEAU_S + DROP_S - 400, drop_s=400))
ok("zu kurzer Abfall Gegenprobe: dieselbe Form mit LANGEM Abfall wird "
   "ausgewertet - sonst prueft die Zeile darueber nur, dass nie etwas kommt",
   _lang is not None)
ok("zu kurzer Abfall Fixture-Beweis: der lange Fall liegt wirklich ueber der "
   "Mindestzahl", (at(at(_lang, "segment"), "points") or 0) >= RAMP_MIN_POINTS)

_codes = [ramp.NO_WATTS, ramp.LENGTH_MISMATCH, ramp.TOO_SHORT, ramp.WARMUP_NO_WATTS,
          ramp.WARMUP_NOT_FLAT, ramp.RAMP_NOT_RISING, ramp.COOLDOWN_MISSING,
          ramp.COOLDOWN_TOO_SHORT, ramp.COOLDOWN_TOO_LONG, ramp.NO_ALPHA, ramp.NO_FALL,
          ramp.TOO_FEW_POINTS]
check("Gruende: nicht jeder Grund ist oben ausgeloest worden", sorted(REASONS), sorted(_codes))
check("Gruende: zwei Faelle teilen sich einen Satz", len(set(REASONS.values())), len(_codes))
for _wort in ("zu locker", "Fehler", "Mangel", "leider", "nicht ausreich"):
    ok(f"Gruende: gesperrtes Wort ({_wort})", all(_wort not in t for t in REASONS.values()))
ok("Gruende: der Satz ohne Einrollen nennt die gemessene Steigung nicht",
   "W/min" in (REASONS.get(ramp.WARMUP_NOT_FLAT) or "") and "–" not in (REASONS.get(ramp.WARMUP_NOT_FLAT) or "–"))
import ramp_tests  # noqa: E402
ok("Gruende: ein Satz ist laenger als das Archivfeld - set_entry schnitte ihn still ab",
   all(len(t) <= ramp_tests.NOTE_LIMIT for t in REASONS.values()))
ok("Gruende: der alte Sammelsatz steht noch",
   all("auswertbarer Abfall" not in t for t in REASONS.values()))

# ── 7 Artefakte verschieben die Zeitachse nicht ─────────────────────────────
loecher = list(DFA)
for i in range(P0 + 100, P0 + 160):
    loecher[i] = None
ok("Loecher Trefferzusicherung: es wurden wirklich Werte entfernt",
   sum(1 for v in loecher if v is None) == 60)
res_loch = ramp.evaluate(loecher, WATTS, HR)
near("Loecher: die Schwelle wandert mit dem Loch",
     at(at(res_loch, "hrvt1"), "seconds"), at(at(res, "hrvt1"), "seconds"), 15)
ok("Loecher: die Punktzahl im Segment sinkt nicht",
   (at(at(res_loch, "segment"), "points") or 0) < (at(at(res, "segment"), "points") or 0))

# ── 8 Der geduennte Strom: sample_secs traegt den Unterschied ───────────────
STEP = 10
duenn = DFA[::STEP]
duenn_w = WATTS[::STEP]
res_duenn = ramp.evaluate(duenn, duenn_w, None, sample_secs=STEP)
ok("geduennt: gar keine Auswertung", res_duenn is not None)
near("geduennt: die Schwelle liegt an derselben SEKUNDE, nicht an derselben "
     "Stelle", at(at(res_duenn, "hrvt1"), "seconds"), at(at(res, "hrvt1"), "seconds"), 3 * STEP)
ok("geduennt Fixture-Beweis: der Strom ist wirklich kuerzer",
   len(duenn) < len(DFA) // 2)

# ── 9 Die Schwellen und Setzungen kommen aus const/derive ───────────────────
src = (Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu"
       / "ramp.py").read_text(encoding="utf-8")
body = src.split('"""', 2)[2] if src.count('"""') >= 2 else src
for zahl in ["0.75", "0,75"]:
    ok(f"Waechter: die aerobe Schwelle steht als {zahl} im Quelltext",
       zahl not in body)
for zahl in ["0.8", "0.5 *", "* 0.5"]:
    ok(f"Waechter: eine Protokoll-Setzung steht als {zahl!r} im Quelltext", zahl not in body)
ok("Waechter Gegenprobe: eine eingebaute 0.75 wuerde gefunden",
   "0.75" in "if value > 0.75: pass")
ok("Waechter: DFA_AEROBIC wird gar nicht benutzt", "DFA_AEROBIC" in body)
ok("Waechter: DFA_ANAEROBIC wird gar nicht benutzt", "DFA_ANAEROBIC" in body)
for name in ["RAMP_SMOOTH_S", "RAMP_FLAT_S", "RAMP_READ_WINDOW_S",
             "RAMP_MIN_POINTS", "RAMP_RECOVERY_WINDOW_S", "RAMP_WARMUP_MIN",
             "RAMP_COOLDOWN_MIN", "RAMP_STEP_W_PER_MIN", "RAMP_PROTOCOL_SLOPE_SHARE",
             "RAMP_COOLDOWN_MAX_SHARE", "RAMP_END_CHECK_WINDOW_S", "RAMP_END_CHECK_GAP_S"]:
    ok(f"Waechter: {name} kommt nicht aus const", name in body)

# ── 10 Die Karte braucht die Setzungen, also liefert die Payload sie ────────
for key in ["smooth_s", "flat_s", "read_window_s", "protocol"]:
    ok(f"Payload: {key} fehlt - der Erklaertext muesste die Zahl erfinden",
       at(res, key) is not None)
check("Payload: die Glaettung wird gemeldet", at(res, "smooth_s"), RAMP_SMOOTH_S)
check("Payload: die Ablesebreite wird gemeldet", at(res, "read_window_s"), RAMP_READ_WINDOW_S)
check("Payload: die Flachstrecke wird gemeldet", at(res, "flat_s"), RAMP_FLAT_S)
_pp = at(res, "protocol")
check("Payload: der Rampenbeginn wird nicht in Sekunden gemeldet", at(_pp, "ramp_start_s"), WARMUP_S)
check("Payload: das Lastende wird nicht in Sekunden gemeldet", at(_pp, "load_end_s"), LOAD_END)
check("Payload: der Steigungsanteil wird gemeldet", at(_pp, "slope_share"), RAMP_PROTOCOL_SLOPE_SHARE)
check("Payload: der Ausrollanteil wird gemeldet", at(_pp, "cooldown_max_share"), RAMP_COOLDOWN_MAX_SHARE)
ok("Payload: das Segment nennt seine Grenzen nicht",
   (at(at(res, "segment"), "from_s") or 0) < (at(at(res, "segment"), "to_s") or 0))
ok("Payload: das Segment nennt seine Punktzahl nicht",
   (at(at(res, "segment"), "points") or 0) > 0)

# (f) ABGELESEN WIRD DER MEDIAN EINES FENSTERS, nicht ein einzelner Wert.
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
     at(at(res_zack, "hrvt1"), "watts"), w_at(DFA_AEROBIC), 3)

# ── 11 Die Setzungen einzeln bissfest ───────────────────────────────────────
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
#     kommen nie unter 0,5. Die Ausgleichsgerade schon, MITTEN im Segment.
BODEN = 0.55
konvex = ([WARM_ALPHA] * WARMUP_S + [PEAK] * PLATEAU_S
          + [BODEN + (PEAK - BODEN) * math.exp(-t / 260) for t in range(DROP_S)]
          + [BODEN + (0.95 - BODEN) * t / (COOL_S - 1) for t in range(COOL_S)])
ok("konvexer Abfall Fixture-Beweis: gleich lang wie der Leistungsstrom",
   len(konvex) == len(WATTS))
ok("konvexer Abfall Fixture-Beweis: die Daten kommen nie unter 0,5",
   min(konvex) >= DFA_ANAEROBIC)
res_konvex = ramp.evaluate(konvex, WATTS, HR)
ok("konvexer Abfall: die Auswertung faellt ganz aus", res_konvex is not None)
check("konvexer Abfall: der Boden gilt als erreicht",
      at(res_konvex, "reached_anaerobic"), False)
_v = ramp._clean(konvex)
_seg = at(res_konvex, "segment")
_f = ramp._fit(_v, at(_seg, "from_s") or 0, at(_seg, "to_s") or 0, 1) or {}
_cross = ((DFA_ANAEROBIC - _f.get("intercept", 0.0)) / _f.get("slope")) if _f.get("slope") else -1
ok("konvexer Abfall Fixture-Beweis: die Gerade schneidet 0,5 IM Segment - "
   "sonst faellt HRVT2 schon an der Segmentgrenze weg",
   (at(_seg, "from_s") or 0) <= _cross <= (at(_seg, "to_s") or -1))
check("konvexer Abfall: HRVT2 wird trotzdem genannt", at(res_konvex, "hrvt2"), None)
ok("konvexer Abfall Gegenprobe: HRVT1 liegt in der Messung und wird genannt",
   at(res_konvex, "hrvt1") is not None)

# (c) DIE GLAETTUNG SUCHT DIE GRENZEN: ein einzelner hoher Ausreisser AM
#     RAMPENBEGINN darf den Hochpunkt nicht an sich reissen.
AUSREISSER_AT = WARMUP_S + 60
AUSREISSER = 1.90
hoch = list(DFA)
hoch[AUSREISSER_AT] = AUSREISSER
ok("Glaettung Trefferzusicherung: der Ausreisser steht wirklich im Strom",
   hoch[AUSREISSER_AT] != DFA[AUSREISSER_AT])
ok("Glaettung Fixture-Beweis: er liegt ueber dem echten Hochpunkt - sonst "
   "aenderte er nichts", AUSREISSER > PEAK)
ok("Glaettung Fixture-Beweis: er liegt HINTER dem Rampenbeginn - nicht die "
   "Grenze haelt ihn fern, sondern die Glaettung", AUSREISSER_AT >= WARMUP_S)
seg_hoch = ramp.segment(hoch, WARMUP_S, LOAD_END)
check("Glaettung: der Ausreisser wird der Hochpunkt",
      at(seg_hoch, "max_alpha_start"), PEAK)
near("Glaettung: und zieht den Segmentanfang an sich",
     at(seg_hoch, "start_index"), P0, 2)

# (c2) EIN AUSREISSER IM EINROLLEN WIRD GAR NICHT MEHR GESEHEN - auch einer,
#      den die Glaettung nicht wegnimmt (ein ganzer Block).
BLOCK_VON, BLOCK_S = 300, 4 * RAMP_SMOOTH_S
einroll = list(DFA)
for _i in range(BLOCK_VON, BLOCK_VON + BLOCK_S):
    einroll[_i] = AUSREISSER
_sm = ramp._smooth(ramp._clean(einroll), RAMP_SMOOTH_S)
ok("Einrollen Fixture-Beweis: der Block ueberlebt die Glaettung - sonst haelt "
   "ihn die Glaettung fern und nicht die Grenze",
   max(v for v in _sm[:WARMUP_S] if v is not None) >= AUSREISSER)
ok("Einrollen Fixture-Beweis: der Block liegt vor dem Rampenbeginn",
   BLOCK_VON + BLOCK_S <= WARMUP_S)
seg_ein = ramp.segment(einroll, WARMUP_S, LOAD_END)
check("Einrollen: der Block im Einrollen wird der Hochpunkt",
      at(seg_ein, "max_alpha_start"), PEAK)

# (d) EIN EINZELNER EINBRUCH IST KEIN ERREICHTER BODEN. Vorher: er beendete den
#     Abfall nicht. Das Ende ist jetzt das Lastende und kann nicht mehr frueh
#     kommen - bissfest bleibt die Frage, ob er als Boden zaehlt.
EINBRUCH_S = 40
einbruch_dfa, einbruch_w, einbruch_hr = ride(bottom=0.62, cool_to=1.0)
loch_von = P0 + 400
for i in range(loch_von, loch_von + EINBRUCH_S):
    einbruch_dfa[i] = 0.40
ok("Einbruch Fixture-Beweis: er ist kuerzer als die geforderte Flachstrecke",
   EINBRUCH_S < RAMP_FLAT_S)
ok("Einbruch Fixture-Beweis: er liegt wirklich unter 0,5", 0.40 < DFA_ANAEROBIC)
ok("Einbruch Fixture-Beweis: er liegt im Segment", WARMUP_S <= loch_von < LOAD_END)
res_einbruch = ramp.evaluate(einbruch_dfa, einbruch_w, einbruch_hr)
check("Einbruch: ein kurzer Einbruch gilt als erreichter Boden",
      at(res_einbruch, "reached_anaerobic"), False)
check("Einbruch: und liefert eine HRVT2", at(res_einbruch, "hrvt2"), None)

# (e) DIE RUECKKEHR MUSS AUCH GEHALTEN WERDEN.
BLIP_S = 20
blip_dfa, blip_w, blip_hr = ride(cool_to=0.35)
blip_von = LOAD_END + 30
for i in range(blip_von, blip_von + BLIP_S):
    blip_dfa[i] = 0.60
ok("Blip Fixture-Beweis: er haelt kuerzer als gefordert", BLIP_S < RAMP_FLAT_S)
ok("Blip Fixture-Beweis: er liegt wirklich ueber 0,5", 0.60 >= DFA_ANAEROBIC)
res_blip = ramp.evaluate(blip_dfa, blip_w, blip_hr)
check("Blip: ein Zucken nach oben gilt als Rueckkehr",
      at(at(res_blip, "recovery"), "back_above_s"), None)

# ── 12 Der echte Strom: Stufentest 16.09.2026, Aktivitaet i187258578 ────────
# Die SOLLWERTE sind am Strom gerechnet und in der Uebergabe festgehalten
# (Grenzen 900 / N-600). Die Umstellung muss sie treffen.
_real_path = Path(__file__).resolve().parent / "data" / "ramp_i187258578.json"
REAL = json.loads(_real_path.read_text(encoding="utf-8")) if _real_path.exists() else {}
RA, RW, RH = REAL.get("alpha1") or [], REAL.get("watts") or [], REAL.get("heartrate") or []
check("echter Strom Trefferzusicherung: Laenge 2735 s", len(RA), 2735)
ok("echter Strom Trefferzusicherung: alle drei Stroeme gleich lang und lueckenlos",
   len(RA) == len(RW) == len(RH) and REAL.get("gaps") == 0 and REAL.get("sample_secs") == 1)
real_proto = ramp.protocol(len(RA), RW)
check("echter Strom: das Protokoll wird abgelehnt", at(real_proto, "code"), None)
check("echter Strom: Einrollen W/min", at(real_proto, "warmup_w_per_min"), 1.26)
check("echter Strom: Rampe W/min", at(real_proto, "ramp_w_per_min"), 5.69)
check("echter Strom: Watt vor dem Lastende", at(real_proto, "before_w"), 249.0)
check("echter Strom: Watt nach dem Lastende", at(real_proto, "after_w"), 130.0)
real = ramp.evaluate(RA, RW, RH)
_rs = at(real, "segment")
check("echter Strom: Segmentanfang", at(_rs, "from_s"), 1058)
check("echter Strom: Segmentende", at(_rs, "to_s"), 2134)
check("echter Strom: Hochpunkt", at(real, "max_alpha_start"), 1.662)
check("echter Strom: Steigung je Minute", at(_rs, "slope_per_min"), -0.0649)
check("echter Strom: r2", at(_rs, "r2"), 0.815)
check("echter Strom: Boden erreicht", at(real, "reached_anaerobic"), True)
for _key, _want in (("hrvt1", (1630, 213.0, 178.0)), ("hrvt2", (1861, 233.0, 186.0)),
                    ("hrvt1_pers", (1324, 183.0, 167.0))):
    _got = at(real, _key)
    check(f"echter Strom: {_key} Sekunde / Watt / Puls",
          (at(_got, "seconds"), at(_got, "watts"), at(_got, "hr")), _want)
check("echter Strom: personalisiertes alpha", at(real, "pers_alpha"), 1.081)
check("echter Strom: Rueckkehr ueber 0,5 ab Lastende", at(at(real, "recovery"), "back_above_s"), 193)

# DER BEFUND, als Fixture-Beweis am echten Strom - so, wie er am Strom TRAEGT.
# (i) Blind war die KOMBINATION: Start im Einrollen (s 224, Plateau in der
#     Regression) plus Ende am ersten Lauf unter 0,5. Dort liegt die Gerade
#     noch ueber 0,5, HRVT2 null - das gespeicherte Ergebnis.
_rdip = first_run_below(RA, RAMP_FLAT_S)
ok("Befund Trefferzusicherung: der erste Lauf unter 0,5 liegt vor dem Lastende",
   _rdip is not None and _rdip < 2134)
_rclean = ramp._clean(RA)


def _line_at(start, end):
    fit = ramp._fit(_rclean, start, end, 1) or {}
    return fit.get("intercept", 0.0) + fit.get("slope", 0.0) * end


ok("Befund: mit Start s 224 und Ende am ersten Dip liegt die Gerade am Dip "
   "NICHT ueber 0,5 - dann erklaert das die gespeicherte hrvt2 null nicht",
   _line_at(224, _rdip or 224) > DFA_ANAEROBIC)
# (ii) Das Dip-Ende ALLEIN ist nicht blind: ab Rampenbeginn gefittet, trifft
#      auch es 0,5 vor dem Dip. Diese Zeile haelt die korrigierte Diagnose fest
#      (Uebergabe sagte "gleich welcher Start" - am Strom widerlegt).
ok("Befund: mit Start ab Rampenbeginn und Ende am ersten Dip liegt die Gerade "
   "am Dip ueber 0,5 - die Diagnose \"Dip-Ende allein ist blind\" traefe zu",
   _line_at(1058, _rdip or 1058) < DFA_ANAEROBIC)
# (ii) Start ohne die Grenze Rampenbeginn: der Hochpunkt liegt im Einrollen.
_rpeak = ramp._peak(ramp._smooth(ramp._clean(RA), RAMP_SMOOTH_S), 0, 2134)
ok("Befund: ohne die Grenze Rampenbeginn laege der Hochpunkt NICHT im Einrollen",
   _rpeak is not None and _rpeak[0] < RAMP_WARMUP_MIN * 60)
near("Befund: und die Leistung dort ist nicht die flache des Einrollens",
     ramp._span_median(RW, (_rpeak or (0, 0))[0] - 30, (_rpeak or (0, 0))[0] + 30), 128, 3)


print(f"\ntest_ramp: {CHECKS} Prüfungen, {len(failures)} Fehler")
print("FEHLER:", failures if failures else "keine")
sys.exit(1 if failures else 0)
