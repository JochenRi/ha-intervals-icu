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

DIE SEGMENTREGEL - Rechenweg e1 (eine Bestimmung, zwei Ergebnisse)
  Ende   das LASTENDE aus dem Protokoll: Laenge der Fahrt minus
         RAMP_COOLDOWN_MIN. Die Gerade laeuft bis zum letzten Zeitpunkt der
         Belastung, gegen die ZEIT. Frueher endete das Segment am ersten
         Lauf unter 0,5 - dort liegt die ueber den ganzen Abfall gemittelte
         Gerade fast immer noch ueber 0,5, und HRVT2 war damit strukturell
         unerreichbar.
  Anfang der LETZTE Hochpunkt der geglaetteten Kurve AB RAMPENBEGINN
         (RAMP_WARMUP_MIN) bis zum Ende. Bei einem Plateau ist das dessen
         rechtes Ende - also genau die Stelle, an der der Abfall beginnt.
         Ohne die Grenze lag der Hochpunkt im Einrollen, bei konstanter
         Leistung, zwoelf Minuten vor der Rampe.
  Und derselbe Hochpunkt ist `max_alpha_start` fuer die dritte Zahl.
  Beide Grenzen sind SETZUNGEN aus dem Protokoll. Deshalb prueft
  protocol() zuerst, ob die Fahrt das Protokoll traegt - sonst stuenden die
  Grenzen an der falschen Stelle, und das Ergebnis saehe trotzdem aus wie
  eines.

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
        RAMP_COOLDOWN_MAX_SHARE,
        RAMP_COOLDOWN_MIN,
        RAMP_END_CHECK_GAP_S,
        RAMP_END_CHECK_WINDOW_S,
        RAMP_FLAT_S,
        RAMP_MIN_POINTS,
        RAMP_PROTOCOL_SLOPE_SHARE,
        RAMP_READ_WINDOW_S,
        RAMP_RECOVERY_WINDOW_S,
        RAMP_SMOOTH_S,
        RAMP_STEP_W_PER_MIN,
        RAMP_WARMUP_MIN,
    )
    from .derive import DFA_AEROBIC, DFA_ANAEROBIC
