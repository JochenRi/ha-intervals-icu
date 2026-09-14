"""Stufentest: die beiden Schwellen aus EINER Fahrt (docs/ausbau.md N).

WIE DIE SCHWELLE ENTSTEHT - und warum das nicht "ablesen" ist
Beide Arbeiten, an denen dieses Modul haengt, machen dasselbe: DFA a1 wird
ueber die Zeit aufgetragen, die Kurve zeigt einen stabilen Bereich oben, dann
einen nahezu linearen Abfall, dann eine flache Strecke unten. Durch den
ABFALL wird eine Gerade gelegt, und die Schwelle ist der SCHNITTPUNKT dieser
Geraden mit 0,75 (HRVT1) bzw. 0,5 (HRVT2).

Das ist etwas anderes als "der erste Punkt unter 0,75", und es liefert ein
anderes Ergebnis: ein einzelner Ausreisser entscheidet nichts mehr, dafuer
entscheidet die Wahl des Segments alles. In beiden Arbeiten wird dieses
Segment VON HAND bestimmt - visuell, am Plot. Unsere Regel dafuer ist deshalb
eine SETZUNG, und die Karte sagt das.

DIE SEGMENTREGEL (eine Bestimmung, zwei Ergebnisse)
  Ende   der erste Punkt, ab dem die GEGLAETTETE Kurve fuer RAMP_FLAT_S
         Sekunden unter 0,5 bleibt. Ein einzelner Ausreisser ist kein Ende.
  Anfang der LETZTE Hochpunkt davor: die letzte Stelle, an der die geglaettete
         Kurve ihr Maximum ueber dem Bereich davor erreicht. Bei einem
         Plateau ist das dessen rechtes Ende - also genau die Stelle, an der
         der Abfall beginnt.
  Und derselbe Hochpunkt ist `max_alpha_start` fuer die dritte Zahl.

Geglaettet wird NUR fuer die Segmentsuche. Gerechnet wird auf den
ungeglaetteten Werten - die Glaettung sucht die Grenzen, sie verschiebt
keinen Messwert.

DIE DRITTE ZAHL - und warum sie aus zweiter Hand ist
Rogers 2024 definiert eine personalisierte erste Schwelle als den Wert mittig
zwischen "the maximum seen during the early ramp incremental" und 0,5. Was
"frueh" heisst, steht dort nicht; die Arbeit ist nicht frei zugaenglich.
Olieslagers 2026 setzt es um und zitiert Rogers dafuer: der hoechste Wert AM
BEGINN DES LINEAREN ABFALLS, also HRVT1pers = (max. DFAa1start + 0,5) / 2.

DAS SIND NICHT DIESELBEN SAETZE. Ein Maximum in einem ZEITFENSTER ist etwas
anderes als ein Maximum an einem KURVENPUNKT. Gebaut ist hier die Fassung von
Olieslagers, weil sie implementierbar ist und an dasselbe Segment haengt, das
die Regression ohnehin braucht - und sie ist als Operationalisierung aus
zweiter Hand beschriftet, nicht als Rogers' Wortlaut.

WAS DIESES MODUL NICHT TUT
Es rechnet nicht ueber das Segment hinaus. Liegt ein Schnittpunkt ausserhalb
des gemessenen Abfalls, gibt es die Schwelle nicht - dieselbe Regel wie in der
Durability-Kachel, die ueber ihre arbeitsreichste Fahrt hinaus nie
hochrechnet. Wer bei alpha 0,6 abbricht, hat keine HRVT2, und das ist eine
Auskunft und kein Fehler.

Kein Home-Assistant-Import: das Modul rechnet auf Listen.
"""

from __future__ import annotations

from typing import Any

try:  # inside the package (Home Assistant)
    from .const import (
        RAMP_FLAT_S,
        RAMP_MIN_POINTS,
        RAMP_READ_WINDOW_S,
        RAMP_RECOVERY_WINDOW_S,
        RAMP_SMOOTH_S,
    )
    from .derive import DFA_AEROBIC, DFA_ANAEROBIC
except ImportError:  # standalone (test suite loads this file directly)
    from const import (  # type: ignore[no-redef]
        RAMP_FLAT_S,
        RAMP_MIN_POINTS,
        RAMP_READ_WINDOW_S,
        RAMP_RECOVERY_WINDOW_S,
        RAMP_SMOOTH_S,
    )
    from derive import DFA_AEROBIC, DFA_ANAEROBIC  # type: ignore[no-redef]


