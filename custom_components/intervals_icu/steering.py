"""Die Vorgabe je Blockfamilie - gerechnet, nicht gespeichert (Paket B).

WARUM NACHRECHNEN STATT SPEICHERN. C6 verschiebt die VORGABE, nicht die
gefahrenen Watt - also muss es eine Vorgabe geben, die bleibt. Zwei Bauarten
standen zur Wahl: sie im Archiv fortschreiben (A) oder sie bei jedem Aufruf
ab einem festen Startwert nachrechnen (B). Simuliert wurde beides:

* A haengt an der REIHENFOLGE, in der markiert wird. Bei identischem Bestand
  und allen 720 Klickreihenfolgen lagen zwischen der kleinsten und groessten
  Vorgabe bis zu 10 W. B ist in allen 720 dieselbe Zahl.
* A kann eine zurueckgenommene Marke nicht zurueckdrehen: der Schritt ist
  geschrieben. In 34,5 % der Laeufe mit geloeschter und neu gemessener Marke
  wich A von der nachgerechneten Zahl ab, bis 10 W.
* A haette beim Blockschalter ZWEI Speicher gebraucht, einen je Auswahl -
  sonst steht in der anderen Stellung eine Zahl, die dort nie gerechnet wurde
  (im Test 235 statt 245 W).
* A braucht einen sechsten Archivblock samt Migration und Schreibweg;
  gerechnet ~53 zusaetzliche Speichervorgaenge je Saison, dazu drei
  Fehlerklassen (Schreiben schlaegt fehl, Abbruch zwischen Messung und
  Fortschreibung, zwei Messungen gleichzeitig). B hat keinen Schreibweg.

Der Preis von B steht im Kopf des Stichtags: ohne ihn aendert das
Nachmarkieren alter Fahrten die heutige Vorgabe (292 von 300 Laeufen, im
Mittel 9,2 W). MIT Stichtag wirkt ein Nachtrag auf Blockreihe, Pulsfenster
und Band - aber nicht auf die Vorgabe.

Dieses Modul ist HA-frei und rechnet ausschliesslich auf dem Ergebnis von
`blocks.series()`. Damit folgt es dem Blockschalter, ohne ihn zu kennen.
"""

from __future__ import annotations

from typing import Any

try:  # inside the package (Home Assistant)
    from . import derive
    from .const import (
        BLOCK_CORRIDORS,
        STEERING_ANCHOR_DATE,
        STEERING_ANCHOR_W,
        STEERING_BAND_MIN_N,
        STEERING_BAND_WINDOW,
        STEERING_CLEAR_AFTER_STEP,
        STEERING_FIRST_BLOCK_COUNTS,
        STEERING_MIN_UNITS,
        STEERING_NEED,
        STEERING_STEP_W,
        STEERING_T90,
        STEERING_WINDOW,
    )
except ImportError:  # standalone (test suite loads this file directly)
    import derive  # type: ignore[no-redef]
    from const import (  # type: ignore[no-redef]
        BLOCK_CORRIDORS,
        STEERING_ANCHOR_DATE,
        STEERING_ANCHOR_W,
        STEERING_BAND_MIN_N,
        STEERING_BAND_WINDOW,
        STEERING_CLEAR_AFTER_STEP,
        STEERING_FIRST_BLOCK_COUNTS,
        STEERING_MIN_UNITS,
        STEERING_NEED,
        STEERING_STEP_W,
        STEERING_T90,
        STEERING_WINDOW,
    )


# DER SCHALTER. Dieselbe Bauart wie der Block- und der Kurvenschalter: er steht
# im Archiv neben ihnen, und ausgeschaltet bleibt das heutige Verhalten
# bitgenau stehen - kein halber Umbau.
STEERING_SWITCH = "steering_v2"

# Die Familien, fuer die es ueberhaupt eine Blockvorgabe gibt. Tempo steht
# nicht darin: seine Zahl kommt aus der FTP, und eine Steuerung ohne eigene
# Messung waere eine Zahl mit falschem Etikett.
STEERING_FAMILIES = tuple(STEERING_ANCHOR_W)

SINGLE_BLOCK_NOTE = "nur ein Block gemessen — keine Vorgabe"
TOO_FEW_NOTE = "noch keine Toleranz"
NO_UNITS_NOTE = ("noch keine Einheit seit dem Startwert — die Vorgabe steht "
                 "auf ihm")

