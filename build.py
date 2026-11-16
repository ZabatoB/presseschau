#!/usr/bin/env python3
"""Presseschau: baut aus den RSS-Feeds seriöser Quellen eine einzige statische Seite.

    python3 build.py          holt alle Feeds und schreibt docs/index.html
    python3 build.py --test   Selbsttest ohne Netz

Quellen pflegen: Liste FEEDS. Themen pflegen: TOPICS. Mehr Stellschrauben gibt es nicht.
Nur Standardbibliothek, keine Abhängigkeiten.
"""
import html
import io
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from math import log, sqrt
from pathlib import Path
from zoneinfo import ZoneInfo

UA = "Presseschau/1.0 (privater Feedreader)"
TZ = ZoneInfo("Europe/Vienna")
OUT = Path(__file__).parent / "docs" / "index.html"
TOP = 8      # Top-Meldungen je Sprachraum
SAME = 0.25  # ab dieser Ähnlichkeit (0..1) gelten zwei Meldungen als dieselbe Geschichte
# Politik-Feeds liefern auch Kultur, Sport und Videoclips mit. Die erkennt man am Ressort in der Adresse.
OFFTOPIC = re.compile(r"/(?:kultur|culture|sports?|film|kino|cinema|musik|music|musique|football|fussball|books|livres"
                      r"|tv-and-radio|lifeandstyle|food|fashion|travel|stage|artanddesign|games|arts|style|movies"
                      r"|videos?|vid(?:é|%C3%A9)os?)/", re.I)

REGIONS = {  # Kürzel: (Name, Beschriftung des Umschalters in der jeweiligen Sprache)
    "de": ("Deutschsprachiger Raum", "Deutsch"),
    "en": ("Englischsprachiger Raum", "English"),
    "fr": ("Französischsprachiger Raum", "Français"),
}

SECTIONS = {  # Rubrik: (Überschrift, Zeitfenster in Tagen, höchstens so viele Einträge je Feed)
    "news": ("Nachrichten", 1.5, 99),
    "thema": ("", 14, 4),  # Themenseiten der Zeitungen; erscheinen unter Nachrichten, sobald ein Thema gewählt ist
    "meinung": ("Leitartikel und Meinung", 7, 2),
    "analyse": ("Analyse und Hintergrund", 21, 2),
    "podcast": ("Podcasts", 14, 1),
}

# ponytail: Themen per Stichwortsuche in Titel und Anriss. Trifft nicht jede Nuance und
# markiert gelegentlich zu viel. Upgrade, falls das stört: Einordnung durch ein Sprachmodell.
TOPICS = {  # Kürzel: (Name, Suchmuster ohne Groß/Klein-Unterscheidung)
    "menschenrechte": ("Menschenrechte", r"""menschenrecht|grundrecht|human rights|droits? (?:de l[’']homme|humains?|fondamentaux)
        |amnesty|\basyl|asylum|\basile\b|flüchtling|geflüchtete|refugee|réfugié|abschieb|deport|expulsion
        |folter|torture|pressefreiheit|press freedom|liberté de la presse|meinungsfreiheit|free speech
        |freedom of (?:expression|speech)|liberté d[’']expression|zensur|censorship|diskriminier|discriminat
        |rassismus|racism|antisemit|antisémit|kriegsverbrech|war crime|crimes? de guerre|völkermord|genozid|genocide|génocide
        |gegen die menschlichkeit|against humanity|contre l[’']humanité|völkerrecht|international law|droit international
        |frauenrechte|women[’']s rights|droits des femmes|femizid|femicide|féminicide|lgbt
        |politische gefangene|political prisoner|prisonni\w+ politique"""),
    "ki": ("KI", r"""künstliche[rn]? intelligenz|artificial intelligence|intelligence artificielle
        |(?-i:\b(?:KIs?|AI|IA)\b|\bA\.I\.)|chatgpt|openai|\banthropic\b|\bllms?\b|sprachmodell|language model
        |deepfake|algorithm|chatbot|machine learning|maschinelles lernen
        |gesichtserkennung|facial recognition|reconnaissance faciale"""),
    "klima": ("Klima", r"""\bklima(?!anlage)|(?<!political\ )(?<!economic\ )(?<!business\ )\bclimate\b(?!\ of\b)
        |climatique|\bclimat\b(?!\ (?:politique|social|délétère|tendu|des\ affaires|de\b|d[’']))
        |erderwärmung|erderhitzung|global warming|global heating|réchauffement|dérèglement
        |treibhausgas|greenhouse gas|effet de serre|\bco2\b|\bcop ?\d\d\b|energiewende|fossil|kohleausstieg
        |net zero|dekarbon|decarbon|décarbon|emissionshandel|carbon (?:tax|emission|price|budget)|taxe carbone"""),
    "todesstrafe": ("Todesstrafe", r"""todesstrafe|todesurteil|hinrichtung|hingerichtet|zum tode verurteilt
        |death penalty|capital punishment|death row|death sentence|sentenced to death|\bexecut(?:e[sd]|ions?)\b
        |peine de mort|peine capitale|condamn\w+ à mort|couloir de la mort|exécution capitale"""),
    "recht": ("Gesetze und Recht", r"""gesetz(?!lich)|novell|verordnung|richtlinie|\burteil|gerichtshof
        |verfassungs(?:gericht|widrig|klage|beschwerde|änderung)|(?-i:\b(?:BVerfG|VfGH|EuGH|EGMR|IStGH|ECHR|ICJ|ICC|CEDH|CJUE|CIJ)\b)
        |legislation|lawmakers|supreme court|constitutional court|unconstitutional|court rul|into law
        |\blaws?\b(?!\ enforcement|\ firm)|\bbill\b(?!\ (?:clinton|gates|maher))|judge (?:rules|blocks|orders)
        |\blois?\b|\bdécrets?\b|législation|législateur|conseil constitutionnel|conseil d[’']état|cour de cassation
        |cour (?:suprême|constitutionnelle|européenne|pénale)|inconstitutionnel|\b49[.,]3\b"""),
    "protest": ("Proteste", r"""protest(?!ant)|demonstrant|demonstrat(?:ion|or)|kundgebung|streik|aufstand|unruhen|ausschreitung
        |ziviler ungehorsam|civil disobedience|désobéissance civile|aktivist|activis
        |(?:protest|klima|friedens|frauen|studenten|jugend|bürger|demokratie)bewegung
        |on strike|strike action|general strike|walkout|\briots?\b|unrest|uprising
        |manifestation|manifestant|\bgrèves?\b|gréviste|blocus|mobilisation|émeute|soulèvement
        |mouvement (?:social|étudiant|lycéen)"""),
}
TOPICS = {k: (name, re.compile(re.sub(r"\s*\n\s*", "", rx), re.I)) for k, (name, rx) in TOPICS.items()}

