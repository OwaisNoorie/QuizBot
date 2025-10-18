# fetch_news.py
import feedparser, re
from bs4 import BeautifulSoup

FEEDS = [
    "http://feeds.bbci.co.uk/news/rss.xml",
    "https://www.reuters.com/world/rss",
    "https://www.aljazeera.com/xml/rss/all.xml",
]

def clean(text: str) -> str:
    if not text: return ""
    return BeautifulSoup(text, "html.parser").get_text(" ", strip=True)

def fetch_items(limit_per_feed=40):
    items = []
    for url in FEEDS:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:limit_per_feed]:
                title = clean(getattr(e, "title", ""))[:220]
                summary = clean(getattr(e, "summary", ""))[:400]
                link = getattr(e, "link", "")
                if title:
                    items.append({"title": title, "summary": summary, "link": link})
        except Exception:
            continue
    # de-dupe by normalized title
    seen, out = set(), []
    for it in items:
        key = re.sub(r"\W+", " ", it["title"].lower()).strip()
        if key not in seen:
            seen.add(key); out.append(it)
    return out
