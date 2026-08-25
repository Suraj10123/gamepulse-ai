# 🎮 GamePulse AI

> **Live Deployment:** [https://gamepulse-ai-c3fn.onrender.com](https://gamepulse-ai-c3fn.onrender.com)

GamePulse is an independent, real-time video game news aggregator, review digest, and AI concierge platform built with **pure Python standard library** (zero third-party package dependencies). I made this using Gemini to brainstorm ideas for a simple gaming news aggregate site that pulls news from various sites.

**Keep in mind that there was quite a bit of genAI code to this, as I wanted to adapt AI usage to a fun little project use case.**
---

## ⚡ Key Features

* **📰 100% Live Multi-Source Ingestion:** Automated 15-minute background daemon aggregating, sanitizing, and indexing feeds from IGN, GameSpot, Eurogamer, PC Gamer, GamesIndustry.biz, Gematsu, Polygon, and r/GamingLeaksAndRumours.
* **🛡️ Freshness Gatekeeper:** Automatically filters and drops outdated stories (>14 days), guaranteeing authentic real-time timestamps and verified media enclosures.
* **🤖 "Pulsey" Conversational AI:** Interactive gaming concierge powered by Groq Llama-3.1 with multi-turn session memory, typo-tolerant fuzzy matching, and mechanical taste-mapping across 20 gaming genres.
* **⭐ Live OpenCritic Verification:** Real-time critic ratings, review tiers (Mighty/Strong), and score breakdowns.
* **📱 Fully Responsive Design:** Clean dark-mode editorial UI optimized for desktop, tablet, and mobile with a full-screen bottom-sheet chat modal.

---

## 🛠️ Tech Stack

* **Backend:** Python 3 (`http.server`, `sqlite3`, `threading`, `urllib`, `xml.etree.ElementTree`)
* **Frontend:** Vanilla JavaScript (ES6+), HTML5, Responsive CSS3
* **AI & Data:** Groq Cloud API (`llama-3.1-8b-instant`), OpenCritic REST API
* **Deployment & CI/CD:** Render, GitHub
