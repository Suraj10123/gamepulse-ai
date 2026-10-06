"""
GamePulse AI - Live Video Game News Digest, Review Aggregator & Pulsar AI Concierge
Zero external Python dependencies (Standard Library Only: http.server, sqlite3, urllib, difflib, xml)
"""

import http.server
import socketserver
import urllib.request
import urllib.parse
import sqlite3
import threading
import time
import json
import re
import html
import os
import sys
import xml.etree.ElementTree as ET
import datetime
import difflib
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from uuid import uuid4

PORT = int(os.environ.get("PORT", 10000))
DB_PATH = os.environ.get("DB_PATH", "gamepulse.db")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
CURRENT_YEAR = datetime.datetime.now(datetime.timezone.utc).year
CURRENT_DATE = datetime.datetime.now(datetime.timezone.utc).date()
SESSION_TTL_SECONDS = 2 * 60 * 60
MEMORY_TTL_SECONDS = 365 * 24 * 60 * 60
MAX_CHAT_HISTORY = 24
MAX_MEMORY_ITEMS = 40
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
METACRITIC_CACHE_TTL = 15 * 60
BROWSE_CACHE_TTL = 15 * 60

# Per-chat-session state. Never use a single global conversation state: that would
# leak one visitor's context into another visitor's chat.
SESSION_STORE = {}
SESSION_LOCK = threading.RLock()
METACRITIC_CACHE = {}
BROWSE_CACHE = {}
FEED_STATUS = {}
FEED_LOCK = threading.RLock()
LAST_AGGREGATION_AT = 0.0
AGGREGATION_MIN_INTERVAL = 90

# ---------------------------------------------------------------------------
# STOP WORDS FOR SAFE MATCHING (Prevents "show" matching "shadow", etc.)
# ---------------------------------------------------------------------------
STOP_WORDS = {
    'show', 'me', 'the', 'a', 'an', 'of', 'and', 'or', 'in', 'on', 'for', 'with',
    'games', 'game', 'best', 'rated', 'top', 'year', 'what', 'can', 'you', 'give',
    'find', 'tell', 'like', 'scores', 'score', 'about', 'how', 'is', 'are', 'out',
    'right', 'now', 'this', 'to', 'at', 'all', 'any', 'from', 'please'
}

# ---------------------------------------------------------------------------
# VERIFIED GAME LOOKUP ALIASES / FALLBACK SNAPSHOTS
# ---------------------------------------------------------------------------
GAME_LOOKUP_REGISTRY = {
    "ace combat 8": {
        "title": "Ace Combat 8: Wings of the Brave",
        "aliases": [
            "ace combat 8",
            "ace combat 8 wings of the brave",
            "ace combat 8: wings of the brave",
            "ace combat viii",
        ],
        "year": 2026,
        "release_date": "2026-10-02",
        "meta_url": "https://www.metacritic.com/game/ace-combat-8-wings-of-theve/",
        "fallback_score": 87,
        "fallback_score_platform": "PS5",
    },
    "control resonant": {
        "title": "CONTROL Resonant",
        "aliases": [
            "control resonant",
            "control: resonant",
            "control 2",
        ],
        "year": 2026,
        "release_date": "2026-09-24",
        "meta_url": "https://www.metacritic.com/game/control-resonant/",
        "fallback_score": 84,
        "fallback_score_platform": "PS5",
    },
    "gta 6": {
        "title": "Grand Theft Auto VI",
        "aliases": [
            "gta 6",
            "gta vi",
            "grand theft auto vi",
            "grand theft auto 6",
        ],
        "year": 2026,
        "release_date": "2026-11-19",
        "meta_url": "https://www.metacritic.com/game/grand-theft-auto-vi/",
        "fallback_score": None,
        "fallback_score_platform": None,
    },
}

CURRENT_YEAR_FALLBACK = [
    {
        "title": "Sektori",
        "year": 2026,
        "score": 94,
        "meta_url": "https://www.metacritic.com/game/sektori/",
        "release_date": "2026-05-14",
    },
    {
        "title": "Resident Evil Requiem",
        "year": 2026,
        "score": 89,
        "meta_url": "https://www.metacritic.com/game/resident-evil-requiem/",
        "release_date": "2026-02-27",
    },
    {
        "title": "Pokémon Pokopia",
        "year": 2026,
        "score": 89,
        "meta_url": "https://www.metacritic.com/game/pokemon-pokopia/",
        "release_date": "2026-03-05",
    },
    {
        "title": "Ace Combat 8: Wings of the Brave",
        "year": 2026,
        "score": 87,
        "meta_url": "https://www.metacritic.com/game/ace-combat-8-wings-of-theve/",
        "release_date": "2026-10-02",
    },
    {
        "title": "CONTROL Resonant",
        "year": 2026,
        "score": 84,
        "meta_url": "https://www.metacritic.com/game/control-resonant/",
        "release_date": "2026-09-24",
    },
]

DECADE_FALLBACK = [
    {"title": "Overwatch", "year": 2016, "score": 90, "meta_url": "https://www.metacritic.com/game/overwatch/"},
    {"title": "The Legend of Zelda: Breath of the Wild", "year": 2017, "score": 97, "meta_url": "https://www.metacritic.com/game/the-legend-of-zelda-breath-of-the-wild/"},
    {"title": "Super Mario Odyssey", "year": 2017, "score": 97, "meta_url": "https://www.metacritic.com/game/super-mario-odyssey/"},
    {"title": "Red Dead Redemption 2", "year": 2018, "score": 97, "meta_url": "https://www.metacritic.com/game/red-dead-redemption-2/"},
    {"title": "Resident Evil 2", "year": 2019, "score": 91, "meta_url": "https://www.metacritic.com/game/resident-evil-2/"},
    {"title": "Sekiro: Shadows Die Twice", "year": 2019, "score": 90, "meta_url": "https://www.metacritic.com/game/sekiro-shadows-die-twice/"},
    {"title": "Persona 5 Royal", "year": 2020, "score": 95, "meta_url": "https://www.metacritic.com/game/persona-5-royal/"},
    {"title": "The Last of Us Part II", "year": 2020, "score": 93, "meta_url": "https://www.metacritic.com/game/the-last-of-us-part-ii/"},
    {"title": "Forza Horizon 5", "year": 2021, "score": 92, "meta_url": "https://www.metacritic.com/game/forza-horizon-5/"},
    {"title": "Elden Ring", "year": 2022, "score": 96, "meta_url": "https://www.metacritic.com/game/elden-ring/"},
    {"title": "Baldur's Gate 3", "year": 2023, "score": 96, "meta_url": "https://www.metacritic.com/game/baldurs-gate-3/"},
    {"title": "The Legend of Zelda: Tears of the Kingdom", "year": 2023, "score": 96, "meta_url": "https://www.metacritic.com/game/the-legend-of-zelda-tears-of-the-kingdom/"},
    {"title": "Astro Bot", "year": 2024, "score": 94, "meta_url": "https://www.metacritic.com/game/astro-bot/"},
    {"title": "Metaphor: ReFantazio", "year": 2024, "score": 94, "meta_url": "https://www.metacritic.com/game/metaphor-refantazio/"},
    {"title": "Hades II", "year": 2025, "score": 95, "meta_url": "https://www.metacritic.com/game/hades-ii/"},
    {"title": "Clair Obscur: Expedition 33", "year": 2025, "score": 92, "meta_url": "https://www.metacritic.com/game/clair-obscur-expedition-33/"},
] + CURRENT_YEAR_FALLBACK

KNOWN_GAME_SLUGS = {
    "ace combat 8": "ace-combat-8-wings-of-theve",
    "control resonant": "control-resonant",
    "control: resonant": "control-resonant",
    "control 2": "control-resonant",
    "gta 6": "grand-theft-auto-vi",
    "gta vi": "grand-theft-auto-vi",
    "grand theft auto vi": "grand-theft-auto-vi",
    "sektori": "sektori",
}

# ---------------------------------------------------------------------------
# 32 ALL-ENCOMPASSING GENRE & SPECIFIC GAME ARCHETYPES
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
            "immersive sim", "sniper elite", "silent assassin"
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
        "id": "platformer",
        "title": "Platformers (Mario, Zelda & Astro Bot)",
        "icon": "🕹️",
        "keywords": ["platformer", "platformers", "2d platformer", "3d platformer", "3d platformers", "precision platformer"],
        "description": "Precision jumps, exploration, movement mastery, and inventive level design.",
        "games": [
            {"title": "The Legend of Zelda: Breath of the Wild", "platforms": ["Switch", "Wii U"], "year": 2017, "score": 97, "desc": "Open-air exploration, physics-driven traversal, and enormous freedom."},
            {"title": "Super Mario Odyssey", "platforms": ["Switch"], "year": 2017, "score": 97, "desc": "Exceptional 3D movement, Cappy mechanics, and creative sandbox kingdoms."},
            {"title": "Astro Bot", "platforms": ["PS5"], "year": 2024, "score": 94, "desc": "Polished 3D platforming with tactile DualSense-driven set pieces."},
            {"title": "Super Mario Bros. Wonder", "platforms": ["Switch"], "year": 2023, "score": 92, "desc": "Inventive 2D levels, Wonder Effects, and excellent co-op."},
            {"title": "Metroid Dread", "platforms": ["Switch"], "year": 2021, "score": 88, "desc": "Fast, precise 2D traversal and action with excellent boss encounters."}
        ]
    }
]

ARCHETYPES_BY_ID = {a["id"]: a for a in ALL_ARCHETYPES}

# ---------------------------------------------------------------------------
# PULSAR AI INTELLIGENCE ENGINE
# ---------------------------------------------------------------------------
def clean_and_tokenize(text):
    clean = re.sub(r"[^a-z0-9\s:'-]", " ", text.lower())
    return clean, [w for w in clean.split() if w]


def normalize_published_at(value):
    """Return a sortable UTC ISO timestamp, or None when the source gave no date."""
    if not value:
        return None
    value = html.unescape(str(value)).strip()
    candidates = [value]
    if value.endswith("Z"):
        candidates.append(value[:-1] + "+00:00")
    try:
        dt = datetime.datetime.fromisoformat(candidates[-1])
    except ValueError:
        try:
            dt = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def display_date(value):
    if not value:
        return "Date unavailable"
    try:
        dt = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y %H:%M UTC")
    except ValueError:
        return value


def rolling_decade_years():
    """The rolling ten-year window ending today, rather than an arbitrary fixed decade."""
    start = CURRENT_DATE.replace(year=CURRENT_DATE.year - 10)
    return start.year, CURRENT_DATE.year, start.isoformat(), CURRENT_DATE.isoformat()


def purge_expired_sessions():
    cutoff = time.time() - SESSION_TTL_SECONDS
    with SESSION_LOCK:
        for sid, state in list(SESSION_STORE.items()):
            if state.get("last_seen", 0) < cutoff:
                SESSION_STORE.pop(sid, None)


def get_session_state(session_id):
    session_id = session_id or "local-default"
    now = time.time()
    purge_expired_sessions()
    with SESSION_LOCK:
        state = SESSION_STORE.setdefault(session_id, {
            "last_seen": now,
            "last_game": None,
            "last_topic": None,
            "last_platform": None,
            "history": [],
        })
        state["last_seen"] = now
        return state


def merge_session_history(state, supplied_history):
    history = state.setdefault("history", [])
    if isinstance(supplied_history, list):
        cleaned = []
        for msg in supplied_history[-MAX_CHAT_HISTORY:]:
            if not isinstance(msg, dict):
                continue
            role = msg.get("role")
            content = str(msg.get("content", "")).strip()
            if role in {"user", "assistant"} and content:
                cleaned.append({"role": role, "content": content[:5000]})
        if cleaned:
            history[:] = cleaned
    return history[-MAX_CHAT_HISTORY:]


DEFAULT_MEMORY = {
    "favorite_games": [],
    "liked_games": [],
    "disliked_games": [],
    "favorite_genres": [],
    "platforms": [],
    "play_styles": [],
    "preferences": [],
    "notes": [],
}