G, N, S, Z, M, F24 = ("https://www.theguardian.com/", "https://www.nytimes.com/svc/collections/v1/publish/",
                      "https://www.spiegel.de/", "https://newsfeed.zeit.de/", "https://www.lemonde.fr/",
                      "https://www.france24.com/fr/")
RF = "https://radiofrance-podcast.net/podcast09/podcast_"

# (Sprachraum, Rubrik, Quelle, Feed-Adresse[, festes Thema])
# Reihenfolge = Rangfolge: Wer weiter oben steht, stellt bei gleichen Geschichten die Hauptüberschrift.
FEEDS = [
    # ---------- Deutschsprachiger Raum ----------
    ("de", "news", "Der Spiegel", S + "politik/index.rss"),
    ("de", "news", "Der Spiegel", S + "ausland/index.rss"),
    ("de", "news", "Die Zeit", Z + "politik/index"),
    ("de", "news", "Süddeutsche Zeitung", "https://rss.sueddeutsche.de/rss/Politik"),
    ("de", "news", "FAZ", "https://www.faz.net/rss/aktuell/politik/"),
    ("de", "news", "Tagesschau", "https://www.tagesschau.de/inland/index~rss2.xml"),
    ("de", "news", "Tagesschau", "https://www.tagesschau.de/ausland/index~rss2.xml"),
    ("de", "news", "Der Standard", "https://www.derstandard.at/rss/inland"),
    ("de", "news", "Der Standard", "https://www.derstandard.at/rss/international"),
    ("de", "news", "Die Presse", "https://www.diepresse.com/rss/Politik"),
    ("de", "news", "NZZ", "https://www.nzz.ch/international.rss"),
    ("de", "news", "NZZ", "https://www.nzz.ch/schweiz.rss"),
    ("de", "news", "taz", "https://taz.de/!p4615;rss/"),
    ("de", "thema", "Der Spiegel", S + "thema/menschenrechte/index.rss", "menschenrechte"),
    ("de", "thema", "Der Spiegel", S + "thema/kuenstliche_intelligenz/index.rss", "ki"),
    ("de", "thema", "Der Spiegel", S + "thema/klimawandel/index.rss", "klima"),
    ("de", "thema", "Der Spiegel", S + "thema/todesstrafe/index.rss", "todesstrafe"),
    ("de", "thema", "Der Spiegel", S + "thema/proteste/index.rss", "protest"),
    ("de", "thema", "Die Zeit", Z + "thema/menschenrechte", "menschenrechte"),
    ("de", "thema", "Die Zeit", Z + "thema/kuenstliche-intelligenz", "ki"),
    ("de", "thema", "Die Zeit", Z + "thema/klimawandel", "klima"),
    ("de", "thema", "Die Zeit", Z + "thema/todesstrafe", "todesstrafe"),
    ("de", "meinung", "Der Spiegel: Leitartikel", S + "thema/spiegel-leitartikel/index.rss"),
    ("de", "meinung", "Süddeutsche Zeitung: Meinung", "https://rss.sueddeutsche.de/rss/Meinung"),
    ("de", "meinung", "Die Zeit: Fünf vor acht", Z + "serie/fuenf-vor-acht"),
    ("de", "meinung", "Tagesschau: Kommentar", "https://www.tagesschau.de/kommentar/index~rss2.xml"),
    ("de", "meinung", "Deutschlandfunk: Presseschau", "https://www.deutschlandfunk.de/presseschau-100.rss"),
    ("de", "meinung", "Der Standard: Diskurs", "https://www.derstandard.at/rss/diskurs"),
    ("de", "meinung", "NZZ: Meinung", "https://www.nzz.ch/meinung.rss"),
    ("de", "meinung", "taz: Debatte", "https://taz.de/!p4633;rss/"),
    ("de", "analyse", "Verfassungsblog", "https://verfassungsblog.de/feed/", "recht"),
    ("de", "analyse", "Legal Tribune Online", "https://www.lto.de/rss/feed.xml", "recht"),
    ("de", "analyse", "netzpolitik.org", "https://netzpolitik.org/feed/"),
    ("de", "analyse", "Amnesty Deutschland", "https://www.amnesty.de/rss/news", "menschenrechte"),
    ("de", "analyse", "Blätter für deutsche und internationale Politik", "https://www.blaetter.de/rss.xml"),
    ("de", "analyse", "Geschichte der Gegenwart", "https://geschichtedergegenwart.ch/feed/"),
    ("de", "podcast", "Lage der Nation", "https://feeds.lagedernation.org/feeds/ldn-mp3.xml"),
    ("de", "podcast", "Das Politikteil (Die Zeit)", "https://feeds.simplecast.com/yEFOt1A_"),
    ("de", "podcast", "Der Tag (Deutschlandfunk)", "https://www.deutschlandfunk.de/podcast-104.xml"),
    ("de", "podcast", "Interview der Woche (Deutschlandfunk)", "https://www.deutschlandfunk.de/interview-der-woche-102.xml"),
    ("de", "podcast", "Sein und Streit (Deutschlandfunk Kultur)", "https://www.deutschlandfunkkultur.de/sein-und-streit-das-philosophiemagazin-102.xml"),
    ("de", "podcast", "Sternstunde Philosophie (SRF)", "https://www.srf.ch/feed/podcast/sd/28426f25-6beb-4264-8ca9-ddddf717d6ea.xml"),
    ("de", "podcast", "Jung & Naiv", "https://jung-naiv.podigee.io/feed/mp3"),
    ("de", "podcast", "Thema des Tages (Der Standard)", "https://themadestages.podigee.io/feed/mp3"),
    ("de", "podcast", "Falter Radio", "https://feeds.acast.com/public/shows/1974c592-0a34-5e8c-a961-7ff704ac4476"),
    # ---------- Englischsprachiger Raum ----------
    ("en", "news", "The Guardian", G + "politics/rss"),
    ("en", "news", "The Guardian", G + "us-news/us-politics/rss"),
    ("en", "news", "The Guardian", G + "world/rss"),
    ("en", "news", "The New York Times", "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml"),
    ("en", "news", "The New York Times", "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"),
    ("en", "news", "BBC News", "https://feeds.bbci.co.uk/news/politics/rss.xml"),
    ("en", "news", "BBC News", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("en", "news", "NPR", "https://feeds.npr.org/1014/rss.xml"),
    ("en", "news", "Politico Europe", "https://www.politico.eu/feed/"),
    ("en", "thema", "The Guardian", G + "law/human-rights/rss", "menschenrechte"),
    ("en", "thema", "The Guardian", G + "technology/artificialintelligenceai/rss", "ki"),
    ("en", "thema", "The Guardian", G + "environment/climate-crisis/rss", "klima"),
    ("en", "thema", "The Guardian", G + "world/capital-punishment/rss", "todesstrafe"),
    ("en", "thema", "The Guardian", G + "world/protest/rss", "protest"),
    ("en", "thema", "The New York Times", N + "https://www.nytimes.com/topic/subject/human-rights-and-human-rights-violations/rss.xml", "menschenrechte"),
    ("en", "thema", "The New York Times", N + "https://www.nytimes.com/spotlight/artificial-intelligence/rss.xml", "ki"),
    ("en", "thema", "The New York Times", "https://rss.nytimes.com/services/xml/rss/nyt/Climate.xml", "klima"),
    ("en", "thema", "The New York Times", N + "https://www.nytimes.com/topic/subject/capital-punishment/rss.xml", "todesstrafe"),
    ("en", "meinung", "The Guardian view", G + "profile/editorial/rss"),
    ("en", "meinung", "The New York Times: Editorial Board", N + "www.nytimes.com/by/the-editorial-board/rss.xml"),
    ("en", "meinung", "The Economist: Leaders", "https://www.economist.com/leaders/rss.xml"),
    ("en", "meinung", "The Guardian: Opinion", G + "commentisfree/rss"),
    ("en", "meinung", "The New York Times: Opinion", "https://rss.nytimes.com/services/xml/rss/nyt/Opinion.xml"),
    ("en", "analyse", "The Conversation (UK)", "https://theconversation.com/uk/politics/articles.atom"),
    ("en", "analyse", "The Conversation (US)", "https://theconversation.com/us/politics/articles.atom"),
    ("en", "analyse", "The Guardian: Long read", G + "news/series/the-long-read/rss"),
    ("en", "analyse", "LSE: British Politics and Policy", "https://blogs.lse.ac.uk/politicsandpolicy/feed/"),
    ("en", "analyse", "LSE: European Politics and Policy", "https://blogs.lse.ac.uk/europpblog/feed/"),
    ("en", "analyse", "Just Security", "https://www.justsecurity.org/feed/", "recht"),
    ("en", "analyse", "Project Syndicate", "https://www.project-syndicate.org/rss"),
    ("en", "analyse", "Human Rights Watch", "https://www.hrw.org/rss/news", "menschenrechte"),
    ("en", "analyse", "Amnesty International", "https://www.amnesty.org/en/latest/news/feed/", "menschenrechte"),
    ("en", "analyse", "Death Penalty Information Center", "https://deathpenaltyinfo.org/feed", "todesstrafe"),
    ("en", "analyse", "Carbon Brief", "https://www.carbonbrief.org/feed/", "klima"),
    ("en", "podcast", "Today in Focus (The Guardian)", G + "news/series/todayinfocus/podcast.xml"),
    ("en", "podcast", "The Daily (The New York Times)", "https://feeds.simplecast.com/Sl5CSM3S"),
    ("en", "podcast", "The Ezra Klein Show", "https://feeds.simplecast.com/kEKXbjuJ"),
    ("en", "podcast", "Political Thinking with Nick Robinson (BBC)", "https://podcasts.files.bbci.co.uk/b08qmsh6.rss"),
    ("en", "podcast", "The Rest Is Politics: Leading", "https://feeds.megaphone.fm/GLT9029505120"),
    ("en", "podcast", "Past Present Future", "https://feeds.megaphone.fm/ARML2708405200"),
    ("en", "podcast", "Philosophy Bites", "https://rss.libsyn.com/shows/18828/destinations/14010.xml"),
    ("en", "podcast", "Outrage + Optimism", "https://feeds.acast.com/public/shows/6781112bec40818e0b501b6a", "klima"),
    ("en", "podcast", "Your Undivided Attention", "https://feeds.simplecast.com/rZ0cYk12", "ki"),
    # ---------- Französischsprachiger Raum ----------
    ("fr", "news", "France 24", F24 + "france/rss"),
    ("fr", "news", "France 24", F24 + "rss"),
    ("fr", "news", "TV5MONDE", "https://information.tv5monde.com/rss.xml"),
    ("fr", "news", "Le Monde", M + "politique/rss_full.xml"),
    ("fr", "news", "Le Monde", M + "international/rss_full.xml"),
    ("fr", "news", "franceinfo", "https://www.francetvinfo.fr/politique.rss"),
    ("fr", "news", "RFI", "https://www.rfi.fr/fr/france/rss"),
    ("fr", "news", "RFI", "https://www.rfi.fr/fr/rss"),
    ("fr", "news", "Libération", "https://www.liberation.fr/arc/outboundfeeds/rss/category/politique/?outputType=xml"),
    ("fr", "news", "Le Figaro", "https://www.lefigaro.fr/rss/figaro_politique.xml"),
    ("fr", "news", "Le Figaro", "https://www.lefigaro.fr/rss/figaro_elections.xml"),
    ("fr", "news", "La Libre (Belgique)", "https://www.lalibre.be/arc/outboundfeeds/rss/section/belgique/politique-belge/?outputType=xml"),
    ("fr", "news", "Le Temps (Suisse)", "https://www.letemps.ch/monde.rss"),
    ("fr", "thema", "Le Monde", M + "droits-humains/rss_full.xml", "menschenrechte"),
    ("fr", "thema", "Le Monde", M + "intelligence-artificielle/rss_full.xml", "ki"),
    ("fr", "thema", "Le Monde", M + "climat/rss_full.xml", "klima"),
    ("fr", "thema", "France 24", F24 + "tag/droits-de-l-homme/rss", "menschenrechte"),
    ("fr", "thema", "France 24", F24 + "tag/intelligence-artificielle/rss", "ki"),
    ("fr", "thema", "France 24", F24 + "tag/peine-de-mort/rss", "todesstrafe"),
    ("fr", "thema", "RFI", "https://www.rfi.fr/fr/tag/droits-de-l-homme/rss", "menschenrechte"),
    ("fr", "meinung", "Le Monde: éditorial", M + "editoriaux/rss_full.xml"),
    ("fr", "meinung", "Le Monde: idées", M + "idees/rss_full.xml"),
    ("fr", "meinung", "Libération: idées et débats", "https://www.liberation.fr/arc/outboundfeeds/rss/category/idees-et-debats/?outputType=xml"),
    ("fr", "meinung", "Le Figaro: Vox", "https://www.lefigaro.fr/rss/figaro_vox.xml"),
    ("fr", "meinung", "Le Temps: opinions", "https://www.letemps.ch/opinions.rss"),
    ("fr", "analyse", "The Conversation France", "https://theconversation.com/fr/politique/articles.atom"),
    ("fr", "analyse", "La Vie des idées", "https://laviedesidees.fr/spip.php?page=backend"),
    ("fr", "analyse", "AOC", "https://aoc.media/feed/"),
    ("fr", "analyse", "Le Grand Continent", "https://legrandcontinent.eu/fr/feed/"),
    ("fr", "analyse", "Human Rights Watch", "https://www.hrw.org/fr/rss/news", "menschenrechte"),
    ("fr", "podcast", "L'Heure du Monde (Le Monde)", "https://feeds.acast.com/public/shows/68db9d2509b1c365e44318ca"),
    ("fr", "podcast", "L'Esprit public (France Culture)", RF + "be0662d8-d0b5-442a-940d-837109136fe1.xml"),
    ("fr", "podcast", "L'Invité de 8h20 (France Inter)", RF + "ab4b2678-edce-11e1-a7b7-782bcb76618d.xml"),
    ("fr", "podcast", "L'Invité(e) des Matins (France Culture)", RF + "3681cfac-8727-4611-ad9a-fbe336cedfac.xml"),
    ("fr", "podcast", "Avec philosophie (France Culture)", RF + "b073d78c-d0d6-4910-b2e1-f9b370158a12.xml"),
    ("fr", "podcast", "Répliques (France Culture)", RF + "5a130e94-44df-11e5-9fe0-005056a87c89.xml"),
    ("fr", "podcast", "Cultures Monde (France Culture)", RF + "8f2d1e07-aaf1-4935-96d2-4307f470baec.xml"),
    ("fr", "podcast", "Chaleur humaine (Le Monde)", "https://feeds.acast.com/public/shows/68db9a016d92c33f9c2eff83", "klima"),
]
RANK = {}
for _f in FEEDS:
    RANK.setdefault(_f[2], len(RANK))


# ---------- Feeds lesen ----------

CORE = {"", "http://www.w3.org/2005/Atom", "http://purl.org/rss/1.0/"}


def split(tag):
    if tag[:1] == "{":
        ns, _, name = tag[1:].partition("}")
        return ns, name
    return "", tag


def when(s):
    s = (s or "").strip()
    if not s:
        return None
    try:
        d = parsedate_to_datetime(s)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(re.sub(r"\.\d+", "", s.replace("Z", "+00:00")))
        except ValueError:
            return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def clean(s):
    """Feed-Text ist fremde Eingabe: Tags raus, Entities auflösen. Escapt wird erst bei der Ausgabe."""
    s = re.sub(r"<[^>]*>", " ", s or "")
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def elements(stream):
    """Wie ET.iterparse, verzeiht aber Müll hinter dem Feed-Ende (kommt bei manchen WordPress-Feeds vor)."""
    seen = False
    try:
        for _, el in ET.iterparse(stream):
            seen = seen or split(el.tag)[1] in ("item", "entry")
            yield el
    except ET.ParseError:
        if not seen:
            raise


def parse(stream, limit=120):
    """Liest RSS 2.0, RSS 1.0 und Atom. Bricht nach `limit` Einträgen ab, damit riesige Podcast-Feeds nicht ganz geladen werden."""
    out = []
    for el in elements(stream):
        if split(el.tag)[1] not in ("item", "entry"):
            continue
        f = {}
        for c in el:
            ns, name = split(c.tag)
            if name == "link" and ns in CORE:
                if c.get("href") is None:
                    f.setdefault("link", (c.text or "").strip())
                elif c.get("rel", "alternate") == "alternate":
                    f.setdefault("link", c.get("href"))
            elif name == "enclosure":
                f.setdefault("audio", c.get("url", ""))
            elif name in ("title", "description", "summary", "content") and ns in CORE:
                f.setdefault(name, "".join(c.itertext()))
            elif name in ("pubDate", "published", "date", "updated"):
                f.setdefault(name, c.text)
        out.append({
            "title": clean(f.get("title")),
            "link": f.get("link") or f.get("audio") or "",
            "text": clean(f.get("description") or f.get("summary") or f.get("content")),
            "date": when(f.get("pubDate") or f.get("published") or f.get("date") or f.get("updated")),
        })
        el.clear()
        if len(out) >= limit:
            break
    return out


def select(feed, raw, now):
    """Aus den rohen Einträgen eines Feeds die frischen, brauchbaren machen (neueste zuerst)."""
    region, section, source, _url, *topic = feed
    _, days, cap = SECTIONS[section]
    items = []
    for it in raw:
        # Ohne Datum lässt sich Frische nicht beurteilen; nur http(s)-Links (kein javascript: o. Ä.)
        if not it["title"] or not it["date"] or not it["link"].startswith(("http://", "https://")):
            continue
        if not timedelta(hours=-1) <= now - it["date"] <= timedelta(days=days):
            continue
        if section in ("news", "thema") and OFFTOPIC.search(it["link"]):
            continue
        if region == "fr":  # französische Typografie: kein Zeilenumbruch vor : ; ? ! » und nach «
            it = {**it, **{k: re.sub(r" (?=[:;?!»])|(?<=«) ", chr(160), it[k]) for k in ("title", "text")}}  # chr(160) = geschütztes Leerzeichen
        blob = it["title"] + " " + it["text"][:400]
        items.append({**it, "region": region, "section": section, "source": source,
                      "topics": set(topic) | {k for k, (_, rx) in TOPICS.items() if rx.search(blob)}})
    items.sort(key=lambda i: i["date"], reverse=True)
    return items[:cap]


def load(feed, now):
    """Holt einen Feed, bei einem Fehler ein zweites Mal. Ergebnis: (Einträge, Fehlerhinweis oder None)."""
    for attempt in (1, 2):
        try:
            req = urllib.request.Request(feed[3], headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = parse(r)
            return select(feed, raw, now), None if raw else f"{feed[2]} (leer)"
        except Exception as e:  # ein kaputter Feed darf die Ausgabe nicht verhindern; er wird im Fuß genannt
            if attempt == 2:
                return [], f"{feed[2]} ({type(e).__name__})"


# ---------- Gleiche Geschichten zusammenfassen ----------

def stems(s):
    return {w[:6] for w in re.findall(r"[^\W\d_]{4,}", s.lower())}


def cos(a, b):
    return sum(x * b.get(s, 0) for s, x in a.items()) / (sqrt(sum(x * x for x in a.values()) * sum(x * x for x in b.values())) or 1)


def merge(groups):
    """Ein Durchgang: Jede Gruppe (Meldungen, Wortvektor) wandert zur ähnlichsten bisherigen Gruppe oder bleibt allein."""
    out = []
    for members, vec in groups:
        near = [g for g in out if abs(members[0]["date"] - g[0][0]["date"]) <= timedelta(hours=36)]
        best = max(near, key=lambda g: cos(vec, g[1]), default=None)
        if best and cos(vec, best[1]) >= SAME:
            best[0].extend(members)
            for s, x in vec.items():
                best[1][s] = best[1].get(s, 0) + x
        else:
            out.append([list(members), dict(vec)])
    return out


def cluster(items):
    """Gruppiert Meldungen, die dieselbe Geschichte erzählen. Jede Gruppe ist nach Datum sortiert, neueste zuerst.

    ponytail: grobe Wortstämme, tf-idf, Kosinus zum Gruppenschwerpunkt. Reicht für "wer berichtet noch darüber".
    Kleben Geschichten falsch zusammen: SAME erhöhen. Echtes Upgrade wären Embeddings.
    """
    df = Counter()
    for it in items:
        it["_t"], it["_x"] = stems(it["title"]), stems(it["text"][:300])
        df.update(it["_t"] | it["_x"])
    newest = sorted(items, key=lambda i: i["date"], reverse=True)
    vec = lambda it: {s: (2 if s in it["_t"] else 1) * log(len(items) / df[s]) for s in it["_t"] | it["_x"]}
    # Zweiter Durchgang führt Gruppen zusammen, die im ersten getrennt gestartet sind (sonst steht eine Geschichte doppelt oben)
    groups = merge(merge([[it], vec(it)] for it in newest))
    return [sorted(members, key=lambda i: i["date"], reverse=True) for members, _ in groups]


def pick_top(clusters):
    """Top-Meldungen: zuerst, worüber die meisten Quellen berichten, dann reihum die neueste Meldung je Quelle."""
    fresh = [c for c in clusters if any(i["section"] == "news" for i in c)]
    n_src = lambda c: len({i["source"] for i in c})
    multi = sorted((c for c in fresh if n_src(c) > 1), key=lambda c: (-n_src(c), -c[0]["date"].timestamp()))
    turn, singles = Counter(), []
    for c in fresh:
        if n_src(c) == 1:
            singles.append((turn[c[0]["source"]], RANK[c[0]["source"]], c))
            turn[c[0]["source"]] += 1
    return (multi + [c for *_, c in sorted(singles, key=lambda t: t[:2])])[:TOP]


# ---------- Seite schreiben ----------

DAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
e = html.escape


def stamp(d, now):
    d, today = d.astimezone(TZ), now.astimezone(TZ).date()
    ago = (today - d.date()).days
    return f"{d:%H:%M}" if ago <= 0 else f"gestern {d:%H:%M}" if ago == 1 else f"{d.day}.{d.month}."


def short(s, n=160):
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0].rstrip(",;:.") + " …"


def link(it, label):
    return f'<a href="{e(it["link"])}" target="_blank" rel="noopener noreferrer">{e(label)}</a>'


def entry(group, now, cls=""):
    """Ein Eintrag. `group` ist eine Liste: Hauptmeldung zuerst, danach dieselbe Geschichte bei anderen Quellen."""
    it, others = group[0], group[1:]
    topics = [t for t in TOPICS if any(t in i["topics"] for i in group)]
    teaser = "" if not it["text"] or it["text"].startswith(it["title"][:40]) else f'<p class="teaser">{e(short(it["text"]))}</p>'
    tags = "".join(f'<span class="tag">{e(TOPICS[t][0])}</span>' for t in topics)
    also = ""
    if others:
        names = ", ".join(e(i["source"]) for i in others)
        rows = "".join(f'<li><b>{e(i["source"])}</b> {link(i, i["title"])}</li>' for i in others)
        also = f'<details class="also"><summary>Auch bei {names}</summary><ul>{rows}</ul></details>'
    return (f'<article class="{cls}" data-t="{" ".join(topics)}"><h4>{link(it, it["title"])}</h4>{teaser}'
            f'<p class="meta"><span class="src">{e(it["source"])}</span>'
            f'<time datetime="{it["date"].isoformat()}">{stamp(it["date"], now)}</time>{tags}</p>{also}</article>')


def by_source(c):
    """Je Quelle die neueste Meldung der Gruppe, wichtigste Quelle zuerst."""
    first = {}
    for i in c:
        first.setdefault(i["source"], i)
    return sorted(first.values(), key=lambda i: RANK[i["source"]])


def render(items, failed, now):
    cols = {(r, s): [] for r in REGIONS for s in SECTIONS}
    for region in REGIONS:
        pool = [i for i in items if i["region"] == region]
        clusters = cluster([i for i in pool if i["section"] in ("news", "thema")])
        top = pick_top(clusters)
        shown = {id(c) for c in top}
        rest = [c for c in clusters if id(c) not in shown and any(i["topics"] for i in c)]
        cols[region, "news"] = [entry(by_source(c), now, "top") for c in top] + [entry(by_source(c), now, "extra") for c in rest]
        for s in ("meinung", "analyse", "podcast"):
            cols[region, s] = [entry([i], now) for i in sorted((i for i in pool if i["section"] == s), key=lambda i: RANK[i["source"]])]

    local = now.astimezone(TZ)
    dateline = f"{DAYS[local.weekday()]}, {local.day}. {MONTHS[local.month - 1]} {local.year}"
    radio = lambda name, key, label, on, lang="": (
        f'<input type="radio" name="{name}" id="{name}-{key}"{" checked" if on else ""}>'
        f'<label for="{name}-{key}"{lang}>{e(label)}</label>')
    regions = "".join(radio("r", r, sw, r == "de", f' lang="{r}"') for r, (_, sw) in REGIONS.items())
    topics = radio("t", "alle", "Alle", True) + "".join(radio("t", t, name, False) for t, (name, _) in TOPICS.items())

    bands = ""
    for s, (title, *_rest) in SECTIONS.items():
        if not title:
            continue
        inner = "".join(
            f'<div class="col" data-r="{r}" lang="{r}"><h3 lang="de">{e(REGIONS[r][0])}</h3>'
            f'{"".join(cols[r, s]) or "<p class=none lang=de>Heute nichts Neues.</p>"}</div>' for r in REGIONS)
        bands += f'<section class="band"><h2>{e(title)}</h2><div class="cols">{inner}</div></section>'

    css = STYLE
    for r in REGIONS:  # Handy: nur der gewählte Sprachraum
        css += f'@media (max-width:59.99rem){{:root:has(#r-{r}:checked) .col:not([data-r="{r}"]){{display:none}}}}\n'
    for t in TOPICS:   # Themenfilter ganz ohne JavaScript
        css += (f':root:has(#t-{t}:checked) article:not([data-t~="{t}"]){{display:none}}\n'
                f':root:has(#t-{t}:checked) article.extra[data-t~="{t}"]{{display:block}}\n'
                f':root:has(#t-{t}:checked) .col:not(:has(article[data-t~="{t}"]))::after{{content:"Dazu heute nichts."}}\n')

    sources = "".join(
        f'<p><b>{e(REGIONS[r][0])}:</b> {e(", ".join(dict.fromkeys(f[2] for f in FEEDS if f[0] == r)))}</p>' for r in REGIONS)
    missing = f'<p>Heute nicht erreichbar: {e(", ".join(failed))}.</p>' if failed else ""
    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex, nofollow">
<meta name="referrer" content="no-referrer">
<title>Presseschau in drei Sprachen</title>
<style>
{css}</style>
</head>
<body>
<div class="page">
<header>
<h1>Presseschau</h1>
<p>{dateline} · Stand {local:%H:%M} Uhr · Politik aus drei Sprachräumen</p>
</header>
<fieldset class="switch regions"><legend>Sprachraum</legend>{regions}</fieldset>
<fieldset class="switch topics"><legend>Thema</legend>{topics}</fieldset>
<main>{bands}</main>
<footer>
<details><summary>Quellen dieser Ausgabe</summary>{sources}</details>
{missing}
<p>Überschriften und Anrisse stammen aus den öffentlichen RSS-Feeds der genannten Medien. Jeder Link führt zum Original.</p>
</footer>
</div>
</body>
</html>
"""


STYLE = """/* Layout: drei Spalten = drei Sprachräume, Bänder = Rubriken. Am Handy ein Sprachraum zur Zeit, der Umschalter klebt oben. */
:root {
  --paper: #f2f5f7; --ink: #14202b; --muted: #54616e; --faint: #d9dfe5; --read: #7b8895;
  --marker: #ffe35a; --marker-ink: #2a2300;
  --serif: "Iowan Old Style", "Palatino Linotype", Palatino, Charter, Georgia, serif;
  --sans: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  color-scheme: light;
  padding-block: env(safe-area-inset-top, 0px) env(safe-area-inset-bottom, 0px);
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { --paper: #10171e; --ink: #e6ebf0; --muted: #9ba8b5; --faint: #27323c; --read: #74818e; --marker: #4f4409; --marker-ink: #ffe9a0; color-scheme: dark }
}
:root[data-theme="dark"] { --paper: #10171e; --ink: #e6ebf0; --muted: #9ba8b5; --faint: #27323c; --read: #74818e; --marker: #4f4409; --marker-ink: #ffe9a0; color-scheme: dark }
* { box-sizing: border-box }
body { margin: 0; background: var(--paper); color: var(--ink); font: 1rem/1.5 var(--sans); -webkit-text-size-adjust: 100% }
body::before { content: ""; position: fixed; inset: 0 0 auto; height: env(safe-area-inset-top, 0px); z-index: 10; background: var(--paper) }
.page { max-width: 88rem; margin-inline: auto; padding-block: 1.75rem 3rem; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)) }
a:focus-visible, summary:focus-visible { outline: 2px solid var(--ink); outline-offset: 2px }
header h1 { margin: 0; font: 700 2.1rem/1.1 var(--serif); letter-spacing: -.01em }
header p { margin: .35rem 0 0; color: var(--muted); font-size: .9rem; font-variant-numeric: tabular-nums }

/* Umschalter: echte Radio-Buttons, als Marken gestaltet */
.switch { border: 0; margin: 1.1rem 0 0; padding: 0; min-width: 0; display: flex; flex-wrap: wrap; align-items: center; gap: .4rem }
.switch legend { float: left; padding: 0; margin-right: .35rem; font-size: .72rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: var(--muted) }
.switch input { position: absolute; width: 1px; height: 1px; margin: 0; opacity: 0; pointer-events: none }
.switch label { cursor: pointer; padding: .28rem .8rem; border: 1px solid var(--faint); border-radius: 999px; font-size: .88rem; line-height: 1.4; user-select: none; -webkit-user-select: none }
.switch label:hover { border-color: var(--muted) }
.switch input:checked + label { background: var(--marker); border-color: var(--marker); color: var(--marker-ink); font-weight: 600 }
.switch input:focus-visible + label { outline: 2px solid var(--ink); outline-offset: 2px }
.regions { display: none }

.band { margin-top: 2.75rem }
.band > h2 { margin: 0 0 1.1rem; padding-top: .8rem; border-top: 3px solid var(--ink); font: 700 .8rem/1.2 var(--sans); letter-spacing: .12em; text-transform: uppercase }
.cols { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 2rem 2.75rem; align-items: start }
.col { min-width: 0; display: flex; flex-direction: column; gap: 1.15rem }
.col > h3 { margin: 0; font: 600 .8rem/1.2 var(--sans); color: var(--muted) }
.col::after, .none { margin: 0; color: var(--muted); font-size: .9rem }

article { min-width: 0 }
article h4 { margin: 0; font: 600 1.06rem/1.3 var(--serif); text-wrap: balance; overflow-wrap: anywhere }
article.top h4 { font-size: 1.22rem; line-height: 1.25 }
article h4 a { color: inherit; text-decoration: none }
article h4 a:hover { text-decoration: underline; text-underline-offset: .16em }
article h4 a:visited { color: var(--read) }
.teaser { margin: .3rem 0 0; font-size: .9rem; color: var(--muted); overflow-wrap: anywhere }
.meta { margin: .35rem 0 0; display: flex; flex-wrap: wrap; align-items: center; gap: .2rem .55rem; font-size: .78rem; color: var(--muted); font-variant-numeric: tabular-nums }
.src { font-weight: 600; color: var(--ink) }
.tag { padding: 0 .4rem; border-radius: 2px; background: var(--marker); color: var(--marker-ink); font-weight: 600 }
.also { margin-top: .4rem; font-size: .84rem }
.also summary { cursor: pointer; color: var(--muted); width: fit-content }
.also ul { margin: .4rem 0 0; padding: 0 0 0 .9rem; list-style: none; display: grid; gap: .35rem; border-left: 2px solid var(--faint) }
.also a { color: inherit; text-underline-offset: .16em }
.also a:visited { color: var(--read) }
.extra { display: none }

footer { margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--faint); color: var(--muted); font-size: .82rem; max-width: 65ch }
footer p { margin: .5rem 0 0 }
footer summary { cursor: pointer; width: fit-content }

