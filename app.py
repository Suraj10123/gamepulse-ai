#!/usr/bin/env python3
"""
GamePulse - Video Game News, Reviews & Editorial Digest
Production-grade editorial interface powered by standard library Python & Groq AI.
"""

import os
import sys
import time
import json
import sqlite3
import threading
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import re
import webbrowser
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==========================================
# AUTO-LOAD .ENV FILE
# ==========================================
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("'\""))

# ==========================================
# CONFIGURATION & ENVIRONMENT
# ==========================================
PORT = int(os.environ.get("PORT", 8080))
DB_FILE = os.environ.get("DB_FILE", "gaming_news.db")
REFRESH_INTERVAL_HOURS = int(os.environ.get("REFRESH_HOURS", 24))

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GITHUB_REPO_URL = os.environ.get("GITHUB_URL", "https://github.com/Suraj10123/gamepulse-ai")

FEEDS = [
    {"name": "r/Games", "url": "https://www.reddit.com/r/Games/.rss?limit=25", "category": "Community"},
    {"name": "PC Gamer", "url": "https://www.pcgamer.com/rss/", "category": "PC Gaming"},
    {"name": "Eurogamer", "url": "https://www.eurogamer.net/feed", "category": "Console & PC"},
    {"name": "Polygon", "url": "https://www.polygon.com/rss/index.xml", "category": "Industry"},
    {"name": "IGN", "url": "https://feeds.feedburner.com/ign/all", "category": "Gaming"}
]

DEFAULT_UA = "desktop:gamepulse.app:v1.0 (by /u/surajpatel)"


