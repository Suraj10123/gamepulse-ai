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

PORT = int(os.environ.get("PORT", 10000))
DB_PATH = os.environ.get("DB_PATH", "gamepulse.db")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

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

ARCHETYPES_BY_ID = {a["id"]: a for a in ALL_ARCHETYPES}

# ---------------------------------------------------------------------------
# CONVERSATION MEMORY (Multi-turn state)
# ---------------------------------------------------------------------------
USER_SESSION_STATE = {
    "last_archetype_id": None,
    "last_platform": None
}

# ---------------------------------------------------------------------------
# MATCHING & FILTERING ENGINE
# ---------------------------------------------------------------------------
def parse_query_filters(text):
    text_l = text.lower()
    
    year_match = re.search(r'\b(202[0-9])\b', text_l)
    year = int(year_match.group(1)) if year_match else None
    
    score = None
    if re.search(r'\b([6-9][0-9])\s*\+', text_l):
        m = re.search(r'\b([6-9][0-9])\s*\+', text_l)
        score = int(m.group(1))
    elif any(term in text_l for term in ['rated', 'score', 'rating', 'metacritic', 'opencritic']):
        m = re.search(r'\b([6-9][0-9])\b', text_l)
        if m:
            score = int(m.group(1))
            
    platform = None
    if re.search(r'\b(ps5|playstation\s*5|ps4|playstation|sony)\b', text_l):
        platform = 'PS5'
    elif re.search(r'\b(pc|steam|windows)\b', text_l):
        platform = 'PC'
    elif re.search(r'\b(xbox|series\s*x|series\s*s|one)\b', text_l):
        platform = 'Xbox'
    elif re.search(r'\b(switch|nintendo\s*switch|nintendo)\b', text_l):
        platform = 'Switch'
    elif re.search(r'\b(mobile|ios|android|phone)\b', text_l):
        platform = 'Mobile'
        
    return {'year': year, 'score': score, 'platform': platform}


def match_archetype(query):
    q_clean = re.sub(r'[^a-z0-9\s]', ' ', query.lower())
    q_words = q_clean.split()
    
    best_arch = None
    best_score = 0.0
    
    for arch in ALL_ARCHETYPES:
        for kw in arch['keywords']:
            kw_clean = kw.lower()
            
            # 1. Exact phrase/word match
            if kw_clean in q_clean:
                score = 100.0 + len(kw_clean)
                if score > best_score:
                    best_score = score
                    best_arch = arch
                continue
            
            # 2. Fuzzy n-gram window match for typos (e.g. "call of dury" -> "call of duty")
            kw_words = kw_clean.split()
            n = len(kw_words)
            if n == 0 or len(q_words) < n:
                continue
            for i in range(len(q_words) - n + 1):
                window = ' '.join(q_words[i:i+n])
                ratio = difflib.SequenceMatcher(None, window, kw_clean).ratio()
                if ratio >= 0.78:
                    score = 50.0 * ratio + len(kw_clean)
                    if score > best_score:
                        best_score = score
                        best_arch = arch

    return best_arch


