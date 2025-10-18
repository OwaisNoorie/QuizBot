# answerer.py
import os, json, re, requests
import spacy
from fetch_news import fetch_items

DATA_DIR = "data"
NEWS_PATH = os.path.join(DATA_DIR, "news.json")
nlp = None

def _nlp():
    global nlp
    if nlp is None:
        nlp = spacy.load("en_core_web_sm")
    return nlp

def refresh_news():
    os.makedirs(DATA_DIR, exist_ok=True)
    items = fetch_items()
    with open(NEWS_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    return len(items)

def load_news():
    if not os.path.exists(NEWS_PATH): return []
    with open(NEWS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

# ---- Wikipedia helpers (no API key) ----
def wiki_search(q: str):
    # REST search
    r = requests.get("https://en.wikipedia.org/w/rest.php/v1/search/title",
                     params={"q": q, "limit": 1})
    if r.ok and r.json().get("pages"):
        title = r.json()["pages"][0]["title"]
        s = requests.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}")
        if s.ok:
            J = s.json()
            return {
                "title": title,
                "summary": J.get("extract", ""),
                "url": J.get("content_urls",{}).get("desktop",{}).get("page","")
            }
    return None

def simple_answer_from_wiki(q: str):
    hit = wiki_search(q)
    if not hit: return None
    # Shorten summary
    text = hit["summary"]
    if len(text) > 400:
        text = text[:400].rsplit(". ", 1)[0] + "."
    return {"answer": text, "sources": [{"title": hit["title"], "url": hit["url"]}]}

# ---- News matching ----
def keyword_candidates(q: str):
    doc = _nlp()(q)
    # pull nouns, proper nouns, orgs, people, places
    keys = {t.text for t in doc if t.pos_ in {"PROPN","NOUN"} and len(t.text) > 2}
    keys.update(e.text for e in doc.ents if e.label_ in {"PERSON","ORG","GPE","EVENT"})
    return {k.lower() for k in keys}

def news_answer(q: str, k=5):
    items = load_news()
    if not items: 
        return None
    keys = keyword_candidates(q)
    # very simple scoring: count keyword overlaps in title+summary
    scored = []
    for it in items:
        blob = (it["title"] + " " + it.get("summary","")).lower()
        score = sum(1 for kw in keys if kw and kw in blob)
        if score > 0:
            scored.append((score, it))
    if not scored: 
        return None
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:k]
    # Compose a compact answer from the best title/summary
    best = top[0][1]
    ans = best["title"]
    if best.get("summary"):
        ans += " — " + re.sub(r"\s+", " ", best["summary"]).strip()
    sources = [{"title": it["title"], "url": it["link"]} for _, it in top]
    # trim long answer
    if len(ans) > 500:
        ans = ans[:500].rsplit(". ", 1)[0] + "."
    return {"answer": ans, "sources": sources}

def answer_query(q: str):
    # 1) Try news first (current-affairs)
    ans = news_answer(q)
    if ans: 
        ans["mode"] = "news"
        return ans
    # 2) Fall back to Wikipedia summary
    ans = simple_answer_from_wiki(q)
    if ans:
        ans["mode"] = "wikipedia"
        return ans
    # 3) Nothing found
    return {"answer": "I couldn't find a reliable current-affairs snippet for that yet. Try rephrasing or hit Refresh.",
            "sources": [], "mode": "none"}