# ==========================================
# DATABASE LAYER
# ==========================================
def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                ai_title TEXT,
                summary TEXT,
                key_takeaways TEXT,
                category TEXT,
                tag TEXT,
                source_name TEXT,
                source_url TEXT UNIQUE,
                image_url TEXT,
                published_at TEXT,
                created_at TEXT,
                batch_date TEXT,
                sentiment TEXT
            )
        """)
        try:
            conn.execute("ALTER TABLE articles ADD COLUMN image_url TEXT")
        except sqlite3.OperationalError:
            pass

        conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()


# ==========================================
# FEED AGGREGATION & CLEANING
# ==========================================
def clean_html(raw_html):
    if not raw_html:
        return ""
    # Strip Reddit boilerplate
    text = re.sub(r'submitted by\s+/u/\S+(\s+\[link\])?(\s+\[comments\])?', '', raw_html, flags=re.IGNORECASE)
    text = re.sub(r'\[link\]|\[comments\]', '', text, flags=re.IGNORECASE)
    clean = re.sub(r'<[^>]+>', ' ', text)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&#39;', "'")

def extract_image_from_html(html_str):
    if not html_str:
        return ""
    match = re.search(r'<img[^>]+src=["\'](https?://[^"\']+)["\']', html_str, re.IGNORECASE)
    if match:
        url = match.group(1)
        if not any(sub in url.lower() for sub in ["1x1", "pixel", "avatar", "icon", "badge", "emoji"]):
            return url
    return ""

def find_first_elem(parent, tag_names, ns=None):
    for tag in tag_names:
        elem = parent.find(tag, ns) if ns else parent.find(tag)
        if elem is not None:
            return elem
    return None

def fetch_feed_items(feed_info):
    items = []
    req = urllib.request.Request(
        feed_info["url"],
        headers={"User-Agent": DEFAULT_UA, "Accept": "application/rss+xml, application/atom+xml, text/xml, */*"}
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            content = response.read()
            root = ET.fromstring(content)
            
            media_ns = {
                "media": "http://search.yahoo.com/mrss/",
                "atom": "http://www.w3.org/2005/Atom",
                "content": "http://purl.org/rss/1.0/modules/content/"
            }
            
            channel = root.find("channel")
            if channel is not None:
                for item in channel.findall("item"):
                    title = item.findtext("title", "").strip()
                    link = item.findtext("link", "").strip()
                    desc = item.findtext("description", "").strip()
                    pub_date = item.findtext("pubDate", "").strip()
                    
                    image_url = ""
                    enclosure = item.find("enclosure")
                    if enclosure is not None and "image" in enclosure.attrib.get("type", ""):
                        image_url = enclosure.attrib.get("url", "")
                    
                    if not image_url:
                        media_content = item.find("media:content", media_ns)
                        if media_content is not None:
                            image_url = media_content.attrib.get("url", "")
                            
                    if not image_url:
                        media_thumb = item.find("media:thumbnail", media_ns)
                        if media_thumb is not None:
                            image_url = media_thumb.attrib.get("url", "")
                            
                    if not image_url:
                        image_url = extract_image_from_html(desc)

                    if title and link:
                        items.append({
                            "title": clean_html(title),
                            "link": link,
                            "summary": clean_html(desc)[:600],
                            "image_url": image_url,
                            "published_at": pub_date,
                            "source_name": feed_info["name"],
                            "category": feed_info["category"]
                        })
            else:
                ns = {"atom": "http://www.w3.org/2005/Atom", "media": "http://search.yahoo.com/mrss/"}
                entries = root.findall("atom:entry", ns) or root.findall("entry")

                for entry in entries:
                    title_elem = find_first_elem(entry, ["atom:title", "title"], ns)
                    title = title_elem.text.strip() if (title_elem is not None and title_elem.text) else ""
                    
                    link_elem = find_first_elem(entry, ["atom:link", "link"], ns)
                    link = link_elem.attrib.get("href", "") if link_elem is not None else ""
                    
                    content_elem = find_first_elem(entry, ["atom:content", "content", "atom:summary", "summary"], ns)
                    raw_content = content_elem.text.strip() if (content_elem is not None and content_elem.text) else ""
                    
                    image_url = ""
                    media_thumb = entry.find("media:thumbnail", ns)
                    if media_thumb is not None:
                        image_url = media_thumb.attrib.get("url", "")
                    if not image_url:
                        image_url = extract_image_from_html(raw_content)

                    updated_elem = find_first_elem(entry, ["atom:updated", "updated"], ns)
                    pub_date = updated_elem.text.strip() if (updated_elem is not None and updated_elem.text) else ""
                    
                    if title and link:
                        items.append({
                            "title": clean_html(title),
                            "link": link,
                            "summary": clean_html(raw_content)[:600],
                            "image_url": image_url,
                            "published_at": pub_date,
                            "source_name": feed_info["name"],
                            "category": feed_info["category"]
                        })
    except Exception as e:
        print(f"[!] Feed notice: {feed_info['name']} ({e})")
    return items


# ==========================================
# AI SYNTHESIS (EDITORIAL ENGINE)
# ==========================================
def call_groq_api(prompt, api_key):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "GamePulse/1.0"
    }
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system",
                "content": "You are a senior gaming editor for GamePulse, a prestigious publication like IGN and Polygon. Write objective, high-signal, professional gaming journalism. Do not include Reddit metadata or usernames. Return strictly valid JSON."
            },
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=15) as response:
        res = json.loads(response.read().decode("utf-8"))
        return json.loads(res["choices"][0]["message"]["content"])

def rule_based_synthesizer(title, summary, category):
    title_lower = title.lower()
    if any(w in title_lower for w in ["trailer", "gameplay", "revealed", "teaser", "first look"]):
        tag = "TRAILER"
    elif any(w in title_lower for w in ["review", "impressions", "verdict", "score", "benchmarks"]):
        tag = "REVIEW"
    elif any(w in title_lower for w in ["patch", "update", "dlc", "expansion", "hotfix", "season"]):
        tag = "UPDATE"
    elif any(w in title_lower for w in ["rumor", "leak", "report:", "insider"]):
        tag = "RUMOR"
    elif any(w in title_lower for w in ["layoff", "studio", "sales", "ceo", "sony", "xbox", "nintendo", "valve"]):
        tag = "INDUSTRY"
    elif any(w in title_lower for w in ["mod", "fan", "remake", "indie", "demo"]):
        tag = "COMMUNITY"
    else:
        tag = "NEWS"

    clean_summary = summary if len(summary) > 60 else f"{title}. Full coverage and ongoing reporting across major gaming platforms."
    takeaways = [
        "Verified development and community coverage.",
        "Key gameplay, platform, or industry implications highlighted.",
        "Official announcement details and source commentary linked below."
    ]
    return {
        "ai_title": title,
        "summary": clean_summary,
        "key_takeaways": json.dumps(takeaways),
        "tag": tag,
        "sentiment": "Neutral"
    }

def synthesize_article(raw_item):
    title, summary, category = raw_item["title"], raw_item["summary"], raw_item["category"]
    prompt = f"""
    Act as a professional video game journalist writing for GamePulse.
    Transform this gaming news item into an objective, engaging editorial article.
    Do NOT mention Reddit usernames, submission tags, or 'submitted by'.

    Headline: {title}
    Details: {summary}
    Source Outlet: {raw_item['source_name']}

    Return a JSON object with:
    - "ai_title": Crisp, professional, non-clickbait editorial headline.
    - "summary": 2-paragraph journalistic breakdown covering what occurred and why it matters to players.
    - "key_takeaways": Array of 2-3 bullet point takeaways.
    - "tag": One of ["INDUSTRY", "TRAILER", "UPDATE", "REVIEW", "RUMOR", "COMMUNITY", "NEWS"].
    - "sentiment": "Positive", "Neutral", or "Critical".
    """

    if GROQ_API_KEY:
        try:
            res = call_groq_api(prompt, GROQ_API_KEY)
            return {
                "ai_title": res.get("ai_title", title),
                "summary": res.get("summary", summary),
                "key_takeaways": json.dumps(res.get("key_takeaways", [])),
                "tag": res.get("tag", "NEWS"),
                "sentiment": res.get("sentiment", "Neutral")
            }
        except Exception:
            pass

    return rule_based_synthesizer(title, summary, category)


# ==========================================
# PIPELINE & SCHEDULER
# ==========================================
pipeline_lock = threading.Lock()

def run_news_aggregation_pipeline():
    if not pipeline_lock.acquire(blocking=False):
        return

    try:
        all_raw_items = []
        for feed in FEEDS:
            items = fetch_feed_items(feed)
            all_raw_items.extend(items)

        unique_items = {it["link"]: it for it in all_raw_items if it.get("link")}
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        now_iso = datetime.now(timezone.utc).isoformat()

        conn = get_db()
        for item in list(unique_items.values())[:35]:
            cursor = conn.execute("SELECT id FROM articles WHERE source_url = ?", (item["link"],))
            if cursor.fetchone() is not None:
                continue

            ai_data = synthesize_article(item)
            conn.execute("""
                INSERT INTO articles (
                    title, ai_title, summary, key_takeaways, category, tag,
                    source_name, source_url, image_url, published_at, created_at, batch_date, sentiment
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item["title"], ai_data["ai_title"], ai_data["summary"], ai_data["key_takeaways"],
                item["category"], ai_data["tag"], item["source_name"], item["link"],
                item.get("image_url", ""), item["published_at"], now_iso, today_str, ai_data["sentiment"]
            ))

        conn.execute("INSERT OR REPLACE INTO sync_meta (key, value) VALUES ('last_sync', ?)", (now_iso,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[!] Sync note: {e}")
    finally:
        pipeline_lock.release()

def scheduler_worker():
    conn = get_db()
    cursor = conn.execute("SELECT COUNT(*) as count FROM articles")
    count = cursor.fetchone()["count"]
    conn.close()

    if count == 0:
        run_news_aggregation_pipeline()

    while True:
        time.sleep(REFRESH_INTERVAL_HOURS * 3600)
        run_news_aggregation_pipeline()


# ==========================================
# IGN/POLYGON GRADE EDITORIAL FRONTEND
# ==========================================
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GamePulse • Video Game News, Reviews & Editorial</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🎮</text></svg>">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #07090e;
            --bg-secondary: #0e131f;
            --bg-card: #131927;
            --border: #1e2638;
            --border-hover: #3b82f6;
            --text-main: #e2e8f0;
            --text-muted: #8492a6;
            --heading: #ffffff;
            --brand-red: #ef4444;
            --brand-blue: #38bdf8;
            --font: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background-color: var(--bg-primary); color: var(--text-main); font-family: var(--font); line-height: 1.6; -webkit-font-smoothing: antialiased; }

        /* Top Notification & Utility Bar */
        .top-utility-bar {
            background: #0b0e17; border-bottom: 1px solid var(--border);
            padding: 6px 16px; font-size: 0.76rem; color: var(--text-muted);
            display: flex; justify-content: space-between; align-items: center;
        }
        .trending-wrap { display: flex; align-items: center; gap: 8px; }
        .trending-tag { color: var(--brand-red); font-weight: 800; text-transform: uppercase; font-size: 0.72rem; }

        /* Masthead Header */
        header {
            background: rgba(11, 14, 23, 0.95);
            backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
            border-bottom: 1px solid var(--border);
            position: sticky; top: 0; z-index: 100;
        }
        .header-inner {
            max-width: 1140px; margin: 0 auto; padding: 14px 16px;
            display: flex; justify-content: space-between; align-items: center;
        }
        .brand-link { display: flex; align-items: center; gap: 10px; text-decoration: none; }
        .brand-logo { font-size: 1.65rem; font-weight: 900; color: #fff; letter-spacing: -0.8px; text-transform: uppercase; }
        .brand-logo span { color: var(--brand-red); }
        
        .main-nav { display: flex; gap: 4px; }
        .nav-item {
            color: #94a3b8; text-decoration: none; font-size: 0.86rem; font-weight: 700;
            padding: 6px 12px; border-radius: 6px; transition: all 0.15s ease;
        }
        .nav-item:hover, .nav-item.active { color: #fff; background: #1e2638; }

        /* Secondary Editorial Nav Strip */
        .sub-nav-strip {
            background: var(--bg-secondary); border-bottom: 1px solid var(--border);
            padding: 10px 16px;
        }
        .sub-nav-inner {
            max-width: 1140px; margin: 0 auto;
            display: flex; gap: 8px; overflow-x: auto; scrollbar-width: none;
        }
        .sub-nav-inner::-webkit-scrollbar { display: none; }
        .category-pill {
            background: var(--bg-card); border: 1px solid var(--border); color: #94a3b8;
            padding: 5px 14px; border-radius: 20px; font-size: 0.78rem; font-weight: 700;
            text-decoration: none; white-space: nowrap; transition: all 0.15s ease;
        }
        .category-pill:hover, .category-pill.active { background: #222d42; color: #fff; border-color: var(--brand-blue); }

        /* Feed & Layout */
        .page-container { max-width: 1140px; margin: 32px auto; padding: 0 16px; }
        .editorial-grid { display: flex; flex-direction: column; gap: 28px; }

        /* Article Card Design */
        .editorial-card {
            background: var(--bg-card); border: 1px solid var(--border);
            border-radius: 12px; overflow: hidden; transition: border-color 0.2s ease, transform 0.2s ease;
        }
        .editorial-card:hover { border-color: #334155; transform: translateY(-2px); }

        .banner-wrap { display: block; width: 100%; max-height: 420px; overflow: hidden; background: #000; text-decoration: none; }
        .banner-img { width: 100%; height: 300px; object-fit: cover; display: block; transition: transform 0.3s ease; }
        .banner-wrap:hover .banner-img { transform: scale(1.02); }

        .card-inner { padding: 26px; }
        .card-header-meta {
            display: flex; justify-content: space-between; align-items: center;
            gap: 12px; margin-bottom: 12px; flex-wrap: wrap;
        }
        .badge-group { display: flex; align-items: center; gap: 8px; }
        
        .cat-badge {
            padding: 3px 10px; border-radius: 4px; font-size: 0.72rem;
            font-weight: 800; text-transform: uppercase; letter-spacing: 0.6px;
        }
        .badge-industry { background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); }
        .badge-trailer { background: rgba(192, 132, 252, 0.15); color: #c084fc; border: 1px solid rgba(192, 132, 252, 0.3); }
        .badge-review { background: rgba(250, 204, 21, 0.15); color: #facc15; border: 1px solid rgba(250, 204, 21, 0.3); }
        .badge-update { background: rgba(74, 222, 128, 0.15); color: #4ade80; border: 1px solid rgba(74, 222, 128, 0.3); }
        .badge-rumor { background: rgba(251, 146, 60, 0.15); color: #fb923c; border: 1px solid rgba(251, 146, 60, 0.3); }
        .badge-community { background: rgba(45, 212, 191, 0.15); color: #2dd4bf; border: 1px solid rgba(45, 212, 191, 0.3); }
        .badge-news { background: rgba(148, 163, 184, 0.15); color: #cbd5e1; border: 1px solid rgba(148, 163, 184, 0.3); }

        .byline-meta { font-size: 0.8rem; color: var(--text-muted); }
        
        .article-headline {
            font-size: 1.4rem; font-weight: 800; color: var(--heading);
            line-height: 1.35; margin-bottom: 14px; letter-spacing: -0.3px;
        }
        .headline-link { color: inherit; text-decoration: none; transition: color 0.15s ease; }
        .headline-link:hover { color: var(--brand-blue); }

        .article-body { font-size: 0.96rem; color: #cbd5e1; line-height: 1.7; margin-bottom: 18px; }

        .highlights-card {
            background: rgba(7, 9, 14, 0.7); border-left: 3px solid var(--brand-red);
            border-radius: 0 8px 8px 0; padding: 14px 18px; margin-bottom: 20px;
        }
        .highlights-label { font-size: 0.76rem; font-weight: 800; text-transform: uppercase; color: var(--brand-red); letter-spacing: 0.6px; margin-bottom: 6px; }
        .highlights-card ul { padding-left: 18px; font-size: 0.88rem; color: #94a3b8; }
        .highlights-card li { margin-bottom: 4px; }

        .card-bottom-bar {
            display: flex; justify-content: space-between; align-items: center;
            border-top: 1px solid var(--border); padding-top: 16px; font-size: 0.84rem;
        }
        .read-original-link {
            color: var(--brand-blue); text-decoration: none; font-weight: 700;
            display: inline-flex; align-items: center; gap: 4px; transition: gap 0.15s ease;
        }
        .read-original-link:hover { text-decoration: underline; gap: 8px; }

        /* Professional Publication Footer */
        footer {
            background: #05070a; border-top: 1px solid var(--border);
            margin-top: 80px; padding: 48px 16px 24px;
        }
        .footer-inner { max-width: 1140px; margin: 0 auto; }
        .footer-columns {
            display: grid; grid-template-columns: 2fr 1fr 1fr;
            gap: 40px; margin-bottom: 40px;
        }
        @media (max-width: 768px) {
            .footer-columns { grid-template-columns: 1fr; gap: 24px; }
            .main-nav { display: none; }
        }
        .footer-col h4 { color: #fff; font-size: 0.92rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 14px; }
        .footer-col p { font-size: 0.86rem; color: var(--text-muted); line-height: 1.6; }
        .footer-links { list-style: none; }
        .footer-links li { margin-bottom: 8px; }
        .footer-links a { color: var(--text-muted); text-decoration: none; font-size: 0.84rem; transition: color 0.15s ease; }
        .footer-links a:hover { color: #fff; }

        .footer-sub-bar {
            border-top: 1px solid #131927; padding-top: 24px;
            display: flex; justify-content: space-between; align-items: center;
            font-size: 0.78rem; color: #475569; flex-wrap: wrap; gap: 12px;
        }
        
        /* Discreet, non-intrusive GitHub repository icon */
        .github-subtle-link {
            display: inline-flex; align-items: center; gap: 6px;
            color: #475569; text-decoration: none; transition: color 0.15s ease;
        }
        .github-subtle-link:hover { color: #94a3b8; }
        .github-svg { width: 16px; height: 16px; fill: currentColor; }
    </style>
</head>
<body>
    <div class="top-utility-bar">
        <div class="trending-wrap">
            <span class="trending-tag">Trending</span>
            <span>PlayStation 5 Pro • Nintendo Switch 2 • GTA VI • Unreal Engine 5</span>
        </div>
        <div>{{TODAY_DATE}}</div>
    </div>

    <header>
        <div class="header-inner">
            <a href="/" class="brand-link">
                <span class="brand-logo">GAME<span>PULSE</span></span>
            </a>
            <nav class="main-nav">
                <a href="/" class="nav-item {{ACT_ALL}}">All News</a>
                <a href="/?tag=REVIEW" class="nav-item {{ACT_REV}}">Reviews</a>
                <a href="/?tag=TRAILER" class="nav-item {{ACT_TRAILER}}">Trailers</a>
                <a href="/?tag=UPDATE" class="nav-item {{ACT_UPD}}">Patches & DLC</a>
                <a href="/?tag=INDUSTRY" class="nav-item {{ACT_IND}}">Industry</a>
            </nav>
        </div>
    </header>

    <div class="sub-nav-strip">
        <div class="sub-nav-inner">
            <a href="/" class="category-pill {{ACT_ALL}}">All Coverage</a>
            <a href="/?tag=INDUSTRY" class="category-pill {{ACT_IND}}">Industry & Studios</a>
            <a href="/?tag=TRAILER" class="category-pill {{ACT_TRAILER}}">Trailers & Reveals</a>
            <a href="/?tag=REVIEW" class="category-pill {{ACT_REV}}">Reviews & Scores</a>
            <a href="/?tag=UPDATE" class="category-pill {{ACT_UPD}}">Patches & Expansions</a>
            <a href="/?tag=RUMOR" class="category-pill {{ACT_RUMOR}}">Rumors & Leaks</a>
            <a href="/?tag=COMMUNITY" class="category-pill {{ACT_COMM}}">Indie & Mods</a>
        </div>
    </div>

    <main class="page-container">
        <section class="editorial-grid">
            {{ARTICLES_LIST}}
        </section>
    </main>

    <footer>
        <div class="footer-inner">
            <div class="footer-columns">
                <div class="footer-col">
                    <h4>About GamePulse</h4>
                    <p>GamePulse is an independent video game news digest delivering continuous editorial reporting, game reviews, trailers, and industry coverage across all major platforms.</p>
                </div>
                <div class="footer-col">
                    <h4>Platforms</h4>
                    <ul class="footer-links">
                        <li><a href="/?tag=INDUSTRY">PlayStation</a></li>
                        <li><a href="/?tag=INDUSTRY">Xbox Series X|S</a></li>
                        <li><a href="/?tag=INDUSTRY">Nintendo Switch</a></li>
                        <li><a href="/?tag=UPDATE">PC Gaming & Steam</a></li>
                    </ul>
                </div>
                <div class="footer-col">
                    <h4>Sections</h4>
                    <ul class="footer-links">
                        <li><a href="/?tag=TRAILER">Trailers & Footage</a></li>
                        <li><a href="/?tag=REVIEW">Reviews & Impressions</a></li>
                        <li><a href="/?tag=UPDATE">Patch Notes & DLC</a></li>
                        <li><a href="/?tag=COMMUNITY">Indie Spotlight</a></li>
                    </ul>
                </div>
            </div>
            <div class="footer-sub-bar">
                <div>&copy; 2026 GamePulse Media Network. All trademarks and media belong to their respective owners.</div>
                <a href="{{GITHUB_REPO_URL}}" target="_blank" rel="noopener" class="github-subtle-link" title="Open Source Project">
                    <svg class="github-svg" viewBox="0 0 24 24">
                        <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
                    </svg>
                    <span>GitHub</span>
                </a>
            </div>
        </div>
    </footer>
</body>
</html>
"""

def get_badge_class(tag):
    tag_clean = (tag or "").upper()
    if "INDUSTRY" in tag_clean: return "badge-industry"
    if "TRAILER" in tag_clean: return "badge-trailer"
    if "REVIEW" in tag_clean: return "badge-review"
    if "UPDATE" in tag_clean or "PATCH" in tag_clean: return "badge-update"
    if "RUMOR" in tag_clean: return "badge-rumor"
    if "COMMUNITY" in tag_clean or "INDIE" in tag_clean: return "badge-community"
    return "badge-news"

def render_card(row):
    takeaways = []
    try:
        if row["key_takeaways"]:
            takeaways = json.loads(row["key_takeaways"])
    except Exception:
        pass

    takeaways_html = ""
    if takeaways:
        items = "".join([f"<li>{t}</li>" for t in takeaways])
        takeaways_html = f"""
        <div class="highlights-card">
            <div class="highlights-label">Key Highlights</div>
            <ul>{items}</ul>
        </div>
        """

    tag = row["tag"] or "NEWS"
    title = row["ai_title"] or row["title"]
    source = row["source_name"] or "Editorial"
    source_url = row["source_url"] or "#"
    created = row["created_at"][:10] if row["created_at"] else "Today"
    badge_class = get_badge_class(tag)

    image_html = ""
    if row["image_url"]:
        image_html = f"""
        <a href="{source_url}" target="_blank" rel="noopener" class="banner-wrap">
            <img src="{row['image_url']}" alt="{title}" class="banner-img" loading="lazy" onerror="this.parentElement.style.display='none';">
        </a>
        """

    return f"""
    <article class="editorial-card">
        {image_html}
        <div class="card-inner">
            <div class="card-header-meta">
                <div class="badge-group">
                    <span class="cat-badge {badge_class}">{tag}</span>
                </div>
                <div class="byline-meta">
                    <span>Source: <strong>{source}</strong></span> • <span>{created}</span> • <span>2 min read</span>
                </div>
            </div>
            <h2 class="article-headline">
                <a href="{source_url}" target="_blank" rel="noopener" class="headline-link">{title}</a>
            </h2>
            <div class="article-body">{row['summary']}</div>
            {takeaways_html}
            <div class="card-bottom-bar">
                <span>By GamePulse Staff</span>
                <a href="{source_url}" target="_blank" rel="noopener" class="read-original-link">
                    Read Full Story on {source} &rarr;
                </a>
            </div>
        </div>
    </article>
    """

class WebHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path, params = parsed.path, urllib.parse.parse_qs(parsed.query)

        if path == "/":
            tag_filter = params.get("tag", [None])[0]
            conn = get_db()
            cursor = conn.execute(
                "SELECT * FROM articles WHERE tag LIKE ? ORDER BY id DESC LIMIT 50" if tag_filter else "SELECT * FROM articles ORDER BY id DESC LIMIT 50",
                (f"%{tag_filter}%",) if tag_filter else ()
            )
            rows = cursor.fetchall()
            conn.close()

            articles_html = "\n".join([render_card(r) for r in rows]) if rows else """
            <div style="text-align:center; padding: 80px 20px; color: #64748b;">
                <h3>No stories in this section yet.</h3>
                <p>Check back shortly for the latest gaming coverage.</p>
            </div>
            """

            today_date_str = datetime.now().strftime("%A, %B %d, %Y")

            html = HTML_TEMPLATE.replace("{{ARTICLES_LIST}}", articles_html)
            html = html.replace("{{TODAY_DATE}}", today_date_str)
            html = html.replace("{{GITHUB_REPO_URL}}", GITHUB_REPO_URL)
            html = html.replace("{{ACT_ALL}}", "active" if not tag_filter else "")
            html = html.replace("{{ACT_IND}}", "active" if tag_filter == "INDUSTRY" else "")
            html = html.replace("{{ACT_TRAILER}}", "active" if tag_filter == "TRAILER" else "")
            html = html.replace("{{ACT_REV}}", "active" if tag_filter == "REVIEW" else "")
            html = html.replace("{{ACT_UPD}}", "active" if tag_filter == "UPDATE" else "")
            html = html.replace("{{ACT_RUMOR}}", "active" if tag_filter == "RUMOR" else "")
            html = html.replace("{{ACT_COMM}}", "active" if tag_filter == "COMMUNITY" else "")

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Not Found")

    def log_message(self, format, *args):
        return

def main():
    init_db()
    scheduler_thread = threading.Thread(target=scheduler_worker, daemon=True)
    scheduler_thread.start()

    server = HTTPServer(("0.0.0.0", PORT), WebHandler)
    print(f"[*] GamePulse Server listening on port {PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()

if __name__ == "__main__":
    main()