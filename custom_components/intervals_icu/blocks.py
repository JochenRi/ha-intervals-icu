"""Ein Wert je Block, aufgetragen über die Zeit (docs/ausbau.md Paket M).

ZWEI GRÖSSEN MIT VERSCHIEDENEN AUFGABEN, und sie werden nie vertauscht:

* Der ERSTE eingeschwungene Block ist die VERLAUFSGRÖSSE. Er misst den
  frischesten Zustand und ist über Wochen erstaunlich stabil (259/260 W).
  Steigt er bei gleichem alpha, ist das eine belegbare Verbesserung.
* Der MEDIAN über alle eingeschwungenen Blöcke ist die STEUERGRÖSSE. Er misst
  die Einheit statt den frischesten Moment. Eine Regelung auf dem ersten Block
  sieht dauerhaft den besten Wert und driftet nach oben - in der Simulation
  +12 % gegen tatsächlich +2 % (PROJEKTSTAND §7).

Der Unterschied ist PHYSIOLOGIE, keine Datenstörung: die Lap-Etiketten wurden
geprüft, der erste harte Block trägt auch bei gleicher Leistung und nach zwei
Minuten Verwerfen systematisch das höhere alpha.

DER REGELKREIS IST KEIN SPIEGEL. Gemessen werden zwei Dinge zugleich - die
Leistung UND das alpha dabei. Das alpha sagt, ob die Leistung gepasst hat; die
Zahl kann deshalb steigen, ohne dass die Vorgeschichte sie treibt. Und NICHTS
davon greift automatisch: gerechnet wird ein Vorschlag, entschieden wird am
Rad.
"""

from __future__ import annotations

from typing import Any

try:  # inside the package (Home Assistant)
    from . import derive
    from .const import (
        BLOCK_CORRIDORS,
        BLOCK_MIN_FOR_TREND,
        BLOCK_STEP_FAR_PCT,
        BLOCK_STEP_NEAR_PCT,
        BLOCK_WARMUP_DISCARD_S,
    )
except ImportError:  # standalone (test suite loads this file directly)
    import derive  # type: ignore[no-redef]
    from const import (  # type: ignore[no-redef]
        BLOCK_CORRIDORS,
        BLOCK_MIN_FOR_TREND,
        BLOCK_STEP_FAR_PCT,
        BLOCK_STEP_NEAR_PCT,
        BLOCK_WARMUP_DISCARD_S,
    )


def family_of(name: str | None) -> str | None:
    """Zu welcher Familie gehört eine Einheit? Aus ihrem NAMEN.

    Der Athlet benennt seine Einheiten nach dem, was er fährt. Eine Erkennung
    aus der Blockstruktur wäre eine zweite Wahrheit - und sie hielte eine
    abgebrochene VO2max-Einheit für etwas anderes als eine ganze.
    """
    low = str(name or "").lower()
    if "sweetspot" in low or "sweet spot" in low:
        return "sweetspot"
    if "vo2" in low:
        return "vo2max"
    if "tempo" in low:
        return "tempo"
    return None


