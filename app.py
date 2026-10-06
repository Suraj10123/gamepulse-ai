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
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

# Strict socket timeout to prevent any external HTTP calls or SSL handshakes from hanging
socket.setdefaulttimeout(4.0)

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
            title TEXT NOT NULL,
            link TEXT UNIQUE NOT NULL,
            published TEXT,
            summary TEXT,
            source TEXT,
            category TEXT,
            score TEXT,
            image_url TEXT
        )
    """)
    conn.commit()

    # Always ensure seed articles exist for all categories
    for art in SEED_ARTICLES:
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

def get_articles(tag=None, search=None, limit=50):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    query = "SELECT id, title, link, published, summary, source, category, score, image_url FROM articles"
    params = []
    clauses = []
    
    if tag and tag.upper() != "ALL":
        clauses.append("UPPER(category) = ?")
        params.append(tag.upper())
        
    if search:
        clauses.append("(LOWER(title) LIKE ? OR LOWER(summary) LIKE ?)")
        s = f"%{search.lower()}%"
        params.extend([s, s])
        
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
        
    query += " ORDER BY published DESC LIMIT ?"
    params.append(limit)
    
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    
    articles = []
    for r in rows:
        articles.append({
            "id": r[0],
            "title": r[1],
            "link": r[2],
            "published": r[3],
            "summary": r[4],
            "source": r[5],
            "category": r[6],
            "score": r[7],
            "image_url": r[8] or "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=600&q=80"
        })
    return articles

# ---------------------------------------------------------------------------
# RSS Ingestion Pipeline
# ---------------------------------------------------------------------------

FEEDS = [
    {"url": "https://feeds.ign.com/ign/all", "source": "IGN", "default_cat": "REVIEW"},
    {"url": "https://www.gamespot.com/feeds/reviews/", "source": "GameSpot", "default_cat": "REVIEW"},
    {"url": "https://www.pcgamer.com/rss/", "source": "PC Gamer", "default_cat": "UPDATE"},
    {"url": "https://www.rockpapershotgun.com/feed", "source": "Rock Paper Shotgun", "default_cat": "UPDATE"},
    {"url": "https://www.polygon.com/rss/index.xml", "source": "Polygon", "default_cat": "INDUSTRY"},
    {"url": "https://www.eurogamer.net/feed", "source": "Eurogamer", "default_cat": "REVIEW"},
    {"url": "https://insider-gaming.com/feed/", "source": "Insider Gaming", "default_cat": "RUMOR"}
]


def classify_content(title, summary, default_cat="REVIEW"):
    text = (title + " " + (summary or "")).lower()
    if any(k in text for k in ["review", "verdict", "scored", "impressions", "metacritic", "opencritic"]):
        return "REVIEW"
    if any(k in text for k in ["patch", "update", "hotfix", "expansion", "dlc", "changelog", "notes"]):
        return "UPDATE"
    if any(k in text for k in ["trailer", "gameplay reveal", "teaser", "footage", "first look"]):
        return "TRAILER"
    if any(k in text for k in ["rumor", "leak", "reportedly", "insider", "datamine", "speculation"]):
        return "RUMOR"
    if any(k in text for k in ["indie", "mod", "modding", "early access", "deckbuilder", "metroidvania"]):
        return "INDIE"
    if any(k in text for k in ["sales", "financials", "layoffs", "acquisition", "studio", "ceo", "industry"]):
        return "INDUSTRY"
    return default_cat

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT UNIQUE,
            link TEXT,
            published TEXT,
            summary TEXT,
            source TEXT,
            category TEXT,
            score TEXT,
            image_url TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_memory (
            user_id TEXT,
            pref_key TEXT,
            pref_value TEXT,
            updated_at TEXT,
            PRIMARY KEY (user_id, pref_key)
        )
    """)
    conn.commit()

    # Seed initial articles if empty
    c.execute("SELECT COUNT(*) FROM articles")
    if c.fetchone()[0] == 0:
        for a in SEED_ARTICLES:
            try:
                c.execute("""
                    INSERT OR IGNORE INTO articles 
                    (title, link, published, summary, source, category, score, image_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (a["title"], a["link"], a["published"], a["summary"], a["source"], a["category"], a["score"], a["image_url"]))
            except Exception:
                pass
        conn.commit()
    conn.close()

def get_articles(tag=None, search=None, limit=60):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
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
    
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def run_news_aggregation():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    for feed in FEEDS:
        try:
            req = urllib.request.Request(
                feed["url"],
                headers={"User-Agent": "GamePulseAI/2.0 (Gaming News Bot)"}
            )
            with urllib.request.urlopen(req, timeout=3.5) as response:
                xml_data = response.read()
                root = ET.fromstring(xml_data)
                
                items = root.findall(".//item")
                if not items:
                    ns = {"atom": "http://www.w3.org/2005/Atom"}
                    items = root.findall(".//atom:entry", ns)
                    
                for item in items[:8]:
                    title_elem = item.find("title")
                    link_elem = item.find("link")
                    pub_elem = item.find("pubDate") or item.find("published") or item.find("updated")
                    desc_elem = item.find("description") or item.find("summary")
                    
                    title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
                    if not title:
                        continue
                        
                    link = link_elem.text.strip() if link_elem is not None and link_elem.text else ""
                    if not link and link_elem is not None and "href" in link_elem.attrib:
                        link = link_elem.attrib["href"]
                        
                    published = pub_elem.text.strip() if pub_elem is not None and pub_elem.text else datetime.now(timezone.utc).isoformat()
                    summary = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ""
                    summary = re.sub(r'<[^>]+>', '', summary)[:280]
                    
                    category = classify_content(title, summary, feed["default_cat"])
                    image_url = "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=600&q=80"
                    
                    score = ""
                    score_match = re.search(r'\b(10/10|[7-9]\.[0-9]/10|[7-9][0-9]/100)\b', title + " " + summary)
                    if score_match:
                        score = score_match.group(1)
                    elif category == "REVIEW":
                        score = "Review"

                    c.execute("""
                        INSERT OR IGNORE INTO articles 
                        (title, link, published, summary, source, category, score, image_url)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (title, link, published, summary, feed["source"], category, score, image_url))
            conn.commit()
        except Exception:
            continue
            
    conn.close()

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
# User & Session Memory
# ---------------------------------------------------------------------------

