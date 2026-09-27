"""Die Vorgabe je Blockfamilie - gerechnet, nicht gespeichert.

0.75.0 (W2): DIE VORGABE FOLGT DEM GEFAHRENEN. Sie ist der mittlere Wert
(Median) der gefahrenen Watt der letzten STEERING_ANCHOR_UNITS nutzbaren
Einheiten dieser Familie, jeweils ab Block 2 - dieselbe Rechnung, mit der
bis 0.74.9 nur der Startwert entstand (`derive_anchor`). Es gibt EINEN
Erzeuger (`rolling_target`); Startwert und Vorgabe rufen ihn beide.

Bis 0.74.9 stand die Vorgabe auf einem festen Startwert und bewegte sich
in 5-W-Schritten nur, wenn alpha mehrerer Einheiten neben dem Korridor lag
(C6). Am Livebestand blieb sie 250 W, waehrend die Einheiten laengst bei
243 W lagen: die Vorgabe folgte der Form nicht (PROJEKTSTAND §10). Die
alpha-Schritte sind entfallen; alpha, Seite und Korridor bleiben Anzeige.

Der gespeicherte Startwert (settings.steering_anchor) bleibt im Archiv und
wird weiter angelegt (`ensure_anchors`, `migrate_legacy_anchor`); fuer die
Vorgabe hat er keinen Zweck mehr.

Dieses Modul ist HA-frei und rechnet ausschliesslich auf dem Ergebnis von
`blocks.series()`. Damit folgt es dem Blockschalter, ohne ihn zu kennen.
"""

from __future__ import annotations

from typing import Any

try:  # inside the package (Home Assistant)
    from . import derive
    from .const import (
        BLOCK_CORRIDORS,
        LEGACY_ANCHOR_TOLERANCE,
        LEGACY_STEERING_ANCHOR,
        STEERING_ANCHOR_MIN_UNITS,
        STEERING_ANCHOR_UNITS,
        STEERING_BAND_MIN_N,
        STEERING_BAND_QUOTE_MIN_N,
        STEERING_BAND_WINDOW,
        STEERING_FIRST_BLOCK_COUNTS,
        T90_ONE_SIDED,
    )
except ImportError:  # standalone (test suite loads this file directly)
    import derive  # type: ignore[no-redef]
    from const import (  # type: ignore[no-redef]
        BLOCK_CORRIDORS,
        LEGACY_ANCHOR_TOLERANCE,
        LEGACY_STEERING_ANCHOR,
        STEERING_ANCHOR_MIN_UNITS,
        STEERING_ANCHOR_UNITS,
        STEERING_BAND_MIN_N,
        STEERING_BAND_QUOTE_MIN_N,
        STEERING_BAND_WINDOW,
        STEERING_FIRST_BLOCK_COUNTS,
        T90_ONE_SIDED,
    )


# DER SCHALTER. Dieselbe Bauart wie der Block- und der Kurvenschalter: er steht
# im Archiv neben ihnen, und ausgeschaltet bleibt das heutige Verhalten
# bitgenau stehen - kein halber Umbau.
STEERING_SWITCH = "steering_v2"

# Die Familien, fuer die es ueberhaupt eine Blockvorgabe gibt. Tempo steht
# nicht darin: seine Zahl kommt aus der FTP, und eine Steuerung ohne eigene
# Messung waere eine Zahl mit falschem Etikett.
STEERING_FAMILIES = ("sweetspot", "vo2max")

# DER STARTWERT JE ATHLET (0.66.3, Michael-Befund). Er steht im Archiv unter
# settings.steering_anchor, je Familie {w, date, source, units}, entsteht beim
# Einschalten aus den letzten eigenen Einheiten und bleibt stehen. Seit 0.75.0
# (W2) traegt er die Vorgabe nicht mehr - sie wird bei jedem Aufruf aus den
# letzten Einheiten gerechnet. Er bleibt im Archiv und wird weiter angelegt.
ANCHOR_KEY = "steering_anchor"
ANCHOR_PENDING_NOTE = ("noch keine Vorgabe — {n} von {min} Einheiten gemessen; "
                       "ab der {min}. entsteht sie aus deinen letzten Einheiten")
