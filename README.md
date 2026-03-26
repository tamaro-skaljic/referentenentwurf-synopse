<!-- markdownlint-disable MD033 -->

# Synopse IKJHG - Vergleich der Referentenentwürfe 2024 und 2026 📘

## Direkt zu den Ergebnissen 🚀

- [Synopse IKJHG - Vergleich der Referentenentwürfe 2024 und 2026.pdf](https://raw.githubusercontent.com/tamaro-skaljic/referentenentwurf-synopse/refs/heads/main/output/Synopse%20IKJHG%20-%20Vergleich%20der%20Referentenentw%C3%BCrfe%202024%20und%202026.pdf)
- [Synopse IKJHG - Vergleich nur der Änderungen zwischen den Referentenentwürfen 2024 und 2026.pdf](https://raw.githubusercontent.com/tamaro-skaljic/referentenentwurf-synopse/refs/heads/main/output/Synopse%20IKJHG%20-%20Vergleich%20nur%20der%20%C3%84nderungen%20zwischen%20den%20Referentenentw%C3%BCrfe%202024%20und%202026.pdf)

## Hinweise & Transparenz 🤝

<p align="center">
 <img src="./careleaver_logo_rgb.png" alt="Careleaver e. V. Logo" width="320" />
</p>

Dieses kostenlose und quelloffene Projekt wurde von Tamaro Skaljic entwickelt (seit Februar 2026 im Vorstandsbeisitz des [Careleaver e. V.](https://careleaver.de/ueber-uns/)).

Da Menschen auch beim Programmieren Fehler machen können, nutzen Sie bitte die aktuellste Version dieser Synopsen, die Download-Links sehen Sie oben.

Wenn Sie über neue Versionen informiert werden möchten, können Sie sich [per E-Mail](mailto:tamaro.skaljic@careleaver.de?subject=Eintragung%20in%20den%20Verteiler&body=Hiermit%20stimme%20ich%20zu%2C%20dass%20Sie%20mich%20per%20E-Mail%20%C3%BCber%20neue%20Versionen%20der%20Synopsen%0D%0A%0D%0A-%20Vergleich%20der%20Referentenentw%C3%BCrfe%202024%20und%202026%0D%0A%0D%0Aund%0D%0A%0D%0A-%20Vergleich%20nur%20der%20%C3%84nderungen%20zwischen%20den%20Referentenentw%C3%BCrfen%202024%20und%202026%0D%0A%0D%0Ainformieren.%0D%0A%0D%0AIch%20wurde%20dar%C3%BCber%20informiert%2C%20dass%20ich%20mich%20jederzeit%20formlos%20per%20E-Mail%20an%20tamaro.skaljic%40careleaver.de%20aus%20dem%20Verteiler%20austragen%20kann.) in den Verteiler eintragen.

Wenn wir Ihnen die Arbeit erleichtern konnten, freut sich der Careleaver e. V. über eine [Spende](https://careleaver.de/spenden/jetzt-spenden/). 💛

## Was dieses Projekt macht 🛠️

Dieses Repository verarbeitet zwei juristische Synopsen (2024 und 2026), richtet die Inhalte aus, führt sie zusammen und erzeugt daraus druckbare Vergleichs-PDFs.

Kurz gesagt:

- 📥 Eingabe: Synopsen der Referentenentwürfe 2024 und 2026 (PDF)
- 🔄 Verarbeitung: Extraktion, Alignment und Zusammenführung der Inhalte
- 📄 Ausgabe: strukturierte Vergleichs-Synopsen als PDF

## Datengrundlage 📚

Die Generierung erfolgt auf Basis dieser Quelldokumente:

- [Referentenentwurf-Synopse 2024](https://raw.githubusercontent.com/tamaro-skaljic/referentenentwurf-synopse/refs/heads/main/input/2024-09_Referentenentwurf_Synopse.pdf)
- [Referentenentwurf-Synopse 2026](https://raw.githubusercontent.com/tamaro-skaljic/referentenentwurf-synopse/refs/heads/main/input/2026-03_Referentenentwurf_Synopse.pdf)

## Schnellstart ⚡

### Einrichtung & Ausführung

```powershell
.\setup.ps1   # Installiert uv, Python, Abhängigkeiten und MiKTeX
.\run.ps1     # Erzeugt synopsis_combined.pdf
```

Die fertigen Synopsen liegen anschließend im Verzeichnis [`output`](output).

## Projektüberblick (technisch) 🧩

- `src/extract_synopsis.py`: Extrahiert strukturierte Inhalte aus den Eingabe-PDFs
- `src/align_and_merge.py`: Richtet Inhalte aus und führt Versionen zusammen
- `src/generate_latex.py`: Erzeugt LaTeX/PDF-Ausgaben
- `tests/`: Automatisierte Tests für Kernlogik

## Lizenz

Public Domain – siehe [LICENSE](LICENSE) (Unlicense).
