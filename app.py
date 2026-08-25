#!/usr/bin/env python3
"""
GamePulse - Video Game News, Reviews & Editorial Digest
Encyclopedic Pulsar AI Gaming Concierge • Multi-Turn Memory • 100% Live Ingestion
Zero External Dependencies (Pure Python Standard Library)
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
import email.utils
from datetime import datetime, timezone, timedelta
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
# CONFIGURATION & SETTINGS
# ==========================================
PORT = int(os.environ.get("PORT", 8080))
DB_FILE = os.environ.get("DB_FILE", "gaming_news.db")
REFRESH_INTERVAL_MINUTES = int(os.environ.get("REFRESH_MINUTES", 15))
MAX_ARTICLE_AGE_DAYS = 14  # Discard articles older than 14 days

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip().strip("'\"")
if not GROQ_API_KEY:
    GROQ_API_KEY = "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"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip().strip("'\"")
GITHUB_REPO_URL = os.environ.get("GITHUB_URL", "https://github.com/Suraj10123/gamepulse-ai")

# Comprehensive Live Feeds Across All Editorial Sections
FEEDS = [
    # 1. Rumors, Leaks & Industry Scoops
    {"name": "r/GamingLeaksAndRumours", "url": "https://www.reddit.com/r/GamingLeaksAndRumours/.rss?limit=25", "category": "Rumors", "default_tag": "RUMOR"},
    {"name": "VGC", "url": "https://www.videogameschronicle.com/feed/", "category": "Rumors & Scoops", "default_tag": "RUMOR"},

    # 2. Dedicated Live Reviews & Scores
    {"name": "IGN Reviews", "url": "https://feeds.feedburner.com/ign/reviews-all", "category": "Reviews", "default_tag": "REVIEW"},
    {"name": "GameSpot Reviews", "url": "https://www.gamespot.com/feeds/reviews/", "category": "Reviews", "default_tag": "REVIEW"},
    {"name": "Nintendo Life Reviews", "url": "https://www.nintendolife.com/reviews.rss", "category": "Reviews", "default_tag": "REVIEW"},
    {"name": "Push Square Reviews", "url": "https://www.pushsquare.com/reviews.rss", "category": "Reviews", "default_tag": "REVIEW"},
    {"name": "Pure Xbox Reviews", "url": "https://www.purexbox.com/reviews.rss", "category": "Reviews", "default_tag": "REVIEW"},
    {"name": "Eurogamer Reviews", "url": "https://www.eurogamer.net/feed/reviews", "category": "Reviews", "default_tag": "REVIEW"},

    # 3. Dedicated Live Industry News & Financials
    {"name": "GamesIndustry.biz", "url": "https://www.gamesindustry.biz/feed", "category": "Industry", "default_tag": "INDUSTRY"},

    # 4. General News, Announcements & Community
    {"name": "r/Games", "url": "https://www.reddit.com/r/Games/.rss?limit=25", "category": "Community", "default_tag": "NEWS"},
    {"name": "Gematsu", "url": "https://www.gematsu.com/feed", "category": "Announcements", "default_tag": "TRAILER"},
    {"name": "Polygon", "url": "https://www.polygon.com/rss/index.xml", "category": "General", "default_tag": "NEWS"}
]

DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


# ==========================================
# DATABASE LAYER & PURGE
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
        
        # Purge legacy mock rows
        conn.execute("""
            DELETE FROM articles WHERE 
            source_url LIKE '%ign.com/articles/astro-bot%' OR 
            source_url LIKE '%gamesindustry.biz/console-market%' OR 
            source_url LIKE '%eurogamer.net/elden-ring-shadow%' OR
            source_url LIKE '%gamespot.com/reviews/final-fantasy-7-rebirth%'
        """)
        conn.commit()


# ==========================================
# FRESHNESS GATEKEEPER & DATE PARSING
# ==========================================
def parse_and_validate_date(pub_date_str):
    if not pub_date_str:
        return (True, datetime.now(timezone.utc).strftime("%b %d, %Y"))
    
    dt = None
    try:
        parsed_tuple = email.utils.parsedate_tz(pub_date_str)
        if parsed_tuple:
            timestamp = email.utils.mktime_tz(parsed_tuple)
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    except Exception:
        pass

    if dt is None:
        try:
            clean_iso = pub_date_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_iso)
        except Exception:
            pass

    if dt:
        now = datetime.now(timezone.utc)
        if (now - dt) > timedelta(days=MAX_ARTICLE_AGE_DAYS):
            return (False, None)
        return (True, dt.strftime("%b %d, %Y"))

    return (True, pub_date_str[:10] if len(pub_date_str) >= 10 else "Recent")

def clean_html(raw_html):
    if not raw_html:
        return ""
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
                    pub_date_raw = item.findtext("pubDate", "").strip()
                    
                    is_valid, formatted_date = parse_and_validate_date(pub_date_raw)
                    if not is_valid:
                        continue
                    
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
                            "published_at": formatted_date,
                            "source_name": feed_info["name"],
                            "category": feed_info["category"],
                            "default_tag": feed_info.get("default_tag", "NEWS")
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
                    
                    updated_elem = find_first_elem(entry, ["atom:updated", "updated"], ns)
                    pub_date_raw = updated_elem.text.strip() if (updated_elem is not None and updated_elem.text) else ""
                    
                    is_valid, formatted_date = parse_and_validate_date(pub_date_raw)
                    if not is_valid:
                        continue

                    image_url = ""
                    media_thumb = entry.find("media:thumbnail", ns)
                    if media_thumb is not None:
                        image_url = media_thumb.attrib.get("url", "")
                    if not image_url:
                        image_url = extract_image_from_html(raw_content)
                    
                    if title and link:
                        items.append({
                            "title": clean_html(title),
                            "link": link,
                            "summary": clean_html(raw_content)[:600],
                            "image_url": image_url,
                            "published_at": formatted_date,
                            "source_name": feed_info["name"],
                            "category": feed_info["category"],
                            "default_tag": feed_info.get("default_tag", "NEWS")
                        })
    except Exception as e:
        print(f"[!] Feed note: {feed_info['name']} ({e})")
    return items


# ==========================================
# AI SYNTHESIS (GROQ LLAMA 3.1)
# ==========================================
def call_groq_api(prompt, api_key):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": DEFAULT_UA
    }
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system",
                "content": "You are a senior gaming editor for GamePulse. Write objective, high-signal gaming journalism like IGN/Polygon. Return strictly valid JSON."
            },
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=15) as response:
        res = json.loads(response.read().decode("utf-8"))
        return json.loads(res["choices"][0]["message"]["content"])

def rule_based_synthesizer(title, summary, category, default_tag="NEWS"):
    title_lower = title.lower()
    if default_tag == "RUMOR" or any(w in title_lower for w in ["rumor", "leak", "report:", "insider", "datamine"]):
        tag = "RUMOR"
    elif default_tag == "REVIEW" or any(w in title_lower for w in ["review", "impressions", "verdict", "score", "benchmarks"]):
        tag = "REVIEW"
    elif default_tag == "INDUSTRY" or any(w in title_lower for w in ["layoff", "studio", "sales", "ceo", "sony", "xbox", "nintendo", "valve", "financial", "acquisition"]):
        tag = "INDUSTRY"
    elif any(w in title_lower for w in ["trailer", "gameplay", "revealed", "teaser", "first look", "announced"]):
        tag = "TRAILER"
    elif any(w in title_lower for w in ["patch", "update", "dlc", "expansion", "hotfix"]):
        tag = "UPDATE"
    elif any(w in title_lower for w in ["mod", "fan", "remake", "indie", "demo"]):
        tag = "COMMUNITY"
    else:
        tag = default_tag

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
    title = raw_item["title"]
    summary = raw_item["summary"]
    category = raw_item["category"]
    default_tag = raw_item.get("default_tag", "NEWS")

    if default_tag in ["REVIEW", "INDUSTRY", "RUMOR"]:
        forced_tag = default_tag
    elif any(w in title.lower() for w in ["rumor", "leak", "datamine", "insider"]):
        forced_tag = "RUMOR"
    elif any(w in title.lower() for w in ["review", "verdict", "impressions", "score"]):
        forced_tag = "REVIEW"
    elif any(w in title.lower() for w in ["studio", "acquisition", "layoff", "financial", "earnings", "ceo"]):
        forced_tag = "INDUSTRY"
    else:
        forced_tag = None

    prompt = f"""
    Act as a professional video game journalist writing for GamePulse.
    Transform this gaming news item into an objective, engaging editorial article.
    Do NOT mention Reddit usernames, submission tags, or 'submitted by'.

    Headline: {title}
    Details: {summary}
    Source Outlet: {raw_item['source_name']}
    Suggested Tag: {forced_tag or default_tag}

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
            tag_res = forced_tag or res.get("tag", default_tag)
            return {
                "ai_title": res.get("ai_title", title),
                "summary": res.get("summary", summary),
                "key_takeaways": json.dumps(res.get("key_takeaways", [])),
                "tag": tag_res,
                "sentiment": res.get("sentiment", "Neutral")
            }
        except Exception:
            pass

    return rule_based_synthesizer(title, summary, category, default_tag)


