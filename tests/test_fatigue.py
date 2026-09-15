"""Die Ermuedungskurve: der Ausschluss VOR der Messung, und die Grenzen aus
der Belegung. Lauf: python3 tests/test_fatigue.py"""

import sys
from pathlib import Path

import coldcache  # noqa: F401  - MUSS vor jedem Bauteil-Import stehen (§9)
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
   abs(next(r for r in a["literature"] if r["hour"] == 1)["watts"] - a["anchor_watts"]) < 0.2)
ok("sie faellt monoton", all(
    a["literature"][i]["watts"] > a["literature"][i + 1]["watts"]
    for i in range(len(a["literature"]) - 1)))
ok("sie reicht ueber den Bestand hinaus - dort ist sie reine Setzung",
   max(row["t"] for row in a["literature"]) > max(row["t"] for row in a["measured"]))
check("jenseits des Bestands traegt sie KEINE Stundennummer aus der Messung",
      [row["hour"] for row in a["literature"] if row["t"] > 1.6][:1], [None])

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
ok("das Raster ist feiner als die Messstunden - der Zeiger rastet nicht ein",
   len(a["literature"]) > 3 * len(a["measured"]))

print("\n=== gepaart gegen ungepaart, und das Erkennungszeichen ===")

# Der Auswahleffekt, den die Live-Messung gezeigt hat, nachgebaut: Fahrten, die
# NUR eine zweite Stunde liefern (die lockeren erreichen die Schwelle erst,
# wenn alpha gesunken ist), stehen neben durchgaengigen Fahrten. Ungepaart
# faellt die Reihe dann steiler, als jede einzelne Fahrt es tut.
durch = [(f"p{i}", f"2026-08-{i + 1:02d}", "volumen", [160, 156], VOLUMEN, 130)
         for i in range(8)]
# vier Fahrten, deren erste Stunde keinen Wert hergibt: tiefe alpha-Lage erst
# ab Stunde 2, modelliert ueber eine erste Stunde ausserhalb des Fensters
# ACHT solcher Fahrten, nicht vier: der Median daempft (§7, 0.45.0), er kippt
# erst bei Paritaet - wer den Effekt mit einer Handvoll nachbaut, baut einen
# stumpfen Test.
nur_zwei = []
for i in range(8):
    key = f"n{i}"
    dfa, watts = ride_streams([130])
    # Stunde 1 kuenstlich ohne Ablesung: alpha-Lage komplett ueber 0,75
    hoch_dfa = [round(1.20 + (k % 400) / 400 * 0.30, 3) for k in range(3600)]
    hoch_w = [140.0] * 3600
    nur_zwei.append((key, f"2026-09-{i + 1:02d}", "volumen", None, VOLUMEN, 130,
                     hoch_dfa + dfa, hoch_w + watts))

data = bestand(durch)
for key, day, name, _lv, zone_times, minutes, dfa, watts in nur_zwei:
    data["activities"][key] = {
        "start_date_local": f"{day}T09:00:00", "name": name, "type": "Ride",
        "moving_time": minutes * 60, "icu_zone_times": zone_times,
        "icu_average_watts": 150, "icu_weighted_avg_watts": 155}
    data["dfa"][key] = {"hours": derive.dfa_hours(dfa, watts)}

schief = fatigue.curve(data)
counts = [(r["hour"], r["n"]) for r in schief["measured"]]
print(f"      Belegung je Stunde: {counts}")
ok("Erkennungszeichen: die Belegung STEIGT, wo sie fallen muesste",
   len(schief["occupancy_rising"]) > 0)
check("und die Stunde wird benannt", schief["occupancy_rising"][0]["hour"], 2)
check("mit beiden Zahlen, damit der Sprung sichtbar ist",
      (schief["occupancy_rising"][0]["previous"], schief["occupancy_rising"][0]["n"]), (8, 16))
# Die Gegenprobe, GEZAEHLT UND BENANNT: ein sauberer Bestand darf NICHT
# anschlagen - sonst prueft die Regel oben nur, dass sie ueberhaupt feuert.
check("Gegenprobe: sauberer Bestand meldet keinen Auswahleffekt",
      fatigue.curve(bestand(durch))["occupancy_rising"], [])

# Und die gepaarte Rechnung sieht, was die ungepaarte nicht sieht.
ungepaart = schief["measured"][0]["watts"] - schief["measured"][1]["watts"]
gepaart = next(p for p in schief["paired"] if p["from_hour"] == 1)
print(f"      ungepaart {ungepaart:+.1f} W  |  gepaart {-gepaart['delta']:+.1f} W "
      f"ueber {gepaart['n']} Paare")
