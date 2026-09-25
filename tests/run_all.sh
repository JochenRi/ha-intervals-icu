#!/usr/bin/env bash
# Prüfstand: alle test_*.py mit Python >= 3.12, alle test_*.js mit node.
# Aufruf aus dem Repo-Wurzelverzeichnis:  bash tests/run_all.sh
# Ausgabe je Datei eine Zeile, am Ende "Dateien=N Summe=N Fehler=N"; rc != 0 bei jedem Fehler.
set -u
cd "$(dirname "$0")"
PY=""
for c in python3.13 python3.12 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)'; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then echo "kein Python >= 3.12 gefunden (coordinator.py nutzt die type-Anweisung)"; exit 2; fi
echo "Python: $($PY --version 2>&1) · node: $(node --version 2>&1)"
files=0; sum=0; bad=0
for f in test_*.py test_*.js; do
  case "$f" in *.py) out=$("$PY" "$f" 2>&1); rc=$?;; *) out=$(node "$f" 2>&1); rc=$?;; esac
  n=$(printf '%s\n' "$out" | grep -oE '[0-9]+ Prüfungen' | tail -1 | grep -oE '[0-9]+')
  files=$((files + 1)); sum=$((sum + ${n:-0}))
  if [ "$rc" -ne 0 ]; then bad=$((bad + 1)); printf '%-34s rc=%s %6s  FEHLER\n' "$f" "$rc" "${n:-?}"; printf '%s\n' "$out" | tail -15
  else printf '%-34s rc=0 %6s\n' "$f" "${n:-?}"; fi
done
echo "Dateien=$files Summe=$sum Fehler=$bad"
[ "$bad" -eq 0 ]