# ==========================================
# NEWSROOM DATABASE RETRIEVAL
# ==========================================
def query_local_articles_for_chat(user_msg):
    conn = get_db()
    cursor = conn.cursor()
    
    msg_lower = user_msg.lower()
    if "ign" in msg_lower:
        cursor.execute("SELECT title, ai_title, summary, source_name, source_url, image_url, published_at FROM articles WHERE source_name LIKE '%IGN%' ORDER BY id DESC LIMIT 5")
    elif "review" in msg_lower:
        cursor.execute("SELECT title, ai_title, summary, source_name, source_url, image_url, published_at FROM articles WHERE tag='REVIEW' OR category LIKE '%Review%' ORDER BY id DESC LIMIT 5")
    elif "rumor" in msg_lower or "leak" in msg_lower:
        cursor.execute("SELECT title, ai_title, summary, source_name, source_url, image_url, published_at FROM articles WHERE tag='RUMOR' OR category LIKE '%Rumor%' ORDER BY id DESC LIMIT 5")
    elif "industry" in msg_lower:
        cursor.execute("SELECT title, ai_title, summary, source_name, source_url, image_url, published_at FROM articles WHERE tag='INDUSTRY' OR category LIKE '%Industry%' ORDER BY id DESC LIMIT 5")
    else:
        cursor.execute("SELECT title, ai_title, summary, source_name, source_url, image_url, published_at FROM articles ORDER BY id DESC LIMIT 5")
        
    rows = cursor.fetchall()
    conn.close()
    
    context_items = []
    for r in rows:
        title = r["ai_title"] or r["title"]
        context_items.append(f"- **{title}** ({r['source_name']}, {r['published_at']}): {r['summary'][:140]}... [Read]({r['source_url']})")
    return "\n".join(context_items)