ok("gepaart faellt die Reihe FLACHER als ungepaart", -gepaart["delta"] < ungepaart)
check("die gepaarte Rechnung nennt ihre Paarzahl", gepaart["n"], 8)
ok("und sagt, ob sie ueberhaupt etwas aussagen darf", gepaart["enough"] is True)
duenn = fatigue.curve(bestand(durch[:3]))
knapp = next((p for p in duenn["paired"] if p["from_hour"] == 1), None)
check("zu wenige Paare: die Zahl wird nicht behauptet", knapp["enough"], False)

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

print("\n=== p050 wird ERHOBEN und von NICHTS benutzt ===")

dfa_lo, w_lo = [], []
for k in range(3600):
    a = 0.35 + (k % 400) / 400 * 0.70
    dfa_lo.append(round(a, 3))
    w_lo.append(200 - (a - 0.5) * 100)
zeile = derive.dfa_hours(dfa_lo, w_lo)[0]
ok("p050 wird gemessen", zeile["p050"] is not None)
ok("und p075 daneben weiter", zeile["p075"] is not None)
ok("die Signalqualitaet im unteren Band wird getrennt ausgewiesen",
   zeile["low_points"] > 0 and zeile["low_dropped_share"] is not None)
# Eine Stunde ganz OBERHALB von 0,5 traegt kein p050 - nicht extrapoliert.
dfa_hi = [round(0.80 + (k % 400) / 400 * 0.60, 3) for k in range(3600)]
hoch = derive.dfa_hours(dfa_hi, [150.0] * 3600)[0]
check("ohne Punkte unter 0,5 gibt es kein p050", hoch["p050"], None)
check("und auch keine Belegung dort", hoch["low_points"], 0)

# DER WAECHTER: p050 steuert NICHTS. Kein Renderer liest es, kein Trainer-Pfad
# haengt daran - sonst rutscht es in eine Anzeige, bevor bekannt ist, ob es
# traegt. Geprueft am Quelltext aller Verbraucher, nicht an der Absicht.
import re as _re  # noqa: E402
ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "intervals_icu"
for name in ("fatigue.py", "coach.py", "workouts.py", "analytics.py", "websocket.py",
             "frontend/intervals-panel.js"):
    text = (ROOT / name).read_text()
    hits = [line for line in text.splitlines()
            if "p050" in line and not line.strip().startswith(("#", "//", "*"))]
    check(f"Waechter: {name} liest p050 nicht", hits, [])
# Gegenprobe, GEZAEHLT UND BENANNT: eine eingebaute Leseszeile wird gefunden.
_planted = ['  const w = f.p050;', '# ok', 'x = row["p050"]']
check("Gegenprobe: eine Leseszeile wird gefunden",
      [line for line in _planted
       if "p050" in line and not line.strip().startswith(("#", "//", "*"))],
      ['  const w = f.p050;', 'x = row["p050"]'])

# --- Die Leitzahl: Leistung fuer eine GEPLANTE Dauer --------------------------
# Andere Leserichtung, dieselbe Rechnung. Und sie ist VERKETTET aus den
# gepaarten Schritten, nicht aus den rohen Stundenmedianen - die stammen aus
# verschiedenen Fahrten und tragen genau den Auswahleffekt, gegen den die
# Paarung gebaut ist.
def _r(key, *paare):
    return {"activity_id": key, "hours": [{"hour": h, "p075": p} for h, p in paare]}

BESTAND = [_r("a", (1, 150.0), (2, 140.0)), _r("b", (1, 160.0), (2, 148.0)),
           _r("c", (1, 140.0)), _r("d", (1, 130.0), (2, 126.0))]
kette = fatigue._plan_chain(BESTAND)

check("Leitzahl: je geplanter Dauer ein Eintrag", [r.get("hours") for r in kette], [1, 2])
check("Leitzahl: eine Stunde ist der Median der ersten Stunde",
      (kette[0].get("watts") if kette else None), 145.0)
# Roh waere der Median der zweiten Stunde (140+148+126)/3 -> 140,0.
# Verkettet: 145,0 + Median(-10, -12, -4) = 145,0 - 10,0 = 135,0.
check("Leitzahl: zwei Stunden kommt aus der KETTE, nicht aus dem rohen Median",
      (kette[1].get("watts") if len(kette) > 1 else None), 135.0)
check("Leitzahl: der Schritt reist als Rechenweg mit",
      [(r.get("step"), r.get("step_n")) for r in kette], [(None, None), (-10.0, 3)])
# GEGENPROBE, gezaehlt und benannt: der rohe Stundenmedian ist eine ANDERE
# Zahl. Ohne sie prueft der Test oben nur, dass irgendetwas herauskommt.
roh = sorted([140.0, 148.0, 126.0])[1]
check("Leitzahl Gegenprobe: der rohe Median saehe anders aus", roh, 140.0)

