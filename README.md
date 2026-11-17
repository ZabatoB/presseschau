# Presseschau

Tägliche politische Presseschau aus drei Sprachräumen (deutsch, englisch, französisch) als eine einzige Webseite fürs Handy. Entstanden am 16.11.2026 aus einem Wunsch-Transkript: Updates nur aus seriösen Quellen, nach Sprachraum sortiert, dazu Leitartikel, tiefere Analysen und Podcasts.

Online: <https://zabatob.github.io/presseschau/>

## Was die Seite zeigt

Oben wählt man die Rubrik (Reiter), am Handy zusätzlich den Sprachraum. Am Desktop stehen die drei Sprachräume als Spalten nebeneinander.

| Rubrik | Inhalt |
|---|---|
| Nachrichten | Je Sprachraum die 8 Top-Meldungen, nummeriert. Oben steht, worüber die meisten Quellen gleichzeitig berichten. "n weitere Quellen" klappt die Überschriften der anderen Zeitungen zur selben Geschichte auf. Darunter stehen bis zu drei Kommentare, Analysen oder Podcast-Folgen, die zur selben Geschichte gehören. |
| Meinung | Hausleitartikel (Spiegel, Guardian view, NYT Editorial Board, Economist Leaders, Le Monde éditorial) plus Meinungsseiten von links bis konservativ, nach Quelle gruppiert. Je Quelle zwei Beiträge, bevorzugt solche, die zu einer Top-Meldung oder einem der Themen passen. |
| Analyse | Texte aus Wissenschaft und Fachwelt: Verfassungsblog, The Conversation, LSE, La Vie des idées, AOC, Amnesty, Human Rights Watch u. a. |
| Podcasts | Je Sendung die neueste Folge mit Dauer; eine Folge zu einer Top-Meldung hat Vorrang. |

Themenfilter: Menschenrechte, KI, Klima, Todesstrafe, Gesetze und Recht, Proteste. Ein gewähltes Thema zeigt unter Nachrichten zusätzlich die Themenseiten der Zeitungen aus den letzten 14 Tagen.

Die Seite merkt sich den zuletzt gewählten Sprachraum und warnt, wenn die Ausgabe älter als 36 Stunden ist.

## Benutzen

```bash
python3 build.py            # holt alle Feeds, schreibt docs/index.html (ca. 30 Sekunden)
python3 build.py --test     # Selbsttest ohne Netz
python3 build.py --ersatz   # baut nur, wenn die vorhandene Ausgabe älter als drei Stunden ist
```

Braucht nur Python 3.9 oder neuer, keine Pakete.

## Anpassen

Alles steht oben in `build.py`:

- `FEEDS`: eine Zeile je Quelle `(Sprachraum, Rubrik, Name, Feed-Adresse[, festes Thema])`. Zeile löschen oder ergänzen genügt. Die Reihenfolge bestimmt, wessen Überschrift bei gleichen Geschichten vorn steht.
- `TOPICS`: Themen und ihre Suchwörter.
- `TOP`: Zahl der Top-Meldungen je Sprachraum. `SECTIONS`: Zeitfenster und Obergrenzen je Rubrik.
- `SAME` und `NEAR`: wie ähnlich zwei Meldungen sein müssen, um als dieselbe Geschichte zu gelten, und ab wann ein Kommentar dazugehört. Höher heißt strenger.

## Automatische Aktualisierung

- `.github/workflows/presseschau.yml` baut zwei Ausgaben am Tag: morgens ab 04:17 UTC und nachmittags ab 15:17 UTC (in Wien 05:17 und 16:17 Winterzeit, in der Sommerzeit eine Stunde später). Die fertige Seite wird nach `docs/` committet, GitHub Pages liefert `docs/` vom Branch `main` aus.
- GitHub lässt geplante Läufe gelegentlich aus (am 17.11.2026 fiel gleich der erste aus). Deshalb gibt es je Ausgabe zwei Ersatz-Zeitpunkte eine und zwei Stunden später. Ein Ersatz-Lauf baut nur, wenn die letzte Ausgabe älter als drei Stunden ist (`--ersatz`).
- Außer der Reihe neu bauen: `gh workflow run presseschau.yml` oder auf GitHub unter Actions > Presseschau > Run workflow.
- Sind mehr als die Hälfte der Feeds nicht erreichbar, bricht der Lauf ab und die vorige Ausgabe bleibt stehen.
- Änderungen an `build.py` wirken nach `git push` ab dem nächsten Lauf. Vorher `git pull`, weil die Läufe selbst committen.
- `docs/icon.png` ist das Symbol für den Home-Bildschirm. Die Seite trägt `noindex`, taucht also nicht in Suchmaschinen auf, ist aber für jeden mit dem Link lesbar.

## Bewusst weggelassen

- Keine KI-Zusammenfassungen. Die Auswahl entsteht durch die Quellenliste und dadurch, wie viele Zeitungen dieselbe Geschichte bringen. Ein tägliches "Lagebild in fünf Sätzen" mit Gegenüberstellung der Sichtweisen wäre ein Aufruf eines Sprachmodells im Workflow (braucht einen API-Schlüssel, kostet einige Cent pro Tag).
- Kein Archiv. Jede Ausgabe zeigt, was die Feeds gerade hergeben.
- Keine Mitteilungen aufs Handy.

Stellen im Code, an denen bewusst vereinfacht wurde, sind mit `ponytail:` markiert.
