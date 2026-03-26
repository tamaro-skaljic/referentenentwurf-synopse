# Referentenentwurf-Synopse

Hier geht es direkt zur Synopse:
 <https://raw.githubusercontent.com/tamaro-skaljic/referentenentwurf-synopse/refs/heads/main/output/Synopse%20IKJHG%20-%20Vergleich%20der%20Referentenentw%C3%BCrfe%202024%20und%202026.pdf>

Und eine Synopse, welche nur die Änderungen zwischen beiden Entwürfen beinhaltet (Jede Reihe, wo beide Referentenentwürfe identisch sind, wurde entfernt): <https://raw.githubusercontent.com/tamaro-skaljic/referentenentwurf-synopse/refs/heads/main/output/Synopse%20IKJHG%20-%20Vergleich%20nur%20der%20%C3%84nderungen%20zwischen%20den%20Referentenentw%C3%BCrfe%202024%20und%202026.pdf>

Erzeugt eine dreispaltige PDF-Synopse, die das geltende Recht den Änderungen der Referentenentwürfe von 2024 und 2026 gegenüberstellt.

| Geltendes Recht | Änderungen RefE 2024 | Änderungen RefE 2026 |
|-----------------|----------------------|----------------------|

## Schnellstart

### Einrichtung & Ausführung

```powershell
.\setup.ps1   # Installiert uv, Python, Abhängigkeiten und MiKTeX
.\run.ps1     # Erzeugt synopsis_combined.pdf
```

Die fertige Synopse liegt anschließend als [Synopse IKJHG - Vergleich der Referentenentwürfe 2024 und 2026.pdf](https://raw.githubusercontent.com/tamaro-skaljic/referentenentwurf-synopse/refs/heads/main/output/Synopse%20IKJHG%20-%20Vergleich%20der%20Referentenentw%C3%BCrfe%202024%20und%202026.pdf) im `output/`-Verzeichnis.

| Markierungsfarbe | Änderungen RefE 2024                      | Änderungen RefE 2026                                                                                               |
| ---------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Grün             | -                                         | Wurde im Vergleich zum RefE 2024 (oder geltendem Recht, falls RefE 2024 nicht vorhanden / unverändert) hinzugefügt |
| Rot              | Wurde im Vergleich zum RefE 2026 gelöscht | -                                                                                                                  |

## Lizenz

Public Domain – siehe [LICENSE](LICENSE) (Unlicense).