@media (max-width: 59.99rem) {
  .regions { display: flex; flex-wrap: nowrap; position: sticky; top: env(safe-area-inset-top, 0px); z-index: 5; margin-top: .9rem; padding-block: .55rem; background: var(--paper); border-bottom: 1px solid var(--faint) }
  .regions legend { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%) }
  .regions label { flex: 1; text-align: center }
  .topics { margin-top: .8rem }
  .cols { grid-template-columns: minmax(0, 1fr) }
  .col > h3 { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%) }
  .band { margin-top: 2.25rem }
  header h1 { font-size: 1.8rem }
}
"""


def build():
    now = datetime.now(timezone.utc)
    with ThreadPoolExecutor(16) as pool:
        results = list(pool.map(lambda f: load(f, now), FEEDS))
    failed = list(dict.fromkeys(err for _, err in results if err))
    for name in failed:
        print("nicht erreichbar:", name, file=sys.stderr)
    # Lieber die gestrige Ausgabe stehen lassen als eine fast leere veröffentlichen (z. B. bei Netzausfall)
    if sum(1 for _, err in results if err) > len(FEEDS) / 2:
        sys.exit("Abbruch: mehr als die Hälfte der Feeds nicht erreichbar, docs/index.html bleibt unverändert.")
    # Doppelte zusammenführen. Meinung/Analyse/Podcast gewinnen gegen Nachrichten, damit ein Leitartikel nicht als Meldung läuft.
    order = sorted(range(len(FEEDS)), key=lambda i: (FEEDS[i][1] in ("news", "thema"), i))
    seen, items = {}, []
    for i in order:
        for it in results[i][0]:
            dup = seen.get(it["link"]) or seen.get((it["source"], it["title"]))
            if dup:
                dup["topics"] |= it["topics"]
                continue
            seen[it["link"]] = seen[it["source"], it["title"]] = it
            items.append(it)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(render(items, failed, now), encoding="utf-8")
    print(f"{OUT}: {len(items)} Einträge aus {len(FEEDS) - len(failed)} von {len(FEEDS)} Feeds")


def selftest():
    now = datetime(2026, 11, 16, 6, 0, tzinfo=timezone.utc)
    rss = """<rss><channel><item><title>Bundestag &amp; Klimaschutzgesetz</title><link>https://x.test/a</link>
      <description>&lt;p&gt;Die &lt;b&gt;Novelle&lt;/b&gt; kommt.&lt;/p&gt;&lt;script&gt;x&lt;/script&gt;</description>
      <pubDate>Mon, 16 Nov 2026 06:30:00 +0100</pubDate></item>
      <item><title>Böse</title><link>javascript:alert(1)</link><pubDate>Mon, 16 Nov 2026 06:30:00 +0100</pubDate></item>
      <item><title>Alt</title><link>https://x.test/alt</link><pubDate>Mon, 02 Nov 2026 06:30:00 +0100</pubDate></item></channel></rss>"""
    atom = """<feed xmlns="http://www.w3.org/2005/Atom"><entry><title type="html">Iran executes &lt;i&gt;two&lt;/i&gt;</title>
      <link rel="self" href="https://x.test/self"/><link rel="alternate" href="https://x.test/b"/>
      <summary>A.I. tools flagged the case</summary><published>2026-11-16T05:00:00Z</published></entry></feed>"""
    feed = ("de", "news", "Der Spiegel", "")
    a = select(feed, parse(io.BytesIO(rss.encode())), now)
    b = select(feed, parse(io.BytesIO(atom.encode())), now)
    assert [i["link"] for i in a] == ["https://x.test/a"], a          # javascript:-Link und alter Eintrag fallen raus
    assert a[0]["title"] == "Bundestag & Klimaschutzgesetz" and a[0]["text"] == "Die Novelle kommt. x"
    assert a[0]["topics"] == {"klima", "recht"}, a[0]["topics"]
    assert b[0]["link"] == "https://x.test/b" and b[0]["topics"] == {"todesstrafe", "ki"}, b
    tag = lambda t: {k for k, (_, rx) in TOPICS.items() if rx.search(t)}
    assert tag("Das politische Betriebsklima und die gesetzliche Rente") == set()
    assert tag("J'ai lu que la motion de censure échoue") == set()
    assert tag("Projet de loi sur l'IA: manifestation à Paris") == {"ki", "recht", "protest"}
    mk = lambda src, title, h: {"source": src, "section": "news", "title": title, "text": "", "date": now - timedelta(hours=h), "topics": set()}
    news = [mk("Der Spiegel", "Koalition einigt sich auf Rentenpaket", 1), mk("Die Zeit", "Rentenpaket: Koalition einigt sich nach langem Streit", 2),
            mk("FAZ", "Erdbeben erschüttert Norditalien", 3), mk("taz", "Bahnstreik legt Fernverkehr lahm", 4),
            mk("NZZ", "Schweiz stimmt über Mietrecht ab", 5), mk("Der Standard", "Nationalrat debattiert Budget", 6)]
    top = pick_top(cluster(news))
    assert sorted(i["source"] for i in top[0]) == ["Der Spiegel", "Die Zeit"], top[0]   # gleiche Geschichte, zwei Quellen, ganz oben
    assert len(top) == 5
    page = render([{**a[0], "title": "<script>alert(1)</script>"}], ["Kaputt <b>"], now)
    assert "<script>alert" not in page and "&lt;script&gt;alert(1)" in page and "Kaputt &lt;b&gt;" in page
    print("Selbsttest ok")


if __name__ == "__main__":
    selftest() if "--test" in sys.argv else build()
