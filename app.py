#!/usr/bin/env python3
"""
GamePulse - Video Game News, Reviews & Editorial Digest
Omni-Category Live Ingestion • Multi-Turn Memory • 20-Genre Pulsar AI
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
import ssl
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
MAX_ARTICLE_AGE_DAYS = 30  # Allow up to 30 days of active coverage

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip().strip("'\"")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip().strip("'\"")
GITHUB_REPO_URL = os.environ.get("GITHUB_URL", "https://github.com/Suraj10123/gamepulse-ai")

# Comprehensive Live Feeds Across All Editorial Sections
FEEDS = [
    # 1. Dedicated Live Reviews & Scores
    {"name": "IGN Reviews", "url": "https://feeds.feedburner.com/ign/reviews-all", "category": "Reviews", "default_tag": "REVIEW"},
    {"name": "GameSpot Reviews", "url": "https://www.gamespot.com/feeds/reviews/", "category": "Reviews", "default_tag": "REVIEW"},
    {"name": "Eurogamer Reviews", "url": "https://www.eurogamer.net/feed/reviews", "category": "Reviews", "default_tag": "REVIEW"},
    {"name": "Push Square Reviews", "url": "https://www.pushsquare.com/reviews.rss", "category": "Reviews", "default_tag": "REVIEW"},
    {"name": "Nintendo Life Reviews", "url": "https://www.nintendolife.com/reviews.rss", "category": "Reviews", "default_tag": "REVIEW"},

    # 2. Dedicated Live Industry News & Financials
    {"name": "GamesIndustry.biz", "url": "https://www.gamesindustry.biz/feed", "category": "Industry", "default_tag": "INDUSTRY"},

    # 3. Dedicated Live Patches, Updates & Expansions
    {"name": "PC Gamer Updates", "url": "https://www.pcgamer.com/rss/", "category": "Updates & DLC", "default_tag": "UPDATE"},
    {"name": "Rock Paper Shotgun", "url": "https://www.rockpapershotgun.com/feed", "category": "Updates & DLC", "default_tag": "UPDATE"},
    {"name": "r/pcgaming Updates", "url": "https://www.reddit.com/r/pcgaming/.rss?limit=25", "category": "Updates & DLC", "default_tag": "UPDATE"},

    # 4. Rumors, Leaks & Industry Scoops
    {"name": "r/GamingLeaksAndRumours", "url": "https://www.reddit.com/r/GamingLeaksAndRumours/.rss?limit=25", "category": "Rumors", "default_tag": "RUMOR"},
    {"name": "VGC", "url": "https://www.videogameschronicle.com/feed/", "category": "Rumors & Scoops", "default_tag": "RUMOR"},

    # 5. Announcements, Trailers & Community
    {"name": "Gematsu", "url": "https://www.gematsu.com/feed", "category": "Announcements", "default_tag": "TRAILER"},
    {"name": "Polygon", "url": "https://www.polygon.com/rss/index.xml", "category": "General", "default_tag": "NEWS"},
    {"name": "r/Games", "url": "https://www.reddit.com/r/Games/.rss?limit=25", "category": "Community", "default_tag": "COMMUNITY"}
]

DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Curated High-Signal Seed Articles Across All Categories
SEED_ARTICLES = [
    # REVIEWS & SCORES
    {
        "title": "Astro Bot Review - A Joyous 3D Platforming Masterpiece on PS5",
        "ai_title": "Astro Bot Review: The Benchmark for Modern 3D Platformers",
        "summary": "Team Asobi delivers a platforming masterpiece on PlayStation 5, celebrating 30 years of PlayStation heritage with inventive level gimmicks, flawless kinematic controls, and unmatched DualSense haptic feedback. OpenCritic rating: 94 (Mighty Tier).",
        "key_takeaways": json.dumps([
            "Benchmark 3D platforming level design rivaling Super Mario Galaxy.",
            "Inventive integration of DualSense adaptive triggers and motion controls.",
            "Over 150 VIP Bot cameos from classic and modern gaming history."
        ]),
        "category": "Reviews", "tag": "REVIEW", "source_name": "IGN Reviews",
        "source_url": "https://www.ign.com/articles/astro-bot-review",
        "image_url": "https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&w=1000&q=80",
        "published_at": "Recent", "sentiment": "Positive"
    },
    {
        "title": "Final Fantasy VII Rebirth Review - Monumental Open-World JRPG Triumph",
        "ai_title": "Final Fantasy VII Rebirth Review: A Landmark Action-RPG Achievement",
        "summary": "Square Enix expands the journey beyond Midgar into a breathtaking open-world adventure. Featuring deep Synergy ability combat, expansive regional exploration, and an unforgettable rendition of classic story beats. OpenCritic rating: 92.",
        "key_takeaways": json.dumps([
            "Dynamic party synergy attacks elevate active-time combat to new heights.",
            "Vast, secrets-filled open regions with varied traversal mechanics.",
            "Deep Queen's Blood card minigame and rich character banter."
        ]),
        "category": "Reviews", "tag": "REVIEW", "source_name": "GameSpot Reviews",
        "source_url": "https://www.gamespot.com/reviews/final-fantasy-7-rebirth-review/1900-6418182/",
        "image_url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=1000&q=80",
        "published_at": "Recent", "sentiment": "Positive"
    },
    {
        "title": "Silent Hill 2 Remake Review - Atmospheric Psychological Horror Reborn",
        "ai_title": "Silent Hill 2 Remake Review: Fog, Dread, and Masterful Sound Design",
        "summary": "Bloober Team and Konami deliver a faithful, deeply unsettling Unreal Engine 5 reconstruction of James Sunderland's nightmare. Modernized over-the-shoulder perspective, suffocating volumetric fog, and Akira Yamaoka's iconic score shine. OpenCritic rating: 86.",
        "key_takeaways": json.dumps([
            "Unreal Engine 5 volumetric fog and lighting create relentless dread.",
            "Tactile combat overhaul balances vulnerability with deliberate feedback.",
            "Expanded puzzle rooms and nuanced character performances."
        ]),
        "category": "Reviews", "tag": "REVIEW", "source_name": "Eurogamer Reviews",
        "source_url": "https://www.eurogamer.net/silent-hill-2-remake-review",
        "image_url": "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?auto=format&fit=crop&w=1000&q=80",
        "published_at": "Recent", "sentiment": "Positive"
    },

    # INDUSTRY & STUDIOS
    {
        "title": "Sony Announces PlayStation 5 Pro with Enhanced GPU, PSSR Upscaling and 2TB SSD",
        "ai_title": "Sony Unveils PS5 Pro: Technical Architecture and 60FPS Fidelity Vision",
        "summary": "Lead architect Mark Cerny revealed the PlayStation 5 Pro console, featuring 67% more Compute Units, advanced ray tracing hardware, and PlayStation Spectral Super Resolution (PSSR) machine learning upscaling.",
        "key_takeaways": json.dumps([
            "Upgraded GPU delivers 45% faster rendering performance for demanding titles.",
            "PSSR AI-driven upscaling boosts fidelity while maintaining 60FPS target.",
            "Standard 2TB high-speed NVMe storage and Wi-Fi 7 wireless connectivity."
        ]),
        "category": "Industry", "tag": "INDUSTRY", "source_name": "GamesIndustry.biz",
        "source_url": "https://www.gamesindustry.biz/sony-unveils-playstation-5-pro",
        "image_url": "https://images.unsplash.com/photo-1606813907291-d86efa9b94db?auto=format&fit=crop&w=1000&q=80",
        "published_at": "Recent", "sentiment": "Neutral"
    },

    # TRAILERS & REVEALS
    {
        "title": "Ghost of Yotei Revealed - Sucker Punch Showcases Feudal Japan Successor",
        "ai_title": "Ghost of Yotei: New Protagonist Atsu and Hokkaido Setting Detailed",
        "summary": "Sucker Punch Productions revealed Ghost of Yotei, set in 1603 around the base of Mount Yotei in northern Japan. Introducing new protagonist Atsu, dual-wielding katanas, firearms, and sprawling wilderness biomes.",
        "key_takeaways": json.dumps([
            "Takes place 300 years after Ghost of Tsushima in rugged northern Ezo.",
            "New weapon arsenal includes dual katanas, kusarigama, and early firearms.",
            "Built from the ground up to take native advantage of PS5 visual hardware."
        ]),
        "category": "Announcements", "tag": "TRAILER", "source_name": "Gematsu",
        "source_url": "https://www.gematsu.com/2024/09/ghost-of-yotei-announced-for-ps5",
        "image_url": "https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?auto=format&fit=crop&w=1000&q=80",
        "published_at": "Recent", "sentiment": "Positive"
    },

    # PATCHES, EXPANSIONS & DLC
    {
        "title": "Baldur's Gate 3 Patch 7 Launches with Official Mod Manager and 13 Evil Endings",
        "ai_title": "Baldur's Gate 3: Patch 7 Modding Toolkit & Cinematic Endings Breakdown",
        "summary": "Larian Studios has deployed Patch 7 for Baldur's Gate 3, introducing the integrated in-game mod manager, official modding tools, and 13 newly scored cinematic endings for evil playthroughs. The update also overhauls dynamic split-screen co-op mechanics.",
        "key_takeaways": json.dumps([
            "Official in-game Mod Manager and mod authoring toolkit now live across all platforms.",
            "13 brand-new cinematic evil endings with unique cutscenes and custom musical scores.",
            "Dynamic split-screen co-op seamlessly merges viewports when characters are nearby."
        ]),
        "category": "Updates & DLC", "tag": "UPDATE", "source_name": "PC Gamer Updates",
        "source_url": "https://store.steampowered.com/news/app/1086940/view/4260047716942440871",
        "image_url": "https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=1000&q=80",
        "published_at": "Recent", "sentiment": "Positive"
    },
    {
        "title": "Diablo IV: Vessel of Hatred Expansion Overhauls Progression & Adds Spiritborn Class",
        "ai_title": "Diablo IV: Vessel of Hatred Expansion & Level Cap Overhaul",
        "summary": "Blizzard's Vessel of Hatred expansion launches alongside a systemic rework of Diablo IV. The expansion introduces the Nahantu jungle region, the martial arts Spiritborn class, Runewords itemization, and resets the core level cap to 60.",
        "key_takeaways": json.dumps([
            "New Spiritborn class utilizing Centipede, Gorilla, Eagle, and Jaguar combat spirits.",
            "Runewords crafting system returns to enable customized skill triggers and defensive utility.",
            "Progression squish sets base level cap to 60 with 300 account-wide Paragon levels."
        ]),
        "category": "Updates & DLC", "tag": "UPDATE", "source_name": "PC Gamer Updates",
        "source_url": "https://news.blizzard.com/en-us/diablo4/24141676/vessel-of-hatred-launch-details",
        "image_url": "https://images.unsplash.com/photo-1538481199705-c710c4e965fc?auto=format&fit=crop&w=1000&q=80",
        "published_at": "Recent", "sentiment": "Positive"
    },

    # RUMORS & SCOOPS
    {
        "title": "Insider Report: FromSoftware Developing Unannounced Dark Fantasy IP with Sony",
        "ai_title": "FromSoftware Rumor: New Dark Fantasy Action RPG in Production",
        "summary": "Industry reports suggest FromSoftware is collaborating on an unannounced original dark fantasy action RPG under director Hidetaka Miyazaki, featuring faster-paced combat mechanics distinct from Elden Ring.",
        "key_takeaways": json.dumps([
            "New standalone dark fantasy IP planned rather than a direct sequel.",
            "Emphasizes tight, rhythmic parry-and-deflection combat.",
            "Targeted for high-end console and PC release cycle."
        ]),
        "category": "Rumors", "tag": "RUMOR", "source_name": "r/GamingLeaksAndRumours",
        "source_url": "https://www.reddit.com/r/GamingLeaksAndRumours/comments/fromsoftware_new_ip",
        "image_url": "https://images.unsplash.com/photo-1511512578047-dfb367046420?auto=format&fit=crop&w=1000&q=80",
        "published_at": "Recent", "sentiment": "Neutral"
    },

    # COMMUNITY & INDIE
    {
        "title": "Fallout: London Massive Total Conversion Mod Surpasses 1 Million Downloads",
        "ai_title": "Community Milestone: Fallout London Achieves Historic Modding Success",
        "summary": "Team FOLON's total conversion mod Fallout: London has surpassed one million downloads via GOG. Featuring a completely new post-apocalyptic British wasteland, full professional voice acting, and 90 hours of questlines.",
        "key_takeaways": json.dumps([
            "Fastest-redeemed independent game modification in digital storefront history.",
            "Complete overhaul with original factions, authentic London boroughs, and music.",
            "Demonstrates the power of independent PC modding communities."
        ]),
        "category": "Community", "tag": "COMMUNITY", "source_name": "r/Games",
        "source_url": "https://www.reddit.com/r/Games/comments/fallout_london_one_million",
        "image_url": "https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&w=1000&q=80",
        "published_at": "Recent", "sentiment": "Positive"
    }
]


# ==========================================
# DATABASE LAYER & SEED MIGRATION
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
        
        now_iso = datetime.now(timezone.utc).isoformat()
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        for item in SEED_ARTICLES:
            cursor = conn.execute("SELECT id FROM articles WHERE source_url = ?", (item["source_url"],))
            if cursor.fetchone() is None:
                conn.execute("""
                    INSERT INTO articles (
                        title, ai_title, summary, key_takeaways, category, tag,
                        source_name, source_url, image_url, published_at, created_at, batch_date, sentiment
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item["title"], item["ai_title"], item["summary"], item["key_takeaways"],
                    item["category"], item["tag"], item["source_name"], item["source_url"],
                    item["image_url"], item["published_at"], now_iso, today_str, item["sentiment"]
                ))

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
        diff_sec = (now - dt).total_seconds()
        if diff_sec > (MAX_ARTICLE_AGE_DAYS * 86400):
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
        ctx = ssl._create_unverified_context()
        with urllib.request.urlopen(req, timeout=12, context=ctx) as response:
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
    ctx = ssl._create_unverified_context()
    with urllib.request.urlopen(req, timeout=15, context=ctx) as response:
        res = json.loads(response.read().decode("utf-8"))
        return json.loads(res["choices"][0]["message"]["content"])