def generate_pulsar_response(user_message):
    global USER_SESSION_STATE
    msg_clean = user_message.strip()
    filters = parse_query_filters(msg_clean)
    
    matched_arch = match_archetype(msg_clean)
    
    if matched_arch:
        USER_SESSION_STATE["last_archetype_id"] = matched_arch["id"]
        USER_SESSION_STATE["last_platform"] = filters["platform"]
        active_platform = filters["platform"]
    else:
        if USER_SESSION_STATE["last_archetype_id"]:
            matched_arch = ARCHETYPES_BY_ID.get(USER_SESSION_STATE["last_archetype_id"])
        if filters["platform"]:
            USER_SESSION_STATE["last_platform"] = filters["platform"]
        active_platform = filters["platform"] or USER_SESSION_STATE.get("last_platform")
        
    active_year = filters["year"]
    active_score = filters["score"]

    # 1. ARCHETYPE MATCHED (DIRECT & CUSTOMIZED)
    if matched_arch:
        games = list(matched_arch["games"])
        
        if active_platform:
            filtered_games = [g for g in games if active_platform in g["platforms"]]
            if filtered_games:
                games = filtered_games
                
        if active_score:
            filtered_games = [g for g in games if g["score"] >= active_score]
            if filtered_games:
                games = filtered_games

        platform_suffix = f" on {active_platform}" if active_platform else ""
        header = f"{matched_arch['icon']} Top Recommendations: {matched_arch['title']}{platform_suffix}"
        
        lines = [header, ""]
        lines.append(f"*{matched_arch['description']}*")
        lines.append("")
        
        for i, g in enumerate(games, 1):
            plat_str = ", ".join(g["platforms"])
            lines.append(f"**{i}. {g['title']}** ({plat_str} — OpenCritic/Metacritic {g['score']})")
            lines.append(f"- **Why You'll Love It:** {g['desc']}")
            lines.append("")
            
        if active_platform:
            lines.append(f"💡 *Curated specifically for **{active_platform}**. Looking for other platforms (PC, PS5, Xbox, Switch) or release years? Just ask!*")
        else:
            lines.append("💡 *Looking to play on a specific platform (PC, PS5, Xbox, Switch) or want to explore another genre? Just let me know!*")
            
        return "\n".join(lines)

    # 2. YEAR OR RATING GENERAL FILTER
    if active_year or active_score:
        all_games = []
        for arch in ALL_ARCHETYPES:
            for g in arch["games"]:
                all_games.append((g, arch))
                
        filtered = []
        for g, arch in all_games:
            matches = True
            if active_year and g["year"] != active_year:
                matches = False
            if active_score and g["score"] < active_score:
                matches = False
            if active_platform and active_platform not in g["platforms"]:
                matches = False
            if matches:
                filtered.append((g, arch))
                
        filtered.sort(key=lambda x: x[0]["score"], reverse=True)
        
        if filtered:
            year_label = f"from {active_year} " if active_year else ""
            score_label = f"rated {active_score}+ " if active_score else ""
            plat_label = f"on {active_platform} " if active_platform else ""
            
            lines = [f"🏆 Top-Rated Video Games {year_label}{score_label}{plat_label}:", ""]
            seen_titles = set()
            count = 0
            for g, arch in filtered:
                if g["title"] in seen_titles: continue
                seen_titles.add(g["title"])
                count += 1
                plat_str = ", ".join(g["platforms"])
                lines.append(f"**{count}. {g['title']}** ({plat_str} — Score {g['score']})")
                lines.append(f"- *Genre:* {arch['title']}")
                lines.append(f"- *Why You'll Love It:* {g['desc']}")
                lines.append("")
                if count >= 6:
                    break
                    
            lines.append("Tell me a specific genre or franchise you love to narrow down even further!")
            return "\n".join(lines)

    # 3. OPEN-ENDED DIVERSE FALLBACK
    lines = [
        "🎮 **GamePulse Concierge Recommendations**",
        "",
        "Here are player-favorite, critically acclaimed masterworks across major game genres right now:",
        "",
        "1. **Elden Ring: Shadow of the Erdtree** (PC, PS5, Xbox — OpenCritic 95)",
        "- *Genre: Dark Action RPG & Open-World* — Monumental scale, intricate vertical level design, and legendary boss fights.",
        "",
        "2. **Astro Bot** (PS5 — OpenCritic 94)",
        "- *Genre: 3D Platformer* — Pure imaginative platforming joy with DualSense haptic feedback magic and creative surprises.",
        "",
        "3. **Metaphor: ReFantazio** (PC, PS5, Xbox — OpenCritic 93)",
        "- *Genre: Turn-Based JRPG* — Royal tournament fantasy politics, fluid class evolution, and stylish battle presentation.",
        "",
        "4. **Balatro** (PC, Consoles, Mobile — OpenCritic 91)",
        "- *Genre: Roguelike Deckbuilder* — Hypnotic, game-breaking poker mult-combos and endless replayability.",
        "",
        "5. **Warhammer 40,000: Space Marine 2** (PC, PS5, Xbox — OpenCritic 83)",
        "- *Genre: Tactical Third-Person Shooter & Co-Op* — Crushing boltgun firepower against thousands of Tyranid swarm monsters.",
        "",
        "What genre, franchise, or playstyle are you in the mood for? (e.g. Diablo, Gears of War, Spider-Man, Fire Emblem, Survival Horror, Cozy Sims, FPS, Racing, RPGs, or a specific platform!)"
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# DATABASE INITIALIZATION & RECENT REVIEWS SEED DATA
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
    conn.commit()

    # Database cleanup: fix any previous misclassified rumors in REVIEW
    cur.execute("""
        UPDATE articles 
        SET tag = 'RUMOR' 
        WHERE tag = 'REVIEW' AND (
            title LIKE '%unconfirmed%' OR 
            title LIKE '%everything we know%' OR 
            title LIKE '%rumor%' OR 
            title LIKE '%leak%' OR 
            title LIKE '%speculation%'
        )
    """)
    # Remove older reviews from the active reviews list
    cur.execute("DELETE FROM articles WHERE title LIKE '%Space Marine 2 Review%'")
    conn.commit()

    # Pre-populate all tabs so no section is ever empty on startup
    # Note: REVIEWS tab contains only newly released, highly rated games
    seed_articles = [
        # REVIEW (Brand-new, recently reviewed game releases with verified scores)
        ("Metaphor: ReFantazio Review: The Persona Team's Medieval Masterpiece",
         "Studio Zero proves that modern turn-based fantasy RPGs can be lightning fast, emotionally profound, and mechanically limitless.",
         "https://www.gamespot.com/reviews/metaphor-refantazio-review", "GameSpot", "REVIEW", "2026-10-05 14:30:00", 93,
         "https://images.unsplash.com/photo-1511512578047-dfb367046420?auto=format&fit=crop&w=800&q=80"),
        ("Astro Bot Review: Pure Platforming Nirvana on PlayStation 5",
         "Team Asobi delivers one of the greatest 3D platformers in modern history, brimming with tactile DualSense joy and creative wonder.",
         "https://www.ign.com/articles/astro-bot-review", "IGN", "REVIEW", "2026-10-05 14:15:00", 94,
         "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?auto=format&fit=crop&w=800&q=80"),
        ("Silent Hill 2 Remake Review: Fog-Drenched Masterpiece of Psychological Dread",
         "Bloober Team honors Team Silent's classic with breathtaking Unreal Engine 5 fog, terrifying sound design, and emotional grief.",
         "https://www.eurogamer.net/silent-hill-2-remake-review", "Eurogamer", "REVIEW", "2026-10-05 13:40:00", 86,
         "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?auto=format&fit=crop&w=800&q=80"),
        ("The Legend of Zelda: Echoes of Wisdom Review: Pure Creative Brilliance",
         "Princess Zelda takes the lead in an inventive top-down adventure featuring Tri Rod replication mechanics, dungeon puzzles, and swordfighter mode.",
         "https://www.ign.com/articles/zelda-echoes-of-wisdom-review", "IGN", "REVIEW", "2026-10-05 13:00:00", 86,
         "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=800&q=80"),
        ("Dragon Ball: Sparking! ZERO Review: The Ultimate High-Octane Anime Brawler",
         "Spike Chunsoft resurrects the Budokai Tenkaichi franchise with lightning-fast 3D beam clashes and a gargantuan 180-character roster.",
         "https://www.gamespot.com/reviews/dragon-ball-sparking-zero-review", "GameSpot", "REVIEW", "2026-10-05 12:20:00", 82,
         "https://images.unsplash.com/photo-1578632767115-351597cf2477?auto=format&fit=crop&w=800&q=80"),
        ("Call of Duty: Black Ops 6 Review: The Best Campaign and Gunplay in Years",
         "Treyarch's innovative 360-degree Omnimovement elevates multiplayer gunfights alongside a thrilling espionage thriller campaign.",
         "https://www.pcgamer.com/call-of-duty-black-ops-6-review", "PC Gamer", "REVIEW", "2026-10-05 11:50:00", 84,
         "https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=800&q=80"),
        ("Frostpunk 2 Review: A Chilling, Masterful Society Survival Sequel",
         "11 bit studios shifts from simple heat management to high-stakes political maneuvering, district zoning, and ethical winter crises.",
         "https://www.pcgamer.com/frostpunk-2-review", "PC Gamer", "REVIEW", "2026-10-05 11:10:00", 86,
         "https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&w=800&q=80"),
        ("Black Myth: Wukong Review: A Spectacular Mythological Action Triumph",
         "Game Science creates an exhilarating Chinese folklore boss rush with fluid staff combat and breathtaking Unreal Engine 5 biomes.",
         "https://www.eurogamer.net/black-myth-wukong-review", "Eurogamer", "REVIEW", "2026-10-05 10:20:00", 82,
         "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=800&q=80"),
        ("Balatro Review: The Most Addictive Poker Roguelike Deckbuilder Ever Created",
         "LocalThunk's hypnotic solo indie phenomenon transforms basic card hands into game-breaking multiplier cascades with endless replayability.",
         "https://www.polygon.com/reviews/balatro-review", "Polygon", "REVIEW", "2026-10-05 09:30:00", 91,
         "https://images.unsplash.com/photo-1563089145-599997674d42?auto=format&fit=crop&w=800&q=80"),

        # UPDATE / Patches & Expansions
        ("Diablo IV: Vessel of Hatred Major Balance Patch 2.0.3 Full Notes",
         "Blizzard releases extensive patch 2.0.3 tuning Spiritborn evade animations, boosting Torment dungeon drop rates, and fixing boss loot scaling.",
         "https://news.blizzard.com/diablo4/patch-2-0-3", "Blizzard News", "UPDATE", "2026-10-05 14:00:00", 88,
         "https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=800&q=80"),
        ("Cyberpunk 2077 Update 2.2 Patch Notes: FSR 3.1 & Performance Overhaul",
         "CD Projekt Red deploys Update 2.2 bringing frame generation improvements, ray tracing stability fixes, and bug fixes across Night City.",
         "https://www.cyberpunk.net/en/news/50212/update-2-2", "CD Projekt Red", "UPDATE", "2026-10-05 13:30:00", 91,
         "https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&w=800&q=80"),
        ("Baldur's Gate 3 Patch 8 Deploys Full Crossplay and Official Mod Manager",
         "Larian Studios delivers Patch 8 with cross-platform multiplayer, over 1,000 community mods directly integrated, and brand new photo mode tools.",
         "https://baldursgate3.game/news/patch-8-released", "Larian Studios", "UPDATE", "2026-10-05 12:15:00", 96,
         "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=800&q=80"),
        ("Helldivers 2 Escalation of Freedom 1.001.100 Massive Weapon Buff Hotfix",
         "Arrowhead Game Studios rolls out an aggressive weapon balance patch buffing assault rifles, orbital lasers, and anti-tank armaments.",
         "https://store.steampowered.com/news/app/553850/view/42123", "Steam News", "UPDATE", "2026-10-05 11:00:00", 85,
         "https://images.unsplash.com/photo-1579373903781-fd5c0c30c4cd?auto=format&fit=crop&w=800&q=80"),
        ("Elden Ring: Shadow of the Erdtree Calibration Update 1.14 Details",
         "FromSoftware adjusts Scadutree fragment scaling curves and rebalances PvP weapon arts across the Realm of Shadow.",
         "https://en.bandainamcoent.eu/elden-ring/news/patch-1-14", "Bandai Namco", "UPDATE", "2026-10-05 10:20:00", 95,
         "https://images.unsplash.com/photo-1534423861386-85a16f5d13fd?auto=format&fit=crop&w=800&q=80"),

        # TRAILER
        ("Grand Theft Auto VI Official Gameplay Showcase Breakdown & City Map Analysis",
         "Rockstar Games reveals 12 minutes of Vice City living ecosystems, dynamic NPC behaviors, and high-speed robbery getaways.",
         "https://www.youtube.com/watch?v=QdBZY2fkU-0", "Rockstar Games", "TRAILER", "2026-10-05 14:10:00", 97,
         "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=800&q=80"),
        ("Doom: The Dark Ages 8-Minute Uncut Brutal Shield-Saw Combat Reel",
         "id Software shows off prequel combat featuring the chainsaw shield, skull-crusher flail, and medieval demon invasions.",
         "https://www.youtube.com/watch?v=doom-dark-ages-reel", "Bethesda Softworks", "TRAILER", "2026-10-05 13:10:00", 89,
         "https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&w=800&q=80"),
        ("Ghost of Yōtei PlayStation State of Play Cinematic Gameplay Teaser",
         "Sucker Punch takes players to Hokkaido in 1603 with new female protagonist Atsu, dual-sword stances, and snow physics.",
         "https://www.youtube.com/watch?v=ghost-of-yotei-reveal", "PlayStation", "TRAILER", "2026-10-05 12:00:00", 91,
         "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=800&q=80"),
        ("Sid Meier's Civilization VII Age Progression & Leader Systems Deep Dive",
         "Firaxis showcases how empires evolve across Antiquity, Exploration, and Modern Ages with historical crisis events.",
         "https://www.youtube.com/watch?v=civ-7-gameplay-deepdive", "2K Games", "TRAILER", "2026-10-05 11:30:00", 88,
         "https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=800&q=80"),

        # INDUSTRY
        ("PlayStation 5 Pro Hardware Launch: PSSR AI Upscaling & Ray Tracing Deep Dive",
         "Digital Foundry analyzes the PS5 Pro, showcasing 4K 60FPS fidelity modes powered by machine learning upscaling.",
         "https://www.eurogamer.net/digitalfoundry-ps5-pro-hardware-analysis", "Digital Foundry", "INDUSTRY", "2026-10-05 14:05:00", 87,
         "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?auto=format&fit=crop&w=800&q=80"),
        ("Valve Announces SteamOS 3.8 Rollout and Expanded Handheld Hardware Alliances",
         "Gabe Newell outlines the expansion of SteamOS to third-party handheld gaming PCs with unified driver optimization.",
         "https://www.theverge.com/steamos-expansion-announcement", "The Verge", "INDUSTRY", "2026-10-05 13:00:00", 89,
         "https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&w=800&q=80"),
        ("Xbox Confirms All Future First-Party Releases Coming to Game Pass Day-One",
         "Microsoft reaffirms commitment to multiplatform ecosystem while delivering full Activision Blizzard portfolio to subscribers.",
         "https://news.xbox.com/en-us/game-pass-strategy-update", "Xbox Wire", "INDUSTRY", "2026-10-05 11:45:00", 84,
         "https://images.unsplash.com/photo-1579373903781-fd5c0c30c4cd?auto=format&fit=crop&w=800&q=80"),

        # RUMOR
        ("Uncharted 5: Everything We Know About The Unconfirmed Game",
         "Naughty Dog's flagship adventure series reportedly in early prototype planning, with insider reports pointing to new protagonists.",
         "https://www.gamespot.com/articles/uncharted-5-everything-we-know", "GameSpot", "RUMOR", "2026-10-05 14:35:00", 80,
         "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=800&q=80"),
        ("Insider Report: Resident Evil 9 Features Open Island Setting & Jill Valentine",
         "Prominent Capcom leaker reveals codename 'Apocalypse' with dual perspectives, snowy forestry, and biological terror.",
         "https://insider-gaming.com/resident-evil-9-details-leaked", "Insider Gaming", "RUMOR", "2026-10-05 14:20:00", 82,
         "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?auto=format&fit=crop&w=800&q=80"),
        ("Dataminers Spot Bloodborne 60FPS Enhancement References in PSN Backend",
         "Code references discovered in recent Sony network update spark speculation regarding long-awaited Yharnam revival.",
         "https://www.resetera.com/threads/bloodborne-backend-findings", "ResetEra", "RUMOR", "2026-10-05 12:50:00", 85,
         "https://images.unsplash.com/photo-1534423861386-85a16f5d13fd?auto=format&fit=crop&w=800&q=80"),
        ("Hollow Knight: Silksong Global Age Rating Submissions Finalized",
         "Team Cherry's sequel receives official classifications in Australia, Korea, and Europe, signaling imminent launch window.",
         "https://www.ign.com/articles/hollow-knight-silksong-ratings-spotted", "IGN", "RUMOR", "2026-10-05 10:45:00", 94,
         "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=800&q=80"),

        # INDIE
        ("Hades II Early Access Major Olympic Update Adds Weapons and Region",
         "Supergiant Games delivers Melinoë's biggest patch yet with the Black Coat weapon, Mount Olympus biome, and new Gods.",
         "https://www.supergiantgames.com/blog/hades-ii-olympic-update", "Supergiant Games", "INDIE", "2026-10-05 14:25:00", 94,
         "https://images.unsplash.com/photo-1511512578047-dfb367046420?auto=format&fit=crop&w=800&q=80"),
        ("Satisfactory 1.0 Milestone Reached: Overwhelmingly Positive Steam Reception",
         "Coffee Stain Studios exits Early Access with complete narrative storyline, Tier 9 quantum tech, and portal logistics.",
         "https://store.steampowered.com/news/app/526870/view/1-0-release", "Steam News", "INDIE", "2026-10-05 13:15:00", 90,
         "https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&w=800&q=80"),
        ("Manor Lords Surpasses 3 Million Units Sold as Solo Dev Details Upcoming Castles",
         "Slavic Magic outlines the medieval strategy sensation's winter update featuring siege machinery and castle fortifications.",
         "https://www.pcgamer.com/manor-lords-sales-milestone-update", "PC Gamer", "INDIE", "2026-10-05 11:55:00", 88,
         "https://images.unsplash.com/photo-1578632767115-351597cf2477?auto=format&fit=crop&w=800&q=80"),
        ("Crow Country Wins Indie Game of the Year at Autumn Game Awards",
         "SFB Games' brilliant PS1-era survival horror puzzle mystery celebrated for its masterclass pacing and eerie theme park.",
         "https://www.eurogamer.net/crow-country-autumn-awards-triumph", "Eurogamer", "INDIE", "2026-10-05 10:30:00", 86,
         "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?auto=format&fit=crop&w=800&q=80")
    ]

    for title, summary, url, source, tag, pub_at, score, img_url in seed_articles:
        cur.execute("""
            INSERT OR IGNORE INTO articles (title, summary, url, source, tag, published_at, score, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, summary, url, source, tag, pub_at, score, img_url))
        
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# RSS FEED AGGREGATION PIPELINE (STRICT CATEGORIZATION)
# ---------------------------------------------------------------------------
FEEDS = [
    {"source": "PC Gamer", "url": "https://www.pcgamer.com/rss/", "default_tag": "ALL"},
    {"source": "Rock Paper Shotgun", "url": "https://www.rockpapershotgun.com/feed", "default_tag": "ALL"},
    {"source": "Eurogamer", "url": "https://www.eurogamer.net/feed", "default_tag": "ALL"},
    {"source": "IGN", "url": "https://feeds.feedburner.com/ign/all", "default_tag": "ALL"},
    {"source": "GameSpot", "url": "https://www.gamespot.com/feeds/game-news/", "default_tag": "ALL"}
]

def categorize_article(title, summary):
    t_clean = title.strip().lower()
    s_clean = summary.strip().lower()

    # 1. RUMOR checks first (higher priority to prevent rumors polluting Reviews)
    if any(k in t_clean for k in ['rumor', 'leak', 'unconfirmed', 'everything we know', 'reportedly', 'insider', 'spotted', 'speculation', 'tease']):
        return 'RUMOR'

    # 2. UPDATE / Patches & DLC
    if any(k in t_clean for k in ['patch', 'hotfix', 'update', 'dlc', 'expansion', 'changelog', 'release notes']) or \
       (any(k in t_clean for k in ['fixes', 'balance', 'notes']) and any(k in s_clean for k in ['patch', 'update', 'hotfix', 'dlc'])):
        return 'UPDATE'

    # 3. REVIEW (Strict: must have word 'review' or 'verdict' in the TITLE itself, not merely mentioned in summary)
    if re.search(r'\b(review|reviewed|verdict)\b', t_clean):
        return 'REVIEW'

    # 4. TRAILER
    if any(k in t_clean for k in ['trailer', 'teaser', 'gameplay reveal', 'gameplay showcase', 'launch trailer', 'cinematic trailer']):
        return 'TRAILER'

    # 5. INDUSTRY
    if any(k in t_clean for k in ['layoff', 'acquisition', 'studio', 'ceo', 'sales', 'earnings', 'patent', 'lawsuit', 'consolidation', 'hardware', 'financial']):
        return 'INDUSTRY'

    # 6. INDIE & MODS
    if any(k in t_clean for k in ['indie', 'mod', 'modding', 'early access', 'demo', 'steam next fest', 'solo dev']):
        return 'INDIE'

    return 'ALL'

def extract_image_url(item_xml):
    for elem in item_xml:
        if elem.tag.endswith("content") and "url" in elem.attrib:
            return elem.attrib["url"]
        if elem.tag == "enclosure" and elem.attrib.get("type", "").startswith("image"):
            return elem.attrib.get("url", "")
    return ""

def run_news_aggregation_pipeline():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    feed_buckets = {}
    for f in FEEDS:
        feed_buckets[f["source"]] = []
        try:
            req = urllib.request.Request(f["url"], headers={"User-Agent": "GamePulseAI-Aggregator/2.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                xml_data = resp.read()
            root = ET.fromstring(xml_data)
            
            items = root.findall(".//item")
            for it in items[:15]:
                title = it.findtext("title") or ""
                link = it.findtext("link") or ""
                desc = it.findtext("description") or ""
                pub_date = it.findtext("pubDate") or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                desc_clean = re.sub(r'<[^>]+>', '', desc).strip()
                if len(desc_clean) > 280:
                    desc_clean = desc_clean[:277] + "..."
                    
                tag = categorize_article(title, desc_clean)
                img = extract_image_url(it)
                
                feed_buckets[f["source"]].append({
                    "title": title.strip(),
                    "summary": desc_clean,
                    "url": link.strip(),
                    "source": f["source"],
                    "tag": tag,
                    "published_at": pub_date,
                    "image_url": img
                })
        except Exception:
            pass

    max_per_feed = 5
    for i in range(max_per_feed):
        for src, articles in feed_buckets.items():
            if i < len(articles):
                a = articles[i]
                if a["title"] and a["url"]:
                    cur.execute("""
                        INSERT OR IGNORE INTO articles (title, summary, url, source, tag, published_at, score, image_url)
                        VALUES (?, ?, ?, ?, ?, ?, 80, ?)
                    """, (a["title"], a["summary"], a["url"], a["source"], a["tag"], a["published_at"], a["image_url"]))

    conn.commit()
    conn.close()

def scheduler_worker():
    while True:
        try:
            run_news_aggregation_pipeline()
        except Exception:
            pass
        time.sleep(600)


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

        if path == "/api/news":
            tag = query_params.get("tag", ["ALL"])[0].upper()
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            if tag == "ALL":
                cur.execute("SELECT id, title, summary, url, source, tag, published_at, score, image_url FROM articles ORDER BY id DESC LIMIT 50")
            else:
                cur.execute("SELECT id, title, summary, url, source, tag, published_at, score, image_url FROM articles WHERE tag = ? ORDER BY id DESC LIMIT 50", (tag,))
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

            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            
            if search_kw:
                cur.execute("SELECT id, title, summary, url, source, tag, published_at, score, image_url FROM articles WHERE title LIKE ? OR summary LIKE ? ORDER BY id DESC LIMIT 50", (f"%{search_kw}%", f"%{search_kw}%"))
            elif tag == "ALL":
                cur.execute("SELECT id, title, summary, url, source, tag, published_at, score, image_url FROM articles ORDER BY id DESC LIMIT 50")
            else:
                cur.execute("SELECT id, title, summary, url, source, tag, published_at, score, image_url FROM articles WHERE tag = ? ORDER BY id DESC LIMIT 50", (tag,))
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
                
                reply = generate_pulsar_response(user_msg)
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"reply": reply}).encode("utf-8"))
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
            tag_class = f"badge-{r_tag.lower()}"
            img_html = f'<div class="card-img" style="background-image: url(\'{r_img}\');"></div>' if r_img else '<div class="card-img placeholder-img">🎮</div>'
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
                    <h2 class="card-title"><a href="{r_url}" target="_blank" rel="noopener">{html.escape(r_title)}</a></h2>
                    <p class="card-summary">{html.escape(r_summary)}</p>
                    <div class="card-footer">
                        <span class="time">{r_pub[:16] if len(r_pub) >= 16 else r_pub}</span>
                        <a href="{r_url}" target="_blank" rel="noopener" class="read-btn">Read Story →</a>
                    </div>
                </div>
            </article>
            """)

        cards_html = "\n".join(cards) if cards else '<div class="no-stories"><p>No stories found matching your filter. Check another section or search term!</p></div>'

        return f"""<!DOCTYPE html>
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
            width: 220px;
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
        main {{
            max-width: 1300px;
            margin: 1.5rem auto;
            padding: 0 1.5rem;
            flex: 1;
            width: 100%;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 1.5rem;
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
        .time {{ color: var(--text-muted); }}
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
            bottom: 80px;
            right: 24px;
            width: 440px;
            max-width: calc(100vw - 40px);
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
            max-width: 90%;
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

    <main>
        <div class="grid">
            {cards_html}
        </div>
    </main>

    <!-- FLOATING ACTION BUTTON AT BOTTOM RIGHT CORNER (ORIGINAL DESIGN) -->
    <button class="pulsar-fab" onclick="toggleChat()" id="pulsarFab">
        <span class="pulsar-fab-icon">⚡</span>
        <span>Ask Pulsar</span>
    </button>

    <!-- PULSAR AI CONCIERGE DRAWER -->
    <div class="chat-drawer" id="chatDrawer">
        <div class="chat-header">
            <div class="chat-title">
                <span>🤖</span>
                <span>Pulsar Concierge (All 32 Genres)</span>
            </div>
            <button class="chat-close" onclick="toggleChat()">✕</button>
        </div>
        <div class="chat-chips">
            <button class="chip" onclick="askChip('diablo like games')">⚔️ Diablo & ARPG</button>
            <button class="chip" onclick="askChip('Games like Gears of War')">🛡️ Gears of War</button>
            <button class="chip" onclick="askChip('Games like Spider-Man 2')">🕸️ Spider-Man</button>
            <button class="chip" onclick="askChip('Games like Star Wars Jedi Survivor')">🗡️ Star Wars Jedi</button>
            <button class="chip" onclick="askChip('Games like Call of Duty')">🎯 Call of Duty</button>
            <button class="chip" onclick="askChip('Doom boomer shooters')">💥 Doom Shooters</button>
            <button class="chip" onclick="askChip('Fire Emblem tactical RPGs')">♟️ Fire Emblem</button>
            <button class="chip" onclick="askChip('Persona and JRPGs')">✨ Persona & JRPGs</button>
            <button class="chip" onclick="askChip('Baldurs Gate CRPGs')">🎲 Baldur's Gate</button>
            <button class="chip" onclick="askChip('Silent Hill survival horror')">🔦 Silent Hill</button>
            <button class="chip" onclick="askChip('Hitman stealth games')">🕶️ Hitman Stealth</button>
            <button class="chip" onclick="askChip('Cozy farming games like Stardew')">🌾 Stardew & Cozy</button>
            <button class="chip" onclick="askChip('Civilization strategy games')">👑 Civ 7 & 4X</button>
            <button class="chip" onclick="askChip('Gran Turismo racing games')">🏎️ Racing & Forza</button>
            <button class="chip" onclick="askChip('Street Fighter and Tekken fighting')">🥋 Fighting Games</button>
            <button class="chip" onclick="askChip('show me 2026 games rated 80+ or more')">🏆 2026 Games 80+</button>
        </div>
        <div class="chat-messages" id="chatMsgs">
            <div class="msg msg-pulsar">
                <p><strong>Hi! I'm Pulsar, your GamePulse AI Concierge.</strong></p>
                <p>I cover all 32 gaming genres and thousands of game archetypes (from <em>Diablo</em> and <em>Gears of War</em> to <em>Spider-Man 2</em>, <em>Star Wars Jedi</em>, <em>Fire Emblem</em>, <em>Silent Hill</em>, cozy sims, boomer shooters, and more).</p>
                <p>Ask for any genre, game recommendation, platform (PC, PS5, Xbox, Switch), or rating filter!</p>
            </div>
        </div>
        <div class="chat-input-bar">
            <input type="text" id="chatInput" placeholder="Ask about any genre or game..." onkeydown="if(event.key==='Enter') sendChat()">
            <button class="chat-send" onclick="sendChat()">➔</button>
        </div>
    </div>

    <footer>
        <p>GamePulse AI &copy; 2026 &bull; Real-time Gaming Intelligence & Concierge &bull; Clean Python Architecture</p>
    </footer>

    <script>
        function toggleChat() {{
            const d = document.getElementById('chatDrawer');
            if (d.style.display === 'flex') {{
                d.style.display = 'none';
            }} else {{
                d.style.display = 'flex';
                document.getElementById('chatInput').focus();
            }}
        }}

        function askChip(text) {{
            document.getElementById('chatInput').value = text;
            sendChat();
        }}

        function sendChat() {{
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
            loadDiv.innerHTML = '<em>Pulsar is analyzing games...</em>';
            box.appendChild(loadDiv);
            box.scrollTop = box.scrollHeight;

            fetch('/api/chat', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ message: msg }})
            }})
            .then(res => res.json())
            .then(data => {{
                loadDiv.remove();
                const pDiv = document.createElement('div');
                pDiv.className = 'msg msg-pulsar';
                
                let formatted = data.reply
                    .replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>')
                    .replace(/\\*(.*?)\\*/g, '<em>$1</em>')
                    .replace(/\\n/g, '<br>');
                pDiv.innerHTML = formatted;
                box.appendChild(pDiv);
                box.scrollTop = box.scrollHeight;
            }})
            .catch(err => {{
                loadDiv.remove();
                const eDiv = document.createElement('div');
                eDiv.className = 'msg msg-pulsar';
                eDiv.innerHTML = '<span style="color:var(--accent-red)">Error contacting Pulsar. Please retry!</span>';
                box.appendChild(eDiv);
            }});
        }}
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
    print(f"Loaded {len(ALL_ARCHETYPES)} all-encompassing genres & game archetypes.")
    init_db()
    print("Database initialized with cold-start multi-category dataset.")

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