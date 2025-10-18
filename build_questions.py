import json, os, random, re
import numpy as np
import spacy

DATA_DIR = "data"
OUT_PATH = os.path.join(DATA_DIR, "questions.json")
os.makedirs(DATA_DIR, exist_ok=True)

QUESTION_TYPES = {"PERSON", "ORG", "GPE", "LOC", "NORP", "EVENT"}

def pick_entity(doc):
    # Prefer PERSON/ORG/GPE for better distractors
    ents = [e for e in doc.ents if e.label_ in QUESTION_TYPES and len(e.text) > 2]
    if not ents:
        return None
    # rank: PERSON > ORG > GPE > others
    pref = {"PERSON":0, "ORG":1, "GPE":2, "LOC":3, "NORP":4, "EVENT":5}
    ents.sort(key=lambda e:(pref.get(e.label_, 9), -len(e.text)))
    return ents[0]

def mask_answer(text, answer):
    # Replace exact span once; fall back to pattern
    escaped = re.escape(answer)
    masked = re.sub(rf"\b{escaped}\b", "_____", text, count=1)
    if masked == text:
        # try a looser mask if case/spacing differs
        masked = text.replace(answer, "_____")
    return masked

def build_mcqs(items, nlp, max_q=40):
    # collect entities pool for distractors
    pool = {"PERSON": set(), "ORG": set(), "GPE": set(), "LOC": set(), "NORP": set(), "EVENT": set()}
    docs = [(i, nlp(i["title"])) for i in items]
    for _, d in docs:
        for e in d.ents:
            if e.label_ in pool and 2 < len(e.text) < 50:
                pool[e.label_].add(e.text)

    questions = []
    for it, doc in docs:
        ent = pick_entity(doc)
        if not ent: 
            continue
        answer = ent.text.strip()
        stem_src = it["title"]
        stem = mask_answer(stem_src, answer)
        label = ent.label_
        # distractors: sample from same-label pool (exclude answer)
        candidates = list(pool.get(label, set()) - {answer})
        random.shuffle(candidates)
        distractors = candidates[:6]  # grab more; we’ll dedup later

        # fallback: cross-label if too few
        if len(distractors) < 3:
            others = []
            for k, vals in pool.items():
                if k != label:
                    others.extend(list(vals))
            random.shuffle(others)
            distractors += others[: (3 - len(distractors))]

        opts = list({answer, *distractors})  # dedup
        random.shuffle(opts)
        # ensure 4 options
        if len(opts) < 4:
            continue
        opts = opts[:4]
        if answer not in opts:
            opts[0] = answer
            random.shuffle(opts)

        questions.append({
            "question": stem,
            "options": opts,
            "answer": answer,
            "label": label,
            "source": it["link"],
            "original": stem_src
        })
        if len(questions) >= max_q:
            break
    return questions

def refresh_questions():
    from fetch_news import fetch_items
    items = fetch_items()
    if not items:
        return []
    nlp = spacy.load("en_core_web_sm")
    qs = build_mcqs(items, nlp, max_q=50)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(qs, f, ensure_ascii=False, indent=2)
    return qs

if __name__ == "__main__":
    qs = refresh_questions()
    print(f"Built {len(qs)} questions → {OUT_PATH}")
