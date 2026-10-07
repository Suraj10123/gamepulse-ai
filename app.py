#!/usr/bin/env python3
"""
GamePulse AI — Live Video Game News Digest, Review Aggregator & Pulsar AI Concierge
Zero external Python dependencies (Standard Library Only: http.server, socketserver, urllib, sqlite3, threading, socket, json, re, html, os, sys, xml, datetime, difflib)
"""

import os
import sys
import json
import time
import socket
import sqlite3
import urllib.request
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET
import threading
import re
import html
import difflib
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

# Strict socket timeout to prevent any external HTTP calls or SSL handshakes from hanging
socket.setdefaulttimeout(5.0)

PORT = int(os.environ.get("PORT", 10000))
DB_PATH = os.environ.get("DB_PATH", "gamepulse.db")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
CURRENT_YEAR = datetime.now(timezone.utc).year


# ---------------------------------------------------------------------------
# Seed Articles & Feeds
# ---------------------------------------------------------------------------

SEED_ARTICLES = [
    # REVIEWS (category: REVIEW)
    {
        "title": "Astro Bot Review: A Pure, Unadulterated Triumph of 3D Platforming",
        "link": "https://www.ign.com/articles/astro-bot-review",
        "published": "2026-10-05T09:30:00Z",
        "summary": "Team ASOBI has crafted a modern PlayStation masterpiece. Every stage is brimming with DualSense haptic inventiveness, celebrating decades of iconic gaming history with razor-sharp platforming controls.",
        "source": "IGN",
        "category": "REVIEW",
        "score": "94 Metacritic",
        "image_url": "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=600&q=80"
    },
    {
        "title": "Metaphor: ReFantazio Review — Atlus's High-Fantasy Masterpiece",
        "link": "https://www.gamespot.com/reviews/metaphor-refantazio-review/",
        "published": "2026-10-05T08:15:00Z",
        "summary": "From the creative minds behind Persona 3, 4, and 5 comes an epic royal tournament RPG combining real-time overworld slashing, intricate Archetype build crafting, and unforgettable political storytelling.",
        "source": "GameSpot",
        "category": "REVIEW",
        "score": "93 Metacritic",
        "image_url": "https://images.unsplash.com/photo-1538481199705-c710c4e965fc?w=600&q=80"
    },
    {
        "title": "Silent Hill 2 Remake Review: Fog-Drenched Terror Reborn",
        "link": "https://www.eurogamer.net/silent-hill-2-remake-review",
        "published": "2026-10-04T16:45:00Z",
        "summary": "Bloober Team pulls off the impossible. Reconstructed in Unreal Engine 5, this psychological horror descent captures James Sunderland's grief with haunting 3D audio, terrifying encounters, and respectful fidelity.",
        "source": "Eurogamer",
        "category": "REVIEW",
        "score": "86 Metacritic",
        "image_url": "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?w=600&q=80"
    },
    {
        "title": "Fire Emblem: Fortune's Weave Review — Tactical Brilliance on Switch 2",
        "link": "https://www.polygon.com/reviews/fire-emblem-fortunes-weave-review",
        "published": "2026-10-04T14:20:00Z",
        "summary": "Intelligent Systems delivers a technical tour de force for Nintendo's new hardware. Featuring 60FPS fluid battles, weapon triangle strategy, and the emotional resonance of Three Houses.",
        "source": "Polygon",
        "category": "REVIEW",
        "score": "88 Metacritic",
        "image_url": "https://images.unsplash.com/photo-1563089145-599997674d42?w=600&q=80"
    },
    {
        "title": "Warhammer 40,000: Space Marine 2 Review — Glorious Power Armor Carnage",
        "link": "https://www.pcgamer.com/space-marine-2-review/",
        "published": "2026-10-03T19:10:00Z",
        "summary": "Saber Interactive's visceral horde-shooter channels the heavy, kinetic intensity of Gears of War. Holding back thousands of Tyranids with roaring chainswords and bolters is gaming bliss.",
        "source": "PC Gamer",
        "category": "REVIEW",
        "score": "82 Metacritic",
        "image_url": "https://images.unsplash.com/photo-1542751371-adc38448a05e?w=600&q=80"
    },
    {
        "title": "Black Myth: Wukong Review — A Mythological Boss-Rush Spectacle",
        "link": "https://www.rockpapershotgun.com/black-myth-wukong-review",
        "published": "2026-10-03T12:00:00Z",
        "summary": "Game Science's action RPG adaptation of Journey to the West shines with stunning visual fidelity, lightning-fast staff martial arts, and dozens of creative mythological boss battles.",
        "source": "Rock Paper Shotgun",
        "category": "REVIEW",
        "score": "81 Metacritic",
        "image_url": "https://images.unsplash.com/photo-1511512578047-dfb367046420?w=600&q=80"
    },
    {
        "title": "Balatro Review: The Roguelike Poker Addiction of the Generation",
        "link": "https://www.kotaku.com/balatro-review-poker-roguelike",
        "published": "2026-10-02T15:00:00Z",
        "summary": "LocalThunk's hypnotic deckbuilder turns traditional poker hands into exponential scoring cascades with game-breaking Jokers, celestial tarot cards, and hypnotic retro synth vibes.",
        "source": "Kotaku",
        "category": "REVIEW",
        "score": "90 Metacritic",
        "image_url": "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=600&q=80"
    },
    {
        "title": "Elden Ring: Shadow of the Erdtree Review — FromSoftware Outdoes Itself",
        "link": "https://www.destructoid.com/shadow-of-the-erdtree-review",
        "published": "2026-10-01T11:00:00Z",
        "summary": "A massive, labyrinthine Realm of Shadow that dwarfs entire standalone games. With 8 distinct new weapon archetypes and punishing, awe-inspiring bosses, it is an essential triumph.",
        "source": "Destructoid",
        "category": "REVIEW",
        "score": "95 Metacritic",
        "image_url": "https://images.unsplash.com/photo-1579373903781-fd5c0c30c4cd?w=600&q=80"
    },

    # PATCHES & EXPANSIONS (category: UPDATE)
    {
        "title": "Diablo IV: Vessel of Hatred Major Balance Patch 2.1 Live Notes",
        "link": "https://news.blizzard.com/en-us/diablo4/vessel-of-hatred-patch-2-1",
        "published": "2026-10-05T11:00:00Z",
        "summary": "Blizzard balances the new Spiritborn martial arts class, increases Torment dungeon glyph experience rates, rebalances Runeword crafting costs, and optimizes Nahantu zone loading times.",
        "source": "Blizzard Entertainment",
        "category": "UPDATE",
        "score": "Patch Notes",
        "image_url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=600&q=80"
    },
    {
        "title": "Helldivers 2 Patch 1.002.300: Heavy Armor Buffs & Galactic War Rebalance",
        "link": "https://store.steampowered.com/news/app/553850/view/patch1002300",
        "published": "2026-10-05T07:45:00Z",
        "summary": "Arrowhead Studios delivers sweeping weapon buffs to energy weapons, recalibrates Automaton projectile accuracy, and introduces the new Orbital Napalm Barrage stratagem across Super Earth frontiers.",
        "source": "PlayStation Studios",
        "category": "UPDATE",
        "score": "Update 1.02",
        "image_url": "https://images.unsplash.com/photo-1534423861386-85a16f5d13fd?w=600&q=80"
    },
    {
        "title": "Path of Exile 2: Beta Update 0.8.2 Adds Druid Form Synergies & Console Co-Op Tweaks",
        "link": "https://www.pathofexile.com/forum/view-thread/poe2-update-082",
        "published": "2026-10-04T18:00:00Z",
        "summary": "Grinding Gear Games optimizes twin-stick controller navigation, refines dodge-roll invulnerability frames, and rolls out substantial skill-gem socket overhauls for Act 4 testing.",
        "source": "Grinding Gear Games",
        "category": "UPDATE",
        "score": "Beta Patch",
        "image_url": "https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?w=600&q=80"
    },
    {
        "title": "Cyberpunk 2077 Update 2.2 Rolls Out with Enhanced FSR 3.1 & PS5 Pro Support",
        "link": "https://www.cyberpunk.net/en/news/50201/patch-2-2-notes",
        "published": "2026-10-03T15:20:00Z",
        "summary": "CD Projekt Red brings enhanced ray-tracing optimizations, fixes cyberware perk stacking quirks, and unlocks PSSR upscaling for PlayStation 5 Pro hardware in Night City.",
        "source": "CD Projekt Red",
        "category": "UPDATE",
        "score": "Hotfix 2.2",
        "image_url": "https://images.unsplash.com/photo-1542751110-97427bbecf20?w=600&q=80"
    },
    {
        "title": "Baldur's Gate 3 Patch 7: Official Modding Toolkit & Evil Endings Deployed",
        "link": "https://baldursgate3.game/news/patch-7-released",
        "published": "2026-10-02T13:30:00Z",
        "summary": "Larian Studios introduces the integrated cross-platform mod manager, cinematic evil epilogues for villainous playthroughs, and refined Honour Mode legendary actions.",
        "source": "Larian Studios",
        "category": "UPDATE",
        "score": "Patch 7",
        "image_url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=600&q=80"
    },

    # TRAILERS & REVEALS (category: TRAILER)
    {
        "title": "Grand Theft Auto VI Trailer 2 Breaks Records With Next-Gen Physics Showcase",
        "link": "https://www.youtube.com/watch?v=gta6-trailer-2-official",
        "published": "2026-10-05T10:00:00Z",
        "summary": "Rockstar Games pulls back the curtain on Vice City's living ecosystem, showcasing dynamic weather storms, vehicular damage simulation, and seamless character swaps between Lucia and Jason.",
        "source": "Rockstar Games",
        "category": "TRAILER",
        "score": "4K Trailer",
        "image_url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=600&q=80"
    },
    {
        "title": "Ghost of Yōtei 15-Minute Gameplay Deep Dive: Dual Stances & Ezo Wilderness",
        "link": "https://www.youtube.com/watch?v=ghost-of-yotei-deep-dive",
        "published": "2026-10-04T17:30:00Z",
        "summary": "Sucker Punch reveals Atsu's journey around Mount Yōtei in 1603. Watch devastating dual-katana combos, grappling hook verticality, and firearms integrated into feudal Japanese combat.",
        "source": "PlayStation",
        "category": "TRAILER",
        "score": "Gameplay Reveal",
        "image_url": "https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?w=600&q=80"
    },
    {
        "title": "Doom: The Dark Ages Combat Showcase — Shield Saw & Flail Mayhem",
        "link": "https://www.youtube.com/watch?v=doom-dark-ages-shield-saw",
        "published": "2026-10-03T18:15:00Z",
        "summary": "id Software unveils the visceral medieval prequel to Doom Eternal. Featuring the serrated Shield Saw that parries projectile attacks and giant Atlan mech brawls.",
        "source": "Bethesda Softworks",
        "category": "TRAILER",
        "score": "Combat Reveal",
        "image_url": "https://images.unsplash.com/photo-1542751371-adc38448a05e?w=600&q=80"
    },
    {
        "title": "Monster Hunter Wilds: Scarlet Forest Ecosystem & Apex Monster Hunt",
        "link": "https://www.youtube.com/watch?v=monster-hunter-wilds-hunt",
        "published": "2026-10-02T14:40:00Z",
        "summary": "Capcom shows off seamless riding mount transitions, active weather shifts from torrential downpour to lush sunshine, and dual-weapon hunting tactics.",
        "source": "Capcom",
        "category": "TRAILER",
        "score": "Hunt Gameplay",
        "image_url": "https://images.unsplash.com/photo-1538481199705-c710c4e965fc?w=600&q=80"
    },

    # INDUSTRY & STUDIOS (category: INDUSTRY)
    {
        "title": "PlayStation 5 Pro Global Launch: Technical Analysis of PSSR AI Upscaling",
        "link": "https://www.gamesindustry.biz/articles/ps5-pro-technical-analysis-pssr",
        "published": "2026-10-05T08:00:00Z",
        "summary": "Digital Foundry and industry engineers test Sony's custom PlayStation Spectral Super Resolution machine learning chip, confirming native 4K clarity at locked 60FPS across 50+ enhanced titles.",
        "source": "GamesIndustry.biz",
        "category": "INDUSTRY",
        "score": "Hardware Report",
        "image_url": "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=600&q=80"
    },
    {
        "title": "Nintendo Switch 2 Developer Kits Reportedly Feature DLSS 3.5 & 12GB RAM",
        "link": "https://www.theverge.com/games/nintendo-switch-2-hardware-specs-leak",
        "published": "2026-10-04T12:15:00Z",
        "summary": "Studio sources detail Nintendo's next-generation hybrid console architecture, confirming backward compatibility support for original Switch game cartridges and enhanced HDR dock output.",
        "source": "The Verge",
        "category": "INDUSTRY",
        "score": "Tech Insight",
        "image_url": "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=600&q=80"
    },
    {
        "title": "Epic Games Reveals Unreal Engine 5.5: MegaLights & Nanite Skeletal Meshes",
        "link": "https://www.unrealengine.com/blog/unreal-engine-5-5-released",
        "published": "2026-10-03T16:00:00Z",
        "summary": "The new iteration brings hundreds of movable cinematic lights rendering in real time with virtually zero performance penalty, empowering next-gen console and PC developers.",
        "source": "Epic Games",
        "category": "INDUSTRY",
        "score": "Engine Roadmap",
        "image_url": "https://images.unsplash.com/photo-1511512578047-dfb367046420?w=600&q=80"
    },

    # RUMORS & LEAKS (category: RUMOR)
    {
        "title": "Insider Report: FromSoftware Developing New Dark Fantasy IP With Sony",
        "link": "https://insider-gaming.com/fromsoftware-new-sony-exclusive-ip/",
        "published": "2026-10-05T06:30:00Z",
        "summary": "Credible industry insiders report that Hidetaka Miyazaki is directing a brand new dark gothic action RPG engineered exclusively for PlayStation 5 hardware.",
        "source": "Insider Gaming",
        "category": "RUMOR",
        "score": "Insider Leak",
        "image_url": "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?w=600&q=80"
    },
    {
        "title": "Capcom Datamine Points to Resident Evil 9 Starring Leon Kennedy in Open Island Setting",
        "link": "https://www.videogameschronicle.com/news/resident-evil-9-leak-leon-setting/",
        "published": "2026-10-04T11:45:00Z",
        "summary": "Leaked development documents indicate Resident Evil 9 features an ominous Southeast Asian archipelago setting with third-person and first-person perspective toggles.",
        "source": "VGC",
        "category": "RUMOR",
        "score": "Datamine",
        "image_url": "https://images.unsplash.com/photo-1579373903781-fd5c0c30c4cd?w=600&q=80"
    },
    {
        "title": "Xbox Handheld Console Codenamed 'Keenan' Targeted for Late 2026 Reveal",
        "link": "https://www.windowscentral.com/gaming/xbox/xbox-portable-console-keenan",
        "published": "2026-10-03T13:20:00Z",
        "summary": "Microsoft is actively engineering a native Windows handheld device with seamless Xbox Game Pass offline play and dedicated controller grip ergonomics.",
        "source": "Windows Central",
        "category": "RUMOR",
        "score": "Supply Chain Leak",
        "image_url": "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=600&q=80"
    },

    # INDIE & MODS (category: INDIE)
    {
        "title": "Hades II Early Access Major Content Pack: Olympus Heights & New Boons",
        "link": "https://www.supergiantgames.com/blog/hades-ii-olympus-update",
        "published": "2026-10-05T09:00:00Z",
        "summary": "Supergiant Games expands Melinoë's journey with a complete mountain realm, Apollo and Hera duo boons, and weapon aspect enchantments.",
        "source": "Supergiant Games",
        "category": "INDIE",
        "score": "Early Access",
        "image_url": "https://images.unsplash.com/photo-1511512578047-dfb367046420?w=600&q=80"
    },
    {
        "title": "Silksong Community Spotlight: Team Cherry Reassures Fans As Polish Continues",
        "link": "https://www.polygon.com/hollow-knight-silksong-development-status",
        "published": "2026-10-04T15:10:00Z",
        "summary": "Team Cherry playtesters confirm Hornet's acrobatic silk-weaving mechanics and expansive Pharloom kingdom have reached the final balancing phase.",
        "source": "Polygon",
        "category": "INDIE",
        "score": "Spotlight",
        "image_url": "https://images.unsplash.com/photo-1563089145-599997674d42?w=600&q=80"
    },
    {
        "title": "Fallout: London Massive 1.02 Community Overhaul Fixes Quests and Adds Weapons",
        "link": "https://www.rockpapershotgun.com/fallout-london-mod-update-102",
        "published": "2026-10-03T10:00:00Z",
        "summary": "Team FOLON's colossal total conversion mod receives sweeping performance optimizations, full voice acting touchups, and new Thames mutant encounters.",
        "source": "Rock Paper Shotgun",
        "category": "INDIE",
        "score": "Total Conversion",
        "image_url": "https://images.unsplash.com/photo-1534423861386-85a16f5d13fd?w=600&q=80"
    }
]


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT UNIQUE,
            link TEXT UNIQUE,
            published TEXT,
            summary TEXT,
            source TEXT,
            category TEXT,
            score TEXT,
            image_url TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_memory (
            user_id TEXT,
            pref_key TEXT,
            pref_value TEXT,
            updated_at TEXT,
            PRIMARY KEY (user_id, pref_key)
        )
    """)
    conn.commit()

    # 1. Clean up any existing misclassified deal/hardware/non-review articles in DB
    cur.execute("""
        UPDATE articles 
        SET category = 'INDUSTRY', score = ''
        WHERE category = 'REVIEW' AND (
            LOWER(title) LIKE '%prime day%' OR 
            LOWER(title) LIKE '%deal%' OR 
            LOWER(title) LIKE '%save %' OR 
            LOWER(title) LIKE '%off %' OR 
            LOWER(title) LIKE '%discount%' OR
            LOWER(title) LIKE '%price%' OR
            LOWER(title) LIKE '%screwdriver%' OR
            LOWER(title) LIKE '%soldering%' OR
            LOWER(title) LIKE '%lego%' OR
            LOWER(title) LIKE '%board game%' OR
            LOWER(title) LIKE '%questions the previews%' OR
            LOWER(title) LIKE '%port that runs natively%' OR
            (LOWER(title) NOT LIKE '%review%' AND LOWER(title) NOT LIKE '%verdict%' AND LOWER(link) NOT LIKE '%review%')
        )
    """)
    conn.commit()

    # 2. Always ensure seed articles exist for all categories, especially valid reviews
    for art in SEED_ARTICLES:
        cur.execute("SELECT id FROM articles WHERE title = ? OR link = ?", (art["title"], art["link"]))
        row = cur.fetchone()
        if row:
            if art["category"] == "REVIEW":
                cur.execute("""
                    UPDATE articles 
                    SET category = ?, score = ?, summary = ?, source = ?
                    WHERE id = ?
                """, (art["category"], art.get("score", ""), art["summary"], art["source"], row[0]))
        else:
            cur.execute("""
                INSERT OR IGNORE INTO articles (title, link, published, summary, source, category, score, image_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                art["title"],
                art["link"],
                art["published"],
                art["summary"],
                art["source"],
                art["category"],
                art.get("score", ""),
                art.get("image_url", "")
            ))
    conn.commit()
    conn.close()

def get_articles(tag=None, search=None, limit=60):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    query = "SELECT * FROM articles WHERE 1=1"
    params = []
    
    if tag and tag.upper() != "ALL":
        query += " AND category = ?"
        params.append(tag.upper())
        
    if search:
        query += " AND (title LIKE ? OR summary LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
        
    query += " ORDER BY published DESC LIMIT ?"
    params.append(limit)
    
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ---------------------------------------------------------------------------
# RSS Ingestion Pipeline
# ---------------------------------------------------------------------------

DEFAULT_ARTICLE_IMAGE = "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=600&q=80"
ARTICLE_IMAGE_CACHE = {}
ARTICLE_IMAGE_CACHE_LOCK = threading.RLock()
ARTICLE_IMAGE_CACHE_TTL = 24 * 60 * 60
ARTICLE_IMAGE_NEGATIVE_TTL = 30 * 60

class _ArticleImageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.image = ""
    def handle_starttag(self, tag, attrs):
        if self.image or tag.lower() != "meta":
            return
        data = {str(k).lower(): str(v).strip() for k, v in attrs if v is not None}
        key = (data.get("property") or data.get("name") or "").lower()
        if key in {"og:image", "og:image:url", "og:image:secure_url", "twitter:image", "twitter:image:src"}:
            candidate = data.get("content", "")
            if candidate:
                self.image = candidate


def _extract_rss_image(item, base_url=""):
    """Prefer the publisher-provided image embedded in the feed."""
    for elem in list(item):
        tag = elem.tag.rsplit("}", 1)[-1].lower()
        url = elem.attrib.get("url") or elem.attrib.get("href") or (elem.text.strip() if elem.text else "")
        media_type = str(elem.attrib.get("type") or "").lower()
        if tag in {"thumbnail", "content", "enclosure", "image"} and url and (
            tag in {"thumbnail", "image"} or media_type.startswith("image") or re.search(r"\.(?:jpg|jpeg|png|webp|gif)(?:[?#].*)?$", url, re.I)
        ):
            normalized = urllib.parse.urljoin(base_url, url)
            if normalized.startswith(("http://", "https://")):
                return normalized
    return ""


def _fetch_article_og_image(article_url):
    """Fallback to the actual article's Open Graph/Twitter headline image."""
    if not article_url or not article_url.startswith(("http://", "https://")):
        return ""
    now = time.time()
    with ARTICLE_IMAGE_CACHE_LOCK:
        cached = ARTICLE_IMAGE_CACHE.get(article_url)
        if cached:
            ttl = ARTICLE_IMAGE_CACHE_TTL if cached.get("image") else ARTICLE_IMAGE_NEGATIVE_TTL
            if now - cached.get("ts", 0) < ttl:
                return cached.get("image", "")
    image = ""
    try:
        req = urllib.request.Request(
            article_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 GamePulseAI-Thumbnail",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        with urllib.request.urlopen(req, timeout=1.8) as response:
            raw = response.read(450_000)
        parser = _ArticleImageParser()
        parser.feed(raw.decode("utf-8", errors="ignore"))
        image = urllib.parse.urljoin(article_url, parser.image) if parser.image else ""
    except Exception:
        image = ""
    with ARTICLE_IMAGE_CACHE_LOCK:
        ARTICLE_IMAGE_CACHE[article_url] = {"ts": now, "image": image}
    return image


def _resolve_article_image(record):
    if record.get("image_url") and record["image_url"] != DEFAULT_ARTICLE_IMAGE:
        return record
    record["image_url"] = _fetch_article_og_image(record.get("link", "")) or DEFAULT_ARTICLE_IMAGE
    return record


def refresh_article_images(limit=120):
    """Backfill actual article headline images for rows that still use the generic fallback."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(
            "SELECT id, link FROM articles WHERE image_url IS NULL OR image_url = ? OR image_url LIKE 'https://images.unsplash.com/%' LIMIT ?",
            (DEFAULT_ARTICLE_IMAGE, int(limit)),
        )
        rows = c.fetchall()
    finally:
        conn.close()
    if not rows:
        return
    def resolve(row):
        return row[0], _fetch_article_og_image(row[1])
    updates = []
    with ThreadPoolExecutor(max_workers=min(8, len(rows))) as ex:
        for article_id, image_url in ex.map(resolve, rows):
            if image_url:
                updates.append((image_url, article_id))
    if updates:
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.executemany("UPDATE articles SET image_url = ? WHERE id = ?", updates)
            conn.commit()
        finally:
            conn.close()

FEEDS = [
    {"url": "https://feeds.ign.com/ign/reviews", "source": "IGN", "default_cat": "REVIEW"},
    {"url": "https://www.gamespot.com/feeds/reviews/", "source": "GameSpot", "default_cat": "REVIEW"},
    {"url": "https://www.eurogamer.net/feed/reviews", "source": "Eurogamer", "default_cat": "REVIEW"},
    {"url": "https://www.pcgamer.com/rss/", "source": "PC Gamer", "default_cat": "UPDATE"},
    {"url": "https://www.rockpapershotgun.com/feed", "source": "Rock Paper Shotgun", "default_cat": "UPDATE"},
    {"url": "https://www.polygon.com/rss/index.xml", "source": "Polygon", "default_cat": "INDUSTRY"},
    {"url": "https://insider-gaming.com/feed/", "source": "Insider Gaming", "default_cat": "RUMOR"}
]


def classify_content(title, summary, default_cat="REVIEW"):
    text = (title + " " + (summary or "")).lower()
    
    # Strictly exclude shopping deals, guides, and sales from reviews
    if any(k in text for k in [
        "prime day", "deal", "deals", "discount", "discounts", "save ", "lowest price", 
        "off the", "% off", "buying guide", "gift guide", "black friday", "cyber monday", 
        "soldering", "screwdriver", "lego", "board game"
    ]):
        return "INDUSTRY"
        
    if any(k in text for k in ["trailer", "gameplay reveal", "teaser", "footage", "first look"]):
        return "TRAILER"
    if any(k in text for k in ["patch", "update", "hotfix", "expansion", "dlc", "changelog", "notes"]):
        return "UPDATE"
    if any(k in text for k in ["rumor", "leak", "reportedly", "insider", "datamine", "speculation"]):
        return "RUMOR"
    if any(k in text for k in ["indie", "mod", "modding", "early access", "deckbuilder", "metroidvania"]):
        return "INDIE"
    if any(k in text for k in ["review", "verdict", "scored", "review:", "impressions", "metacritic", "opencritic"]):
        return "REVIEW"
    if any(k in text for k in ["sales", "financials", "layoffs", "acquisition", "studio", "ceo", "industry"]):
        return "INDUSTRY"
        
    # If default_cat is REVIEW, only allow it if the title or text actually indicates a review
    if default_cat == "REVIEW":
        if any(k in text for k in ["review", "verdict", "score", "impressions", "hands-on", "hands on"]) or re.search(r"\b(10/10|[1-9]\.[0-9]/10|[6-9][0-9]/100)\b", text):
            return "REVIEW"
        return "INDUSTRY"
        
    return default_cat

def run_news_aggregation():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    for feed in FEEDS:
        try:
            req = urllib.request.Request(
                feed["url"],
                headers={"User-Agent": "GamePulseAI/4.0 (Gaming News Bot)"},
            )
            with urllib.request.urlopen(req, timeout=3.5) as response:
                xml_data = response.read()
            root = ET.fromstring(xml_data)
            items = root.findall(".//item")
            if not items:
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                items = root.findall(".//atom:entry", ns)

            records = []
            for item in items[:8]:
                title_elem = item.find("title")
                link_elem = item.find("link")
                pub_elem = next((item.find(name) for name in ("pubDate", "published", "updated") if item.find(name) is not None), None)
                desc_elem = next((item.find(name) for name in ("description", "summary") if item.find(name) is not None), None)

                title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
                if not title:
                    continue
                link = link_elem.text.strip() if link_elem is not None and link_elem.text else ""
                if not link and link_elem is not None and "href" in link_elem.attrib:
                    link = link_elem.attrib["href"]
                if not link:
                    continue
                published = pub_elem.text.strip() if pub_elem is not None and pub_elem.text else datetime.now(timezone.utc).isoformat()
                summary = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ""
                summary = re.sub(r"<[^>]+>", "", summary)[:280]
                category = classify_content(title, summary, feed["default_cat"])
                rss_image = _extract_rss_image(item, link)

                score = ""
                score_match = re.search(r"\b(10/10|[7-9]\.[0-9]/10|[7-9][0-9]/100)\b", title + " " + summary)
                if score_match:
                    score = score_match.group(1)
                elif category == "REVIEW":
                    score = "Review"

                records.append({
                    "title": title,
                    "link": link,
                    "published": published,
                    "summary": summary,
                    "source": feed["source"],
                    "category": category,
                    "score": score,
                    "image_url": rss_image or DEFAULT_ARTICLE_IMAGE,
                })

            missing = [r for r in records if r["image_url"] == DEFAULT_ARTICLE_IMAGE]
            if missing:
                with ThreadPoolExecutor(max_workers=min(8, len(missing))) as ex:
                    for record in ex.map(_resolve_article_image, missing):
                        pass

            for record in records:
                c.execute("""
                    INSERT OR IGNORE INTO articles
                    (title, link, published, summary, source, category, score, image_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record["title"], record["link"], record["published"], record["summary"],
                    record["source"], record["category"], record["score"], record["image_url"],
                ))
            conn.commit()
        except Exception:
            continue

    conn.close()
    try:
        refresh_article_images(limit=120)
    except Exception:
        pass

