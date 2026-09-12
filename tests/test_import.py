"""Full import simulation against a replay of the live account's shapes."""

import asyncio
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

# Load the two Home-Assistant-free modules as a tiny package, so their
# relative imports work without pulling Home Assistant into the test run.
import importlib.util  # noqa: E402
import types  # noqa: E402

COMP = Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu"
_pkg = types.ModuleType("iv")
_pkg.__path__ = [str(COMP)]
sys.modules["iv"] = _pkg


def _load(name):
    spec = importlib.util.spec_from_file_location(f"iv.{name}", COMP / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"iv.{name}"] = module
    spec.loader.exec_module(module)
    return module


derive = _load("derive")
importer = _load("importer")

failures = []
CHECKS = 0


def check(label, got, expected):
    global CHECKS
    CHECKS += 1
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}  {label}: {got!r}" + ("" if ok else f"  (erwartet {expected!r})"))
    if not ok:
        failures.append(label)


# --- replay of the real account ------------------------------------------------
# 498 wellness days (2025-05-01 .. 2026-09-10), 250 activities of which 8 are
# Strava placeholders, streams at 1 Hz with a leading 0.0 artefact and coasting
# zeros in the power channel - all of that measured on the live account.
START = date(2025, 5, 1)
END = date(2026, 9, 10)
random.seed(11)


_WELLNESS_CACHE: dict[str, dict] = {}


def _wellness_rows(oldest, newest):
    if _WELLNESS_CACHE:
        return [row for day, row in sorted(_WELLNESS_CACHE.items())
                if oldest.isoformat() <= day <= newest.isoformat()]
    rows = []
    day = oldest
    ctl = 20.0
    while day <= newest:
        load = random.choice([0, 0, 0, 40, 60, 93, 129])
        ctl += (load - ctl) / 42
        atl = ctl * random.uniform(0.6, 1.3)
        rows.append({
            "id": day.isoformat(), "ctl": round(ctl, 4), "atl": round(atl, 4),
            "ctlLoad": float(load), "restingHR": random.randint(50, 62),
            "hrv": float(random.randint(30, 65)), "sleepSecs": random.randint(20000, 39000),
            "weight": None, "vo2max": 49.0 if load else None,
            "sportInfo": [{"type": "Ride", "eftp": 192.0, "wPrime": 13400.0, "pMax": 890.0}],
            "updated": f"{day.isoformat()}T22:00:00.000+00:00",
            "tempWeight": bool(load), "tempRestingHR": False,
        })
        day += timedelta(days=1)
    _WELLNESS_CACHE.update({row["id"]: row for row in rows})
    return [row for day, row in sorted(_WELLNESS_CACHE.items())
            if oldest.isoformat() <= day <= newest.isoformat()]


_ACTIVITY_CACHE: list[dict] = []


def _activities():
    if _ACTIVITY_CACHE:
        return _ACTIVITY_CACHE
    items = []
    day = END
    for index in range(250):
        if index < 8:  # the oldest eight came in through Strava
            items.append({
                "id": f"1436423028{index}", "icu_athlete_id": "i123456",
                "start_date_local": (START + timedelta(days=index)).isoformat() + "T15:52:02",
                "source": "STRAVA",
                "_note": "STRAVA activities are not available via the API",
            })
            continue
        sport = random.choice(["Ride", "Ride", "Ride", "Walk", "Run"])
        streams = ["time", "heartrate", "dfa_a1"] + (["watts"] if sport == "Ride" else [])
        items.append({
            "id": f"i18{400000 + index}", "start_date_local": (day - timedelta(days=index)).isoformat() + "T11:07:27",
            "type": sport, "name": f"{sport} {index}", "source": "GARMIN_CONNECT",
            "icu_training_load": random.randint(9, 140), "moving_time": random.randint(2400, 12000),
            "distance": random.uniform(4000, 90000), "average_heartrate": random.randint(90, 155),
            "max_heartrate": random.randint(120, 180), "calories": random.randint(200, 2200),
            "icu_ctl": 35.0, "icu_atl": 30.0, "stream_types": streams,
            "icu_hr_zone_times": [4089, 0, 0, 0, 0, 0, 0],
        })
    _ACTIVITY_CACHE.extend(items)
    return items


def _streams(activity_id, types):
    """A 1 Hz stream set with the artefacts seen in the real data."""
    n = 3600
    dfa = [0.0] + [round(random.uniform(0.9, 1.6), 4) for _ in range(n - 1)]
    dfa[1000:1100] = [round(random.uniform(0.70, 0.80), 4) for _ in range(100)]
    dfa[2000:2200] = [round(random.uniform(0.2, 0.49), 4) for _ in range(200)]
    hr = [random.randint(120, 170) for _ in range(n)]
    watts = [random.choice([0, 0, 120, 150, 190, 210]) for _ in range(n)]
    out = []
    for name, values in (("dfa_a1", dfa), ("heartrate", hr), ("watts", watts)):
        if name in types:
            out.append({"type": name, "data": values})
    return out