def rule_based_synthesizer(title, summary, category, default_tag="NEWS"):
    title_lower = title.lower()
    update_words = ["patch", "update", "dlc", "expansion", "hotfix", "season", "roadmap", "changelog", "rework", "overhaul", "notes"]
    
    if any(w in title_lower for w in update_words) and not any(w in title_lower for w in ["review", "verdict"]):
        tag = "UPDATE"
    elif default_tag in ["REVIEW", "INDUSTRY", "RUMOR", "UPDATE", "TRAILER", "COMMUNITY"]:
        tag = default_tag
    elif any(w in title_lower for w in ["rumor", "leak", "report:", "insider", "datamine"]):
        tag = "RUMOR"
    elif any(w in title_lower for w in ["review", "impressions", "verdict", "score", "benchmarks"]):
        tag = "REVIEW"
    elif any(w in title_lower for w in ["layoff", "studio", "sales", "ceo", "sony", "xbox", "nintendo", "valve", "financial", "acquisition"]):
        tag = "INDUSTRY"
    elif any(w in title_lower for w in ["trailer", "gameplay", "revealed", "teaser", "first look", "announced"]):
        tag = "TRAILER"
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

    # Priority tag detection
    update_words = ["patch", "update", "dlc", "expansion", "hotfix", "season", "roadmap", "changelog", "content drop", "rework", "overhaul", "notes"]
    if any(w in title.lower() for w in update_words) and not any(w in title.lower() for w in ["review", "verdict"]):
        forced_tag = "UPDATE"
    elif default_tag in ["REVIEW", "INDUSTRY", "RUMOR", "UPDATE", "TRAILER", "COMMUNITY"]:
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
    - "tag": One of ["REVIEW", "INDUSTRY", "TRAILER", "UPDATE", "RUMOR", "COMMUNITY", "NEWS"].
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
    if "patch" in msg_lower or "update" in msg_lower or "dlc" in msg_lower or "expansion" in msg_lower:
        cursor.execute("SELECT title, ai_title, summary, source_name, source_url, image_url, published_at FROM articles WHERE tag='UPDATE' OR category LIKE '%Update%' ORDER BY id DESC LIMIT 5")
    elif "ign" in msg_lower:
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
# MULTI-TIER RESILIENT AI CALLER
# ==========================================
def call_ai_backend(system_prompt, messages):
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
                "max_tokens": 800
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            ctx = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=12, context=ctx) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                reply_content = res["choices"][0]["message"]["content"].strip()
                if reply_content:
                    return reply_content
        except Exception as e:
            print(f"[!] Groq notice: {e}")

    if GEMINI_API_KEY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
            gemini_contents = []
            for m in messages:
                if m["role"] == "system":
                    continue
                role = "user" if m["role"] == "user" else "model"
                gemini_contents.append({"role": role, "parts": [{"text": m["content"]}]})
            gemini_payload = {
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": gemini_contents,
                "generationConfig": {"temperature": 0.3, "maxOutputTokens": 800}
            }
            data = json.dumps(gemini_payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
            ctx = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=12, context=ctx) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                text = res["candidates"][0]["content"]["parts"][0]["text"].strip()
                if text:
                    return text
        except Exception as e:
            print(f"[!] Gemini notice: {e}")

    return None