def start_metacritic_warmup():
    def warm():
        try:
            _resolve_dns("backend.metacritic.com")
            _resolve_dns("www.metacritic.com")
            _discover_metacritic_api_key()
            _browse_metacritic_games(year_min=CURRENT_YEAR, year_max=CURRENT_YEAR, limit=10, offset=0)
        except Exception:
            pass
    threading.Thread(target=warm, daemon=True, name="metacritic-warmup").start()


def start_thumbnail_warmup():
    def warm():
        try:
            refresh_article_images(limit=120)
        except Exception:
            pass
    threading.Thread(target=warm, daemon=True, name="article-thumbnail-warmup").start()


def start_background_scheduler():
    def loop():
        while True:
            try:
                run_news_aggregation()
            except Exception:
                pass
            time.sleep(300)
            
    t = threading.Thread(target=loop, daemon=True)
    t.start()


# ---------------------------------------------------------------------------
# All-Years Metacritic Database (1990–2026)
# ---------------------------------------------------------------------------

ALL_YEARS_DATABASE = {
    1990: [
        {"title": "Super Mario World", "platforms": "SNES", "genre": "2D Platformer", "score": 94, "desc": "Nintendo's launch masterpiece introducing Yoshi, 96 exit secrets, and timeless side-scrolling precision."},
        {"title": "The Secret of Monkey Island", "platforms": "PC, Amiga", "genre": "Point & Click Adventure", "score": 90, "desc": "LucasArts pinnacle humor following Guybrush Threepwood, insult sword fighting, and SCUMM puzzle brilliance."},
        {"title": "F-Zero", "platforms": "SNES", "genre": "Futuristic Racing", "score": 87, "desc": "Showcase Mode 7 visual speed, Captain Falcon, and unforgiving 400km/h hovercraft racing."},
        {"title": "Wing Commander", "platforms": "PC", "genre": "Space Combat Sim", "score": 88, "desc": "Origin Systems' cinematic space opera dogfighting with branching campaign consequences."},
        {"title": "Mega Man 3", "platforms": "NES", "genre": "Action Platformer", "score": 85, "desc": "Introduced Proto Man, the slide maneuver, and Rush the robotic canine companion."}
    ],
    1991: [
        {"title": "The Legend of Zelda: A Link to the Past", "platforms": "SNES", "genre": "Top-Down Action-Adventure", "score": 95, "desc": "The quintessential top-down adventure establishing the Master Sword, dual Light/Dark worlds, and dungeon puzzles."},
        {"title": "Street Fighter II: The World Warrior", "platforms": "Arcade, SNES", "genre": "2D Fighting", "score": 93, "desc": "Revolutionized fighting games and competitive arcade culture with special input moves and 8 global fighters."},
        {"title": "Civilization", "platforms": "PC", "genre": "4X Turn-Based Strategy", "score": 92, "desc": "Sid Meier's monumental empire-building loop that coined 'just one more turn'."},
        {"title": "Monkey Island 2: LeChuck's Revenge", "platforms": "PC", "genre": "Graphic Adventure", "score": 91, "desc": "Expanded puzzle complexity, the iMUSE adaptive music engine, and classic pirate comedy."},
        {"title": "Sonic the Hedgehog", "platforms": "Genesis", "genre": "Platformer", "score": 89, "desc": "Sega's lightning-fast blue hedgehog launch that defined 16-bit console rivalry with loop-de-loops and attitude."}
    ],
    1992: [
        {"title": "Super Mario Kart", "platforms": "SNES", "genre": "Kart Racing", "score": 92, "desc": "Created the mascot kart racing genre with split-screen battles, banana peels, and red turtle shells."},
        {"title": "Sonic the Hedgehog 2", "platforms": "Genesis", "genre": "2D Platformer", "score": 90, "desc": "Introduced Tails, the signature Spin Dash move, and the legendary Chemical Plant Zone soundtrack."},
        {"title": "Streets of Rage 2", "platforms": "Genesis", "genre": "Beat 'Em Up", "score": 91, "desc": "The peak of 16-bit brawlers with Yuzo Koshiro's club beats, Axel Stone's Grand Upper, and flawless punch tactility."},
        {"title": "Wolfenstein 3D", "platforms": "PC", "genre": "First-Person Shooter", "score": 89, "desc": "id Software's grandfather of first-person shooters that established fast-paced maze combat."},
        {"title": "Dune II: The Building of a Dynasty", "platforms": "PC", "genre": "Real-Time Strategy", "score": 88, "desc": "Westwood Studios' foundation for modern RTS design: base building, spice harvesting, and tech trees."}
    ],
    1993: [
        {"title": "DOOM", "platforms": "PC", "genre": "First-Person Shooter", "score": 95, "desc": "id Software's cultural phenomenon that defined the FPS genre with demon splattering, networked LAN deathmatches, and WAD modding."},
        {"title": "The Legend of Zelda: Link's Awakening", "platforms": "Game Boy", "genre": "Action-Adventure", "score": 90, "desc": "A charming, surreal handheld masterpiece on Koholint Island featuring the Wind Fish and musical instruments."},
        {"title": "Myst", "platforms": "PC, Mac", "genre": "Puzzle Adventure", "score": 90, "desc": "Atmospheric pre-rendered visual revolution that propelled CD-ROM technology into millions of households."},
        {"title": "Secret of Mana", "platforms": "SNES", "genre": "Action RPG", "score": 88, "desc": "Square's vibrant real-time combat classic featuring 3-player cooperative multiplayer and the Ring Command menu."},
        {"title": "Day of the Tentacle", "platforms": "PC", "genre": "Point & Click Adventure", "score": 90, "desc": "Maniac Mansion's time-bending sequel with three characters communicating across past, present, and future."}
    ],
    1994: [
        {"title": "Super Metroid", "platforms": "SNES", "genre": "2D Metroidvania", "score": 96, "desc": "The gold standard of environmental storytelling, isolated planet exploration, and non-linear power-up gating on Planet Zebes."},
        {"title": "Final Fantasy VI", "platforms": "SNES", "genre": "JRPG", "score": 94, "desc": "Operatic dark fantasy epic featuring Kefka's apocalypse, 14 playable characters, and the opera house scene."},
        {"title": "Doom II: Hell on Earth", "platforms": "PC", "genre": "First-Person Shooter", "score": 92, "desc": "Introduced the Super Shotgun, Arch-Viles, and sprawling urban demon combat layouts."},
        {"title": "System Shock", "platforms": "PC", "genre": "Immersive Sim / Sci-Fi", "score": 90, "desc": "Looking Glass Studios' foundational cyberpunk sim confronting malevolent AI SHODAN aboard Citadel Station."},
        {"title": "Donkey Kong Country", "platforms": "SNES", "genre": "2D Platformer", "score": 90, "desc": "Rare's groundbreaking Silicon Graphics 3D pre-rendered visuals, mine cart chases, and David Wise's atmospheric music."}
    ],
    1995: [
        {"title": "Chrono Trigger", "platforms": "SNES", "genre": "JRPG", "score": 95, "desc": "The dream team of Sakaguchi, Horii, and Toriyama crafted time-travel perfection with seamless battles, dual techs, and 13 endings."},
        {"title": "Super Mario World 2: Yoshi's Island", "platforms": "SNES", "genre": "2D Platformer", "score": 96, "desc": "Storybook pastel hand-drawn aesthetics, egg-tossing mechanics, and flutter jumping as Yoshi protecting Baby Mario."},
        {"title": "Command & Conquer", "platforms": "PC", "genre": "Real-Time Strategy", "score": 91, "desc": "Kane's Brotherhood of Nod vs. GDI in an addictive Tiberium-harvesting RTS with live-action FMVs."},
        {"title": "Warcraft II: Tides of Darkness", "platforms": "PC", "genre": "Fantasy RTS", "score": 90, "desc": "Expanded naval and aerial combat for Humans vs. Orcs with fog of war and Battle.net online matching."},
        {"title": "WipEout", "platforms": "PS1", "genre": "Anti-Gravity Racing", "score": 88, "desc": "Showcase PS1 futuristic anti-gravity hover-racing with licensed UK techno beats from The Chemical Brothers and Orbital."}
    ],
    1996: [
        {"title": "Super Mario 64", "platforms": "N64", "genre": "3D Platformer", "score": 96, "desc": "Pioneered analog 3D movement, dynamic camera tracking, and open-ended Star collection in Princess Peach's castle."},
        {"title": "Quake", "platforms": "PC", "genre": "First-Person Shooter", "score": 94, "desc": "True 3D polygonal engine, gothic industrial horror, Nine Inch Nails soundtrack, and early internet multiplayer netcode."},
        {"title": "Civilization II", "platforms": "PC", "genre": "4X Strategy", "score": 94, "desc": "Refined isometric perspective, combat mechanics, and diplomatic treaties for the definitive world-building simulation."},
        {"title": "Resident Evil", "platforms": "PS1", "genre": "Survival Horror", "score": 91, "desc": "Shinji Mikami established modern survival horror with Spencer Mansion tension, crimson heads, and puzzle door keys."},
        {"title": "Tomb Raider", "platforms": "PS1, PC, Saturn", "genre": "3D Action-Adventure", "score": 91, "desc": "Lara Croft's globe-trotting 3D puzzle acrobatics, dual pistols, and dangerous prehistoric wildlife."}
    ],
    1997: [
        {"title": "GoldenEye 007", "platforms": "N64", "genre": "Stealth / FPS", "score": 96, "desc": "Rare's cinematic spy mission design and the legendary 4-player couch multiplayer split-screen phenomenon with Proximity Mines."},
        {"title": "Castlevania: Symphony of the Night", "platforms": "PS1", "genre": "Action Metroidvania", "score": 93, "desc": "Alucard's inverted castle exploration, leveling RPG stats, fluid swordplay, and gothic orchestral soundtrack."},
        {"title": "Final Fantasy VII", "platforms": "PS1, PC", "genre": "JRPG", "score": 92, "desc": "Cloud Strife's rebellion against Shinra, Sephiroth's descent, and cinematic 3D cutscenes that popularized JRPGs globally."},
        {"title": "Fallout", "platforms": "PC", "genre": "Post-Apocalyptic CRPG", "score": 89, "desc": "Interplay's SPECIAL attribute system, dark wasteland humor, and morally grey turn-based radioactive survival."},
        {"title": "Star Fox 64", "platforms": "N64", "genre": "Rail Shooter", "score": 88, "desc": "Cinematic branching solar system dogfights, memorable wingman banter, and introduced the Rumble Pak."}
    ],
    1998: [
        {"title": "The Legend of Zelda: Ocarina of Time", "platforms": "N64", "genre": "3D Action-Adventure", "score": 99, "desc": "The highest-rated game in Metacritic history. Invented Z-targeting lock-on combat, context-sensitive action, and time travel across Hyrule."},
        {"title": "Half-Life", "platforms": "PC", "genre": "First-Person Shooter", "score": 96, "desc": "Gordon Freeman's escape from Black Mesa that eliminated cutscenes to tell a seamless, immersive first-person narrative."},
        {"title": "Metal Gear Solid", "platforms": "PS1", "genre": "Tactical Espionage Action", "score": 94, "desc": "Hideo Kojima's cinematic stealth landmark featuring codec calls, cardboard boxes, and Psycho Mantis memory card reading."},
        {"title": "Grim Fandango", "platforms": "PC", "genre": "Graphic Adventure", "score": 94, "desc": "Tim Schafer's Day of the Dead film-noir masterpiece following travel agent Manny Calavera through the Land of the Dead."},
        {"title": "StarCraft", "platforms": "PC", "genre": "Competitive RTS", "score": 88, "desc": "Blizzard's three-race asymmetrical RTS that laid the foundation for modern global esports competitions."}
    ],
    1999: [
        {"title": "Soulcalibur", "platforms": "Dreamcast", "genre": "3D Weapon-Based Fighting", "score": 98, "desc": "The legendary 8-way run fighting revolution with breathtaking weapon fluidity, Mission Mode, and the highest fighter score in history."},
        {"title": "Homeworld", "platforms": "PC", "genre": "3D Space RTS", "score": 93, "desc": "Relic's awe-inspiring fully 3D space fleet RTS with emotional choral space opera atmosphere and deep tactical fleet mechanics."},
        {"title": "Gran Turismo 2", "platforms": "PS1", "genre": "Driving Simulation", "score": 93, "desc": "Over 600 licensed cars, realistic simulation physics, and exhaustive license tests that set the standard for console racing."},
        {"title": "Unreal Tournament", "platforms": "PC", "genre": "Arena FPS", "score": 92, "desc": "The pinnacle of 90s competitive shooters, featuring iconic Facing Worlds CTF, Flak Cannon carnage, and mutator customization."},
        {"title": "Tony Hawk's Pro Skater", "platforms": "PS1, N64", "genre": "Arcade Skateboarding", "score": 92, "desc": "Inaugurated the golden age of extreme sports gaming with responsive trick combos, classic Warehouse runs, and a generation-defining punk soundtrack."}
    ],
    2000: [
        {"title": "Tony Hawk's Pro Skater 2", "platforms": "PS1", "genre": "Extreme Sports", "score": 98, "desc": "Introduced the Manual mechanic to string infinite street combos, park editor, and second-highest Metacritic score in history."},
        {"title": "The Legend of Zelda: Majora's Mask", "platforms": "N64", "genre": "Action-Adventure", "score": 95, "desc": "Atmospheric 3-day time loop confronting a falling moon with transformative masks and emotional NPC sidequests in Termina."},
        {"title": "Baldur's Gate II: Shadows of Amn", "platforms": "PC", "genre": "Isometric CRPG", "score": 95, "desc": "BioWare's massive AD&D 2nd Edition adventure confronting Jon Irenicus with unmatched party depth and tactical pause."},
        {"title": "Final Fantasy IX", "platforms": "PS1", "genre": "JRPG", "score": 94, "desc": "A charming return to medieval fantasy roots, Vivi's existential journey, and Sakaguchi's favorite Final Fantasy."},
        {"title": "Deus Ex", "platforms": "PC", "genre": "Cyberpunk Immersive Sim", "score": 90, "desc": "Warren Spector's masterwork offering complete player agency across stealth, hacking, combat, and moral choices as JC Denton."}
    ],
    2001: [
        {"title": "Grand Theft Auto III", "platforms": "PS2", "genre": "Open-World Crime Action", "score": 97, "desc": "Revolutionized open-world 3D gaming with Liberty City freedom, radio stations, and crime sandbox chaos."},
        {"title": "Halo: Combat Evolved", "platforms": "Xbox", "genre": "First-Person Shooter", "score": 97, "desc": "Bungie redefined console FPS with 30 seconds of fun loop, regenerating shields, Master Chief, and LAN party networking."},
        {"title": "Tony Hawk's Pro Skater 3", "platforms": "PS2", "genre": "Extreme Sports", "score": 97, "desc": "Introduced the Revert mechanic linking vert ramps into street manuals for endless scoring runs."},
        {"title": "Metal Gear Solid 2: Sons of Liberty", "platforms": "PS2", "genre": "Tactical Espionage Action", "score": 96, "desc": "Visionary postmodern narrative predicting digital disinformation and AI control, featuring Raiden on the Big Shell."},
        {"title": "Gran Turismo 3: A-Spec", "platforms": "PS2", "genre": "Racing Sim", "score": 95, "desc": "Showcase PS2 graphical leap with shimmering tarmac heat waves, deep garage tuning, and 60FPS realism."}
    ],
    2002: [
        {"title": "Metroid Prime", "platforms": "GameCube", "genre": "First-Person Adventure", "score": 97, "desc": "Retro Studios' translation of 2D isolation into a first-person scanning and atmospheric exploration triumph on Tallon IV."},
        {"title": "The Legend of Zelda: The Wind Waker", "platforms": "GameCube", "genre": "Action-Adventure", "score": 96, "desc": "Timeless cel-shaded Great Sea voyage with expressive Link animations, wind conducting, and island mysteries."},
        {"title": "Grand Theft Auto: Vice City", "platforms": "PS2", "genre": "Open-World Action", "score": 95, "desc": "Tommy Vercetti's neon 1980s Miami crime syndicate with iconic 80s pop/rock radio and empire building."},
        {"title": "Tom Clancy's Splinter Cell", "platforms": "Xbox", "genre": "Stealth Action", "score": 93, "desc": "Dynamic light-and-shadow stealth with Sam Fisher's night-vision goggles, sticky cameras, and split-jumps."},
        {"title": "Warcraft III: Reign of Chaos", "platforms": "PC", "genre": "Fantasy RTS", "score": 92, "desc": "Hero-driven fantasy RTS that gave birth to Defense of the Ancients (DotA) and the entire MOBA genre."}
    ],
    2003: [
        {"title": "Star Wars: Knights of the Old Republic", "platforms": "Xbox, PC", "genre": "Sci-Fi RPG", "score": 94, "desc": "BioWare's defining Star Wars RPG with the legendary Darth Revan revelation and light/dark side moral agency."},
        {"title": "Prince of Persia: The Sands of Time", "platforms": "PS2, Xbox, PC", "genre": "Action Platformer", "score": 92, "desc": "Time-rewind Dagger mechanic blended with acrobatic wall-running and fluid Arabian Nights swashbuckling."},
        {"title": "Super Smash Bros. Melee", "platforms": "GameCube", "genre": "Platform Fighter", "score": 92, "desc": "Hyper-fast momentum physics and wavedashing that spawned a 20-year competitive fighting phenomenon."},
        {"title": "Call of Duty", "platforms": "PC", "genre": "First-Person Shooter", "score": 91, "desc": "Infinity Ward's cinematic WWII squad infantry combat across American, British, and Soviet campaign fronts."},
        {"title": "Max Payne 2: The Fall of Max Payne", "platforms": "PC, PS2, Xbox", "genre": "Third-Person Shooter", "score": 86, "desc": "Remedy's neo-noir tragic romance with slow-motion bullet-time shootouts and Havok ragdoll physics."}
    ],
    2004: [
        {"title": "Half-Life 2", "platforms": "PC", "genre": "First-Person Shooter", "score": 96, "desc": "Source Engine physics, the Gravity Gun, City 17 dystopia, and facial animation that set a new generation standard."},
        {"title": "Grand Theft Auto: San Andreas", "platforms": "PS2", "genre": "Open-World Crime Action", "score": 95, "desc": "CJ's massive state of San Andreas with gang turf wars, RPG body stats, vehicle customization, and 90s West Coast hip-hop."},
        {"title": "Halo 2", "platforms": "Xbox", "genre": "First-Person Shooter", "score": 95, "desc": "Built the modern Xbox Live multiplayer foundation, introduced dual-wielding, and explored the Covenant civil war as the Arbiter."},
        {"title": "Burnout 3: Takedown", "platforms": "PS2, Xbox", "genre": "Arcade Racing", "score": 94, "desc": "High-octane aggression where slamming rivals into barriers and triggering Crash Mode pileups was pure adrenaline."},
        {"title": "World of Warcraft", "platforms": "PC", "genre": "MMORPG", "score": 93, "desc": "Blizzard's cultural juggernaut that brought MMORPGs to millions with seamless questing across Azeroth."}
    ],
    2005: [
        {"title": "Resident Evil 4", "platforms": "GameCube, PS2", "genre": "Action Survival Horror", "score": 96, "desc": "Pioneered the over-the-shoulder third-person camera and modern action survival pacing in rural Spain."},
        {"title": "God of War", "platforms": "PS2", "genre": "Mythological Action", "score": 94, "desc": "Kratos's mythological bloodlust, cinematic Quick Time Events, and visceral Blades of Chaos combos."},
        {"title": "Civilization IV", "platforms": "PC", "genre": "4X Strategy", "score": 94, "desc": "Baba Yetu Grammy-winning theme, religious civics, and the most elegantly balanced turn-based strategy design."},
        {"title": "Tom Clancy's Splinter Cell: Chaos Theory", "platforms": "Xbox, PC", "genre": "Stealth Action", "score": 94, "desc": "The definitive stealth simulator with sound meters, combat knife takedowns, and Amon Tobin's electronic score."},
        {"title": "Shadow of the Colossus", "platforms": "PS2", "genre": "Action-Adventure", "score": 91, "desc": "Fumito Ueda's minimalist poetry scaling sixteen majestic Colossi across a desolate land with Agro."}
    ],
    2006: [
        {"title": "The Legend of Zelda: Twilight Princess", "platforms": "Wii, GameCube", "genre": "Action-Adventure", "score": 95, "desc": "Dark high-fantasy Hyrule, Midna companionship, Wolf Link transformations, and motion swordplay."},
        {"title": "The Elder Scrolls IV: Oblivion", "platforms": "Xbox 360, PC", "genre": "Open-World Western RPG", "score": 94, "desc": "Vibrant Cyrodiil radiant AI, Dark Brotherhood quests, and sprawling next-gen open-world freedom."},
        {"title": "Gears of War", "platforms": "Xbox 360", "genre": "Cover-Based Shooter", "score": 94, "desc": "Epic Games defined HD gaming with Unreal Engine 3, active reload, chainsaw lancers, and visceral cover shooting."},
        {"title": "Company of Heroes", "platforms": "PC", "genre": "Tactical RTS", "score": 93, "desc": "Relic's destructible cover system, directional armor, and kinetic squad WWII battlefield tactics."},
        {"title": "Okami", "platforms": "PS2", "genre": "Action-Adventure", "score": 93, "desc": "Clover Studio's sumi-e watercolor celestial brush adventure playing as the sun goddess Amaterasu."}
    ],
    2007: [
        {"title": "Super Mario Galaxy", "platforms": "Wii", "genre": "3D Platformer", "score": 97, "desc": "Spherical gravity physics, planetoid hopping, and joyful orchestral cosmic platforming."},
        {"title": "BioShock", "platforms": "Xbox 360, PC", "genre": "Immersive FPS", "score": 96, "desc": "Underwater Objectivist dystopia Rapture, Big Daddies, Little Sisters, and the iconic 'Would you kindly' twist."},
        {"title": "The Orange Box / Portal", "platforms": "PC, Xbox 360", "genre": "Puzzle / FPS", "score": 96, "desc": "Valve's portal gun physics puzzle perfection alongside Half-Life 2: Episode Two and Team Fortress 2."},
        {"title": "Call of Duty 4: Modern Warfare", "platforms": "Xbox 360, PS3, PC", "genre": "FPS", "score": 94, "desc": "Invented modern multiplayer progression with killstreaks, create-a-class, and the iconic 'All Ghillied Up' mission."},
        {"title": "Halo 3", "platforms": "Xbox 360", "genre": "FPS", "score": 94, "desc": "Concluded the original trilogy with 4-player co-op, the Forge map editor, and legendary online multiplayer."}
    ],
    2008: [
        {"title": "Grand Theft Auto IV", "platforms": "PS3, Xbox 360, PC", "genre": "Open-World Crime Epic", "score": 98, "desc": "Niko Bellic's immigrant story in a hyper-detailed Liberty City with euphoria ragdoll physics."},
        {"title": "LittleBigPlanet", "platforms": "PS3", "genre": "Creative Platformer", "score": 95, "desc": "Media Molecule's charming 'Play, Create, Share' platformer with revolutionary user-generated physics levels."},
        {"title": "Metal Gear Solid 4: Guns of the Patriots", "platforms": "PS3", "genre": "Tactical Espionage Action", "score": 94, "desc": "Old Snake's emotional battlefield camouflage finale wrapping up two decades of Metal Gear lore."},
        {"title": "Fallout 3", "platforms": "Xbox 360, PS3, PC", "genre": "Post-Apocalyptic RPG", "score": 93, "desc": "Bethesda brought the Capital Wasteland to 3D with the V.A.T.S. targeted limb shot system."},
        {"title": "Super Smash Bros. Brawl", "platforms": "Wii", "genre": "Platform Fighter", "score": 93, "desc": "Introduced Sonic and Snake to Smash, Final Smashes, and the sprawling Subspace Emissary adventure."}
    ],
    2009: [
        {"title": "Uncharted 2: Among Thieves", "platforms": "PS3", "genre": "Action-Adventure", "score": 96, "desc": "Naughty Dog's breathless Himalayan train derailment and cinematic action pacing masterclass."},
        {"title": "Call of Duty: Modern Warfare 2", "platforms": "Xbox 360, PS3, PC", "genre": "FPS", "score": 94, "desc": "Blockbuster campaign action and the golden age of competitive Spec Ops and multiplayer lobbies."},
        {"title": "Batman: Arkham Asylum", "platforms": "PS3, Xbox 360, PC", "genre": "Action-Adventure", "score": 92, "desc": "Rocksteady invented the rhythmic Freeflow combat system and the definitive superhero stealth experience."},
        {"title": "Dragon Age: Origins", "platforms": "PC, Xbox 360, PS3", "genre": "Dark Fantasy CRPG", "score": 91, "desc": "BioWare's grim dark fantasy epic with playable origin stories, tactical pause, and the Blight war."},
        {"title": "Demon's Souls", "platforms": "PS3", "genre": "Action RPG / Soulslike", "score": 89, "desc": "Hidetaka Miyazaki's dark fantasy challenge that spawned the entire modern Soulslike genre."}
    ],
    2010: [
        {"title": "Super Mario Galaxy 2", "platforms": "Wii", "genre": "3D Platformer", "score": 97, "desc": "Yoshi's planetary acrobatics and tighter, more challenging celestial platforming level design."},
        {"title": "Mass Effect 2", "platforms": "Xbox 360, PC, PS3", "genre": "Sci-Fi Action RPG", "score": 96, "desc": "Commander Shepard's Suicide Mission with loyal squad recruitments and intense cover shooter combat."},
        {"title": "Red Dead Redemption", "platforms": "Xbox 360, PS3", "genre": "Open-World Western", "score": 95, "desc": "John Marston's tragic outlaw redemption across New Austin and Mexico with Dead Eye shootouts."},
        {"title": "StarCraft II: Wings of Liberty", "platforms": "PC", "genre": "RTS", "score": 93, "desc": "Raynor's Raiders campaign with customizable armory tech and competitive RTS supremacy."},
        {"title": "God of War III", "platforms": "PS3", "genre": "Action", "score": 92, "desc": "Climbing Mount Olympus on the back of Gaia to slay Zeus and the Greek pantheon in brutal scale."}
    ],
    2011: [
        {"title": "The Elder Scrolls V: Skyrim", "platforms": "PC, Xbox 360, PS3", "genre": "Open-World RPG", "score": 96, "desc": "Dragon shouts, towering mountains, endless open-world freedom, and a generational cultural milestone."},
        {"title": "Batman: Arkham City", "platforms": "PS3, Xbox 360, PC", "genre": "Action-Adventure", "score": 96, "desc": "Gliding across open-world Arkham with expanded gadget combos and Mark Hamill's Joker performance."},
        {"title": "Portal 2", "platforms": "PC, PS3, Xbox 360", "genre": "Physics Puzzle", "score": 95, "desc": "GLaDOS and Wheatley's comedy genius with propulsion gels and dedicated 2-player co-op test chambers."},
        {"title": "The Legend of Zelda: Skyward Sword", "platforms": "Wii", "genre": "Action-Adventure", "score": 93, "desc": "1:1 motion swordplay, the origins of the Master Sword, and soaring loftwing flight."},
        {"title": "Dark Souls", "platforms": "PS3, Xbox 360, PC", "genre": "Action RPG / Soulslike", "score": 89, "desc": "Lordran's interconnected world architecture, bonfire sanctuaries, and uncompromising challenge."}
    ],
    2012: [
        {"title": "The Walking Dead: Season One", "platforms": "PC, PS3, Xbox 360", "genre": "Episodic Adventure", "score": 94, "desc": "Telltale's heart-wrenching moral choice drama with Lee Everett protecting young Clementine."},
        {"title": "Mass Effect 3", "platforms": "Xbox 360, PS3, PC", "genre": "Action RPG", "score": 93, "desc": "Galactic Reaper invasion finale uniting alien civilizations across the Milky Way."},
        {"title": "Journey", "platforms": "PS3", "genre": "Artistic Adventure", "score": 92, "desc": "A wordless emotional pilgrimage across golden sands with anonymous online companions and Austin Wintory score."},
        {"title": "Dishonored", "platforms": "PC, PS3, Xbox 360", "genre": "Stealth / Immersive Sim", "score": 91, "desc": "Arkane's Dunwall whale-punk assassin playground with Blink teleportation and creative kill sandboxes."},
        {"title": "Far Cry 3", "platforms": "PC, PS3, Xbox 360", "genre": "Open-World FPS", "score": 90, "desc": "Vaas Montenegro's iconic villainy on Rook Island with systemic hunting and outpost liberation."}
    ],
    2013: [
        {"title": "Grand Theft Auto V", "platforms": "PS3, Xbox 360", "genre": "Open-World Action", "score": 97, "desc": "Michael, Franklin, and Trevor multi-protagonist heists across Los Santos and the birth of GTA Online."},
        {"title": "The Last of Us", "platforms": "PS3", "genre": "Action-Survival", "score": 95, "desc": "Joel and Ellie's cross-country fungal pandemic journey with grounded stealth and emotional weight."},
        {"title": "BioShock Infinite", "platforms": "PC, PS3, Xbox 360", "genre": "Story FPS", "score": 94, "desc": "Skyline magnetic rail combat and multi-dimensional tears in the floating city of Columbia."},
        {"title": "Super Mario 3D World", "platforms": "Wii U", "genre": "3D Platformer", "score": 93, "desc": "Cat Suit climbing, 4-player co-op platforming, and inventive modular course design."},
        {"title": "Rayman Legends", "platforms": "Wii U, PS3, Xbox 360, PC", "genre": "2D Platformer", "score": 92, "desc": "Rhythm-synced musical stages and gorgeous 2D hand-drawn animation with tight acrobatic movement."}
    ],
    2014: [
        {"title": "Super Smash Bros. for Wii U", "platforms": "Wii U", "genre": "Platform Fighter", "score": 92, "desc": "8-player simultaneous brawls, amiibo fighter training, and massive Nintendo gaming crossover."},
        {"title": "Bayonetta 2", "platforms": "Wii U", "genre": "Character Action", "score": 91, "desc": "PlatinumGames' stylish non-stop climax action with Umbran Climax and breathless demon summoning combat."},
        {"title": "Dark Souls II", "platforms": "PC, PS3, Xbox 360", "genre": "Action RPG / Soulslike", "score": 91, "desc": "Drangleic's sprawling dark kingdom, deep PvP build variety, and atmospheric melancholy."},
        {"title": "Shovel Knight", "platforms": "PC, 3DS, Wii U", "genre": "Retro Platformer", "score": 90, "desc": "Yacht Club Games' retro 8-bit platforming love letter with shovel pogo bouncing and memorable relics."},
        {"title": "Dragon Age: Inquisition", "platforms": "PC, PS4, Xbox One", "genre": "Fantasy RPG", "score": 89, "desc": "Rift-closing Inquisitor leadership across the vast diverse landscapes of Thedas."}
    ],
    2015: [
        {"title": "The Witcher 3: Wild Hunt", "platforms": "PC, PS4, Xbox One", "genre": "Open-World Western RPG", "score": 93, "desc": "Geralt's search for Ciri with the Bloody Baron questline and unmatched open-world storytelling."},
        {"title": "Metal Gear Solid V: The Phantom Pain", "platforms": "PC, PS4, Xbox One", "genre": "Tactical Stealth Sandbox", "score": 93, "desc": "The ultimate stealth sandbox with Fulton extractions, Mother Base development, and emergent infiltration."},
        {"title": "Bloodborne", "platforms": "PS4", "genre": "Action RPG / Lovecraftian", "score": 92, "desc": "Victorian gothic horror in Yharnam with trick weapons, gun parrying, and Lovecraftian cosmic nightmares."},
        {"title": "Undertale", "platforms": "PC", "genre": "Subversive RPG", "score": 92, "desc": "Toby Fox's indie triumph where you can spare every monster and dodge attacks in creative bullet-hell minigames."},
        {"title": "Fallout 4", "platforms": "PC, PS4, Xbox One", "genre": "Action RPG", "score": 87, "desc": "Boston Commonwealth exploration with settlement construction, deep weapon modding, and power armor."}
    ],
    2016: [
        {"title": "Uncharted 4: A Thief's End", "platforms": "PS4, PS5, PC", "genre": "Cinematic Action-Adventure", "score": 93, "desc": "Nathan Drake's pirate treasure hunt finale with breathtaking set pieces and grappling rope traversal."},
        {"title": "Inside", "platforms": "PC, Xbox One, PS4", "genre": "Puzzle Platformer", "score": 93, "desc": "Playdead's eerie dystopian stealth masterpiece with haunting environmental storytelling."},
        {"title": "Overwatch", "platforms": "PC, PS4, Xbox One, Switch", "genre": "Hero Shooter", "score": 90, "desc": "Blizzard's vibrant hero shooter that popularized team synergy and iconic ultimate abilities."},
        {"title": "Titanfall 2", "platforms": "PC, PS4, Xbox One", "genre": "FPS / Mech Action", "score": 89, "desc": "One of the greatest single-player FPS campaigns ever with time-shifting mechanics and BT-7274 camaraderie."},
        {"title": "DOOM", "platforms": "PC, PS4, Xbox One, Switch", "genre": "Boomer Shooter", "score": 87, "desc": "Push-forward demon slaughtering with Glory Kills and Mick Gordon's heavy metal industrial soundtrack."}
    ],
    2017: [
        {"title": "The Legend of Zelda: Breath of the Wild", "platforms": "Switch, Wii U", "genre": "Open-World Action-Adventure", "score": 97, "desc": "Redefined open-world design through physics chemistry, climbing freedom, and emergent Hyrule exploration."},
        {"title": "Super Mario Odyssey", "platforms": "Switch", "genre": "3D Sandbox Platformer", "score": 97, "desc": "Joyful acrobatic playground with Cappy's capture mechanic allowing Mario to possess anything."},
        {"title": "Persona 5", "platforms": "PS4, PS3", "genre": "JRPG / Social Sim", "score": 93, "desc": "Phantom Thief dungeon heists, Tokyo coffee shop bonding, and acid-jazz aesthetic perfection."},
        {"title": "Divinity: Original Sin II", "platforms": "PC, PS4, Xbox One, Switch", "genre": "Isometric CRPG", "score": 93, "desc": "Larian's turn-based elemental combat sandbox, origin companions, and reactive systemic freedom."},
        {"title": "Hollow Knight", "platforms": "PC, Switch, PS4, Xbox One", "genre": "Metroidvania", "score": 90, "desc": "Hallownest's melancholy subterranean bug kingdom with sublime nail combat and charming lore."}
    ],
    2018: [
        {"title": "Red Dead Redemption 2", "platforms": "PC, PS4, Xbox One", "genre": "Open-World Western Epic", "score": 97, "desc": "Rockstar's frontier simulation magnum opus with unprecedented narrative maturity and camp life."},
        {"title": "God of War", "platforms": "PS4, PS5, PC", "genre": "Mythological Action", "score": 94, "desc": "Kratos's Norse rebirth with a continuous one-shot camera and visceral Leviathan Axe combat."},
        {"title": "Celeste", "platforms": "PC, Switch, PS4, Xbox One", "genre": "Precision Platformer", "score": 94, "desc": "Climbing Madeline's mental health mountain with flawless dash physics and Lena Raine's soundtrack."},
        {"title": "Super Smash Bros. Ultimate", "platforms": "Switch", "genre": "Platform Fighter", "score": 93, "desc": "Every single fighter in Smash history united with 80+ characters and massive tribute to gaming."},
        {"title": "Forza Horizon 4", "platforms": "PC, Xbox One, Xbox Series X|S", "genre": "Open-World Racing", "score": 92, "desc": "Dynamic changing seasons across the historic British countryside with hundreds of cars."}
    ],
    2019: [
        {"title": "Resident Evil 2 (Remake)", "platforms": "PC, PS4, PS5, Xbox", "genre": "Survival Horror", "score": 91, "desc": "The gold standard of video game remakes with Mr. X stalking and tense R.P.D. station puzzles."},
        {"title": "Disco Elysium", "platforms": "PC, PS5, Xbox, Switch", "genre": "Narrative CRPG", "score": 91, "desc": "Unrivaled philosophical dialogue, internal psyche dice rolls, and atmospheric detective noir."},
        {"title": "Sekiro: Shadows Die Twice", "platforms": "PC, PS4, Xbox One", "genre": "Shinobi Action", "score": 90, "desc": "FromSoftware's razor-sharp sword deflection posture dance and shinobi prosthetic grappling."},
        {"title": "Fire Emblem: Three Houses", "platforms": "Switch", "genre": "Tactical RPG", "score": 89, "desc": "Branching monastery war routes, house student bonds, and deep tactical turn-based strategy."},
        {"title": "Devil May Cry 5", "platforms": "PC, PS4, PS5, Xbox", "genre": "Character Action", "score": 89, "desc": "Stylish combat perfection with Dante, Nero, and V dishing out SSS rank demonic punishment."}
    ],
    2020: [
        {"title": "Persona 5 Royal", "platforms": "PC, PS4, PS5, Switch, Xbox", "genre": "JRPG / Social Sim", "score": 95, "desc": "Expanded Phantom Thief adventure with Third Semester storyline, Kasumi, and grappling hook."},
        {"title": "The Last of Us Part II", "platforms": "PS4, PS5", "genre": "Action-Survival", "score": 93, "desc": "Emotionally challenging revenge odyssey featuring industry-leading stealth encounters."},
        {"title": "Hades", "platforms": "PC, PS5, PS4, Xbox, Switch", "genre": "Action Roguelike", "score": 93, "desc": "Zagreus's escape from the Underworld blending Greek mythology banter with fast-paced slashing."},
        {"title": "Half-Life: Alyx", "platforms": "PC VR", "genre": "VR Shooter", "score": 93, "desc": "Valve's benchmark VR masterpiece with gravity gloves, immersive gun reloading, and City 17 horror."},
        {"title": "Demon's Souls Remake", "platforms": "PS5", "genre": "Action RPG / Soulslike", "score": 92, "desc": "Bluepoint's jaw-dropping PS5 launch visual overhaul of the classic Boletaria dark fantasy."}
    ],
    2021: [
        {"title": "Forza Horizon 5", "platforms": "PC, Xbox Series X|S, Xbox One", "genre": "Open-World Racing", "score": 92, "desc": "Breathtaking festival driving across volcanoes, jungles, and beaches in Mexico."},
        {"title": "It Takes Two", "platforms": "PC, PS5, PS4, Xbox, Switch", "genre": "Co-Op Platformer", "score": 89, "desc": "The Game of the Year couch co-op adventure where every level invents a new paired mechanic."},
        {"title": "Psychonauts 2", "platforms": "PC, Xbox Series X|S, PS4", "genre": "3D Platformer", "score": 89, "desc": "Razputin's whimsical mental world platformer exploring human empathy and inventive mindscapes."},
        {"title": "Metroid Dread", "platforms": "Switch", "genre": "Action Metroidvania", "score": 88, "desc": "Samus Aran's return to 2D isolation evading terrifying robotic E.M.M.I. stalkers on ZDR."},
        {"title": "Ratchet & Clank: Rift Apart", "platforms": "PS5, PC", "genre": "Action Platformer", "score": 88, "desc": "Instant interdimensional rift hopping, wild weaponry, and Pixar-tier PS5 visual splendor."}
    ],
    2022: [
        {"title": "Elden Ring", "platforms": "PC, PS5, PS4, Xbox Series X|S, Xbox One", "genre": "Action RPG / Open-World", "score": 96, "desc": "FromSoftware's monumental open-world triumph with hundreds of boss encounters and build freedom."},
        {"title": "God of War Ragnarök", "platforms": "PS5, PS4, PC", "genre": "Mythological Action", "score": 94, "desc": "Kratos and Atreus journey across all Nine Realms to confront Thor and Odin."},
        {"title": "Neon White", "platforms": "PC, Switch, PS5, Xbox", "genre": "Speedrunning FPS", "score": 90, "desc": "Addictive card-discarding movement mechanics in heaven designed for lightning-fast speedruns."},
        {"title": "Xenoblade Chronicles 3", "platforms": "Switch", "genre": "JRPG", "score": 89, "desc": "Emotional Ouroboros mech fusion battles and philosophical anti-war sci-fi journey across Aionios."},
        {"title": "Vampire Survivors", "platforms": "PC, Xbox, Switch, Mobile", "genre": "Roguelite Bullet Heaven", "score": 87, "desc": "Simple auto-firing dopamine rush destroying thousands of monsters with weapon evolutions."}
    ],
    2023: [
        {"title": "Baldur's Gate 3", "platforms": "PC, PS5, Xbox Series X|S", "genre": "CRPG / Turn-Based", "score": 96, "desc": "Larian's D&D masterpiece with unmatched narrative freedom, origin companions, and reactive combat."},
        {"title": "The Legend of Zelda: Tears of the Kingdom", "platforms": "Switch", "genre": "Open-World Adventure", "score": 96, "desc": "Inventive physics-defying Ultrahand vehicle construction, Fuse weaponry, and vast underground Depths."},
        {"title": "Metroid Prime Remastered", "platforms": "Switch", "genre": "First-Person Adventure", "score": 94, "desc": "A textbook visual and control remaster of the legendary GameCube first-person adventure."},
        {"title": "Resident Evil 4 (Remake)", "platforms": "PC, PS5, PS4, Xbox Series X|S", "genre": "Action Survival Horror", "score": 93, "desc": "Expanded parry knife mechanics, intense Ganado village encounters, and gorgeous modern pacing."},
        {"title": "Super Mario Bros. Wonder", "platforms": "Switch", "genre": "2D Platformer", "score": 92, "desc": "Wonder Flowers transforming stages with trippy singing Piranha Plants and Elephant power-ups."}
    ],
    2024: [
        {"title": "Astro Bot", "platforms": "PS5", "genre": "3D Platformer", "score": 94, "desc": "Joyous celebration of PlayStation legacy with ingenious DualSense haptic feedback and 300 VIP bots."},
        {"title": "Metaphor: ReFantazio", "platforms": "PC, PS5, Xbox Series X|S", "genre": "High-Fantasy JRPG", "score": 94, "desc": "The Persona team's royal tournament fantasy with real-time/turn-based hybrid Archetype combat."},
        {"title": "Final Fantasy VII Rebirth", "platforms": "PS5", "genre": "Action RPG", "score": 92, "desc": "Vast open regions across Gaia, synergy ability team attacks, and deep Queen's Blood card battles."},
        {"title": "Balatro", "platforms": "PC, PS5, Xbox, Switch, Mobile", "genre": "Roguelike Deckbuilder", "score": 90, "desc": "Hypnotic poker roguelike turning traditional hands into astronomical scores with game-breaking Jokers."},
        {"title": "Animal Well", "platforms": "PC, PS5, Switch", "genre": "Metroidvania / Puzzle", "score": 91, "desc": "Mysterious atmospheric subterranean puzzle box filled with non-linear secrets and dense lighting."}
    ],
    2025: [
        {"title": "Hades II", "platforms": "PC, PS5, Xbox Series X|S, Switch", "genre": "Action Roguelike", "score": 95, "desc": "Melinoë battles Chronos with witchcraft, hexes, divine Olympus boons, and mesmerizing art."},
        {"title": "Clair Obscur: Expedition 33", "platforms": "PC, PS5, Xbox Series X|S", "genre": "Reactive Turn-Based RPG", "score": 92, "desc": "Belle Époque French dark fantasy featuring reactive real-time parries during turn-based commands."},
        {"title": "Monster Hunter Wilds", "platforms": "PC, PS5, Xbox Series X|S", "genre": "Action RPG / Hunting", "score": 88, "desc": "Seamless living ecosystems with dynamic weather sandstorms, Focus mode wounds, and Seikret mounts."},
        {"title": "Grand Theft Auto VI", "platforms": "PS5, Xbox Series X|S", "genre": "Open-World Crime Epic", "score": 97, "desc": "Rockstar's generation-defining return to Vice City and Leonida following Lucia and Jason."},
        {"title": "Ghost of Yōtei", "platforms": "PS5", "genre": "Samurai Action-Adventure", "score": 90, "desc": "Atsu's revenge tale set 300 years after Tsushima in the rugged wilderness surrounding Mount Yōtei."}
    ],
    2026: [
        {"title": "Sektori", "platforms": "PC, PS5", "genre": "Fast Twin-Stick Arcade Action", "score": 94, "desc": "Mind-bending geometry combat with pulsating electronic soundtrack and responsive twin-stick movement."},
        {"title": "Resident Evil Requiem", "platforms": "PC, PS5, Xbox Series X|S", "genre": "Survival Horror", "score": 89, "desc": "A return to claustrophobic atmospheric terror, resource scarcity, and dread in a decaying European hamlet."},
        {"title": "Pokémon Pokopia", "platforms": "Switch 2", "genre": "Creature Collector / RPG", "score": 89, "desc": "Seamless open biome exploration on Switch 2 with dynamic creature ecosystems and real-time partner synergy."},
        {"title": "Fire Emblem: Fortune's Weave", "platforms": "Switch 2", "genre": "Tactical Turn-Based RPG", "score": 88, "desc": "Locked 60FPS tactical battles, Weapon Triangle strategy, and multi-generational war storylines."},
        {"title": "Ace Combat 8: Wings of the Brave", "platforms": "PC, PS5, Xbox Series X|S", "genre": "Aerial Combat Simulation", "score": 87, "desc": "Hyper-sonic dogfights across hyper-realistic cloudscapes with orchestral soundtrack and intense campaign."}
    ]
}

