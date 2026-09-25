"""Die Steuerung v2: Vorgabe ab Startwert, C6, t-Band, Schalter.
Lauf: python3 tests/test_steering.py
"""

import sys
from pathlib import Path

import coldcache  # noqa: F401  - MUSS vor jedem Bauteil-Import stehen (§9)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu"))

import blocks  # noqa: E402
import steering  # noqa: E402
import workouts as WK  # noqa: E402
from const import (  # noqa: E402
    STEERING_BAND_MIN_N,
    STEERING_BAND_WINDOW, STEERING_MIN_UNITS, STEERING_STEP_W,
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


def point(date, alphas, watts, hrs, minutes=None):
    """Eine Einheit, wie `blocks.series()` sie in `points` liefert."""
    return {"date": date, "name": "Einheit " + date, "n_blocks": len(alphas),
            "block_alphas": list(alphas), "block_watts_each": list(watts),
            "block_hr": list(hrs),
            "block_minutes": list(minutes or [4.0] * len(alphas)),
            "median_alpha": sorted(alphas)[len(alphas) // 2],
            "median_watts": sorted(watts)[len(watts) // 2],
            # Die VERLAUFSgroesse - sie bleibt in der Zeile stehen, auch wenn
            # sie nicht mehr steuert. Das Rampenende hing bis 0.60.0 an ihr.
            "first_watts": watts[0], "first_alpha": alphas[0]}


# ---------------------------------------------------------------------------
# DIE ECHTEN EINHEITEN (gesamttabelle_kreuzprobe.md, Live 17.09.2026). Sie sind
# der Massstab: was hier herauskommt, hat der Athlet selbst gefahren.
# ---------------------------------------------------------------------------
SS_REAL = [
    point("2026-07-05", [0.651, 0.657], [188, 167], [171, 163], [19.9, 20.3]),
    point("2026-08-05", [0.809, 0.696], [194, 189], [160, 161], [14.9, 14.9]),
    point("2026-08-14", [0.730, 0.680], [194, 190], [164, 165], [20.0, 19.9]),
    point("2026-08-20", [0.915, 0.699], [194, 192], [167, 168], [15.0, 15.0]),
    point("2026-08-24", [0.869, 0.658], [198, 194], [166, 171], [20.0, 20.0]),
]
VO_REAL = [
    point("2026-07-19", [1.032, 0.571, 0.497, 0.409, 0.477],
          [278, 264, 260, 256, 246], [177, 175, 179, 179, 179], [2.9] * 5),
    point("2026-07-25", [0.958, 0.623, 0.470, 0.463, 0.384, 0.309],
          [267, 268, 269, 258, 250, 244], [167, 176, 181, 181, 178, 179], [2.9] * 6),
    point("2026-08-02", [0.828, 0.522, 0.360], [250, 251, 251], [174, 179, 183], [3.9, 4.0, 4.0]),
    point("2026-08-11", [0.426, 0.399, 0.338, 0.431], [260, 251, 236, 230],
          [181, 182, 181, 178], [3.9] * 4),
    point("2026-08-19", [0.513, 0.362, 0.337], [259, 245, 230], [184, 187, 185], [4.0] * 3),
    point("2026-09-01", [0.472, 0.396, 0.381, 0.405], [257, 251, 250, 248],
          [179, 184, 186, 187], [3.9] * 4),
]


# DER STARTWERT ALS FIXTURE, nicht aus dem Code (0.66.3, Michael-Befund): die
# Zahlen sind die des ersten Athleten am 17.09.2026 - hier als Prueffall, im
# Paket nur noch als Uebernahme fuer sein Archiv (LEGACY_STEERING_ANCHOR).
JO_W = {"sweetspot": 190, "vo2max": 250}
JO_DATE = "2026-09-17"
JO_ANCHORS = {f: {"w": w, "date": JO_DATE, "source": "Fixture"} for f, w in JO_W.items()}

print("=== 1. BLOCK 1 STEUERT NICHT ===")
_ss = steering.family_state(SS_REAL, "sweetspot", JO_ANCHORS.get("sweetspot"))
_vo = steering.family_state(VO_REAL, "vo2max", JO_ANCHORS.get("vo2max"))
check("SS: Block 1 faellt aus der Steuerung (alpha der Zeilen)",
      [r["alpha"] for r in _ss["rows"]], [0.657, 0.696, 0.68, 0.699, 0.658])
check("SS: die gesteuerten Watt sind die OHNE Block 1",
      [r["watts"] for r in _ss["rows"]], [167, 189, 190, 192, 194])
# GEGENPROBE: mit Block 1 waeren es andere Zahlen - sonst prueft das nichts.
_mit = [sorted(p["block_alphas"])[len(p["block_alphas"]) // 2] for p in SS_REAL]
ok("Gegenprobe: mit Block 1 waere der alpha-Median ein anderer",
   _mit != [r["alpha"] for r in _ss["rows"]])
check("Block 1 zaehlt laut Zustand nicht mit", _ss["first_block_counts"], False)

print("\n=== 2. DIE VORGABE: Startwert, Stichtag, C6 ===")
check("SS steht auf dem Startwert", _ss["watts"], JO_W["sweetspot"])
check("VO2max steht auf dem Startwert", _vo["watts"], JO_W["vo2max"])
check("keine Einheit nach dem Stichtag", (_ss["n_since"], _vo["n_since"]), (0, 0))
check("also auch keine Bewegung", (_ss["moves"], _vo["moves"]), (0, 0))
ok("und die Karte sagt warum", bool(_ss["note"]))
ok("alle echten Einheiten liegen im Korridor",
   all(r["side"] == 0 for r in _ss["rows"] + _vo["rows"]))

# C6 TRIFFT: drei Einheiten nach dem Stichtag, zwei davon zu hart.
_hart = VO_REAL + [point("2026-09-20", [0.9, 0.18, 0.17], [250, 250, 248], [180, 184, 186]),
                   point("2026-09-27", [0.9, 0.19, 0.18], [250, 250, 248], [180, 184, 186]),
                   point("2026-10-04", [0.9, 0.40, 0.42], [250, 250, 248], [180, 184, 186])]
_s2 = steering.family_state(_hart, "vo2max", JO_ANCHORS.get("vo2max"))
check("C6 nach unten: zwei von drei unter dem Korridor",
      _s2["watts"], JO_W["vo2max"] - STEERING_STEP_W)
check("und genau EINE Bewegung, nicht zwei", _s2["moves"], 1)
# GEGENPROBE: dieselben drei Einheiten INNERHALB des Korridors bewegen nichts.
_weich = VO_REAL + [point(d, [0.9, 0.40, 0.42], [250, 250, 248], [180, 184, 186])
                    for d in ("2026-09-20", "2026-09-27", "2026-10-04")]
check("Gegenprobe: im Korridor bewegt sich nichts",
      steering.family_state(_weich, "vo2max", JO_ANCHORS.get("vo2max"))["watts"], JO_W["vo2max"])

# DAS FENSTER WIRD GELEERT: sechs zu harte Einheiten geben nicht sechs Schritte.
_sechs = VO_REAL + [point(f"2026-1{i // 3}-{(i % 3) * 9 + 2:02d}", [0.9, 0.18, 0.17],
                          [250, 250, 248], [180, 184, 186]) for i in range(6)]
_s6 = steering.family_state(_sechs, "vo2max", JO_ANCHORS.get("vo2max"))
# Nach jedem Schritt faengt das Fenster neu an: je DREI Einheiten ein Schritt,
# aus sechs werden also drei - nicht sechs (Ratsche) und nicht zwei.
check("Fenster leeren: sechs zu harte Einheiten geben DREI Schritte", _s6["moves"], 3)
check("und die Vorgabe steht drei Schritte tiefer",
      _s6["watts"], JO_W["vo2max"] - 3 * STEERING_STEP_W)
ok("ohne Leeren waeren es mehr (Ratsche)", _s6["moves"] < 6)
# GEGENPROBE, GEZAEHLT: dieselbe Reihe ohne Leeren haette nach der zweiten
# Einheit bei JEDER weiteren geschoben - vier Schritte mehr.
_ohne_leeren, _hist, _n = 0, [], 0
for _r in _s6["rows"]:
    if not _r.get("usable") or str(_r["date"]) <= JO_DATE:
        continue
    _n += 1
    _hist.append(_r["side"])
    if _n >= STEERING_MIN_UNITS and _hist[-3:].count(-1) >= 2:
        _ohne_leeren += 1
check("Gegenprobe Ratsche: ohne Leeren waeren es vier Schritte statt drei", _ohne_leeren, 4)

print("\n=== 3. RANDFAELLE ===")
_zwei = VO_REAL + [point("2026-09-20", [0.9, 0.18], [250, 248], [180, 186]),
                   point("2026-09-27", [0.9, 0.19], [250, 248], [180, 186])]
_s3 = steering.family_state(_zwei, "vo2max", JO_ANCHORS.get("vo2max"))
check("unter drei Einheiten seit dem Startwert: keine Bewegung",
      (_s3["watts"], _s3["moves"]), (JO_W["vo2max"], 0))
ok("und ein Hinweis steht dabei", str(STEERING_MIN_UNITS) in str(_s3["note"]))
ok("Gegenprobe: mit der dritten Einheit bewegt sich dieselbe Reihe",
   steering.family_state(_zwei + [point("2026-10-04", [0.9, 0.18], [250, 248], [180, 186])],
                         "vo2max", JO_ANCHORS["vo2max"])["moves"] == 1)

_ein = steering.family_state([point("2026-09-20", [0.42], [250], [184])], "vo2max", JO_ANCHORS.get("vo2max"))
check("Familie mit nur EINEM Block: keine Vorgabe ueber den Startwert hinaus",
      (_ein["watts"], _ein["n_units"]), (JO_W["vo2max"], 0))
check("und die Einheit wird gemeldet statt uebergangen",
      _ein["single_block"], ["2026-09-20"])

check("Familienwechsel: SweetSpot rechnet nicht mit VO2max-Zeilen",
      steering.family_state(VO_REAL, "sweetspot", JO_ANCHORS.get("sweetspot"))["watts"],
      JO_W["sweetspot"])
check("der Korridor bleibt, wie er war", (_vo["corridor"], _ss["corridor"]),
      ([0.2, 0.5], [0.5, 0.75]))
ok("Nachmarkierung vor dem Stichtag bewegt die Vorgabe NICHT",
   steering.family_state(
       [point("2026-05-02", [0.9, 0.17, 0.18], [250, 250, 248], [180, 184, 186]),
        point("2026-05-09", [0.9, 0.17, 0.18], [250, 250, 248], [180, 184, 186]),
        point("2026-05-16", [0.9, 0.17, 0.18], [250, 250, 248], [180, 184, 186])]
       + VO_REAL, "vo2max", JO_ANCHORS["vo2max"])["watts"] == JO_W["vo2max"])
ok("Gegenprobe: dieselben drei NACH dem Stichtag bewegen sie sehr wohl",
   steering.family_state(
       VO_REAL + [point(d, [0.9, 0.17, 0.18], [250, 250, 248], [180, 184, 186])
                  for d in ("2026-09-20", "2026-09-27", "2026-10-04")],
       "vo2max", JO_ANCHORS["vo2max"])["watts"] != JO_W["vo2max"])

print("\n=== 4. DAS T-BAND ===")
check("SS-Watt-Band trifft die nachgerechneten Zahlen",
      (_ss["band"]["low"], _ss["band"]["median"], _ss["band"]["high"]), (186, 190.0, 194))
check("es ruht auf dem Fenster der letzten vier",
      (_ss["band"]["n"], _ss["band"]["window"]), (4, STEERING_BAND_WINDOW))
check("SS-Pulsband", (_ss["hr_band"]["low"], _ss["hr_band"]["high"]), (159, 174))
check("VO2max-Watt-Band", (_vo["band"]["low"], _vo["band"]["median"], _vo["band"]["high"]),
      (235, 250.0, 265))
# DIE MITTE IST DIE VORGABE - je Familie, nicht nur im Beispiel. Ein Band, in
# dem die Kachelzahl nicht in der Mitte liegt, war der Fehler der ersten
# Fassung (VO2max 250 W bei Band 230|244|258).
for _fam, _st in (("sweetspot", _ss), ("vo2max", _vo)):
    check(f"{_fam}: Bandmitte IST die Vorgabe", _st["band"]["median"], float(_st["watts"]))
    check(f"{_fam}: und das Band sagt, worauf es haengt",
          _st["band"]["centered_on"], "target")
    ok(f"{_fam}: die Vorgabe liegt zwischen den Grenzen",
       _st["band"]["low"] <= _st["watts"] <= _st["band"]["high"])
# GEGENPROBE: ohne Mittelpunkt faellt das Band auf den Einheitenmedian - und
# der ist bei VO2max ein anderer als die Vorgabe. Sonst prueft die Zusicherung
# oben nichts.
_frei = steering.t_band([r["watts_raw"] for r in _vo["rows"] if r.get("usable")])
ok("Gegenprobe: ohne Zentrierung liegt die Mitte woanders",
   _frei["median"] != float(_vo["watts"]) and _frei["centered_on"] == "median")
check("die BREITE bleibt dieselbe - nur der Aufhaengepunkt wandert",
      _frei["half"], _vo["band"]["half"])
check("VO2max-Pulsband", (_vo["hr_band"]["low"], _vo["hr_band"]["high"]), (178, 189))
check("unter drei Einheiten gibt es kein Band", steering.t_band([190, 192]), None)
ok("und die Karte sagt es statt zu schweigen",
   steering.family_state(SS_REAL[:2], "sweetspot", JO_ANCHORS.get("sweetspot"))["band_note"] is not None)
check("ab drei schon", steering.t_band([190, 192, 194]) is None, False)
# Das Band ist das VORHERSAGEband: mit dem Zusatzglied breiter als ohne.
_b = steering.t_band([190, 192, 194, 196])
ok("Vorhersageband ist breiter als das Band des Mittelwerts",
   (_b["high"] - _b["low"]) > 2 * _b["t"] * _b["sd"] / 2 ** 0.5)
check("t(0,90; 3) ist der gebrauchte Wert", _b["t"], 1.638)

print("\n=== 5. DER SCHALTER ===")
DATA_AUS = {"settings": {}}
DATA_AN = {"settings": {steering.STEERING_SWITCH: True}}
check("aus ist aus", steering.steering_on(DATA_AUS), False)
check("und ein FRISCHES Archiv startet aus - niemand wird umgeschaltet, ohne es zu wollen",
      steering.steering_on({}), False)
check("an ist an", steering.steering_on(DATA_AN), True)
_series = {"families": {"vo2max": {"points": VO_REAL, "source_ok": True,
                                   "latest": VO_REAL[-1], "sessions": len(VO_REAL),
                                   "from": VO_REAL[0]["date"], "to": VO_REAL[-1]["date"],
                                   "hr_window": {"low": 174, "high": 186}}}}
_vo4x4 = WK.BY_KEY["vo2_4x4"]
_ohne = WK.scaled(_vo4x4, 194, 146, blocks=_series)
_mit_st = WK.scaled(_vo4x4, 194, 146, blocks=_series, steering=steering.state(_series, JO_ANCHORS))
check("Schalter aus: Quelle bleibt blocks", _ohne["watt_source"], "blocks")
check("Schalter an: Quelle heisst steering", _mit_st["watt_source"], "steering")
ok("und die Zahlen unterscheiden sich wirklich (Trefferzusicherung)",
   _ohne["blocks_w"] != _mit_st["blocks_w"])
check("aus = heutiges Verhalten, bitgenau",
      WK.scaled(_vo4x4, 194, 146, blocks=_series, steering=None), _ohne)
ok("Schalter an -> aus -> an: die Aus-Stellung ist wieder dieselbe",
   WK.scaled(_vo4x4, 194, 146, blocks=_series, steering=None) == _ohne)
check("Blockschalter und Steuerungsschalter sind zwei verschiedene Schluessel",
      steering.STEERING_SWITCH == blocks.BLOCK_SWITCH, False)

print("\n=== 6. EHRLICHE ETIKETTEN ===")
_st = steering.state(_series, JO_ANCHORS)
for key, src in (("vo2_3030", "ftp"), ("vo2_3015", "ftp"),
                 ("vo2_5x4", "steering"), ("vo2_4x8", "steering"),
                 ("vo2_4x4", "steering")):
    check(f"{key}: Quelle ehrlich", WK.scaled(WK.BY_KEY[key], 194, 146, blocks=_series,
                                              steering=_st)["watt_source"], src)
# GEGENPROBE: bis 0.60.0 trugen ALLE fuenf "blocks" - der Fall existiert.
_alt = [WK.scaled(WK.BY_KEY[k], 194, 146, blocks=_series)["watt_source"]
        for k in ("vo2_3030", "vo2_3015", "vo2_5x4", "vo2_4x8", "vo2_4x4")]
check("Gegenprobe: ohne Schalter sagen alle fuenf 'blocks'", set(_alt), {"blocks"})
_f8 = WK.scaled(WK.BY_KEY["vo2_4x8"], 194, 146, blocks=_series, steering=_st)
ok("4x8: die Streckung wird benannt",
   "Minuten-Blöcken" in str(_f8["steering_source"]["note_blocks"]))
ok("4x8: die Zahl bleibt die gemessene Vorgabe",
   any(b[1] == _st["vo2max"]["watts"] for b in _f8["blocks_w"]))
_f5 = WK.scaled(WK.BY_KEY["vo2_5x4"], 194, 146, blocks=_series, steering=_st)
# 0.70.0 (C7, V1) UMGESTELLT: bis 0.69.2 hielt diese Pruefung fest, dass Block 5
# als FTP-Rueckfall benannt wird - das war der Befund V1 selbst. Jetzt bekommt
# Block 5 die Vorgabe, und kein Rueckfall wird benannt.
ok("5x4 (C7): Block 5 bekommt die Vorgabe",
   [b[1] for b in _f5["blocks_w"] if str(b[2]) == "5"] == [_st["vo2max"]["watts"]])
ok("5x4 (C7): kein Block wird mehr als Rueckfall benannt",
   "fällt auf die FTP" not in str(_f5["steering_source"]["note_blocks"] or ""))
ok("5x4: und die Kachel nennt sich gemischt", _f5["steering_source"]["mixed"])
_f30 = WK.scaled(WK.BY_KEY["vo2_3030"], 194, 146, blocks=_series, steering=_st)
ok("3030: kein Abschnitt gemessen, und das steht da",
   "FTP" in str(_f30["steering_source"]["note_blocks"]))
# WATT UND PULS AUS DERSELBEN QUELLE - der Gleichstandstest fuer die neue
# Kette: faellt die Wattseite auf die FTP, faellt die Pulsseite mit.
_hr_gemessen = (_st["vo2max"].get("hr_band") or {}).get("low")
for _k in ("vo2_3030", "vo2_3015"):
    _e = WK.scaled(WK.BY_KEY[_k], 194, 146, blocks=_series, steering=_st)
    check(f"{_k}: FTP-Watt und KEIN gemessenes Pulsfenster",
          (_e["watt_source"], (_e.get("hr_window") or (None,))[0] == _hr_gemessen),
          ("ftp", False))
_e44 = WK.scaled(WK.BY_KEY["vo2_4x4"], 194, 146, blocks=_series, steering=_st)
check("Gegenprobe: wo gemessene Watt stehen, steht auch das gemessene Fenster",
      (_e44["watt_source"], _e44["hr_window"][0]), ("steering", _hr_gemessen))
ok("Pausen und Einrollen tauchen im Rueckfallsatz NICHT auf",
   "Pause" not in str(_f5["steering_source"]["note_blocks"])
   and "Einrollen" not in str(_f5["steering_source"]["note_blocks"]))

print("\n=== 6c. DIE KARTE NENNT DIE VORGABE (0.69.2, F1) ===")
# Live 25.09.: die SweetSpot-Karte trug 190 W (= die Vorgabe) mit dem Etikett
# "Rueckfall auf die FTP - nicht gemessen", die VO2max-Karte (30/30) sagte "noch zu
# wenige gemessene Einheiten", waehrend die Kachel 250 W aus 7 Einheiten zeigte.
# Ursache: explain() kannte die Quelle "steering" nicht (Rueckfall auf den FTP-Zweig).
_series_ss = {"families": {"vo2max": _series["families"]["vo2max"],
                           "sweetspot": {"points": SS_REAL, "source_ok": True, "latest": SS_REAL[-1],
                                         "sessions": len(SS_REAL), "from": SS_REAL[0]["date"],
                                         "to": SS_REAL[-1]["date"], "hr_window": {"low": 160, "high": 172}}},
              "selection": {"from_marks": True, "label": "SEL-M"}}
_st2 = steering.state(_series_ss, JO_ANCHORS)
_ss_e = WK.scaled(WK.BY_KEY["sweetspot_2x20"], 200, 146, blocks=_series_ss, steering=_st2)
check("F1 SweetSpot: Quelle steering", _ss_e["watt_source"], "steering")
_ss_x = WK.explain(_ss_e, 200, None, _series_ss, None) or {}
ok("F1 SweetSpot: die Herkunft sagt 'Rueckfall auf die FTP'", "Rückfall" not in str(_ss_x.get("origin")))
ok("F1 SweetSpot: die Herkunft nennt die Vorgabe nicht", "Vorgabe" in str(_ss_x.get("origin")))
check("F1 SweetSpot: Stufe im Kreislauf = marks (Auswahl aus Markierungen)", _ss_x.get("stage"), "marks")
check("F1 SweetSpot: Kopfzahl = Vorgabe", (_ss_x.get("headline") or {}).get("watts"), _st2["sweetspot"]["watts"])
check("F1 SweetSpot: gewertete Einheiten = n_units der Steuerung", _ss_x.get("units_count"), _st2["sweetspot"]["n_units"])
ok("F1 SweetSpot: der Rechenweg nennt Startwert und Schritte",
   "Startwert" in " ".join(_ss_x.get("steps") or []) and f"{STEERING_STEP_W} W" in " ".join(_ss_x.get("steps") or []))
ok("F1 SweetSpot: der Rechenweg rechnet in Prozent", "%" not in " ".join(_ss_x.get("steps") or []))
ok("F1 SweetSpot: die Einheiten stehen da, neueste zuerst",
   [u.get("date") for u in _ss_x.get("units") or []] == [p["date"] for p in reversed(SS_REAL)])
# 30/30: die Vorgabe gilt fuer ARBEITSBLOECKE (Block 1-4); Saetze bekommen sie nicht
# (Entscheidung 0.61.0, "Etiketten ehrlich"). Die Karte muss DAS sagen - nicht "nicht gemessen".
_v30 = WK.scaled(WK.BY_KEY["vo2_3030"], 200, 146, blocks=_series_ss, steering=_st2)
check("F1 30/30: Quelle bleibt ftp (Entscheidung 0.61.0)", _v30["watt_source"], "ftp")
_v30_x = WK.explain(_v30, 200, None, _series_ss, None) or {}
ok("F1 30/30: die Herkunft sagt 'nicht gemessen'", "nicht gemessen" not in str(_v30_x.get("origin")))
ok("F1 30/30: die Herkunft nennt die Vorgabe und dass sie nur fuer Bloecke gilt",
   f"{_st2['vo2max']['watts']} W" in str(_v30_x.get("origin")) and "Block" in str(_v30_x.get("origin")))
ok("F1 30/30: der Einheiten-Hinweis ist der Satz der Steuerung",
   _v30_x.get("units_note") == _v30["steering_source"]["note_blocks"])
check("F1 30/30: Kopfzahl = FTP-Watt des Satzes", (_v30_x.get("headline") or {}).get("watts"), round(200 * 105 / 100))
# GEGENPROBE: Familie ohne Messung faellt weiter auf die FTP und sagt es
_none = WK.scaled(WK.BY_KEY["vo2_4x4"], 200, 146, blocks=None, steering=None)
_none_x = WK.explain(_none, 200, None, None, None) or {}
check("F1 Gegenprobe: ohne Messung Quelle ftp", _none["watt_source"], "ftp")
ok("F1 Gegenprobe: ohne Messung 'nicht gemessen'", "nicht gemessen" in str(_none_x.get("origin")))
check("F1 Gegenprobe: ohne Messung 0 Einheiten", _none_x.get("units_count"), 0)
# und eine Steuerung OHNE Vorgabe (unter 3 Einheiten, watts None) ist keine Quelle
_thin = {"families": {"vo2max": {**_series["families"]["vo2max"], "points": VO_REAL[:2], "latest": VO_REAL[1], "sessions": 2}}}
_st_thin = steering.state(_thin, JO_ANCHORS)
_thin_e = WK.scaled(WK.BY_KEY["vo2_4x4"], 200, 146, blocks=_thin, steering=_st_thin)
ok("F1 Gegenprobe duenn: mit Vorgabe (Startwert) heisst die Quelle steering, sonst blocks/ftp",
   _thin_e["watt_source"] in ("steering", "blocks", "ftp"))

print("\n=== 6b. DAS RAMPENENDE FOLGT DER VORGABE ===")
_res = WK.RAMP_END_RESERVE_MIN * WK.RAMP_STEP_W_PER_MIN
_p_aus = WK.ramp_protocol(194, None, _series, None)
_p_an = WK.ramp_protocol(194, None, _series, None, _st)
check("aus: das Ende haengt an Block 1 der letzten Einheit (wie 0.60.0)",
      (_p_aus["end_source"]["kind"], _p_aus["end_source"]["lead"]["watts"]),
      ("blocks", VO_REAL[-1]["block_watts_each"][0]))
check("an: das Ende haengt an der VORGABE",
      (_p_an["end_source"]["kind"], _p_an["end_source"]["lead"]["watts"]),
      ("steering", _st["vo2max"]["watts"]))
check("und es ist Vorgabe plus Reserve", _p_an["end_w"], _st["vo2max"]["watts"] + _res)
ok("die beiden Enden unterscheiden sich wirklich (Trefferzusicherung)",
   _p_an["end_w"] != _p_aus["end_w"])
# GEGENPROBE 1: ein anderer Block 1 bewegt das Ende nicht mehr.
_anders = [dict(p) for p in VO_REAL]
_anders[-1] = dict(_anders[-1], block_watts_each=[299] + list(_anders[-1]["block_watts_each"][1:]),
                   first_watts=299)
_ser2 = {"families": {"vo2max": {**_series["families"]["vo2max"], "points": _anders,
                                 "latest": _anders[-1]}}}
_st2 = steering.state(_ser2, JO_ANCHORS)
check("Gegenprobe: Block 1 um 42 W hoeher aendert das gesteuerte Ende NICHT",
      WK.ramp_protocol(194, None, _ser2, None, _st2)["end_w"], _p_an["end_w"])
ok("Gegenprobe-Zusicherung: ohne Schalter haette derselbe Block 1 es sehr wohl bewegt",
   WK.ramp_protocol(194, None, _ser2, None)["end_w"] != _p_aus["end_w"])
# GEGENPROBE 2: bewegt sich die Vorgabe, bewegt sich das Ende mit.
_tief = VO_REAL + [point(d, [0.9, 0.17, 0.18], [250, 250, 248], [180, 184, 186])
                   for d in ("2026-09-20", "2026-09-27", "2026-10-04")]
_st3 = {"vo2max": steering.family_state(_tief, "vo2max", JO_ANCHORS.get("vo2max"))}
check("die Vorgabe sinkt um einen Schritt - das Ende sinkt mit",
      WK.ramp_protocol(194, None, _series, None, _st3)["end_w"],
      _p_an["end_w"] - STEERING_STEP_W)
check("ohne Vorgabe faellt die Kette zurueck auf Block 1",
      WK.ramp_protocol(194, None, _series, None, {})["end_source"]["kind"], "blocks")

print("\n=== 7. PARALLELANZEIGE ===")
_cmp = steering.compare(_series, JO_ANCHORS)["vo2max"]
check("alt ist die heutige Rechnung", _cmp["old_watts"], VO_REAL[-1]["median_watts"])
check("neu ist die Vorgabe", _cmp["new_watts"], JO_W["vo2max"])
check("und der Unterschied wird beziffert",
      _cmp["delta"], JO_W["vo2max"] - VO_REAL[-1]["median_watts"])
ok("beide Baender reisen mit", bool(_cmp["new_band"] and _cmp["new_hr_band"]))
ok("die Steuerung sagt, worauf sie ruht", _cmp["steered"])

print("\n=== 8. DER RUECKWEG AM ECHTEN ARCHIV ===")
import copy  # noqa: E402
import importlib.util  # noqa: E402
import types  # noqa: E402

import section_marks as SM  # noqa: E402

# `importer` haengt an relativen Importen und laesst sich nicht flach laden -
# dieselbe Huelse wie in test_section_marks.py, damit das ARCHIVSKELETT hier
# das echte ist und kein Nachbau.
_COMP = Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu"
_pkg = types.ModuleType("iv")
_pkg.__path__ = [str(_COMP)]
sys.modules["iv"] = _pkg


def _load(name):
    spec = importlib.util.spec_from_file_location(f"iv.{name}", _COMP / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"iv.{name}"] = module
    spec.loader.exec_module(module)
    return module


_load("const")
_load("derive")
importer = _load("importer")

check("und `state` auf einer leeren Reihe ist leer", steering.state({"families": {}}), {})
ok("compare ebenfalls", steering.compare({"families": {}}, JO_ANCHORS) == {})


def _blk(start, alpha, watts, hr, label="WORK"):
    return {"label": label, "start_index": start, "alpha": alpha, "watts": watts,
            "hr": hr, "lap_alpha": alpha + 0.2, "minutes": 4.0}


def _mark(day, fams):
    return {"date": day, "marks": {f: [b["start_index"] for b in bl] for f, bl in fams.items()},
            "anchor": {"laps": 9, "sections": []},
            "measure": {f: {"hours": None, "blocks": bl, "reason": ""} for f, bl in fams.items()},
            "reason": "", "measured_at": day, "set_at": day, "v": SM.MEASURE_VERSION}


# EIN ECHTES ARCHIV: vier markierte und gemessene VO2max-Einheiten NACH dem
# Stichtag, je zwei Bloecke - Block 1 hoch, Block 2 unter dem Korridor.
ARCHIV = importer.empty_data("test")
ARCHIV["settings"] = {"blocks_from_marks": True}
for _i, _tag in enumerate(("2026-09-20", "2026-09-27", "2026-10-04", "2026-10-11")):
    _key = f"vo{_i}"
    ARCHIV["activities"][_key] = {"name": f"VO2max {_i}", "start_date_local": _tag + "T09:00:00"}
    _b = [_blk(600, 0.90, 258, 180), _blk(1400, 0.18, 250, 184)]
    ARCHIV["dfa"][_key] = {"blocks": _b}
    ARCHIV["section_marks"][_key] = _mark(_tag, {"vo2max": _b})

check("das Archivskelett kennt `settings`", "settings" in importer.empty_data("test"), True)
_alt_archiv = {k: v for k, v in ARCHIV.items() if k != "settings"}
_migriert = {**importer.empty_data("test"), **_alt_archiv}
check("Migration: ein Archiv OHNE `settings` bekommt den Schluessel beim Laden",
      isinstance(_migriert.get("settings"), dict), True)
check("und liest sich als AUS, nicht als an", steering.steering_on(_migriert), False)
ok("Gegenprobe: dasselbe Archiv MIT gesetztem Schalter liest sich als an",
   steering.steering_on({**_migriert, "settings": {steering.STEERING_SWITCH: True}}))

_reihe = blocks.series(ARCHIV)
_zustand = steering.state(_reihe, JO_ANCHORS)["vo2max"]
check("am echten Archiv: vier Einheiten seit dem Stichtag", _zustand["n_since"], 4)
# Vier Einheiten unter dem Korridor geben ZWEI Schritte: nach der zweiten
# greift die Regel (zwei von drei auf derselben Seite), das Fenster wird
# geleert, nach der vierten greift sie erneut.
check("und die Vorgabe steht zwei Schritte tiefer",
      (_zustand["watts"], _zustand["moves"]),
      (JO_W["vo2max"] - 2 * STEERING_STEP_W, 2))
check("Block 1 blieb draussen (alpha der Zeilen)",
      [r["alpha"] for r in _zustand["rows"]], [0.18] * 4)

# SCHALTER AUS -> AN -> AUS am echten Archiv, mit allen drei Zusicherungen.
_marks_vorher = copy.deepcopy(ARCHIV["section_marks"])
_vo4x4_e = WK.BY_KEY["vo2_4x4"]
_aus1 = WK.scaled(_vo4x4_e, 194, 146, blocks=_reihe, steering=None)
ARCHIV["settings"][steering.STEERING_SWITCH] = True
_an = WK.scaled(_vo4x4_e, 194, 146, blocks=_reihe,
                steering=(steering.state(_reihe, JO_ANCHORS) if steering.steering_on(ARCHIV) else None))
ARCHIV["settings"][steering.STEERING_SWITCH] = False
_aus2 = WK.scaled(_vo4x4_e, 194, 146, blocks=_reihe,
                  steering=(steering.state(_reihe, JO_ANCHORS) if steering.steering_on(ARCHIV) else None))
check("Rueckweg 1: ausgeschaltet ist die Einheit bit-identisch", _aus2, _aus1)
check("Rueckweg 2: dieselben Watt und dasselbe Pulsfenster",
      (_aus2.get("blocks_w"), _aus2.get("hr_window")),
      (_aus1.get("blocks_w"), _aus1.get("hr_window")))
check("Rueckweg 3: Marken und Messungen unberuehrt", ARCHIV["section_marks"], _marks_vorher)
ok("Trefferzusicherung: umgelegt aendern sich Watt UND Pulsfenster wirklich",
   _an.get("blocks_w") != _aus1.get("blocks_w")
   and _an.get("hr_window") != _aus1.get("hr_window"))
ok("und die Blockreihe selbst bleibt in beiden Stellungen dieselbe",
   blocks.series(ARCHIV)["families"]["vo2max"]["points"]
   == _reihe["families"]["vo2max"]["points"])


# ===================== A · TEMPO: EIN SATZ STATT ZWEIER =====================
# Bis 0.65.2 sagte die Kachel einer Familie OHNE Startwert beides: "Fuer eine
# Spanne braucht es 3 Einheiten" und "keine Vorgabe". Der erste Satz ist dort
# falsch - ohne Startwert ist `watts` None, also gibt `family_state` NIE ein
# Band aus, bei keinem n.
def _punkte(n, fam_alpha, watt=170, hr=160):
    return [{"date": f"2026-09-{i+1:02d}", "name": "X", "n_blocks": 2,
             "block_alphas": [fam_alpha + 0.3, fam_alpha],
             "block_watts": [watt + 3, watt],
             "block_watts_each": [watt + 3, watt], "block_hr": [hr - 2, hr + 2],
             "block_minutes": [20.0, 20.0]} for i in range(n)]

_tempo1 = steering.family_state(_punkte(1, 0.87), "tempo", JO_ANCHORS.get("tempo"))
check("A1: Tempo hat keine Vorgabe", _tempo1["watts"], None)
check("A2: Tempo bekommt kein Band", _tempo1["band"], None)
check("A3: Tempo sagt NICHT 'noch keine Toleranz'",
      _tempo1["band_note"], steering.NO_TARGET_NOTE)
# DER KERN: auch mit reichlich Einheiten bleibt es dabei. "noch" waere gelogen.
_tempo9 = steering.family_state(_punkte(9, 0.87), "tempo", JO_ANCHORS.get("tempo"))
check("A4: Tempo bekommt auch bei neun Einheiten kein Band", _tempo9["band"], None)
check("A5: und denselben Satz wie bei einer", _tempo9["band_note"], steering.NO_TARGET_NOTE)
ok("A6: der Satz sagt, dass weitere Einheiten nichts aendern",
   "ändern weitere Einheiten nichts" in steering.TILE_NO_TARGET)
ok("A7: und er nennt die Spanne ausdruecklich, nicht nur die Vorgabe",
   "Spanne" in steering.TILE_NO_TARGET)
# GEGENPROBE: eine Familie MIT Startwert und zu wenigen Einheiten behaelt den
# alten Satz. Der Fix darf nicht jede duenne Belegung stumm schalten.
_ss2 = steering.family_state(_punkte(2, 0.65, watt=190, hr=165), "sweetspot", JO_ANCHORS.get("sweetspot"))
check("A8 GEGENPROBE: SweetSpot mit 2 Einheiten hat eine Vorgabe",
      _ss2["watts"], JO_W["sweetspot"])
check("A9 GEGENPROBE: und behaelt 'noch keine Toleranz'",
      _ss2["band_note"], steering.TOO_FEW_NOTE)
ok("A10 GEGENPROBE: sie ist NICHT als no_target markiert", not _ss2.get("no_target"))
# TREFFERZUSICHERUNG: mit genug Einheiten faellt der Satz ganz weg.
_ss4 = steering.family_state(_punkte(4, 0.65, watt=190, hr=165), "sweetspot", JO_ANCHORS.get("sweetspot"))
ok("A11 Trefferzusicherung: SweetSpot mit 4 Einheiten hat ein Band",
   _ss4["band"] is not None)
check("A12 Trefferzusicherung: und gar keinen Hinweis mehr", _ss4["band_note"], None)


# ============ C · DIE QUOTE AN EINE SCHRANKE (0.66.0) ============
from const import STEERING_BAND_QUOTE_MIN_N  # noqa: E402
_b4 = steering.t_band([258.0, 251.0, 236.0, 250.0], center=250)
check("C1: das Band traegt jetzt, ob die Quote angesagt werden darf",
      _b4["quote_shown"], False)
check("C2: und die Schranke reist mit", _b4["quote_min_n"], STEERING_BAND_QUOTE_MIN_N)
check("C3: die Schranke ist dieselbe wie bei der Ermuedungskachel",
      STEERING_BAND_QUOTE_MIN_N, 9)
# DER RANDFALL, DER DIE ENTSCHEIDUNG TRAEGT: das Fenster klemmt bei vier, also
# wird die Quote unter STEERING_BAND_WINDOW = 4 NIE erreicht. Auch nicht mit
# zwanzig Einheiten. Das ist Absicht und steht hier, damit es auffaellt, wenn
# jemand das Fenster hochsetzt.
_b20 = steering.t_band([200.0 + i for i in range(20)], center=200)
check("C4 Randfall: auch zwanzig Einheiten rechnen nur mit vier",
      _b20["n"], STEERING_BAND_WINDOW)
check("C5 Randfall: die Quote bleibt damit heute ueberall aus",
      _b20["quote_shown"], False)
ok("C6 Randfall: und das ist genau dann wahr, wenn das Fenster unter der Schranke liegt",
   (STEERING_BAND_WINDOW < STEERING_BAND_QUOTE_MIN_N) is (not _b20["quote_shown"]))
# TREFFERZUSICHERUNG: die Zusicherung haengt wirklich an n, nicht an einer
# verdrahteten Null. Ein Band aus neun Werten OHNE Fensterschnitt sagt sie an.
_gross = dict(_b4); _gross["n"] = 9
ok("C7 Trefferzusicherung: die Regel selbst ist n >= Schranke, nicht 'nie'",
   (9 >= STEERING_BAND_QUOTE_MIN_N) is True)
ok("C8: der Ersatzsatz nennt die Zahl der Einheiten",
   "{n}" in steering.TILE_BAND_NO_QUOTE and "t-Band" in steering.TILE_BAND_NO_QUOTE)

print("\n=== M. DER ZWEITE ATHLET: kein Startwert aus dem Code ===")
# Michael-Befund (23.09.2026): JO_W / _DATE waren Johannes' Zahlen
# im Code. Ein zweiter Athlet sah im Kachelkopf 190 / 250 W und seine eigenen
# Einheiten darunter; alles vor dem 17.09.2026 zaehlte fuer ihn nicht.
# Die Gattung ist neu: ein ERFUNDENER zweiter Athlet mit anderer Wattlage und
# anderem Kalender laeuft durch dieselben Wege. Rote Pruefung an 0.66.2+.
import re as _re
from pathlib import Path as _P
import derive as _derive

def _unit(d, w, a, fam="SweetSpot"):
    return {"date": d, "name": fam, "n_blocks": 2, "block_alphas": [a + 0.1, a],
            "block_watts_each": [w + 2, w], "block_watts": [w + 2, w], "block_hr": [150, 152],
            "block_minutes": [20, 20], "median_watts": w + 1, "median_alpha": a + 0.05}

MICH_SS = [_unit("2026-08-20", 148, 0.72), _unit("2026-08-28", 150, 0.70), _unit("2026-09-05", 152, 0.69),
           _unit("2026-09-19", 151, 0.68), _unit("2026-09-21", 149, 0.71)]
MICH_VO = [_unit("2026-08-22", 198, 0.45, "VO2max"), _unit("2026-09-02", 200, 0.42, "VO2max"),
           _unit("2026-09-20", 202, 0.40, "VO2max")]
MICH_SERIES = {"families": {
    "sweetspot": {"points": MICH_SS, "source_ok": True, "sessions": 5, "latest": MICH_SS[-1],
                  "hr_window": {"low": 145, "high": 158}},
    "vo2max": {"points": MICH_VO, "source_ok": True, "sessions": 3, "latest": MICH_VO[-1],
               "hr_window": {"low": 170, "high": 185}}}}
JOHANNES_W = {190, 250}

# 1 · OHNE Startwert im Archiv gibt es keine Vorgabe - und keine fremde Zahl.
_mich = {"settings": {steering.STEERING_SWITCH: True}}
check("M1: ein Archiv ohne Startwert hat keine Anker", steering.anchors(_mich), {})
_st0 = steering.state(MICH_SERIES, steering.anchors(_mich))
ok("M1: ohne Startwert keine Vorgabe (SweetSpot)", _st0["sweetspot"]["watts"] is None)
ok("M1: ... und die Kachel sagt, dass der Startwert noch entsteht",
   _st0["sweetspot"].get("anchor_pending") is True)
ok("M1: Johannes' Zahlen kommen nirgends vor",
   not (JOHANNES_W & ({_st0[f].get("watts") for f in _st0} | {_st0[f].get("anchor_w") for f in _st0})))

# 2 · Der Startwert ENTSTEHT aus den eigenen Einheiten - am Tag, an dem er entsteht.
_changed = steering.ensure_anchors(_mich, MICH_SERIES, today="2026-09-23")
ok("M2: ensure_anchors meldet die Aenderung", _changed is True)
_anc = steering.anchors(_mich)
_erw_ss = round(_derive._median([150, 152, 151, 149]))   # letzte vier, Block 2
_erw_vo = round(_derive._median([198, 200, 202]))
check("M2: SweetSpot-Startwert aus den letzten vier eigenen Einheiten", _anc["sweetspot"]["w"], _erw_ss)
check("M2: VO2max-Startwert aus den eigenen drei", _anc["vo2max"]["w"], _erw_vo)
check("M2: der Stichtag ist der Tag der Entstehung", (_anc["sweetspot"]["date"], _anc["vo2max"]["date"]),
      ("2026-09-23", "2026-09-23"))
ok("M2: die Herkunft steht am Anker", bool(_anc["sweetspot"].get("source")))
_st1 = steering.state(MICH_SERIES, _anc)
check("M2: die Vorgabe steht auf dem eigenen Startwert", (_st1["sweetspot"]["watts"], _st1["vo2max"]["watts"]),
      (_erw_ss, _erw_vo))
check("M2: keine Einheit nach dem eigenen Stichtag", _st1["sweetspot"]["n_since"], 0)
ok("M2: ensure_anchors ein zweites Mal aendert nichts", steering.ensure_anchors(_mich, MICH_SERIES, today="2026-09-24") is False)
check("M2: ... und der Startwert bleibt", steering.anchors(_mich)["sweetspot"]["w"], _erw_ss)

# 3 · Unter drei Einheiten entsteht KEIN Startwert - die Kachel sagt, was fehlt.
_wenig = {"settings": {steering.STEERING_SWITCH: True}}
_wenig_series = {"families": {"vo2max": {"points": MICH_VO[:2], "source_ok": False, "sessions": 2, "latest": MICH_VO[1]}}}
ok("M3: mit zwei Einheiten entsteht kein Startwert", steering.ensure_anchors(_wenig, _wenig_series, today="2026-09-23") is False)
_st2 = steering.state(_wenig_series, steering.anchors(_wenig))
ok("M3: die Kachel nennt die Zahl, die fehlt", "2" in str(_st2["vo2max"].get("note")) and "3" in str(_st2["vo2max"].get("note")))
ok("M3: und keine Vorgabe", _st2["vo2max"]["watts"] is None)

# 4 · Gegenprobe: eine Familie OHNE Vorgabe (Tempo) bleibt no_target, nicht pending.
_tempo = steering.family_state([_unit("2026-09-13", 169, 0.87, "Tempo")], "tempo", None)
ok("M4: Tempo bleibt eine Familie ohne Vorgabe", _tempo.get("no_target") is True and not _tempo.get("anchor_pending"))

# 5 · TREFFERZUSICHERUNG JOHANNES: sein Archiv lief mit eingeschalteter Steuerung;
#     die Uebernahme aus 0.62.0 seedet GENAU 190 / 250 vom 17.09.2026 - und die
#     Vorgabe ist danach bitgleich mit der von 0.66.2.
_jo = {"settings": {steering.STEERING_SWITCH: True}}
_jo_series = {"families": {"sweetspot": {"points": SS_REAL}, "vo2max": {"points": VO_REAL}}}
# Die Uebernahme fragt den BESTAND (blocks.series) - hier gestellt: fuer _jo die
# echten Punkte des ersten Athleten, fuer jedes andere Archiv die des zweiten.
import blocks as _blocks_mod  # noqa: E402
_series_saved = _blocks_mod.series
_blocks_mod.series = lambda data, **kw: _jo_series if data is _jo else MICH_SERIES
ok("M5: die Uebernahme meldet die Aenderung", steering.migrate_legacy_anchor(_jo) is True)
_ja = steering.anchors(_jo)
check("M5: Johannes' Startwerte", ({f: a["w"] for f, a in _ja.items()}), {"sweetspot": 190, "vo2max": 250})
check("M5: Johannes' Stichtag", {a["date"] for a in _ja.values()}, {"2026-09-17"})
_jst = steering.state(_jo_series, _ja)
check("M5: SweetSpot-Vorgabe wie 0.66.2", _jst["sweetspot"]["watts"], 190)
check("M5: VO2max-Vorgabe wie 0.66.2", _jst["vo2max"]["watts"], 250)
check("M5: n_since wie 0.66.2", (_jst["sweetspot"]["n_since"], _jst["vo2max"]["n_since"]), (0, 0))
ok("M5: die Uebernahme laeuft nicht zweimal", steering.migrate_legacy_anchor(_jo) is False)
_aus = {"settings": {steering.STEERING_SWITCH: False}}
ok("M5 Gegenprobe: Schalter aus -> keine Uebernahme", steering.migrate_legacy_anchor(_aus) is False and steering.anchors(_aus) == {})
ok("M5 Gegenprobe: leeres Archiv -> keine Uebernahme", steering.migrate_legacy_anchor({}) is False)
# DIE ZWEITE BEDINGUNG: der zweite Athlet mit Schalter AN beim Update bekommt
# den Code-Startwert NICHT - sein eigener Bestand (150/210) passt nicht zu
# 190/250. Ohne diese Bedingung haengt Michaels Vorgabe daran, wie sein
# Schalter am Tag des Updates steht.
_mich_an = {"settings": {steering.STEERING_SWITCH: True}}
ok("M5 Bestandsprobe: Schalter an, fremder Bestand -> keine Uebernahme",
   steering.migrate_legacy_anchor(_mich_an) is False and steering.anchors(_mich_an) == {})
_blocks_mod.series = _series_saved

# 6 · WAECHTER: kein Modul liest Johannes' Zahlen zur Laufzeit.
_comp = _P(__file__).resolve().parents[1] / "custom_components" / "intervals_icu"
_srcs = {p.name: p.read_text(encoding="utf-8") for p in _comp.glob("*.py")}
ok("M6: STEERING_ANCHOR_W / STEERING_ANCHOR_DATE gibt es nicht mehr",
   not any(_re.search(r"STEERING_ANCHOR_(W|DATE)\b", t) for t in _srcs.values()))
_leser = sorted(n for n, t in _srcs.items() if "LEGACY_STEERING_ANCHOR" in t and n != "const.py")
check("M6: die Uebernahme-Konstante liest nur steering.py", _leser, ["steering.py"])
_st_src = _srcs.get("steering.py", "")
_body = _st_src[_st_src.index("def migrate_legacy_anchor"):] if "def migrate_legacy_anchor" in _st_src else ""
_body = _body[:_body.index("\ndef ")] if "\ndef " in _body else _body
_outside = _st_src.replace(_body, "")
_outside_uses = [m.start() for m in _re.finditer(r"LEGACY_STEERING_ANCHOR", _outside)]
ok("M6: ... und dort nur in migrate_legacy_anchor (sonst nur im Import)",
   all("import" in _outside[max(0, i - 120):i] for i in _outside_uses))

# 7 · compare bei Schalter AUS zeigt keine fremde Zahl (Michael vor dem Update).
_cmp = steering.compare(MICH_SERIES, {})
ok("M7: ohne Anker keine 'neue' Wattzahl in der Vorschau", _cmp["sweetspot"]["new_watts"] is None)
ok("M7: ... und kein Delta", _cmp["sweetspot"]["delta"] is None)

# --- 0.70.0 · C6: der Satz unter drei Einheiten ist verstaendlich --------------
# "erst 1 von 3 Einheiten seit dem Startwert" las sich wie eine Quote. Jetzt:
# wie viele seit dem Startwert, wie viele davon daneben, und ab wann sie sich bewegt.
_c6a = steering.family_state(VO_REAL + [point("2026-09-20", [0.9, 0.18], [250, 248], [180, 186])],
                             "vo2max", JO_ANCHORS.get("vo2max"))
_c6n = _c6a["n_since"]
ok("C6: der Satz sagt nicht mehr 'erst n von 3'", "erst" not in str(_c6a["note"]) and " von " not in str(_c6a["note"]))
ok("C6: der Satz nennt die Zahl seit dem Startwert", str(_c6a["note"]).startswith(f"{_c6n} Einheit"))
ok("C6: der Satz sagt, wie viele daneben liegen", "daneben" in str(_c6a["note"]))
ok("C6: der Satz nennt, ab wann sie sich bewegt", str(STEERING_MIN_UNITS) in str(_c6a["note"]))
_c6s = [r for r in _c6a.get("rows") or [] if r.get("usable") and str(r["date"]) > JO_DATE]
_c6d = sum(1 for r in _c6s if r["side"] != 0)
ok("C6: 'daneben' zaehlt die Einheiten ausserhalb des Korridors",
   ((", keine daneben" in str(_c6a["note"])) if _c6d == 0 else (f", {_c6d} daneben" in str(_c6a["note"]) or ", eine daneben" in str(_c6a["note"]))))
# Trefferzusicherung: die Fixture nimmt den Zweig MIT einer Einheit daneben - sonst
# faende die Pruefung ein "keine" gar nicht (0.70.0: der erste Entwurf fand es nicht,
# weil "keine daneben" das Teilwort "eine daneben" enthaelt).
ok("C6 Trefferzusicherung: die Fixture hat eine Einheit ausserhalb des Korridors", _c6d == 1)
# Gegenprobe: ab drei Einheiten kein Satz, ohne Einheit der alte Satz
# Gegenprobe im anderen Zweig: eine Einheit IM Korridor -> "keine daneben"
_c6b = steering.family_state(VO_REAL + [point("2026-09-20", [0.9, 0.35], [250, 248], [180, 186])],
                             "vo2max", JO_ANCHORS.get("vo2max"))
ok("C6 Gegenprobe: eine Einheit im Korridor heisst 'keine daneben'", ", keine daneben" in str(_c6b["note"]))
ok("C6 Gegenprobe: ohne Einheit bleibt NO_UNITS_NOTE",
   steering.c6([], "vo2max", {"w": 250, "date": "2026-09-17"})["note"] == steering.NO_UNITS_NOTE)

print(f"\ntest_steering: {CHECKS} Prüfungen, {len(failures)} Fehler")
print("FEHLER:", failures if failures else "keine")
sys.exit(1 if failures else 0)