class FakeClient:
    """Counts every request so the rate budget can be judged."""

    def __init__(self):
        self.calls = {"wellness": 0, "activities": 0, "streams": 0}

    async def async_get_wellness(self, oldest, newest):
        self.calls["wellness"] += 1
        return _wellness_rows(oldest, newest)

    async def async_get_activities(self, oldest, newest, fields=None):
        self.calls["activities"] += 1
        assert fields, "fields= muss gesetzt sein, sonst kommen 200 Felder pro Aktivitaet"
        return [
            item for item in _activities()
            if oldest.isoformat() <= str(item["start_date_local"])[:10] <= newest.isoformat()
        ]

    async def async_get_streams(self, activity_id, types):
        self.calls["streams"] += 1
        if activity_id.endswith("099"):       # one activity always fails
            raise RuntimeError("boom")
        return _streams(activity_id, types)


async def main():
    client = FakeClient()
    data = importer.empty_data("i123456")

    # --- first full import ----------------------------------------------------
    check("Marker vor dem Import", importer.should_full_import(data), True)
    days = await importer.async_import_wellness(client, data, START, END)
    acts = await importer.async_import_activities(client, data, START, END)
    check("Wellness-Tage importiert", days, 498)
    check("Aktivitaeten importiert", acts, 242)
    check("Strava-Platzhalter aussortiert", len(data["unavailable"]), 8)
    check("Anfragen fuer den Grundbestand", client.calls["wellness"] + client.calls["activities"], 2)
    data["full_import_done"] = True

    # --- the full-import marker must not depend on call order -----------------
    # 0.3.0 decided "is the archive empty?" AFTER the first refresh had already
    # written the recent window into it - so the full history import never ran.
    fresh = importer.empty_data("i123456")
    check("frisches Archiv verlangt Vollimport", importer.should_full_import(fresh), True)
    importer.merge_wellness(fresh, _wellness_rows(END - timedelta(days=30), END))
    check("Teilbefuellung hebt den Vollimport NICHT auf",
          importer.should_full_import(fresh), True)
    fresh["full_import_done"] = True
    check("nach Vollimport kein zweiter", importer.should_full_import(fresh), False)
    check("Bestandsarchiv nach Vollimport erledigt",
          importer.should_full_import(data), False)

    # --- second run must not duplicate anything -------------------------------
    again = await importer.async_import_wellness(client, data, END - timedelta(days=30), END)
    again += await importer.async_import_activities(client, data, END - timedelta(days=30), END)
    check("Wiederholter Lauf aendert nichts", again, 0)
    check("Wellness-Tage unveraendert", len(data["wellness"]), 498)

    # --- DFA in batches --------------------------------------------------------
    pending = importer.pending_dfa(data)
    check("Einheiten mit DFA-Stream", len(pending), 242)

    first = await importer.async_import_dfa(client, data, limit=25)
    check("erster Stapel", first, 25)
    check("Reststapel", len(importer.pending_dfa(data)), 217)

    while importer.pending_dfa(data):
        await importer.async_import_dfa(client, data, limit=50)
    check("alle DFA-Auswertungen da", len(data["dfa"]), 242)
    check("Stream-Anfragen gesamt", client.calls["streams"], 242)


    sample = next(v for v in data["dfa"].values() if v)
    check("Artefakt verworfen", sample["samples"], 3599)
    check("anaerobe Sekunden erkannt", sample["secs_anaerobic"], 200)
    check("Schwellen-HF vorhanden", isinstance(sample["hr_at_threshold"], float), True)

    # --- an algorithm change must reach the stored summaries ---------------------
    # The streams are not kept, so a fixed calculation would never touch values
    # already in the archive unless they are dropped and fetched again.
    check("gleiche Version wirft nichts weg", importer.drop_outdated_dfa(data), 0)
    data["dfa_version"] = 1
    check("aeltere Version wird verworfen", importer.drop_outdated_dfa(data), 242)
    check("Auswertungen wieder offen", len(importer.pending_dfa(data)), 242)
    check("Version nachgezogen", data["dfa_version"], importer.DFA_ALGO_VERSION)
    await importer.async_import_dfa(client, data)
    check("neu berechnet", len(data["dfa"]), 242)

    # --- series for the panel ---------------------------------------------------
    pmc = importer.pmc_series(data)
    check("PMC-Reihe Laenge", len(pmc), 498)
    check("PMC beginnt am Anfang", pmc[0]["date"], "2025-05-01")
    check("Form = CTL - ATL", round(pmc[-1]["form"], 4),
          round(pmc[-1]["ctl"] - pmc[-1]["atl"], 4))

    liste = importer.activity_list(data, limit=10)
    check("Liste neueste zuerst", liste[0]["start_date_local"] > liste[-1]["start_date_local"], True)
    check("DFA an der Aktivitaet", liste[0]["dfa"] is not None, True)

    schwellen = importer.threshold_series(data)
    check("Schwellenreihe gefuellt", len(schwellen) > 200, True)
    check("Schwellenreihe chronologisch", schwellen[0]["date"] <= schwellen[-1]["date"], True)

    # --- size on disk ------------------------------------------------------------
    raw = json.dumps(data)
    kb = len(raw.encode()) / 1024
    print(f"\n  Archivgroesse: {kb:.0f} kB  ({len(data['activities'])} Aktivitaeten, "
          f"{len(data['wellness'])} Wellness-Tage, {len(data['dfa'])} DFA-Auswertungen)")
    check("Archiv bleibt unter 2 MB", kb < 2048, True)

    stats = importer.archive_stats(data)
    check("Statistik: offene DFA", stats["dfa_pending"], 0)
    check("Statistik: nicht abrufbar", stats["unavailable"], 8)

    # --- threshold series: the join key and the session's own numbers --------
    # The DFA tab keys its selection on the activity_id, jumps into the
    # activity with it, and shows the session's duration/load/HR next to the
    # reading. All of that has to arrive with the reading itself.
    series = importer.threshold_series(data)
    check("Schwellenreihe: nicht leer", bool(series), True)
    keys = set(data["activities"])
    check("Schwellenreihe: activity_id trifft den Archivschlüssel",
          all(row.get("activity_id") in keys for row in series), True)
    check("Schwellenreihe: aufsteigend nach Datum",
          [r["date"] for r in series] == sorted(r["date"] for r in series), True)
    for field in ("name", "moving_time", "load", "avg_hr", "decoupling"):
        check(f"Schwellenreihe: Feld {field} vorhanden",
              all(field in row for row in series), True)
    joined = [r for r in series
              if r.get("moving_time") == (data["activities"][r["activity_id"]] or {}).get("moving_time")]
    check("Schwellenreihe: Dauer stammt aus derselben Aktivität",
          len(joined), len(series))

    # since is an inclusive lower bound with NO upper bound: a reading dated
    # in the future (watch with a wrong clock) must not vanish silently
    if series:
        cut = series[len(series) // 2]["date"]
        later = importer.threshold_series(data, since=cut)
        check("Schwellenreihe: since schneidet unten ab",
              all(row["date"] >= cut for row in later), True)
        check("Schwellenreihe: since behält alles ab dem Stichtag",
              len(later), len([r for r in series if r["date"] >= cut]))
        check("Schwellenreihe: since=None ändert nichts",
              importer.threshold_series(data, since=None) == series, True)

    # --- day_context (Paket B2): das Grundgerüst kennt den Block ------------
    # 0.35.0-Lehre: async_load füllt fehlende Schlüssel nur auf der obersten
    # Ebene auf. Ein Block, den empty_data() nicht kennt, entsteht bei
    # Altbeständen NIE - deshalb hängt der Vertrag hier am Grundgerüst.
    day_context = _load("day_context")
    check("day_context im Grundgerüst", importer.empty_data("x").get("day_context"), {})
    legacy = importer.empty_data("x")
    del legacy["day_context"]  # ein Archiv aus 0.36.1
    base = importer.empty_data("x")
    base.update(legacy)  # exakt der async_load-Füllweg
    check("Altbestand ohne day_context lädt mit leerem Block",
          base.get("day_context"), {})
    check("Altbestand: Migration meldet nichts zu tun",
          day_context.migrate(base["day_context"]), None)
    # Normalisierung: kaputte Einträge werden geklemmt statt Basislinien zu
    # vergiften; ein UNBEKANNTES Etikett mit gültigem Gewicht überlebt
    # (Downgrade-Schutz), Müll fliegt raus, krank bekommt sein Vorgabegewicht.
    broken = {"2026-09-01": {"tag": "krank"},
              "kaputt": 1,
              "2026-09-02": "kein-dict",
              "2026-09-03": {"tag": "zukunft", "weight": 0.25},
              "2026-09-04": {"tag": "alkohol", "weight": 7.0}}
    repaired = day_context.migrate(broken)
    check("Migration: krank bekommt Vorgabegewicht 0,0",
          repaired.get("2026-09-01", {}).get("weight"), 0.0)
    check("Migration: ungültiger Datumsschlüssel entfernt", "kaputt" in repaired, False)
    check("Migration: Nicht-dict-Eintrag entfernt", "2026-09-02" in repaired, False)
    check("Migration: unbekanntes Etikett mit gültigem Gewicht überlebt",
          repaired.get("2026-09-03", {}).get("weight"), 0.25)
    check("Migration: Gewicht außerhalb 0-1 fällt auf die Etikett-Vorgabe",
          repaired.get("2026-09-04", {}).get("weight"), 0.5)
    check("Migration: reparierter Block wird beim zweiten Lauf nicht erneut migriert",
          day_context.migrate(repaired), None)
    store_src = (COMP / "store.py").read_text(encoding="utf-8")
    check("store.async_load ruft die day_context-Migration",
          "day_context.migrate" in store_src, True)

    print()
    print(f"test_import: {CHECKS} Prüfungen, {len(failures)} Fehler")
    print("FEHLER:", failures if failures else "keine")
    return 1 if failures else 0


sys.exit(asyncio.run(main()))
