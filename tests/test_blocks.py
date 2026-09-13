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


LAP = [{"label": "WORK", "start_s": 0, "end_s": 600, "moving_time": 600}]
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
VIER = [{"label": "WORK", "start_s": 0, "end_s": 240, "moving_time": 240}]
mit = derive.dfa_blocks(kurz_dfa, kurz_w, kurz_hr, VIER, 1)[0]["alpha"]
ohne = derive._median(kurz_dfa)
check("4-min-Block, verworfen: der eingeschwungene Wert", mit, 0.45)
ok("Gegenprobe: ohne Verwerfen kippt derselbe Block", abs(ohne - mit) > 0.5)
# und beim LANGEN Block ist der Median robust - der Unterschied ist die
# Blocklaenge, nicht die Regel
ok("beim langen Block faellt es nicht auf - genau deshalb ist es gefaehrlich",
   abs(derive._median(dfa) - b["alpha"]) < 0.01)

# Nur Arbeitsabschnitte, und nur lange genug.
kurz = [{"label": "WORK", "start_s": 0, "end_s": 140, "moving_time": 140}]
check("ein zu kurzer Block traegt nichts", derive.dfa_blocks(dfa, w, hr, kurz, 1), [])
knapp = [{"label": "WORK", "start_s": 0, "end_s": 300, "moving_time": 300}]
check("ein Block mit zu wenigen Punkten nach dem Verwerfen faellt raus",
      len(derive.dfa_blocks(dfa[:300], w[:300], hr[:300],
                            [{"label": "WORK", "start_s": 0, "end_s": 135,
                              "moving_time": 155}], 1)), 0)
ok("ein ausreichend langer Block bleibt", len(derive.dfa_blocks(dfa, w, hr, knapp, 1)) == 1)
check("ohne Laps gibt es keine Bloecke", derive.dfa_blocks(dfa, w, hr, [], 1), [])


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