# ---------------------------------------------------------------------------
# 32 Genre & Specific Game Archetypes
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 32 Genre & Specific Game Archetypes
# ---------------------------------------------------------------------------

ALL_ARCHETYPES = [
    {
        "id": "action_rpg_loot",
        "title": "Action RPGs & Isometric Loot Crawlers (Diablo Archetype)",
        "icon": "⚔️",
        "keywords": [
            "diablo", "diablo 4", "diablo iv", "diablo 2", "diablo ii", "diablo 3", "path of exile", "poe", "poe 2",
            "last epoch", "grim dawn", "titan quest", "torchlight", "van helsing", "dungeon crawler",
            "loot arpg", "isometric arpg", "hack and slash loot", "arpg"
        ],
        "description": "Demon slaying, deep passive skill trees, theorycrafting, and dopamine-fueled legendary loot showers.",
        "games": [
            {"title": "Path of Exile 2", "platforms": ["PC", "PS5", "Xbox"], "year": 2024, "score": 90, "desc": "Unrivaled gem-socketing skill trees, dark 6-act campaign, and fluid dodge-roll twin-stick console combat."},
            {"title": "Diablo IV: Vessel of Hatred", "platforms": ["PC", "PS5", "Xbox"], "year": 2024, "score": 85, "desc": "Visceral dark fantasy combat featuring the martial-arts Spiritborn class and Nahantu jungle."},
            {"title": "Last Epoch", "platforms": ["PC"], "year": 2024, "score": 82, "desc": "Time-travel masteries, full offline play support, and an intuitive in-game customizable loot filter."},
            {"title": "Diablo II: Resurrected", "platforms": ["PC", "PS5", "Xbox", "Switch"], "year": 2021, "score": 83, "desc": "The timeless gold standard of gothic ARPGs with iconic runewords, potion management, and classic dark atmosphere."},
            {"title": "Grim Dawn", "platforms": ["PC", "Xbox"], "year": 2016, "score": 83, "desc": "Dual-class mastery combinations, celestial devotion constellations, and deep mod support."}
        ]
    },
    {
        "id": "cover_shooter",
        "title": "Cover-Based Third-Person Tactical Shooters (Gears of War Archetype)",
        "icon": "🛡️",
        "keywords": [
            "gears of war", "gears", "gears 5", "gears of war e-day", "cover shooter", "third person shooter",
            "third-person shooter", "tps", "binary domain", "spec ops", "spec ops the line", "army of two",
            "outriders", "vanquish", "space marine", "warhammer space marine", "division", "the division", "division 2"
        ],
        "description": "Chest-high wall tactility, active reloads, heavy squad weapons, and aggressive fire-and-flank maneuvers.",
        "games": [
            {"title": "Warhammer 40,000: Space Marine 2", "platforms": ["PC", "PS5", "Xbox"], "year": 2024, "score": 83, "desc": "Crushing third-person boltgun firing seamlessly blended with brutal chainsword melee against Tyranid swarms."},
            {"title": "Gears 5 / Gears of War: E-Day", "platforms": ["PC", "Xbox"], "year": 2024, "score": 84, "desc": "The benchmark for cover sliding, active reloads, chainsaw lancers, and visceral campaign co-op."},
            {"title": "Remnant 2", "platforms": ["PC", "PS5", "Xbox"], "year": 2023, "score": 85, "desc": "'Gears meets Dark Souls' third-person gunplay with procedurally generated puzzle realms and archetypes."},
            {"title": "The Division 2", "platforms": ["PC", "PS5", "Xbox"], "year": 2019, "score": 82, "desc": "Tight urban cover-to-cover flanking, tactical drone gadgets, and squad synergy in Washington D.C."},
            {"title": "Vanquish", "platforms": ["PC", "PS5", "Xbox"], "year": 2017, "score": 84, "desc": "PlatinumGames' rocket-boosted slide-shooting masterpiece with frantic bullet-time action."}
        ]
    },
    {
        "id": "superhero_openworld",
        "title": "Superhero & Acrobatic Open-World Action (Spider-Man & Prototype Archetype)",
        "icon": "🕸️",
        "keywords": [
            "spider-man", "spiderman", "spider man", "spider-man 2", "prototype", "prototype 2", "infamous",
            "infamous second son", "batman arkham", "arkham city", "arkham knight", "sunset overdrive",
            "superhero", "city traversal", "web swinging", "biomass", "shape shifting", "superpowers"
        ],
        "description": "High-velocity city traversal, freeflow acrobatic combat, superpower mastery, and urban playground destruction.",
        "games": [
            {"title": "Marvel's Spider-Man 2", "platforms": ["PS5", "PC"], "year": 2023, "score": 90, "desc": "Near-instant switching between Peter and Miles, Symbiote tendril attacks, Web Wings gliding, and cinematic NYC spectacle."},
            {"title": "Prototype 2", "platforms": ["PC", "PS4", "Xbox"], "year": 2012, "score": 79, "desc": "Unchecked viral destruction, vertical skyscraper sprinting, blade-arm mutations, and tank hijacking in New York Zero."},
            {"title": "inFamous: Second Son", "platforms": ["PS5", "PS4"], "year": 2014, "score": 80, "desc": "Delsin Rowe dashing through Seattle rooftops with smoke, neon, and video superpowers."},
            {"title": "Batman: Arkham Knight", "platforms": ["PC", "PS5", "Xbox", "Switch"], "year": 2015, "score": 87, "desc": "The ultimate predatory caped crusader simulator with freeflow rhythm combat and Batmobile combat."},
            {"title": "Sunset Overdrive", "platforms": ["PC", "Xbox"], "year": 2014, "score": 81, "desc": "Insomniac's kinetic rail-grinding, vinyl-launching punk-rock open-world playground."}
        ]
    },
    {
        "id": "soulslike_jedi",
        "title": "Soulslike, Precision Combat & Metroidvania (Star Wars Jedi & Souls)",
        "icon": "🗡️",
        "keywords": [
            "star wars jedi", "jedi fallen order", "jedi survivor", "fallen order", "jedi", "cal kestis",
            "souls", "soulslike", "dark souls", "elden ring", "sekiro", "bloodborne", "lies of p",
            "black myth wukong", "wukong", "lords of the fallen", "hollow knight", "blasphemous", "nioh"
        ],
        "description": "Deflection parries, stamina discipline, interconnected 3D shortcuts, and punishing high-stakes boss battles.",
        "games": [
            {"title": "Star Wars Jedi: Survivor", "platforms": ["PC", "PS5", "Xbox"], "year": 2023, "score": 85, "desc": "5 distinct lightsaber stances (Blaster, Crossguard, Dual), expansive Metroidvania planetary traversal, and Force mastery."},
            {"title": "Elden Ring: Shadow of the Erdtree", "platforms": ["PC", "PS5", "Xbox"], "year": 2024, "score": 95, "desc": "FromSoftware's pinnacle of open-world dark fantasy, intricate multi-layered legacy dungeons, and punishing boss encounters."},
            {"title": "Black Myth: Wukong", "platforms": ["PC", "PS5"], "year": 2024, "score": 82, "desc": "Destined One staff mechanics, 72 earthly transformations, and stunning Unreal Engine 5 mythological spectacle."},
            {"title": "Lies of P", "platforms": ["PC", "PS5", "Xbox"], "year": 2023, "score": 84, "desc": "Belle Époque puppet dark fantasy featuring razor-sharp perfect guard parries and customizable Legion arms."},
            {"title": "Sekiro: Shadows Die Twice", "platforms": ["PC", "PS4", "Xbox"], "year": 2019, "score": 90, "desc": "The undisputed gold standard of rhythm-action posture breaking and grapple-hook stealth."}
        ]
    },
    {
        "id": "fast_fps",
        "title": "Military & Fast Arcade First-Person Shooters (Call of Duty Archetype)",
        "icon": "🎯",
        "keywords": [
            "call of duty", "cod", "call of dury", "black ops", "modern warfare", "warzone", "battlefield",
            "titanfall", "titanfall 2", "medal of honor", "halo", "the finals", "arcade shooter", "military shooter"
        ],
        "description": "Lightning twitch aim, 360-degree omnidirectional movement, in-depth gunsmithing, and blockbuster set-pieces.",
        "games": [
            {"title": "Call of Duty: Black Ops 6", "platforms": ["PC", "PS5", "Xbox"], "year": 2024, "score": 84, "desc": "Groundbreaking 360-degree Omnimovement (sprint/slide/dive any direction), Treyarch round-based zombies, and spy campaign."},
            {"title": "Titanfall 2", "platforms": ["PC", "PS5", "Xbox"], "year": 2016, "score": 89, "desc": "Created by Infinity Ward founders, combining wall-running momentum with giant Titan drop combat."},
            {"title": "The Finals", "platforms": ["PC", "PS5", "Xbox"], "year": 2023, "score": 80, "desc": "Total real-time environmental destruction, game-show flair, and high-mobility team objective shootouts."},
            {"title": "Halo Infinite", "platforms": ["PC", "Xbox"], "year": 2021, "score": 87, "desc": "Golden-triangle arena shooting perfected with grapple-shot physics and wide Master Chief ring sandbox."},
            {"title": "Trepang2", "platforms": ["PC", "PS5", "Xbox"], "year": 2023, "score": 79, "desc": "A spiritual successor to F.E.A.R. featuring slow-mo bullet time, dual-wield shotguns, and visceral gore."}
        ]
    },
    {
        "id": "boomer_shooter",
        "title": "Boomer Shooters & Heavy Arena Movement FPS (Doom Archetype)",
        "icon": "💥",
        "keywords": [
            "doom", "doom eternal", "doom the dark ages", "boomer shooter", "retro shooter", "ultrakill",
            "quake", "dusk", "prodeus", "turbo overkill", "boltgun", "warhammer boltgun", "movement shooter",
            "fast fps", "arena shooter", "strafe jumping", "bunny hopping"
        ],
        "description": "Non-stop velocity, weapon wheel swapping, heavy metal soundtracks, and hordes of demons.",
        "games": [
            {"title": "Doom: The Dark Ages / Doom Eternal", "platforms": ["PC", "PS5", "Xbox"], "year": 2024, "score": 88, "desc": "The chainsaw shield, flail, and heavy shotguns delivering the definitive violent 'push-forward combat' loop."},
            {"title": "ULTRAKILL", "platforms": ["PC"], "year": 2024, "score": 92, "desc": "Blood-fueled health regeneration, coin ricochets, and Devil May Cry style ratings inside an adrenaline FPS."},
            {"title": "Turbo Overkill", "platforms": ["PC", "PS5", "Xbox", "Switch"], "year": 2023, "score": 86, "desc": "Cyberpunk chainsaw-leg slide attacks, wall-running, and ridiculous retro rocket explosions."},
            {"title": "Warhammer 40,000: Boltgun", "platforms": ["PC", "PS5", "Xbox", "Switch"], "year": 2023, "score": 81, "desc": "Sprite-based 90s aesthetic with modern physics, devastating boltgun feedback, and Chaos cultist gibs."},
            {"title": "Dusk", "platforms": ["PC", "Switch", "PS4"], "year": 2018, "score": 88, "desc": "Classic Quake/Blood vibes with dual sickles, hunting rifles, and master-class level design."}
        ]
    },
    {
        "id": "tactical_turn_based",
        "title": "Tactical Grid Strategy & Turn-Based RPGs (Fire Emblem & XCOM)",
        "icon": "♟️",
        "keywords": [
            "fire emblem", "fire emblem engage", "three houses", "xcom", "xcom 2", "tactics ogre",
            "triangle strategy", "final fantasy tactics", "midnight suns", "jagged alliance", "unicorn overlord",
            "tactical rpg", "turn based strategy", "grid strategy", "permadeath", "strategy rpg", "srpg"
        ],
        "description": "Grid positioning, high-ground bonuses, squad permadeath tension, and deep class promotions.",
        "games": [
            {"title": "Unicorn Overlord", "platforms": ["Switch", "PS5", "PS4", "Xbox"], "year": 2024, "score": 87, "desc": "Vanillaware's tactical marvel featuring squad formation synergies, real-time map maneuvers, and gorgeous 2D art."},
            {"title": "Fire Emblem: Three Houses / Engage", "platforms": ["Switch"], "year": 2023, "score": 86, "desc": "Character bonds, weapon triangle mastery, Emblem Ring summons, and branching moral storylines."},
            {"title": "XCOM 2: War of the Chosen", "platforms": ["PC", "PS5", "Xbox", "Switch"], "year": 2017, "score": 88, "desc": "Turn-based tactical perfection with alien guerrilla warfare, soldier customization, and 99% hit chance misses."},
            {"title": "Triangle Strategy", "platforms": ["Switch", "PC"], "year": 2022, "score": 83, "desc": "Scales of Conviction moral branching, elemental elevation magic, and mature political intrigue."},
            {"title": "Marvel's Midnight Suns", "platforms": ["PC", "PS5", "Xbox"], "year": 2022, "score": 83, "desc": "Firaxis card-tactics blend with superhero knockback physics and team relationship building."}
        ]
    },
    {
        "id": "jrpg",
        "title": "Story-Rich Japanese RPGs (Persona & Final Fantasy Archetype)",
        "icon": "✨",
        "keywords": [
            "jrpg", "japanese rpg", "persona", "persona 5", "persona 3 reload", "final fantasy", "ff7 rebirth",
            "ff16", "dragon quest", "metaphor refantazio", "metaphor", "shin megami tensei", "smt", "tales of",
            "xenoblade", "octopath traveler", "trails through daybreak", "like a dragon"
        ],
        "description": "Epic party adventures, emotional narrative journeys, turn-based weakness exploitation, and unforgettable soundtracks.",
        "games": [
            {"title": "Metaphor: ReFantazio", "platforms": ["PC", "PS5", "Xbox"], "year": 2024, "score": 93, "desc": "The Persona team's medieval fantasy masterpiece: Royal Tournament politics, Archetype class evolution, and fast-paced turn battle blend."},
            {"title": "Final Fantasy VII Rebirth", "platforms": ["PS5"], "year": 2024, "score": 92, "desc": "Vast open world beyond Midgar, tactical Synergy abilities, chocobo riding, and legendary musical arrangements."},
            {"title": "Persona 3 Reload / Persona 5 Royal", "platforms": ["PC", "PS5", "Xbox", "Switch"], "year": 2024, "score": 89, "desc": "Stylish social calendar life by day, dungeon crawling and Shadow velvet room fusions by night."},
            {"title": "Like a Dragon: Infinite Wealth", "platforms": ["PC", "PS5", "Xbox"], "year": 2024, "score": 89, "desc": "Ichiban and Kiryu's Hawaiian vacation turn-based crime epic filled with wacky summons and poignant heart."},
            {"title": "Octopath Traveler II", "platforms": ["PC", "PS5", "Xbox", "Switch"], "year": 2023, "score": 85, "desc": "Eight distinct intertwining character tales in jaw-dropping HD-2D with Break and Boost mechanics."}
        ]
    },
    {
        "id": "crpg",
        "title": "Computer RPGs & Choice-Driven Western RPGs (Baldur's Gate Archetype)",
        "icon": "🎲",
        "keywords": [
            "crpg", "baldur's gate", "baldurs gate", "bg3", "divinity original sin", "pillars of eternity",
            "pathfinder wrath of the righteous", "rogue trader", "disco elysium", "wasteland 3", "dragon age",
            "isometric rpg", "tabletop rpg", "dnd", "d&d"
        ],
        "description": "Dice rolls, immense branching choices, companion romances, and environmental reaction combat.",
        "games": [
            {"title": "Baldur's Gate 3", "platforms": ["PC", "PS5", "Xbox"], "year": 2023, "score": 96, "desc": "Unprecedented player freedom, D&D 5e rules, fully voiced cinematic dialogues, and deep turn-based physics."},
            {"title": "Divinity: Original Sin 2", "platforms": ["PC", "PS5", "Xbox", "Switch"], "year": 2017, "score": 93, "desc": "Elemental surface combination magic (oil + fire = inferno) and boundless co-op sandbox freedom."},
            {"title": "Warhammer 40,000: Rogue Trader", "platforms": ["PC", "PS5", "Xbox"], "year": 2023, "score": 81, "desc": "Command a voidship across the Koronus Expanse with grimdark party members and turn-based squad combat."},
            {"title": "Disco Elysium - The Final Cut", "platforms": ["PC", "PS5", "Xbox", "Switch"], "year": 2021, "score": 92, "desc": "Combat-free literary masterpiece where your own brain faculties argue with each other during a murder investigation."},
            {"title": "Pathfinder: Wrath of the Righteous", "platforms": ["PC", "PS5", "Xbox"], "year": 2021, "score": 83, "desc": "Lead a crusade against demonic rifts with mythic progression paths (Angel, Lich, Demon, Trickster)."}
        ]
    },
    {
        "id": "survival_horror",
        "title": "Survival Horror & Psychological Terror (Silent Hill & Resident Evil)",
        "icon": "🔦",
        "keywords": [
            "horror", "survival horror", "silent hill", "silent hill 2", "resident evil", "resident evil 4",
            "dead space", "alan wake", "alan wake 2", "callisto protocol", "outlast", "amnesia", "signalis",
            "the evil within", "fatal frame", "psychological horror", "scary games", "jump scares"
        ],
        "description": "Scarce ammunition, puzzle inventory management, chilling atmosphere, and psychological dread.",
        "games": [
            {"title": "Silent Hill 2 (Remake)", "platforms": ["PC", "PS5"], "year": 2024, "score": 86, "desc": "Over-the-shoulder foggy nightmare reimagined in UE5 with haunting sound design and psychological tragedy."},
            {"title": "Alan Wake 2", "platforms": ["PC", "PS5", "Xbox"], "year": 2023, "score": 89, "desc": "Mind Place detective investigation, live-action shifts, flashlight combat, and reality-bending Pacific Northwest dread."},
            {"title": "Resident Evil 4 (Remake)", "platforms": ["PC", "PS5", "Xbox"], "year": 2023, "score": 93, "desc": "The high watermark of action survival horror: knife parrying, roundhouse kicks, and merchant attache case management."},
            {"title": "Dead Space (Remake)", "platforms": ["PC", "PS5", "Xbox"], "year": 2023, "score": 89, "desc": "Zero-G space station terror, plasma cutter strategic limb dismemberment, and audio atmosphere."},
            {"title": "Signalis", "platforms": ["PC", "PS5", "Xbox", "Switch"], "year": 2022, "score": 82, "desc": "Classic PS1 retro aesthetic survival horror with cosmic mysteries, 6-slot inventory, and melancholic synth soundtrack."}
        ]
    },
    {
        "id": "stealth_immersive_sim",
        "title": "Stealth & Immersive Sims (Hitman, Metal Gear & Dishonored)",
        "icon": "🕶️",
        "keywords": [
            "stealth", "stealth action", "hitman", "hitman world of assassination", "metal gear", "metal gear solid",
            "mgs", "mgs delta", "dishonored", "deus ex", "splinter cell", "prey", "thief", "deathloop",
            "immersive sim", "sniper elite", "shadow", "silent assassin"
        ],
        "description": "Disguises, emergent sandbox clockwork AI, silent takedowns, and multiple non-lethal infiltration paths.",
        "games": [
            {"title": "Hitman World of Assassination", "platforms": ["PC", "PS5", "Xbox", "Switch"], "year": 2023, "score": 87, "desc": "The pinnacle of clockwork murder sandboxes with hundreds of costumes, poison cups, and rogue-lite Freelancer mode."},
            {"title": "Metal Gear Solid Delta: Snake Eater / MGSV", "platforms": ["PC", "PS5", "Xbox"], "year": 2024, "score": 89, "desc": "Jungle camouflage index, survival injury treatment, CQC throws, and tactical espionage operational freedom."},
            {"title": "Dishonored 2", "platforms": ["PC", "PS4", "Xbox"], "year": 2016, "score": 88, "desc": "Blink teleportation, clockwork mansion puzzle layouts, and complete non-lethal ghost playthrough freedom."},
            {"title": "Prey (2017)", "platforms": ["PC", "PS4", "Xbox"], "year": 2017, "score": 84, "desc": "Arkane's sci-fi masterpiece aboard Talos I: turn into a coffee mug, build Gloo Cannon bridges, and hack alien systems."},
            {"title": "Sniper Elite 5", "platforms": ["PC", "PS5", "Xbox"], "year": 2022, "score": 79, "desc": "Long-range ballistics, wind and bullet-drop physics, and signature X-ray kill cam assassinations across WWII maps."}
        ]
    },
    {
        "id": "extraction_milsim",
        "title": "Extraction Shooters & Hardcore Tactical Mil-Sims (Tarkov Archetype)",
        "icon": "🎒",
        "keywords": [
            "extraction shooter", "extraction", "tarkov", "escape from tarkov", "hunt showdown", "hunt showdown 1896",
            "gray zone warfare", "marauders", "arena breakout", "arma", "arma 3", "arma reforger", "squad",
            "insurgency sandstorm", "ready or not", "tactical shooter", "milsim", "hardcore shooter"
        ],
        "description": "Loot loss on death, realistic ballistics, weapon jams, room-clearing breaches, and high-tension extractions.",
        "games": [
            {"title": "Hunt: Showdown 1896", "platforms": ["PC", "PS5", "Xbox"], "year": 2024, "score": 82, "desc": "Binaural sound-driven 1890s bayou bounty hunting: crows, snapping twigs, lever-action rifles, and banishing monsters."},
            {"title": "Ready or Not", "platforms": ["PC"], "year": 2023, "score": 83, "desc": "High-intensity SWAT tactical breaching, civilian preservation, flashbang timing, and unforgiving CQB shootouts."},
            {"title": "Escape from Tarkov", "platforms": ["PC"], "year": 2024, "score": 85, "desc": "The pioneer of hardcore weapon modding, realistic medical limb repair, scav battles, and raid extracts."},
            {"title": "Squad", "platforms": ["PC"], "year": 2020, "score": 80, "desc": "50v50 combined arms military simulation requiring VOIP radio communication, logistics supply lines, and FOB building."},
            {"title": "Insurgency: Sandstorm", "platforms": ["PC", "PS5", "Xbox"], "year": 2021, "score": 80, "desc": "Lethal close-quarters urban combat with zero crosshairs, weapon momentum, and deafening fire support."}
        ]
    },
    {
        "id": "looter_shooter_coop",
        "title": "Looter Shooters & Co-Op PvE Action (Borderlands, Destiny & Helldivers)",
        "icon": "🚀",
        "keywords": [
            "looter shooter", "loot shooter", "destiny", "destiny 2", "borderlands", "borderlands 3", "warframe",
            "the first descendant", "helldivers", "helldivers 2", "deep rock galactic", "drg", "remnant",
            "pve shooter", "coop shooter", "co-op shooter"
        ],
        "description": "Co-op raids, elemental gun drops, orbital stratagems, horde defense, and exponential gear builds.",
        "games": [
            {"title": "Helldivers 2", "platforms": ["PC", "PS5"], "year": 2024, "score": 85, "desc": "Hilarious patriotic democracy spread: 500kg bomb stratagems, friendly fire chaos, and relentless bug & bot swarms."},
            {"title": "Destiny 2: The Final Shape", "platforms": ["PC", "PS5", "Xbox"], "year": 2024, "score": 90, "desc": "Prismatic subclass fusion, master-tier 6-player raids, and peerless first-person gun feel."},
            {"title": "Deep Rock Galactic", "platforms": ["PC", "PS5", "Xbox"], "year": 2020, "score": 86, "desc": "Four dwarf miner classes, 100% destructible alien caverns, swarm defense, and Rock and Stone camaraderie."},
            {"title": "Warframe", "platforms": ["PC", "PS5", "Xbox", "Switch"], "year": 2024, "score": 86, "desc": "Lightning-fast parkour space ninjas with 50+ unique bio-metal warframes and free-to-play depth."},
            {"title": "Borderlands 3 / Tiny Tina's Wonderlands", "platforms": ["PC", "PS5", "Xbox"], "year": 2022, "score": 80, "desc": "Over one billion procedurally rolled guns, comedic action skills, and colorful co-op mayhem."}
        ]
    },
    {
        "id": "roguelike_deckbuilder",
        "title": "Action Roguelites & Card Deckbuilders (Hades & Balatro Archetype)",
        "icon": "🃏",
        "keywords": [
            "roguelike", "roguelite", "rogue-like", "rogue-lite", "hades", "hades 2", "balatro", "slay the spire",
            "dead cells", "binding of isaac", "enter the gungeon", "vampire survivors", "risk of rain", "risk of rain 2",
            "monster train", "deckbuilder", "card roguelike", "bullet heaven"
        ],
        "description": "Procedural runs, permanent meta-progression, crazy card and boon synergies, and 'just one more run' addiction.",
        "games": [
            {"title": "Hades II", "platforms": ["PC"], "year": 2024, "score": 94, "desc": "Melinoë's witchcraft dash combat, Olympian god boons, incredible voice acting, and layered roguelite depth."},
            {"title": "Balatro", "platforms": ["PC", "PS5", "Xbox", "Switch", "Mobile"], "year": 2024, "score": 91, "desc": "Hypnotic poker roguelike: combine illegal hands with game-breaking Joker mult-cards and planet upgrades."},
            {"title": "Slay the Spire", "platforms": ["PC", "PS5", "Xbox", "Switch", "Mobile"], "year": 2019, "score": 89, "desc": "The gold standard of deckbuilders: Ironclad, Silent, Defect, and Watcher climbing the Spire with tight relics."},
            {"title": "Dead Cells", "platforms": ["PC", "PS5", "Xbox", "Switch", "Mobile"], "year": 2018, "score": 89, "desc": "Lightning 2D roguevania combat with roll dodges, traps, and Castlevania crossover expansions."},
            {"title": "Vampire Survivors", "platforms": ["PC", "PS5", "Xbox", "Switch", "Mobile"], "year": 2022, "score": 87, "desc": "The definitive auto-shooting bullet-heaven sensation with thousands of monsters and treasure chests."}
        ]
    },
    {
        "id": "open_world_rpg",
        "title": "Open-World Narrative Epics (Witcher, Cyberpunk & GTA Archetype)",
        "icon": "🌄",
        "keywords": [
            "open world", "open-world", "witcher", "witcher 3", "cyberpunk", "cyberpunk 2077", "red dead",
            "red dead redemption", "rdr2", "gta", "grand theft auto", "ghost of tsushima", "horizon forbidden west",
            "zelda", "breath of the wild", "tears of the kingdom", "starfield", "assassins creed", "ac valhalla"
        ],
        "description": "Breathtaking living worlds, branching moral dilemmas, horse & vehicle travel, and cinematic storylines.",
        "games": [
            {"title": "Cyberpunk 2077: Phantom Liberty", "platforms": ["PC", "PS5", "Xbox"], "year": 2023, "score": 89, "desc": "Dogtown spy thriller starring Idris Elba, revamped perk tree cyberware, vehicle combat, and dazzling ray tracing."},
            {"title": "The Witcher 3: Wild Hunt (Complete)", "platforms": ["PC", "PS5", "Xbox", "Switch"], "year": 2022, "score": 94, "desc": "Geralt's quest across Novigrad and Skellige: morally grey quests, monster contracts, and Gwent card matches."},
            {"title": "Red Dead Redemption 2", "platforms": ["PC", "PS4", "Xbox"], "year": 2018, "score": 97, "desc": "Arthur Morgan's outlaw odyssey featuring unmatched environmental physics, campfire tales, and hunting realism."},
            {"title": "Ghost of Tsushima: Director's Cut", "platforms": ["PC", "PS5", "PS4"], "year": 2021, "score": 87, "desc": "Wind-guided navigation across feudal Japan, duel standoffs, katana stances, and legendary samurai honour vs. ghost stealth."},
            {"title": "The Legend of Zelda: Tears of the Kingdom", "platforms": ["Switch"], "year": 2023, "score": 96, "desc": "Ultrahand physics engineering: craft flying machines, fuse weapons, and explore Sky Islands and Depths."}
        ]
    },
    {
        "id": "cozy_farming_sim",
        "title": "Cozy Games, Farming & Social Life Sims (Stardew & Animal Crossing)",
        "icon": "🌾",
        "keywords": [
            "cozy", "cozy game", "farming sim", "life sim", "stardew valley", "stardew", "animal crossing",
            "animal crossing new horizons", "sims", "the sims", "the sims 4", "coral island", "slime rancher",
            "dave the diver", "harvest moon", "story of seasons", "rune factory", "relaxing games", "chill games"
        ],
        "description": "Relaxing crop harvest cycles, village festivals, home decoration, and peaceful wholesome escapism.",
        "games": [
            {"title": "Stardew Valley (Update 1.6)", "platforms": ["PC", "PS5", "Xbox", "Switch", "Mobile"], "year": 2024, "score": 91, "desc": "The gold standard: seasonal festivals, pet upgrades, greenhouse crops, mine delving, and Pelican Town romances."},
            {"title": "Animal Crossing: New Horizons", "platforms": ["Switch"], "year": 2020, "score": 90, "desc": "Real-time deserted island paradise building, turnip stalk market, museum fossils, and villager friendships."},
            {"title": "Dave the Diver", "platforms": ["PC", "PS5", "Switch"], "year": 2023, "score": 90, "desc": "Spearfishing the mysterious Blue Hole by day, running a bustling gourmet sushi restaurant by night."},
            {"title": "Coral Island", "platforms": ["PC", "PS5", "Xbox"], "year": 2023, "score": 82, "desc": "Tropical island farm revival with underwater reef diving, mermaid kingdoms, and rich diverse villagers."},
            {"title": "Slime Rancher 2", "platforms": ["PC", "PS5", "Xbox"], "year": 2024, "score": 84, "desc": "Explore Rainbow Island, vacuum up bouncy adorable slimes, and build a colorful thriving conservatory."}
        ]
    },
    {
        "id": "colony_management_factory",
        "title": "Colony Sims, Automation & City Builders (Factorio & RimWorld)",
        "icon": "🏭",
        "keywords": [
            "colony sim", "colony management", "city builder", "city building", "management sim", "automation",
            "factory", "factorio", "rimworld", "satisfactory", "cities skylines", "frostpunk", "frostpunk 2",
            "manor lords", "timberborn", "oxygen not included", "builder"
        ],
        "description": "Conveyor belt logistics, survivor survival psychologies, town zoning, and resource efficiency loops.",
        "games": [
            {"title": "Satisfactory (1.0)", "platforms": ["PC"], "year": 2024, "score": 90, "desc": "First-person alien world automation: construct gigantic multi-tier factories, hyper-tubes, and freight trains."},
            {"title": "Frostpunk 2", "platforms": ["PC", "PS5", "Xbox"], "year": 2024, "score": 86, "desc": "Brutal frozen post-apocalyptic society survival: district zoning, political faction negotiations, and city oil greed."},
            {"title": "Manor Lords", "platforms": ["PC"], "year": 2024, "score": 88, "desc": "Photorealistic medieval village builder featuring organic ungridded road growth and Total War style militia defense."},
            {"title": "Factorio: Space Age", "platforms": ["PC", "Switch"], "year": 2024, "score": 95, "desc": "The ultimate automation obsession: planetary space platforms, vulcanus smelting, and endless logistical conveyor belts."},
            {"title": "RimWorld", "platforms": ["PC", "PS4", "Xbox"], "year": 2021, "score": 87, "desc": "AI storyteller-driven colony survival: mental breakdowns, bionic limb implants, and hilarious emergent tragedies."}
        ]
    },
    {
        "id": "grand_strategy_rts",
        "title": "4X Grand Strategy & Real-Time Strategy (Civilization & Age of Empires)",
        "icon": "👑",
        "keywords": [
            "4x", "grand strategy", "rts", "real time strategy", "civilization", "civ", "civ 6", "civ 7",
            "stellaris", "crusader kings", "crusader kings 3", "hearts of iron", "europa universalis",
            "age of empires", "total war", "total war warhammer", "starcraft", "command and conquer"
        ],
        "description": "Explore, Expand, Exploit, Exterminate: diplomatic treaties, dynastic marriages, tech trees, and massive armies.",
        "games": [
            {"title": "Crusader Kings III: Roads to Power", "platforms": ["PC", "PS5", "Xbox"], "year": 2024, "score": 91, "desc": "Play as landless adventurers or Byzantine emperors, plot dynastic assassinations, and rule medieval history."},
            {"title": "Sid Meier's Civilization VI / VII", "platforms": ["PC", "PS5", "Xbox", "Switch"], "year": 2024, "score": 88, "desc": "Unstacked city districts, historical wonder building, tactical army formations, and 'One More Turn' magic."},
            {"title": "Age of Empires IV", "platforms": ["PC", "Xbox"], "year": 2021, "score": 81, "desc": "Asymmetrical medieval civilizations (English longbows, Mongol nomad relocations) with crisp historical documentary flair."},
            {"title": "Stellaris", "platforms": ["PC", "PS4", "Xbox"], "year": 2024, "score": 83, "desc": "Galaxy-spanning 4X empire customization: robot uprisings, Dyson spheres, and interstellar diplomacy."},
            {"title": "Total War: Warhammer III", "platforms": ["PC"], "year": 2022, "score": 85, "desc": "Immense Immortal Empires campaign combining turn-based empire map strategy with 10,000-unit fantasy battles."}
        ]
    },
    {
        "id": "survival_crafting_sandbox",
        "title": "Survival Crafting & Open Sandbox (Minecraft & Valheim Archetype)",
        "icon": "🏕️",
        "keywords": [
            "survival crafting", "survival", "crafting", "sandbox", "base building", "minecraft", "valheim",
            "terraria", "rust", "ark survival", "ark survival ascended", "subnautica", "sons of the forest",
            "the forest", "palworld", "enshrouded", "7 days to die", "raft"
        ],
        "description": "Tree punching, tool crafting, base fortification, hunger meters, and dangerous wilderness biomes.",
        "games": [
            {"title": "Palworld", "platforms": ["PC", "PS5", "Xbox"], "year": 2024, "score": 82, "desc": "Capture quirky elemental Pals to automate your factory bases, craft firearms, and explore a massive archipelago."},
            {"title": "Enshrouded", "platforms": ["PC"], "year": 2024, "score": 83, "desc": "Voxel-based building freedom in an atmospheric realm smothered by deadly fungal fog with Souls-lite combat."},
            {"title": "Valheim", "platforms": ["PC", "Xbox"], "year": 2023, "score": 89, "desc": "Viking purgatory survival: longship sailing across stormy seas, mead brewing, and physics-based wooden longhouses."},
            {"title": "Subnautica", "platforms": ["PC", "PS5", "Xbox", "Switch"], "year": 2018, "score": 87, "desc": "Submerged alien ocean survival: pilot the Cyclops submarine into dark bioluminescent depths with Reaper leviathans."},
            {"title": "Minecraft", "platforms": ["PC", "PS5", "Xbox", "Switch", "Mobile"], "year": 2024, "score": 93, "desc": "The infinite block sandbox of creativity, Nether portals, Redstone computer logic, and limitless survival exploration."}
        ]
    },
    {
        "id": "racing_motorsport",
        "title": "Racing, Drifting & Motorsports (Forza & Gran Turismo Archetype)",
        "icon": "🏎️",
        "keywords": [
            "racing", "racing game", "driving", "cars", "forza", "forza horizon", "forza motorsport",
            "gran turismo", "gt7", "need for speed", "nfs", "f1", "f1 24", "assetto corsa", "dirt rally",
            "ea sports wrc", "mario kart", "kart racer", "drift", "car racing"
        ],
        "description": "Apex cornering, force-feedback steering wheels, open-road festival cruises, and hypercar tuning.",
        "games": [
            {"title": "Forza Horizon 5", "platforms": ["PC", "Xbox"], "year": 2021, "score": 92, "desc": "Breathtaking open-world Mexico festival with hundreds of licensed cars, jungle trails, and volcano sprints."},
            {"title": "Gran Turismo 7", "platforms": ["PS5", "PS4"], "year": 2022, "score": 87, "desc": "The real driving simulator: PS VR2 full cockpit immersion, automotive history cafe, and hyper-accurate tire physics."},
            {"title": "Mario Kart 8 Deluxe (Booster Course)", "platforms": ["Switch"], "year": 2023, "score": 92, "desc": "96 legendary courses, anti-gravity drift boosting, blue shells, and timeless couch multiplayer perfection."},
            {"title": "Assetto Corsa Competizione", "platforms": ["PC", "PS5", "Xbox"], "year": 2022, "score": 82, "desc": "The hardcore GT3 esports benchmark with laser-scanned tracks and realistic tire degradation."},
            {"title": "EA Sports WRC", "platforms": ["PC", "PS5", "Xbox"], "year": 2023, "score": 80, "desc": "Codemasters' rally sim: treacherous gravel hairpins, co-driver pacenotes, and pulse-pounding stage times."}
        ]
    },
    {
        "id": "sports_athletics",
        "title": "Sports & Competitive Athletics (EA Sports FC & NBA 2K Archetype)",
        "icon": "⚽",
        "keywords": [
            "sports", "football", "soccer", "basketball", "baseball", "hockey", "fifa", "ea sports fc",
            "fc 24", "fc 25", "nba 2k", "nba 2k25", "madden", "mlb the show", "nhl", "wwe 2k",
            "college football", "college football 25", "rocket league", "topspin"
        ],
        "description": "Franchise management, authentic player ball physics, playbook strategy, and stadium atmosphere.",
        "games": [
            {"title": "EA Sports College Football 25", "platforms": ["PS5", "Xbox"], "year": 2024, "score": 84, "desc": "Electrifying return of campus rivalries, marching bands, Dynasty recruiting, and fast-paced option offense."},
            {"title": "EA Sports FC 25", "platforms": ["PC", "PS5", "Xbox", "Switch"], "year": 2024, "score": 77, "desc": "FC IQ tactical overhaul, 5v5 Rush small-sided mode, and world football licenses across Champions League."},
            {"title": "NBA 2K25", "platforms": ["PC", "PS5", "Xbox", "Switch"], "year": 2024, "score": 80, "desc": "ProPLAY animation fidelity mimicking real NBA superstars, MyCAREER street courts, and Era franchise modes."},
            {"title": "MLB The Show 24", "platforms": ["PS5", "Xbox", "Switch"], "year": 2024, "score": 80, "desc": "Diamond Dynasty card collection, pinpoint pitching control, and historic Negro Leagues Storylines."},
            {"title": "Rocket League", "platforms": ["PC", "PS5", "Xbox", "Switch"], "year": 2020, "score": 86, "desc": "Acrobatic rocket-powered cars playing physics soccer with aerial boost saves and zero RNG."}
        ]
    },
    {
        "id": "fighting_brawler",
        "title": "Fighting Games & Martial Arts Brawlers (Street Fighter & Tekken)",
        "icon": "🥋",
        "keywords": [
            "fighting", "fighting game", "fighters", "street fighter", "sf6", "tekken", "tekken 8", "mortal kombat",
            "mk1", "guilty gear", "guilty gear strive", "smash bros", "smash ultimate", "dragon ball",
            "sparking zero", "brawler", "beat em up", "sifu", "streets of rage"
        ],
        "description": "Frame data precision, combo cancels, footsies spacing, defensive parries, and hype tournament battles.",
        "games": [
            {"title": "Tekken 8", "platforms": ["PC", "PS5", "Xbox"], "year": 2024, "score": 90, "desc": "Aggressive Heat System mechanics, cinematic destructible stages, and accessible Arcade Quest mode."},
            {"title": "Street Fighter 6", "platforms": ["PC", "PS5", "Xbox"], "year": 2023, "score": 92, "desc": "Drive Gauge system balance, modern controller inputs, rollback netcode, and open-world World Tour mode."},
            {"title": "Dragon Ball: Sparking! ZERO", "platforms": ["PC", "PS5", "Xbox"], "year": 2024, "score": 82, "desc": "The return of Budokai Tenkaichi 3D arena brawling with 180+ anime fighters and beam clashes."},
            {"title": "Sifu", "platforms": ["PC", "PS5", "Xbox", "Switch"], "year": 2022, "score": 81, "desc": "Pak Mei Kung Fu aging mechanic: master directional parries, sweeps, and nightclub brawl choreography."},
            {"title": "Super Smash Bros. Ultimate", "platforms": ["Switch"], "year": 2018, "score": 93, "desc": "89 iconic video game fighters, platform edge-guarding, and the ultimate tribute to gaming history."}
        ]
    },
    {
        "id": "platformer",
        "title": "2D & 3D Platformers (Mario & Astro Bot Archetype)",
        "icon": "🍄",
        "keywords": [
            "platformer", "3d platformer", "2d platformer", "jump and run", "astro bot", "mario", "mario odyssey",
            "mario wonder", "celeste", "rayman", "crash bandicoot", "spyro", "psychonauts", "sonic",
            "prince of persia", "lost crown", "ori", "ori and the will of the wisps"
        ],
        "description": "Precision jumping, secret collectibles, inventive gadget traversal, and pure unadulterated joy.",
        "games": [
            {"title": "Astro Bot", "platforms": ["PS5"], "year": 2024, "score": 94, "desc": "PlayStation's masterpiece of haptic DualSense magic, 80 creative levels, and joyous VIP bot cameos."},
            {"title": "Super Mario Bros. Wonder", "platforms": ["Switch"], "year": 2023, "score": 92, "desc": "Wonder Flowers transforming levels into singing piranha plants, elephant power-ups, and badges."},
            {"title": "Prince of Persia: The Lost Crown", "platforms": ["PC", "PS5", "Xbox", "Switch"], "year": 2024, "score": 86, "desc": "Phenomenal 60FPS acrobatic parrying, time-shift powers, and map screenshot memory markers."},
            {"title": "Celeste", "platforms": ["PC", "PS5", "Xbox", "Switch"], "year": 2018, "score": 91, "desc": "Tight 8-directional air dash platforming combined with a touching personal story about anxiety."},
            {"title": "Ori and the Will of the Wisps", "platforms": ["PC", "Xbox", "Switch"], "year": 2020, "score": 90, "desc": "Gorgeous painterly visuals, orchestral score, spirit weapon combat, and kinetic chase sequences."}
        ]
    },
    {
        "id": "character_action",
        "title": "Character Action & Stylish Spectacle Fighters (Devil May Cry & Bayonetta)",
        "icon": "⚡",
        "keywords": [
            "character action", "spectacle fighter", "stylish action", "hack and slash", "devil may cry", "dmc",
            "dmc5", "bayonetta", "god of war", "ninja gaiden", "metal gear rising", "astral chain", "stellar blade",
            "stylish rank", "air juggling"
        ],
        "description": "Weapon switching mid-combo, SSS style ratings, aerial juggle loops, and over-the-top boss climaxes.",
        "games": [
            {"title": "Stellar Blade", "platforms": ["PS5"], "year": 2024, "score": 82, "desc": "Eve's dazzling sci-fi sword choreography: perfect parries, dodge counters, and breathtaking Naytiba bosses."},
            {"title": "Devil May Cry 5: Special Edition", "platforms": ["PC", "PS5", "Xbox"], "year": 2020, "score": 89, "desc": "Triple character combat depth (Dante, Nero, V/Vergil) with royal guard parries and smokin' sexy style."},
            {"title": "God of War Ragnarök", "platforms": ["PC", "PS5", "PS4"], "year": 2022, "score": 94, "desc": "Kratos' Leviathan Axe recall physics, Blades of Chaos whip grappling, and Norse mythical grandeur."},
            {"title": "Bayonetta 3", "platforms": ["Switch"], "year": 2022, "score": 86, "desc": "Witch Time slow motion dodges and Kaiju-sized Demon Slave summons across multiversal timelines."},
            {"title": "Hi-Fi Rush", "platforms": ["PC", "PS5", "Xbox"], "year": 2023, "score": 89, "desc": "Action rhythm hybrid where attacks, parries, and stage environments sync perfectly to rock beats."}
        ]
    },
    {
        "id": "puzzle_detective_narrative",
        "title": "Puzzle, Mystery & Detective Adventures (Portal, Outer Wilds & Obra Dinn)",
        "icon": "🔍",
        "keywords": [
            "puzzle", "detective", "mystery", "narrative", "story rich", "walking simulator", "portal", "portal 2",
            "the witness", "return of the obra dinn", "outer wilds", "talos principle", "talos principle 2",
            "ace attorney", "phoenix wright", "lorelei and the laser eyes", "blue prince", "case of the golden idol"
        ],
        "description": "Deduction mechanics, perspective puzzles, time loop investigations, and brilliant eureka moments.",
        "games": [
            {"title": "Lorelei and the Laser Eyes", "platforms": ["PC", "PS5", "Switch"], "year": 2024, "score": 88, "desc": "Simogo's monochromatic hotel mystery woven with cryptographic riddles, optical illusions, and surreal cinema."},
            {"title": "The Talos Principle 2", "platforms": ["PC", "PS5", "Xbox"], "year": 2023, "score": 88, "desc": "Deep philosophical questions on humanity wrapped around elegant laser redirection and gravity beam puzzles."},
            {"title": "Outer Wilds", "platforms": ["PC", "PS5", "Xbox", "Switch"], "year": 2019, "score": 85, "desc": "The greatest mystery in gaming: 22-minute solar system time loop fueled strictly by player curiosity."},
            {"title": "Return of the Obra Dinn", "platforms": ["PC", "PS4", "Xbox", "Switch"], "year": 2018, "score": 89, "desc": "Use a magical pocket watch to observe frozen death moments and deduce the fates of 60 ship crew members."},
            {"title": "The Rise of the Golden Idol", "platforms": ["PC", "PS5", "Xbox", "Switch", "Mobile"], "year": 2024, "score": 87, "desc": "Fill-in-the-blank deduction mechanics piecing together bizarre 1970s crimes and occult conspiracies."}
        ]
    },
    {
        "id": "mmo_shared_world",
        "title": "MMORPGs & Persistent Online Worlds (World of Warcraft & FFXIV)",
        "icon": "🌐",
        "keywords": [
            "mmo", "mmorpg", "massive multiplayer", "world of warcraft", "wow", "final fantasy xiv", "ff14",
            "ffxiv", "elder scrolls online", "eso", "guild wars 2", "lost ark", "runescape", "osrs",
            "throne and liberty", "black desert", "mmo raid"
        ],
        "description": "Persistent fantasy realms, guild coordination, raid tier progression, player economies, and endless quests.",
        "games": [
            {"title": "World of Warcraft: The War Within", "platforms": ["PC"], "year": 2024, "score": 84, "desc": "Underground Khaz Algar continent, bite-sized Delves solo/duo progression, and Warbands account sharing."},
            {"title": "Final Fantasy XIV: Dawntrail", "platforms": ["PC", "PS5", "Xbox"], "year": 2024, "score": 82, "desc": "Vibrant Tural expansion, Viper and Pictomancer jobs, graphical overhaul, and cinematic raid bosses."},
            {"title": "Guild Wars 2: Janthir Wilds", "platforms": ["PC"], "year": 2024, "score": 83, "desc": "Player homestead housing, spear weapons on land, mount physics, and zero gear-treadmill casual respect."},
            {"title": "The Elder Scrolls Online: Gold Road", "platforms": ["PC", "PS5", "Xbox"], "year": 2024, "score": 79, "desc": "Custom skill Scribing system, West Weald exploration, and Tamriel lore fully voiced in any order."},
            {"title": "Old School RuneScape", "platforms": ["PC", "Mobile"], "year": 2024, "score": 90, "desc": "Varlanmore expansion, classic point-and-click grinding, player-polled updates, and rich sandbox economy."}
        ]
    },
    {
        "id": "rhythm_music",
        "title": "Rhythm, Music & Synchronization (Hi-Fi Rush & Beat Saber)",
        "icon": "🎵",
        "keywords": [
            "rhythm", "music game", "rhythm game", "beat saber", "hi-fi rush", "guitar hero", "clone hero",
            "synth riders", "rhythm doctor", "crypt of the necrodancer", "taiko no tatsujin", "metal hellsinger"
        ],
        "description": "Audio cue reflexes, musical timing beat hits, note highways, and infectious soundtracks.",
        "games": [
            {"title": "Hi-Fi Rush", "platforms": ["PC", "PS5", "Xbox"], "year": 2023, "score": 89, "desc": "Pure Saturday-morning cartoon joy syncing attacks, combos, and parries to licensed rock beats."},
            {"title": "Beat Saber", "platforms": ["PC", "PS5"], "year": 2019, "score": 86, "desc": "Dual laser sabers slicing colored blocks in VR to heart-pumping electronic and rock music."},
            {"title": "Metal: Hellsinger", "platforms": ["PC", "PS5", "Xbox"], "year": 2022, "score": 79, "desc": "Shoot demons on the beat of original heavy metal tracks featuring Serj Tankian and Alissa White-Gluz."},
            {"title": "Crypt of the NecroDancer: Synchrony", "platforms": ["PC", "Switch", "PS4"], "year": 2024, "score": 87, "desc": "Rogue-like dungeon crawler where every tile hop and attack must land on the Danny Baranowsky beat."},
            {"title": "Rhythm Doctor", "platforms": ["PC"], "year": 2021, "score": 88, "desc": "Defibrillate patient hearts by hitting the spacebar exactly on the 7th beat amidst visual glitch hijinks."}
        ]
    },
    {
        "id": "vehicle_space_simulation",
        "title": "Vehicle, Flight & Space Simulators (Flight Sim & No Man's Sky)",
        "icon": "🛸",
        "keywords": [
            "flight simulator", "flight sim", "space sim", "space flight", "msfs", "microsoft flight simulator",
            "elite dangerous", "star citizen", "no man's sky", "kerbal space program", "euro truck simulator",
            "farming simulator", "simulator", "sim"
        ],
        "description": "Cockpit instruments, realistic avionics, planetary atmospheric entries, and relaxing cargo hauls.",
        "games": [
            {"title": "Microsoft Flight Simulator 2024", "platforms": ["PC", "Xbox"], "year": 2024, "score": 90, "desc": "Full Earth digital twin with commercial aviation careers, search & rescue, hot air balloons, and live weather."},
            {"title": "No Man's Sky (Worlds Part 1)", "platforms": ["PC", "PS5", "Xbox", "Switch"], "year": 2024, "score": 84, "desc": "18 quintillion procedural planets, seamless planetary landings, base building, and deep space exploration."},
            {"title": "Elite Dangerous: Odyssey", "platforms": ["PC"], "year": 2021, "score": 80, "desc": "1:1 Milky Way galaxy replica: bounty hunt in asteroid rings, trade commodities, and land on alien worlds."},
            {"title": "Euro Truck Simulator 2", "platforms": ["PC"], "year": 2024, "score": 85, "desc": "The ultimate zen driving experience hauling freight across scenic European highways with radio streaming."},
            {"title": "Kerbal Space Program", "platforms": ["PC", "PS4", "Xbox"], "year": 2015, "score": 88, "desc": "Build realistic multi-stage rockets using actual orbital mechanics and aerodynamics physics."}
        ]
    },
    {
        "id": "party_couch_coop",
        "title": "Party Games & Couch Co-Op (It Takes Two & Overcooked Archetype)",
        "icon": "🎉",
        "keywords": [
            "co-op", "coop", "local coop", "couch coop", "party game", "2 player", "two player", "it takes two",
            "overcooked", "a way out", "lethal company", "among us", "party animals", "human fall flat", "gang beasts"
        ],
        "description": "Split-screen laughter, kitchen fire coordination, proximity-voice panic, and teamwork bond tests.",
        "games": [
            {"title": "It Takes Two", "platforms": ["PC", "PS5", "Xbox", "Switch"], "year": 2021, "score": 89, "desc": "The undisputed Game of the Year co-op masterpiece where every single chapter invents brand new shared mechanics."},
            {"title": "Overcooked! All You Can Eat", "platforms": ["PC", "PS5", "Xbox", "Switch"], "year": 2020, "score": 84, "desc": "Frenetic kitchen management with shifting floors, balloon fires, dishwashing bottlenecks, and yelling."},
            {"title": "Lethal Company", "platforms": ["PC"], "year": 2023, "score": 88, "desc": "Hilarious proximity-chat horror: scavenge abandoned industrial moons to hit Profit Quotas while dodging monsters."},
            {"title": "Party Animals", "platforms": ["PC", "Xbox"], "year": 2023, "score": 78, "desc": "Fluffy physics brawler where puppies and kittens drop-kick each other off flying submarine wings."},
            {"title": "A Way Out", "platforms": ["PC", "PS5", "Xbox"], "year": 2018, "score": 79, "desc": "Mandatory 2-player prison breakout with cinematic split-screen perspectives and emotional twists."}
        ]
    },
    {
        "id": "hero_competitive_shooter",
        "title": "Hero Shooters & Competitive Tactical FPS (Valorant, CS2 & Overwatch)",
        "icon": "🏆",
        "keywords": [
            "hero shooter", "competitive shooter", "tactical fps", "valorant", "counter strike", "cs2", "csgo",
            "rainbow six siege", "siege", "marvel rivals", "overwatch", "overwatch 2", "bomb defusal", "esports fps"
        ],
        "description": "5v5 team coordination, utility lineups, crosshair headshot placement, and ultimate ability combos.",
        "games": [
            {"title": "Counter-Strike 2", "platforms": ["PC"], "year": 2023, "score": 82, "desc": "Sub-tick hit registration, volumetric responsive smoke grenades, and pure tactical bomb defusal mastery."},
            {"title": "Valorant", "platforms": ["PC", "PS5", "Xbox"], "year": 2024, "score": 83, "desc": "Riot's tactical shooter blending precise gunplay recoil with agent smoke, dash, and wall abilities."},
            {"title": "Marvel Rivals", "platforms": ["PC", "PS5", "Xbox"], "year": 2024, "score": 83, "desc": "6v6 superhero team shooter with dynamic Team-Up abilities (Rocket on Groot's back) and destructible maps."},
            {"title": "Rainbow Six Siege", "platforms": ["PC", "PS5", "Xbox"], "year": 2024, "score": 81, "desc": "Destructible drywall surfaces, drone reconnaissance, reinforcing walls, and lethal one-shot headshot angles."},
            {"title": "Overwatch 2", "platforms": ["PC", "PS5", "Xbox", "Switch"], "year": 2024, "score": 79, "desc": "Fast hero combat with tanks, damage dealers, and healers pushing payloads in vibrant global cities."}
        ]
    },
    {
        "id": "card_battler_tcg",
        "title": "Card Battlers & Digital TCGs (Magic, Yu-Gi-Oh & Marvel Snap)",
        "icon": "🎴",
        "keywords": [
            "card game", "card battler", "tcg", "ccg", "autobattler", "auto chess", "tft", "teamfight tactics",
            "hearthstone", "magic the gathering", "mtg", "mtg arena", "yugioh", "master duel", "marvel snap", "inscryption"
        ],
        "description": "Deck optimization, mana curve mathematics, bluffing snaps, and strategic turn order sequencing.",
        "games": [
            {"title": "Balatro", "platforms": ["PC", "PS5", "Xbox", "Switch", "Mobile"], "year": 2024, "score": 91, "desc": "The addictive poker card roguelike phenomenon blending spectral packs, tarot cards, and multi-triggers."},
            {"title": "Inscryption", "platforms": ["PC", "PS5", "Xbox", "Switch"], "year": 2021, "score": 87, "desc": "Atmospheric cabin horror deckbuilder that continually morphs and breaks its own boundaries."},
            {"title": "Marvel Snap", "platforms": ["PC", "Mobile"], "year": 2022, "score": 85, "desc": "Bite-sized 3-minute card duels across 3 randomized locations with bluffing 'Snap' poker stakes."},
            {"title": "Teamfight Tactics (TFT)", "platforms": ["PC", "Mobile"], "year": 2024, "score": 85, "desc": "Riot's premier 8-player autobattler with economy interest management, trait synergies, and item slams."},
            {"title": "Magic: The Gathering Arena", "platforms": ["PC", "Mobile"], "year": 2024, "score": 82, "desc": "The definitive grandfather of TCGs in digital form with standard, commander brawl, and draft events."}
        ]
    },
    {
        "id": "visual_novel_interactive_story",
        "title": "Visual Novels & Interactive Narrative Dramas (Life is Strange & Detroit)",
        "icon": "📖",
        "keywords": [
            "visual novel", "interactive movie", "interactive drama", "vn", "choose your own adventure",
            "steins gate", "danganronpa", "doki doki", "doki doki literature club", "life is strange",
            "detroit become human", "until dawn", "the quarry", "oxenfree", "narrative choice"
        ],
        "description": "Divergent flowchart branches, butterfly effect consequences, moral dilemmas, and unforgettable character arcs.",
        "games": [
            {"title": "Detroit: Become Human", "platforms": ["PC", "PS5", "PS4"], "year": 2018, "score": 80, "desc": "Massive branching narrative flowchart following three androids awakening to consciousness with real permanent deaths."},
            {"title": "Until Dawn (Remake)", "platforms": ["PC", "PS5"], "year": 2024, "score": 76, "desc": "Teen slasher movie survival where your quick-time decisions and clues determine who survives until morning."},
            {"title": "Life is Strange: Double Exposure", "platforms": ["PC", "PS5", "Xbox", "Switch"], "year": 2024, "score": 75, "desc": "Max Caulfield shifts between two parallel timelines to investigate and prevent a friend's murder."},
            {"title": "Steins;Gate", "platforms": ["PC", "PS4", "Switch"], "year": 2015, "score": 87, "desc": "The undisputed pinnacle of time-travel fiction: sending microwave text messages to the past with dire butterfly effects."},
            {"title": "Doki Doki Literature Club Plus!", "platforms": ["PC", "PS5", "Xbox", "Switch"], "year": 2021, "score": 85, "desc": "A deceptively cute high school poetry club that deconstructs the medium with Fourth-wall breaking psychological terror."}
        ]
    }
]


