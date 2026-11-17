# Presseschau

Tägliche politische Presseschau aus drei Sprachräumen (deutsch, englisch, französisch) als eine einzige Webseite fürs Handy. Entstanden am 16.11.2026 aus einem Wunsch-Transkript: Updates nur aus seriösen Quellen, nach Sprachraum sortiert, dazu Leitartikel, tiefere Analysen und Podcasts.

## Was die Seite zeigt

| Rubrik | Inhalt |
|---|---|
| Nachrichten | Je Sprachraum die 8 Top-Meldungen. Oben steht, worüber die meisten Quellen gleichzeitig berichten. "Auch bei ..." klappt die Überschriften der anderen Zeitungen zur selben Geschichte auf. Unter "Einordnung" stehen bis zu drei Kommentare, Analysen oder Podcast-Folgen, die zur selben Geschichte gehören. |
| Leitartikel und Meinung | Hausleitartikel (Spiegel, Guardian view, NYT Editorial Board, Economist Leaders, Le Monde éditorial) plus Meinungsseiten von links bis konservativ. Je Quelle zwei Beiträge, bevorzugt solche, die zu einer Top-Meldung oder einem der Themen passen. |
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
- `SAME` und `NEAR`: wie ähnlich zwei Meldungen sein müssen, um als dieselbe Geschichte zu gelten, und ab wann ein Kommentar als Einordnung dazugehört. Höher heißt strenger.

## Online

Die Seite steht unter <https://zabatob.github.io/presseschau/> (seit 17.11.2026). Am Handy im Browser öffnen und über "Teilen" zum Home-Bildschirm hinzufügen, dann liegt sie dort wie eine App.

- `.github/workflows/presseschau.yml` baut die Seite zweimal täglich neu, um 04:17 und 15:17 UTC (in Wien 05:17 und 16:17 Winterzeit, in der Sommerzeit eine Stunde später), und committet sie nach `docs/`. GitHub Pages liefert `docs/` vom Branch `main` aus.
- `docs/icon.png` ist das Symbol für den Home-Bildschirm.
- Außer der Reihe neu bauen: `gh workflow run presseschau.yml` oder auf GitHub unter Actions > Presseschau > Run workflow.
- Änderungen an `build.py` wirken nach `git push` ab dem nächsten Lauf. Vorher `git pull`, weil der tägliche Lauf selbst committet.
- Die Seite trägt `noindex`, taucht also nicht in Suchmaschinen auf, ist aber für jeden mit dem Link lesbar.

## Bewusst weggelassen

- Keine KI-Zusammenfassungen. Die Auswahl entsteht durch die Quellenliste und dadurch, wie viele Zeitungen dieselbe Geschichte bringen. Ein tägliches "Lagebild in fünf Sätzen" mit Gegenüberstellung der Sichtweisen wäre ein Aufruf eines Sprachmodells im Workflow (braucht einen API-Schlüssel, kostet einige Cent pro Tag).
- Kein Archiv. Jede Ausgabe zeigt, was die Feeds gerade hergeben.
- Keine Mitteilungen aufs Handy.

Stellen im Code, an denen bewusst vereinfacht wurde, sind mit `ponytail:` markiert.
