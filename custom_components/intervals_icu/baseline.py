"""DIE BASISLINIE - ein Erzeuger fuer Trainer, Ampel und Signale (S1, 0.69.0).

Bis 0.68.0 gab es drei HRV-Basislinien im Paket (Karte 4b, F4b.3): der
Trainer (`coach.state`) rechnete 60 Naechte VOR heute, gewichtet ueber die
Tagesetiketten; die Ampel (`analytics.hrv_status`) Mittel und Streuung der
letzten 60 ROLLWERTE einschliesslich heute, ungewichtet; die Signale
(`coach.signals`) ein Fenster vor dem Tag, ungewichtet. Alle drei standen mit
"+-0,5 SD" beschriftet, und die Belastung konnte "im Normalbereich" sagen,
waehrend der Trainer "beansprucht" zeigte. Entscheidung 25.09. (Wahl 1): alle
drei gewichtet, ein Rechenweg, Fensterlage VOR dem beurteilten Tag - die
Nacht, die beurteilt wird, gehoert nicht in ihre eigene Basislinie.

Was hier steht, ist der Rechenweg. Die Gewichte kommen aus `day_context`
(Etiketten, eine SETZUNG - siehe dort); die Ebene-3-Regel bleibt fuer die
LAST: ACWR, Monotonie und Budget lesen keine Gewichte.
"""
from __future__ import annotations

import math
from statistics import mean, pstdev
from typing import Any, NamedTuple

try:  # inside the package (Home Assistant)
    from . import day_context
except ImportError:  # standalone (test suite loads this file directly)
    import day_context  # type: ignore[no-redef]

# Unter so vielen Naechten sagt ein Band nichts (Setzung, seit B3).
MIN_VALUES = 20
# Das Fenster der Basislinie: so viele Naechte vor dem beurteilten Tag.
WINDOW = 60


class Band(NamedTuple):
    """A baseline with its provenance, so a fallback can say WHY."""

    base: float
    spread: float
    weighted: bool     # the sum-of-weights rule allowed weighting
    weight_sum: float  # effective days in the window
    labeled: int       # usable values carrying a weight below 1


def _plain(values: list[float]) -> tuple[float, float]:
    if not values:
        return (0.0, 0.0)
    return (mean(values), pstdev(values) if len(values) > 1 else 0.0)


def norm_band(raw: list[float], *, log: bool,
              weights: list[float] | None = None) -> Band | None:
    """THE baseline of a wellness signal - the only place it is computed.

    The weighting rule (docs/ausbau.md B3, level 1 - a STIPULATION):
    weighted mean and spread when at least one day carries a weight below 1
    and the weight sum reaches day_context.MIN_WEIGHT_SUM; otherwise the
    plain band over the same values. An archive without labels is
    BIT-IDENTICAL to the unweighted world. A flat history (spread 0) is no
    band: a distance in "standard deviations" from nothing is not a number.

    Returns the Band on the (possibly log) scale, or None when the history
    is too thin to mean anything.
    """
    if weights is None:
        weights = [1.0] * len(raw)
    pairs = list(zip(raw, weights))
    if log:
        pairs = [(math.log(v), w) for v, w in pairs if v > 0]
    if len(pairs) < MIN_VALUES:
        return None
    values = [v for v, _w in pairs]
    weight_sum = sum(w for _v, w in pairs)
    labeled = sum(1 for _v, w in pairs if w < 1.0)
    if labeled and weight_sum >= day_context.MIN_WEIGHT_SUM:
        base = sum(v * w for v, w in pairs) / weight_sum
        spread = math.sqrt(sum(w * (v - base) ** 2 for v, w in pairs) / weight_sum)
        is_weighted = True
    else:
        base, spread = _plain(values)
        is_weighted = False
    if spread <= 0:
        return None
    return Band(base, spread, is_weighted, round(weight_sum, 2), labeled)


def z_at(value: float | None, band: Band | None, *,
         log: bool, sign: int = 1) -> float | None:
    """A value's distance from its band, on the band's own scale."""
    if value is None or band is None:
        return None
    if log:
        if value <= 0:
            return None
        value = math.log(value)
    return sign * (value - band.base) / band.spread


def fallback_note(band: Band | None) -> str | None:
    """Says WHAT is missing when the weighted baseline is not usable yet."""
    if band is None or band.weighted or band.labeled == 0:
        return None
    have = f"{band.weight_sum:.1f}".replace(".", ",").removesuffix(",0")
    days = "Tag ist" if band.labeled == 1 else "Tage sind"
    return (f"Basislinie auf ungewichtet zurückgefallen — nur {have} belastbare "
            f"Tage von {int(day_context.MIN_WEIGHT_SUM)} nötigen, "
            f"{band.labeled} {days} etikettiert")


def band_before(data: dict[str, Any], values: dict[str, float], day: str, *,
                log: bool, window: int = WINDOW) -> Band | None:
    """Das Band der `window` Naechte VOR `day`, gewichtet ueber day_context."""
    history = [d for d in sorted(values) if d < day][-window:]
    return norm_band([values[d] for d in history], log=log,
                     weights=[day_context.weight_for(data, d) for d in history])


def z_series(values: dict[str, float], days: list[str], window: int = WINDOW,
             log: bool = False, sign: int = 1,
             weights: dict[str, float] | None = None) -> dict[str, float]:
    """Distance from a trailing baseline, in standard deviations, day by day.

    The baseline trails the day it judges, so today is never part of its own
    normal - otherwise a slow drift would erase itself.
    """
    out: dict[str, float] = {}
    ordered = [d for d in days if d in values]
    for index, day in enumerate(ordered):
        history = ordered[max(0, index - window):index]
        band = norm_band([values[d] for d in history], log=log,
                         weights=[(weights or {}).get(d, 1.0) for d in history])
        z = z_at(values[day], band, log=log, sign=sign)
        if z is not None:
            out[day] = z
    return out


def weights_for(data: dict[str, Any], days: list[str]) -> dict[str, float]:
    """Die Gewichte aller Tage - ein Aufruf statt vier."""
    return {d: day_context.weight_for(data, d) for d in days}
