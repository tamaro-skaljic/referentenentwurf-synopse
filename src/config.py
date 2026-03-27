"""URL constants and configuration shared across the pipeline."""

SOURCE_2024_PDF_URL = "https://raw.githubusercontent.com/tamaro-skaljic/referentenentwurf-synopse/refs/heads/main/input/2024-09_Referentenentwurf_Synopse.pdf"
SOURCE_2026_PDF_URL = "https://raw.githubusercontent.com/tamaro-skaljic/referentenentwurf-synopse/refs/heads/main/input/2026-03_Referentenentwurf_Synopse.pdf"
GITHUB_URL = "https://github.com/tamaro-skaljic/referentenentwurf-synopse?tab=readme-ov-file#readme"
CARELEAVER_URL = "https://careleaver.de/ueber-uns/"
DONATION_URL = "https://careleaver.de/spenden/jetzt-spenden/"

FULL_PDF_URL = (
    "https://raw.githubusercontent.com/tamaro-skaljic/referentenentwurf-synopse"
    "/refs/heads/main/output/Synopse%20IKJHG%20-%20Vergleich%20der%20Referentenentw%C3%BCrfe%202024%20und%202026.pdf"
)

MINIFIED_PDF_URL = (
    "https://raw.githubusercontent.com/tamaro-skaljic/referentenentwurf-synopse"
    "/refs/heads/main/output/Synopse%20IKJHG%20-%20Vergleich%20nur%20der%20%C3%84nderungen"
    "%20zwischen%20den%20Referentenentw%C3%BCrfe%202024%20und%202026.pdf"
)

SUBSCRIBE_URL = (
    "mailto:tamaro.skaljic@careleaver.de"
    "?subject=Eintragung%20in%20den%20Verteiler"
    "&body=Hiermit%20stimme%20ich%20zu%2C%20dass%20Sie%20mich%20per%20E-Mail"
    "%20%C3%BCber%20neue%20Versionen%20der%20Synopsen"
    "%0D%0A%0D%0A-%20Vergleich%20der%20Referentenentw%C3%BCrfe%202024%20und%202026"
    "%0D%0A%0D%0Aund"
    "%0D%0A%0D%0A-%20Vergleich%20nur%20der%20%C3%84nderungen%20zwischen%20den"
    "%20Referentenentw%C3%BCrfen%202024%20und%202026"
    "%0D%0A%0D%0Ainformieren."
    "%0D%0A%0D%0AIch%20wurde%20dar%C3%BCber%20informiert%2C%20dass%20ich%20mich"
    "%20jederzeit%20formlos%20per%20E-Mail%20an%20tamaro.skaljic%40careleaver.de"
    "%20aus%20dem%20Verteiler%20austragen%20kann."
)

REPORT_PROBLEM_URL_TEMPLATE = (
    "mailto:tamaro.skaljic@careleaver.de"
    "?subject=Problem%20melden%20-%20%22{synopse_title}%22%20(Stand%3A%20{synopse_date})"
    "&body=---%20Hinweis%20---"
    "%0D%0ABevor%20Sie%20ein%20Problem%20melden%2C%20%C3%BCberpr%C3%BCfen%20Sie%20bitte%2C"
    "%20ob%20die%20Synopse%2C%20welche%20Sie%20sich%20anschauen"
    "%20(Stand%3A%20{synopse_date})%2C%20der%20aktuellsten%20Version%20entspricht."
    "%20Sie%20finden%20einen%20Link%20zur%20aktuellsten%20Version%20ganz%20oben%20in%20der%20Synopse."
    "%0D%0AVielen%20Dank%20im%20Voraus."
    "%0D%0A---%20Hinweis%20Ende%20---"
)
