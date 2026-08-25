#!/usr/bin/env python3
"""
GamePulse AI - 24-Hour AI Video Game News Aggregator & Blog
Includes Clickable Headlines/Images, Groq AI (Llama 3.1), and .env Auto-Loading.
100% Python Standard Library (Zero External Dependencies).
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
# AUTO-LOAD .ENV FILE (Zero Dependencies)
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
# CONFIGURATION & SETTINGS
# ==========================================
PORT = int(os.environ.get("PORT", 8080))
DB_FILE = os.environ.get("DB_FILE", "gaming_news.db")
REFRESH_INTERVAL_HOURS = int(os.environ.get("REFRESH_HOURS", 24))

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

FEEDS = [
    {"name": "r/Games", "url": "https://www.reddit.com/r/Games/.rss?limit=25", "category": "Community & Discussion"},
    {"name": "PC Gamer", "url": "https://www.pcgamer.com/rss/", "category": "PC Gaming"},
    {"name": "Eurogamer", "url": "https://www.eurogamer.net/feed", "category": "General Gaming"},
    {"name": "Polygon", "url": "https://www.polygon.com/rss/index.xml", "category": "Industry & Culture"},
    {"name": "IGN", "url": "https://feeds.feedburner.com/ign/all", "category": "General Gaming"}
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
# FEED AGGREGATION & IMAGE EXTRACTION
# ==========================================
def clean_html(raw_html):
    if not raw_html:
        return ""
    clean = re.sub(r'<[^>]+>', ' ', raw_html)
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
                entries = root.findall("atom:entry", ns)
                if not entries:
                    entries = root.findall("entry")

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
        print(f"[!] Warning: Could not fetch {feed_info['name']} ({e})")
    return items


# ==========================================
# AI SYNTHESIS (GROQ, GEMINI, FALLBACK)
# ==========================================
def call_groq_api(prompt, api_key):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "GamePulseAI/1.0"
    }
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system",
                "content": "You are a professional video game news editor for an r/Games-style blog. Return strictly valid JSON only."
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

def call_gemini_api(prompt, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2}
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=15) as response:
        result = json.loads(response.read().decode("utf-8"))
        text = result["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)

def rule_based_synthesizer(title, summary, category):
    title_lower = title.lower()
    if any(w in title_lower for w in ["trailer", "gameplay", "revealed", "teaser", "first look"]):
        tag = "TRAILER / REVEAL"
    elif any(w in title_lower for w in ["review", "impressions", "verdict", "score", "benchmarks"]):
        tag = "REVIEW"
    elif any(w in title_lower for w in ["patch", "update", "dlc", "expansion", "hotfix", "season"]):
        tag = "UPDATE / PATCH"
    elif any(w in title_lower for w in ["rumor", "leak", "report:", "insider"]):
        tag = "RUMOR"
    elif any(w in title_lower for w in ["layoff", "studio", "sales", "ceo", "sony", "xbox", "nintendo", "valve"]):
        tag = "INDUSTRY"
    elif any(w in title_lower for w in ["mod", "fan", "remake", "indie", "demo"]):
        tag = "COMMUNITY & INDIE"
    else:
        tag = "NEWS"

    clean_summary = summary if len(summary) > 60 else f"{title}. Key developments and community discussion across the gaming sphere."
    takeaways = [
        "Curated from active gaming community and press feeds.",
        "Reflects player feedback, gameplay changes, and industry implications.",
        "Complete original reporting and thread commentary linked below."
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
    Act as an r/Games style news editor. Synthesize this gaming news item into an objective, high-signal post.

    Headline: {title}
    Context: {summary}
    Source: {raw_item['source_name']}

    Return a JSON object with:
    - "ai_title": Objective, non-clickbait headline.
    - "summary": 2-paragraph editorial breakdown of what happened and why it matters to players.
    - "key_takeaways": Array of 2-3 bullet point takeaways.
    - "tag": One of ["INDUSTRY", "TRAILER / REVEAL", "UPDATE / PATCH", "REVIEW", "RUMOR", "COMMUNITY & INDIE", "NEWS"].
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
        except Exception as e:
            print(f"[!] Groq inference error ({e}). Using rule-based fallback.")
    elif GEMINI_API_KEY:
        try:
            res = call_gemini_api(prompt, GEMINI_API_KEY)
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
        print(f"\n[*] [{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}] Starting 24h News Refresh...")
        all_raw_items = []
        for feed in FEEDS:
            items = fetch_feed_items(feed)
            print(f"    - Ingested {len(items):2d} stories from {feed['name']}")
            all_raw_items.extend(items)

        unique_items = {it["link"]: it for it in all_raw_items if it.get("link")}
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        now_iso = datetime.now(timezone.utc).isoformat()

        conn = get_db()
        new_count = 0
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
            new_count += 1

        conn.execute("INSERT OR REPLACE INTO sync_meta (key, value) VALUES ('last_sync', ?)", (now_iso,))
        conn.commit()
        conn.close()
        print(f"[*] Aggregation Complete! {new_count} new synthesized articles stored.\n")
    except Exception as e:
        print(f"[!] Pipeline Error: {e}")
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
# WEB FRONTEND & SERVER
# ==========================================
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GamePulse AI • 24-Hour Video Game News Digest</title>
    <style>
        :root {
            --bg: #0d1117; --card-bg: #161b22; --border: #30363d; --accent: #58a6ff;
            --accent-hover: #79c0ff; --text: #c9d1d9; --heading: #f0f6fc; --muted: #8b949e;
            --tag-bg: #21262d; --green: #3fb950;
            --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background-color: var(--bg); color: var(--text); font-family: var(--font); line-height: 1.6; padding-bottom: 60px; }
        header { background: linear-gradient(180deg, #161b22 0%, #0d1117 100%); border-bottom: 1px solid var(--border); padding: 2.2rem 1rem 1.6rem; text-align: center; }
        .header-wrap { max-width: 920px; margin: 0 auto; }
        .logo { font-size: 2.3rem; font-weight: 800; color: var(--heading); letter-spacing: -0.5px; }
        .logo span.pulse { color: #ff4757; }
        .subtitle { color: var(--muted); margin-top: 6px; font-size: 1rem; }
        .status-pill { display: inline-flex; align-items: center; gap: 16px; margin-top: 18px; padding: 8px 18px; background: rgba(33, 38, 45, 0.8); border: 1px solid var(--border); border-radius: 30px; font-size: 0.86rem; flex-wrap: wrap; justify-content: center; }
        .dot { width: 8px; height: 8px; background-color: var(--green); border-radius: 50%; display: inline-block; box-shadow: 0 0 8px var(--green); }
        .btn-refresh { background-color: #238636; color: #fff; border: none; padding: 4px 12px; border-radius: 6px; font-weight: 600; cursor: pointer; font-size: 0.82rem; text-decoration: none; }
        .btn-refresh:hover { background-color: #2ea043; }
        .container { max-width: 920px; margin: 24px auto; padding: 0 16px; }
        .filters { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 22px; }
        .filter-chip { background: var(--card-bg); border: 1px solid var(--border); color: var(--muted); padding: 6px 14px; border-radius: 20px; font-size: 0.84rem; text-decoration: none; }
        .filter-chip.active, .filter-chip:hover { color: var(--heading); border-color: var(--accent); background: #1f242c; }
        .article { background-color: var(--card-bg); border: 1px solid var(--border); border-radius: 10px; margin-bottom: 24px; overflow: hidden; }
        .article:hover { border-color: #484f58; }
        .card-img-link { display: block; width: 100%; max-height: 380px; overflow: hidden; background-color: #0b0e14; border-bottom: 1px solid var(--border); text-decoration: none; }
        .card-img-link:hover .card-img { opacity: 0.92; }
        .card-img { width: 100%; height: 260px; object-fit: cover; display: block; }
        .card-body { padding: 22px; }
        .meta-row { display: flex; align-items: center; gap: 10px; font-size: 0.82rem; color: var(--muted); margin-bottom: 10px; flex-wrap: wrap; }
        .badge { background: var(--tag-bg); border: 1px solid rgba(88, 166, 255, 0.3); color: var(--accent); padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 0.74rem; text-transform: uppercase; }
        .title { font-size: 1.35rem; font-weight: 700; color: var(--heading); margin-bottom: 12px; line-height: 1.4; }
        .title-link { color: var(--heading); text-decoration: none; transition: color 0.15s ease; }
        .title-link:hover { color: var(--accent); text-decoration: underline; }
        .summary { color: var(--text); font-size: 0.98rem; line-height: 1.65; margin-bottom: 16px; }
        .takeaways { background: rgba(13, 17, 23, 0.75); border-left: 3px solid var(--accent); padding: 12px 16px; border-radius: 0 6px 6px 0; margin-bottom: 16px; }
        .takeaways-title { font-size: 0.8rem; font-weight: 700; text-transform: uppercase; color: var(--accent); margin-bottom: 6px; letter-spacing: 0.5px; }
        .takeaways ul { padding-left: 18px; font-size: 0.9rem; color: #b1bac4; }
        .takeaways li { margin-bottom: 4px; }
        .footer-row { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #21262d; padding-top: 14px; font-size: 0.84rem; }
        .source-link { color: var(--accent); text-decoration: none; font-weight: 600; }
        .source-link:hover { text-decoration: underline; color: var(--accent-hover); }
        .empty { text-align: center; padding: 60px 20px; color: var(--muted); }
        footer { text-align: center; color: var(--muted); font-size: 0.84rem; margin-top: 40px; }
    </style>
</head>
<body>
    <header>
        <div class="header-wrap">
            <h1 class="logo">🎮 GamePulse <span class="pulse">AI</span></h1>
            <p class="subtitle">Daily Video Game News Digest • AI Aggregated & Synthesized Every 24 Hours</p>
            <div class="status-pill">
                <span><span class="dot"></span> 24h Scheduler Active</span>
                <span>Engine: <strong>{{ENGINE_NAME}}</strong></span>
                <span>Last Updated: <strong>{{LAST_SYNC}}</strong></span>
                <span>Articles: <strong>{{TOTAL_COUNT}}</strong></span>
                <a href="/refresh" class="btn-refresh">⚡ Refresh Now</a>
            </div>
        </div>
    </header>
    <main class="container">
        <div class="filters">
            <a href="/" class="filter-chip {{ACT_ALL}}">All Topics</a>
            <a href="/?tag=INDUSTRY" class="filter-chip {{ACT_IND}}">Industry</a>
            <a href="/?tag=TRAILER" class="filter-chip {{ACT_TRAILER}}">Trailers & Reveals</a>
            <a href="/?tag=REVIEW" class="filter-chip {{ACT_REV}}">Reviews</a>
            <a href="/?tag=UPDATE" class="filter-chip {{ACT_UPD}}">Patches & DLC</a>
            <a href="/?tag=RUMOR" class="filter-chip {{ACT_RUMOR}}">Rumors</a>
            <a href="/?tag=COMMUNITY" class="filter-chip {{ACT_COMM}}">Indie & Mods</a>
        </div>
        <section>{{ARTICLES_LIST}}</section>
        <footer><p>GamePulse AI • Pure Python Blog • Powered by {{ENGINE_NAME}}</p></footer>
    </main>
</body>
</html>
"""

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
        <div class="takeaways">
            <div class="takeaways-title">⚡ Key Takeaways</div>
            <ul>{items}</ul>
        </div>
        """

    tag = row["tag"] or "NEWS"
    title = row["ai_title"] or row["title"]
    source = row["source_name"] or "Web"
    source_url = row["source_url"] or "#"
    created = row["created_at"][:10] if row["created_at"] else "Today"

    image_html = ""
    if row["image_url"]:
        image_html = f"""
        <a href="{source_url}" target="_blank" rel="noopener" class="card-img-link">
            <img src="{row['image_url']}" alt="{title}" class="card-img" loading="lazy" onerror="this.parentElement.style.display='none';">
        </a>
        """

    return f"""
    <article class="article">
        {image_html}
        <div class="card-body">
            <div class="meta-row">
                <span class="badge">{tag}</span>
                <span>via <strong>{source}</strong></span>
                <span>•</span>
                <span>{created}</span>
            </div>
            <h2 class="title"><a href="{source_url}" target="_blank" rel="noopener" class="title-link">{title}</a></h2>
            <div class="summary">{row['summary']}</div>
            {takeaways_html}
            <div class="footer-row">
                <span>Original Source: <em>{row['source_name']}</em></span>
                <a href="{source_url}" target="_blank" rel="noopener" class="source-link">View Original Discussion →</a>
            </div>
        </div>
    </article>
    """

class WebHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path, params = parsed.path, urllib.parse.parse_qs(parsed.query)

        if path == "/refresh":
            threading.Thread(target=run_news_aggregation_pipeline, daemon=True).start()
            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
            return

        if path == "/":
            tag_filter = params.get("tag", [None])[0]
            conn = get_db()
            cursor = conn.execute(
                "SELECT * FROM articles WHERE tag LIKE ? ORDER BY id DESC LIMIT 50" if tag_filter else "SELECT * FROM articles ORDER BY id DESC LIMIT 50",
                (f"%{tag_filter}%",) if tag_filter else ()
            )
            rows = cursor.fetchall()
            
            sync_cur = conn.execute("SELECT value FROM sync_meta WHERE key = 'last_sync'")
            last_sync_row = sync_cur.fetchone()
            last_sync_str = last_sync_row["value"][:16].replace("T", " ") + " UTC" if last_sync_row else "Just now"

            count_cur = conn.execute("SELECT COUNT(*) as count FROM articles")
            total_count = count_cur.fetchone()["count"]
            conn.close()

            engine_name = "Groq (Llama 3.1)" if GROQ_API_KEY else ("Gemini" if GEMINI_API_KEY else "Editorial Extractor")

            articles_html = "\n".join([render_card(r) for r in rows]) if rows else """
            <div class="empty">
                <h3>No gaming news indexed yet!</h3>
                <p>Click 'Refresh Now' above to pull the latest headlines from r/Games and gaming outlets.</p>
            </div>
            """

            html = HTML_TEMPLATE.replace("{{ARTICLES_LIST}}", articles_html)
            html = html.replace("{{LAST_SYNC}}", last_sync_str).replace("{{TOTAL_COUNT}}", str(total_count))
            html = html.replace("{{ENGINE_NAME}}", engine_name)
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
    active_engine = "Groq Cloud (Llama 3.1 8B - 100% Free)" if GROQ_API_KEY else ("Google Gemini" if GEMINI_API_KEY else "Built-in Editorial Extractor")
    print("=" * 65)
    print("🎮 GamePulse AI - 24-Hour Video Game News Aggregator & Blog")
    print("=" * 65)
    print(f"[*] Database: {DB_FILE}")
    print(f"[*] HTTP Port: {PORT}")
    print(f"[*] AI Engine: {active_engine}")
    print(f"[*] Refresh Cycle: Automated every {REFRESH_INTERVAL_HOURS} hours")

    scheduler_thread = threading.Thread(target=scheduler_worker, daemon=True)
    scheduler_thread.start()

    server = HTTPServer(("0.0.0.0", PORT), WebHandler)
    print(f"[*] Serving web interface at: http://localhost:{PORT}")
    
    # Auto-open browser
    threading.Timer(1.0, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()

if __name__ == "__main__":
    main()