# ---------------------------------------------------------------------------
# Pulsar Session Memory & Grounded Gaming Intelligence
# ---------------------------------------------------------------------------

SESSION_LOCK = threading.RLock()
PULSAR_SESSIONS = {}
PULSAR_SESSION_TTL = 60 * 60 * 8
METACRITIC_CACHE = {}
METACRITIC_CACHE_LOCK = threading.RLock()
METACRITIC_CACHE_TTL = 60 * 10
METACRITIC_NEGATIVE_CACHE_TTL = 15
METACRITIC_DETAIL_CACHE_TTL = 60 * 60
METACRITIC_API_BASE = os.environ.get("METACRITIC_API_BASE", "https://backend.metacritic.com").rstrip("/")
METACRITIC_API_KEY = os.environ.get("METACRITIC_API_KEY", "").strip()
DEFAULT_METACRITIC_KEY = "1MOZgmNFxvmljaQR1X9KAij9Mo4xAY3u"
METACRITIC_DISCOVERED_KEY = DEFAULT_METACRITIC_KEY
METACRITIC_DISCOVERY_LOCK = threading.RLock()
METACRITIC_DNS_CACHE = {}
METACRITIC_DNS_LOCK = threading.RLock()
METACRITIC_DNS_TTL = 300

PLATFORM_ALIASES = {
    "pc": ["pc", "steam", "windows"],
    "ps5": ["ps5", "playstation 5", "playstation 5"],
    "ps4": ["ps4", "playstation 4"],
    "xbox": ["xbox", "xbox series", "series x", "series s", "xbox one"],
    "switch": ["switch", "nintendo switch", "switch 2"],
    "steam deck": ["steam deck"],
}