def _sessions(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Je Einheit: die eingeschwungenen Arbeitsblöcke, ihre Zahlen."""
    out: list[dict[str, Any]] = []
    for key, activity in (data.get("activities") or {}).items():
        family = family_of(activity.get("name"))
        if family is None:
            continue
        summary = (data.get("dfa") or {}).get(key) or {}
        work = [b for b in (summary.get("blocks") or []) if b.get("label") == "WORK"]
        if not work:
            continue
        alphas = [float(b["alpha"]) for b in work if b.get("alpha") is not None]
        powers = [float(b["watts"]) for b in work if b.get("watts")]
        if not alphas or not powers:
            continue
        out.append({
            "activity_id": key,
            "date": str(activity.get("start_date_local") or "")[:10],
            "name": activity.get("name"),
            "family": family,
            "n_blocks": len(work),
            # Die EINZELWERTE reisen mit: die Karte soll zeigen, worauf die
            # Steuerung ruht, statt eine geglättete Zahl zu drucken.
            "block_alphas": [b.get("alpha") for b in work],
            "block_watts": [b.get("watts") for b in work],
            "first_alpha": work[0].get("alpha"),
            "first_watts": work[0].get("watts"),
            "median_alpha": round(derive._median(alphas), 3),
            "median_watts": round(derive._median(powers)),
            "alpha_span": round(max(alphas) - min(alphas), 3),
        })
    out.sort(key=lambda row: row["date"])
    return out


def _spread(values: list[float]) -> float:
    """Die übliche Schwankung DERSELBEN Familie - die Schrittgrenze folgt ihr.

    Sie wird nicht gesetzt: eine Abweichung, die kleiner ist als die übliche
    Schwankung, ist keine Abweichung. Deshalb ist die Grenze bei jeder Familie
    eine andere.
    """
    if len(values) < 2:
        return 0.1
    mean = sum(values) / len(values)
    return max((sum((x - mean) ** 2 for x in values) / len(values)) ** 0.5, 0.02)


def suggest_step(alpha: float, corridor: tuple[float, float], spread: float) -> dict[str, Any]:
    """Ein Vorschlag, keine Anweisung. Nach oben wie nach unten."""
    low, high = corridor
    if alpha > high:
        gap = alpha - high
        pct = BLOCK_STEP_FAR_PCT if gap >= spread else BLOCK_STEP_NEAR_PCT
        where = "above"
    elif alpha < low:
        gap = low - alpha
        pct = -(BLOCK_STEP_FAR_PCT if gap >= spread else BLOCK_STEP_NEAR_PCT)
        where = "below"
    else:
        return {"pct": 0, "gap": 0.0, "where": "inside"}
    return {"pct": pct, "gap": round(gap, 3), "where": where}


def series(data: dict[str, Any]) -> dict[str, Any]:
    """Der Verlauf je Familie, die Steuergröße und der Vorschlag."""
    sessions = _sessions(data)
    families: dict[str, Any] = {}
    for family, corridor in BLOCK_CORRIDORS.items():
        rows = [s for s in sessions if s["family"] == family]
        if not rows:
            continue
        spread = round(_spread([r["median_alpha"] for r in rows]), 3)
        points = []
        for row in rows:
            step = suggest_step(row["median_alpha"], corridor, spread)
            points.append({
                "date": row["date"], "name": row["name"],
                "n_blocks": row["n_blocks"],
                "block_alphas": row["block_alphas"], "block_watts": row["block_watts"],
                "alpha_span": row["alpha_span"],
                # Verlaufsgröße
                "first_alpha": row["first_alpha"], "first_watts": row["first_watts"],
                # Steuergröße
                "median_alpha": row["median_alpha"], "median_watts": row["median_watts"],
                "step_pct": step["pct"], "step_gap": step["gap"], "step_where": step["where"],
                "suggested_watts": round(row["median_watts"] * (1 + step["pct"] / 100.0)),
            })
        newest = points[-1]
        families[family] = {
            "corridor": list(corridor),
            "sessions": len(points),
            "spread": spread,
            # Die Linie wird NUR gezeichnet, wenn sie getragen wird. Zwei Punkte
            # sind kein Verlauf, und eine Linie durch drei ist die 0.13.0-Falle.
            "trend": len(points) >= BLOCK_MIN_FOR_TREND,
            "min_for_trend": BLOCK_MIN_FOR_TREND,
            "points": points,
            "latest": newest,
            # Der Verlauf der VERLAUFSGRÖSSE - die Zahl, an der sich Fortschritt
            # zeigt: dieselbe Leistung bei gleichem alpha bedeutet nichts,
            # MEHR Leistung bei gleichem alpha ist die Verbesserung.
            "first_block_watts": [p["first_watts"] for p in points],
        }
    return {
        "families": families,
        "discarded_s": BLOCK_WARMUP_DISCARD_S,
        "step_near_pct": BLOCK_STEP_NEAR_PCT,
        "step_far_pct": BLOCK_STEP_FAR_PCT,
        # Die Grenze, und sie steht in jeder Karte: gemessen wurde auf der
        # Rolle, in eigenen Einheiten, bei fester Blockstruktur. DERSELBE
        # alpha-Wert bedeutet draußen eine andere Leistung - am eigenen Bestand
        # liegen zwischen beiden Zusammenhängen 40 W (PROJEKTSTAND §7).
        "scope": "rolle",
    }