# ==========================================
# 20-GENRE ENCYCLOPEDIC PULSAR AI CONCIERGE
# ==========================================
def chat_with_pulsar(user_message, history=None):
    msg_clean = user_message.strip()
    msg_lower = msg_clean.lower()
    current_year = datetime.now().year
    today_str = datetime.now().strftime("%A, %B %d, %Y")
    recent_context = query_local_articles_for_chat(msg_clean)

    system_prompt = f"""You are Pulsar, the official AI gaming expert for GamePulse ({current_year}).
You possess encyclopedic knowledge across all 20 video game genres, developers, game engines, and franchises.
Answer any question directly and conversationally with game titles, platforms, verified OpenCritic/Metacritic scores, and detailed mechanical comparisons ("Why You'll Love It").
Retain context across conversation turns. Zero profanity.

LIVE NEWSROOM CONTEXT:
{recent_context}"""

    messages = sanitize_chat_messages(system_prompt, history, msg_clean)
    ai_reply = call_ai_backend(system_prompt, messages)
    if ai_reply:
        return ai_reply

    # ==========================================
    # MULTI-TURN CONTEXT RESOLUTION
    # ==========================================
    # Handles follow-ups like "PC", "PS5", "Xbox", "Switch"
    platforms = ["pc", "ps5", "ps4", "xbox", "switch", "playstation", "nintendo"]
    if msg_lower in platforms and history:
        prior_context = " ".join([h.get("content", "").lower() for h in history])
        target_platform = msg_clean.upper()

        if any(w in prior_context for w in ["diablo", "arpg", "path of exile", "poe", "loot", "blizzard"]):
            if "pc" in msg_lower:
                return (
                    "### ⚔️ **Best Action RPGs Like Diablo on PC**\n\n"
                    "1. **Path of Exile 2** *(PC — Beta Access)*\n"
                    "- **Why You'll Love It**: The undisputed gold standard for PC ARPGs with deep skill-gem linkages, WASD or click movement, and extensive endgame mapping.\n\n"
                    "2. **Last Epoch** *(PC — OpenCritic 80)*\n"
                    "- **Why You'll Love It**: Hits the sweet spot between Diablo IV's polish and PoE's depth with dedicated offline mode and creative time-travel masteries.\n\n"
                    "3. **Diablo II: Resurrected** *(PC — OpenCritic 83)*\n"
                    "- **Why You'll Love It**: Classic dark gothic atmosphere with legacy keyboard hotkeys and modern ultrawide monitor support.\n\n"
                    "4. **Grim Dawn** *(PC — Metacritic 83)*\n"
                    "- **Why You'll Love It**: Dual-class combinations and massive offline loot progression."
                )
            else:
                return (
                    f"### ⚔️ **Best Action RPGs Like Diablo on {target_platform}**\n\n"
                    "1. **Diablo IV: Vessel of Hatred** *(PS5, Xbox — OpenCritic 85)*\n"
                    "- **Why You'll Love It**: Responsive controller vibrations, the martial arts Spiritborn class, and couch co-op support.\n\n"
                    "2. **Diablo II: Resurrected** *(PS5, Xbox, Switch — OpenCritic 83)*\n"
                    "- **Why You'll Love It**: Tailored controller navigation, inventory shortcuts, and 60FPS console performance.\n\n"
                    "3. **Path of Exile 2** *(PS5, Xbox Series X|S — Beta Access)*\n"
                    "- **Why You'll Love It**: Twin-stick console combat controls with couch co-op support on the big screen.\n\n"
                    "4. **Titan Quest / Torchlight II**\n"
                    "- **Why You'll Love It**: Accessible mythology and steampunk dungeon crawling on consoles."
                )

        if any(w in prior_context for w in ["silent hill", "horror", "resident evil", "dead space"]):
            return (
                f"### 🔦 **Top Psychological Horror Games on {target_platform}**\n\n"
                f"1. **Silent Hill 2 Remake** *({'PS5 Exclusive on Console' if 'ps5' in msg_lower else 'PC, PS5'}) — OpenCritic 86*\n"
                "- Fog-choked psychological descent into guilt with tactile modern third-person combat.\n\n"
                "2. **Alan Wake 2** *(OpenCritic 89)*\n"
                "- Shifting dimensions in The Dark Place, detective mind palace investigations, and surreal live-action integration.\n\n"
                "3. **Resident Evil 4 Remake** *(OpenCritic 92)*\n"
                "- Masterpiece of survival tension, roundhouse parries, and resource management."
            )

        if any(w in prior_context for w in ["cod", "call of duty", "shooter", "activision", "fps"]):
            return (
                f"### 🎯 **Top Fast-Paced Shooters on {target_platform}**\n\n"
                "1. **Call of Duty: Black Ops 6** *(OpenCritic 84)*\n"
                "- 360-degree omnimovement allowing running, sliding, and diving in any direction.\n\n"
                "2. **Titanfall 2** *(Metacritic 89)*\n"
                "- Peak wall-running momentum, crisp weapon recoil, and mechanized Titan warfare.\n\n"
                "3. **Doom Eternal** *(OpenCritic 89)*\n"
                "- High-intensity demon slaying with shoulder flame cannons and meat-hook traversal."
            )

    # ==========================================
    # 20-GENRE SPELLING-TOLERANT ENGINE
    # ==========================================
    # 1. Diablo & Action RPGs
    if any(w in msg_lower for w in ["diablo", "diaablo", "arpg", "path of exile", "poe", "last epoch", "grim dawn", "loot"]):
        return (
            "### ⚔️ **Top Action RPGs and Isometric Dungeon Crawlers Like Diablo**\n\n"
            "If you love slaughtering demon hordes, theorycrafting deep skill trees, and hunting for legendary loot showers like in *Diablo*, here are the best games to play:\n\n"
            "1. **Path of Exile 2** *(PC, PS5, Xbox Series X|S — Beta Access)*\n"
            "- **Why You'll Love It**: The deepest skill-gem customization tree in ARPG history, dark 6-act campaign, and responsive dodge-roll combat.\n\n"
            "2. **Last Epoch** *(PC — OpenCritic 80)*\n"
            "- **Why You'll Love It**: Features dedicated offline play, an innovative in-game loot filter builder, and time-travel crafting across historical eras.\n\n"
            "3. **Diablo II: Resurrected** *(PC, PS5, Xbox, Switch — OpenCritic 83)*\n"
            "- **Why You'll Love It**: The gold standard of dark fantasy ARPGs with iconic runewords, potion management, and classic dark atmosphere.\n\n"
            "4. **Grim Dawn** *(PC, Xbox — Metacritic 83)*\n"
            "- **Why You'll Love It**: Allows you to combine any two classes into hybrid masteries with constellation passives and deep mod support.\n\n"
            "Are you looking to play on **PC, PS5, Xbox, or Switch**?"
        )

    # 2. Horror & Silent Hill
    if any(w in msg_lower for w in ["silent hill", "silenthill", "slient hill", "horror", "horor", "scary", "resident evil", "reident evil", "dead space", "alan wake", "signalis", "soma"]):
        return (
            "### 🔦 **Top Psychological & Survival Horror Games Like Silent Hill**\n\n"
            "1. **Silent Hill 2 Remake** *(PlayStation 5, PC — OpenCritic 86 / Metacritic 86)*\n"
            "- Faithful Unreal Engine 5 reconstruction of James Sunderland's nightmare in Silent Hill, with modernized combat and suffocating fog.\n\n"
            "2. **Alan Wake 2** *(PC, PS5, Xbox Series X|S — OpenCritic 89)*\n"
            "- Shifting psychological dimensions (The Dark Place), ritualistic murder mysteries, and live-action surrealism.\n\n"
            "3. **Signalis** *(PC, Switch, PlayStation, Xbox — OpenCritic 82)*\n"
            "- Classic retro survival horror with cryptic puzzle boxes, limited inventory management, and cosmic dread.\n\n"
            "4. **Resident Evil 4 Remake** *(PC, PS5, Xbox — OpenCritic 92)*\n"
            "- Unmatched tension, resource conservation, audio cues, and terrifying encounters."
        )

    # 3. Call of Duty & Activision Shooters
    if any(w in msg_lower for w in ["cod", "call of duty", "activision", "fps", "shooter", "shooting", "black ops", "modern warfare", "titanfall", "doom"]):
        return (
            "### 🎯 **Top Fast-Paced & Military Shooters Like Call of Duty (by Activision)**\n\n"
            "1. **Call of Duty: Black Ops 6** *(PC, PS5, Xbox Series X|S — OpenCritic 84)*\n"
            "- Omnimovement allows sprinting, sliding, and diving in 360 degrees with signature arcade gunplay.\n\n"
            "2. **Titanfall 2** *(PC, PS4, Xbox — Metacritic 89)*\n"
            "- Created by the original *Modern Warfare* developers, featuring wall-running mobility, crisp weapon recoil, and giant mech combat.\n\n"
            "3. **The Finals / Apex Legends** *(Free to Play)*\n"
            "- High-mobility squad shooting with environmental destruction and tactical abilities."
        )

    # 4. Cinematic Action (Uncharted / Tomb Raider)
    if any(w in msg_lower for w in ["uncharted", "unchearted", "tomb raider", "naughty dog", "last of us", "indiana jones"]):
        return (
            "### 🌿 **Top Cinematic Action-Adventure Games Like Uncharted**\n\n"
            "1. **Tomb Raider Reboot Trilogy** *(Metacritic 86–89)* — Ancient tomb puzzles, climbing traversal, and shootouts.\n"
            "2. **The Last of Us Part I & Part II** *(Metacritic 93 / OpenCritic 90)* — Motion capture benchmark and visceral combat.\n"
            "3. **Indiana Jones and the Great Circle / Star Wars Jedi: Survivor** *(OpenCritic 85)* — Globe-trotting exploration and whip/lightsaber traversal."
        )

    # 5. Open-World Discovery (Zelda, Elden Ring, Ghost of Tsushima)
    if any(w in msg_lower for w in ["zelda", "zelder", "breath of the wild", "tears of the kingdom", "ghost of tsushima", "discovery", "open world"]):
        return (
            "### 🗡️ **Top Open-World Discovery Games Like The Legend of Zelda**\n\n"
            "1. **Elden Ring** *(OpenCritic 95)* — Emergent discovery across a colossal fantasy landscape.\n"
            "2. **Tunic** *(OpenCritic 85)* — Cryptic in-game manual pages and environmental puzzle boxes.\n"
            "3. **Ghost of Tsushima** *(OpenCritic 87)* — Guiding wind navigation and fluid katana combat."
        )

    # 6. Crime Sandboxes (GTA, Red Dead, Cyberpunk)
    if any(w in msg_lower for w in ["gta", "grand theft auto", "red dead", "rockstar", "cyberpunk"]):
        return (
            "### 🤠 **Top Living World Sandboxes Like GTA & Red Dead Redemption**\n\n"
            "1. **Cyberpunk 2077: Phantom Liberty** *(OpenCritic 89)* — Night City urban sandbox with cyberware builds.\n"
            "2. **Sleeping Dogs: Definitive Edition** *(PC, PS4, Xbox)* — Hong Kong martial arts undercover cop drama.\n"
            "3. **Mafia: Definitive Edition** *(PC, PS4, Xbox)* — 1930s mobster drama with authentic period cars."
        )

    # 7. Soulslikes
    if any(w in msg_lower for w in ["soulslike", "fromsoftware", "dark souls", "bloodborne", "sekiro", "lies of p", "wukong"]):
        return (
            "### 💀 **Top Must-Play Soulslikes & Precision Action Games**\n\n"
            "1. **Elden Ring: Shadow of the Erdtree** *(OpenCritic 95)* — The pinnacle of dark fantasy exploration.\n"
            "2. **Lies of P** *(OpenCritic 84)* — Tight deflections inspired by Bloodborne and Sekiro in a Belle Époque world.\n"
            "3. **Black Myth: Wukong** *(OpenCritic 82)* — Fast-paced staff martial arts combat and mythological spectacles."
        )

    # 8. JRPGs (Persona, FF7, Metaphor)
    if any(w in msg_lower for w in ["persona", "metaphor", "final fantasy", "ff7", "jrpg", "turn based", "turn-based"]):
        return (
            "### 🎭 **Top Acclaimed JRPGs & Turn-Based Masterpieces**\n\n"
            "1. **Metaphor: ReFantazio** *(OpenCritic 94)* — Tactical turn-based combat and royal kingdom tournament narrative.\n"
            "2. **Persona 5 Royal** *(OpenCritic 94)* — High school simulator meets supernatural dungeon crawling.\n"
            "3. **Final Fantasy VII Rebirth** *(OpenCritic 92)* — Expansive party synergy combat and cinematic storytelling."
        )

    # 9. Looter Shooters (Destiny, Helldivers, Remnant)
    if any(w in msg_lower for w in ["destiny", "warframe", "remnant", "helldivers", "borderlands"]):
        return (
            "### 🛡️ **Top Co-Op Looter Shooters Like Destiny & Helldivers**\n\n"
            "1. **Helldivers 2** *(OpenCritic 83)* — Co-op galactic war with stratagems and chaotic friendly fire.\n"
            "2. **Remnant 2** *(OpenCritic 85)* — Tactical third-person shooting with procedural worlds and secret archetypes.\n"
            "3. **Warframe** *(Free to Play)* — High-speed space ninja parkour and deep crafting."
        )

    # 10. Platformers (Astro Bot, Mario)
    if any(w in msg_lower for w in ["platformer", "astro bot", "mario", "sonic", "hollow knight"]):
        return (
            "### 🍄 **Top 3D & 2D Platforming Masterpieces Like Mario & Astro Bot**\n\n"
            "1. **Astro Bot** *(PS5 Exclusive — OpenCritic 94)* — Joyous level gimmicks and DualSense haptics.\n"
            "2. **Super Mario Bros. Wonder / Odyssey** *(OpenCritic 91 / 97)* — Benchmark creative movement mechanics.\n"
            "3. **Hollow Knight** *(Metacritic 90)* — Atmospheric 2D metroidvania with tight nail combat."
        )

    # 11. Sandbox Creation (Roblox, Minecraft)
    if any(w in msg_lower for w in ["roblox", "roblx", "minecraft", "sandbox", "terraria"]):
        return (
            "### 🧱 **Top Games & Sandbox Creation Hubs Like Roblox & Minecraft**\n\n"
            "1. **Minecraft** *(Metacritic 93)* — The ultimate voxel sandbox for survival and redstone engineering.\n"
            "2. **LEGO Fortnite & Fortnite Creative / UEFN** — Massive creator ecosystem with millions of community worlds.\n"
            "3. **Terraria** *(Metacritic 88)* — 2D action-adventure sandbox with deep boss progression."
        )

    # 12. Numerical Scores (60+, 70+, 80+, 85+, 90+)
    score_match = re.search(r'(?:score(?: of)?|rated|rating of|above|at least)\s*(\d{2})|(\d{2})\s*\+', msg_lower)
    if score_match:
        min_score = int(score_match.group(1) or score_match.group(2))
        if min_score <= 79:
            return (
                f"### ⭐ **Recent & Notable Games Rated {min_score}+ (OpenCritic / Metacritic)**\n\n"
                "1. **Star Wars Outlaws** *(OpenCritic 76)* — Scoundrel syndicate adventure.\n"
                "2. **The Crew Motorfest** *(OpenCritic 76)* — Hawaiian festival racing.\n"
                "3. **Need for Speed Unbound** *(OpenCritic 77)* — Stylized anime street graffiti racing.\n"
                "4. **Warhammer 40K: Space Marine 2** *(OpenCritic 82)* — Visceral third-person swarm brawler."
            )
        elif min_score <= 89:
            return (
                f"### ⭐ **Top Critically Acclaimed Games Rated {min_score}+**\n\n"
                "1. **Like a Dragon: Infinite Wealth** *(OpenCritic 89)* — Massive Hawaiian RPG.\n"
                "2. **Alan Wake 2** *(OpenCritic 89)* — Psychological survival horror benchmark.\n"
                "3. **Dragon's Dogma 2** *(OpenCritic 86)* — Emergent fantasy climbing combat.\n"
                "4. **Remnant 2** *(OpenCritic 85)* — Tactical procedural shooter."
            )
        else:
            return (
                f"### 🏆 **Elite Masterpieces Rated {min_score}+ (Mighty Tier)**\n\n"
                "1. **Elden Ring: Shadow of the Erdtree** *(OpenCritic 95)*\n"
                "2. **Astro Bot** *(PS5 Exclusive — OpenCritic 94)*\n"
                "3. **Metaphor: ReFantazio** *(OpenCritic 94)*\n"
                "4. **Final Fantasy VII Rebirth** *(PS5 Exclusive — OpenCritic 92)*"
            )

    # Default Contextual Recommendations
    return (
        f"### 🎮 **GamePulse Concierge**\n\n"
        f"I analyzed recommendations matching **{msg_clean}**:\n\n"
        "Here are three top-rated, player-favorite games across major genres right now:\n"
        "1. **Elden Ring: Shadow of the Erdtree** *(OpenCritic 95)* — Grand open-world dark fantasy action RPG.\n"
        "2. **Astro Bot** *(PlayStation 5 — OpenCritic 94)* — The gold standard of modern creative 3D platformers.\n"
        "3. **Balatro** *(PC, Consoles, Mobile — OpenCritic 90)* — Hypnotic roguelike poker deckbuilder.\n\n"
        "Tell me a specific genre (e.g., *Action RPG, Horror, Shooter, Open World*) or a game you enjoyed to narrow it down!"
    )


