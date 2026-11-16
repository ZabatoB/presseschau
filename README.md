# Presseschau

Tägliche politische Presseschau aus drei Sprachräumen (deutsch, englisch, französisch) als eine einzige Webseite fürs Handy. Entstanden am 16.11.2026 aus einem Wunsch-Transkript: Updates nur aus seriösen Quellen, nach Sprachraum sortiert, dazu Leitartikel, tiefere Analysen und Podcasts.

## Was die Seite zeigt

| Rubrik | Inhalt |
|---|---|
| Nachrichten | Je Sprachraum die 8 Top-Meldungen. Oben steht, worüber die meisten Quellen gleichzeitig berichten. "Auch bei ..." klappt die Überschriften der anderen Zeitungen zur selben Geschichte auf. |
| Leitartikel und Meinung | Hausleitartikel (Spiegel, Guardian view, NYT Editorial Board, Economist Leaders, Le Monde éditorial) plus Meinungsseiten von links bis konservativ. |
| Analyse und Hintergrund | Texte aus Wissenschaft und Fachwelt: Verfassungsblog, The Conversation, LSE, La Vie des idées, AOC, Amnesty, Human Rights Watch u. a. |
| Podcasts | Jeweils die neueste Folge von Politik- und Philosophie-Podcasts. |

Themenfilter oben: Menschenrechte, KI, Klima, Todesstrafe, Gesetze und Recht, Proteste. Ein gewähltes Thema zeigt zusätzlich die Themenseiten der Zeitungen aus den letzten 14 Tagen.

## Benutzen

```bash
python3 build.py          # holt alle Feeds, schreibt docs/index.html (ca. 30 Sekunden)
python3 build.py --test   # Selbsttest ohne Netz
```

Braucht nur Python 3.9 oder neuer, keine Pakete.

## Anpassen

Alles steht oben in `build.py`:

- `FEEDS`: eine Zeile je Quelle `(Sprachraum, Rubrik, Name, Feed-Adresse[, festes Thema])`. Zeile löschen oder ergänzen genügt. Die Reihenfolge bestimmt, wessen Überschrift bei gleichen Geschichten vorn steht.
- `TOPICS`: Themen und ihre Suchwörter.
- `TOP`: Zahl der Top-Meldungen je Sprachraum. `SECTIONS`: Zeitfenster und Obergrenzen je Rubrik.

## Online stellen (noch offen)

Vorbereitet ist `.github/workflows/presseschau.yml`: GitHub baut die Seite jeden Morgen gegen 5 bis 6 Uhr neu und legt sie in `docs/` ab. Dafür fehlt noch:

1. `gh auth login`
2. Repo anlegen und hochladen: `git init -b main && git add -A && git commit -m "Presseschau" && gh repo create presseschau --public --source . --push`
3. In den Repo-Einstellungen unter Pages: "Deploy from a branch", Branch `main`, Ordner `/docs`.

Danach ist die Seite unter `https://<github-name>.github.io/presseschau/` erreichbar und lässt sich am Handy zum Home-Bildschirm hinzufügen. Der Workflow ist bisher nicht gelaufen, also ungetestet. Die Seite trägt `noindex`, taucht also nicht in Suchmaschinen auf, ist aber für jeden mit dem Link lesbar.

## Bewusst weggelassen

- Keine KI-Zusammenfassungen. Die Auswahl entsteht durch die Quellenliste und dadurch, wie viele Zeitungen dieselbe Geschichte bringen. Ein tägliches "Lagebild in fünf Sätzen" mit Gegenüberstellung der Sichtweisen wäre ein Aufruf eines Sprachmodells im Workflow (braucht einen API-Schlüssel, kostet einige Cent pro Tag).
- Kein Archiv. Jede Ausgabe zeigt, was die Feeds gerade hergeben.
- Keine Mitteilungen aufs Handy.

Stellen im Code, an denen bewusst vereinfacht wurde, sind mit `ponytail:` markiert.
