# Referentenentwurf-Synopse

Erzeugt eine dreispaltige PDF-Synopse, die das geltende Recht den Änderungen der Referentenentwürfe von 2024 und 2026 gegenüberstellt.

| Geltendes Recht | Änderungen RefE 2024 | Änderungen RefE 2026 |
|-----------------|----------------------|----------------------|

## Schnellstart

### Einrichtung & Ausführung

**PowerShell:**

```powershell
.\setup.ps1   # Installiert uv, Python, Abhängigkeiten und MiKTeX
.\run.ps1     # Erzeugt synopsis_combined.pdf
```

**Bash:**

```bash
./setup.sh   # Installiert uv, Python, Abhängigkeiten und MiKTeX
./run.sh     # Erzeugt synopsis_combined.pdf
```

Die fertige Synopse liegt anschließend als [synopsis_combined.pdf](output/synopsis_combined.pdf) im `output/`-Verzeichnis.

| Markierungsfarbe | Änderungen RefE 2024                      | Änderungen RefE 2026                                                                                               |
| ---------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Grün             | -                                         | Wurde im Vergleich zum RefE 2024 (oder geltendem Recht, falls RefE 2024 nicht vorhanden / unverändert) hinzugefügt |
| Rot              | Wurde im Vergleich zum RefE 2026 gelöscht | -                                                                                                                  |

## Lizenz

Public Domain – siehe [LICENSE](LICENSE) (Unlicense).
