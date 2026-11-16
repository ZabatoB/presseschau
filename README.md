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

## Online

Die Seite steht unter <https://zabatob.github.io/presseschau/> (seit 17.11.2026). Am Handy im Browser öffnen und über "Teilen" zum Home-Bildschirm hinzufügen, dann liegt sie dort wie eine App.

- `.github/workflows/presseschau.yml` baut die Seite jeden Morgen um 04:17 UTC neu (05:17 Winterzeit, 06:17 Sommerzeit in Wien) und committet sie nach `docs/`. GitHub Pages liefert `docs/` vom Branch `main` aus.
- Außer der Reihe neu bauen: `gh workflow run presseschau.yml` oder auf GitHub unter Actions > Presseschau > Run workflow.
- Änderungen an `build.py` wirken nach `git push` ab dem nächsten Lauf. Vorher `git pull`, weil der tägliche Lauf selbst committet.
- Die Seite trägt `noindex`, taucht also nicht in Suchmaschinen auf, ist aber für jeden mit dem Link lesbar.

## Bewusst weggelassen

- Keine KI-Zusammenfassungen. Die Auswahl entsteht durch die Quellenliste und dadurch, wie viele Zeitungen dieselbe Geschichte bringen. Ein tägliches "Lagebild in fünf Sätzen" mit Gegenüberstellung der Sichtweisen wäre ein Aufruf eines Sprachmodells im Workflow (braucht einen API-Schlüssel, kostet einige Cent pro Tag).
- Kein Archiv. Jede Ausgabe zeigt, was die Feeds gerade hergeben.
- Keine Mitteilungen aufs Handy.

Stellen im Code, an denen bewusst vereinfacht wurde, sind mit `ponytail:` markiert.