# ==========================================
# BACKGROUND SCHEDULER (ROUND-ROBIN INGESTION)
# ==========================================
pipeline_lock = threading.Lock()

def run_news_aggregation_pipeline():
    if not pipeline_lock.acquire(blocking=False):
        return

    try:
        feed_results = []
        for feed in FEEDS:
            items = fetch_feed_items(feed)
            if items:
                feed_results.append(items)

        selected_items = []
        seen_links = set()
        max_per_feed = 5

        for step in range(max_per_feed):
            for f_items in feed_results:
                if step < len(f_items):
                    it = f_items[step]
                    if it["link"] not in seen_links:
                        seen_links.add(it["link"])
                        selected_items.append(it)

        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        now_iso = datetime.now(timezone.utc).isoformat()

        conn = get_db()
        for item in selected_items:
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
    # ALWAYS execute a live aggregation run on startup so all tabs populate immediately
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
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0">
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
        * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
        body { background-color: var(--bg-primary); color: var(--text-main); font-family: var(--font); line-height: 1.6; -webkit-font-smoothing: antialiased; }

        .top-utility-bar {
            background: #0b0e17; border-bottom: 1px solid var(--border);
            padding: 6px 16px; font-size: 0.76rem; color: var(--text-muted);
            display: flex; justify-content: space-between; align-items: center;
        }
        .trending-wrap { display: flex; align-items: center; gap: 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .trending-tag { color: var(--brand-red); font-weight: 800; text-transform: uppercase; font-size: 0.72rem; flex-shrink: 0; }

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
            padding: 10px 16px; -webkit-overflow-scrolling: touch;
        }
        .sub-nav-inner {
            max-width: 1140px; margin: 0 auto;
            display: flex; gap: 8px; overflow-x: auto; scrollbar-width: none;
        }
        .sub-nav-inner::-webkit-scrollbar { display: none; }
        .category-pill {
            background: var(--bg-card); border: 1px solid var(--border); color: #94a3b8;
            padding: 6px 16px; border-radius: 20px; font-size: 0.8rem; font-weight: 700;
            text-decoration: none; white-space: nowrap; transition: all 0.15s ease; flex-shrink: 0;
            min-height: 36px; display: inline-flex; align-items: center;
        }
        .category-pill:hover, .category-pill.active { background: #222d42; color: #fff; border-color: var(--brand-blue); }

        .page-container { max-width: 1140px; margin: 32px auto; padding: 0 16px; }
        .editorial-grid { display: flex; flex-direction: column; gap: 28px; }

        .editorial-card {
            background: var(--bg-card); border: 1px solid var(--border);
            border-radius: 12px; overflow: hidden; transition: border-color 0.2s ease, transform 0.2s ease;
        }
        .editorial-card:hover { border-color: #334155; transform: translateY(-2px); }

        .banner-wrap { display: block; width: 100%; overflow: hidden; background: #000; text-decoration: none; }
        .banner-img {
            width: 100%; aspect-ratio: 16 / 9; object-fit: cover; display: block;
            max-height: 380px; transition: transform 0.3s ease;
        }
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
            flex-wrap: wrap; gap: 8px;
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

        /* PULSAR AI POPUP */
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
            display: flex; justify-content: space-between; align-items: center; flex-shrink: 0;
        }
        .pulsar-profile { display: flex; align-items: center; gap: 10px; }
        .pulsar-avatar { width: 34px; height: 34px; border-radius: 50%; background: linear-gradient(135deg, #ef4444, #8b5cf6); display: flex; align-items: center; justify-content: center; font-size: 1.1rem; }
        .pulsar-title-wrap h3 { font-size: 0.95rem; font-weight: 800; color: #fff; margin-bottom: 2px; }
        .pulsar-subtitle { font-size: 0.74rem; color: #94a3b8; }

        .pulsar-controls { display: flex; align-items: center; gap: 6px; }
        .pulsar-ctrl-btn { background: transparent; border: none; color: #94a3b8; font-size: 1.2rem; cursor: pointer; padding: 6px; line-height: 1; }
        .pulsar-ctrl-btn:hover { color: #fff; }

        .pulsar-messages-area {
            flex: 1; padding: 16px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px;
            font-size: 0.88rem; background: #080c16; -webkit-overflow-scrolling: touch;
        }
        .pulsar-messages-area::-webkit-scrollbar { width: 4px; }
        .pulsar-messages-area::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 4px; }

        .msg-bubble { max-width: 88%; padding: 10px 14px; border-radius: 14px; line-height: 1.45; word-wrap: break-word; }
        .msg-pulsar { background: #151e31; color: #e2e8f0; border-bottom-left-radius: 2px; border: 1px solid #202d4a; align-self: flex-start; }
        .msg-user { background: #ef4444; color: #fff; border-bottom-right-radius: 2px; align-self: flex-end; }
        .msg-pulsar a { color: #38bdf8; text-decoration: underline; }

        .suggestion-chips-wrap { display: flex; flex-direction: column; gap: 6px; margin-top: 8px; }
        .sugg-chip {
            background: #111827; border: 1px solid #24314c; color: #93c5fd;
            padding: 10px 14px; border-radius: 8px; font-size: 0.82rem; text-align: left;
            cursor: pointer; transition: all 0.15s ease; font-family: inherit; font-weight: 600;
            min-height: 40px;
        }
        .sugg-chip:hover { background: #1a253c; color: #fff; border-color: #38bdf8; }

        .gemini-pill-container {
            background: #111827; border-top: 1px solid #1f2c47; padding: 12px 14px;
            padding-bottom: max(12px, env(safe-area-inset-bottom)); flex-shrink: 0;
        }
        .gemini-pill-box {
            display: flex; align-items: center; gap: 8px;
            background: #162035; border: 1px solid #2c3e63; border-radius: 28px;
            padding: 6px 10px 6px 14px; transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }
        .gemini-pill-box:focus-within { border-color: #ef4444; box-shadow: 0 0 12px rgba(239, 68, 68, 0.25); }

        .gemini-plus-btn {
            background: transparent; border: none; color: #94a3b8; font-size: 1.3rem;
            cursor: pointer; display: flex; align-items: center; justify-content: center;
            width: 28px; height: 28px; border-radius: 50%; transition: background 0.15s ease, color 0.15s ease;
            flex-shrink: 0;
        }
        .gemini-plus-btn:hover { background: #22304d; color: #fff; }

        .gemini-pill-input {
            flex: 1; background: transparent; border: none; color: #fff;
            font-size: 16px; outline: none; font-family: inherit;
        }
        .gemini-pill-input::placeholder { color: #64748b; font-size: 0.88rem; }

        .gemini-send-circle {
            background: #ef4444; color: #fff; border: none; width: 32px; height: 32px;
            border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center;
            font-size: 0.9rem; font-weight: bold; transition: background 0.15s ease, transform 0.15s ease;
            flex-shrink: 0;
        }
        .gemini-send-circle:hover { background: #dc2626; transform: scale(1.05); }

        .quick-actions-drawer {
            display: none; padding: 8px 12px 12px; background: #111827; border-top: 1px dashed #1f2c47;
            gap: 6px; flex-direction: column; flex-shrink: 0;
        }
        .quick-action-link {
            background: #162035; border: 1px solid #283755; color: #cbd5e1;
            padding: 8px 12px; border-radius: 6px; font-size: 0.8rem; text-align: left;
            cursor: pointer; transition: all 0.15s ease; min-height: 38px;
        }
        .quick-action-link:hover { color: #38bdf8; border-color: #38bdf8; background: #1c2944; }

        /* RESPONSIVE MEDIA QUERIES */
        @media (max-width: 1024px) {
            .page-container { margin: 24px auto; padding: 0 16px; }
            .footer-columns { grid-template-columns: 1fr 1fr; gap: 32px; }
        }

        @media (max-width: 768px) {
            .main-nav { display: none; }
            .brand-logo { font-size: 1.45rem; }
            .top-utility-bar { font-size: 0.72rem; padding: 5px 12px; }
            .card-inner { padding: 18px 16px; }
            .article-headline { font-size: 1.22rem; line-height: 1.35; margin-bottom: 10px; }
            .article-body { font-size: 0.92rem; line-height: 1.6; margin-bottom: 14px; }
            .highlights-card { padding: 12px 14px; margin-bottom: 16px; }
            .highlights-card ul { font-size: 0.84rem; padding-left: 16px; }
            .footer-columns { grid-template-columns: 1fr; gap: 24px; }
            footer { margin-top: 50px; padding: 36px 16px 20px; }
        }

        @media (max-width: 640px) {
            .pulsar-launcher-btn { bottom: 16px; right: 16px; padding: 10px 16px; font-size: 0.82rem; }
            .pulsar-popup-box {
                width: 100vw; height: 100dvh; max-width: 100vw; max-height: 100dvh;
                bottom: 0; right: 0; border-radius: 0; border: none;
            }
            .pulsar-header { padding: 16px 14px; padding-top: max(16px, env(safe-area-inset-top)); }
            .msg-bubble { max-width: 92%; }
        }
    </style>
</head>
<body>
    <div class="top-utility-bar">
        <div class="trending-wrap">
            <span class="trending-tag">Trending</span>
            <span>PlayStation 5 Pro • Switch 2 • GTA VI • Unreal Engine 5</span>
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
            <a href="/?tag=REVIEW" class="category-pill {{ACT_REV}}">Reviews & Scores</a>
            <a href="/?tag=INDUSTRY" class="category-pill {{ACT_IND}}">Industry & Studios</a>
            <a href="/?tag=TRAILER" class="category-pill {{ACT_TRAILER}}">Trailers & Reveals</a>
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
                <button class="pulsar-ctrl-btn" onclick="togglePulsar()" title="Close">✕</button>
            </div>
        </div>
        <div class="pulsar-messages-area" id="pulsarMessages">
            <div class="msg-bubble msg-pulsar">
                <p><strong>Hi! What do you want to do today?</strong></p>
                <div class="suggestion-chips-wrap">
                    <button class="sugg-chip" onclick="sendPulsarPrompt('Articles posted today')">📰 Articles posted today</button>
                    <button class="sugg-chip" onclick="sendPulsarPrompt('Give me games like Diablo')">⚔️ Action RPGs & Diablo</button>
                    <button class="sugg-chip" onclick="sendPulsarPrompt('Find me a game to play that is horror like Silent Hill')">🔦 Silent Hill Style Horror</button>
                </div>
            </div>
        </div>

        <div class="quick-actions-drawer" id="quickActionsDrawer">
            <button class="quick-action-link" onclick="sendPulsarPrompt('Give me games like Diablo')">⚔️ Diablo & Isometric RPGs</button>
            <button class="quick-action-link" onclick="sendPulsarPrompt('Find me a game to play that is horror like Silent Hill')">🔦 Horror Games (Silent Hill / RE)</button>
            <button class="quick-action-link" onclick="sendPulsarPrompt('Show me games like COD made by Activision')">🎯 Call of Duty & Activision</button>
        </div>

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
                        <button class="sugg-chip" onclick="sendPulsarPrompt('Give me games like Diablo')">⚔️ Action RPGs & Diablo</button>
                        <button class="sugg-chip" onclick="sendPulsarPrompt('Find me a game to play that is horror like Silent Hill')">🔦 Silent Hill Style Horror</button>
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
            
            if tag_filter == "REVIEW":
                cursor = conn.execute("""
                    SELECT * FROM articles 
                    WHERE tag='REVIEW' 
                       OR category LIKE '%Review%' 
                       OR title LIKE '%Review%' 
                       OR title LIKE '%Verdict%' 
                       OR title LIKE '%Score%' 
                       OR title LIKE '%Impressions%'
                       OR source_name LIKE '%Review%'
                    ORDER BY id DESC LIMIT 50
                """)
            elif tag_filter == "INDUSTRY":
                cursor = conn.execute("""
                    SELECT * FROM articles 
                    WHERE tag='INDUSTRY' 
                       OR category LIKE '%Industry%' 
                       OR source_name LIKE '%Industry%' 
                       OR title LIKE '%Sales%' 
                       OR title LIKE '%Layoff%' 
                       OR title LIKE '%Studio%' 
                       OR title LIKE '%Acquisition%'
                       OR title LIKE '%Sony%'
                       OR title LIKE '%Xbox%'
                       OR title LIKE '%Nintendo%'
                       OR title LIKE '%Financial%'
                    ORDER BY id DESC LIMIT 50
                """)
            elif tag_filter == "TRAILER":
                cursor = conn.execute("""
                    SELECT * FROM articles 
                    WHERE tag='TRAILER' 
                       OR category LIKE '%Trailer%' 
                       OR category LIKE '%Announcement%' 
                       OR title LIKE '%Trailer%' 
                       OR title LIKE '%Gameplay%' 
                       OR title LIKE '%Reveal%' 
                       OR title LIKE '%Announce%'
                    ORDER BY id DESC LIMIT 50
                """)
            elif tag_filter == "UPDATE":
                cursor = conn.execute("""
                    SELECT * FROM articles 
                    WHERE tag='UPDATE' 
                       OR category LIKE '%Update%' 
                       OR category LIKE '%Patch%'
                       OR title LIKE '%Patch%' 
                       OR title LIKE '%Update%' 
                       OR title LIKE '%DLC%' 
                       OR title LIKE '%Hotfix%' 
                       OR title LIKE '%Season%' 
                       OR title LIKE '%Roadmap%' 
                       OR title LIKE '%Expansion%' 
                       OR title LIKE '%Overhaul%'
                       OR title LIKE '%Mod%'
                       OR ai_title LIKE '%Patch%' 
                       OR ai_title LIKE '%Update%' 
                       OR ai_title LIKE '%DLC%' 
                       OR ai_title LIKE '%Expansion%'
                    ORDER BY id DESC LIMIT 50
                """)
            elif tag_filter == "RUMOR":
                cursor = conn.execute("""
                    SELECT * FROM articles 
                    WHERE tag='RUMOR' 
                       OR category LIKE '%Rumor%' 
                       OR source_name LIKE '%GamingLeaks%' 
                       OR title LIKE '%Rumor%' 
                       OR title LIKE '%Leak%' 
                       OR title LIKE '%Report:%' 
                       OR title LIKE '%Insider%'
                    ORDER BY id DESC LIMIT 50
                """)
            elif tag_filter == "COMMUNITY":
                cursor = conn.execute("""
                    SELECT * FROM articles 
                    WHERE tag='COMMUNITY' 
                       OR category LIKE '%Community%' 
                       OR title LIKE '%Mod%' 
                       OR title LIKE '%Indie%'
                    ORDER BY id DESC LIMIT 50
                """)
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