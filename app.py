# app.py
import os, json
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from answerer import refresh_news, answer_query

app = FastAPI(title="Current Affairs Q&A Bot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# Serve the UI
app.mount("/", StaticFiles(directory="web", html=True), name="web")

@app.post("/api/refresh")
def api_refresh():
    n = refresh_news()
    return {"fetched": n}

@app.get("/api/ask")
def api_ask(q: str = Query(..., min_length=2)):
    return answer_query(q)