# DIE SAETZE ZUM SCHALTER - aus dem Modul, nicht aus dem Frontend (fuenfte
# Bauregel). Zwei Fassungen, weil die beiden Lagen verschieden sind, und beide
# sagen nur, was der Code auch tut.
SWITCH_ON_NOTE = ("Deine Wattzahl ist eine Vorgabe: sie startet auf einem festen "
                  "Wert und bewegt sich erst, wenn mehrere Einheiten "
                  "nacheinander daneben liegen. Der erste Block einer Einheit "
                  "zählt dabei nicht mit. Neben jeder Zahl steht eine Spanne, "
                  "in der die nächste Einheit erwartet wird.")
SWITCH_OFF_NOTE = ("Deine Wattzahl ist der Wert deiner letzten Einheit und "
                   "springt mit jeder neuen Messung mit. Das ist das Verhalten "
                   "von 0.60.0 — ausgeschaltet ändert dieses Paket nichts.")
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


def c6(rows: list[dict[str, Any]], family: str) -> dict[str, Any]:
    """Die Regel. Ab Startwert, ueber die Einheiten NACH dem Stichtag.

    Bezug ist die VORGABE: der Schritt von 5 W wird auf sie gerechnet, nicht
    auf die gefahrenen Watt. Ohne diesen Bezug faellt die Vorgabe bei
    geregelten Einheiten mit den gefahrenen Watt ab (Kreuzprobe, -18 W).
    """
    anchor = STEERING_ANCHOR_W[family]
    since = [r for r in rows if r.get("usable") and str(r.get("date") or "") > STEERING_ANCHOR_DATE]
    target = anchor
    steps: list[dict[str, Any]] = []
    hist: list[int] = []
    for row in since:
        hist.append(row["side"])
        if len(since) < STEERING_MIN_UNITS:
            continue
        window = hist[-STEERING_WINDOW:]
        for direction in (1, -1):
            if window.count(direction) >= STEERING_NEED:
                target += direction * STEERING_STEP_W
                steps.append({"date": row["date"], "to": target,
                              "dir": direction, "window": list(window)})
                if STEERING_CLEAR_AFTER_STEP:
                    hist = []
                break
    note = None
    if not since:
        note = NO_UNITS_NOTE
    elif len(since) < STEERING_MIN_UNITS:
        note = (f"erst {len(since)} von {STEERING_MIN_UNITS} Einheiten seit dem "
                "Startwert — die Vorgabe bewegt sich noch nicht")
    return {
        "watts": target, "anchor_w": anchor, "anchor_date": STEERING_ANCHOR_DATE,
        "n_since": len(since), "min_units": STEERING_MIN_UNITS,
        "steps": steps, "moves": len(steps),
        "sides": [r["side"] for r in since], "note": note,
    }


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
    t = STEERING_T90.get(n - 1, STEERING_T90[max(STEERING_T90)])
    half = t * sd * (1 + 1 / n) ** 0.5
    return {
        "low": round(mid - half, digits) if digits else round(mid - half),
        "high": round(mid + half, digits) if digits else round(mid + half),
        "median": round(mid, 1), "centered_on": "target" if center is not None else "median",
        "unit_median": round(derive._median(used), 1),
        "half": round(half, 2), "sd": round(sd, 2), "t": t, "n": n,
        "window": STEERING_BAND_WINDOW, "min_n": STEERING_BAND_MIN_N,
    }


def family_state(points: list[dict[str, Any]], family: str) -> dict[str, Any]:
    """Alles, was eine Familie unter der neuen Steuerung traegt."""
    rows = unit_rows(points, family)
    usable = [r for r in rows if r.get("usable")]
    state = c6(rows, family)
    state["rows"] = rows
    state["n_units"] = len(usable)
    state["single_block"] = [r["date"] for r in rows if not r.get("usable")]
    state["band"] = t_band([r.get("watts_raw", r["watts"]) for r in usable],
                          center=state["watts"])
    state["hr_band"] = t_band([r["hr"] for r in usable if r.get("hr")])
    state["band_note"] = None if state["band"] else TOO_FEW_NOTE
    state["hr_band_note"] = None if state["hr_band"] else TOO_FEW_NOTE
    state["first_block_counts"] = STEERING_FIRST_BLOCK_COUNTS
    mins = [r["minutes"] for r in usable if r.get("minutes")]
    state["measured_minutes"] = round(derive._median(mins), 1) if mins else None
    state["corridor"] = list(BLOCK_CORRIDORS[family])
    return state


def state(series: dict[str, Any]) -> dict[str, Any]:
    """Je Familie die neue Vorgabe - gerechnet aus der Blockreihe."""
    families = (series or {}).get("families") or {}
    out: dict[str, Any] = {}
    for family in STEERING_FAMILIES:
        box = families.get(family)
        if not box:
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
            "delta": (None if (new is None or old_w is None)
                      else round(new["watts"] - old_w)),
        }
    return out