METACRITIC_PLATFORM_SLUGS = {
    "pc": "pc",
    "ps5": "playstation",
    "ps4": "ps4",
    "xbox": "xboxone",
    "switch": "switch",
    "dreamcast": "dreamcast",
    "n64": "n64",
    "gamecube": "gamecube",
    "wii": "wii",
}

GENRE_ALIASES = {
    "rpg": ["rpg", "role playing", "role-playing"],
    "jrpg": ["jrpg", "japanese rpg"],
    "crpg": ["crpg", "computer rpg"],
    "action rpg": ["action rpg", "action-rpg"],
    "soulslike": ["soulslike", "souls-like", "souls like"],
    "fps": ["fps", "first person shooter", "first-person shooter"],
    "horror": ["horror", "survival horror", "psychological horror"],
    "platformer": ["platformer", "platformers", "platforming"],
    "strategy": ["strategy", "4x", "turn based strategy", "rts"],
    "roguelike": ["roguelike", "roguelite", "rogue-like", "rogue-lite"],
    "deckbuilder": ["deckbuilder", "deck builder", "card battler"],
    "racing": ["racing", "racer"],
    "fighting": ["fighting", "fighter", "fighting game"],
    "stealth": ["stealth", "stealth game"],
    "metroidvania": ["metroidvania"],
    "cozy": ["cozy", "cosy"],
    "story-rich": ["story-rich", "story rich", "narrative", "story driven", "story-driven"],
    "open-world": ["open-world", "open world"],
    "single-player": ["single-player", "single player"],
}


def _purge_pulsar_sessions():
    cutoff = time.time() - PULSAR_SESSION_TTL
    with SESSION_LOCK:
        stale = [sid for sid, state in PULSAR_SESSIONS.items() if state.get("last_seen", 0) < cutoff]
        for sid in stale:
            PULSAR_SESSIONS.pop(sid, None)


def _get_pulsar_session(session_id):
    if not session_id:
        return {"memory": {}, "last_results": [], "last_query": "", "last_seen": time.time()}
    _purge_pulsar_sessions()
    with SESSION_LOCK:
        state = PULSAR_SESSIONS.setdefault(session_id, {
            "memory": {},
            "last_results": [],
            "last_query": "",
            "last_seen": time.time(),
        })
        state["last_seen"] = time.time()
        return state


def _session_memory(session_id):
    return _get_pulsar_session(session_id).setdefault("memory", {})


def _session_set(session_id, key, value):
    if not session_id:
        return
    state = _get_pulsar_session(session_id)
    with SESSION_LOCK:
        state["memory"][key] = value


def _session_clear(session_id):
    if not session_id:
        return
    with SESSION_LOCK:
        PULSAR_SESSIONS.pop(session_id, None)


def get_user_memory(user_id):
    if user_id and str(user_id).startswith("pulsar_session_"):
        return dict(_session_memory(user_id))
    if not user_id:
        return {}
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("SELECT pref_key, pref_value FROM user_memory WHERE user_id = ?", (user_id,))
        rows = c.fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()
    return {k: v for k, v in rows}


def set_user_memory(user_id, key, val):
    if not user_id:
        return
    if str(user_id).startswith("pulsar_session_"):
        _session_set(user_id, key, val)
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("""
            INSERT OR REPLACE INTO user_memory (user_id, pref_key, pref_value, updated_at)
            VALUES (?, ?, ?, ?)
        """, (user_id, key, val, datetime.now(timezone.utc).isoformat()))
        conn.commit()
    except sqlite3.Error:
        pass
    finally:
        conn.close()


def clear_user_memory(user_id):
    if not user_id:
        return
    if str(user_id).startswith("pulsar_session_"):
        _session_clear(user_id)
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("DELETE FROM user_memory WHERE user_id = ?", (user_id,))
        conn.commit()
    except sqlite3.Error:
        pass
    finally:
        conn.close()


def _dedupe_preserve(values):
    out = []
    seen = set()
    for value in values:
        value = str(value).strip()
        if value and value.lower() not in seen:
            seen.add(value.lower())
            out.append(value)
    return out


def _memory_add(session_id, key, values):
    if not values:
        return
    mem = _session_memory(session_id)
    existing = mem.get(key, [])
    if not isinstance(existing, list):
        existing = [existing]
    _session_set(session_id, key, _dedupe_preserve(existing + values))