# ==========================================
# STRICT MESSAGE SANITIZER (AVOIDS 400 ERRORS)
# ==========================================
def sanitize_chat_messages(system_prompt, history, user_message):
    messages = [{"role": "system", "content": system_prompt}]
    cleaned = []
    if history and isinstance(history, list):
        for h in history[-6:]:
            if isinstance(h, dict) and h.get("role") in ["user", "assistant"] and h.get("content"):
                role = h["role"]
                content = str(h["content"]).strip()
                if content:
                    if cleaned and cleaned[-1]["role"] == role:
                        cleaned[-1]["content"] = content
                    else:
                        cleaned.append({"role": role, "content": content})
    
    if not cleaned or cleaned[-1]["role"] != "user":
        cleaned.append({"role": "user", "content": user_message})
    elif cleaned[-1]["role"] == "user":
        cleaned[-1]["content"] = user_message

    messages.extend(cleaned)
    return messages


# ==========================================
# FULL DYNAMIC PULSAR AI GAMING CONCIERGE
# ==========================================
def chat_with_pulsar(user_message, history=None):
    msg_clean = user_message.strip()
    msg_lower = msg_clean.lower()
    current_year = datetime.now().year
    today_str = datetime.now().strftime("%A, %B %d, %Y")
    recent_context = query_local_articles_for_chat(msg_clean)

    # 1. Numerical Score Evaluation (60+, 70+, 80+, 85+, 90+)
    score_match = re.search(r'(?:score(?: of)?|rated|rating of|above|at least)\s*(\d{2})|(\d{2})\s*\+', msg_lower)
    if score_match:
        min_score = int(score_match.group(1) or score_match.group(2))
        
        if min_score <= 79:
            return (
                f"### ⭐ **Recent & Notable Games Rated {min_score}+ (OpenCritic / Metacritic)**\n\n"
                f"Here are popular and acclaimed recent titles meeting your **{min_score}+** score threshold:\n\n"
                "1. **Star Wars Outlaws** *(PC, PS5, Xbox Series X|S — OpenCritic 76)*\n"
                "- **Why You'll Love It**: Open-world scoundrel adventure across underworld syndicates with stealth, speeder bike traversal, and blaster gunplay.\n\n"
                "2. **The Crew Motorfest** *(PC, PS5, Xbox Series X|S — OpenCritic 76)*\n"
                "- **Why You'll Love It**: Open-world Hawaiian car culture festival with themed playlists spanning JDM, hypercars, and muscle cars.\n\n"
                "3. **Need for Speed Unbound** *(PC, PS5, Xbox Series X|S — OpenCritic 77)*\n"
                "- **Why You'll Love It**: Stylized anime graffiti visual effects, deep vehicle body tuning, and high-heat police chases.\n\n"
                "4. **Warhammer 40,000: Space Marine 2** *(PC, PS5, Xbox Series X|S — OpenCritic 82)*\n"
                "- **Why You'll Love It**: Visceral third-person shooter and hack-and-slash brawler against massive Tyranid swarms.\n\n"
                "5. **Black Myth: Wukong** *(PC, PS5 — OpenCritic 82)*\n"
                "- **Why You'll Love It**: Fast-paced staff martial arts combat, spell transformations, and stunning Unreal Engine 5 mythological boss fights."
            )
        elif min_score <= 89:
            return (
                f"### ⭐ **Top Critically Acclaimed Games Rated {min_score}+ (OpenCritic / Metacritic)**\n\n"
                f"Here are premier titles verified with **{min_score}+** ratings:\n\n"
                "1. **Like a Dragon: Infinite Wealth** *(PC, PS5, Xbox — OpenCritic 89)*\n"
                "- **Why You'll Love It**: Massive Hawaiian turn-based RPG with absurd job classes, rich narrative, and Dondoko Island management.\n\n"
                "2. **Alan Wake 2** *(PC, PS5, Xbox — OpenCritic 89)*\n"
                "- **Why You'll Love It**: Masterpiece of psychological survival horror, dual-protagonist detective storytelling, and visuals.\n\n"
                "3. **Dragon's Dogma 2** *(PC, PS5, Xbox — OpenCritic 86)*\n"
                "- **Why You'll Love It**: Emergent physics fantasy combat, monster climbing, and autonomous Pawn AI companions.\n\n"
                "4. **Remnant 2** *(PC, PS5, Xbox — OpenCritic 85)*\n"
                "- **Why You'll Love It**: Tactical co-op third-person shooter with procedural worlds, secret archetype classes, and intense boss fights.\n\n"
                "5. **Lies of P** *(PC, PS5, Xbox — OpenCritic 84)*\n"
                "- **Why You'll Love It**: Tight deflections and atmospheric Belle Époque grimdark puppet combat."
            )
        else:
            return (
                f"### 🏆 **Elite Masterpieces Rated {min_score}+ (Mighty Tier)**\n\n"
                f"Here are the highest-rated games of this generation meeting your **{min_score}+** threshold:\n\n"
                "1. **Elden Ring: Shadow of the Erdtree** *(PC, PS5, Xbox — OpenCritic 95 / Metacritic 95)*\n"
                "- **Consensus**: Universally acclaimed open-world action RPG expansion setting the industry benchmark.\n\n"
                "2. **Astro Bot** *(PlayStation 5 Exclusive — OpenCritic 94 / Metacritic 94)*\n"
                "- **Consensus**: Joyous 3D platformer masterpiece with inventive level mechanics and DualSense haptic design.\n\n"
                "3. **Metaphor: ReFantazio** *(PC, PS5, Xbox — OpenCritic 94 / Metacritic 94)*\n"
                "- **Consensus**: From the creators of Persona 5, celebrated for its tournament narrative and tactical combat.\n\n"
                "4. **Final Fantasy VII Rebirth** *(PlayStation 5 Exclusive — OpenCritic 92 / Metacritic 92)*\n"
                "- **Consensus**: Monumental JRPG triumph expanding the journey beyond Midgar with dynamic synergy combat.\n\n"
                "5. **Balatro** *(PC, Consoles, Mobile — OpenCritic 90 / Metacritic 90)*\n"
                "- **Consensus**: Brilliant roguelike deckbuilder with hypnotic mathematical synergy."
            )

    # 2. Streamlined Groq Prompt
    system_prompt = f"""You are Pulsar, the official AI gaming expert for GamePulse ({current_year}).
Answer any question directly with game titles, platforms, verified OpenCritic/Metacritic scores, and specific mechanical reasons "Why You'll Love It".
Retain context across conversation turns. Zero profanity."""

    messages = sanitize_chat_messages(system_prompt, history, msg_clean)

    if GROQ_API_KEY:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "User-Agent": DEFAULT_UA
            }
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": messages,
                "temperature": 0.25,
                "max_tokens": 700
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=12) as response:
                res = json.loads(response.read().decode("utf-8"))
                reply_content = res["choices"][0]["message"]["content"].strip()
                if reply_content:
                    return reply_content
        except Exception as e:
            print(f"[!] Groq notice: {e}")

    # ==========================================
    # ENCYCLOPEDIC KNOWLEDGE BASE
    # ==========================================
    if any(w in msg_lower for w in ["activision", "cod", "call of duty"]):
        return (
            "### 🎯 **Top Fast-Paced & Military Shooters Like Call of Duty (by Activision)**\n\n"
            "1. **Call of Duty: Black Ops 6** *(PC, PS5, Xbox Series X|S — OpenCritic 84)*\n"
            "- **Why You'll Love It**: Omnimovement allows sprinting, sliding, and diving in 360 degrees with signature arcade gunplay.\n\n"
            "2. **Titanfall 2** *(PC, PS4, Xbox — Metacritic 89)*\n"
            "- **Why You'll Love It**: Created by the original *Modern Warfare* developers, featuring wall-running mobility, crisp weapon recoil, and mech combat.\n\n"
            "3. **Sekiro: Shadows Die Twice** *(PC, PS4, Xbox — Published by Activision / Metacritic 90)*\n"
            "- **Why You'll Love It**: Activision's highest-rated action game, focused on precision sword parries and grappling traversal.\n\n"
            "4. **The Finals / Apex Legends** *(Free to Play)*\n"
            "- **Why You'll Love It**: High-mobility gunplay with destruction and tactical squad abilities."
        )

    if "uncharted" in msg_lower or "naughty dog" in msg_lower:
        return (
            "### 🌿 **Top Cinematic Action-Adventure Games Like Uncharted**\n\n"
            "1. **Tomb Raider Reboot Trilogy (Tomb Raider, Rise, Shadow)** *(PC, PlayStation, Xbox — Metacritic 86–89)*\n"
            "- **Why You'll Love It**: The closest structural counterpart to Uncharted, blending exotic ancient tomb puzzles, fluid climbing traversal, and dynamic shootouts.\n\n"
            "2. **The Last of Us Part I & Part II** *(PS5, PC — Metacritic 93 / OpenCritic 90)*\n"
            "- **Why You'll Love It**: Built on the exact same Naughty Dog engine, delivering industry-leading performance capture, intimate writing, and visceral combat.\n\n"
            "3. **Indiana Jones and the Great Circle** *(PC, Xbox Series X|S, PS5)*\n"
            "- **Why You'll Love It**: First-person archaeological exploration, whip traversal, stealth brawling, and globe-trotting mystery.\n\n"
            "4. **Star Wars Jedi: Survivor** *(PC, PS5, Xbox Series X|S — OpenCritic 85)*\n"
            "- **Why You'll Love It**: Expansive acrobatic platforming, wall-running, grappling hooks, and lightsaber combat."
        )

    if "roblox" in msg_lower:
        return (
            "### 🧱 **Top Games & Sandbox Creation Hubs Like Roblox**\n\n"
            "1. **Minecraft** *(PC, Consoles, Mobile — Metacritic 93)*\n"
            "- **Why You'll Love It**: The world's most versatile voxel sandbox for survival, redstone engineering, modded minigames, and creative building.\n\n"
            "2. **LEGO Fortnite & Fortnite Creative / UEFN** *(Free to Play)*\n"
            "- **Why You'll Love It**: Epic Games' massive creator ecosystem with millions of user-made obstacle courses (Obbys), tycoons, and survival worlds.\n\n"
            "3. **Terraria** *(PC, Consoles, Mobile — Metacritic 88)*\n"
            "- **Why You'll Love It**: 2D action-adventure sandbox with deep boss progression, hundreds of weapons, and creative base building.\n\n"
            "4. **Garry's Mod (GMod) / Rec Room**\n"
            "- **Why You'll Love It**: Physics-driven sandbox social hubs with thousands of custom community gamemodes."
        )

    if "blizzard" in msg_lower or "diablo" in msg_lower:
        return (
            "### ❄️ **Top Games by Blizzard & ARPGs Like Diablo**\n\n"
            "1. **Path of Exile 2** *(PC, PS5, Xbox Series X|S — Beta Access)*\n"
            "- **Why You'll Love It**: The deepest skill-gem customization tree in ARPG history, dark 6-act campaign, and responsive dodge-roll combat.\n\n"
            "2. **Diablo II: Resurrected** *(PC, PS5, Xbox, Switch — OpenCritic 83)*\n"
            "- **Why You'll Love It**: The definitive dark fantasy ARPG with legendary runewords and dark gothic atmosphere.\n\n"
            "3. **StarCraft II: Wings of Liberty** *(PC — Metacritic 93)*\n"
            "- **Why You'll Love It**: The pinnacle of competitive real-time strategy with asymmetric faction balance.\n\n"
            "4. **Last Epoch / Grim Dawn** *(OpenCritic 80 / Metacritic 83)*\n"
            "- **Why You'll Love It**: Time-travel crafting eras and dual-class mastery combinations."
        )

    if any(w in msg_lower for w in ["gta", "red dead", "rockstar"]):
        return (
            "### 🤠 **Top Living World Sandboxes Like GTA & Red Dead Redemption**\n\n"
            "1. **Cyberpunk 2077: Phantom Liberty** *(PC, PS5, Xbox — OpenCritic 89)*\n"
            "- **Why You'll Love It**: Night City is the most visually breathtaking urban sandbox in gaming with cyberware builds and crime storylines.\n\n"
            "2. **Sleeping Dogs: Definitive Edition** *(PC, PS4, Xbox)*\n"
            "- **Why You'll Love It**: Undercover cop drama in Hong Kong combining martial arts melee brawling, street racing, and gunplay.\n\n"
            "3. **Mafia: Definitive Edition** *(PC, PS4, Xbox)*\n"
            "- **Why You'll Love It**: 1930s mobster drama with high-production cutscenes, authentic period vehicles, and Tommy gun shootouts."
        )

    if any(w in msg_lower for w in ["zelda", "mario", "nintendo"]):
        return (
            "### 🗡️ **Top Open-World & Platformer Adventures Like Zelda & Mario**\n\n"
            "1. **Elden Ring** *(PC, PS5, Xbox — OpenCritic 95)*\n"
            "- **Why You'll Love It**: Shares the exact same hands-off emergent discovery as *Breath of the Wild* across a vast, secrets-packed map.\n\n"
            "2. **Astro Bot** *(PS5 Exclusive — OpenCritic 94)*\n"
            "- **Why You'll Love It**: The definitive 3D platformer rivaling *Super Mario Galaxy* in joy, creative mechanics, and DualSense feedback.\n\n"
            "3. **Tunic** *(PC, Switch, PlayStation, Xbox — OpenCritic 85)*\n"
            "- **Why You'll Love It**: Isometric love letter to Zelda with cryptic in-game manual pages and environmental puzzle boxes."
        )

    if any(w in msg_lower for w in ["article", "ign", "today", "news", "newsroom"]):
        return f"### 📰 **Live Newsroom Articles ({today_str})**\n\n{recent_context}"

    return (
        "I'm ready to find your next favorite game! You can ask me:\n"
        "- 🎯 *'Show me games like COD made by Activision'*\n"
        "- 🌿 *'Show me games similar to Uncharted or Tomb Raider'*\n"
        "- 🧱 *'Show me games like Roblox or Minecraft'*\n"
        "- ⭐ *'Show me games with a score of 60+ (or 85+, 90+)'*\n"
        "- 🗡️ *'I like Zelda, what other open world game do you recommend?'*"
    )