ANCHOR_SOURCE = "aus deinen letzten {n} Einheiten"


def anchors(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Die gespeicherten Startwerte je Familie - {} wenn keiner da ist."""
    box = (data or {}).get("settings")
    got = box.get(ANCHOR_KEY) if isinstance(box, dict) else None
    if not isinstance(got, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for family, row in got.items():
        if family in STEERING_FAMILIES and isinstance(row, dict) \
                and isinstance(row.get("w"), (int, float)) and row.get("date"):
            out[family] = dict(row)
    return out


def rolling_target(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """DER EINE ERZEUGER der Vorgabe (W2): Median der gefahrenen Watt (ab Block 2)
    der letzten STEERING_ANCHOR_UNITS nutzbaren Einheiten - None unter
    STEERING_ANCHOR_MIN_UNITS. Startwert (`derive_anchor`) und Vorgabe
    (`target`) rufen beide hierher; einen zweiten Rechenweg gibt es nicht.
    """
    usable = [r for r in rows or [] if r.get("usable")]
    if len(usable) < STEERING_ANCHOR_MIN_UNITS:
        return None
    last = usable[-STEERING_ANCHOR_UNITS:]
    watts = [float(r.get("watts_raw", r["watts"])) for r in last]
    return {"w": int(round(derive._median(watts))),
            "units": [r["date"] for r in last],
            "unit_watts": [r.get("watts_raw", r["watts"]) for r in last],
            "n": len(last), "n_total": len(usable)}


def derive_anchor(points: list[dict[str, Any]], family: str, today: str) -> dict[str, Any] | None:
    """Ein Startwert aus den eigenen Einheiten - oder None, wenn es zu wenige sind."""
    got = rolling_target(unit_rows(points, family))
    if got is None:
        return None
    return {"w": got["w"], "date": str(today),
            "source": ANCHOR_SOURCE.format(n=got["n"]), "units": got["units"]}


def ensure_anchors(data: dict[str, Any], series: dict[str, Any], today: str) -> bool:
    """Startwerte anlegen, wo noch keiner steht und genug Einheiten da sind.

    GIBT ZURUECK, OB SICH ETWAS GEAENDERT HAT - der Aufrufer speichert nur
    dann (J7). Ein vorhandener Startwert wird NIE ueberschrieben.
    """
    box = (data or {}).setdefault("settings", {})
    if not isinstance(box, dict):
        box = data["settings"] = {}
    stored = box.get(ANCHOR_KEY)
    if not isinstance(stored, dict):
        stored = {}
    have = anchors(data)
    changed = False
    families = ((series or {}).get("families") or {})
    for family in STEERING_FAMILIES:
        if family in have:
            continue
        fresh = derive_anchor((families.get(family) or {}).get("points") or [], family, today)
        if fresh is None:
            continue
        stored[family] = fresh
        changed = True
    if changed:
        box[ANCHOR_KEY] = stored
    return changed


def migrate_legacy_anchor(data: dict[str, Any]) -> bool:
    """Die UEBERNAHME fuer Archive, die vor 0.66.3 mit eingeschalteter Steuerung liefen.

    Dort GALT der Startwert aus dem Code schon (0.62.0 bis 0.66.2); die
    Reparatur darf ihn nicht neu entstehen lassen, sonst bewegte sich die
    Vorgabe des ersten Athleten. Bedingung ist allein der Schalter: stand er
    aus, hat der Code-Startwert nie eine Vorgabe getragen, und ein zweiter
    Athlet bekommt keine fremde Zahl untergeschoben. Laeuft genau einmal.
    """
    box = (data or {}).get("settings")
    if not isinstance(box, dict) or not box.get(STEERING_SWITCH):
        return False
    if isinstance(box.get(ANCHOR_KEY), dict) and box[ANCHOR_KEY]:
        return False
    # ZWEITE BEDINGUNG: der Code-Startwert muss zum Bestand passen. Der eigene
    # Startwert aus den letzten Einheiten VOR dem alten Stichtag wird gerechnet;
    # weicht er je Familie um mehr als LEGACY_ANCHOR_TOLERANCE ab, gibt es
    # keine Uebernahme - ein zweiter Athlet, dessen Schalter beim Update
    # zufaellig an steht, bekommt so keine fremde Zahl (Michael-Befund).
    try:
        from . import blocks as blocks_lib
    except ImportError:
        import blocks as blocks_lib  # type: ignore[no-redef]
    legacy = LEGACY_STEERING_ANCHOR
    families = ((blocks_lib.series(data, with_other=False) or {}).get("families") or {})
    taken: dict[str, dict[str, Any]] = {}
    for family, w in legacy["w"].items():
        points = [p for p in ((families.get(family) or {}).get("points") or [])
                  if str(p.get("date") or "") <= legacy["date"]]
        own = derive_anchor(points, family, legacy["date"])
        if own is None or abs(own["w"] - int(w)) > LEGACY_ANCHOR_TOLERANCE * int(w):
            continue
        taken[family] = {"w": int(w), "date": legacy["date"], "source": legacy["source"], "units": []}
    if not taken:
        return False
    box[ANCHOR_KEY] = taken
    return True

SINGLE_BLOCK_NOTE = "nur ein Block gemessen — keine Vorgabe"
TOO_FEW_NOTE = "noch keine Toleranz"
# ZWEI GRUENDE, ZWEI SAETZE. "noch keine Toleranz" heisst: es fehlen
# Einheiten, und mit der naechsten kann die Spanne kommen. Fuer eine Familie
# OHNE Vorgabe (Tempo) stimmt das "noch" nicht - dort entsteht nie eine Spanne,
# weil es keine Vorgabe gibt, um die herum sie liegen koennte. Bis 0.65.2
# stand der erste Satz auch dort, neben "keine Vorgabe" - zwei Saetze, einer
# falsch (PROJEKTSTAND §7, Klasse "Zahl mit fremdem Etikett").
NO_TARGET_NOTE = "keine Vorgabe, keine Spanne"

# DIE SAETZE ZUM SCHALTER - aus dem Modul, nicht aus dem Frontend (fuenfte
# Bauregel). Zwei Fassungen, weil die beiden Lagen verschieden sind, und beide
# sagen nur, was der Code auch tut.
SWITCH_ON_NOTE = ("Deine Wattzahl ist eine Vorgabe: der mittlere Wert deiner letzten "
                  f"{STEERING_ANCHOR_UNITS} Einheiten dieser Art, jeweils ab Block 2. "
                  "Nach alpha regelst du in der Einheit selbst nach – die App startet "
                  "dich beim nächsten Mal dort, wo du gelandet bist. Neben jeder Zahl "
                  "steht eine Spanne, in der die nächste Einheit erwartet wird.")
SWITCH_OFF_NOTE = ("Deine Wattzahl ist der Wert deiner letzten Einheit und "
                   "springt mit jeder neuen Messung mit. Das ist das Verhalten "
                   "von 0.60.0 — ausgeschaltet ändert dieses Paket nichts.")
# DIE SAETZE DER KACHEL. Auch sie stehen hier und nicht im Frontend: die
# Kachel sagt damit dasselbe wie der Schalter, aus einer Quelle.
TILE_RIDE = "Fahr die {watts} W."
TILE_INSIDE = ("Landet deine nächste Einheit zwischen {low} und {high} W, ist alles "
               "normal. Die Vorgabe folgt dem, was du fährst: fährst du über mehrere "
               "Einheiten mehr, steigt sie mit – fährst du weniger, sinkt sie.")
TILE_NO_BAND = ("Für eine Spanne braucht es {min_n} gemessene Einheiten; solange "
                "steht die Vorgabe allein.")
TILE_BAND_MEANS = ("Die Spanne ist keine Grenze, sondern das Messrauschen: {share} "
                   "von 10 Einheiten landen erfahrungsgemäß darin.")
TILE_FIRST_BLOCK = ("Block 1 bleibt in der Blockreihe sichtbar, er trägt nur "
                    "regelmäßig das höhere alpha und steuert deshalb nicht mit.")
TILE_OFF = ("Die Steuerung ist aus — diese Zahl ist der Wert deiner letzten "
            "Einheit. Einschalten im Reiter „Woher die Zahlen kommen“, Schalter "
            "„Wattvorgabe“.")
# DER SATZ FUER EINE FAMILIE OHNE VORGABE. Er sagt beides in einem: keine
# Vorgabe, und deshalb auch keine Spanne - und ausdruecklich, dass weitere
# Einheiten daran nichts aendern. Das ist keine Vertroestung, sondern die
# Bauart: STEERING_FAMILIES kennt die Familie nicht, also ist `watts` None,
# also gibt `family_state` kein Band aus, egal bei welchem n.
TILE_NO_TARGET = ("Für diese Familie wird keine Vorgabe geführt — ihre Zahl kommt "
                  "aus der FTP. Ohne Vorgabe gibt es auch keine Spanne, und daran "
                  "ändern weitere Einheiten nichts.")
# Wie viele von zehn Einheiten das Band erfahrungsgemaess trifft. Das ist die
# Deckung des t-Bandes bei 80 % zweiseitig, nicht gerundetes Bauchgefuehl:
# t(0,90; n-1) laesst je 10 % nach oben und unten draussen.
TILE_BAND_SHARE = 8
# UND DER SATZ, WENN SIE NICHT ANGESAGT WERDEN DARF. Er sagt, WIE das Band
# gebaut ist, und verspricht keine Quote - wortgleich gebaut wie
# `fatigue_v2` "band_no_quote", damit beide Kacheln dieselbe Sprache
# sprechen, wenn sie dasselbe meinen.
TILE_BAND_NO_QUOTE = "t-Band über {n} Einheiten"

# DER AUFKLAPPTEIL. Er war bis 0.62.0 eine zweispaltige Tabelle - ein Format
# fuer den Vergleich ZWISCHEN Zeilen. Hier vergleicht niemand die Streuung mit
# dem Pulsfenster: es sind zusammenhaengende Angaben zu EINER Zahl, und im
# schmalen Container zerfiel die Tabelle in Wortfetzen. Jetzt: ein Satz mit
# eingebetteten Zahlen, eine abgesetzte Formelzeile, drei Chips.
# Der Satz wird HIER gefuellt (`origin_sentence`), nicht im Frontend: Kachel,
# Trainer-Karte, Rechenweg und Quellen-Reiter lesen denselben fertigen Satz.
MORE_ORIGIN = ("Die Vorgabe ist der mittlere Wert deiner letzten {n} Einheiten ({dates}), "
               "jeweils ab Block 2: {watts} W.")
MORE_FORMULA_LABEL = "Spanne"
MORE_FORMULA_CAP = ("{factor} = t(0,90; n−1) · √(1+1/n) · Streuung {sd} W aus den "
                    "letzten {n} Einheiten, jeweils ab Block 2")
MORE_MEASURED = "Gemessen wurde:"
CHIP_ALPHA = "alpha {low} – {high} · Korridor {clow} – {chigh}"
CHIP_HR = "Puls {low} – {high} bpm"
CHIP_FIRST_BLOCK = "Block 1 zählt nicht mit"

SWITCH_OFF_LABEL = "wie bisher"
SWITCH_ON_LABEL = "mit Vorgabe"
SWITCH_GO_LABEL = "auf die Vorgabe umstellen"
SWITCH_BACK_LABEL = "zurück auf die letzte Einheit"


def steering_on(data: dict[str, Any]) -> bool:
    """Steht der Steuerungsschalter auf AN?"""
    box = (data or {}).get("settings")
    return bool(isinstance(box, dict) and box.get(STEERING_SWITCH))


def _steering_blocks(point: dict[str, Any]) -> tuple[list[float], list[float], list[float]]:
    """Die Bloecke, die STEUERN - alpha, Watt, Puls, jeweils ohne Block 1.

    Block 1 bleibt in der Karte stehen; er zaehlt hier nicht mit (const.py
    STEERING_FIRST_BLOCK_COUNTS).
    """
    start = 0 if STEERING_FIRST_BLOCK_COUNTS else 1
    alphas = [a for a in (point.get("block_alphas") or [])[start:] if a is not None]
    watts = [w for w in (point.get("block_watts_each") or [])[start:] if w]
    pulses = [h for h in (point.get("block_hr") or [])[start:] if h]
    return ([float(x) for x in alphas], [float(x) for x in watts],
            [float(x) for x in pulses])


def _steering_minutes(point: dict[str, Any]) -> list[float]:
    """Die DAUER der steuernden Bloecke - woran gemessen wurde."""
    start = 0 if STEERING_FIRST_BLOCK_COUNTS else 1
    return [float(m) for m in (point.get("block_minutes") or [])[start:] if m]


def side(alpha: float, family: str) -> int:
    """Auf welcher Seite des Korridors liegt die Einheit? +1 zu locker, -1 zu hart."""
    low, high = BLOCK_CORRIDORS[family]
    if alpha > high:
        return 1
    if alpha < low:
        return -1
    return 0


def unit_rows(points: list[dict[str, Any]], family: str) -> list[dict[str, Any]]:
    """Je Einheit EINE Zeile aus den steuernden Bloecken - oder keine.

    Eine Einheit mit nur einem Block liefert nach dem Wegfall von Block 1
    nichts mehr. Sie wird nicht stillschweigend uebergangen, sondern als
    solche gemeldet (`single_block`).
    """
    rows: list[dict[str, Any]] = []
    for point in points or []:
        alphas, watts, pulses = _steering_blocks(point)
        if not alphas or not watts:
            rows.append({"date": point.get("date"), "name": point.get("name"),
                         "usable": False, "n_blocks": point.get("n_blocks")})
            continue
        rows.append({
            "date": point.get("date"), "name": point.get("name"), "usable": True,
            "n_blocks": point.get("n_blocks"),
            "alpha": round(derive._median(alphas), 3),
            "watts": round(derive._median(watts)),
            # UNGERUNDET fuer das Band. Der Median zweier Bloecke ist oft eine
            # halbe Zahl (237,5 W); rundet man ihn vor der Streuung, wandert
            # die Bandbreite um bis zu 1 W - genug, um das Band gegen die
            # nachgerechneten Zahlen zu verfehlen.
            "watts_raw": round(derive._median(watts), 2),
            "hr": round(derive._median(pulses)) if pulses else None,
            "minutes": (round(derive._median(_steering_minutes(point)), 1)
                        if _steering_minutes(point) else None),
            "side": side(derive._median(alphas), family),
        })
    return rows


def _dm(iso: Any) -> str:
    """TT.MM. aus einem ISO-Datum - fuer den Herkunftssatz."""
    t = str(iso or "")[:10].split("-")
    return f"{t[2]}.{t[1]}." if len(t) == 3 else str(iso or "")


def origin_sentence(state: dict[str, Any]) -> str | None:
    """MORE_ORIGIN mit den Zahlen der Vorgabe gefuellt - None ohne Vorgabe."""
    if not state or state.get("watts") is None:
        return None
    return MORE_ORIGIN.format(n=len(state.get("units") or []),
                              dates=", ".join(_dm(d) for d in state.get("units") or []),
                              watts=state["watts"])


def target(rows: list[dict[str, Any]], family: str) -> dict[str, Any]:
    """Die Vorgabe (W2): der mittlere Wert der letzten Einheiten, aus `rolling_target`.

    Familien OHNE Vorgabe (Tempo) bekommen keine - ihre Zeilen werden
    trotzdem gerechnet, damit der Verlauf ab Block 2 fuer jede Blockfamilie
    gezeichnet werden kann. Familien MIT Vorgabe, die noch zu wenige Einheiten
    haben, sagen das (`anchor_pending`, ANCHOR_PENDING_NOTE).
    """
    usable = [r for r in rows if r.get("usable")]
    base = {"watts": None, "units": [], "unit_watts": [], "sides": [], "note": None,
            "window": STEERING_ANCHOR_UNITS, "min_units": STEERING_ANCHOR_MIN_UNITS}
    if family not in STEERING_FAMILIES:
        return {**base, "no_target": True}
    got = rolling_target(rows)
    if got is None:
        return {**base,
                "note": ANCHOR_PENDING_NOTE.format(n=len(usable), min=STEERING_ANCHOR_MIN_UNITS),
                "anchor_pending": True, "anchor_min_units": STEERING_ANCHOR_MIN_UNITS,
                "n_units_total": len(usable)}
    last = usable[-STEERING_ANCHOR_UNITS:]
    return {**base, "watts": got["w"], "units": got["units"], "unit_watts": got["unit_watts"],
            # alpha-Seite je Einheit: ANZEIGE (Chip, Verlauf), sie bewegt nichts mehr.
            "sides": [r["side"] for r in last]}


def t_band(values: list[float], digits: int = 0,
           center: float | None = None) -> dict[str, Any] | None:
    """Median +/- t(0,90; n-1) * s * sqrt(1 + 1/n) ueber die letzten Einheiten.

    Das VORHERSAGEband fuer die naechste Einheit - deshalb die Wurzel mit dem
    Zusatzglied, und deshalb NICHT das schmalere Band des Mittelwerts. Unter
    drei Werten gibt es keins, und dann sagt die Karte das, statt eine Spanne
    aus zwei Punkten zu zeichnen.
    """
    used = [float(v) for v in (values or []) if v is not None][-STEERING_BAND_WINDOW:]
    n = len(used)
    if n < STEERING_BAND_MIN_N:
        return None
    # DIE MITTE IST DIE VORGABE, wo es eine gibt. Ein Band um den Median der
    # letzten vier Einheiten liegt sonst NEBEN der Zahl, die in der Kachel
    # steht - VO2max zeigte 250 W und ein Band 230|244|258, in dem 250 nicht
    # die Mitte war. Die BREITE kommt weiter aus dem Fenster; nur ihr
    # Aufhaengepunkt ist die Vorgabe.
    mid = derive._median(used) if center is None else float(center)
    mean = sum(used) / n
    # Stichprobenstreuung (n-1), passend zum t-Quantil.
    sd = (sum((x - mean) ** 2 for x in used) / (n - 1)) ** 0.5
    # EINSEITIG, ausdruecklich. t(0,90) symmetrisch um eine Mitte gelegt
    # schliesst 80 % ein - genau die "8 von 10", die die Kachel ansagt. Die
    # zweiseitige Tabelle steht daneben in `const.py` und gehoert der
    # Ermuedungskachel; welche hier richtig ist, ist eine offene Frage
    # (docs/rechenwege.md K6.2), aber keine stillschweigende.
    t = T90_ONE_SIDED.get(n - 1, T90_ONE_SIDED[max(T90_ONE_SIDED)])
    half = t * sd * (1 + 1 / n) ** 0.5
    return {
        "low": round(mid - half, digits) if digits else round(mid - half),
        "high": round(mid + half, digits) if digits else round(mid + half),
        "median": round(mid, 1), "centered_on": "target" if center is not None else "median",
        "unit_median": round(derive._median(used), 1),
        "half": round(half, 2), "sd": round(sd, 2), "t": t, "n": n,
        "window": STEERING_BAND_WINDOW, "min_n": STEERING_BAND_MIN_N,
        # DARF DIE QUOTE ANGESAGT WERDEN? Dieselbe Form wie bei der
        # Ermuedungskachel (`fatigue_v2.reversal_band`): das Band wird
        # gerechnet wie immer, nur die Zusage darueber haelt sich zurueck,
        # solange sie nicht nachpruefbar ist.
        "quote_shown": n >= STEERING_BAND_QUOTE_MIN_N,
        "quote_min_n": STEERING_BAND_QUOTE_MIN_N,
    }


def family_state(points: list[dict[str, Any]], family: str) -> dict[str, Any]:
    """Alles, was eine Familie unter der neuen Steuerung traegt."""
    rows = unit_rows(points, family)
    usable = [r for r in rows if r.get("usable")]
    state = target(rows, family)
    state["origin"] = origin_sentence(state)
    state["rows"] = rows
    state["n_units"] = len(usable)
    state["single_block"] = [r["date"] for r in rows if not r.get("usable")]
    state["band"] = (t_band([r.get("watts_raw", r["watts"]) for r in usable],
                            center=state["watts"]) if state.get("watts") else None)
    state["hr_band"] = t_band([r["hr"] for r in usable if r.get("hr")])
    # WELCHER GRUND FEHLT? Ohne Vorgabe (Tempo) fehlt sie dauerhaft, sonst
    # fehlen Einheiten (voruebergehend). Zwei Lagen, zwei Saetze.
    state["band_note"] = (NO_TARGET_NOTE if state.get("no_target")
                          else (None if state["band"] else TOO_FEW_NOTE))
    state["hr_band_note"] = None if state["hr_band"] else TOO_FEW_NOTE
    state["first_block_counts"] = STEERING_FIRST_BLOCK_COUNTS
    mins = [r["minutes"] for r in usable if r.get("minutes")]
    state["measured_minutes"] = round(derive._median(mins), 1) if mins else None
    state["corridor"] = list(BLOCK_CORRIDORS[family])
    return state


def state(series: dict[str, Any]) -> dict[str, Any]:
    """Je Familie die Vorgabe - gerechnet allein aus der Blockreihe (W2)."""
    families = (series or {}).get("families") or {}
    out: dict[str, Any] = {}
    for family, box in families.items():
        if family not in BLOCK_CORRIDORS:
            continue
        out[family] = family_state(box.get("points") or [], family)
    return out


def compare(series: dict[str, Any]) -> dict[str, Any]:
    """ALT neben NEU, je Familie - fuer die Parallelanzeige.

    ALT ist die heutige Rechnung, Zeichen fuer Zeichen dieselbe Quelle wie in
    `workouts.scaled()`: der Median der LETZTEN Einheit, und nur wenn die
    Belegung reicht. NEU ist die Vorgabe dieses Moduls. Beide Zahlen stehen
    nebeneinander, damit ueber mehrere Einheiten vergleichbar wird, was der
    Schalter tut - statt dass eine Zahl still eine andere ersetzt.
    """
    families = (series or {}).get("families") or {}
    steering = state(series)
    out: dict[str, Any] = {}
    for family, box in families.items():
        latest = box.get("latest") or {}
        window = box.get("hr_window") or {}
        new = steering.get(family)
        old_w = latest.get("median_watts") if box.get("source_ok") else None
        out[family] = {
            "old_watts": old_w,
            "old_hr_low": window.get("low"), "old_hr_high": window.get("high"),
            "old_source": "blocks" if old_w is not None else "ftp",
            "new_watts": (new or {}).get("watts"),
            "new_band": (new or {}).get("band"),
            "new_hr_band": (new or {}).get("hr_band"),
            "new_note": (new or {}).get("note"),
            "steered": bool(new),
            # None, wenn es keine Vorgabe gibt - eine Familie ohne Vorgabe
            # (Tempo, oder ein Athlet mit zu wenigen Einheiten) hat
            # nichts, wogegen sich der Median vergleichen liesse (F2.1: bis
            # 0.66.2 fiel hier der ganze `blocks`-Befehl mit TypeError).
            "delta": (None if (new is None or old_w is None or new.get("watts") is None)
                      else round(new["watts"] - old_w)),
        }
    return out