def _extract_preferences(text):
    low = text.lower()
    changes = {}

    platforms = []
    for canonical, aliases in PLATFORM_ALIASES.items():
        if any(re.search(r"\b" + re.escape(alias) + r"\b", low) for alias in aliases):
            platforms.append(canonical)
    if platforms and any(k in low for k in ["i play", "play on", "i use", "i own", "my platform", "i prefer", "main platform", "mostly play", "remember"]):
        changes["platforms"] = platforms

    genres = []
    for canonical, aliases in GENRE_ALIASES.items():
        if any(alias in low for alias in aliases):
            genres.append(canonical)
    if genres and any(k in low for k in ["i like", "i love", "i enjoy", "favorite", "favourite", "i prefer", "remember"]):
        changes["favorite_genres"] = genres

    disliked_genres = []
    if any(k in low for k in ["i hate", "i dislike", "i don't like", "i dont like", "avoid", "not a fan"]):
        for canonical, aliases in GENRE_ALIASES.items():
            if any(alias in low for alias in aliases):
                disliked_genres.append(canonical)
    if disliked_genres:
        changes["disliked_genres"] = disliked_genres

    if re.search(r"\b(single[- ]player|singleplayer)\b", low):
        if any(k in low for k in ["prefer", "like", "love", "mostly", "play", "remember"]):
            changes["playstyle"] = "single-player"
    elif re.search(r"\b(co[- ]?op|cooperative)\b", low):
        if any(k in low for k in ["prefer", "like", "love", "mostly", "play", "remember"]):
            changes["playstyle"] = "co-op"
    elif re.search(r"\b(multiplayer|competitive)\b", low):
        if any(k in low for k in ["prefer", "like", "love", "mostly", "play", "remember"]):
            changes["playstyle"] = "multiplayer/competitive"

    if "no spoilers" in low or "without spoilers" in low:
        changes["spoilers"] = "avoid spoilers"
    elif "spoilers are fine" in low or "spoilers okay" in low or "spoil it" in low:
        changes["spoilers"] = "spoilers allowed"

    if any(k in low for k in ["favorite game", "favourite game", "i love ", "i like ", "games i love"]):
        candidates = re.split(r"(?:favorite game is|favourite game is|i love|i like|games i love)", text, flags=re.I)
        if len(candidates) > 1:
            candidate = re.split(r"[.!?,;]| and ", candidates[-1], maxsplit=1)[0].strip()
            if candidate:
                game = find_game_across_databases(candidate)
                if game and candidate.lower() in game["title"].lower() or (game and game["title"].lower() in candidate.lower()):
                    changes["favorite_games"] = [game["title"]]

    if any(k in low for k in ["hate", "dislike", "don't like", "dont like", "avoid"]):
        candidates = re.split(r"(?:i hate|i dislike|i don't like|i dont like|avoid)", text, flags=re.I)
        if len(candidates) > 1:
            candidate = re.split(r"[.!?,;]", candidates[-1], maxsplit=1)[0].strip()
            if candidate:
                game = find_game_across_databases(candidate)
                if game and (candidate.lower() in game["title"].lower() or game["title"].lower() in candidate.lower()):
                    changes["disliked_games"] = [game["title"]]

    return changes


def _apply_preferences(session_id, changes):
    for key, value in changes.items():
        if isinstance(value, list):
            _memory_add(session_id, key, value)
        else:
            _session_set(session_id, key, value)


def _memory_summary(mem):
    if not mem:
        return "No gaming preferences have been captured in this session."
    parts = []
    for key, value in mem.items():
        label = key.replace("_", " ").title()
        if isinstance(value, list):
            value = ", ".join(value)
        parts.append(f"- {label}: {value}")
    return "\n".join(parts)


def _metacritic_year_url(year, platform=None):
    if platform:
        slug = METACRITIC_PLATFORM_SLUGS.get(platform.lower())
        if slug:
            return f"https://www.metacritic.com/browse/game/{slug}/all/{year}/"
    return f"https://www.metacritic.com/browse/game/all/all/{year}/"


def _metacritic_current_url():
    return "https://www.metacritic.com/browse/game/all/all/current-year/metascore/"


def _metacritic_all_time_url():
    return "https://www.metacritic.com/browse/game/"


def _metacritic_game_url(title):
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return f"https://www.metacritic.com/game/{slug}/"


def _resolve_dns(hostname, force=False):
    now = time.time()
    with METACRITIC_DNS_LOCK:
        cached = METACRITIC_DNS_CACHE.get(hostname)
        if cached and not force and now - cached["ts"] < METACRITIC_DNS_TTL:
            return cached["addresses"]
    try:
        addresses = sorted({info[4][0] for info in socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)})
    except (socket.gaierror, OSError):
        addresses = []
    with METACRITIC_DNS_LOCK:
        METACRITIC_DNS_CACHE[hostname] = {"ts": now, "addresses": addresses}
    return addresses


def _discover_metacritic_api_key(force=False):
    global METACRITIC_DISCOVERED_KEY
    if METACRITIC_API_KEY:
        return METACRITIC_API_KEY
    with METACRITIC_DISCOVERY_LOCK:
        if METACRITIC_DISCOVERED_KEY and not force:
            return METACRITIC_DISCOVERED_KEY
        urls = ["https://www.metacritic.com/", "https://www.metacritic.com/game/"]
        for page_url in urls:
            try:
                try:
                    _resolve_dns(urllib.parse.urlparse(page_url).hostname or "www.metacritic.com")
                except Exception:
                    pass
                req = urllib.request.Request(
                    page_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 GamePulseAI",
                        "Accept": "text/html,application/xhtml+xml",
                        "Accept-Language": "en-US,en;q=0.9",
                    },
                )
                with urllib.request.urlopen(req, timeout=3.0) as response:
                    html_bytes = response.read(350_000)
                text = html_bytes.decode("utf-8", errors="ignore")
                match = re.search(r"backend\.metacritic\.com[^\"' ]*apiKey=([A-Za-z0-9]+)", text)
                if not match:
                    match = re.search(r"apiKey=([A-Za-z0-9]{20,})", text)
                if match:
                    METACRITIC_DISCOVERED_KEY = match.group(1)
                    return METACRITIC_DISCOVERED_KEY
            except Exception:
                continue
    return DEFAULT_METACRITIC_KEY


def _metacritic_api_url(path, **params):
    q = dict(params)
    key = _discover_metacritic_api_key()
    if key:
        q.setdefault("apiKey", key)
    return f"{METACRITIC_API_BASE}/{path.lstrip('/')}?{urllib.parse.urlencode(q)}"