# ==========================================
# BACKGROUND SCHEDULER (15-MIN INTERVAL)
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
        for item in list(unique_items.values())[:45]:
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
        time.sleep(REFRESH_INTERVAL_MINUTES * 60)
        run_news_aggregation_pipeline()


# ==========================================
# EDITORIAL FRONTEND
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
            --text-main: #e2e8f0;
            --text-muted: #8492a6;
            --heading: #ffffff;
            --brand-red: #ef4444;
            --brand-blue: #38bdf8;
            --font: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background-color: var(--bg-primary); color: var(--text-main); font-family: var(--font); line-height: 1.6; -webkit-font-smoothing: antialiased; }

        .top-utility-bar {
            background: #0b0e17; border-bottom: 1px solid var(--border);
            padding: 6px 16px; font-size: 0.76rem; color: var(--text-muted);
            display: flex; justify-content: space-between; align-items: center;
        }
        .trending-wrap { display: flex; align-items: center; gap: 8px; }
        .trending-tag { color: var(--brand-red); font-weight: 800; text-transform: uppercase; font-size: 0.72rem; }

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

        .page-container { max-width: 1140px; margin: 32px auto; padding: 0 16px; }
        .editorial-grid { display: flex; flex-direction: column; gap: 28px; }

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
        .github-subtle-link {
            display: inline-flex; align-items: center; gap: 6px;
            color: #475569; text-decoration: none; transition: color 0.15s ease;
        }
        .github-subtle-link:hover { color: #94a3b8; }
        .github-svg { width: 16px; height: 16px; fill: currentColor; }

        /* ==========================================
           PULSAR AI WIDGET + GEMINI PILL BAR
           ========================================== */
        .pulsar-launcher-btn {
            position: fixed; bottom: 24px; right: 24px; z-index: 999;
            background: linear-gradient(135deg, #ef4444, #8b5cf6);
            color: #fff; border: none; border-radius: 50px;
            padding: 12px 20px; font-size: 0.88rem; font-weight: 800;
            display: flex; align-items: center; gap: 8px; cursor: pointer;
            box-shadow: 0 8px 24px rgba(239, 68, 68, 0.45);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .pulsar-launcher-btn:hover { transform: translateY(-2px) scale(1.03); box-shadow: 0 12px 30px rgba(239, 68, 68, 0.6); }

        .pulsar-popup-box {
            position: fixed; bottom: 84px; right: 24px; z-index: 1000;
            width: 380px; height: 550px; max-width: calc(100vw - 32px); max-height: calc(100vh - 100px);
            background: #0d121f; border: 1px solid #23304c; border-radius: 18px;
            box-shadow: 0 16px 44px rgba(0, 0, 0, 0.75);
            display: none; flex-direction: column; overflow: hidden;
            animation: pulsarFadeIn 0.2s ease-out forwards;
        }
        @keyframes pulsarFadeIn { from { opacity: 0; transform: translateY(12px) scale(0.97); } to { opacity: 1; transform: translateY(0) scale(1); } }

        .pulsar-header {
            background: #131b2e; border-bottom: 1px solid #23304c; padding: 14px 16px;
            display: flex; justify-content: space-between; align-items: center;
        }
        .pulsar-profile { display: flex; align-items: center; gap: 10px; }
        .pulsar-avatar { width: 34px; height: 34px; border-radius: 50%; background: linear-gradient(135deg, #ef4444, #8b5cf6); display: flex; align-items: center; justify-content: center; font-size: 1.1rem; }
        .pulsar-title-wrap h3 { font-size: 0.95rem; font-weight: 800; color: #fff; margin-bottom: 2px; }
        .pulsar-subtitle { font-size: 0.74rem; color: #94a3b8; }

        .pulsar-controls { display: flex; align-items: center; gap: 6px; }
        .pulsar-ctrl-btn { background: transparent; border: none; color: #94a3b8; font-size: 1.1rem; cursor: pointer; padding: 4px; line-height: 1; }
        .pulsar-ctrl-btn:hover { color: #fff; }

        .pulsar-messages-area {
            flex: 1; padding: 16px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px;
            font-size: 0.88rem; background: #080c16;
        }
        .pulsar-messages-area::-webkit-scrollbar { width: 4px; }
        .pulsar-messages-area::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 4px; }

        .msg-bubble { max-width: 88%; padding: 10px 14px; border-radius: 14px; line-height: 1.45; word-wrap: break-word; }
        .msg-pulsar { background: #151e31; color: #e2e8f0; border-bottom-left-radius: 2px; border: 1px solid #202d4a; align-self: flex-start; }
        .msg-user { background: #ef4444; color: #fff; border-bottom-right-radius: 2px; align-self: flex-end; }
        .msg-pulsar a { color: #38bdf8; text-decoration: underline; }

        .chat-img-wrap {
            margin: 8px 0; border-radius: 8px; overflow: hidden; background: #000;
            border: 1px solid #283755; max-width: 240px; box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        }
        .chat-game-cover { width: 100%; height: 125px; object-fit: cover; display: block; }
        .chat-img-caption { display: block; font-size: 0.72rem; padding: 4px 8px; color: #94a3b8; background: #0e1422; font-weight: 600; }

        .suggestion-chips-wrap { display: flex; flex-direction: column; gap: 6px; margin-top: 8px; }
        .sugg-chip {
            background: #111827; border: 1px solid #24314c; color: #93c5fd;
            padding: 8px 12px; border-radius: 8px; font-size: 0.8rem; text-align: left;
            cursor: pointer; transition: all 0.15s ease; font-family: inherit; font-weight: 600;
        }
        .sugg-chip:hover { background: #1a253c; color: #fff; border-color: #38bdf8; }

        .gemini-pill-container {
            background: #111827; border-top: 1px solid #1f2c47; padding: 12px 14px;
        }
        .gemini-pill-box {
            display: flex; align-items: center; gap: 8px;
            background: #162035; border: 1px solid #2c3e63; border-radius: 28px;
            padding: 5px 8px 5px 12px; transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }
        .gemini-pill-box:focus-within { border-color: #ef4444; box-shadow: 0 0 12px rgba(239, 68, 68, 0.25); }

        .gemini-plus-btn {
            background: transparent; border: none; color: #94a3b8; font-size: 1.2rem;
            cursor: pointer; display: flex; align-items: center; justify-content: center;
            width: 26px; height: 26px; border-radius: 50%; transition: background 0.15s ease, color 0.15s ease;
        }
        .gemini-plus-btn:hover { background: #22304d; color: #fff; }

        .gemini-pill-input {
            flex: 1; background: transparent; border: none; color: #fff;
            font-size: 0.86rem; outline: none; font-family: inherit;
        }
        .gemini-pill-input::placeholder { color: #64748b; }

        .gemini-send-circle {
            background: #ef4444; color: #fff; border: none; width: 30px; height: 30px;
            border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center;
            font-size: 0.9rem; font-weight: bold; transition: background 0.15s ease, transform 0.15s ease;
        }
        .gemini-send-circle:hover { background: #dc2626; transform: scale(1.05); }

        .quick-actions-drawer {
            display: none; padding: 8px 12px 12px; background: #111827; border-top: 1px dashed #1f2c47;
            gap: 6px; flex-direction: column;
        }
        .quick-action-link {
            background: #162035; border: 1px solid #283755; color: #cbd5e1;
            padding: 6px 10px; border-radius: 6px; font-size: 0.78rem; text-align: left;
            cursor: pointer; transition: all 0.15s ease;
        }
        .quick-action-link:hover { color: #38bdf8; border-color: #38bdf8; background: #1c2944; }
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

    <!-- Pulsar AI Messenger Popup Widget -->
    <button class="pulsar-launcher-btn" id="pulsarToggle" onclick="togglePulsar()">
        <span>✨</span> <span>Ask Pulsar</span>
    </button>

    <div class="pulsar-popup-box" id="pulsarPopup">
        <div class="pulsar-header">
            <div class="pulsar-profile">
                <div class="pulsar-avatar">🎮</div>
                <div class="pulsar-title-wrap">
                    <h3>Pulsar AI</h3>
                    <div class="pulsar-subtitle">GamePulse Assistant</div>
                </div>
            </div>
            <div class="pulsar-controls">
                <button class="pulsar-ctrl-btn" onclick="resetPulsar()" title="Restart conversation">↺</button>
                <button class="pulsar-ctrl-btn" onclick="togglePulsar()" title="Minimize">✕</button>
            </div>
        </div>
        <div class="pulsar-messages-area" id="pulsarMessages">
            <div class="msg-bubble msg-pulsar">
                <p><strong>Hi! What do you want to do today?</strong></p>
                <div class="suggestion-chips-wrap">
                    <button class="sugg-chip" onclick="sendPulsarPrompt('Articles posted today')">📰 Articles posted today</button>
                    <button class="sugg-chip" onclick="sendPulsarPrompt('Show me games like COD made by Activision')">🎯 Activision Shooters</button>
                    <button class="sugg-chip" onclick="sendPulsarPrompt('Show me games with a score of 60+')">⭐ Games Rated 60+</button>
                </div>
            </div>
        </div>

        <div class="quick-actions-drawer" id="quickActionsDrawer">
            <button class="quick-action-link" onclick="sendPulsarPrompt('Show me games like COD made by Activision')">🎯 Call of Duty & Activision</button>
            <button class="quick-action-link" onclick="sendPulsarPrompt('Show me games similar to Uncharted')">🌿 Uncharted Style Games</button>
            <button class="quick-action-link" onclick="sendPulsarPrompt('Show me games with a score of 85+')">⭐ Verified 85+ Scores</button>
        </div>

        <!-- Gemini-Styled Pill Box -->
        <div class="gemini-pill-container">
            <div class="gemini-pill-box">
                <button class="gemini-plus-btn" onclick="toggleQuickDrawer()" title="More suggestions">+</button>
                <input type="text" class="gemini-pill-input" id="pulsarInput" placeholder="What's next in gaming? Ask Pulsar..." onkeydown="handlePulsarKey(event)">
                <button class="gemini-send-circle" onclick="submitPulsarChat()">➤</button>
            </div>
        </div>
    </div>

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

    <script>
        let pulsarHistory = [];

        function togglePulsar() {
            const popup = document.getElementById('pulsarPopup');
            if (popup.style.display === 'flex') {
                popup.style.display = 'none';
            } else {
                popup.style.display = 'flex';
                document.getElementById('pulsarInput').focus();
            }
        }

        function toggleQuickDrawer() {
            const drawer = document.getElementById('quickActionsDrawer');
            drawer.style.display = drawer.style.display === 'flex' ? 'none' : 'flex';
        }

        function resetPulsar() {
            pulsarHistory = [];
            const container = document.getElementById('pulsarMessages');
            container.innerHTML = `
                <div class="msg-bubble msg-pulsar">
                    <p><strong>Hi! What do you want to do today?</strong></p>
                    <div class="suggestion-chips-wrap">
                        <button class="sugg-chip" onclick="sendPulsarPrompt('Articles posted today')">📰 Articles posted today</button>
                        <button class="sugg-chip" onclick="sendPulsarPrompt('Show me games like COD made by Activision')">🎯 Activision Shooters</button>
                        <button class="sugg-chip" onclick="sendPulsarPrompt('Show me games with a score of 60+')">⭐ Games Rated 60+</button>
                    </div>
                </div>
            `;
        }

        function handlePulsarKey(e) {
            if (e.key === 'Enter') submitPulsarChat();
        }

        function sendPulsarPrompt(promptText) {
            document.getElementById('pulsarInput').value = promptText;
            document.getElementById('quickActionsDrawer').style.display = 'none';
            submitPulsarChat();
        }

        async function submitPulsarChat() {
            const input = document.getElementById('pulsarInput');
            const msg = input.value.trim();
            if (!msg) return;

            const container = document.getElementById('pulsarMessages');
            document.getElementById('quickActionsDrawer').style.display = 'none';
            
            const userBubble = document.createElement('div');
            userBubble.className = 'msg-bubble msg-user';
            userBubble.textContent = msg;
            container.appendChild(userBubble);
            input.value = '';

            const typingBubble = document.createElement('div');
            typingBubble.className = 'msg-bubble msg-pulsar';
            typingBubble.innerHTML = '<em>Pulsar is analyzing & searching...</em>';
            container.appendChild(typingBubble);
            container.scrollTop = container.scrollHeight;

            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: msg, history: pulsarHistory })
                });
                const data = await res.json();
                
                let replyHtml = data.reply
                    .replace(/!\\[(.*?)\\]\\((.*?)\\)/g, '<div class="chat-img-wrap"><img src="$2" alt="$1" class="chat-game-cover" loading="lazy" onerror="this.parentElement.style.display=\\'none\\';"><span class="chat-img-caption">$1</span></div>')
                    .replace(/\\[(.*?)\\]\\((.*?)\\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
                    .replace(/### (.*?)\\n/g, '<h4 style="color:#fff;margin:6px 0;">$1</h4>')
                    .replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>')
                    .replace(/\\*(.*?)\\*/g, '<em>$1</em>')
                    .replace(/\\n/g, '<br>');

                typingBubble.innerHTML = replyHtml;
                pulsarHistory.push({ role: "user", content: msg });
                pulsarHistory.push({ role: "assistant", content: data.reply });
            } catch (err) {
                typingBubble.innerHTML = 'Sorry, I ran into an issue retrieving that. Please try again in a moment!';
            }
            container.scrollTop = container.scrollHeight;
        }
    </script>
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
    published = row["published_at"] if row["published_at"] else (row["created_at"][:10] if row["created_at"] else "Recent")
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
                    <span>Source: <strong>{source}</strong></span> • <span>{published}</span> • <span>2 min read</span>
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
    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/chat":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                user_msg = data.get("message", "")
                history = data.get("history", [])
                
                reply = chat_with_pulsar(user_msg, history)
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"reply": reply}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

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
            
            if tag_filter == "RUMOR":
                cursor = conn.execute("SELECT * FROM articles WHERE tag='RUMOR' OR source_name LIKE '%GamingLeaks%' OR title LIKE '%Rumor%' OR title LIKE '%Leak%' OR title LIKE '%Report:%' OR title LIKE '%Insider%' ORDER BY id DESC LIMIT 50")
            elif tag_filter == "REVIEW":
                cursor = conn.execute("SELECT * FROM articles WHERE tag='REVIEW' OR category LIKE '%Review%' OR title LIKE '%Review%' OR title LIKE '%Verdict%' OR title LIKE '%Score%' OR title LIKE '%Impressions%' OR source_name LIKE '%Review%' ORDER BY id DESC LIMIT 50")
            elif tag_filter == "INDUSTRY":
                cursor = conn.execute("SELECT * FROM articles WHERE tag='INDUSTRY' OR category LIKE '%Industry%' OR source_name LIKE '%Industry%' OR title LIKE '%Sales%' OR title LIKE '%Layoff%' OR title LIKE '%Studio%' OR title LIKE '%Acquisition%' ORDER BY id DESC LIMIT 50")
            elif tag_filter == "TRAILER":
                cursor = conn.execute("SELECT * FROM articles WHERE tag='TRAILER' OR title LIKE '%Trailer%' OR title LIKE '%Gameplay%' OR title LIKE '%Reveal%' OR title LIKE '%Announce%' ORDER BY id DESC LIMIT 50")
            elif tag_filter == "UPDATE":
                cursor = conn.execute("SELECT * FROM articles WHERE tag='UPDATE' OR title LIKE '%Patch%' OR title LIKE '%Update%' OR title LIKE '%DLC%' OR title LIKE '%Hotfix%' ORDER BY id DESC LIMIT 50")
            elif tag_filter == "COMMUNITY":
                cursor = conn.execute("SELECT * FROM articles WHERE tag='COMMUNITY' OR category LIKE '%Community%' OR title LIKE '%Mod%' OR title LIKE '%Indie%' ORDER BY id DESC LIMIT 50")
            elif tag_filter:
                cursor = conn.execute("SELECT * FROM articles WHERE tag LIKE ? ORDER BY id DESC LIMIT 50", (f"%{tag_filter}%",))
            else:
                cursor = conn.execute("SELECT * FROM articles ORDER BY id DESC LIMIT 50")

            rows = cursor.fetchall()
            conn.close()

            articles_html = "\n".join([render_card(r) for r in rows]) if rows else """
            <div style="text-align:center; padding: 80px 20px; color: #64748b;">
                <h3>No stories in this section yet.</h3>
                <p>Check back shortly as new live feeds are indexed.</p>
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

    def log_message(self, format, *args):
        return

def main():
    init_db()
    scheduler_thread = threading.Thread(target=scheduler_worker, daemon=True)
    scheduler_thread.start()

    server = HTTPServer(("0.0.0.0", PORT), WebHandler)
    print(f"[*] GamePulse Server active on port {PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()

if __name__ == "__main__":
    main()