except ImportError:  # standalone (test suite loads this file directly)
    from const import (  # type: ignore[no-redef]
        RAMP_COOLDOWN_MAX_SHARE,
        RAMP_COOLDOWN_MIN,
        RAMP_END_CHECK_GAP_S,
        RAMP_END_CHECK_WINDOW_S,
        RAMP_FLAT_S,
        RAMP_MIN_POINTS,
        RAMP_PROTOCOL_SLOPE_SHARE,
        RAMP_READ_WINDOW_S,
        RAMP_RECOVERY_WINDOW_S,
        RAMP_SMOOTH_S,
        RAMP_STEP_W_PER_MIN,
        RAMP_WARMUP_MIN,
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


def _slope_per_min(values: list[Any] | None, first: int, last: int,
                   step: int) -> float | None:
    """Watt-Steigung je Minute ueber [first, last], Nullwerte raus.

    Null Watt ist Rollenlassen, keine Leistung (dieselbe Regel wie
    _window_median). Unter zwei Punkten gibt es keine Steigung.
    """
    xs: list[float] = []
    ys: list[float] = []
    for index in range(max(0, first), min(len(values or []), last + 1)):
        value = _number(values[index])
        if value is not None and value > 0:
            xs.append(float(index * step))
            ys.append(value)
    if len(xs) < 2:
        return None
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    sxx = sum((x - mean_x) ** 2 for x in xs)
    if sxx <= 0:
        return None
    return 60.0 * sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / sxx


def _span_median(values: list[Any] | None, first: int, last: int) -> float | None:
    """Median ueber [first, last], Nullwerte raus."""
    if not values or last < first:
        return None
    picked = [v for v in (_number(values[i]) for i in range(max(0, first), min(len(values), last + 1)))
              if v is not None and v > 0]
    return _median(picked) if picked else None


# Die Gruende, warum KEINE Zahlen herauskommen - je Fall ein eigener Satz. Der
# Handler schreibt den Satz ins Archiv; ein Sammelsatz wie "kein auswertbarer
# Abfall" waere bei einer Fahrt ohne Einrollen schlicht falsch.
NO_WATTS = "no_watts"
LENGTH_MISMATCH = "length_mismatch"
TOO_SHORT = "too_short"
WARMUP_NO_WATTS = "warmup_no_watts"
WARMUP_NOT_FLAT = "warmup_not_flat"
RAMP_NOT_RISING = "ramp_not_rising"
COOLDOWN_MISSING = "cooldown_missing"
COOLDOWN_TOO_SHORT = "cooldown_too_short"
COOLDOWN_TOO_LONG = "cooldown_too_long"
NO_ALPHA = "no_alpha"
NO_FALL = "no_fall"
TOO_FEW_POINTS = "too_few_points"


def _share(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def _reason(code: str, facts: dict[str, Any]) -> str:
    """Der Satz zu einem Grund, mit den gemessenen Zahlen, wo es welche gibt."""
    limit = _share(RAMP_PROTOCOL_SLOPE_SHARE * RAMP_STEP_W_PER_MIN)

    def num(key: str) -> str:
        value = facts.get(key)
        return "–" if value is None else _share(float(value))

    texts = {
        NO_WATTS: "Kein Leistungsstrom in dieser Fahrt — ohne Watt lässt sich "
                  "nicht prüfen, ob sie dem Stufentest-Protokoll folgt.",
        LENGTH_MISMATCH: "Leistungs- und alpha-Strom sind verschieden lang — die "
                         "Protokollgrenzen lägen in beiden an verschiedenen Sekunden.",
        TOO_SHORT: f"Die Fahrt ist kürzer als {RAMP_WARMUP_MIN} Minuten Einrollen "
                   f"plus {RAMP_COOLDOWN_MIN} Minuten Ausrollen — für eine Rampe "
                   "bleibt keine Zeit.",
        WARMUP_NO_WATTS: f"In den ersten {RAMP_WARMUP_MIN} Minuten steht keine "
                         "Leistung — das Einrollen ist nicht prüfbar.",
        WARMUP_NOT_FLAT: f"Die ersten {RAMP_WARMUP_MIN} Minuten steigen um "
                         f"{num('warmup_w_per_min')} W/min, flaches Einrollen heißt "
                         f"unter {limit} W/min — die Rampe hat vermutlich ohne "
                         "Einrollen begonnen.",
        RAMP_NOT_RISING: f"Zwischen Einrollen und Ausrollen steigt die Leistung um "
                         f"{num('ramp_w_per_min')} W/min, eine Rampe heißt mindestens "
                         f"{limit} W/min.",
        COOLDOWN_MISSING: "Am Ende der Fahrt fällt die Leistung nicht ab — es gibt "
                          "kein Ausrollen, das Lastende ist nicht bestimmbar.",
        COOLDOWN_TOO_SHORT: f"Das Ausrollen ist kürzer als {RAMP_COOLDOWN_MIN} "
                            f"Minuten: {RAMP_COOLDOWN_MIN} Minuten vor Schluss liegt "
                            f"noch Last an ({num('before_w')} W davor, "
                            f"{num('after_w')} W danach).",
        COOLDOWN_TOO_LONG: f"Das Ausrollen ist länger als {RAMP_COOLDOWN_MIN} "
                           f"Minuten: {RAMP_COOLDOWN_MIN} Minuten vor Schluss wird "
                           f"schon ausgerollt ({num('before_w')} W davor, "
                           f"{num('after_w')} W danach).",
        NO_ALPHA: "Zwischen Rampenbeginn und Lastende steht kein alpha-Wert — "
                  "die Uhr hat DFA a1 nicht aufgezeichnet.",
        NO_FALL: "DFA a1 fällt zwischen Rampenbeginn und Lastende nicht ab — der "
                 "höchste Wert liegt am Ende.",
        TOO_FEW_POINTS: f"Der Abfall von DFA a1 trägt weniger als {RAMP_MIN_POINTS} "
                        "Messpunkte — daraus wird keine Gerade gelegt.",
    }
    return texts[code]


def protocol(length: int, watts: list[Any] | None,
             sample_secs: int = 1) -> dict[str, Any]:
    """Traegt die Fahrt das Protokoll, aus dem die Segmentgrenzen kommen?

    Geprueft wird am LEISTUNGSSTROM, in dieser Reihenfolge, und der erste
    Befund gewinnt:
      Einrollen flach   Steigung in [0, Rampenbeginn) unter dem Anteil
      Ende sitzt        NUR wenn es ein Ausrollen gibt (letztes Fenster beim
                        Anteil unter dem hoechsten): Median kurz nach dem
                        Lastende beim Anteil unter dem davor - sonst zu kurz
                        oder zu lang
      Rampe steigt      Steigung in [Rampenbeginn, Lastende] mindestens der Anteil
      Ausrollen da      das letzte Fenster liegt beim Anteil unter dem hoechsten
    "Ende sitzt" vor der Rampe, weil ein verschobenes Ende das Rampenfenster
    verfaelscht. "Ausrollen da" nach der Rampe, weil eine Fahrt ohne Rampe
    auch kein Ausrollen hat - der wahre Satz ist dann "keine Rampe".

    Gibt IMMER einen Block zurueck: `code` None heisst traegt, sonst steht der
    Grund darin. Die gemessenen Zahlen stehen in beiden Faellen dabei.
    """
    step = max(1, int(sample_secs))
    first = (RAMP_WARMUP_MIN * 60) // step
    last = (length - 1) - (RAMP_COOLDOWN_MIN * 60) // step
    out: dict[str, Any] = {"code": None, "ramp_start_index": first, "load_end_index": last,
                           "warmup_w_per_min": None, "ramp_w_per_min": None,
                           "before_w": None, "after_w": None, "last_w": None, "top_w": None}

    def fail(code: str) -> dict[str, Any]:
        out["code"] = code
        out["reason"] = _reason(code, out)
        return out

    if not watts or not any((_number(v) or 0) > 0 for v in watts):
        return fail(NO_WATTS)
    if len(watts) != length:
        return fail(LENGTH_MISMATCH)
    if last <= first:
        return fail(TOO_SHORT)

    warm = _slope_per_min(watts, 0, first - 1, step)
    out["warmup_w_per_min"] = None if warm is None else round(warm, 2)
    ramp_slope = _slope_per_min(watts, first, last, step)
    out["ramp_w_per_min"] = None if ramp_slope is None else round(ramp_slope, 2)
    win = max(1, RAMP_END_CHECK_WINDOW_S // step)
    gap = max(1, RAMP_END_CHECK_GAP_S // step)
    before = _span_median(watts, last - gap - win + 1, last - gap)
    after = _span_median(watts, last + gap + 1, last + gap + win)
    tail = _span_median(watts, length - win, length - 1)
    windows = [_span_median(watts, i, i + win - 1) for i in range(0, length, win)]
    top = max((w for w in windows if w is not None), default=None)
    out.update({"before_w": before, "after_w": after, "last_w": tail, "top_w": top})

    limit = RAMP_PROTOCOL_SLOPE_SHARE * RAMP_STEP_W_PER_MIN
    cooled = tail is not None and top is not None and tail <= RAMP_COOLDOWN_MAX_SHARE * top
    if warm is None:
        return fail(WARMUP_NO_WATTS)
    if warm >= limit:
        return fail(WARMUP_NOT_FLAT)
    if cooled and (before is None or after is None or after > RAMP_COOLDOWN_MAX_SHARE * before):
        # Es GIBT ein Ausrollen, nur nicht an der Protokollstelle. Das kommt vor
        # der Rampensteigung: ein zu langes Ausrollen liegt sonst im
        # Rampenfenster und drueckt die Steigung - und der Satz "keine Rampe"
        # waere falsch. Liegt schon VOR dem Protokollende nur noch
        # Ausrollleistung an, ist es zu lang; sonst liegt danach noch Last an.
        if before is not None and before <= RAMP_COOLDOWN_MAX_SHARE * top:
            return fail(COOLDOWN_TOO_LONG)
        return fail(COOLDOWN_TOO_SHORT)
    if ramp_slope is None or ramp_slope < limit:
        return fail(RAMP_NOT_RISING)
    if not cooled:
        return fail(COOLDOWN_MISSING)
    out["reason"] = ""
    return out


def _peak(smooth: list[float | None], first: int, last: int) -> tuple[int, float] | None:
    """Der LETZTE Hochpunkt der geglaetteten Kurve in [first, last]."""
    window = [(i, smooth[i]) for i in range(max(0, first), min(len(smooth), last + 1))
              if smooth[i] is not None]
    if not window:
        return None
    peak = max(v for _, v in window)
    return max(i for i, v in window if v == peak), peak


def segment(dfa: list[Any] | None, first_index: int, last_index: int,
            sample_secs: int = 1) -> dict[str, Any] | None:
    """Der Abfall nach Rechenweg e1: vom letzten Hochpunkt ab `first_index`
    (Rampenbeginn) bis `last_index` (Lastende).

    Die Grenzen kommen aus dem Protokoll und werden hier NICHT gesucht - siehe
    protocol(). Gibt None zurueck, wenn es keinen brauchbaren Abfall gibt.
    """
    values = _clean(dfa)
    step = max(1, int(sample_secs))
    last_index = min(last_index, len(values) - 1)
    smooth = _smooth(values, max(1, RAMP_SMOOTH_S // step))
    found = _peak(smooth, first_index, last_index)
    if found is None:
        return None
    start, peak = found
    if start >= last_index:
        return None
    points = sum(1 for v in values[start:last_index + 1] if v is not None)
    if points < RAMP_MIN_POINTS // step:
        return None

    # Boden erreicht: die geglaettete Kurve bleibt IM SEGMENT fuer RAMP_FLAT_S
    # unter 0,5. Das beendet das Segment nicht mehr - es ist nur die Bedingung,
    # unter der HRVT2 genannt wird.
    flat_needed = max(1, RAMP_FLAT_S // step)
    reached = False
    run = 0
    for index in range(start, last_index + 1):
        value = smooth[index]
        if value is None:
            continue
        run = run + 1 if value < DFA_ANAEROBIC else 0
        if run >= flat_needed:
            reached = True
            break
    return {"start_index": start, "end_index": last_index, "max_alpha_start": round(peak, 3),
            "points": points, "reached_anaerobic": reached}


def _fit(values: list[float | None], start: int, end: int, step: int) -> dict[str, float] | None:
    """Gerade durch den Abfall, auf den UNGEGLAETTETEN Werten, gegen die ZEIT."""
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


def measure(dfa: list[Any] | None, watts: list[Any] | None = None,
            heartrate: list[Any] | None = None,
            sample_secs: int = 1) -> dict[str, Any]:
    """Die Auswertung MIT Grund: {"result", "code", "reason", "protocol"}.

    `result` None heisst: keine Zahlen, und `reason` sagt als Satz, warum.
    Erwartet den UNGEDUENNTEN Strom. Der Panel-Endpunkt deckelt bei 900
    Punkten - das sind 7 bis 18 Sekunden je Probe, und eine Gerade durch den
    Abfall staende dann auf rund hundert Punkten statt auf tausenden.
    """
    step = max(1, int(sample_secs))
    length = len(dfa or [])
    proto = protocol(length, watts, step)

    def none(code: str) -> dict[str, Any]:
        reason = proto.get("reason") if code == proto.get("code") else _reason(code, proto)
        return {"result": None, "code": code, "reason": reason, "protocol": proto}

    if proto["code"] is not None:
        return none(proto["code"])
    first, last = proto["ramp_start_index"], proto["load_end_index"]
    values = _clean(dfa)
    if not any(values[i] is not None for i in range(first, last + 1)):
        return none(NO_ALPHA)
    seg = segment(dfa, first, last, step)
    if seg is None:
        found = _peak(_smooth(values, max(1, RAMP_SMOOTH_S // step)), first, last)
        return none(NO_FALL if found is None or found[0] >= last else TOO_FEW_POINTS)
    fit = _fit(values, seg["start_index"], seg["end_index"], step)
    if fit is None:
        return none(TOO_FEW_POINTS)

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
    if fit["slope"] >= 0:
        return none(NO_FALL)

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
        # Die Setzungen und Messwerte der Protokollpruefung, damit die Karte
        # sie nennen kann statt sie zu erfinden.
        "protocol": {"ramp_start_s": first * step, "load_end_s": last * step,
                     "warmup_w_per_min": proto["warmup_w_per_min"],
                     "ramp_w_per_min": proto["ramp_w_per_min"],
                     "before_w": proto["before_w"], "after_w": proto["after_w"],
                     "slope_share": RAMP_PROTOCOL_SLOPE_SHARE,
                     "cooldown_max_share": RAMP_COOLDOWN_MAX_SHARE},
    }
    # Die Erholung setzt am LASTENDE an (seit e1) - `back_above_s` zaehlt also
    # ab dem Ende der Belastung, nicht mehr ab dem ersten Lauf unter 0,5.
    out["recovery"] = recovery(dfa, seg["end_index"], sample_secs)
    return {"result": out, "code": None, "reason": "", "protocol": proto}


def evaluate(dfa: list[Any] | None, watts: list[Any] | None = None,
             heartrate: list[Any] | None = None,
             sample_secs: int = 1) -> dict[str, Any] | None:
    """Nur die Zahlen, ohne Grund - derselbe Weg wie measure(), kein zweiter."""
    return measure(dfa, watts, heartrate, sample_secs)["result"]


def recovery(dfa: list[Any] | None, from_index: int,
             sample_secs: int = 1) -> dict[str, Any] | None:
    """Was im Ausrollen passiert. KEINE Protokollgroesse, eigene Idee.

    Zwei Zahlen: der Wert am Ende der Fahrt, und wie lange es vom LASTENDE
    (seit Rechenweg e1; vorher: Ende des Abfalls am ersten Lauf unter 0,5)
    gedauert hat, bis die Kurve wieder ueber 0,5 lag und dort blieb.
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