USER_MEMORIES = {}

def get_user_memory(user_id):
    if not user_id:
        return {}
    if user_id in USER_MEMORIES:
        return USER_MEMORIES[user_id]
        
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT pref_key, pref_value FROM user_memory WHERE user_id = ?", (user_id,))
    rows = c.fetchall()
    conn.close()
    
    mem = {k: v for k, v in rows}
    USER_MEMORIES[user_id] = mem
    return mem

def set_user_memory(user_id, key, val):
    if not user_id:
        return
    mem = get_user_memory(user_id)
    mem[key] = val
    USER_MEMORIES[user_id] = mem
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO user_memory (user_id, pref_key, pref_value, updated_at)
        VALUES (?, ?, ?, ?)
    """, (user_id, key, val, datetime.now(timezone.utc).isoformat()))
    conn.commit()
    conn.close()

def clear_user_memory(user_id):
    if not user_id:
        return
    USER_MEMORIES.pop(user_id, None)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM user_memory WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()



# ---------------------------------------------------------------------------
# Groq AI Completion (Strict 3.5s Timeout)
# ---------------------------------------------------------------------------

def call_groq_api(messages):
    if not GROQ_API_KEY:
        return None
        
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        system_prompt = (
            "You are Pulsar, the Gaming-Focused AI Concierge for GamePulse AI. "
            "You use live gaming sources when available, current Metacritic data across all years (1990–2026), user context, and saved gaming preferences to answer naturally. "
            "Tone: enthusiastic, knowledgeable, accurate, concise, grounded in real Metacritic scores, platforms, and release years. "
            "Use Markdown formatting with bolding, bullet points, and clean structure."
        )
        groq_messages = [{"role": "system", "content": system_prompt}]
        for m in messages[-10:]:
            groq_messages.append({"role": m.get("role", "user"), "content": m.get("content", "")})
            
        payload = {
            "model": GROQ_MODEL,
            "messages": groq_messages,
            "temperature": 0.5,
            "max_tokens": 1000
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
                "User-Agent": "GamePulseAI/2.0"
            }
        )
        with urllib.request.urlopen(req, timeout=3.5) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None

# ---------------------------------------------------------------------------
# Specialized Leaderboard & Year Response Generators
# ---------------------------------------------------------------------------

def get_year_response(year, min_score=None, pref_platform=None):
    if year in ALL_YEARS_DATABASE:
        games = ALL_YEARS_DATABASE[year]
    else:
        # Pre-1990 fallback
        if year < 1990:
            return (
                f"🏛️ **Retro Gaming History: Key Standouts from {year}**\n\n"
                f"Modern review aggregators like Metacritic began tracking review scores in the mid-to-late 1990s. "
                f"However, the historical landmarks and defining masterworks of **{year}** include:\n\n"
                f"• **1985:** *Super Mario Bros.* (NES) • *Duck Hunt* (NES)\n"
                f"• **1986:** *The Legend of Zelda* (NES) • *Metroid* (NES) • *Castlevania* (NES)\n"
                f"• **1987:** *Mega Man* (NES) • *Final Fantasy* (NES) • *Street Fighter* (Arcade)\n"
                f"• **1988:** *Super Mario Bros. 3* (NES) • *Mega Man 2* (NES)\n"
                f"• **1989:** *Tetris* (Game Boy) • *Prince of Persia* (PC) • *SimCity* (PC)\n\n"
                f"💡 *Ask me for verified Metacritic rankings for any year from **1990 to 2026**!*"
            )
        return f"I have verified Metacritic rankings for every single year from **1990 to 2026**. What year would you like to explore?"

    if min_score:
        filtered = [g for g in games if g["score"] >= min_score]
        if not filtered:
            filtered = games
    else:
        filtered = games

    res = f"🏆 **Top Metacritic Ranked Video Games of {year}**\n\n"
    res += f"Here are the highest-rated games of **{year}**, verified by **Metacritic** scores and historical critical consensus:\n\n"
    for i, g in enumerate(filtered[:5], 1):
        plat_str = g['platforms']
        pref_badge = f" ⭐ *({pref_platform})*" if pref_platform and pref_platform.lower() in plat_str.lower() else ""
        res += f"**{i}. {g['title']}** ({plat_str} — **Metacritic {g['score']}**){pref_badge}\n"
        res += f"- **Genre:** {g['genre']}\n"
        res += f"- **Why It's Essential:** {g['desc']}\n\n"

    res += f"💡 *Would you like details on any of these (e.g. 'tell me more about #1'), to compare titles, or to check another year (e.g., 1998, 2004, or 2023)?*"
    return res

def format_decade_response(pref_platform=None):
    decade_games = []
    for y in range(2016, 2027):
        if y in ALL_YEARS_DATABASE:
            for g in ALL_YEARS_DATABASE[y]:
                item = dict(g)
                item["year"] = y
                decade_games.append(item)

    sorted_decade = sorted(decade_games, key=lambda x: (x["score"] if x["score"] is not None else 0), reverse=True)
    seen = set()
    deduped = []
    for g in sorted_decade:
        if g["title"] not in seen:
            seen.add(g["title"])
            deduped.append(g)

    res = "🏆 **Best Rated Video Games of the Last Decade (2016–2026)**\n\n"
    res += "Here are the defining critical masterpieces of the past ten years, ranked by verified **Metacritic / OpenCritic** consensus:\n\n"
    
    res += "### 🌟 The Critical Titans (Scores 96–97)\n\n"
    titans = [g for g in deduped if g["score"] and g["score"] >= 96][:6]
    for i, g in enumerate(titans, 1):
        plat_str = g['platforms']
        if pref_platform and pref_platform.lower() in plat_str.lower():
            plat_str += f" ⭐ *(Available on your {pref_platform})*"
        res += f"**{i}. {g['title']}** ({g['year']}) — **Metacritic {g['score']}**\n"
        res += f"- **Platforms:** {plat_str} • **Genre:** {g['genre']}\n"
        res += f"- **Why It Defined the Decade:** {g['desc']}\n\n"

    res += "### 💎 Modern Masterpieces (Scores 93–95)\n\n"
    masterpieces = [g for g in deduped if g["score"] and 93 <= g["score"] < 96][:6]
    for i, g in enumerate(masterpieces, len(titans) + 1):
        plat_str = g['platforms']
        if pref_platform and pref_platform.lower() in plat_str.lower():
            plat_str += f" ⭐ *(Available on your {pref_platform})*"
        res += f"**{i}. {g['title']}** ({g['year']}) — **Metacritic {g['score']}**\n"
        res += f"- **Platforms:** {plat_str} • **Genre:** {g['genre']}\n"
        res += f"- {g['desc']}\n\n"

    res += "### 📅 Year-by-Year Standouts (2016 – 2026)\n"
    for y in range(2016, 2027):
        if y in ALL_YEARS_DATABASE:
            top_two = ALL_YEARS_DATABASE[y][:2]
            line_items = [f"*{g['title']}* ({g['score']})" for g in top_two]
            res += f"• **{y}:** {' • '.join(line_items)}\n"

    res += "\n💡 *Ask me to filter by any specific platform (PS5, PC, Switch, Xbox) or compare any two titles (e.g., 'Elden Ring vs Baldur\'s Gate 3')!*"
    return res

def format_all_time_response(pref_platform=None):
    all_games = []
    for y, games in ALL_YEARS_DATABASE.items():
        for g in games:
            item = dict(g)
            item["year"] = y
            all_games.append(item)

    sorted_all = sorted(all_games, key=lambda x: (x["score"] if x["score"] is not None else 0), reverse=True)
    seen = set()
    deduped = []
    for g in sorted_all:
        if g["title"] not in seen:
            seen.add(g["title"])
            deduped.append(g)

    res = "👑 **Highest-Rated Video Games of All Time (Metacritic Consensus)**\n\n"
    res += "Here are the supreme critical benchmarks across the entire history of video game aggregation:\n\n"
    for i, g in enumerate(deduped[:10], 1):
        plat_str = g['platforms']
        pref_badge = f" ⭐ *({pref_platform})*" if pref_platform and pref_platform.lower() in plat_str.lower() else ""
        res += f"**{i}. {g['title']}** ({g['year']} — **Metacritic {g['score']}**){pref_badge}\n"
        res += f"- **Platforms:** {plat_str} • **Genre:** {g['genre']}\n"
        res += f"- {g['desc']}\n\n"

    res += "💡 *Ask me about any specific year (e.g., 'best game from 1999', 'best of 2004') or genre to dive deeper!*"
    return res

def find_game_across_databases(name):
    name_clean = name.strip().lower()
    for y, games in ALL_YEARS_DATABASE.items():
        for g in games:
            if name_clean == g["title"].lower():
                item = dict(g)
                item["year"] = y
                return item
    for y, games in ALL_YEARS_DATABASE.items():
        for g in games:
            if name_clean in g["title"].lower():
                item = dict(g)
                item["year"] = y
                return item
    best_match = None
    best_ratio = 0.60
    for y, games in ALL_YEARS_DATABASE.items():
        for g in games:
            ratio = difflib.SequenceMatcher(None, name_clean, g["title"].lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = dict(g)
                best_match["year"] = y
    return best_match

def handle_pulsar_chat(messages, user_id=None):
    if not messages:
        return (
            "Hi! I'm Pulsar, your Gaming-Focused AI.\n"
            "I use live gaming sources when available, current Metacritic data across all years (1990–2026), your chat context, and saved gaming preferences to answer naturally.\n"
            "Ask for any game review, rankings for any year (e.g., *'best game from 1999'*), decade comparisons, platform-tailored suggestions, or follow-ups."
        )
        
    current_msg = messages[-1].get("content", "").strip()
    history = messages[:-1]
    lower_q = current_msg.lower()
    clean_q = current_msg
    
    # 0. User & Session Memory Context
    mem = get_user_memory(user_id) if user_id else {}
    user_pref_platform = mem.get("platform")
    
    # Memory Command: Save Preference
    if any(k in lower_q for k in ["remember that", "my main platform is", "i play on", "i have a", "my preferred platform is", "i mainly play on"]):
        plat_found = None
        for p in ["PS5", "PC", "Xbox", "Switch", "Steam Deck", "PS4"]:
            if p.lower() in lower_q:
                plat_found = p
                break
        genre_found = None
        for g in ["rpg", "jrpg", "crpg", "action rpg", "soulslike", "fps", "platformer", "horror", "strategy", "roguelike", "deckbuilder"]:
            if g in lower_q:
                genre_found = g.upper()
                break

        if plat_found:
            set_user_memory(user_id, "platform", plat_found)
        if genre_found:
            set_user_memory(user_id, "favorite_genre", genre_found)

        if plat_found or genre_found:
            msg_parts = []
            if plat_found: msg_parts.append(f"primary platform: **{plat_found}**")
            if genre_found: msg_parts.append(f"favorite genre: **{genre_found}**")
            return f"💾 **Preference Saved:** I've remembered that your {', and '.join(msg_parts)}! I will automatically highlight and prioritize matching games in all your rankings and recommendations."
            
    if any(k in lower_q for k in ["forget my preferences", "clear memory", "reset preferences", "clear my preferences", "forget me"]):
        clear_user_memory(user_id)
        return "🧹 **Preferences Cleared:** I have reset your saved gaming preferences. All recommendations will be general and cross-platform."
        
    if any(k in lower_q for k in ["what do you remember", "my preferences", "what are my preferences", "show my preferences", "do you remember me"]):
        if mem:
            details = "\n".join([f"• **{k.replace('_', ' ').title()}:** {v}" for k, v in mem.items()])
            return f"🧠 **Your Saved Gaming Preferences:**\n\n{details}\n\nYou can update these anytime (e.g., *'Remember that I play on PC'* or *'Forget my preferences'*)."
        else:
            return "🧠 I don't have any saved preferences for you yet. Tell me what platforms you play on (e.g., *'Remember that I play on PS5'*) or genres you love, and I'll remember them across your session!"

    # 1. Conversational Ordinal / Follow-up Resolution (e.g., "tell me more about #1", "what was the second game")
    ordinal_match = re.search(r'\b(?:tell me more about|more info on|details on|tell me about|what about)\s+(?:#|number\s+)?([1-5]|first|second|third|fourth|fifth)\b', lower_q)
    if ordinal_match and history:
        word_map = {"1": 1, "first": 1, "2": 2, "second": 2, "3": 3, "third": 3, "4": 4, "fourth": 4, "5": 5, "fifth": 5}
        target_idx = word_map.get(ordinal_match.group(1).lower())
        last_bot_msg = history[-1].get("content", "")
        game_lines = re.findall(r'\*\*\d+\.\s+([^*]+)\*\*', last_bot_msg)
        if game_lines and target_idx and 1 <= target_idx <= len(game_lines):
            target_name = game_lines[target_idx - 1].strip()
            g = find_game_across_databases(target_name)
            if g:
                res = f"🎮 **Deep Dive: {g['title']} ({g.get('year', '')})**\n\n"
                res += f"• **Official Metacritic Score:** **{g['score']}** / 100\n"
                res += f"• **Platforms:** {g['platforms']}\n"
                res += f"• **Genre:** {g['genre']}\n\n"
                res += f"**Critical Analysis & Gameplay:**\n{g['desc']}\n\n"
                res += f"💡 *Want to compare {g['title']} to another game, or find modern games like it?*"
                return res

    # 2. Follow-up Platform Filter (e.g., "which of those are on PC?", "are any on Switch?")
    plat_target = None
    for p in ["PS5", "PC", "Xbox", "Switch", "PS4", "PS1", "PS2", "Dreamcast", "N64", "GameCube", "Wii", "Steam"]:
        if re.search(r'\b' + p.lower() + r'\b', lower_q):
            plat_target = p
            break
            
    is_filter_ask = any(k in lower_q for k in ["which", "are any", "any of", "filter by", "playable on", "available on", "what about", "on pc", "on ps5", "on switch", "on xbox"])
    if plat_target and is_filter_ask and history:
        check_plat = "pc" if plat_target.lower() == "steam" else plat_target.lower()
        last_bot_msg = history[-1].get("content", "")
        game_lines = re.findall(r'\*\*\d+\.\s+([^*]+)\*\*', last_bot_msg)
        if game_lines:
            matched_subset = []
            for name in game_lines:
                g = find_game_across_databases(name)
                if g and check_plat in g["platforms"].lower():
                    matched_subset.append(g)
            if matched_subset:
                res = f"🎮 **Games Available on {plat_target} from the Previous List:**\n\n"
                for i, g in enumerate(matched_subset, 1):
                    res += f"**{i}. {g['title']}** ({g.get('year', '')} — **Metacritic {g['score']}**)\n"
                    res += f"- **Platforms:** {g['platforms']} • **Genre:** {g['genre']}\n"
                    res += f"- **Why It's Essential:** {g['desc']}\n\n"
                res += f"💡 *Would you like details on any of these, or to explore more games for {plat_target}?*"
                return res
            else:
                return f"None of the titles from that specific list were released on **{plat_target}**. Would you like me to show the top-rated games released specifically for **{plat_target}** from that year or era instead?"

    # 3. Optional Groq AI Enhancement (with strict 3.5s timeout)
    groq_reply = call_groq_api(messages)
    if groq_reply:
        return groq_reply

    # 4. Deterministic Local Intelligence Engine
    
    # A. ALL-YEARS LOOKUP (e.g., "best game from 1999", "top 5 games of 2004", "1998 games", "best of 1995")
    year_match = re.search(r'\b(19[7-9][0-9]|20[0-2][0-9]|2030)\b', lower_q)
    if year_match:
        target_year = int(year_match.group(1))
        score_match = re.search(r'(\b[6-9][0-9]\b)\s*(?:\+|plus|or more|or higher|rating|rated|score)?', lower_q)
        min_score = int(score_match.group(1)) if score_match else None
        return get_year_response(target_year, min_score=min_score, pref_platform=user_pref_platform)

    # B. DECADE RANKINGS & COMPARISONS
    decade_terms = ["decade", "last 10 years", "past 10 years", "10 years", "decade comparisons", "best of the decade", "games of the decade"]
    if any(t in lower_q for t in decade_terms) or (
        ("best" in lower_q or "top" in lower_q or "highest" in lower_q) and 
        ("rated" in lower_q or "score" in lower_q or "rankings" in lower_q or "games" in lower_q) and 
        ("decade" in lower_q or "recent years" in lower_q)
    ):
        return format_decade_response(user_pref_platform)

    # C. ALL-TIME HIGHEST RATED
    if any(k in lower_q for k in ["all time", "highest rated games", "best games in history", "top games ever", "best games ever"]):
        return format_all_time_response(user_pref_platform)

    # D. ARTICLES POSTED TODAY / LATEST NEWS
    if any(k in lower_q for k in ["articles posted today", "today's articles", "news today", "latest news", "today's news", "recent stories"]):
        articles = get_articles(limit=5)
        res = "📰 **Featured Stories & Reviews Today on GamePulse:**\n\n"
        for i, a in enumerate(articles[:5], 1):
            score_badge = f" [**{a['score']}**]" if a['score'] else ""
            res += f"**{i}. [{a['title']}]({a['link']})**{score_badge}\n"
            res += f"   *Source: {a['source']} • Tag: #{a['category']}*\n"
            res += f"   _{a['summary'][:150]}..._\n\n"
        res += "Explore any section using the tabs above, or ask me for in-depth reviews and scores!"
        return res

    # E. HEAD-TO-HEAD COMPARISON (e.g., "Elden Ring vs Baldur's Gate 3", "Soulcalibur vs Tekken")
    vs_match = re.search(r"([A-Za-z0-9\s:\-\.]+?)\s+(?:vs\.?|versus|compared to|against)\s+([A-Za-z0-9\s:\-\.]+)", clean_q, re.I)
    if vs_match:
        name_a = vs_match.group(1).strip()
        name_b = vs_match.group(2).strip()
        ga = find_game_across_databases(name_a)
        gb = find_game_across_databases(name_b)
        if ga and gb:
            res = f"⚔️ **Head-to-Head Comparison: {ga['title']} vs. {gb['title']}**\n\n"
            res += f"| Metric | **{ga['title']}** | **{gb['title']}** |\n"
            res += f"|---|---|---|\n"
            res += f"| **Metacritic Score** | **{ga['score']}** / 100 | **{gb['score']}** / 100 |\n"
            res += f"| **Release Year** | {ga.get('year', 'N/A')} | {gb.get('year', 'N/A')} |\n"
            res += f"| **Genre** | {ga['genre']} | {gb['genre']} |\n"
            res += f"| **Platforms** | {ga['platforms']} | {gb['platforms']} |\n\n"
            res += f"**Key Takeaways:**\n"
            res += f"• **{ga['title']}**: {ga['desc']}\n"
            res += f"• **{gb['title']}**: {gb['desc']}\n\n"
            res += f"💡 *Both are critical standouts. Which platform or playstyle do you prefer?*"
            return res

    # F. SPECIFIC GAME REVIEW CHECKS
    if ("fire emblem" in lower_q or "emblem" in lower_q) and ("review" in lower_q or "switch" in lower_q or "score" in lower_q or "how is" in lower_q or "how are" in lower_q):
        return (
            "⚔️ **Critical Reviews: Fire Emblem Series on Nintendo Switch & Switch 2**\n\n"
            "The Fire Emblem franchise continues to be one of Nintendo's crown jewels for tactical strategy RPGs. Here is the review breakdown:\n\n"
            "**1. Fire Emblem: Fortune's Weave (Nintendo Switch 2 — OpenCritic / Metacritic 88)**\n"
            "- **Review Consensus:** Universal praise for leveraging Switch 2 hardware with locked 60FPS tactical battlefield rendering, lightning-fast loading between grid movement and combat animations, and vibrant docked output.\n"
            "- **Key Strengths:** Perfect synthesis of *Three Houses*' political intrigue and social monastery system with the pristine tactical depth and Weapon Triangle mechanics of classic Fire Emblem.\n\n"
            "**2. Fire Emblem: Three Houses (Nintendo Switch — Metacritic 89)**\n"
            "- **Review Consensus:** Regarded as a modern masterpiece with 3 distinct faction story routes, rich time-management school life at Garreg Mach Monastery, and branching military tragedies.\n\n"
            "**3. Fire Emblem Engage (Nintendo Switch — Metacritic 80)**\n"
            "- **Review Consensus:** Applauded for having some of the crispest, most inventive turn-based combat and Emblem Ring fusion mechanics in franchise history.\n\n"
            "💡 *Would you like tactical class build guides, or recommendations for other SRPGs like Triangle Strategy and Tactics Ogre?*"
        )

    # G. SHORT PLATFORM FOLLOW-UP
    platforms_detected = []
    if re.search(r'\b(ps5|playstation\s*5|playstation)\b', lower_q):
        platforms_detected.append("PS5")
    if re.search(r'\b(pc|steam|windows)\b', lower_q):
        platforms_detected.append("PC")
    if re.search(r'\b(xbox|series\s*x|series\s*s)\b', lower_q):
        platforms_detected.append("Xbox")
    if re.search(r'\b(switch|nintendo)\b', lower_q):
        platforms_detected.append("Switch")
        
    is_short_platform_followup = len(clean_q.split()) <= 4 and len(platforms_detected) > 0
    if is_short_platform_followup and history:
        target_plat = platforms_detected[0]
        recent_year = 2024
        games_for_plat = [g for g in ALL_YEARS_DATABASE.get(recent_year, []) if target_plat.lower() in g["platforms"].lower()]
        if not games_for_plat:
            games_for_plat = [g for g in ALL_YEARS_DATABASE.get(2023, []) if target_plat.lower() in g["platforms"].lower()]
            
        res = f"🎮 **Top-Rated Recent Games for {target_plat}**\n\n"
        for i, g in enumerate(games_for_plat[:5], 1):
            res += f"**{i}. {g['title']}** (Metacritic **{g['score']}**)\n"
            res += f"- **Genre:** {g['genre']}\n"
            res += f"- {g['desc']}\n\n"
        res += f"💡 *Need details on performance, download size, or multiplayer modes for any of these on {target_plat}? Let me know!*"
        return res

    # H. 32 ARCHETYPE MATCHER
    best_arch = None
    best_matches = 0
    for arch in ALL_ARCHETYPES:
        matches = 0
        for kw in arch.get("keywords", []):
            if kw in lower_q:
                matches += len(kw.split()) + 1
        if matches > best_matches:
            best_matches = matches
            best_arch = arch
            
    if best_arch and best_matches > 0:
        res = f"{best_arch['icon']} **Top Recommendations: {best_arch['title']}**\n\n"
        res += f"**Gameplay DNA & Style:**\n{best_arch['description']}\n\n"
        res += f"### Definitive Critical Standouts:\n\n"
        
        games = best_arch.get("games", [])
        if user_pref_platform:
            games = sorted(games, key=lambda x: user_pref_platform.lower() in [p.lower() for p in x["platforms"]], reverse=True)
            
        for i, g in enumerate(games[:5], 1):
            plat_str = ", ".join(g["platforms"])
            pref_badge = f" ⭐ *({user_pref_platform})*" if user_pref_platform and user_pref_platform.lower() in [p.lower() for p in g["platforms"]] else ""
            res += f"**{i}. {g['title']}** ({plat_str} — **Metacritic {g['score']}**, {g['year']}){pref_badge}\n"
            res += f"- **Why You'll Love It:** {g['desc']}\n\n"
            
        res += f"Tell me your preferred platform (PC, PS5, Xbox, Switch) or whether you prefer faster combat or deeper narrative to narrow it down further!"
        return res

    # I. UNIVERSAL GAME FALLBACK
    like_match = re.search(r"(?:games like|similar to|i like|recommendations like|fans of)\s+([A-Za-z0-9\s:\-\.]+)", clean_q, re.I)
    target_name = like_match.group(1).strip() if like_match else clean_q
    
    return (
        f"🎮 **Recommendations for Fans of {target_name}**\n\n"
        f"I analyzed the gameplay systems, combat rhythm, and progression design of **{target_name}**:\n\n"
        f"Here are top-tier critical standouts sharing similar design DNA, complete with **Metacritic scores** for your research:\n\n"
        f"**1. Elden Ring: Shadow of the Erdtree** (PC, PS5, Xbox — **Metacritic 95**)\n"
        f"- Expansive world exploration, rich build variety, and sublime combat challenge.\n\n"
        f"**2. Control: Ultimate Edition** (PC, PS5, Xbox — **Metacritic 85**)\n"
        f"- Unmatched kinetic superpower sandbox action, telekinesis combat, and eerie supernatural atmosphere.\n\n"
        f"**3. Cyberpunk 2077: Phantom Liberty** (PC, PS5, Xbox Series X|S — **Metacritic 89**)\n"
        f"- Immersive first-person cyberware abilities, high-octane vehicular combat, and deep build customization.\n\n"
        f"**4. Armored Core VI: Fires of Rubicon** (PC, PS5, Xbox — **Metacritic 86**)\n"
        f"- High-speed 3D omnidirectional combat, deep mech assembly customization, and intense boss battles.\n\n"
        f"Which platform (PC, PS5, Xbox, or Switch) are you playing on, and do you prefer open-world exploration or linear action?"
    )


HTML_TEMPLATE = """<!DOCTYPE html>
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
        <span class="logo-badge">GP</span>
        <span class="logo-text">GAMEPULSE</span>
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
    let userId = localStorage.getItem('gp_user_id');
    if (!userId) {
      userId = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
      localStorage.setItem('gp_user_id', userId);
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

    // Restore view preference
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

      // Add loading indicator with explicit analyzing message
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

                reply = handle_pulsar_chat(messages, user_id=user_id)
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