def normalize_memory_item(value):
    value = re.sub(r"\s+", " ", str(value or "").strip(" .,!?:;\"'"))
    value = re.sub(r"^(that|this)\s+", "", value, flags=re.I)
    if len(value) > 140:
        value = value[:137].rstrip() + "..."
    return value


def normalize_memory(memory):
    out = {k: [] for k in DEFAULT_MEMORY}
    if isinstance(memory, dict):
        for key in out:
            vals = memory.get(key, [])
            if isinstance(vals, list):
                seen = set()
                for value in vals:
                    item = normalize_memory_item(value)
                    if item and item.lower() not in seen:
                        seen.add(item.lower())
                        out[key].append(item)
                out[key] = out[key][:MAX_MEMORY_ITEMS]
    return out


def load_user_memory(user_id):
    user_id = str(user_id or "").strip()
    memory = normalize_memory(None)
    if not user_id:
        return memory
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("SELECT memory_json, updated_at FROM user_memory WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if row:
            try:
                if time.time() - float(row[1]) <= MEMORY_TTL_SECONDS:
                    memory = normalize_memory(json.loads(row[0]))
            except (TypeError, ValueError, json.JSONDecodeError):
                pass
    except sqlite3.Error:
        pass
    finally:
        conn.close()
    return memory


def save_user_memory(user_id, memory):
    user_id = str(user_id or "").strip()
    if not user_id:
        return
    memory = normalize_memory(memory)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO user_memory (user_id, memory_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                memory_json=excluded.memory_json,
                updated_at=excluded.updated_at
        """, (user_id, json.dumps(memory, ensure_ascii=False), time.time()))
        conn.commit()
    finally:
        conn.close()


def add_memory_item(memory, bucket, value):
    value = normalize_memory_item(value)
    if not value or bucket not in memory:
        return False
    existing = {x.lower() for x in memory[bucket]}
    if value.lower() in existing:
        return False
    memory[bucket].append(value)
    memory[bucket] = memory[bucket][-MAX_MEMORY_ITEMS:]
    return True


def remove_memory_matches(memory, needle):
    needle = normalize_memory_item(needle).lower()
    if not needle:
        return 0
    removed = 0
    for bucket, values in memory.items():
        kept = []
        for value in values:
            if needle in value.lower() or value.lower() in needle:
                removed += 1
            else:
                kept.append(value)
        memory[bucket] = kept
    return removed


def extract_memory_update(message, memory):
    text = re.sub(r"\s+", " ", str(message or "").strip())
    lower = text.lower()
    changed = []

    if re.search(r"\b(?:forget|delete|remove)\s+(?:that|this|the)?\s*(?:from memory\s*)?everything\b", lower):
        cleared = any(memory.values())
        for key in memory:
            memory[key] = []
        return memory, ("cleared" if cleared else "none")

    forget = re.search(r"\b(?:forget|delete|remove)(?:\s+that)?\s+(.+?)(?:\s+from memory)?$", text, re.I)
    if forget:
        removed = remove_memory_matches(memory, forget.group(1))
        return memory, (f"removed:{removed}" if removed else "none")

    explicit = re.search(r"\bremember(?:\s+that|\s+this)?\s+(.+)$", text, re.I)
    if explicit:
        if add_memory_item(memory, "notes", explicit.group(1)):
            changed.append("note")

    fav_game = re.search(r"\bmy favorite game(?: is| is currently| right now is)?\s+(.+)$", text, re.I)
    if fav_game:
        if add_memory_item(memory, "favorite_games", fav_game.group(1)):
            changed.append("favorite game")

    likes = re.search(r"\b(?:i|i'm|im)\s+(?:really\s+)?(?:like|love|enjoy|am into)\s+(.+)$", text, re.I)
    if likes and "don't" not in likes.group(0).lower() and "do not" not in likes.group(0).lower():
        if add_memory_item(memory, "liked_games", likes.group(1)):
            changed.append("like")

    dislikes = re.search(r"\b(?:i\s+)?(?:don't|do not|never)\s+(?:really\s+)?(?:like|enjoy|want)\s+(.+)$", text, re.I)
    if dislikes and add_memory_item(memory, "disliked_games", dislikes.group(1)):
        changed.append("dislike")
    hates = re.search(r"\b(?:i|i'm|im)\s+(?:really\s+)?hate\s+(.+)$", text, re.I)
    if hates and add_memory_item(memory, "disliked_games", hates.group(1)):
        changed.append("dislike")

    platform = re.search(r"\b(?:i\s+(?:mostly\s+)?play on|my\s+(?:main\s+)?platform is|i use)\s+(pc|ps5|ps4|xbox|switch|steam deck|mobile)\b", text, re.I)
    if platform and add_memory_item(memory, "platforms", platform.group(1).upper() if platform.group(1).lower() != "steam deck" else "Steam Deck"):
        changed.append("platform")

    prefer = re.search(r"\b(?:i\s+)?prefer\s+(.+)$", text, re.I)
    if prefer and add_memory_item(memory, "preferences", prefer.group(1)):
        changed.append("preference")

    genre_terms = [
        "rpg", "jrpg", "action", "adventure", "horror", "soulslike", "shooter", "strategy",
        "simulation", "sim", "platformer", "racing", "fighting", "cozy", "roguelike", "roguelite",
        "metroidvania", "stealth", "survival", "open world", "turn based", "tactical", "indie",
    ]
    for genre in genre_terms:
        if re.search(rf"\b(?:i\s+(?:like|love|enjoy)|i'm into|im into)\s+[^.]*\b{re.escape(genre)}\b", lower):
            if add_memory_item(memory, "favorite_genres", genre.title()):
                changed.append("genre")

    return memory, ("updated:" + ",".join(sorted(set(changed))) if changed else "none")


def memory_summary(memory):
    memory = normalize_memory(memory)
    labels = [
        ("Favorite games", memory["favorite_games"]),
        ("Games you like", memory["liked_games"]),
        ("Games you dislike", memory["disliked_games"]),
        ("Favorite genres", memory["favorite_genres"]),
        ("Platforms", memory["platforms"]),
        ("Play styles", memory["play_styles"]),
        ("Preferences", memory["preferences"]),
        ("Notes", memory["notes"]),
    ]
    lines = ["🧠 **Pulsar Memory**", ""]
    any_memory = False
    for label, values in labels:
        if values:
            any_memory = True
            lines.append(f"- **{label}:** {', '.join(values)}")
    if not any_memory:
        lines.append("I don't have any saved gaming preferences yet.")
    lines += ["", "You can say **remember that...** to save something, or **forget...** to remove it."]
    return "\n".join(lines)


def parse_query_filters(text):
    text_l = text.lower()
    text_l = re.sub(r"\b2926\b", "2026", text_l)
    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", text_l)
    year = int(year_match.group(1)) if year_match else None

    score = None
    m = re.search(r"\b([6-9][0-9])\s*\+", text_l)
    if m:
        score = int(m.group(1))
    elif re.search(r"\b(?:rated|score|rating|metacritic|opencritic)\b", text_l):
        m = re.search(r"\b([6-9][0-9])\b", text_l)
        if m:
            score = int(m.group(1))

    platform = None
    if re.search(r"\b(ps5|playstation\s*5|ps4|playstation|sony)\b", text_l):
        platform = "PS5"
    elif re.search(r"\b(pc|steam|windows)\b", text_l):
        platform = "PC"
    elif re.search(r"\b(xbox|series\s*x|series\s*s|one)\b", text_l):
        platform = "Xbox"
    elif re.search(r"\b(switch|nintendo\s*switch|nintendo)\b", text_l):
        platform = "Switch"
    elif re.search(r"\b(mobile|ios|android|phone)\b", text_l):
        platform = "Mobile"

    return {"year": year, "score": score, "platform": platform}


def match_archetype_safe(query):
    q_clean, q_words = clean_and_tokenize(query)
    meaningful_words = [w for w in q_words if w not in STOP_WORDS]
    if not meaningful_words:
        return None

    best_arch, best_score = None, 0.0
    for arch in ALL_ARCHETYPES:
        for kw in arch["keywords"]:
            kw_clean, kw_words = clean_and_tokenize(kw)
            if not kw_clean:
                continue
            if len(kw_words) == 1:
                if re.search(r"\b" + re.escape(kw_clean) + r"\b", q_clean):
                    score = 100 + len(kw_clean)
                    if score > best_score:
                        best_score, best_arch = score, arch
                    continue
            elif kw_clean in q_clean:
                score = 100 + len(kw_clean)
                if score > best_score:
                    best_score, best_arch = score, arch
                continue

            if len(kw_clean) < 5 or len(q_words) < len(kw_words):
                continue
            n = len(kw_words)
            for i in range(len(q_words) - n + 1):
                window = " ".join(q_words[i:i+n])
                if all(w in STOP_WORDS for w in q_words[i:i+n]):
                    continue
                ratio = difflib.SequenceMatcher(None, window, kw_clean).ratio()
                if ratio >= 0.82:
                    score = 50 * ratio + len(kw_clean)
                    if score > best_score:
                        best_score, best_arch = score, arch
    return best_arch


class LinkTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.current = None
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a" or self.current is not None:
            return
        attrs_d = dict(attrs)
        href = attrs_d.get("href", "")
        if href.startswith("/game/") and href.count("/") >= 2:
            self.current = {
                "href": href,
                "label": attrs_d.get("aria-label") or attrs_d.get("title") or "",
                "parts": [],
                "length": 0,
            }

    def handle_data(self, data):
        if self.current is None or self.current["length"] >= 800:
            return
        piece = re.sub(r"\s+", " ", data)
        if not piece:
            return
        remaining = 800 - self.current["length"]
        piece = piece[:remaining]
        self.current["parts"].append(piece)
        self.current["length"] += len(piece)

    def handle_endtag(self, tag):
        if tag.lower() != "a" or self.current is None:
            return
        href = self.current["href"]
        raw = self.current["label"] or " ".join(self.current["parts"])
        title = clean_metacritic_anchor_title(href, raw)
        self.links.append((href, title))
        self.current = None


def clean_metacritic_anchor_title(href, raw_title):
    raw_title = re.sub(r"\s+", " ", html.unescape(raw_title or "")).strip()
    raw_title = re.sub(r"^\s*\d+\s*[\.)\-:]\s*", "", raw_title)
    date_marker = re.search(
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"\s+\d{1,2},\s+\d{4}\b", raw_title
    )
    if date_marker:
        raw_title = raw_title[:date_marker.start()].strip(" -–—")
    score_marker = re.search(r"\b\d{1,3}\s*Metascore\b", raw_title, re.I)
    if score_marker:
        raw_title = raw_title[:score_marker.start()].strip(" -–—")
    if 2 <= len(raw_title) <= 140:
        return raw_title

    slug = href.rstrip("/").split("/")[-1]
    known = {
        "the-legend-of-zelda-breath-of-the-wild": "The Legend of Zelda: Breath of the Wild",
        "super-mario-odyssey": "Super Mario Odyssey",
        "red-dead-redemption-2": "Red Dead Redemption 2",
        "the-house-in-fata-morgana-dreams-of-the-revenants": "The House in Fata Morgana - Dreams of the Revenants Edition",
        "elden-ring": "Elden Ring",
        "the-legend-of-zelda-tears-of-the-kingdom": "The Legend of Zelda: Tears of the Kingdom",
        "baldurs-gate-3": "Baldur's Gate 3",
        "persona-5-royal": "Persona 5 Royal",
        "portal-companion-collection": "Portal: Companion Collection",
        "hades-ii": "Hades II",
        "metroid-prime-remastered": "Metroid Prime Remastered",
        "god-of-war": "God of War",
        "god-of-war-ragnarok": "God of War Ragnarök",
        "astro-bot": "Astro Bot",
        "sekiro-shadows-die-twice": "Sekiro: Shadows Die Twice",
        "the-last-of-us-part-ii": "The Last of Us Part II",
        "forza-horizon-5": "Forza Horizon 5",
        "elden-ring-shadow-of-the-erdtree": "Elden Ring: Shadow of the Erdtree",
    }
    return known.get(slug, re.sub(r"[-_]+", " ", slug).strip().title())


def cached_fetch(url, timeout=3):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def html_to_text(raw_html):
    no_script = re.sub(r"<(script|style|noscript)\b[^>]*>.*?</\1>", " ", raw_html, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", no_script)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def slugify_game(title):
    key = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
    for alias, slug in KNOWN_GAME_SLUGS.items():
        if key == alias:
            return slug
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def metacritic_url_for(title):
    key = title.lower().strip()
    for alias, slug in KNOWN_GAME_SLUGS.items():
        if alias in key:
            return f"https://www.metacritic.com/game/{slug}/"
    return f"https://www.metacritic.com/game/{slugify_game(title)}/"


def parse_metacritic_game_page(raw_html, requested_title, meta_url):
    text = html_to_text(raw_html)
    title = requested_title
    m = re.search(r"#\s*([A-Za-z0-9][^#]{1,120})", raw_html)
    if m:
        candidate = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))).strip()
        if candidate:
            title = candidate

    score = None
    score_matches = re.findall(r"(?:Metascore|metascore)\s+(?:Universal Acclaim|Generally Favorable|Mixed or Average|Unfavorable)?\s*(?:Based on \d+ Critic Reviews\s*)?(\d{2,3})\b", text, flags=re.I)
    if score_matches:
        score = int(score_matches[0])
    else:
        m = re.search(r"\b(\d{2,3})\s+Metascore\b", text, flags=re.I)
        if m:
            score = int(m.group(1))

    release_date = None
    m = re.search(r"(?:Released On|Initial Release Date):\s*([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})", text)
    if m:
        release_date = datetime.datetime.strptime(m.group(1), "%b %d, %Y").date().isoformat()

    review_count = None
    m = re.search(r"Based on\s+(\d+)\s+Critic Reviews", text, flags=re.I)
    if m:
        review_count = int(m.group(1))

    platforms = []
    m = re.search(r"Platforms:\s*(.*?)(?:Initial Release Date:|Publisher:|Genres:)", text)
    if m:
        chunk = m.group(1)
        for platform in ["PC", "PlayStation 5", "Xbox Series X", "Xbox Series S", "Nintendo Switch 2", "Nintendo Switch", "Xbox One", "PS4"]:
            if platform.lower() in chunk.lower() and platform not in platforms:
                platforms.append(platform)

    return {
        "title": title,
        "score": score,
        "release_date": release_date,
        "review_count": review_count,
        "platforms": platforms,
        "meta_url": meta_url,
        "source": "Metacritic",
        "verified_live": True,
        "retrieved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


def resolve_metacritic_url(title):
    query = urllib.parse.quote(title.strip())
    search_url = f"https://www.metacritic.com/search/{query}/"
    try:
        raw = cached_fetch(search_url, timeout=3)
        parser = LinkTextParser()
        parser.feed(raw)
        title_l = title.lower()
        best = None
        best_ratio = 0.0
        for href, anchor_title in parser.links:
            ratio = difflib.SequenceMatcher(None, title_l, anchor_title.lower()).ratio()
            if ratio > best_ratio:
                best_ratio, best = ratio, href
        if best and best_ratio >= 0.55:
            return urllib.parse.urljoin("https://www.metacritic.com", best)
    except Exception:
        pass
    return metacritic_url_for(title)


def fetch_metacritic_game(title, fallback=None):
    fallback = fallback or {}
    candidate_urls = []
    if fallback.get("meta_url"):
        candidate_urls.append(fallback["meta_url"])
    candidate_urls.append(metacritic_url_for(title))

    if not fallback.get("meta_url"):
        resolved = resolve_metacritic_url(title)
        if resolved not in candidate_urls:
            candidate_urls.insert(0, resolved)

    now = time.time()
    for url in candidate_urls:
        cache_key = url.lower()
        cached = METACRITIC_CACHE.get(cache_key)
        if cached and now - cached["time"] < METACRITIC_CACHE_TTL:
            return cached["data"]
        try:
            raw = cached_fetch(url, timeout=3)
            data = parse_metacritic_game_page(raw, title, url)
            METACRITIC_CACHE[cache_key] = {"time": now, "data": data}
            if data.get("score") is not None or data.get("release_date"):
                return data
        except Exception:
            continue

    url = candidate_urls[0] if candidate_urls else metacritic_url_for(title)
    fb_score = fallback.get("fallback_score") if fallback.get("fallback_score") is not None else fallback.get("score")
    fb_date = fallback.get("release_date") or (f"{fallback['year']}-01-01" if fallback.get("year") else None)
    return {
        "title": fallback.get("title", title),
        "score": fb_score,
        "release_date": fb_date,
        "review_count": None,
        "platforms": [],
        "meta_url": url,
        "source": "Metacritic (fallback snapshot)",
        "verified_live": False,
    }


def parse_metacritic_browse(raw_html, limit=30):
    parser = LinkTextParser()
    try:
        parser.feed(raw_html)
    except Exception:
        pass

    seen = set()
    results = []
    for href, title in parser.links:
        if not href or href in seen:
            continue
        seen.add(href)

        start = raw_html.find(href)
        window = raw_html[start:start + 3500] if start >= 0 else ""
        plain = html_to_text(window)

        score = None
        for pat in [
            r'class="c-finderProductCard_score[^"]*"[^>]*>.*?(\d{2,3})',
            r'data-score=["\'](\d{2,3})["\']',
            r'(\d{2,3})\s*Metascore\b',
        ]:
            m = re.search(pat, window, re.I | re.S) or re.search(pat, plain, re.I | re.S)
            if m:
                score = int(m.group(1))
                break
        if score is None or not 0 <= score <= 100:
            continue

        date = None
        for date_pat in [
            r'class="c-finderProductCard_meta[^"]*"[^>]*>.*?([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})',
            r'([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})\b',
        ]:
            m = re.search(date_pat, window if "class=" in date_pat else plain, re.I | re.S)
            if m:
                try:
                    date = datetime.datetime.strptime(m.group(1), "%b %d, %Y").date().isoformat()
                    break
                except ValueError:
                    pass

        results.append({
            "title": title,
            "year": int(date[:4]) if date else CURRENT_YEAR,
            "score": score,
            "release_date": date,
            "meta_url": urllib.parse.urljoin("https://www.metacritic.com", href),
            "source": "Metacritic",
            "verified_live": True,
        })
        if len(results) >= limit * 2:
            break

    unique = {}
    for g in results:
        key = g["meta_url"].rstrip("/")
        if key not in unique or g["score"] > unique[key]["score"]:
            unique[key] = g

    results = list(unique.values())
    results.sort(key=lambda x: (-int(x.get("score") or 0), x.get("release_date") or "9999-99-99", x["title"].lower()))
    return results[:limit]


def platform_slug(platform):
    return {
        "Switch": "nintendo-switch",
        "PS5": "ps5",
        "PC": "pc",
        "Xbox": "xbox-series-x",
    }.get(platform)


def genre_slugs_for_request(message):
    if re.search(r"\bplatform(?:er|ers)s?\b", message.lower()):
        return ["2d-platformer", "3d-platformer"]
    return []


def build_metacritic_browse_url(year=None, min_year=None, max_year=None, platform=None, genre=None):
    p = platform_slug(platform) if platform else "all"
    g = genre or "all"
    period = str(year) if year else "all-time"
    url = f"https://www.metacritic.com/browse/game/{p}/{g}/{period}/metascore/"
    params = {}
    if min_year is not None:
        params["releaseYearMin"] = str(min_year)
    if max_year is not None:
        params["releaseYearMax"] = str(max_year)
    if platform:
        params["platform"] = p
    if genre:
        params["genre"] = genre
    if params:
        url += "?" + urllib.parse.urlencode(params)
    return url


def fetch_metacritic_browse(year=None, min_year=None, max_year=None, limit=30, platform=None, genre=None):
    cache_key = (year, min_year, max_year, limit, platform, genre)
    now = time.time()
    cached = BROWSE_CACHE.get(cache_key)
    if cached and now - cached["time"] < BROWSE_CACHE_TTL:
        return cached["data"]

    url = build_metacritic_browse_url(
        year=year, min_year=min_year, max_year=max_year,
        platform=platform, genre=genre
    )
    try:
        data = parse_metacritic_browse(cached_fetch(url, timeout=3), limit=limit)
        if not data:
            raise ValueError("empty browse data")
        BROWSE_CACHE[cache_key] = {"time": now, "data": data}
        return data
    except Exception:
        if genre in {"2d-platformer", "3d-platformer"}:
            local_arch = next((a for a in ALL_ARCHETYPES if a.get("id") == "platformer"), None)
            data = []
            if local_arch:
                for g in local_arch.get("games", []):
                    copy = dict(g)
                    copy["release_date"] = copy.get("release_date") or f"{copy.get('year', CURRENT_YEAR)}-01-01"
                    copy["meta_url"] = metacritic_url_for(copy["title"])
                    copy["verified_live"] = False
                    copy["source"] = "Metacritic (fallback snapshot)"
                    data.append(copy)
            if min_year is not None:
                data = [g for g in data if min_year <= int(g.get("year", CURRENT_YEAR)) <= (max_year or CURRENT_YEAR)]
        elif year == CURRENT_YEAR:
            data = list(CURRENT_YEAR_FALLBACK)
        elif min_year is not None:
            start_year, end_year = min_year, max_year or CURRENT_YEAR
            data = [g for g in DECADE_FALLBACK if start_year <= g["year"] <= end_year]
        else:
            data = list(DECADE_FALLBACK)
        for g in data:
            g.setdefault("verified_live", False)
            g.setdefault("source", "Metacritic (fallback snapshot)")
        data.sort(key=lambda x: (-int(x.get("score") or 0), x.get("release_date") or "9999-99-99"))
        return data[:limit]


def extract_game_candidate(message, history, state):
    text_l = message.lower()

    for key, game in GAME_LOOKUP_REGISTRY.items():
        if any(alias in text_l for alias in game["aliases"]):
            return key, game

    if re.search(r"\b(it|that game|this game|that one|the game|the same)\b", text_l):
        if state.get("last_game"):
            key = state["last_game"]
            return key, GAME_LOOKUP_REGISTRY.get(key, {"title": key})
        if history:
            for prior in reversed(history):
                if prior.get("role") == "user" and prior.get("content"):
                    prior_text = prior["content"].lower()
                    for key, game in GAME_LOOKUP_REGISTRY.items():
                        if any(alias in prior_text for alias in game["aliases"]):
                            return key, game

    for g in CURRENT_YEAR_FALLBACK + DECADE_FALLBACK:
        if g["title"].lower() in text_l:
            return slugify_game(g["title"]), g

    patterns = [
        r"\b(?:review|reviews|score|metacritic score|details|info on|information on)\s+(?:for\s+)?(.+)$",
        r"\bwhat (?:do|does) (?:you|it) know about\s+(.+)$",
    ]
    for pattern in patterns:
        m = re.search(pattern, text_l)
        if not m:
            continue
        candidate = m.group(1).strip(" .?!")
        candidate = re.sub(r"\b(?:right now|today|please)$", "", candidate).strip()
        if not candidate or re.fullmatch(r"(?:it|this|that|the game|that game|this game)", candidate):
            continue
        return slugify_game(candidate), {"title": candidate}

    return None, None


def extract_comparison_titles(message):
    text = re.sub(r"\s+", " ", str(message or "").strip())
    patterns = [
        r"^(?:compare\s+)?(.+?)\s+(?:vs\.?|versus)\s+(.+?)[?.!]*$",
        r"^(.+?)\s+or\s+(.+?)[?.!]*$" if re.search(r"\bcompare\b", text, re.I) else r"^$",
    ]
    for pattern in patterns:
        m = re.match(pattern, text, re.I)
        if not m:
            continue
        left = m.group(1).strip(" .?!")
        right = m.group(2).strip(" .?!")
        if left and right and len(left) <= 100 and len(right) <= 100:
            return left, right
    return None


def fetch_comparison_games(left_title, right_title):
    left_key, left_hint = extract_game_candidate(f"review {left_title}", [], {})
    right_key, right_hint = extract_game_candidate(f"review {right_title}", [], {})
    left_fallback = GAME_LOOKUP_REGISTRY.get(left_key, left_hint or {"title": left_title})
    right_fallback = GAME_LOOKUP_REGISTRY.get(right_key, right_hint or {"title": right_title})
    left = fetch_metacritic_game(left_fallback.get("title", left_title), left_fallback)
    right = fetch_metacritic_game(right_fallback.get("title", right_title), right_fallback)
    return left, right


def relevant_articles(game_title=None, query="", limit=6):
    terms = []
    if game_title:
        terms = [w for w in re.findall(r"[A-Za-z0-9]+", game_title.lower()) if len(w) >= 3]
    else:
        terms = [w for w in re.findall(r"[A-Za-z0-9]+", query.lower()) if len(w) >= 4 and w not in STOP_WORDS]
    terms = terms[:6]

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    rows = []
    try:
        if terms:
            clauses, args = [], []
            for term in terms:
                clauses.append("(LOWER(title) LIKE ? OR LOWER(summary) LIKE ?)")
                args.extend([f"%{term}%", f"%{term}%"])
            sql = f"""
                SELECT title, summary, url, source, tag, published_at
                FROM articles
                WHERE {" AND ".join(clauses)}
                ORDER BY CASE WHEN published_at IS NULL THEN 1 ELSE 0 END,
                         published_at DESC, id DESC
                LIMIT ?
            """
            cur.execute(sql, args + [limit])
        else:
            cur.execute("""
                SELECT title, summary, url, source, tag, published_at
                FROM articles
                ORDER BY CASE WHEN published_at IS NULL THEN 1 ELSE 0 END,
                         published_at DESC, id DESC
                LIMIT ?
            """, [limit])
        rows = cur.fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()
    return rows


def latest_reviews(limit=8):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT title, summary, url, source, tag, published_at
            FROM articles
            WHERE tag = 'REVIEW'
            ORDER BY CASE WHEN published_at IS NULL THEN 1 ELSE 0 END,
                     published_at DESC, id DESC
            LIMIT ?
        """, [limit])
        return cur.fetchall()
    except sqlite3.Error:
        return []
    finally:
        conn.close()


def known_platform_for_title(title):
    key = re.sub(r"[^a-z0-9]+", " ", str(title).lower()).strip()
    for game in GAME_LOOKUP_REGISTRY.values():
        aliases = [game.get("title", "")] + game.get("aliases", [])
        if any(re.sub(r"[^a-z0-9]+", " ", a.lower()).strip() == key for a in aliases):
            return game.get("platforms", [])
    for arch in ALL_ARCHETYPES:
        for game in arch.get("games", []):
            if re.sub(r"[^a-z0-9]+", " ", game.get("title", "").lower()).strip() == key:
                return game.get("platforms", [])
    return []


def fallback_filter_platform(games, platform):
    if not platform:
        return games
    filtered = []
    for g in games:
        platforms = g.get("platforms") or known_platform_for_title(g.get("title", ""))
        if platforms and platform.lower() in " ".join(platforms).lower():
            filtered.append(g)
    return filtered


def fetch_ranked_games_for_request(message, filters, intent):
    """Resolve ranking requests, including platform+genre combinations."""
    start_year, end_year, _, _ = rolling_decade_years()
    genres = genre_slugs_for_request(message)

    if intent == "DECADE":
        if genres:
            combined, seen = [], set()
            for genre in genres:
                for g in fetch_metacritic_browse(min_year=start_year, max_year=end_year, limit=40,
                                                 platform=filters.get("platform"), genre=genre):
                    key = g.get("meta_url") or g.get("title", "").lower()
                    if key not in seen:
                        seen.add(key)
                        combined.append(g)
            if filters.get("platform") and combined and all(not g.get("verified_live") for g in combined):
                combined = fallback_filter_platform(combined, filters["platform"])
            combined.sort(key=lambda x: (-int(x.get("score") or 0), x.get("release_date") or "9999-99-99", x["title"].lower()))
            return combined[:30]
        data = fetch_metacritic_browse(min_year=start_year, max_year=end_year, limit=40, platform=filters.get("platform"))
        if filters.get("platform") and data and all(not g.get("verified_live") for g in data):
            data = fallback_filter_platform(data, filters["platform"])
        return data

    if intent == "CURRENT_YEAR":
        if genres:
            combined, seen = [], set()
            for genre in genres:
                for g in fetch_metacritic_browse(year=CURRENT_YEAR, limit=40, platform=filters.get("platform"), genre=genre):
                    key = g.get("meta_url") or g.get("title", "").lower()
                    if key not in seen:
                        seen.add(key)
                        combined.append(g)
            if filters.get("platform") and combined and all(not g.get("verified_live") for g in combined):
                combined = fallback_filter_platform(combined, filters["platform"])
            combined.sort(key=lambda x: (-int(x.get("score") or 0), x.get("release_date") or "9999-99-99", x["title"].lower()))
            return combined[:30]
        data = fetch_metacritic_browse(year=CURRENT_YEAR, limit=40, platform=filters.get("platform"))
        if filters.get("platform") and data and all(not g.get("verified_live") for g in data):
            data = fallback_filter_platform(data, filters["platform"])
        return data

    return []


def source_block(game=None, browse=None, articles=None):
    parts = []
    if game:
        parts.append(
            f"- Metacritic: {game.get('title')} | score={game.get('score') or 'tbd'} | "
            f"release={game.get('release_date') or 'unknown'} | "
            f"live={game.get('verified_live', False)} | {game.get('meta_url')}"
        )
    if browse:
        for g in browse:
            parts.append(
                f"- Metacritic ranking: {g['title']} | {g['score']}/100 | "
                f"release={g.get('release_date') or 'unknown'} | {g['meta_url']}"
            )
    for title, summary, url, source, tag, published_at in (articles or []):
        parts.append(
            f"- {source} [{tag}] {title} | published={published_at or 'unknown'} | {url}"
        )
    return "\n".join(parts)


def call_groq(user_message, history, context, intent, user_memory=None):
    if not GROQ_API_KEY:
        return None
    messages = [{
        "role": "system",
        "content": f"""
You are Pulsar, a gaming-focused AI concierge. Today is {CURRENT_DATE.isoformat()}.
You behave like a normal capable chatbot, but your specialty is video games:
recommendations, reviews, release timing, platform fit, criticism, mechanics,
industry news, and Metacritic/OpenCritic interpretation.

Critical accuracy rules:
1. Never invent a Metacritic score, release date, review date, outlet, URL, or review.
2. Treat anything marked live=true or coming from the live ranking feed as current source data.
3. If the source says TBD/unreleased, say so. Never turn an upcoming game into a reviewed/released game.
4. Distinguish game release date from review publication date.
5. For "best games right now", use the current-year live ranking and exclude games whose release date is after today.
6. For "last decade", use the rolling window ending today; explain the exact window if useful.
7. Use the conversation history for follow-ups and don't repeat the previous answer verbatim.
8. Cite important factual claims with Markdown links using the URLs provided in SOURCES.
9. For recommendations, explain why each pick fits the user's request rather than pretending a score proves preference.
10. If data is missing, be transparent instead of filling the gap from memory.
11. Treat USER MEMORY as preference/context, not as evidence for factual claims.
12. Never expose hidden implementation details, API keys, or raw internal state.
13. Avoid repeating the previous answer verbatim unless the user asks for it.
14. Do not spoil plot twists, endings, bosses, or major story reveals unless the user explicitly asks for spoilers.
15. Use saved gaming preferences to personalize recommendations, but never claim the user likes something that is not in memory.
16. For comparisons, provide a concise winner by category and explain the tradeoffs rather than choosing only by Metascore.

Current intent: {intent}

USER MEMORY:
{memory_summary(user_memory or {})}

SOURCES:
{context or "(No live source data was available.)"}
"""
    }]
    for msg in history[-MAX_CHAT_HISTORY:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    payload = json.dumps({
        "model": GROQ_MODEL,
        "temperature": 0.2,
        "messages": messages,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "GamePulseAI/3.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        reply = data["choices"][0]["message"]["content"].strip()
        return reply or None
    except Exception:
        return None


def deterministic_response(user_message, intent, game, browse, articles, arch, filters, state):
    msg_l = user_message.lower()

    if intent == "COMPARISON":
        games = browse[:2] if browse else []
        if len(games) >= 2:
            a, b = games[0], games[1]
            def score_text(g):
                return f"{g.get('score')}/100" if g.get('score') is not None else "Not currently scored"
            lines = [
                f"⚔️ **{a.get('title', 'Game A')} vs. {b.get('title', 'Game B')}**", "",
                f"| | {a.get('title', 'Game A')} | {b.get('title', 'Game B')} |",
                "|---|---|---|",
                f"| Metacritic | {score_text(a)} | {score_text(b)} |",
                f"| Release | {a.get('release_date') or 'Unknown'} | {b.get('release_date') or 'Unknown'} |",
                "",
                f"- [Metacritic: {a.get('title', 'Game A')}]({a.get('meta_url', '#')})",
                f"- [Metacritic: {b.get('title', 'Game B')}]({b.get('meta_url', '#')})",
                "",
                "Ask me which one fits your preferences, platform, or play style better and I’ll make the recommendation using your saved memory."
            ]
            return "\n".join(lines)

    if browse:
        if intent == "CURRENT_YEAR":
            browse = [g for g in browse if g.get("release_date") and g["release_date"] <= CURRENT_DATE.isoformat()]
        else:
            browse = [g for g in browse if not g.get("release_date") or g["release_date"] <= CURRENT_DATE.isoformat()]
        if filters.get("score"):
            browse = [g for g in browse if g["score"] >= filters["score"]]
        browse.sort(key=lambda x: (-int(x.get("score") or 0), x.get("release_date") or "9999-99-99", x["title"].lower()))

    if intent == "DECADE":
        start_year, end_year, start_date, end_date = rolling_decade_years()
        scope = []
        if filters.get("platform"):
            scope.append(filters["platform"])
        if re.search(r"\bplatform(?:er|ers)s?\b", msg_l):
            scope.append("platformers")
        scope_text = f" ({', '.join(scope)})" if scope else ""
        lines = [
            f"👑 **Highest-rated games in the rolling last decade{scope_text} ({start_date} → {end_date})**",
            "",
            "I’m using live Metacritic ranking data when available; the entries below are sorted by current Metascore.",
            "",
        ]
        for i, g in enumerate(browse[:15], 1):
            lines.append(
                f"{i}. **{g['title']}** — {g['score']}/100 "
                f"([Metacritic]({g['meta_url']}))"
                + (f" — released {g['release_date']}" if g.get("release_date") else "")
            )
        lines.append("")
        lines.append("Scores can differ by platform, so I’ll use the platform-specific Metacritic page when one matters.")
        return "\n".join(lines)

    if intent == "CURRENT_YEAR":
        scope = []
        if filters.get("platform"):
            scope.append(filters["platform"])
        if re.search(r"\bplatform(?:er|ers)s?\b", msg_l):
            scope.append("platformers")
        scope_text = f" ({', '.join(scope)})" if scope else ""
        lines = [
            f"🏆 **Best-reviewed games of {CURRENT_YEAR}{scope_text} released by {CURRENT_DATE.isoformat()}**",
            "",
        ]
        for i, g in enumerate(browse[:15], 1):
            lines.append(
                f"{i}. **{g['title']}** — {g['score']}/100 "
                f"([Metacritic]({g['meta_url']}))"
                + (f" — released {g['release_date']}" if g.get("release_date") else "")
            )
        return "\n".join(lines)

    if game:
        score = game.get("score")
        lines = [
            f"🎮 **{game.get('title', 'Game')}**",
            "",
            f"- **Metacritic:** {score}/100" if score is not None else "- **Metacritic:** not currently scored / not verified",
            f"- **Release date:** {game.get('release_date') or 'not verified'}",
            f"- **Platforms:** {', '.join(game.get('platforms', [])) or 'see Metacritic'}",
            f"- [Metacritic page]({game.get('meta_url')})",
        ]
        if not game.get("verified_live"):
            lines.append("- *The score/date above is a fallback snapshot because the live Metacritic page could not be fetched right now.*")
        if articles:
            lines += ["", "**Recent review/news sources:**"]
            for title, summary, url, source, tag, published_at in articles[:4]:
                when = display_date(published_at)
                lines.append(f"- [{source}: {title}]({url}) — {when}")
        return "\n".join(lines)

    if arch:
        active_platform = filters["platform"] or state.get("last_platform")
        games = list(arch["games"])
        if active_platform:
            filtered = [g for g in games if active_platform in g["platforms"]]
            if filtered:
                games = filtered
        if filters["score"]:
            games = [g for g in games if g["score"] >= filters["score"]]
        state["last_topic"] = arch["id"]
        return (
            f"{arch['icon']} **Recommendations: {arch['title']}**\n\n"
            f"*{arch['description']}*\n\n" +
            "\n".join(
                f"**{i}. {g['title']}**\n"
                f"- {g['desc']}"
                for i, g in enumerate(games, 1)
            ) +
            "\n\n*These are similarity recommendations, not a live Metacritic ranking. "
            "Ask for a specific title's current score/reviews and Pulsar will look it up.*"
        )

    if articles:
        lines = ["📰 **Most relevant recent gaming coverage**", ""]
        for title, summary, url, source, tag, published_at in articles:
            lines.append(f"- **{title}** — {source}, {display_date(published_at)}\n  [Read source]({url})")
        return "\n".join(lines)

    return (
        "🎮 **Pulsar Gaming AI**\n\n"
        "I can review a specific game, compare it with similar games, rank current "
        "releases using live Metacritic data, explain a genre, or build recommendations "
        "around your platform and preferences. I remember the current chat session and "
        "saved gaming preferences, so follow-ups like “what about that one on PC?” keep their context."
    )


def generate_pulsar_response(user_message, history=None, session_id=None, user_id=None):
    msg = str(user_message or "").strip()
    if not msg:
        return "Tell me what game, genre, platform, or review you’re interested in."

    state = get_session_state(session_id)
    history = merge_session_history(state, history or [])
    user_id = str(user_id or "").strip()
    user_memory = load_user_memory(user_id)
    user_memory, memory_action = extract_memory_update(msg, user_memory)
    if memory_action.startswith("updated:") or memory_action.startswith("removed:") or (memory_action in {"cleared", "none"} and re.search(r"\b(?:remember|forget|delete|remove)\b", msg, re.I)):
        save_user_memory(user_id, user_memory)

    msg_l = msg.lower()
    if re.search(r"\b(?:what do you remember|what have you remembered|show my memory|what do you know about my preferences)\b", msg_l):
        reply = memory_summary(user_memory)
        with SESSION_LOCK:
            state["history"] = (history + [{"role": "user", "content": msg}, {"role": "assistant", "content": reply}])[-MAX_CHAT_HISTORY:]
        return reply

    if re.match(r"^\s*(?:remember|forget|delete)\b", msg_l):
        if memory_action.startswith("updated:"):
            items = memory_action.split(":", 1)[1]
            reply = f"🧠 **Got it!** I have updated your gaming preferences ({items}). Ask me for recommendations or say **what do you remember about me** anytime."
        elif memory_action == "cleared":
            reply = "🧠 **Pulsar Memory cleared.** I will start fresh with your saved gaming preferences."
        elif memory_action.startswith("removed:"):
            reply = "🧠 **Updated.** I have removed that from your saved preferences."
        else:
            reply = "🧠 I have noted that in your gaming preferences! Ask me for recommendations or say **what do you remember about me** anytime."
        with SESSION_LOCK:
            state["history"] = (history + [{"role": "user", "content": msg}, {"role": "assistant", "content": reply}])[-MAX_CHAT_HISTORY:]
        return reply

    filters = parse_query_filters(msg)

    is_decade = bool(re.search(r"\b(last decade|past decade|past 10 years|last 10 years|last ten years)\b", msg_l))
    is_current = bool(re.search(r"\b(best games right now|best games out right now|out right now|out now|best of 2026|best games of 2026|highest rated games of the year|highest rated 2026|highest rated games)\b", msg_l))
    is_reviewish = bool(re.search(r"\b(review|reviews|score|metacritic|opencritic|rating|rated)\b", msg_l))
    is_like = bool(re.search(r"\b(games like|similar to|alternative to|recommendations like)\b", msg_l))
    is_contextual_ranking = (
        state.get("last_topic") in {"DECADE", "CURRENT_YEAR"}
        and filters.get("platform")
        and bool(re.search(r"\b(?:narrow|filter|only|just|show|give)\b", msg_l))
    )

    game_key, game_hint = extract_game_candidate(msg, history, state)
    if game_key:
        state["last_game"] = game_key
    comparison_titles = extract_comparison_titles(msg)

    browse = []
    game = None
    articles = []

    arch_match = match_archetype_safe(msg) if not game_key and not comparison_titles else None

    if comparison_titles:
        left, right = fetch_comparison_games(*comparison_titles)
        browse = [left, right]
        state["last_topic"] = "COMPARISON"
        intent = "COMPARISON"
        articles = relevant_articles(game_title=left.get("title"), limit=3) + relevant_articles(game_title=right.get("title"), limit=3)
        context = source_block(browse=browse, articles=articles)

    elif is_decade or (is_contextual_ranking and state.get("last_topic") == "DECADE"):
        state["last_topic"] = "DECADE"
        intent = "DECADE"
        browse = fetch_ranked_games_for_request(msg, filters, intent)
        context = source_block(browse=browse, articles=latest_reviews(6))

    elif is_current or (is_contextual_ranking and state.get("last_topic") == "CURRENT_YEAR"):
        state["last_topic"] = "CURRENT_YEAR"
        intent = "CURRENT_YEAR"
        browse = fetch_ranked_games_for_request(msg, filters, intent)
        context = source_block(browse=browse, articles=latest_reviews(8))

    elif game_key and (is_reviewish or not is_like):
        game_fallback = GAME_LOOKUP_REGISTRY.get(game_key, game_hint or {})
        title = game_fallback.get("title", game_key)
        game = fetch_metacritic_game(title, game_fallback)
        state["last_game"] = game_key
        articles = relevant_articles(game_title=title, limit=6)
        intent = "GAME_LOOKUP"
        context = source_block(game=game, articles=articles)

    else:
        arch = arch_match
        state["last_topic"] = arch["id"] if arch else state.get("last_topic")
        if filters.get("platform"):
            state["last_platform"] = filters["platform"]
        articles = relevant_articles(query=msg, limit=6)
        intent = "RECOMMENDATION" if arch else "GENERAL"
        context = source_block(articles=articles)

    reply = call_groq(msg, history, context, intent, user_memory=user_memory)
    if not reply:
        arch = arch_match if not game else None
        reply = deterministic_response(msg, intent, game, browse, articles, arch, filters, state)

    state["memory_action"] = memory_action

    with SESSION_LOCK:
        state["history"] = (history + [
            {"role": "user", "content": msg},
            {"role": "assistant", "content": reply},
        ])[-MAX_CHAT_HISTORY:]
        state["last_seen"] = time.time()
    return reply


# ---------------------------------------------------------------------------
# DATABASE INITIALIZATION
# ---------------------------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            summary TEXT,
            url TEXT UNIQUE,
            source TEXT,
            tag TEXT,
            published_at TEXT,
            score INTEGER DEFAULT 0,
            image_url TEXT DEFAULT ''
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_articles_tag_date ON articles(tag, published_at DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_articles_date ON articles(published_at DESC)")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_memory (
            user_id TEXT PRIMARY KEY,
            memory_json TEXT NOT NULL,
            updated_at REAL NOT NULL
        )
    """)

    old_seed_urls = [
        "https://www.gamespot.com/reviews/ace-combat-8-review/",
        "https://www.ign.com/articles/control-resonant-review",
        "https://www.eurogamer.net/gta-6-review",
        "https://www.ign.com/articles/ghost-of-yotei-review",
        "https://www.gamespot.com/reviews/death-stranding-2-review",
        "https://www.pcgamer.com/doom-the-dark-ages-review",
        "https://www.nintendolife.com/reviews/metroid-prime-4-beyond",
        "https://www.eurogamer.net/monster-hunter-wilds-review",
        "https://www.pcgamer.com/civilization-7-review",
        "https://www.polygon.com/reviews/judas-review",
        "https://news.blizzard.com/diablo4/patch-2-0-3",
        "https://www.cyberpunk.net/en/news/50212/update-2-2",
        "https://baldursgate3.game/news/patch-8-released",
        "https://www.gamespot.com/articles/uncharted-5-everything-we-know",
        "https://insider-gaming.com/resident-evil-9-details-leaked",
    ]
    placeholders = ",".join("?" for _ in old_seed_urls)
    cur.execute(f"DELETE FROM articles WHERE url IN ({placeholders})", old_seed_urls)

    cur.execute("""
        UPDATE articles
        SET tag = 'RUMOR'
        WHERE tag = 'REVIEW' AND (
            LOWER(title) LIKE '%unconfirmed%' OR
            LOWER(title) LIKE '%everything we know%' OR
            LOWER(title) LIKE '%rumor%' OR
            LOWER(title) LIKE '%leak%' OR
            LOWER(title) LIKE '%speculation%'
        )
    """)
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# RSS FEED AGGREGATION PIPELINE (STRICT CATEGORIZATION)
# ---------------------------------------------------------------------------
FEEDS = [
    {"source": "PC Gamer", "url": "https://www.pcgamer.com/rss/", "default_tag": "ALL"},
    {"source": "Rock Paper Shotgun", "url": "https://www.rockpapershotgun.com/feed", "default_tag": "ALL"},
    {"source": "Eurogamer", "url": "https://www.eurogamer.net/?format=rss", "default_tag": "ALL"},
    {"source": "IGN", "url": "https://feeds.feedburner.com/ign/all", "default_tag": "ALL"},
    {"source": "IGN Reviews", "url": "https://feeds.feedburner.com/ign/reviews", "default_tag": "REVIEW"},
    {"source": "GameSpot", "url": "https://www.gamespot.com/feeds/game-news/", "default_tag": "ALL"},
    {"source": "GameSpot Reviews", "url": "https://www.gamespot.com/feeds/reviews", "default_tag": "REVIEW"},
]


def categorize_article(title, summary):
    t_clean = re.sub(r"\s+", " ", title.strip().lower())
    s_clean = re.sub(r"\s+", " ", summary.strip().lower())

    if any(k in t_clean for k in [
        'rumor', 'leak', 'unconfirmed', 'everything we know', 'reportedly',
        'insider', 'spotted', 'speculation', 'allegedly', 'leaker'
    ]):
        return 'RUMOR'

    if any(k in t_clean for k in [
        'patch', 'hotfix', 'update', 'dlc', 'expansion', 'changelog',
        'release notes', 'balance changes', 'title update', 'version '
    ]) or (any(k in t_clean for k in ['fixes', 'balance']) and any(k in s_clean for k in ['patch', 'update', 'hotfix', 'dlc'])):
        return 'UPDATE'

    if re.search(r'\b(review|reviewed|verdict|review in progress|performance review)\b', t_clean):
        return 'REVIEW'

    if any(k in t_clean for k in [
        'trailer', 'teaser', 'gameplay reveal', 'gameplay showcase',
        'launch trailer', 'cinematic trailer', 'new trailer', 'official reveal',
        'first look', 'gameplay footage'
    ]):
        return 'TRAILER'

    if any(k in t_clean for k in [
        'layoff', 'acquisition', 'acquired', 'studio', 'ceo', 'sales',
        'earnings', 'patent', 'lawsuit', 'consolidation', 'financial',
        'funding', 'investor', 'merger', 'business', 'game industry',
        'developer closes', 'studio closes', 'executive'
    ]):
        return 'INDUSTRY'

    if any(k in t_clean for k in [
        'indie', 'mod', 'modding', 'workshop', 'early access', 'demo',
        'steam next fest', 'solo dev', 'solo developer', 'small studio',
        'independent developer', 'independent studio'
    ]):
        return 'INDIE'

    return 'ALL'


def extract_image_url(item_xml):
    for elem in item_xml:
        tag = elem.tag.lower()
        if tag.endswith("content") and elem.attrib.get("url"):
            return elem.attrib["url"]
        if tag.endswith("thumbnail") and elem.attrib.get("url"):
            return elem.attrib["url"]
        if tag == "enclosure" and elem.attrib.get("type", "").startswith("image"):
            return elem.attrib.get("url", "")
    return ""


def extract_feed_items(root):
    items = root.findall(".//item")
    if items:
        return items
    return root.findall(".//{http://www.w3.org/2005/Atom}entry")


def feed_text(item, names):
    for name in names:
        value = item.findtext(name)
        if value:
            return value
    for elem in item:
        local = elem.tag.split("}")[-1]
        if local in names and elem.text:
            return elem.text
    return ""


def feed_link(item):
    link = feed_text(item, ["link", "id"])
    if link:
        return link.strip()
    for elem in item:
        if elem.tag.split("}")[-1] == "link" and elem.attrib.get("href"):
            return elem.attrib["href"].strip()
    return ""


def run_news_aggregation_pipeline(force=False):
    global LAST_AGGREGATION_AT
    now = time.time()
    with FEED_LOCK:
        if not force and now - LAST_AGGREGATION_AT < AGGREGATION_MIN_INTERVAL:
            return
        LAST_AGGREGATION_AT = now

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    run_started = datetime.datetime.now(datetime.timezone.utc).isoformat()

    for f in FEEDS:
        feed_started = time.time()
        try:
            req = urllib.request.Request(
                f["url"],
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
                },
            )
            xml_data = None
            last_error = None
            for attempt in range(2):
                try:
                    with urllib.request.urlopen(req, timeout=8) as resp:
                        xml_data = resp.read()
                    break
                except Exception as exc:
                    last_error = exc
                    if attempt == 0:
                        time.sleep(0.5)
            if xml_data is None:
                raise last_error or RuntimeError("feed request failed")

            root = ET.fromstring(xml_data)
            items = extract_feed_items(root)
            inserted = 0

            for it in items[:30]:
                title = feed_text(it, ["title"]) or ""
                link = feed_link(it)
                desc = feed_text(it, ["description", "summary", "content"]) or ""
                pub_raw = feed_text(it, ["pubDate", "published", "updated", "date"])
                pub_date = normalize_published_at(pub_raw)

                desc_clean = re.sub(r"<[^>]+>", "", html.unescape(desc)).strip()
                if len(desc_clean) > 400:
                    desc_clean = desc_clean[:397] + "..."

                inferred = categorize_article(title, desc_clean)
                default_tag = f.get("default_tag") or "ALL"
                tag = inferred if default_tag == "ALL" else default_tag
                if inferred in {"RUMOR", "UPDATE"} and default_tag == "ALL":
                    tag = inferred

                img = extract_image_url(it)
                if title.strip() and link:
                    cur.execute("""
                        INSERT OR IGNORE INTO articles
                            (title, summary, url, source, tag, published_at, score, image_url)
                        VALUES (?, ?, ?, ?, ?, ?, 0, ?)
                    """, (
                        title.strip(), desc_clean, link, f["source"],
                        tag, pub_date, img,
                    ))
                    if cur.rowcount > 0:
                        inserted += cur.rowcount

            FEED_STATUS[f["source"]] = {
                "ok": True,
                "items": len(items),
                "inserted": inserted,
                "duration_ms": round((time.time() - feed_started) * 1000),
                "last_sync": run_started,
                "error": None,
                "url": f["url"],
            }
        except Exception as exc:
            FEED_STATUS[f["source"]] = {
                "ok": False,
                "items": 0,
                "inserted": 0,
                "duration_ms": round((time.time() - feed_started) * 1000),
                "last_sync": run_started,
                "error": str(exc)[:300],
                "url": f["url"],
            }

    conn.commit()
    conn.close()


def reclassify_existing_articles():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    updated = 0
    try:
        cur.execute("SELECT id, title, summary, tag FROM articles")
        rows = cur.fetchall()
        for row_id, title, summary, old_tag in rows:
            if old_tag != "ALL":
                continue
            inferred = categorize_article(title or "", summary or "")
            if inferred != "ALL":
                cur.execute("UPDATE articles SET tag = ? WHERE id = ?", (inferred, row_id))
                updated += 1
        conn.commit()
    finally:
        conn.close()
    return updated


def feed_health_summary():
    with FEED_LOCK:
        status = dict(FEED_STATUS)
    failures = [name for name, info in status.items() if not info.get("ok")]
    return {
        "healthy_sources": len(status) - len(failures),
        "total_sources": len(status),
        "failed_sources": failures,
    }


def feed_count(tag="ALL"):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        if tag == "ALL":
            cur.execute("SELECT COUNT(*) FROM articles")
        else:
            cur.execute("SELECT COUNT(*) FROM articles WHERE tag = ?", (tag,))
        return int(cur.fetchone()[0])
    except sqlite3.Error:
        return 0
    finally:
        conn.close()


def ensure_feed_data(tag="ALL"):
    if feed_count(tag) == 0:
        run_news_aggregation_pipeline(force=True)


def scheduler_worker():
    while True:
        try:
            run_news_aggregation_pipeline()
        except Exception:
            pass
        time.sleep(300)


# ---------------------------------------------------------------------------
# HTTP REQUEST HANDLER & HTML TEMPLATE
# ---------------------------------------------------------------------------
class GamePulseHandler(http.server.BaseHTTPRequestHandler):
    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query_params = urllib.parse.parse_qs(parsed.query)

        if path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(b'{"status":"healthy","service":"GamePulse AI"}')
            return

        if path == "/api/feed-status":
            payload = {
                "feeds": FEED_STATUS,
                "last_aggregation_at": LAST_AGGREGATION_AT,
                "review_count": feed_count("REVIEW"),
                "all_count": feed_count("ALL"),
                "trailer_count": feed_count("TRAILER"),
                "industry_count": feed_count("INDUSTRY"),
                "indie_count": feed_count("INDIE"),
                "health": feed_health_summary(),
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(payload).encode("utf-8"))
            return

        if path == "/api/memory":
            user_id = str(query_params.get("user_id", [""])[0]).strip()
            if not user_id:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": "user_id is required"}).encode("utf-8"))
                return
            memory = load_user_memory(user_id)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"memory": memory}).encode("utf-8"))
            return

        if path == "/api/news":
            tag = query_params.get("tag", ["ALL"])[0].upper()
            ensure_feed_data(tag)
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            if tag == "ALL":
                cur.execute("""SELECT id, title, summary, url, source, tag, published_at, score, image_url
                         FROM articles
                         ORDER BY CASE WHEN published_at IS NULL THEN 1 ELSE 0 END,
                                  published_at DESC, id DESC
                         LIMIT 50""")
            else:
                cur.execute("""SELECT id, title, summary, url, source, tag, published_at, score, image_url
                         FROM articles WHERE tag = ?
                         ORDER BY CASE WHEN published_at IS NULL THEN 1 ELSE 0 END,
                                  published_at DESC, id DESC
                         LIMIT 50""", (tag,))
            rows = cur.fetchall()
            conn.close()

            articles = []
            for r in rows:
                articles.append({
                    "id": r[0], "title": r[1], "summary": r[2], "url": r[3],
                    "source": r[4], "tag": r[5], "published_at": r[6],
                    "score": r[7], "image_url": r[8]
                })

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"tag": tag, "count": len(articles), "articles": articles}).encode("utf-8"))
            return

        if path == "/" or path == "/index.html":
            tag = query_params.get("tag", ["ALL"])[0].upper()
            search_kw = query_params.get("q", [""])[0].strip()
            if query_params.get("refresh", ["0"])[0] == "1":
                run_news_aggregation_pipeline(force=True)
            ensure_feed_data(tag)

            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            
            if search_kw:
                cur.execute("""SELECT id, title, summary, url, source, tag, published_at, score, image_url
                         FROM articles WHERE title LIKE ? OR summary LIKE ?
                         ORDER BY CASE WHEN published_at IS NULL THEN 1 ELSE 0 END,
                                  published_at DESC, id DESC
                         LIMIT 50""", (f"%{search_kw}%", f"%{search_kw}%"))
            elif tag == "ALL":
                cur.execute("""SELECT id, title, summary, url, source, tag, published_at, score, image_url
                         FROM articles
                         ORDER BY CASE WHEN published_at IS NULL THEN 1 ELSE 0 END,
                                  published_at DESC, id DESC
                         LIMIT 50""")
            else:
                cur.execute("""SELECT id, title, summary, url, source, tag, published_at, score, image_url
                         FROM articles WHERE tag = ?
                         ORDER BY CASE WHEN published_at IS NULL THEN 1 ELSE 0 END,
                                  published_at DESC, id DESC
                         LIMIT 50""", (tag,))
            rows = cur.fetchall()
            conn.close()

            html_content = self.render_dashboard(tag, rows, search_kw)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html_content.encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"404 Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/chat":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len).decode("utf-8")
            try:
                data = json.loads(body)
                user_msg = data.get("message", "")
                history = data.get("history", [])
                session_id = str(data.get("session_id") or uuid4())
                user_id = str(data.get("user_id") or "").strip()
                client_memory = data.get("memory")
                if user_id and isinstance(client_memory, dict):
                    server_memory = load_user_memory(user_id)
                    merged_memory = normalize_memory(server_memory)
                    for bucket, values in normalize_memory(client_memory).items():
                        for value in values:
                            add_memory_item(merged_memory, bucket, value)
                    save_user_memory(user_id, merged_memory)

                if data.get("clear_memory") and user_id:
                    save_user_memory(user_id, normalize_memory(None))
                    reply = "🧠 **Pulsar Memory cleared.** I’ll start fresh with your saved gaming preferences."
                else:
                    reply = generate_pulsar_response(user_msg, history, session_id=session_id, user_id=user_id)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_cors_headers()
                self.end_headers()
                response_memory = load_user_memory(user_id) if user_id else normalize_memory(None)
                self.wfile.write(json.dumps({
                    "reply": reply,
                    "session_id": session_id,
                    "memory": response_memory,
                }).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

    def render_dashboard(self, active_tag, rows, search_kw):
        tabs = [
            ("ALL", "🌐 All News"),
            ("REVIEW", "⭐ Reviews"),
            ("TRAILER", "🎬 Trailers"),
            ("UPDATE", "🛠️ Patches & DLC"),
            ("INDUSTRY", "💼 Industry"),
            ("RUMOR", "🕵️ Rumors"),
            ("INDIE", "🕹️ Indie & Mods")
        ]

        nav_links = []
        for t_key, t_label in tabs:
            is_active = "active" if t_key == active_tag and not search_kw else ""
            nav_links.append(f'<a href="/?tag={t_key}" class="tab-link {is_active}">{t_label}</a>')
        tabs_html = "\n".join(nav_links)

        cards = []
        for r in rows:
            r_id, r_title, r_summary, r_url, r_source, r_tag, r_pub, r_score, r_img = r
            clean_tag = re.sub(r'[^a-z0-9-]', '', str(r_tag).lower())
            tag_class = f"badge-{clean_tag}"
            safe_url = html.escape(r_url or "#", quote=True)
            safe_img = html.escape(r_img or "", quote=True)
            img_html = f'<div class="card-img" style="background-image: url(&quot;{safe_img}&quot;);"></div>' if safe_img else '<div class="card-img placeholder-img">🎮</div>'
            score_badge = f'<span class="score-badge">★ {r_score}</span>' if r_score and r_score > 0 else ''
            
            cards.append(f"""
            <article class="article-card">
                {img_html}
                <div class="card-body">
                    <div class="card-meta">
                        <span class="badge {tag_class}">{r_tag}</span>
                        <span class="source">{html.escape(r_source)}</span>
                        {score_badge}
                    </div>
                    <h2 class="card-title"><a href="{safe_url}" target="_blank" rel="noopener">{html.escape(r_title)}</a></h2>
                    <p class="card-summary">{html.escape(r_summary)}</p>
                    <div class="card-footer">
                        <time class="time" datetime="{html.escape(r_pub or '')}">{html.escape(display_date(r_pub))}</time>
                        <a href="{safe_url}" target="_blank" rel="noopener" class="read-btn">Read Story →</a>
                    </div>
                </div>
            </article>
            """)

        if cards:
            cards_html = "\n".join(cards)
        elif active_tag == "REVIEW":
            cards_html = (
                '<div class="no-stories">'
                '<p><strong>Review feed is temporarily unavailable.</strong></p>'
                '<p>Retry shortly while the live review sources synchronize. No fake review timestamps or placeholder stories are shown.</p>'
                '<p><a href="/?tag=REVIEW&refresh=1" class="read-btn">Refresh review feed →</a></p>'
                '</div>'
            )
        else:
            cards_html = (
                '<div class="no-stories">'
                '<p><strong>No stories are available for this section yet.</strong></p>'
                '<p>The live feeds may still be synchronizing. Try a refresh before concluding the section is empty.</p>'
                f'<p><a href="/?tag={active_tag}&refresh=1" class="read-btn">Refresh {html.escape(active_tag.title())} feed →</a></p>'
                '</div>'
            )

        return rf"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GamePulse AI | Live Gaming Intelligence & Reviews</title>
    <style>
        :root {{
            --bg-main: #0b0e14;
            --bg-card: #151b26;
            --bg-card-hover: #1c2433;
            --accent-cyan: #00f2fe;
            --accent-purple: #9d4edd;
            --accent-green: #00e676;
            --accent-gold: #ffd166;
            --accent-red: #ff3366;
            --text-main: #f0f4f8;
            --text-muted: #8b9bb4;
            --border-col: #222e42;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: var(--bg-main);
            color: var(--text-main);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            position: relative;
        }}
        header {{
            background: rgba(15, 22, 34, 0.95);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border-col);
            position: sticky;
            top: 0;
            z-index: 100;
            padding: 0.9rem 1.5rem;
        }}
        .header-wrap {{
            max-width: 1300px;
            margin: 0 auto;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
        }}
        .logo-box {{
            display: flex;
            align-items: center;
            gap: 0.6rem;
            text-decoration: none;
            color: #fff;
        }}
        .logo-icon {{
            font-size: 1.6rem;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .logo-text {{
            font-size: 1.3rem;
            font-weight: 800;
            letter-spacing: -0.5px;
        }}
        .logo-tag {{
            font-size: 0.65rem;
            background: var(--border-col);
            padding: 2px 6px;
            border-radius: 4px;
            color: var(--accent-cyan);
            font-weight: 700;
            text-transform: uppercase;
        }}
        .search-box form {{
            display: flex;
            align-items: center;
            background: #0f1724;
            border: 1px solid var(--border-col);
            border-radius: 20px;
            padding: 5px 14px;
        }}
        .search-box input {{
            background: transparent;
            border: none;
            outline: none;
            color: #fff;
            font-size: 0.85rem;
            padding: 4px;
            width: 240px;
        }}
        .tab-bar {{
            background: #0e141f;
            border-bottom: 1px solid var(--border-col);
            padding: 0.5rem 1.5rem;
            overflow-x: auto;
            white-space: nowrap;
        }}
        .tab-wrap {{
            max-width: 1300px;
            margin: 0 auto;
            display: flex;
            gap: 0.5rem;
        }}
        .tab-link {{
            color: var(--text-muted);
            text-decoration: none;
            padding: 0.45rem 0.9rem;
            border-radius: 16px;
            font-size: 0.85rem;
            font-weight: 600;
            transition: all 0.15s ease;
        }}
        .tab-link:hover {{
            color: #fff;
            background: rgba(255, 255, 255, 0.05);
        }}
        .tab-link.active {{
            background: linear-gradient(135deg, rgba(0, 242, 254, 0.15), rgba(157, 78, 221, 0.15));
            color: var(--accent-cyan);
            border: 1px solid rgba(0, 242, 254, 0.3);
        }}
        
        /* TOOLBAR (STORY COUNT & LIST / GRID VIEW TOGGLE) */
        .toolbar-wrap {{
            max-width: 1300px;
            margin: 1.2rem auto 0.4rem auto;
            padding: 0 1.5rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            width: 100%;
        }}
        .feed-count {{
            color: var(--text-muted);
            font-size: 0.85rem;
        }}
        .feed-count strong {{
            color: var(--text-main);
        }}
        .view-toggle-box {{
            display: flex;
            background: #0e1420;
            border: 1px solid var(--border-col);
            border-radius: 8px;
            padding: 2px;
            gap: 2px;
        }}
        .view-btn {{
            background: transparent;
            border: none;
            color: var(--text-muted);
            padding: 5px 12px;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 5px;
            transition: all 0.15s ease;
        }}
        .view-btn:hover {{
            color: #fff;
        }}
        .view-btn.active {{
            background: var(--border-col);
            color: var(--accent-cyan);
        }}

        main {{
            max-width: 1300px;
            margin: 0.8rem auto 1.5rem auto;
            padding: 0 1.5rem;
            flex: 1;
            width: 100%;
        }}

        /* GRID VIEW LAYOUT (DEFAULT) */
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 1.5rem;
            transition: all 0.2s ease;
        }}
        .article-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-col);
            border-radius: 12px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            transition: transform 0.2s ease, border-color 0.2s ease;
        }}
        .article-card:hover {{
            transform: translateY(-3px);
            border-color: rgba(0, 242, 254, 0.4);
            background: var(--bg-card-hover);
        }}
        .card-img {{
            height: 180px;
            background-size: cover;
            background-position: center;
            background-color: #1a2230;
        }}
        .placeholder-img {{
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 3rem;
            color: var(--text-muted);
        }}
        .card-body {{
            padding: 1.1rem;
            display: flex;
            flex-direction: column;
            flex: 1;
        }}
        .card-meta {{
            display: flex;
            align-items: center;
            gap: 0.6rem;
            margin-bottom: 0.6rem;
            font-size: 0.75rem;
        }}
        .badge {{
            padding: 3px 8px;
            border-radius: 4px;
            font-weight: 700;
            text-transform: uppercase;
        }}
        .badge-all {{ background: #263852; color: #a5c7f7; }}
        .badge-review {{ background: rgba(255, 209, 102, 0.15); color: var(--accent-gold); }}
        .badge-trailer {{ background: rgba(157, 78, 221, 0.15); color: #c77dff; }}
        .badge-update {{ background: rgba(0, 230, 118, 0.15); color: var(--accent-green); }}
        .badge-industry {{ background: rgba(0, 242, 254, 0.15); color: var(--accent-cyan); }}
        .badge-rumor {{ background: rgba(255, 51, 102, 0.15); color: var(--accent-red); }}
        .badge-indie {{ background: rgba(255, 140, 0, 0.15); color: #ffa94d; }}
        .source {{ color: var(--text-muted); font-weight: 500; }}
        .score-badge {{
            margin-left: auto;
            color: var(--accent-gold);
            font-weight: 700;
        }}
        .card-title {{
            font-size: 1.05rem;
            line-height: 1.35;
            margin-bottom: 0.6rem;
            font-weight: 700;
        }}
        .card-title a {{
            color: #fff;
            text-decoration: none;
        }}
        .card-title a:hover {{
            color: var(--accent-cyan);
        }}
        .card-summary {{
            color: var(--text-muted);
            font-size: 0.85rem;
            line-height: 1.45;
            margin-bottom: 1rem;
            flex: 1;
        }}
        .card-footer {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.75rem;
            border-top: 1px solid var(--border-col);
            padding-top: 0.8rem;
        }}
        .time {{ color: var(--text-muted); white-space: nowrap; }}
        .read-btn {{
            color: var(--accent-cyan);
            text-decoration: none;
            font-weight: 600;
        }}
        .read-btn:hover {{ text-decoration: underline; }}
        .no-stories {{
            text-align: center;
            padding: 4rem 1rem;
            color: var(--text-muted);
            font-size: 1.1rem;
            grid-column: 1 / -1;
        }}

        /* LIST VIEW LAYOUT (TOGGLEABLE) */
        .grid.list-view {{
            display: flex;
            flex-direction: column;
            gap: 0.85rem;
        }}
        .grid.list-view .article-card {{
            flex-direction: row;
            align-items: center;
            padding: 0.75rem 1rem;
            gap: 1.2rem;
            min-height: 110px;
        }}
        .grid.list-view .card-img {{
            width: 170px;
            min-width: 170px;
            height: 105px;
            border-radius: 8px;
        }}
        .grid.list-view .card-body {{
            padding: 0;
            flex: 1;
            overflow: hidden;
        }}
        .grid.list-view .card-meta {{
            margin-bottom: 0.35rem;
        }}
        .grid.list-view .card-title {{
            font-size: 1.05rem;
            margin-bottom: 0.35rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .grid.list-view .card-summary {{
            font-size: 0.83rem;
            line-height: 1.4;
            margin-bottom: 0.4rem;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}
        .grid.list-view .card-footer {{
            padding-top: 0.3rem;
            border-top: none;
        }}

        @media (max-width: 768px) {{
            .grid.list-view .article-card {{
                flex-direction: column;
                align-items: stretch;
            }}
            .grid.list-view .card-img {{
                width: 100%;
                height: 150px;
            }}
            .grid.list-view .card-title {{
                white-space: normal;
            }}
        }}

        /* FLOATING ACTION BUTTON AT BOTTOM RIGHT CORNER (ORIGINAL DESIGN) */
        .pulsar-fab {{
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            color: #fff;
            border: none;
            border-radius: 30px;
            padding: 12px 20px;
            display: flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
            font-weight: 700;
            font-size: 0.95rem;
            box-shadow: 0 8px 25px rgba(0, 242, 254, 0.4);
            z-index: 999;
            transition: all 0.25s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }}
        .pulsar-fab:hover {{
            transform: translateY(-3px) scale(1.03);
            box-shadow: 0 12px 30px rgba(0, 242, 254, 0.6);
        }}
        .pulsar-fab-icon {{
            font-size: 1.2rem;
            line-height: 1;
        }}

        /* PULSAR CHAT DRAWER (ANCHORED TO BOTTOM RIGHT) */
        .chat-drawer {{
            position: fixed;
            bottom: 84px;
            right: 24px;
            width: 450px;
            max-width: calc(100vw - 32px);
            height: 600px;
            max-height: calc(100vh - 100px);
            background: #111722;
            border: 1px solid var(--border-col);
            border-radius: 16px;
            display: none;
            flex-direction: column;
            box-shadow: 0 15px 45px rgba(0, 0, 0, 0.75);
            z-index: 1000;
            overflow: hidden;
            animation: drawerFadeIn 0.2s ease-out;
        }}
        @keyframes drawerFadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .chat-header {{
            background: #161e2e;
            padding: 0.9rem 1.2rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid var(--border-col);
        }}
        .chat-title {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 700;
            color: #fff;
            font-size: 0.95rem;
        }}
        .chat-close {{
            background: none;
            border: none;
            color: var(--text-muted);
            font-size: 1.3rem;
            cursor: pointer;
            padding: 0 4px;
        }}
        .chat-close:hover {{ color: #fff; }}
        .chat-chips {{
            padding: 0.6rem 0.8rem;
            display: flex;
            gap: 0.4rem;
            overflow-x: auto;
            white-space: nowrap;
            background: #0f1623;
            border-bottom: 1px solid var(--border-col);
        }}
        .chip {{
            background: #1b2434;
            border: 1px solid var(--border-col);
            color: #d1d9e6;
            font-size: 0.75rem;
            padding: 4px 10px;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.15s;
        }}
        .chip:hover {{
            background: var(--accent-cyan);
            color: #0b0e14;
            font-weight: 600;
        }}
        .chat-messages {{
            flex: 1;
            padding: 1rem;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 0.8rem;
        }}
        .msg {{
            padding: 0.75rem 1rem;
            border-radius: 12px;
            font-size: 0.85rem;
            line-height: 1.45;
            max-width: 92%;
            word-break: break-word;
        }}
        .msg-user {{
            background: linear-gradient(135deg, #1f4068, #162447);
            color: #fff;
            align-self: flex-end;
            border-bottom-right-radius: 2px;
        }}
        .msg-pulsar {{
            background: #182233;
            color: #e2e8f0;
            align-self: flex-start;
            border-bottom-left-radius: 2px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }}
        .msg-pulsar p {{ margin-bottom: 0.5rem; }}
        .msg-pulsar p:last-child {{ margin-bottom: 0; }}
        .msg-pulsar strong {{ color: var(--accent-cyan); }}
        .msg-pulsar a {{ color: var(--accent-cyan); text-decoration: underline; }}
        .chat-input-bar {{
            padding: 0.8rem;
            background: #161e2e;
            border-top: 1px solid var(--border-col);
            display: flex;
            gap: 0.5rem;
        }}
        .chat-input-bar input {{
            flex: 1;
            background: #0f1623;
            border: 1px solid var(--border-col);
            border-radius: 20px;
            padding: 0.6rem 1rem;
            color: #fff;
            font-size: 0.85rem;
            outline: none;
        }}
        .chat-input-bar input:focus {{
            border-color: var(--accent-cyan);
        }}
        .chat-send {{
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
            color: #fff;
            border: none;
            width: 38px;
            height: 38px;
            border-radius: 50%;
            cursor: pointer;
            font-weight: 700;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        footer {{
            border-top: 1px solid var(--border-col);
            padding: 1.5rem;
            text-align: center;
            color: var(--text-muted);
            font-size: 0.8rem;
        }}
    </style>
</head>
<body>
    <header>
        <div class="header-wrap">
            <a href="/" class="logo-box">
                <span class="logo-icon">🎮</span>
                <span class="logo-text">GamePulse AI</span>
                <span class="logo-tag">LIVE</span>
            </a>
            <div class="search-box">
                <form action="/" method="GET">
                    <input type="text" name="q" placeholder="Search news, reviews, games..." value="{html.escape(search_kw)}">
                </form>
            </div>
        </div>
    </header>

    <div class="tab-bar">
        <div class="tab-wrap">
            {tabs_html}
        </div>
    </div>

    <!-- TOOLBAR (STORY COUNT & LIST / GRID VIEW TOGGLE) -->
    <div class="toolbar-wrap">
        <div class="feed-count">
            Showing <strong>{len(rows)}</strong> stories
        </div>
        <div class="view-toggle-box">
            <a class="view-btn" href="/?tag={active_tag}&refresh=1" title="Refresh live feed">↻ Refresh</a>
            <button type="button" id="gridBtn" class="view-btn active" onclick="setViewMode('grid')" title="Grid View" aria-pressed="true">
                <span>⊞</span> Grid
            </button>
            <button type="button" id="listBtn" class="view-btn" onclick="setViewMode('list')" title="List View" aria-pressed="false">
                <span>☰</span> List
            </button>
        </div>
    </div>

    <main>
        <div class="grid" id="articlesGrid">
            {cards_html}
        </div>
    </main>

    <!-- FLOATING ACTION BUTTON AT BOTTOM RIGHT CORNER (ORIGINAL DESIGN) -->
    <button class="pulsar-fab" onclick="toggleChat()" id="pulsarFab" title="Ask Pulsar AI">
        <span class="pulsar-fab-icon">⚡</span>
        <span>Ask Pulsar</span>
    </button>

    <!-- PULSAR AI CONCIERGE DRAWER -->
    <div class="chat-drawer" id="chatDrawer">
        <div class="chat-header">
            <div class="chat-title">
                <span>🤖</span>
                <span>Pulsar Gaming AI</span>
                <small style="color:var(--accent-green);font-weight:700">● Memory on</small>
            </div>
            <div style="display:flex;gap:.35rem;align-items:center">
                <button class="chat-close" onclick="askChip('what do you remember about me')" title="Show saved memory">🧠</button>
                <button class="chat-close" onclick="clearPulsarMemory()" title="Clear saved memory">⌫</button>
                <button class="chat-close" onclick="toggleChat()">✕</button>
            </div>
        </div>
        <div class="chat-chips">
            <button class="chip" onclick="askChip('show me highest rated games of the year')">🏆 Best Reviewed Now</button>
            <button class="chip" onclick="askChip('best rated games of the last decade')">👑 Best of the Decade</button>
            <button class="chip" onclick="askChip('review for Ace Combat 8')">✈️ Ace Combat 8 Review</button>
            <button class="chip" onclick="askChip('tell me about Control Resonant')">🔺 Control Resonant</button>
            <button class="chip" onclick="askChip('diablo like games')">⚔️ Diablo & ARPG</button>
            <button class="chip" onclick="askChip('Games like Gears of War')">🛡️ Gears of War</button>
            <button class="chip" onclick="askChip('Games like Call of Duty')">🎯 Call of Duty</button>
            <button class="chip" onclick="askChip('Games like Spider-Man 2')">🕸️ Spider-Man</button>
            <button class="chip" onclick="askChip('what do you remember about me')">🧠 My Memory</button>
        </div>
        <div class="chat-messages" id="chatMsgs">
            <div class="msg msg-pulsar">
                <p><strong>Hi! I'm Pulsar, your Gaming-Focused AI.</strong></p>
                <p>I use live gaming sources when available, current Metacritic data, your chat context, and saved gaming preferences to answer naturally.</p>
                <p>Ask for any game review, current rankings, decade comparisons, platform-tailored suggestions, or follow-ups.</p>
            </div>
        </div>
        <div class="chat-input-bar">
            <input type="text" id="chatInput" placeholder="Ask about reviews, Metacritic, or game recommendations..." onkeydown="if(event.key==='Enter') sendChat()">
            <button class="chat-send" onclick="sendChat()">➔</button>
        </div>
    </div>

    <footer>
        <p>GamePulse AI &copy; {CURRENT_YEAR} &bull; Live Gaming Intelligence & Reviews &bull; Session-aware AI</p>
    </footer>

    <script>
        let chatHistory = [];
        let sessionId = null;
        try {
            sessionId = sessionStorage.getItem('gp_session_id');
        } catch (_) {}
        if (!sessionId) {
            sessionId = (window.crypto && crypto.randomUUID ? crypto.randomUUID() : 's-' + Date.now() + '-' + Math.random().toString(36).substring(2, 9));
            try { sessionStorage.setItem('gp_session_id', sessionId); } catch (_) {}
        }

        let userId = null;
        try {
            userId = localStorage.getItem('gp_user_id');
        } catch (_) {}
        if (!userId) {
            userId = (window.crypto && crypto.randomUUID ? crypto.randomUUID() : 'u-' + Date.now() + '-' + Math.random().toString(36).substring(2, 9));
            try { localStorage.setItem('gp_user_id', userId); } catch (_) {}
        }

        let memoryCache = {};
        try {
            const savedMem = localStorage.getItem('gp_memory_v1');
            if (savedMem) memoryCache = JSON.parse(savedMem);
        } catch (_) {}

        function setViewMode(mode) {
            const grid = document.getElementById('articlesGrid');
            const gBtn = document.getElementById('gridBtn');
            const lBtn = document.getElementById('listBtn');
            const list = mode === 'list';
            grid.classList.toggle('list-view', list);
            lBtn.classList.toggle('active', list);
            gBtn.classList.toggle('active', !list);
            lBtn.setAttribute('aria-pressed', String(list));
            gBtn.setAttribute('aria-pressed', String(!list));
            try { localStorage.setItem('gp_view_mode', list ? 'list' : 'grid'); } catch (_) {}
        }

        // Restore view mode on page load
        document.addEventListener('DOMContentLoaded', () => {
            const savedMode = localStorage.getItem('gp_view_mode');
            if (savedMode === 'list') {
                setViewMode('list');
            }
        });

        function toggleChat() {
            const d = document.getElementById('chatDrawer');
            if (d.style.display === 'flex') {
                d.style.display = 'none';
            } else {
                d.style.display = 'flex';
                document.getElementById('chatInput').focus();
            }
        }

        function askChip(text) {
            document.getElementById('chatInput').value = text;
            sendChat();
        }

        function escapeHtml(value) {
            return String(value)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        }

        function renderChatMarkdown(text) {
            let safe = escapeHtml(text);
            safe = safe.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g,
                '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
            safe = safe.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            safe = safe.replace(/\*(.*?)\*/g, '<em>$1</em>');
            return safe.replace(/\n/g, '<br>');
        }

        function clearPulsarMemory() {
            if (!confirm('Clear Pulsar’s saved gaming preferences and memory?')) return;
            fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: 'clear memory',
                    history: chatHistory.slice(-24),
                    session_id: sessionId,
                    user_id: userId,
                    memory: {},
                    clear_memory: true
                })
            })
            .then(r => r.json())
            .then(data => {
                memoryCache = {};
                try { localStorage.removeItem('gp_memory_v1'); } catch (_) {}
                const p = document.createElement('div');
                p.className = 'msg msg-pulsar';
                p.textContent = data.reply || 'Pulsar Memory cleared.';
                document.getElementById('chatMsgs').appendChild(p);
            });
        }

        function sendChat() {
            const inp = document.getElementById('chatInput');
            const msg = inp.value.trim();
            if (!msg) return;

            const box = document.getElementById('chatMsgs');
            const uDiv = document.createElement('div');
            uDiv.className = 'msg msg-user';
            uDiv.textContent = msg;
            box.appendChild(uDiv);
            inp.value = '';
            box.scrollTop = box.scrollHeight;

            const loadDiv = document.createElement('div');
            loadDiv.className = 'msg msg-pulsar';
            loadDiv.id = 'loadingMsg';
            loadDiv.innerHTML = '<em>Pulsar is analyzing live gaming sources...</em>';
            box.appendChild(loadDiv);
            box.scrollTop = box.scrollHeight;

            try {
                fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message: msg,
                        history: chatHistory.slice(-24),
                        session_id: sessionId,
                        user_id: userId,
                        memory: memoryCache
                    })
                })
                .then(async res => {
                    const data = await res.json();
                    if (!res.ok) throw new Error(data.error || 'Chat request failed');
                    return data;
                })
                .then(data => {
                    try { loadDiv.remove(); } catch (_) {}
                    if (data.session_id) {
                        sessionId = data.session_id;
                        try { sessionStorage.setItem('gp_session_id', sessionId); } catch (_) {}
                    }
                    if (data.memory) {
                        memoryCache = data.memory;
                        try { localStorage.setItem('gp_memory_v1', JSON.stringify(memoryCache)); } catch (_) {}
                    }
                    chatHistory.push({ role: 'user', content: msg });
                    chatHistory.push({ role: 'assistant', content: data.reply });

                    const pDiv = document.createElement('div');
                    pDiv.className = 'msg msg-pulsar';
                    pDiv.innerHTML = renderChatMarkdown(data.reply);
                    box.appendChild(pDiv);
                    box.scrollTop = box.scrollHeight;
                })
                .catch(err => {
                    try { loadDiv.remove(); } catch (_) {}
                    const eDiv = document.createElement('div');
                    eDiv.className = 'msg msg-pulsar';
                    eDiv.innerHTML = '<span style="color:var(--accent-red)">Pulsar could not reach the gaming intelligence service. Please retry.</span>';
                    box.appendChild(eDiv);
                    box.scrollTop = box.scrollHeight;
                });
            } catch (err) {
                try { loadDiv.remove(); } catch (_) {}
                const eDiv = document.createElement('div');
                eDiv.className = 'msg msg-pulsar';
                eDiv.innerHTML = '<span style="color:var(--accent-red)">Error: ' + escapeHtml(err.message) + '</span>';
                box.appendChild(eDiv);
                box.scrollTop = box.scrollHeight;
            }
        }

    </script>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# MAIN ENTRY POINT
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("GamePulse AI starting up...")
    print(f"Loaded {len(ALL_ARCHETYPES)} gaming archetypes.")
    init_db()
    repaired = reclassify_existing_articles()
    print(f"Database initialized; repaired {repaired} category assignments.")
    print("Performing initial live feed synchronization...")
    run_news_aggregation_pipeline(force=True)

    agg_thread = threading.Thread(target=scheduler_worker, daemon=True)
    agg_thread.start()
    print("Live RSS aggregator worker started.")

    server_address = ("0.0.0.0", PORT)
    with socketserver.ThreadingTCPServer(server_address, GamePulseHandler) as httpd:
        print(f"GamePulse AI server listening on port {PORT}...")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")
            httpd.shutdown()

if __name__ == "__main__":
    main()