# Eine Fahrt ohne zweite Stunde bricht die Kette NICHT - sie traegt zur ersten
# bei und fehlt beim Schritt. Genau das ist die Auswahl, die gepaart wegfaellt.
check("Leitzahl: eine kurze Fahrt zaehlt bei der ersten Stunde mit",
      (kette[0].get("n") if kette else None), 4)
check("Leitzahl: und fehlt beim Schritt",
      (kette[1].get("step_n") if len(kette) > 1 else None), 3)
check("Leitzahl: ohne erste Stunde gibt es keine Kette",
      fatigue._plan_chain([_r("x", (2, 140.0))]), [])
check("Leitzahl: ohne Fahrten auch nicht", fatigue._plan_chain([]), [])

# --- Die Weglassprobe als Grenze, MASSSTABSFREI -------------------------------
# Eine Zahl gilt als gemessen, wenn keine einzelne Fahrt sie um mehr verschiebt
# als der Schritt gross ist, auf dem sie sitzt. Eine feste Wattgrenze saenke
# mit der Wurzel aus der Fahrtenzahl von allein.
# Die Fahrten muessen den Ausschluss in rides() PASSIEREN, sonst kommt gar
# keine Kette heraus und der Test prueft nichts - dieselbe Zonen-Fixture wie
# oben, nur mit von Hand gesetzten Stundenwerten.
data = {"activities": {}, "dfa": {}}
for i, ride in enumerate(BESTAND):
    data["activities"][ride["activity_id"]] = {
        "start_date_local": f"2026-09-0{i + 1}T07:00:00", "name": "GA", "type": "Ride",
        "moving_time": 9000, "icu_zone_times": VOLUMEN,
        "icu_average_watts": 150, "icu_weighted_avg_watts": 155}
    data["dfa"][ride["activity_id"]] = {"hours": ride["hours"]}
out = fatigue.curve(data)
check("Weglassprobe: die Fixture passiert den Ausschluss ueberhaupt",
      out.get("rides_used"), 4)
pl = out.get("plan") or []
check("Weglassprobe: jede Leitzahl traegt ihre groesste Verschiebung",
      all(r.get("loo_shift") is not None for r in pl), True)
check("Weglassprobe: und das Verhaeltnis zum Schritt",
      all(r.get("loo_ratio") is not None for r in pl), True)
check("Weglassprobe: die erste Stunde wird am folgenden Schritt gemessen",
      (pl[0].get("loo_ratio") is not None) if pl else None, True)
check("Weglassprobe: jede Leitzahl traegt einen Bereich",
      sorted({r.get("band") for r in pl}) != [], True)
check("Weglassprobe: ueber dem Verhaeltnis 1 ist nichts mehr gemessen",
      [r.get("hours") for r in pl
       if r.get("band") == "solid" and (r.get("loo_ratio") or 0) >= 1.0], [])
check("Weglassprobe: unter dem Verhaeltnis 1 ist nichts duenn",
      [r.get("hours") for r in pl
       if r.get("band") == "thin" and (r.get("loo_ratio") is not None)
       and r["loo_ratio"] < 1.0], [])
check("Weglassprobe: die durchgezogene Grenze bricht beim ERSTEN Riss ab",
      out.get("plan_solid_until_hours"),
      (pl[0]["hours"] if pl and pl[0].get("band") == "solid" else None)
      if not (len(pl) > 1 and pl[1].get("band") == "solid") else pl[1]["hours"])

# EIN STOERER, der die Kette kippt: eine Fahrt, die dem Schritt widerspricht,
# muss das Verhaeltnis ueber 1 treiben und die Zahl aus "gemessen" nehmen.
stoerer = BESTAND + [_r("z", (1, 120.0), (2, 190.0))]
kz = fatigue._plan_chain(stoerer)
check("Weglassprobe: ein Stoerer verschiebt den Schritt sichtbar",
      (kz[1].get("step") if len(kz) > 1 else None) != -10.0, True)

# --- Die zwei Saetze an der Kachel --------------------------------------------
ok("Kachel: der Auswahleffekt der spaeten Stunden steht als Satz bereit",
   "durchschnittliche" in fatigue.SELECTION_NOTE)
ok("Kachel: und er sagt, dass er sich NICHT mit mehr Fahrten schliesst",
   "schließt" in fatigue.SELECTION_NOTE)
ok("Kachel: der Achsen-Vorbehalt nennt die Intensitaet der Vorbelastung",
   "INTENSITÄT" in fatigue.AXIS_NOTE and "Fahrtzeit" in fatigue.AXIS_NOTE)
check("Kachel: beide reisen ueber die Payload, nicht als Literal",
      (out.get("selection_note"), out.get("axis_note")),
      (fatigue.SELECTION_NOTE, fatigue.AXIS_NOTE))


print(f"\ntest_fatigue: {CHECKS} Prüfungen, {len(failures)} Fehler")
print("FEHLER:", failures if failures else "keine")
sys.exit(1 if failures else 0)
