"""Die Ermuedungskurve: der Ausschluss VOR der Messung, und die Grenzen aus
der Belegung. Lauf: python3 tests/test_fatigue.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu"))

import derive  # noqa: E402
import fatigue  # noqa: E402
from const import FATIGUE_SOLID_MIN_RIDES, FATIGUE_THIN_MIN_RIDES  # noqa: E402

failures = []
CHECKS = 0


def check(label, got, expected):
    global CHECKS
    CHECKS += 1
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}  {label}: {got!r}" + ("" if ok else f"  (erwartet {expected!r})"))
    if not ok:
        failures.append(label)


def ok(label, condition):
    check(label, bool(condition), True)


# --- Baukasten ----------------------------------------------------------------
def zones(low, mid, high):
    """icu_zone_times in der Form, die Intervals liefert - inkl. SS-Ueberlappung."""
    return [{"id": "Z1", "secs": low}, {"id": "Z2", "secs": mid}, {"id": "Z3", "secs": high},
            {"id": "Z4", "secs": 0}, {"id": "Z5", "secs": 0}, {"id": "Z6", "secs": 0},
            {"id": "Z7", "secs": 0}, {"id": "SS", "secs": high}]


def ride_streams(levels, spread=0.35, base_alpha=0.60):
    """Ein Strom je Stunde: dieselbe alpha-Lage, aber je Stunde anderes Niveau.

    Die Leistung haengt linear an alpha, sodass P(0,75) exakt dem uebergebenen
    Niveau entspricht - der Test prueft die RECHENVORSCHRIFT, nicht eine Zahl
    aus einer fruehen Messrunde.
    """
    dfa, watts = [], []
    for level in levels:
        for i in range(3600):
            alpha = base_alpha + (i % 400) / 400 * spread
            dfa.append(round(alpha, 3))
            watts.append(level - (alpha - 0.75) * 120)
    return dfa, watts


def bestand(entries):
    """entries: (id, datum, name, stundenniveaus, zonen, minuten)"""
    data = {"activities": {}, "dfa": {}}
    for key, day, name, levels, zone_times, minutes in entries:
        data["activities"][key] = {
            "start_date_local": f"{day}T09:00:00", "name": name, "type": "Ride",
            "moving_time": minutes * 60, "icu_zone_times": zone_times,
            "icu_average_watts": 150, "icu_weighted_avg_watts": 155,
        }
        dfa, watts = ride_streams(levels)
        data["dfa"][key] = {"hours": derive.dfa_hours(dfa, watts)}
    return data


VOLUMEN = zones(3000, 4000, 200)        # 3,1 % ueber Zone 2
STRUKTUR = zones(1000, 1200, 1400)      # 38,9 % ueber Zone 2

print("=== die Falle aus L0 Runde 3: strukturierte Einheiten VORHER ausschliessen ===")

# Acht Volumenfahrten mit einem ECHTEN, kleinen Abfall: 160 -> 156 W.
volumen = [(f"v{i}", f"2026-08-{i + 1:02d}", "volumen", [160, 156], VOLUMEN, 130)
           for i in range(8)]
# Und eine strukturierte Einheit, die den Trainingsplan traegt statt Ermuedung:
# der Block liegt in Stunde 1, danach wird ausgefahren. Genau die Bauart der
# drei SweetSpot-Rollenfahrten vom 14./20./24.08.2026.
strukturiert = [("s1", "2026-08-20", "SweetSpot 2x20Min", [200, 120], STRUKTUR, 130)]

sauber = fatigue.curve(bestand(volumen))
mit_stoerer = fatigue.curve(bestand(volumen + strukturiert))

check("Ausschluss: die strukturierte Einheit zaehlt nicht mit",
      mit_stoerer["rides_used"], sauber["rides_used"])
check("Ausschluss: sie erscheint als 'structured'",
      [row["name"] for row in mit_stoerer["dropped"].get("structured", [])],
      ["SweetSpot 2x20Min"])
check("Ausschluss: mit ihrem Zahlenwert daneben",
      mit_stoerer["dropped"]["structured"][0]["above_z2"], 38.9)
check("Ausschluss: der gemessene Verlauf bleibt unveraendert",
      [(r["hour"], r["watts"], r["n"]) for r in mit_stoerer["measured"]],
      [(r["hour"], r["watts"], r["n"]) for r in sauber["measured"]])

abfall_sauber = sauber["measured"][0]["watts"] - sauber["measured"][1]["watts"]

# DIE GEGENPROBE, GEZAEHLT UND BENANNT. Ohne sie wuerde oben nur belegt, dass
# zwei gleiche Ergebnisse gleich sind - nicht, dass der Ausschluss etwas
# verhindert. Also dieselben Fahrten noch einmal, aber als Volumen GETARNT:
# ihre Zonen sagen "Grundlage", ihr Verlauf ist derselbe Trainingsplan.
#
# UND SIE BRAUCHEN GEWICHT. Eine einzelne strukturierte Einheit unter acht
# Volumenfahrten bewegt den Median nicht - eine erste Fassung dieser
# Gegenprobe ist daran gescheitert und war damit stumpf. Das ist kein Grund,
# den Ausschluss fuer entbehrlich zu halten, sondern die Praezisierung:
# DER MEDIAN DAEMPFT, ER RETTET NICHT. Bei diesem Athleten sind Rollen-
# SweetSpots und VO2max-Einheiten keine Ausreisser, sondern die Haelfte des
# Trainings - und genau bei dieser Paritaet kippt er. Vier unter acht bewegen
# ihn noch nicht; acht unter acht schieben ihn in die Mitte zwischen beide
# Populationen, und die Mitte ist keine von beiden.
getarnt = [(f"g{i}", f"2026-09-{i + 1:02d}", "SweetSpot 2x20Min", [200, 120], VOLUMEN, 130)
           for i in range(8)]
verfaelscht = fatigue.curve(bestand(volumen + getarnt))
check("Gegenprobe: drin gelassen zaehlen sie mit",
      verfaelscht["rides_used"], sauber["rides_used"] + 8)
abfall_falsch = verfaelscht["measured"][0]["watts"] - verfaelscht["measured"][1]["watts"]
print(f"      Abfall Stunde 1 -> 2: sauber {abfall_sauber:+.1f} W, mit Stoerern {abfall_falsch:+.1f} W")
ok("Gegenprobe: die Stoerer VERFAELSCHEN den Abfall nachweislich",
   abfall_falsch > abfall_sauber + 1.0)
ok("Gegenprobe: und zwar nach oben - der Trainingsplan sieht aus wie Ermuedung",
   abfall_falsch >= 2 * abfall_sauber)
check("Ausschluss verhindert genau das", abfall_sauber, mit_stoerer["measured"][0]["watts"]
      - mit_stoerer["measured"][1]["watts"])

# Und der Befund selbst, als Zusicherung: EINE Stoerfahrt unter acht bewegt
# den Median nicht. Wer daraus schliesst, der Ausschluss sei entbehrlich,
# haelt die Daempfung fuer einen Schutz.
einzeln = fatigue.curve(bestand(volumen + [getarnt[0]]))
check("eine einzelne Stoerfahrt bewegt den Median NICHT",
      einzeln["measured"][0]["watts"] - einzeln["measured"][1]["watts"], abfall_sauber)

print("\n=== die Grenzen kommen aus der Belegung, nicht aus dem Code ===")

# Bestand A: viele kurze Fahrten. Bestand B: wenige, aber lange.
kurz = [(f"k{i}", f"2026-08-{i + 1:02d}", "volumen", [160, 156], VOLUMEN, 130)
        for i in range(12)]
lang = [(f"l{i}", f"2026-08-{i + 1:02d}", "volumen", [160, 156, 150, 146], VOLUMEN, 260)
        for i in range(12)]
a, b = fatigue.curve(bestand(kurz)), fatigue.curve(bestand(lang))
check("Bestand A: durchgezogen bis Stunde", a["solid_until_hour"], 2)
check("Bestand B: durchgezogen bis Stunde", b["solid_until_hour"], 4)
ok("ZWEI Bestaende, ZWEI Grenzen - die Schwellen sind nicht hartkodiert",
   a["solid_until_hour"] != b["solid_until_hour"])

# Und die Abstufung selbst: genau an der Mindestbelegung kippt der Bereich.
gemischt = ([(f"m{i}", f"2026-08-{i + 1:02d}", "volumen", [160, 156], VOLUMEN, 130)
             for i in range(FATIGUE_SOLID_MIN_RIDES)]
            + [(f"x{i}", f"2026-09-{i + 1:02d}", "volumen", [160, 156, 150], VOLUMEN, 190)
               for i in range(FATIGUE_THIN_MIN_RIDES)])
g = fatigue.curve(bestand(gemischt))
check("genau an der Mindestbelegung: durchgezogen", g["measured"][0]["band"], "solid")
check("knapp darunter: duenn", g["measured"][2]["band"], "thin")
check("und die duenne Stunde traegt ihre Zahl", g["measured"][2]["n"], FATIGUE_THIN_MIN_RIDES)

print("\n=== Anker gemessen, Form gesetzt - und getrennt gehalten ===")

check("der Anker ist der Median der ersten Stunde", a["anchor_watts"], 160.0)
check("und traegt seine Belegung", a["anchor_n"], 12)
ok("die Literaturkurve sitzt auf dem Anker",
   abs(a["literature"][0]["watts"] - a["anchor_watts"]) < 0.2)
ok("sie faellt monoton", all(
    a["literature"][i]["watts"] > a["literature"][i + 1]["watts"]
    for i in range(len(a["literature"]) - 1)))
ok("sie reicht ueber den Bestand hinaus - dort ist sie reine Setzung",
   max(row["t"] for row in a["literature"]) > max(row["t"] for row in a["measured"]))
check("jenseits des Bestands traegt sie KEINE Stundennummer aus der Messung",
      [row["hour"] for row in a["literature"] if row["t"] > 1.5][:1], [None])

# Die Form selbst, gegen die publizierte Probe: -5 % zwischen 119 und 140 min.
fuenf = next(m for m in range(60, 240)
             if fatigue.literature_factor(m / 60) <= 0.95)
print(f"      Literaturform erreicht -5 % nach {fuenf} min")
ok("Form: -5 % innerhalb der publizierten Sensitivitaetsspanne", 119 <= fuenf <= 140)
check("Form: bei t = 0 exakt 1,0", fatigue.literature_factor(0.0), 1.0)

# Der Anker skaliert die Form, ohne sie zu verformen.
doppelt = [(f"d{i}", f"2026-08-{i + 1:02d}", "volumen", [320, 312], VOLUMEN, 130)
           for i in range(12)]
d = fatigue.curve(bestand(doppelt))
check("doppelter Anker verdoppelt jeden Kurvenwert",
      [round(row["watts"] / 2, 1) for row in d["literature"]],
      [row["watts"] for row in a["literature"]])

print("\n=== L1b: die HF-Setzung, und die eigene Messung daneben ===")
mit_hr = fatigue.curve(bestand(kurz), aerobic_hr=160)
check("die Setzung haengt am EIGENEN Anker",
      mit_hr["hr_drift_expected"][0]["bpm"],
      round(160 * (1 + mit_hr["hr_drift_per_hour_pct"] / 100 * 0.5), 1))
ok("sie steigt mit der Dauer - Gegenrichtung zur Leistung",
   mit_hr["hr_drift_expected"][1]["bpm"] > mit_hr["hr_drift_expected"][0]["bpm"])
check("uebertragen wird der PROZENTSATZ, nicht Stevensons bpm",
      mit_hr["hr_drift_per_hour_pct"],
      round((fatigue.STEVENSON_HR_2H / fatigue.STEVENSON_HR_REST - 1) / 2 * 100, 2))
ohne_hr = fatigue.curve(bestand(kurz))
check("ohne eigenen Anker wird NICHTS hochgerechnet", ohne_hr["hr_drift_expected"], [])
# Ein doppelter Anker verdoppelt die Erwartung - die Setzung skaliert, sie
# verformt nicht.
check("doppelter HF-Anker verdoppelt die Erwartung",
      round(fatigue.curve(bestand(kurz), aerobic_hr=320)["hr_drift_expected"][0]["bpm"], 0),
      round(mit_hr["hr_drift_expected"][0]["bpm"] * 2, 0))

print("\n=== ein Bestand ohne Fahrt ueber einer Stunde sagt das ===")
kurzfahrt = [("q1", "2026-08-01", "Feierabendrunde", [160], VOLUMEN, 45)]
q = fatigue.curve(bestand(kurzfahrt))
check("keine gemessene Zeile", q["measured"], [])
check("kein Anker", q["anchor_watts"], None)
check("keine Literaturkurve ohne Anker", q["literature"], [])
check("und der Grund steht da", list(q["dropped"]), ["short"])

print(f"\ntest_fatigue: {CHECKS} Prüfungen, {len(failures)} Fehler")
print("FEHLER:", failures if failures else "keine")
sys.exit(1 if failures else 0)