def _number(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out == out else None


def _clean(dfa: list[Any] | None) -> list[float | None]:
    """Artefakte raus, Form behalten.

    Die Stelle im Strom traegt die ZEIT, deshalb wird nicht zusammengeschoben:
    ein verworfener Wert wird None und bleibt an seinem Platz. Sonst wanderte
    jeder Zeitpunkt hinter einem Artefakt nach vorn.
    """
    out: list[float | None] = []
    for raw in (dfa or []):
        value = _number(raw)
        # Exakt 0 schreibt Intervals, bevor der Algorithmus eingeschwungen ist -
        # das ist keine Messung (derive.dfa_summary haelt es genauso).
        out.append(value if value is not None and 0.0 < value <= 2.0 else None)
    return out


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _smooth(values: list[float | None], width: int) -> list[float | None]:
    """Gleitender MEDIAN, nicht Mittel: ein Artefakt soll das Fenster nicht
    mitnehmen. Fenster ohne einen einzigen Messwert bleiben None."""
    if width < 1:
        width = 1
    half = width // 2
    out: list[float | None] = []
    for index in range(len(values)):
        window = [v for v in values[max(0, index - half):index + half + 1] if v is not None]
        out.append(_median(window) if window else None)
    return out


def _window_median(values: list[Any] | None, centre: int, half: int) -> float | None:
    """Median eines Fensters um eine Stelle, Nullwerte raus.

    Null Watt heisst Rollenlassen und null bpm ein abgerutschter Gurt - beides
    ist kein Messwert und zoege die Zahl nach unten (dieselbe Regel wie in
    derive.dfa_summary).
    """
    if not values:
        return None
    picked: list[float] = []
    for index in range(max(0, centre - half), min(len(values), centre + half + 1)):
        value = _number(values[index])
        if value is not None and value > 0:
            picked.append(value)
    return _median(picked) if picked else None


def segment(dfa: list[Any] | None, sample_secs: int = 1) -> dict[str, Any] | None:
    """Anfang und Ende des nahezu linearen Abfalls, plus der Hochpunkt davor.

    Gibt None zurueck, wenn es keinen brauchbaren Abfall gibt - das ist der
    Normalfall fuer jede Fahrt, die kein Stufentest ist.
    """
    values = _clean(dfa)
    if not any(v is not None for v in values):
        return None
    step = max(1, int(sample_secs))
    smooth = _smooth(values, max(1, RAMP_SMOOTH_S // step))
    flat_needed = max(1, RAMP_FLAT_S // step)

    # --- Ende: ab hier bleibt die Kurve unten -------------------------------
    end = None
    run = 0
    first_of_run = None
    for index, value in enumerate(smooth):
        if value is None:
            continue
        if value < DFA_ANAEROBIC:
            if first_of_run is None:
                first_of_run = index
            run += 1
            if run >= flat_needed:
                end = first_of_run
                break
        else:
            run = 0
            first_of_run = None
    reached = end is not None
    if end is None:
        # Kein gesicherter Boden: der Abfall endet am letzten Messwert. HRVT2
        # gibt es dann nicht - siehe evaluate().
        end = max(i for i, v in enumerate(smooth) if v is not None)

    # --- Anfang: der LETZTE Hochpunkt davor ---------------------------------
    before = [(i, v) for i, v in enumerate(smooth[:end + 1]) if v is not None]
    if not before:
        return None
    peak = max(v for _, v in before)
    start = max(i for i, v in before if v == peak)
    if start >= end:
        return None
    points = sum(1 for v in values[start:end + 1] if v is not None)
    if points < RAMP_MIN_POINTS // step:
        return None
    return {"start_index": start, "end_index": end, "max_alpha_start": round(peak, 3),
            "points": points, "reached_anaerobic": reached}


def _fit(values: list[float | None], start: int, end: int, step: int) -> dict[str, float] | None:
    """Gerade durch den Abfall, auf den UNGEGLAETTETEN Werten."""
    xs: list[float] = []
    ys: list[float] = []
    for index in range(start, end + 1):
        value = values[index]
        if value is None:
            continue
        xs.append(float(index * step))
        ys.append(value)
    n = len(xs)
    if n < 2:
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    sxx = sum((x - mean_x) ** 2 for x in xs)
    if sxx <= 0:
        return None
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = mean_y - slope * mean_x
    syy = sum((y - mean_y) ** 2 for y in ys)
    r2 = (sxy * sxy) / (sxx * syy) if syy > 0 else 0.0
    return {"slope": slope, "intercept": intercept, "r2": r2, "n": float(n)}


def evaluate(dfa: list[Any] | None, watts: list[Any] | None = None,
             heartrate: list[Any] | None = None,
             sample_secs: int = 1) -> dict[str, Any] | None:
    """Die drei Zahlen plus die Erholung, aus einem einzigen Strom.

    Erwartet den UNGEDUENNTEN Strom. Der Panel-Endpunkt deckelt bei 900
    Punkten - das sind 7 bis 18 Sekunden je Probe, und eine Gerade durch den
    Abfall staende dann auf rund hundert Punkten statt auf tausenden.
    """
    seg = segment(dfa, sample_secs)
    if seg is None:
        return None
    step = max(1, int(sample_secs))
    values = _clean(dfa)
    fit = _fit(values, seg["start_index"], seg["end_index"], step)
    if fit is None:
        return None

    t_start = float(seg["start_index"] * step)
    t_end = float(seg["end_index"] * step)
    half = max(1, (RAMP_READ_WINDOW_S // step) // 2)

    def at(alpha: float) -> dict[str, Any] | None:
        """Der Schnittpunkt der Geraden mit einem alpha-Wert - oder nichts.

        Faellt die Gerade nicht (Steigung >= 0), gibt es keinen Schnittpunkt,
        den man ernst nehmen koennte. Und ausserhalb des gemessenen Abfalls
        wird NICHT hochgerechnet.
        """
        if fit["slope"] >= 0:
            return None
        seconds = (alpha - fit["intercept"]) / fit["slope"]
        if seconds < t_start or seconds > t_end:
            return None
        index = int(round(seconds / step))
        return {
            "alpha": round(alpha, 3),
            "seconds": round(seconds),
            "watts": _window_median(watts, index, half),
            "hr": _window_median(heartrate, index, half),
        }

    peak = float(seg["max_alpha_start"])
    pers_alpha = (peak + DFA_ANAEROBIC) / 2.0

    out: dict[str, Any] = {
        "hrvt1": at(DFA_AEROBIC),
        # HRVT2 gibt es nur, wenn der Abfall unten auch ANGEKOMMEN ist. Ohne
        # das waere der Schnittpunkt eine Verlaengerung der Geraden ins
        # Ungemessene - genau das, was diese Karte nirgends tut.
        "hrvt2": at(DFA_ANAEROBIC) if seg["reached_anaerobic"] else None,
        "hrvt1_pers": at(pers_alpha),
        "max_alpha_start": seg["max_alpha_start"],
        "pers_alpha": round(pers_alpha, 3),
        "segment": {"from_s": round(t_start), "to_s": round(t_end),
                    "points": seg["points"], "r2": round(fit["r2"], 3),
                    "slope_per_min": round(fit["slope"] * 60.0, 4)},
        "reached_anaerobic": seg["reached_anaerobic"],
        "smooth_s": RAMP_SMOOTH_S,
        "flat_s": RAMP_FLAT_S,
        "read_window_s": RAMP_READ_WINDOW_S,
    }
    out["recovery"] = recovery(dfa, seg["end_index"], sample_secs)
    return out


def recovery(dfa: list[Any] | None, from_index: int,
             sample_secs: int = 1) -> dict[str, Any] | None:
    """Was im Ausrollen passiert. KEINE Protokollgroesse, eigene Idee.

    Zwei Zahlen: der Wert am Ende der Fahrt, und wie lange es vom Ende des
    Abfalls gedauert hat, bis die Kurve wieder ueber 0,5 lag und dort blieb.
    Belegt ist nur die FORM - in den ersten Minuten nach der Belastung erholt
    sich der Kreislauf schnell, aber unvollstaendig, und die Literatur schaut
    dafuer auf das Fenster 0 bis 10 Minuten. Eine Dauer fuer ein Ausrollen
    nennt sie nicht, und was ein guter Wert waere, erst recht nicht.

    Die Zahl sagt deshalb nach EINEM Test nichts. Sie faengt an, etwas zu
    sagen, wenn es mehrere gibt - wie die HF-Spanne und die fremde
    Gegenprobe. In keine Vorgabe fliesst sie ein.
    """
    values = _clean(dfa)
    if from_index >= len(values):
        return None
    step = max(1, int(sample_secs))
    tail_from = max(from_index, len(values) - max(1, RAMP_RECOVERY_WINDOW_S // step))
    tail = [v for v in values[tail_from:] if v is not None]
    back: int | None = None
    needed = max(1, RAMP_FLAT_S // step)
    run = 0
    first_of_run = None
    for index in range(from_index, len(values)):
        value = values[index]
        if value is None:
            continue
        if value >= DFA_ANAEROBIC:
            if first_of_run is None:
                first_of_run = index
            run += 1
            if run >= needed:
                back = (first_of_run - from_index) * step
                break
        else:
            run = 0
            first_of_run = None
    if not tail and back is None:
        return None
    return {
        "alpha_end": round(_median(tail), 3) if tail else None,
        "back_above_s": back,
        "window_s": RAMP_RECOVERY_WINDOW_S,
        "n": len(tail),
    }