def _fetch_json_cached(url, timeout=3.5, ttl=METACRITIC_CACHE_TTL):
    now = time.time()
    with METACRITIC_CACHE_LOCK:
        cached = METACRITIC_CACHE.get(url)
        if cached:
            cached_ttl = ttl if cached.get("value") is not None else METACRITIC_NEGATIVE_CACHE_TTL
            if now - cached["ts"] < cached_ttl:
                return cached["value"]

    value = None
    response_status = None
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://www.metacritic.com",
        "Referer": "https://www.metacritic.com/",
        "Cache-Control": "no-cache",
    }

    urls_to_try = [url]
    if "backend.metacritic.com" in url:
        urls_to_try.append(url.replace("https://backend.metacritic.com", "https://internal-prod.apigee.fandom.net/v1/xapi"))

    for target_url in urls_to_try:
        t_parsed = urllib.parse.urlparse(target_url)
        t_host = t_parsed.hostname or ""
        for attempt in range(2):
            try:
                try:
                    _resolve_dns(t_host, force=(attempt == 1))
                except Exception:
                    pass
                req = urllib.request.Request(target_url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    response_status = getattr(response, "status", 200)
                    raw = response.read(1_250_000)
                    if response_status != 200:
                        raise urllib.error.HTTPError(target_url, response_status, "Metacritic API HTTP error", response.headers, None)
                    value = json.loads(raw.decode("utf-8", errors="ignore"))
                    break
            except urllib.error.HTTPError as exc:
                response_status = exc.code
                if exc.code in (401, 403) and t_host.endswith("metacritic.com") and attempt == 0:
                    key = _discover_metacritic_api_key(force=True)
                    if key:
                        parsed = urllib.parse.parse_qs(t_parsed.query, keep_blank_values=True)
                        parsed["apiKey"] = [key]
                        rebuilt_query = urllib.parse.urlencode(parsed, doseq=True)
                        target_url = urllib.parse.urlunparse(t_parsed._replace(query=rebuilt_query))
                        continue
                break
            except Exception:
                if attempt == 0:
                    time.sleep(0.05)
                    continue
                break
        if value is not None:
            break

    with METACRITIC_CACHE_LOCK:
        METACRITIC_CACHE[url] = {"ts": now, "value": value, "status": response_status}
    return value


def _parse_finder_item(item):
    if not isinstance(item, dict):
        return None
    summary = item.get("criticScoreSummary") or {}
    score = summary.get("score")
    if score is None:
        return None
    try:
        score = int(score)
    except (TypeError, ValueError):
        return None
    genres = []
    for genre in item.get("genres") or []:
        if isinstance(genre, dict):
            name = genre.get("name") or genre.get("displayName") or genre.get("slug")
        else:
            name = str(genre)
        if name:
            genres.append(str(name).strip())
    platforms = []
    for platform in item.get("platforms") or item.get("gamePlatforms") or []:
        if isinstance(platform, dict):
            name = platform.get("name") or platform.get("displayName") or platform.get("slug")
        else:
            name = str(platform)
        if name:
            platforms.append(str(name).strip())
    return {
        "title": str(item.get("title") or "").strip(),
        "score": score,
        "year": item.get("premiereYear") or item.get("releaseYear"),
        "slug": item.get("slug"),
        "critic_reviews": summary.get("reviewCount"),
        "user_score": (item.get("userScore") or {}).get("score") if isinstance(item.get("userScore"), dict) else item.get("userScore"),
        "genres": _dedupe_preserve(genres),
        "platforms": _dedupe_preserve(platforms),
    }


def _browse_metacritic_games(year_min=None, year_max=None, limit=24, offset=0):
    params = {
        "sortBy": "META_SCORE",
        "sortDirection": "DESC",
        "mcoTypeId": 13,
        "offset": offset,
        "limit": min(max(1, int(limit)), 50),
        "componentName": "finder",
        "componentType": "Finder",
    }
    if year_min is not None:
        params["releaseYearMin"] = int(year_min)
    if year_max is not None:
        params["releaseYearMax"] = int(year_max)
    url = _metacritic_api_url("finder/metacritic/web", **params)
    data = _fetch_json_cached(url)
    try:
        items = data["data"]["items"]
    except (TypeError, KeyError):
        return [], False, url
    parsed = []
    for item in items:
        parsed_item = _parse_finder_item(item)
        if parsed_item and parsed_item["title"]:
            parsed.append(parsed_item)
    return parsed, bool(parsed), url


def _fetch_metacritic_game_detail(slug):
    if not slug:
        return None
    url = _metacritic_api_url(
        f"games/metacritic/{urllib.parse.quote(str(slug), safe='-')}/web",
        componentName="product",
        componentType="Product",
    )
    data = _fetch_json_cached(url, ttl=METACRITIC_DETAIL_CACHE_TTL)
    try:
        item = data["data"]["item"]
        platforms = []
        for platform in item.get("platforms") or []:
            name = platform.get("name")
            if name:
                platforms.append({
                    "name": name,
                    "slug": platform.get("slug"),
                    "metascore": (platform.get("criticScoreSummary") or {}).get("score"),
                    "critic_reviews": (platform.get("criticScoreSummary") or {}).get("reviewCount"),
                    "release_date": platform.get("releaseDate"),
                })
        genres = []
        for genre in item.get("genres") or []:
            if isinstance(genre, dict):
                name = genre.get("name") or genre.get("displayName") or genre.get("slug")
            else:
                name = str(genre)
            if name:
                genres.append(str(name).strip())
        developers = []
        publishers = []
        for person in item.get("developers") or []:
            if isinstance(person, dict):
                name = person.get("name") or person.get("title")
            else:
                name = str(person)
            if name:
                developers.append(str(name).strip())
        for person in item.get("publishers") or []:
            if isinstance(person, dict):
                name = person.get("name") or person.get("title")
            else:
                name = str(person)
            if name:
                publishers.append(str(name).strip())
        return {
            "title": item.get("title"),
            "slug": item.get("slug") or slug,
            "release_date": item.get("releaseDate"),
            "platform": item.get("platform"),
            "platforms": platforms,
            "score": (item.get("criticScoreSummary") or {}).get("score"),
            "critic_reviews": (item.get("criticScoreSummary") or {}).get("reviewCount"),
            "genres": _dedupe_preserve(genres),
            "developers": _dedupe_preserve(developers),
            "publishers": _dedupe_preserve(publishers),
        }
    except (TypeError, KeyError):
        return None


def _game_matches_platform(detail, platform):
    aliases = PLATFORM_ALIASES.get(platform.lower(), [platform.lower()])
    for p in detail.get("platforms") or []:
        name = str(p.get("name") or "").lower()
        slug = str(p.get("slug") or "").lower()
        if any(alias.lower() in name or alias.lower() in slug for alias in aliases):
            return True
    lead = str(detail.get("platform") or "").lower()
    return any(alias.lower() in lead for alias in aliases)


def _filter_live_by_platform(items, platform, target_count=5):
    if not platform:
        return items[:target_count]
    filtered = []
    for item in items[:24]:
        local = _find_local_for_live_item(item.get("title", ""), item.get("year"))
        if local and any(platform.lower() in p.lower() for p in str(local.get("platforms", "")).split(",")):
            item["local"] = local
            filtered.append(item)
            continue
        detail = _fetch_metacritic_game_detail(item.get("slug"))
        if detail and _game_matches_platform(detail, platform):
            item["detail"] = detail
            filtered.append(item)
        if len(filtered) >= target_count:
            break
    return filtered[:target_count]


def fetch_metacritic_year(year, platform=None, limit=10):
    candidates, ok, url = _browse_metacritic_games(year_min=year, year_max=year, limit=30 if platform else limit)
    if not ok:
        return [], False, _metacritic_year_url(year, platform)
    for item in candidates:
        item["year"] = year
    selected = _filter_live_by_platform(candidates, platform, target_count=limit) if platform else candidates[:limit]
    return selected, bool(selected), url


def fetch_metacritic_current(limit=10, platform=None):
    candidates, ok, url = _browse_metacritic_games(year_min=CURRENT_YEAR, year_max=CURRENT_YEAR, limit=30 if platform else limit)
    if not ok:
        return [], False, _metacritic_current_url()
    for item in candidates:
        item["year"] = CURRENT_YEAR
    selected = _filter_live_by_platform(candidates, platform, target_count=limit) if platform else candidates[:limit]
    return selected, bool(selected), url


def fetch_metacritic_all_time(limit=10, platform=None):
    candidates, ok, url = _browse_metacritic_games(limit=30)
    if not ok:
        return [], False, _metacritic_all_time_url()
    selected = _filter_live_by_platform(candidates, platform, target_count=limit) if platform else candidates[:limit]
    return selected, bool(selected), url


def fetch_metacritic_search(query, limit=8):
    q = urllib.parse.quote(query.strip())
    url = _metacritic_api_url(
        f"finder/metacritic/search/{q}/web",
        offset=0,
        limit=min(max(1, limit), 30),
        sortBy="META_SCORE",
        sortDirection="DESC",
        mcoTypeId=13,
        componentName="search",
        componentType="SearchResult",
    )
    data = _fetch_json_cached(url)
    try:
        items = data["data"]["items"]
    except (TypeError, KeyError):
        return []
    out = []
    for item in items:
        parsed = _parse_finder_item(item)
        if parsed:
            parsed["slug"] = item.get("slug")
            out.append(parsed)
    return out


def _local_year_games(year):
    games = []
    for g in ALL_YEARS_DATABASE.get(year, []):
        item = dict(g)
        item["year"] = year
        games.append(item)
    return sorted(games, key=lambda g: (-int(g.get("score") or 0), g.get("title", "").lower()))


def _find_local_for_live_item(title, year=None):
    target = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
    candidates = ALL_YEARS_DATABASE.get(year, []) if year in ALL_YEARS_DATABASE else []
    if not candidates:
        for y, gms in ALL_YEARS_DATABASE.items():
            candidates.extend(gms)
    for g in candidates:
        gs = re.sub(r"[^a-z0-9]+", " ", g["title"].lower()).strip()
        if target == gs or target in gs or gs in target:
            item = dict(g)
            item["year"] = g.get("year", year)
            return item
    return None


def _format_ranked_games(title, games, source_url, source_label, pref_platform=None, numbered=True):
    lines = [f"🏆 **{title}**", ""]
    lines.append(f"Source: [{source_label}]({source_url})")
    lines.append("")
    results = []
    for i, g in enumerate(games[:10], 1):
        if "score" not in g:
            continue
        local = g.get("local") or _find_local_for_live_item(g["title"], g.get("year")) or {}
        platforms = g.get("platforms") or local.get("platforms") or ""
        genre = g.get("genre") or local.get("genre") or ""
        year = g.get("year") or local.get("year") or ""
        desc = g.get("desc") or local.get("desc") or ""
        label = f"{i}. " if numbered else ""
        lines.append(f"**{label}{g['title']}** — **Metacritic {g['score']}/100**")
        if year:
            lines.append(f"- **Year:** {year}")
        if platforms:
            lines.append(f"- **Platforms:** {platforms}")
        if genre:
            lines.append(f"- **Genre:** {genre}")
        if desc:
            lines.append(f"- **Why it stands out:** {desc}")
        if pref_platform and platforms and pref_platform.lower() in platforms.lower():
            lines.append(f"- ⭐ Matches your **{pref_platform}** preference")
        lines.append(f"- [Metacritic page]({_metacritic_game_url(g['title'])})")
        lines.append("")
        results.append(g["title"])
    return "\n".join(lines).strip(), results


def get_year_response(year, min_score=None, pref_platform=None):
    if year > CURRENT_YEAR:
        return (f"I don't have released Metacritic results for **{year}** because it is in the future. "
                f"I won't invent a ranking. [Open Metacritic's current games page]({_metacritic_current_url()}).", [])

    live, is_live, source_url = fetch_metacritic_year(year, pref_platform, limit=10)
    if is_live:
        games = []
        for item in live:
            if min_score and item["score"] < min_score:
                continue
            local = _find_local_for_live_item(item["title"], year)
            enriched = dict(item)
            enriched["year"] = year
            if local:
                enriched["local"] = local
            detail = item.get("detail") or {}
            if detail.get("platforms") and not enriched.get("platforms"):
                enriched["platforms"] = ", ".join(p.get("name", "") for p in detail.get("platforms", []) if p.get("name"))
            games.append(enriched)
        title = f"Top Metacritic Games of {year}"
        if pref_platform:
            title += f" for {pref_platform}"
        response, results = _format_ranked_games(title, games[:5], source_url, "Metacritic", pref_platform)
        return response, results

    local_games = _local_year_games(year)
    if pref_platform:
        local_games = [g for g in local_games if any(a in g.get("platforms", "").lower() for a in PLATFORM_ALIASES.get(pref_platform.lower(), [pref_platform.lower()]))]
    if min_score:
        local_games = [g for g in local_games if int(g.get("score") or 0) >= min_score]
    if local_games:
        response, results = _format_ranked_games(
            f"Top Indexed Metacritic Games of {year}" + (f" for {pref_platform}" if pref_platform else ""),
            local_games[:5],
            _metacritic_year_url(year, pref_platform),
            "GamePulse indexed historical data",
            pref_platform,
        )
        return response + "\n\n*Live Metacritic retrieval was unavailable, so these results come from GamePulse's indexed historical dataset. I have not labeled them as live.*", results

    if 1984 <= year <= CURRENT_YEAR:
        return (f"I couldn't retrieve a verified ranking for **{year}** right now, so I won't make one up. "
                f"You can verify the year directly on [Metacritic]({_metacritic_year_url(year, pref_platform)}).", [])
    return (f"I don't have a verified gaming dataset for **{year}**. I won't invent scores or rankings.", [])


def get_period_response(start_year, end_year, pref_platform=None):
    start_year = max(1984, start_year)
    end_year = min(CURRENT_YEAR, end_year)
    if start_year > end_year:
        return "That year range is not valid.", []

    try:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        years = list(range(start_year, end_year + 1))
        gathered = []
        with ThreadPoolExecutor(max_workers=min(6, len(years))) as executor:
            future_map = {executor.submit(fetch_metacritic_year, y, pref_platform, 10): y for y in years}
            for fut in as_completed(future_map):
                y = future_map[fut]
                try:
                    ranked, live, url = fut.result()
                except Exception:
                    ranked, live, url = [], False, _metacritic_year_url(y, pref_platform)
                if live:
                    for item in ranked:
                        local = _find_local_for_live_item(item["title"], y)
                        e = dict(item)
                        e["year"] = y
                        if local:
                            e["local"] = local
                        gathered.append(e)
    except Exception:
        gathered = []

    gathered_live = bool(gathered)
    if not gathered:
        for y in range(start_year, end_year + 1):
            for g in _local_year_games(y):
                gathered.append(dict(g, year=y))

    deduped = {}
    for g in sorted(gathered, key=lambda x: (-int(x.get("score") or 0), int(x.get("year") or 0), x.get("title", "").lower())):
        key = g["title"].lower()
        deduped.setdefault(key, g)
    games = list(deduped.values())[:10]
    source_url = _metacritic_year_url(end_year, pref_platform)
    label = "Metacritic" if gathered_live else "GamePulse indexed historical data"
    response, results = _format_ranked_games(f"Highest-Rated Games from {start_year}–{end_year}", games, source_url, label, pref_platform)
    if not gathered_live:
        response += "\n\n*Live Metacritic retrieval was unavailable, so these are clearly labeled indexed historical results rather than a claim of live ranking data.*"
    return response, results


def format_decade_response(pref_platform=None):
    return get_period_response(CURRENT_YEAR - 10, CURRENT_YEAR, pref_platform)


def format_all_time_response(pref_platform=None):
    live, is_live, url = fetch_metacritic_all_time(limit=10)
    if is_live:
        games = []
        for item in live:
            local = find_game_across_databases(item["title"])
            enriched = dict(item)
            if local:
                enriched["local"] = local
                enriched["year"] = local.get("year")
            games.append(enriched)
        return _format_ranked_games("Highest-Rated Video Games of All Time", games, url, "Metacritic", pref_platform)

    all_games = []
    for year, games in ALL_YEARS_DATABASE.items():
        for g in games:
            all_games.append(dict(g, year=year))
    if pref_platform:
        all_games = [g for g in all_games if any(a in g.get("platforms", "").lower() for a in PLATFORM_ALIASES.get(pref_platform.lower(), [pref_platform.lower()]))]
    all_games.sort(key=lambda g: (-int(g.get("score") or 0), g.get("title", "").lower()))
    seen = set()
    deduped = []
    for g in all_games:
        if g["title"].lower() not in seen:
            seen.add(g["title"].lower())
            deduped.append(g)
    response, results = _format_ranked_games(
        "Highest-Rated Indexed Video Games of All Time",
        deduped[:10],
        url,
        "GamePulse indexed historical data",
        pref_platform,
    )
    return response + "\n\n*Live Metacritic retrieval was unavailable, so these are clearly labeled indexed historical results rather than a claim of live ranking data.*", results


def find_game_across_databases(name):
    name_clean = re.sub(r"\s+", " ", str(name).strip().lower())
    if not name_clean:
        return None
    for year, games in ALL_YEARS_DATABASE.items():
        for g in games:
            if name_clean == g["title"].strip().lower():
                return dict(g, year=year)
    for year, games in ALL_YEARS_DATABASE.items():
        for g in games:
            title_clean = g["title"].strip().lower()
            if len(name_clean) >= 5 and (name_clean in title_clean or title_clean in name_clean):
                return dict(g, year=year)
    try:
        results = fetch_metacritic_search(name, limit=8)
    except Exception:
        results = []
    if results:
        best = None
        best_ratio = 0.0
        for item in results:
            ratio = difflib.SequenceMatcher(None, name_clean, item["title"].lower()).ratio()
            if name_clean == item["title"].lower():
                best = item
                best_ratio = 1.0
                break
            if ratio > best_ratio:
                best_ratio = ratio
                best = item
        if best and best_ratio >= 0.78:
            detail = _fetch_metacritic_game_detail(best.get("slug"))
            platforms = ""
            if detail:
                platforms = ", ".join(p.get("name", "") for p in detail.get("platforms", []) if p.get("name"))
            return {
                "title": best["title"],
                "score": best.get("score"),
                "year": best.get("year"),
                "platforms": platforms or (detail.get("platform") if detail else ""),
                "genre": "",
                "desc": "",
                "slug": best.get("slug"),
                "live": True,
            }
    best = None
    best_ratio = 0.86
    for year, games in ALL_YEARS_DATABASE.items():
        for g in games:
            ratio = difflib.SequenceMatcher(None, name_clean, g["title"].lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best = dict(g, year=year)
    return best


def _find_explicit_game_in_text(text):
    low = text.lower()
    titles = []
    for year, games in ALL_YEARS_DATABASE.items():
        for g in games:
            titles.append((len(g["title"]), g["title"], year, g))
    for _, title, year, g in sorted(titles, reverse=True):
        if re.search(r"(?<![a-z0-9])" + re.escape(title.lower()) + r"(?![a-z0-9])", low):
            return dict(g, year=year)
    return None


def _extract_platform(text):
    low = text.lower()
    for canonical, aliases in PLATFORM_ALIASES.items():
        if any(re.search(r"\b" + re.escape(alias) + r"\b", low) for alias in aliases):
            return canonical
    return None


def _extract_year(text):
    years = [int(y) for y in re.findall(r"\b(19\d{2}|20\d{2})\b", text)]
    return years[0] if years else None


def _extract_year_range(text):
    m = re.search(r"\b(19\d{2}|20\d{2})\s*(?:-|–|—|to|through)\s*(19\d{2}|20\d{2})\b", text.lower())
    if not m:
        m = re.search(r"\b(19\d{2}|20\d{2})s\b", text.lower())
        if m:
            y = int(m.group(1))
            return y, y + 9
        return None
    a, b = int(m.group(1)), int(m.group(2))
    return (min(a, b), max(a, b))


def _extract_score_floor(text):
    m = re.search(r"\b(?:score|rated|rating)?\s*(\d{2})\s*\+", text.lower())
    return int(m.group(1)) if m else None


RANKING_TERMS = {
    "best", "top", "highest rated", "highest-rated", "highest", "best rated", "best-rated",
    "greatest", "ranked", "ranking", "rankings", "most acclaimed", "most highly rated",
    "best reviewed", "highest scoring", "highest-scored", "top rated", "top-rated",
    "show me", "give me", "what are", "what're", "which are", "list", "recommend",
}

GENRE_FAMILY_ALIASES = {
    "platformer": ["platformer", "platformers", "platforming", "platform game", "platform games", "2d platformer", "3d platformer", "3d platformers", "2d platformers", "2d platform games", "3d platform games", "jump and run", "jump-and-run"],
    "rpg": ["rpg", "role playing", "role-playing", "role playing games", "role-playing games"],
    "jrpg": ["jrpg", "japanese rpg", "japanese role playing"],
    "crpg": ["crpg", "computer rpg", "computer role playing"],
    "action rpg": ["action rpg", "action-rpg", "action role playing"],
    "soulslike": ["soulslike", "souls-like", "souls like", "soulsborne"],
    "fps": ["fps", "first person shooter", "first-person shooter", "first person shooters", "shooters"],
    "horror": ["horror", "survival horror", "psychological horror", "horror games"],
    "strategy": ["strategy", "strategy games", "4x", "rts", "real-time strategy", "turn based strategy", "turn-based strategy"],
    "roguelike": ["roguelike", "roguelite", "rogue-like", "rogue-lite", "rogue like"],
    "deckbuilder": ["deckbuilder", "deck builder", "card battler", "card-based"],
    "racing": ["racing", "racing games", "racer", "racing game"],
    "fighting": ["fighting", "fighting games", "fighter", "fighting game"],
    "stealth": ["stealth", "stealth games", "stealth game"],
    "metroidvania": ["metroidvania", "metroidvanias"],
    "open-world": ["open world", "open-world", "open world games", "open-world games"],
    "cozy": ["cozy", "cosy", "cozy games", "cozy game"],
    "survival": ["survival", "survival games", "survival game"],
    "adventure": ["adventure", "adventure games", "action adventure", "action-adventure"],
    "simulation": ["simulation", "sim", "simulator", "simulation games"],
    "sports": ["sports", "sports games", "sport game"],
    "puzzle": ["puzzle", "puzzle games", "puzzle game"],
    "sandbox": ["sandbox", "sandbox games", "sandbox game"],
}


def _normalize_search_text(text):
    text = re.sub(r"[’'`]", " ", text.lower())
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_genre(text):
    low = _normalize_search_text(text)
    candidates = []
    for canonical, aliases in GENRE_FAMILY_ALIASES.items():
        for alias in aliases:
            if re.search(r"\b" + re.escape(alias) + r"\b", low):
                candidates.append((len(alias), canonical))
    if not candidates:
        return None
    return max(candidates, key=lambda x: x[0])[1]


def _extract_result_limit(text):
    low = _normalize_search_text(text)
    patterns = [
        r"\btop\s+(\d{1,2})\b",
        r"\b(?:show|give|list|find)\s+(?:me\s+)?(?:the\s+)?(\d{1,2})\b",
        r"\b(\d{1,2})\s+(?:best|top|highest)\b",
    ]
    for pattern in patterns:
        m = re.search(pattern, low)
        if m:
            return max(1, min(20, int(m.group(1))))
    return 5


def _extract_relative_period(text):
    low = _normalize_search_text(text)
    m = re.search(r"\b(?:last|past|previous)\s+(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten)\s+years?\b", low)
    if m:
        word_numbers = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
        token = m.group(1)
        n = word_numbers.get(token, int(token) if token.isdigit() else 10)
        n = max(1, min(50, n))
        return CURRENT_YEAR - n, CURRENT_YEAR
    if re.search(r"\b(?:last|past|previous|preceding)\s+decade\b", low) or re.search(r"\b(?:last|past|previous)\s+(?:10|ten)\s+years?\b", low):
        return CURRENT_YEAR - 10, CURRENT_YEAR
    if re.search(r"\bthis\s+decade\b", low):
        return CURRENT_YEAR // 10 * 10, CURRENT_YEAR
    return None


def _extract_ranking_scope(text):
    low = _normalize_search_text(text)
    explicit_range = _extract_year_range(low)
    if explicit_range:
        return explicit_range[0], min(explicit_range[1], CURRENT_YEAR)
    relative = _extract_relative_period(low)
    if relative:
        return relative
    m = re.search(r"\b(?:the\s+)?((?:19|20)?\d{2})s\b", low)
    if m:
        token = m.group(1)
        if len(token) == 2:
            decade = 1900 + int(token) if int(token) >= 70 else 2000 + int(token)
        else:
            decade = int(token)
        return decade, min(decade + 9, CURRENT_YEAR)
    year = _extract_year(low)
    if year is not None:
        return year, min(year, CURRENT_YEAR)
    return None


def _is_ranking_intent(text):
    low = _normalize_search_text(text)
    if any(phrase in low for phrase in [
        "best", "top", "highest rated", "highest-rated", "most acclaimed", "best rated", "best-rated",
        "greatest", "ranked", "ranking", "rankings", "most highly rated", "best reviewed", "highest scoring",
        "highest-scored", "top rated", "top-rated", "what are the best", "what're the best", "show me the best",
    ]):
        return True
    scope_words = any(k in low for k in [
        "on switch", "on pc", "on ps5", "on xbox", "platformers", "rpg", "fps", "horror", "racing",
        "last decade", "past decade", "previous decade", "last ten years", "past ten years", "last ", "past ",
        "from 19", "from 20", "between 19", "between 20", "in the 19", "in the 20", "this year",
        "right now", "currently",
    ])
    if any(k in low for k in ["recommend", "recommendations", "suggest", "show me", "give me", "list", "which", "what games"]) and scope_words:
        if not any(k in low for k in ["games like", "similar to", "fans of"]):
            return True
    return bool(re.search(r"\b(?:score|metacritic)\b", low) and any(k in low for k in ["games", "titles", "releases", "from", "of", "in"]))


def _ranking_filters(text, mem=None):
    low = _normalize_search_text(text)
    platform = _extract_platform(text)
    if not platform and any(k in low for k in ["my platform", "my console", "on my system", "for my console"]):
        platform = (mem or {}).get("platforms", [None])[0]
    genre = _extract_genre(text)
    start_year, end_year = _extract_ranking_scope(text) or (None, None)
    limit = _extract_result_limit(text)
    score_floor = _extract_score_floor(text)
    current_hint = any(k in low for k in ["right now", "out right now", "currently", "currently available", "this year", "current year", "latest releases"])
    all_time_hint = any(k in low for k in ["all time", "all-time", "ever", "in history", "of history", "throughout history"])
    return {
        "platform": platform,
        "genre": genre,
        "start_year": start_year,
        "end_year": end_year,
        "limit": limit,
        "score_floor": score_floor,
        "current": current_hint,
        "all_time": all_time_hint,
    }


def _genre_tokens_for_record(record):
    values = []
    values.extend(record.get("genres") or [])
    local = record.get("local") or {}
    if local.get("genre"):
        values.append(local.get("genre"))
    if record.get("genre"):
        values.append(record.get("genre"))
    return _normalize_search_text(" | ".join(map(str, values)))


def _genre_matches(record, requested):
    if not requested:
        return True
    text = _genre_tokens_for_record(record)
    aliases = GENRE_FAMILY_ALIASES.get(requested, [requested])
    if any(re.search(r"\b" + re.escape(alias) + r"\b", text) for alias in aliases):
        return True
    title = _normalize_search_text(record.get("title", ""))
    for arch in ALL_ARCHETYPES:
        if requested not in (arch.get("title", "").lower()) and not any(requested == g for g in GENRE_FAMILY_ALIASES if g in arch.get("title", "").lower()):
            continue
        if any(_normalize_search_text(g.get("title", "")) == title for g in arch.get("games", [])):
            return True
    return False


def _record_platform_score(record, platform):
    if not platform:
        return record.get("score")
    aliases = PLATFORM_ALIASES.get(platform.lower(), [platform.lower()])
    detail = record.get("detail") or {}
    for p in detail.get("platforms") or []:
        name = str(p.get("name") or "").lower()
        slug = str(p.get("slug") or "").lower()
        if any(alias.lower() in name or alias.lower() in slug for alias in aliases):
            score = p.get("metascore")
            if score is not None:
                return int(score)
    return None


def _record_matches_platform(record, platform):
    if not platform:
        return True
    aliases = PLATFORM_ALIASES.get(platform.lower(), [platform.lower()])
    local = record.get("local") or {}
    local_platforms = str(local.get("platforms") or record.get("platforms") or "").lower()
    if local_platforms and any(alias.lower() in local_platforms for alias in aliases):
        return True
    detail = record.get("detail") or {}
    return _game_matches_platform(detail, platform)


def _candidate_pages_for_scope(start_year=None, end_year=None, max_pages=3):
    offsets = [i * 50 for i in range(max_pages)]
    def one(offset):
        items, ok, url = _browse_metacritic_games(year_min=start_year, year_max=end_year, limit=50, offset=offset)
        return offset, items, ok, url
    out = []
    try:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=min(4, len(offsets))) as ex:
            futures = [ex.submit(one, offset) for offset in offsets]
            for fut in as_completed(futures):
                out.append(fut.result())
    except Exception:
        for offset in offsets:
            out.append(one(offset))
    items = []
    ok_any = False
    url = _metacritic_all_time_url() if start_year is None and end_year is None else _metacritic_year_url(end_year or start_year)
    for offset, page, ok, page_url in sorted(out, key=lambda x: x[0]):
        if ok:
            ok_any = True
            url = page_url
            items.extend(page)
    return items, ok_any, url


def _grounded_local_candidates(start_year=None, end_year=None, genre=None, platform=None):
    if start_year is None:
        years = sorted(ALL_YEARS_DATABASE.keys())
    else:
        years = range(start_year, (end_year if end_year is not None else start_year) + 1)
    out = []
    for year in years:
        for g in _local_year_games(year):
            record = dict(g, year=year)
            if genre and not _genre_matches(record, genre):
                continue
            if platform and not _record_matches_platform(record, platform):
                continue
            out.append(record)
    out.sort(key=lambda g: (-int(g.get("score") or 0), int(g.get("year") or 0), g.get("title", "").lower()))
    return out


def get_filtered_ranking_response(filters):
    platform = filters.get("platform")
    genre = filters.get("genre")
    start_year = filters.get("start_year")
    end_year = filters.get("end_year")
    limit = int(filters.get("limit") or 5)
    score_floor = filters.get("score_floor")
    current = filters.get("current")
    all_time = filters.get("all_time")

    if start_year is None and end_year is None and not all_time:
        if current:
            start_year = end_year = CURRENT_YEAR
        else:
            all_time = True

    if start_year is not None and start_year > CURRENT_YEAR:
        return (f"I don't have released Metacritic results for **{start_year}** or later because that is in the future. I won't invent a ranking. "
                f"[Open Metacritic]({_metacritic_current_url()})", [])
    if end_year is not None and end_year > CURRENT_YEAR:
        end_year = CURRENT_YEAR
    if start_year is not None:
        start_year = max(1984, start_year)
    if end_year is not None:
        end_year = min(CURRENT_YEAR, end_year)
    if start_year is not None and end_year is not None and start_year > end_year:
        return "That release-year range is not valid. I won't guess what you intended.", []

    scope_pages = 1
    if genre and platform:
        scope_pages = 6
    elif genre or platform:
        scope_pages = 4
    live_candidates, live_ok, source_url = _candidate_pages_for_scope(start_year, end_year, max_pages=scope_pages)
    enriched = []
    seen = set()
    prepared = []
    for item in live_candidates:
        title_key = _normalize_search_text(item.get("title", ""))
        if not title_key or title_key in seen:
            continue
        seen.add(title_key)
        item["year"] = item.get("year") or start_year
        if genre and not _genre_matches(item, genre) and item.get("genres"):
            continue
        if genre and not item.get("genres"):
            detail = _fetch_metacritic_game_detail(item.get("slug"))
            if not detail or not _genre_matches({**item, "genres": detail.get("genres", [])}, genre):
                continue
            item["detail"] = detail
            item["genres"] = detail.get("genres", [])
        prepared.append(item)
        if len(prepared) >= max(limit * 12, 60):
            break

    def enrich_platform(item):
        detail = item.get("detail") or _fetch_metacritic_game_detail(item.get("slug"))
        if not detail:
            return None
        record = dict(item)
        record["detail"] = detail
        record["genres"] = record.get("genres") or detail.get("genres", [])
        record["platforms"] = ", ".join(p.get("name", "") for p in detail.get("platforms", []) if p.get("name"))
        if not _record_matches_platform(record, platform):
            return None
        score = _record_platform_score(record, platform)
        if score is None:
            return None
        record["rank_score"] = score
        return record

    if platform:
        try:
            from concurrent.futures import ThreadPoolExecutor
            for batch_start in range(0, len(prepared), 12):
                batch = prepared[batch_start:batch_start + 12]
                with ThreadPoolExecutor(max_workers=min(12, len(batch))) as ex:
                    for record in ex.map(enrich_platform, batch):
                        if record:
                            if score_floor is None or record["rank_score"] >= score_floor:
                                enriched.append(record)
                if len(enriched) >= max(limit, 5):
                    break
        except Exception:
            for item in prepared:
                record = enrich_platform(item)
                if record and (score_floor is None or record["rank_score"] >= score_floor):
                    enriched.append(record)
                if len(enriched) >= max(limit, 5):
                    break
    else:
        for item in prepared:
            if score_floor is not None and int(item.get("score") or 0) < score_floor:
                continue
            item["rank_score"] = item.get("score")
            enriched.append(item)
            if len(enriched) >= max(limit * 3, 15):
                break

    if live_ok and enriched:
        enriched.sort(key=lambda x: (-int(x.get("rank_score") or 0), int(x.get("year") or 0), x.get("title", "").lower()))
        selected = enriched[:limit]
        scope_label = "all time"
        if start_year is not None and end_year is not None and start_year == end_year:
            scope_label = str(start_year)
        elif start_year is not None and end_year is not None:
            scope_label = f"{start_year}–{end_year}"
        elif current:
            scope_label = str(CURRENT_YEAR)
        qualifier = []
        if genre:
            qualifier.append(genre.title())
        if platform:
            qualifier.append(platform.upper() if platform != "steam deck" else "Steam Deck")
        title = "Top Metacritic Games"
        if qualifier:
            title += " — " + " on ".join(qualifier)
        title += f" ({scope_label})"
        lines = [f"🏆 **{title}**", "", f"Source: [Metacritic]({source_url})", ""]
        results = []
        for i, game in enumerate(selected, 1):
            local = game.get("local") or _find_local_for_live_item(game['title'], game.get('year')) or {}
            year = game.get("year") or local.get("year") or ""
            plats = game.get("platforms") or local.get("platforms") or ""
            genres = game.get("genres") or local.get("genre") or game.get("genre") or ""
            lines.append(f"**{i}. {game['title']}** — **Metacritic {game['rank_score']}/100**")
            if year: lines.append(f"- **Year:** {year}")
            if plats: lines.append(f"- **Platforms:** {plats}")
            if genres:
                if isinstance(genres, list): genres = ", ".join(genres)
                lines.append(f"- **Genre:** {genres}")
            desc = local.get("desc") or game.get("desc")
            if desc: lines.append(f"- **Why it stands out:** {desc}")
            lines.append(f"- [Metacritic page]({_metacritic_game_url(game['title'])})")
            lines.append("")
            results.append(game["title"])
        return "\n".join(lines).strip(), results

    # Live retrieval unavailable: use clearly labeled indexed data fallback
    local = _grounded_local_candidates(start_year, end_year, genre, platform)
    if score_floor is not None:
        local = [g for g in local if int(g.get("score") or 0) >= score_floor]
    selected = local[:limit]
    if selected:
        scope_label = "all time" if start_year is None else (str(start_year) if start_year == end_year else f"{start_year}–{end_year}")
        qualifier = []
        if genre: qualifier.append(genre.title())
        if platform: qualifier.append(platform.upper() if platform != "steam deck" else "Steam Deck")
        heading = "Top Indexed Metacritic Games"
        if qualifier: heading += " — " + " on ".join(qualifier)
        heading += f" ({scope_label})"
        response, results = _format_ranked_games(heading, selected, _metacritic_year_url(end_year or CURRENT_YEAR, platform) if end_year else _metacritic_all_time_url(), "GamePulse indexed historical data", platform)
        return response + "\n\n*Live Metacritic retrieval was unavailable, so these are clearly labeled indexed historical results rather than a claim of live ranking data.*", results

    url = _metacritic_year_url(end_year or CURRENT_YEAR, platform) if end_year else _metacritic_all_time_url()
    return (f"I couldn't retrieve a verified Metacritic ranking matching all of those filters right now. I won't substitute unrelated games or invent scores. "
            f"[Check Metacritic directly]({url})."), []


def _is_year_ranking_query(text):
    low = text.lower()
    return bool(re.search(r"\b(best|top|highest rated|highest-rated|rankings?|metacritic|scores?)\b", low))


def _last_titles_from_history(history, state):
    titles = state.get("last_results", []) if state else []
    if titles:
        return titles
    for msg in reversed(history):
        if msg.get("role") != "assistant":
            continue
        names = re.findall(r"\*\*(?:\d+\.\s*)?([^*]+?)\*\*", msg.get("content", ""))
        if names:
            return [n.strip() for n in names[:10]]
    return []


def _general_recommendations(text, mem):
    platform = _extract_platform(text) or (mem.get("platforms") or [None])[0]
    preferred = set(mem.get("favorite_genres") or [])
    disliked = set(mem.get("disliked_genres") or [])

    candidates = []
    for arch in ALL_ARCHETYPES:
        arch_text = (arch.get("title", "") + " " + arch.get("description", "")).lower()
        score = 1
        for genre in preferred:
            if genre in arch_text:
                score += 4
        for g in arch.get("games", []):
            if platform and not any(platform.lower() in str(p).lower() or any(a in str(p).lower() for a in PLATFORM_ALIASES.get(platform, [])) for p in g.get("platforms", [])):
                continue
            if any(d in arch_text or d in g.get("desc", "").lower() for d in disliked):
                continue
            candidates.append((score, g, arch))

    if not candidates:
        return None, []
    candidates.sort(key=lambda x: (-x[0], -int(x[1].get("score") or 0), x[1].get("title", "").lower()))
    seen = set()
    picks = []
    for item in candidates:
        title = item[1].get("title", "")
        if title.lower() in seen:
            continue
        seen.add(title.lower())
        picks.append(item)
        if len(picks) >= 5:
            break
    if not picks:
        return None, []

    lines = ["🎮 **Pulsar Recommendations**", ""]
    if platform:
        lines.append(f"**Platform:** {platform.upper()}")
    if preferred:
        lines.append(f"**Based on:** {', '.join(sorted(preferred))}")
    lines.append("")
    results = []
    for i, (_, g, arch) in enumerate(picks, 1):
        lines.append(f"**{i}. {g['title']}** — **Metacritic {g.get('score', 'N/A')}**")
        lines.append(f"- **Genre:** {arch.get('title', 'Gaming')}")
        lines.append(f"- **Platforms:** {', '.join(g.get('platforms', []))}")
        lines.append(f"- {g.get('desc', '')}")
        lines.append(f"- [Metacritic page]({_metacritic_game_url(g['title'])})")
        lines.append("")
        results.append(g["title"])
    return "\n".join(lines).strip(), results


def _recommend_from_preferences(text, mem):
    low = text.lower()
    target_platform = _extract_platform(text) or (mem.get("platforms") or [None])[0]
    favorite_genres = mem.get("favorite_genres") or []
    disliked_genres = mem.get("disliked_genres") or []

    like_match = re.search(r"(?:games like|similar to|fans of)\s+(.+)$", text, flags=re.I)
    resolved_target = find_game_across_databases(like_match.group(1).strip(" ?")) if like_match else None

    candidates = []
    for arch in ALL_ARCHETYPES:
        score = 0
        keywords = arch.get("keywords", [])
        if any(k in low for k in keywords):
            score += 5
        if resolved_target:
            target_text = (resolved_target.get("genre", "") + " " + resolved_target.get("desc", "")).lower()
            if any(k in target_text or k in arch.get("title", "").lower() for k in keywords):
                score += 6
            if resolved_target.get("genre") and resolved_target.get("genre").lower() in arch.get("title", "").lower():
                score += 4
        for genre in favorite_genres:
            if genre in arch.get("title", "").lower() or genre in arch.get("description", "").lower():
                score += 2
        if score:
            for g in arch.get("games", []):
                candidates.append((score, g, arch))
    if not candidates:
        return None, []

    ranked = []
    for base_score, game, arch in candidates:
        if target_platform and not any(target_platform.lower() in p.lower() or any(a in p.lower() for a in PLATFORM_ALIASES.get(target_platform, [])) for p in game.get("platforms", [])):
            base_score -= 3
        if any(d in game.get("desc", "").lower() or d in arch.get("title", "").lower() for d in disliked_genres):
            base_score -= 5
        ranked.append((base_score, game, arch))
    ranked.sort(key=lambda x: (-x[0], -int(x[1].get("score", 0))))

    lines = ["🎮 **Pulsar Recommendations Based on Your Current Preferences**", ""]
    if target_platform:
        lines.append(f"**Platform:** {target_platform.upper()}")
    if favorite_genres:
        lines.append(f"**Genres you like:** {', '.join(favorite_genres)}")
    if disliked_genres:
        lines.append(f"**Genres to avoid:** {', '.join(disliked_genres)}")
    lines.append("")
    results = []
    for i, (_, g, arch) in enumerate(ranked[:5], 1):
        lines.append(f"**{i}. {g['title']}** — **Metacritic {g['score']}**")
        lines.append(f"- **Genre:** {arch['title']}")
        lines.append(f"- **Platforms:** {', '.join(g['platforms'])}")
        lines.append(f"- {g['desc']}")
        lines.append("")
        results.append(g["title"])
    return "\n".join(lines), results


def _game_response(game, user_text, session_memory):
    title = game["title"]
    lines = [f"🎮 **{title}**", ""]
    lines.append(f"- **Metacritic:** **{game.get('score', 'N/A')}/100**")
    lines.append(f"- **Release year:** {game.get('year', 'N/A')}")
    lines.append(f"- **Platforms:** {game.get('platforms', 'N/A')}")
    if game.get("genre"):
        lines.append(f"- **Genre:** {game.get('genre')}")
    if game.get("desc"):
        lines.append(f"- **Overview:** {game.get('desc')}")
    lines.append(f"- [Metacritic page]({_metacritic_game_url(title)})")

    reviews = get_articles(search=title, limit=5)
    if reviews:
        lines.append("")
        lines.append("**Relevant GamePulse coverage:**")
        for r in reviews[:3]:
            lines.append(f"- [{r['title']}]({r['link']}) — {r['source']} ({r['published']})")
    return "\n".join(lines), [title]


def _comparison_response(a, b):
    lines = [f"⚔️ **{a['title']} vs. {b['title']}**", "", "| Metric | First game | Second game |", "|---|---|---|",
             f"| Metacritic | **{a.get('score', 'N/A')}** | **{b.get('score', 'N/A')}** |",
             f"| Year | {a.get('year', 'N/A')} | {b.get('year', 'N/A')} |",
             f"| Genre | {a.get('genre', 'N/A')} | {b.get('genre', 'N/A')} |",
             f"| Platforms | {a.get('platforms', 'N/A')} | {b.get('platforms', 'N/A')} |", "",
             f"**{a['title']}:** {a.get('desc', '')}",
             f"**{b['title']}:** {b.get('desc', '')}", "",
             f"[Metacritic — {a['title']}]({_metacritic_game_url(a['title'])}) · [Metacritic — {b['title']}]({_metacritic_game_url(b['title'])})"]
    return "\n".join(lines), [a["title"], b["title"]]


def call_groq_api(messages, memory=None, grounded_context=""):
    if not GROQ_API_KEY:
        return None
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        system_prompt = (
            "You are Pulsar, a gaming-only AI concierge. Answer naturally and quickly. "
            "Do not invent Metacritic scores, review dates, release dates, platforms, games, or citations. "
            "When the supplied facts do not support a claim, say that the data is unavailable rather than guessing. "
            "Use the supplied grounded context as the factual source of truth. User preferences are session-scoped. "
            "You may provide general gaming explanations, but never present uncertain specifics as fact. "
            "Do not repeat the same response verbatim when a follow-up changes the question. "
            "Be concise unless the user asks for detail. Use Markdown.\n\n"
            f"SESSION MEMORY:\n{_memory_summary(memory or {})}\n\n"
            f"GROUNDED DATA:\n{grounded_context[:12000]}"
        )
        groq_messages = [{"role": "system", "content": system_prompt}]
        for m in messages[-8:]:
            role = m.get("role", "user")
            if role not in {"user", "assistant"}:
                continue
            groq_messages.append({"role": role, "content": str(m.get("content", ""))[:5000]})
        payload = {
            "model": GROQ_MODEL,
            "messages": groq_messages,
            "temperature": 0.2,
            "max_tokens": 650,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
                "User-Agent": "GamePulseAI/4.0",
            },
        )
        with urllib.request.urlopen(req, timeout=2.2) as response:
            data = json.loads(response.read().decode("utf-8"))
        reply = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        return reply or None
    except Exception:
        return None


def handle_pulsar_chat(messages, user_id=None):
    try:
        _ = get_articles(limit=1)
    except sqlite3.OperationalError:
        init_db()
    if not messages:
        return ("Hi! I'm Pulsar, your Gaming-Focused AI. Ask me about any game, any release year, rankings, comparisons, reviews, recommendations, current gaming news, or your session preferences.", [])

    session_id = user_id or "pulsar_session_anonymous"
    state = _get_pulsar_session(session_id)
    current_msg = str(messages[-1].get("content", "")).strip()
    history = messages[:-1]
    lower_q = current_msg.lower()
    mem = _session_memory(session_id)

    changes = _extract_preferences(current_msg)
    _apply_preferences(session_id, changes)
    mem = _session_memory(session_id)

    if any(k in lower_q for k in ["forget everything", "forget all", "clear memory", "reset preferences", "forget my preferences", "forget me"]):
        _session_clear(session_id)
        state = _get_pulsar_session(session_id)
        return "🧹 **Session memory cleared.** I won't use previously stored gaming preferences for the rest of this session.", []

    if any(k in lower_q for k in ["what do you remember", "what do you know about me", "my preferences", "show my preferences", "remember me"]):
        return f"🧠 **What Pulsar remembers in this session**\n\n{_memory_summary(mem)}", []

    explicit_remember = any(k in lower_q for k in ["remember that", "remember i", "remember my"])
    query_markers = ["best", "top", "recommend", "recommendation", "what", "which", "review", "score", "compare", "versus", " vs ", "latest", "news", "rank", "games like", "what should i play"]
    memory_only = not any(k in lower_q for k in query_markers)
    if explicit_remember and changes and memory_only:
        return f"💾 **Saved for this Pulsar session.**\n\n{_memory_summary(mem)}", []
    if changes and memory_only:
        return f"🧠 **Got it — I’ll keep that in mind for this Pulsar session.**\n\n{_memory_summary(mem)}", []

    last_results = _last_titles_from_history(history, state)
    ordinal_match = re.search(r"\b(?:tell me more about|more info on|details on|tell me about|what about)\s+(?:#|number\s+)?(\d+|first|second|third|fourth|fifth)\b", lower_q)
    if ordinal_match and last_results:
        idx_map = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5}
        idx = idx_map.get(ordinal_match.group(1), int(ordinal_match.group(1)) if ordinal_match.group(1).isdigit() else 0)
        if 1 <= idx <= len(last_results):
            game = find_game_across_databases(last_results[idx - 1])
            if game:
                reply, results = _game_response(game, current_msg, mem)
                state["last_results"] = results
                return reply, results

    platform = _extract_platform(current_msg)
    is_filter = any(k in lower_q for k in ["which of those", "are any of those", "what about that one", "filter", "available on", "playable on", "on pc", "on switch", "on ps5", "on xbox"])
    if platform and is_filter and last_results:
        subset = []
        for name in last_results:
            g = find_game_across_databases(name)
            if not g:
                continue
            aliases = PLATFORM_ALIASES.get(platform, [platform])
            if any(alias in g.get("platforms", "").lower() for alias in aliases):
                subset.append(g)
        if subset:
            lines = [f"🎮 **From the previous list, these are available on {platform.upper()}:**", ""]
            results = []
            for i, g in enumerate(subset, 1):
                lines.append(f"**{i}. {g['title']}** — **Metacritic {g['score']}**")
                lines.append(f"- {g['platforms']} • {g['genre']}")
                lines.append("")
                results.append(g["title"])
            state["last_results"] = results
            return "\n".join(lines), results
        return f"None of the games in the previous list have a verified **{platform.upper()}** listing in my indexed data. I won't guess.", []

    vs_match = re.search(r"(.+?)\s+(?:vs\.?|versus|compared to|against)\s+(.+)", current_msg, flags=re.I)
    if vs_match:
        a = find_game_across_databases(vs_match.group(1).strip())
        b = find_game_across_databases(vs_match.group(2).strip())
        if a and b:
            reply, results = _comparison_response(a, b)
            state["last_results"] = results
            return reply, results

    if _is_ranking_intent(current_msg):
        ranking_filters = _ranking_filters(current_msg, mem)
        if not any(k in lower_q for k in ["games like", "similar to", "fans of"]):
            reply, results = get_filtered_ranking_response(ranking_filters)
            state["last_results"] = results
            state["last_query"] = current_msg
            return reply, results

    game = _find_explicit_game_in_text(current_msg)

    if not game:
        if any(k in lower_q for k in ["review ", "about ", "tell me about ", "how is ", "score for ", "metacritic score for ", "is "]):
            candidate = re.sub(r"^(review|about|tell me about|how is|score for|metacritic score for|is)\s+", "", current_msg, flags=re.I).strip(" ?")
            if candidate:
                game = find_game_across_databases(candidate)

    if game:
        if any(term in lower_q for term in ["developer", "developed", "publisher", "release date", "when did", "who made"]):
            return (f"I have the verified indexed facts for **{game['title']}** — its Metacritic score, year, platforms, genre, and overview — "
                    "but developer/publisher metadata is not present in my grounded record, so I won't guess. "
                    f"[Open its Metacritic page]({_metacritic_game_url(game['title'])}) for the authoritative details.", [game['title']])
        reply, results = _game_response(game, current_msg, mem)
        state["last_results"] = results
        return reply, results

    if any(k in lower_q for k in ["recommend", "recommendations", "what should i play", "suggest a game", "games like", "similar to", "i like"]):
        reply, results = _recommend_from_preferences(current_msg, mem)
        if not reply:
            reply, results = _general_recommendations(current_msg, mem)
        if reply:
            state["last_results"] = results
            return reply, results

    if any(k in lower_q for k in ["latest news", "latest gaming news", "what's new", "whats new", "today's news", "recent gaming news", "recent stories", "articles posted today"]):
        articles = get_articles(limit=8)
        lines = ["📰 **Latest Gaming Coverage in GamePulse**", ""]
        results = []
        for i, article in enumerate(articles[:8], 1):
            lines.append(f"**{i}. [{article['title']}]({article['link']})**")
            lines.append(f"- {article['source']} • {article['published']} • #{article['category']}")
            if article.get("summary"):
                lines.append(f"- {article['summary'][:220]}")
            lines.append("")
            results.append(article["title"])
        state["last_results"] = results
        return "\n".join(lines), results

    grounded = []
    if mem:
        grounded.append("SESSION MEMORY:\n" + _memory_summary(mem))
    if game:
        grounded.append(json.dumps(game))
    else:
        recent = _local_year_games(CURRENT_YEAR)[:8]
        if recent:
            grounded.append("INDEXED CURRENT-YEAR DATA:\n" + json.dumps(recent))
    if last_results:
        grounded.append("LAST RESULT TITLES:\n" + json.dumps(last_results))
    grounded_context = "\n\n".join(grounded)
    groq_reply = call_groq_api(messages, memory=mem, grounded_context=grounded_context)
    if groq_reply:
        state["last_query"] = current_msg
        return groq_reply, []

    return (
        "I don't have enough verified gaming data to answer that accurately right now, and I won't make up a game, score, release date, or review. "
        "Try a specific game, a release year (for example **1999**), a ranking request, a comparison, a recommendation request, or current gaming news.",
        [],
    )



HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>GamePulse AI — Video Game News & Review Digest</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-dark: #07090e;
      --bg-surface: #0d111a;
      --bg-card: #131926;
      --bg-card-hover: #192233;
      --border: #232d42;
      --border-focus: #3b82f6;
      --accent: #ff4466;
      --accent-glow: rgba(255, 68, 102, 0.35);
      --primary: #3b82f6;
      --text-main: #f1f5f9;
      --text-muted: #94a3b8;
      --font-sans: 'Plus Jakarta Sans', system-ui, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg-dark);
      color: var(--text-main);
      font-family: var(--font-sans);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      line-height: 1.6;
    }

    header {
      background: rgba(13, 17, 26, 0.85);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border);
      position: sticky;
      top: 0;
      z-index: 100;
    }
    .header-top {
      max-width: 1280px;
      margin: 0 auto;
      padding: 16px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .logo-container {
      display: flex;
      align-items: center;
      gap: 12px;
      text-decoration: none;
    }
    .logo-badge {
      background: linear-gradient(135deg, var(--accent), #ff6b8b);
      color: #fff;
      font-weight: 800;
      font-size: 1.1rem;
      padding: 6px 12px;
      border-radius: 8px;
      box-shadow: 0 4px 14px var(--accent-glow);
    }
    .logo-text {
      font-size: 1.4rem;
      font-weight: 800;
      letter-spacing: -0.5px;
      color: #fff;
    }
    .nav-links {
      display: flex;
      gap: 20px;
      list-style: none;
    }
    .nav-links a {
      color: var(--text-muted);
      text-decoration: none;
      font-weight: 600;
      font-size: 0.95rem;
      transition: color 0.2s;
    }
    .nav-links a:hover, .nav-links a.active {
      color: var(--accent);
    }

    .tag-bar-wrap {
      border-top: 1px solid rgba(255,255,255,0.05);
      background: rgba(7, 9, 14, 0.6);
    }
    .tag-bar {
      max-width: 1280px;
      margin: 0 auto;
      padding: 10px 24px;
      display: flex;
      gap: 10px;
      overflow-x: auto;
      scrollbar-width: none;
    }
    .tag-bar::-webkit-scrollbar { display: none; }
    .tag-pill {
      background: var(--bg-surface);
      border: 1px solid var(--border);
      color: var(--text-muted);
      padding: 6px 14px;
      border-radius: 20px;
      font-size: 0.85rem;
      font-weight: 600;
      text-decoration: none;
      white-space: nowrap;
      transition: all 0.2s;
    }
    .tag-pill:hover, .tag-pill.active {
      background: var(--border);
      color: #fff;
      border-color: var(--text-muted);
    }

    .container {
      max-width: 1280px;
      margin: 0 auto;
      padding: 32px 24px;
      flex: 1;
      width: 100%;
    }

    .search-bar-wrap {
      display: flex;
      gap: 12px;
      margin-bottom: 24px;
    }
    .search-input {
      flex: 1;
      background: var(--bg-surface);
      border: 1px solid var(--border);
      color: #fff;
      padding: 12px 18px;
      border-radius: 10px;
      font-size: 1rem;
      font-family: inherit;
      outline: none;
      transition: border-color 0.2s, box-shadow 0.2s;
    }
    .search-input:focus {
      border-color: var(--border-focus);
      box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
    }
    .search-btn {
      background: var(--primary);
      color: #fff;
      border: none;
      padding: 0 24px;
      border-radius: 10px;
      font-weight: 700;
      cursor: pointer;
      transition: opacity 0.2s;
    }
    .search-btn:hover { opacity: 0.9; }

    /* Layout Toggle Controls */
    .view-controls {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 8px;
      margin-bottom: 20px;
    }
    .view-label {
      font-size: 0.85rem;
      color: var(--text-muted);
      margin-right: 4px;
    }
    .view-toggle-btn {
      background: var(--bg-card);
      border: 1px solid var(--border);
      color: var(--text-muted);
      padding: 6px 14px;
      border-radius: 6px;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s ease;
    }
    .view-toggle-btn:hover {
      border-color: var(--accent);
      color: var(--text-main);
    }
    .view-toggle-btn.active {
      background: var(--accent);
      border-color: var(--accent);
      color: #ffffff;
      box-shadow: 0 2px 8px var(--accent-glow);
    }

    /* Grid vs List layouts */
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(330px, 1fr));
      gap: 24px;
    }
    .grid.list-view {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .card {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 12px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
    }
    .card:hover {
      transform: translateY(-4px);
      border-color: rgba(255,255,255,0.2);
      box-shadow: 0 12px 24px rgba(0,0,0,0.5);
    }
    .card-thumb {
      width: 100%;
      height: 180px;
      object-fit: cover;
      background: #000;
    }
    .card-body {
      padding: 18px;
      flex: 1;
      display: flex;
      flex-direction: column;
    }
    .card-meta {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
    }
    .badge {
      font-size: 0.75rem;
      font-weight: 800;
      padding: 3px 8px;
      border-radius: 4px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .badge-REVIEW { background: #8b5cf6; color: #fff; }
    .badge-TRAILER { background: #ec4899; color: #fff; }
    .badge-UPDATE { background: #10b981; color: #fff; }
    .badge-INDUSTRY { background: #3b82f6; color: #fff; }
    .badge-RUMOR { background: #f59e0b; color: #000; }
    .badge-INDIE { background: #06b6d4; color: #000; }

    .card-score {
      font-family: var(--font-mono);
      font-size: 0.85rem;
      font-weight: 700;
      color: #10b981;
      background: rgba(16, 185, 129, 0.1);
      padding: 2px 6px;
      border-radius: 4px;
      border: 1px solid rgba(16, 185, 129, 0.2);
    }
    .card-title {
      font-size: 1.15rem;
      font-weight: 700;
      margin-bottom: 8px;
      line-height: 1.4;
    }
    .card-title a {
      color: #fff;
      text-decoration: none;
      transition: color 0.2s;
    }
    .card-title a:hover {
      color: var(--accent);
    }
    .card-summary {
      color: var(--text-muted);
      font-size: 0.9rem;
      margin-bottom: 16px;
      flex: 1;
      line-height: 1.5;
    }
    .card-footer {
      display: flex;
      justify-content: space-between;
      color: rgba(255,255,255,0.4);
      font-size: 0.8rem;
      border-top: 1px solid rgba(255,255,255,0.05);
      padding-top: 12px;
    }

    /* List View Specific Styling */
    .grid.list-view .card {
      flex-direction: row;
      min-height: 160px;
    }
    .grid.list-view .card-thumb {
      width: 260px;
      min-width: 260px;
      height: 100%;
    }
    .grid.list-view .card-body {
      flex: 1;
      justify-content: space-between;
    }
    @media (max-width: 768px) {
      .grid.list-view .card {
        flex-direction: column;
        min-height: auto;
      }
      .grid.list-view .card-thumb {
        width: 100%;
        height: 180px;
      }
    }

    /* Floating Pulsar Trigger */
    .pulsar-fab {
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 9999;
      background: linear-gradient(135deg, var(--accent), #ff6b8b);
      color: #fff;
      border: none;
      border-radius: 50px;
      padding: 14px 22px;
      font-size: 0.95rem;
      font-weight: 700;
      cursor: pointer;
      box-shadow: 0 8px 24px var(--accent-glow);
      display: flex;
      align-items: center;
      gap: 8px;
      transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s ease;
    }
    .pulsar-fab:hover {
      transform: translateY(-3px) scale(1.04);
      box-shadow: 0 12px 30px rgba(255, 68, 102, 0.6);
    }

    /* Pulsar Drawer / Modal */
    .pulsar-modal {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.7);
      backdrop-filter: blur(8px);
      z-index: 10000;
      align-items: flex-end;
      justify-content: flex-end;
      padding: 24px;
    }
    .pulsar-modal.active {
      display: flex;
    }
    .pulsar-window {
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 16px;
      width: 100%;
      max-width: 580px;
      height: 640px;
      display: flex;
      flex-direction: column;
      box-shadow: 0 20px 40px rgba(0,0,0,0.8);
      overflow: hidden;
      animation: slideUp 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }
    @keyframes slideUp {
      from { transform: translateY(20px); opacity: 0; }
      to { transform: translateY(0); opacity: 1; }
    }
    .pulsar-header {
      padding: 16px 20px;
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: rgba(255,255,255,0.02);
    }
    .pulsar-title {
      font-weight: 800;
      font-size: 1.1rem;
      display: flex;
      align-items: center;
      gap: 8px;
      color: #fff;
    }
    .pulsar-close {
      background: none;
      border: none;
      color: var(--text-muted);
      font-size: 1.5rem;
      cursor: pointer;
      line-height: 1;
    }
    .pulsar-close:hover { color: #fff; }

    .pulsar-messages {
      flex: 1;
      padding: 20px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .pulsar-msg {
      max-width: 88%;
      padding: 12px 16px;
      border-radius: 12px;
      font-size: 0.92rem;
      line-height: 1.5;
      word-break: break-word;
    }
    .pulsar-msg-bot {
      background: var(--bg-card);
      border: 1px solid var(--border);
      color: var(--text-main);
      align-self: flex-start;
    }
    .pulsar-msg-user {
      background: var(--accent);
      color: #fff;
      align-self: flex-end;
    }
    .pulsar-msg-bot.loading {
      color: var(--text-muted);
      font-style: italic;
      animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
      0%, 100% { opacity: 0.6; }
      50% { opacity: 1; }
    }

    .pulsar-quick-prompts {
      padding: 8px 16px;
      background: rgba(0,0,0,0.2);
      display: flex;
      gap: 8px;
      overflow-x: auto;
      scrollbar-width: none;
    }
    .pulsar-quick-prompts::-webkit-scrollbar { display: none; }
    .quick-chip {
      background: var(--bg-card);
      border: 1px solid var(--border);
      color: var(--text-muted);
      padding: 5px 12px;
      border-radius: 16px;
      font-size: 0.78rem;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.2s;
    }
    .quick-chip:hover {
      background: var(--border);
      color: #fff;
      border-color: var(--accent);
    }

    .pulsar-footer {
      padding: 16px;
      border-top: 1px solid var(--border);
      display: flex;
      gap: 10px;
      background: #0d121c;
    }
    .pulsar-input {
      flex: 1;
      background: var(--bg-card);
      border: 1px solid var(--border);
      color: #fff;
      padding: 12px 16px;
      border-radius: 10px;
      font-size: 0.95rem;
      font-family: inherit;
      outline: none;
    }
    .pulsar-input:focus {
      border-color: var(--accent);
    }
    .pulsar-send {
      background: var(--accent);
      color: #fff;
      border: none;
      padding: 0 20px;
      border-radius: 10px;
      font-weight: 700;
      cursor: pointer;
      transition: opacity 0.2s;
    }
    .pulsar-send:hover { opacity: 0.9; }

    footer {
      border-top: 1px solid var(--border);
      padding: 24px;
      font-size: 0.85rem;
      color: var(--text-muted);
      text-align: center;
    }
  </style>
</head>
<body>

  <header>
    <div class="header-top">
      <a href="/" class="logo-container">
        <span class="logo-text">GAME<span style="color: var(--accent);">PULSE</span></span>
      </a>
      <ul class="nav-links">
        <li><a href="/" class="__ACTIVE_ALL__">All News</a></li>
        <li><a href="/?tag=REVIEW" class="__ACTIVE_REVIEW__">Reviews</a></li>
        <li><a href="/?tag=TRAILER" class="__ACTIVE_TRAILER__">Trailers</a></li>
        <li><a href="/?tag=UPDATE" class="__ACTIVE_UPDATE__">Patches & DLC</a></li>
        <li><a href="/?tag=INDUSTRY" class="__ACTIVE_INDUSTRY__">Industry</a></li>
      </ul>
    </div>
    <div class="tag-bar-wrap">
      <div class="tag-bar">
        <a href="/" class="tag-pill __ACTIVE_ALL__">All Coverage</a>
        <a href="/?tag=UPDATE" class="tag-pill __ACTIVE_UPDATE__">Patches & Expansions</a>
        <a href="/?tag=INDUSTRY" class="tag-pill __ACTIVE_INDUSTRY__">Industry & Studios</a>
        <a href="/?tag=TRAILER" class="tag-pill __ACTIVE_TRAILER__">Trailers & Reveals</a>
        <a href="/?tag=REVIEW" class="tag-pill __ACTIVE_REVIEW__">Reviews & Scores</a>
        <a href="/?tag=RUMOR" class="tag-pill __ACTIVE_RUMOR__">Rumors & Leaks</a>
        <a href="/?tag=INDIE" class="tag-pill __ACTIVE_INDIE__">Indie & Mods</a>
      </div>
    </div>
  </header>

  <main class="container">
    <form class="search-bar-wrap" method="GET" action="/">
      <input type="text" name="q" class="search-input" placeholder="Search news, game guides, reviews, patches..." value="__SEARCH_QUERY__">
      <button type="submit" class="search-btn">Search</button>
    </form>

    <div class="view-controls">
      <span class="view-label">Feed Layout:</span>
      <button id="gridBtn" class="view-toggle-btn active" onclick="setFeedView('grid')" title="Switch to Grid View">⊞ Grid</button>
      <button id="listBtn" class="view-toggle-btn" onclick="setFeedView('list')" title="Switch to List View">☰ List</button>
    </div>

    <div class="grid" id="articlesGrid">
      __ARTICLE_CARDS__
    </div>
  </main>

  <!-- Pulsar Floating Button (Bottom-Right Docked) -->
  <button class="pulsar-fab" onclick="openPulsar()">
    ⚡ Ask Pulsar
  </button>

  <!-- Pulsar Modal Drawer -->
  <div class="pulsar-modal" id="pulsarModal">
    <div class="pulsar-window">
      <div class="pulsar-header">
        <div class="pulsar-title">
          <span>🎮</span> Pulsar AI Gaming Concierge
        </div>
        <button class="pulsar-close" onclick="closePulsar()">&times;</button>
      </div>
      <div class="pulsar-messages" id="pulsarMessages">
        <div class="pulsar-msg pulsar-msg-bot">
          <strong>Hi! I'm Pulsar, your Gaming-Focused AI.</strong><br><br>
          I use verified Metacritic rankings across all years (1990–2026), live news feeds, your session context, and saved preferences to answer factually and instantly.<br><br>
          Ask for any year (e.g. <em>"best game from 1999"</em> or <em>"top games of 2004"</em>), decade rankings, game reviews, head-to-head comparisons, or personalized recommendations!
        </div>
      </div>
      <div class="pulsar-quick-prompts">
        <span class="quick-chip" onclick="sendPrompt('best game from 1999')">🕹️ Best Game from 1999</span>
        <span class="quick-chip" onclick="sendPrompt('best rated games of the last decade')">🏆 Best Games of the Decade</span>
        <span class="quick-chip" onclick="sendPrompt('highest rated games of all time')">👑 All-Time Greatest</span>
        <span class="quick-chip" onclick="sendPrompt('Articles posted today')">📰 Articles posted today</span>
        <span class="quick-chip" onclick="sendPrompt('show me 2026 games rated 80+ or more')">🌟 2026 Games (80+)</span>
        <span class="quick-chip" onclick="sendPrompt('⚔️ Action RPGs & Diablo')">⚔️ Action RPGs & Diablo</span>
        <span class="quick-chip" onclick="sendPrompt('I like games like Prototype 2')">🧬 Like Prototype 2</span>
      </div>
      <div class="pulsar-footer">
        <input type="text" id="pulsarInput" class="pulsar-input" placeholder="Ask for recommendations, reviews, scores..." onkeydown="handleKeyDown(event)">
        <button class="pulsar-send" onclick="submitMessage()">Send</button>
      </div>
    </div>
  </div>

  <footer>
    <p>© 2026 GamePulse Media Network • Independent Video Game News & Review Digest</p>
  </footer>

  <script>
    let chatHistory = [];
    let userId = null;
    try { userId = sessionStorage.getItem('gp_pulsar_session_id'); } catch (_) {}
    if (!userId) {
      userId = 'pulsar_session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
      try { sessionStorage.setItem('gp_pulsar_session_id', userId); } catch (_) {}
    }

    function setFeedView(mode) {
      const grid = document.getElementById('articlesGrid');
      const gridBtn = document.getElementById('gridBtn');
      const listBtn = document.getElementById('listBtn');
      if (mode === 'list') {
        grid.classList.add('list-view');
        listBtn.classList.add('active');
        gridBtn.classList.remove('active');
        localStorage.setItem('gp_feed_view', 'list');
      } else {
        grid.classList.remove('list-view');
        gridBtn.classList.add('active');
        listBtn.classList.remove('active');
        localStorage.setItem('gp_feed_view', 'grid');
      }
    }

    document.addEventListener('DOMContentLoaded', () => {
      const savedView = localStorage.getItem('gp_feed_view');
      if (savedView === 'list') {
        setFeedView('list');
      }
    });

    function openPulsar() {
      document.getElementById('pulsarModal').classList.add('active');
      document.getElementById('pulsarInput').focus();
    }
    function closePulsar() {
      document.getElementById('pulsarModal').classList.remove('active');
      chatHistory = [];
      try { sessionStorage.removeItem('gp_pulsar_session_id'); } catch (_) {}
      userId = 'pulsar_session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
      try { sessionStorage.setItem('gp_pulsar_session_id', userId); } catch (_) {}
    }
    function handleKeyDown(e) {
      if (e.key === 'Enter') {
        submitMessage();
      }
    }
    function sendPrompt(text) {
      document.getElementById('pulsarInput').value = text;
      submitMessage();
    }

    async function submitMessage() {
      const input = document.getElementById('pulsarInput');
      const text = input.value.trim();
      if (!text) return;

      appendMessage(text, 'user');
      input.value = '';

      chatHistory.push({ role: 'user', content: text });

      const typingId = appendMessage('Pulsar is analyzing live gaming sources...', 'bot', true);

      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 14000);

        const response = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text, history: chatHistory, user_id: userId }),
          signal: controller.signal
        });
        clearTimeout(timeoutId);

        if (!response.ok) {
          throw new Error('HTTP ' + response.status);
        }
        const data = await response.json();
        const reply = data.reply || 'Sorry, I had trouble processing that request.';
        
        chatHistory.push({ role: 'assistant', content: reply });
        updateMessage(typingId, formatMarkdown(reply));
      } catch (err) {
        console.error('Chat error:', err);
        updateMessage(typingId, 'Sorry, something went wrong connecting to Pulsar. Please try again!');
      }
    }

    function appendMessage(text, sender, isLoading=false) {
      const msgs = document.getElementById('pulsarMessages');
      const div = document.createElement('div');
      const id = 'msg-' + Date.now() + '-' + Math.random().toString(36).substr(2, 5);
      div.id = id;
      div.className = 'pulsar-msg ' + (sender === 'user' ? 'pulsar-msg-user' : 'pulsar-msg-bot');
      if (isLoading) {
        div.classList.add('loading');
      }
      div.innerHTML = sender === 'user' ? escapeHtml(text) : formatMarkdown(text);
      msgs.appendChild(div);
      msgs.scrollTop = msgs.scrollHeight;
      return id;
    }

    function updateMessage(id, html) {
      const el = document.getElementById(id);
      if (el) {
        el.classList.remove('loading');
        el.innerHTML = html;
        const msgs = document.getElementById('pulsarMessages');
        msgs.scrollTop = msgs.scrollHeight;
      }
    }

    function escapeHtml(str) {
      return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    function formatMarkdown(text) {
      let html = escapeHtml(text);
      html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
      html = html.replace(/\[([^\]]+)\]\(([^\)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
      html = html.replace(/\n/g, '<br>');
      return html;
    }
  </script>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# HTTP Server & Request Handler
# ---------------------------------------------------------------------------

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class GamePulseHandler(BaseHTTPRequestHandler):
    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.send_header("Connection", "close")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query_params = urllib.parse.parse_qs(parsed.query)

        if path == "/api/metacritic-status":
            host = urllib.parse.urlparse(METACRITIC_API_BASE).hostname or "backend.metacritic.com"
            addresses = _resolve_dns(host)
            key_available = bool(_discover_metacritic_api_key())
            payload = {"host": host, "dns_resolved": bool(addresses), "address_count": len(addresses), "api_key_available": key_available}
            resp_bytes = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(resp_bytes)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(resp_bytes)
            return

        if path == "/api/articles":
            tag = query_params.get("tag", [None])[0]
            search = query_params.get("q", [None])[0]
            articles = get_articles(tag=tag, search=search)
            resp_bytes = json.dumps(articles).encode("utf-8")
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(resp_bytes)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Connection", "close")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(resp_bytes)
            return

        if path == "/api/memory":
            user_id = query_params.get("user_id", [None])[0]
            mem = get_user_memory(user_id) if user_id else {}
            resp_bytes = json.dumps(mem).encode("utf-8")
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(resp_bytes)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(resp_bytes)
            return

        if path == "/" or path == "" or path == "/index.html":
            tag = query_params.get("tag", [None])[0]
            search = query_params.get("q", [None])[0]
            articles = get_articles(tag=tag, search=search)

            active_tag = (tag.upper() if tag else "ALL")
            active_map = {
                "active_all": "active" if active_tag == "ALL" else "",
                "active_review": "active" if active_tag == "REVIEW" else "",
                "active_update": "active" if active_tag == "UPDATE" else "",
                "active_trailer": "active" if active_tag == "TRAILER" else "",
                "active_industry": "active" if active_tag == "INDUSTRY" else "",
                "active_rumor": "active" if active_tag == "RUMOR" else "",
                "active_indie": "active" if active_tag == "INDIE" else "",
                "search_query": search or ""
            }

            cards_html = ""
            if not articles:
                cards_html = """
                <div style="grid-column: 1 / -1; text-align: center; padding: 60px 20px; color: var(--text-muted);">
                  <h3>No stories in this section yet.</h3>
                  <p>Check back shortly as new live feeds are indexed.</p>
                </div>
                """
            else:
                for a in articles:
                    score_span = f'<span class="card-score">{a["score"]}</span>' if a["score"] else ""
                    pub_date = a["published"][:10] if a.get("published") else ""
                    cards_html += f"""
                    <article class="card">
                      <img class="card-thumb" src="{a['image_url']}" alt="{a['title']}" loading="lazy" onerror="this.src='https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=600&q=80'">
                      <div class="card-body">
                        <div class="card-meta">
                          <span class="badge badge-{a['category']}">{a['category']}</span>
                          {score_span}
                        </div>
                        <h2 class="card-title">
                          <a href="{a['link']}" target="_blank" rel="noopener">{a['title']}</a>
                        </h2>
                        <p class="card-summary">{a['summary']}</p>
                        <div class="card-footer">
                          <span>{a['source']}</span>
                          <span>{pub_date}</span>
                        </div>
                      </div>
                    </article>
                    """

            page_html = HTML_TEMPLATE
            page_html = page_html.replace("__ARTICLE_CARDS__", cards_html)
            page_html = page_html.replace("__ACTIVE_ALL__", active_map["active_all"])
            page_html = page_html.replace("__ACTIVE_REVIEW__", active_map["active_review"])
            page_html = page_html.replace("__ACTIVE_UPDATE__", active_map["active_update"])
            page_html = page_html.replace("__ACTIVE_TRAILER__", active_map["active_trailer"])
            page_html = page_html.replace("__ACTIVE_INDUSTRY__", active_map["active_industry"])
            page_html = page_html.replace("__ACTIVE_RUMOR__", active_map["active_rumor"])
            page_html = page_html.replace("__ACTIVE_INDIE__", active_map["active_indie"])
            page_html = page_html.replace("__SEARCH_QUERY__", active_map["search_query"])
            
            resp_bytes = page_html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(resp_bytes)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(resp_bytes)
            return

        self.send_response(404)
        self.send_header("Content-Length", "13")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(b"404 Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/chat":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                messages = data.get("history", [])
                user_msg = data.get("message", "")
                user_id = data.get("user_id")
                
                if not messages and user_msg:
                    messages = [{"role": "user", "content": user_msg}]
                elif messages and user_msg and (not messages or messages[-1].get("content") != user_msg):
                    messages.append({"role": "user", "content": user_msg})

                result = handle_pulsar_chat(messages, user_id=user_id)
                reply = result[0] if isinstance(result, tuple) else result
            except Exception as e:
                reply = "I encountered an error analyzing your request. Please try again!"

            resp_bytes = json.dumps({"reply": reply}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(resp_bytes)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Connection", "close")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(resp_bytes)
            return

        if parsed.path == "/api/memory":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                user_id = data.get("user_id")
                key = data.get("key")
                val = data.get("value")
                if user_id and key:
                    set_user_memory(user_id, key, val)
                resp_bytes = json.dumps({"status": "ok"}).encode("utf-8")
            except Exception:
                resp_bytes = json.dumps({"status": "error"}).encode("utf-8")
                
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(resp_bytes)))
            self.send_header("Connection", "close")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(resp_bytes)
            return

        self.send_response(404)
        self.send_header("Content-Length", "13")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(b"404 Not Found")

# ---------------------------------------------------------------------------
# Main Execution
# ---------------------------------------------------------------------------

def main():
    print("[GamePulse AI] Initializing database...")
    init_db()

    print("[GamePulse AI] Warming Metacritic network/cache in the background...")
    start_metacritic_warmup()

    print("[GamePulse AI] Warming article thumbnails in the background...")
    start_thumbnail_warmup()

    print("[GamePulse AI] Starting background feed sync worker...")
    start_background_scheduler()

    server = ThreadedHTTPServer(("0.0.0.0", PORT), GamePulseHandler)
    print(f"[GamePulse AI] Server active and listening on port {PORT}...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()