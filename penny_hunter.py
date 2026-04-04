"""
Penny Hunter Bot
Scrapes deal communities for penny items near Wichita, KS
and posts alerts to Discord channels via a Bot Token.
"""

import requests
import json
import re
import os
import time
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────

# Discord Bot Token — stored as GitHub Secret: DISCORD_BOT_TOKEN
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")

# Your Discord channel IDs
CHANNEL_WICHITA = "1489745449546944605"
CHANNEL_KANSAS  = "1489746039002108094"

# How far back to look (minutes). Match your cron interval.
LOOKBACK_MINUTES = 65

# Cities considered "Wichita area" (~25 mile radius)
WICHITA_CITIES = [
    "wichita", "derby", "haysville", "andover", "goddard",
    "maize", "park city", "valley center", "mulvane",
    "augusta", "newton", "bel aire", "kechi",
]

# Broader Kansas keywords
KANSAS_KEYWORDS = [
    "kansas", " ks ", "(ks)", "ks -", "overland park", "topeka",
    "lawrence", "olathe", "salina", "manhattan", "lenexa",
    "shawnee", "leawood", "merriam", "prairie village",
    "hutchinson", "dodge city", "emporia", "garden city",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

STORE_EMOJI = {
    "home depot":     "🟠",
    "dollar general": "🟡",
    "dollar tree":    "🟢",
    "walmart":        "🔵",
    "target":         "🎯",
    "lowes":          "🔷",
    "walgreens":      "💊",
    "cvs":            "💊",
}


# ─────────────────────────────────────────────
#  LOCATION CLASSIFIER
# ─────────────────────────────────────────────

def classify_location(text):
    lower = text.lower()
    for city in WICHITA_CITIES:
        if city in lower:
            return "wichita"
    for kw in KANSAS_KEYWORDS:
        if kw in lower:
            return "kansas"
    return "none"


def detect_store(text):
    lower = text.lower()
    for store in STORE_EMOJI:
        if store in lower:
            return store.title()
    return "Unknown Store"


# ─────────────────────────────────────────────
#  DISCORD SENDER  (Bot Token + Channel ID)
# ─────────────────────────────────────────────

def send_discord(channel_id, title, description, url, store, source, color=0xFFD700):
    if not DISCORD_BOT_TOKEN:
        print(f"[WARN] No bot token set — skipping: {title}")
        return

    store_emoji = STORE_EMOJI.get(store.lower(), "🏪")
    timestamp   = datetime.now(timezone.utc).isoformat()
    api_url     = f"https://discord.com/api/v10/channels/{channel_id}/messages"

    headers = {
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
        "Content-Type":  "application/json",
    }
    payload = {
        "embeds": [{
            "title":       f"{store_emoji} {title}",
            "description": description[:2000],
            "url":         url,
            "color":       color,
            "footer":      {"text": f"Source: {source} • {timestamp[:10]}"},
            "timestamp":   timestamp,
        }]
    }

    try:
        r = requests.post(api_url, headers=headers, json=payload, timeout=10)
        r.raise_for_status()
        print(f"[✓] Posted to channel {channel_id}: {title[:60]}")
    except requests.HTTPError:
        print(f"[ERROR] Discord HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"[ERROR] Discord send failed: {e}")

    time.sleep(1)


# ─────────────────────────────────────────────
#  SCRAPER: REDDIT
# ─────────────────────────────────────────────

REDDIT_SUBS = ["extremecouponing", "frugal", "pennyshopping", "coupons"]

def scrape_reddit():
    print("[Reddit] Scanning...")
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=LOOKBACK_MINUTES)
    found  = []

    for sub in REDDIT_SUBS:
        try:
            r     = requests.get(f"https://www.reddit.com/r/{sub}/new.json?limit=50",
                                  headers=HEADERS, timeout=15)
            r.raise_for_status()
            posts = r.json()["data"]["children"]
        except Exception as e:
            print(f"[Reddit] Error on r/{sub}: {e}")
            continue

        for post in posts:
            d       = post["data"]
            created = datetime.fromtimestamp(d["created_utc"], tz=timezone.utc)
            if created < cutoff:
                continue

            full_text = f"{d.get('title','')} {d.get('selftext','')} {d.get('link_flair_text','')}"
            location  = classify_location(full_text)
            if location == "none":
                continue

            penny_kw = ["penny", "$.01", "$0.01", "one cent", "1 cent", "penny item", "penny deal"]
            if not any(kw in full_text.lower() for kw in penny_kw):
                continue

            found.append({
                "title":    d["title"],
                "text":     d.get("selftext", "")[:500],
                "url":      f"https://reddit.com{d['permalink']}",
                "store":    detect_store(full_text),
                "location": location,
                "source":   f"r/{sub}",
            })

    print(f"[Reddit] Found {len(found)} relevant posts")
    return found


# ─────────────────────────────────────────────
#  SCRAPER: PENNYCENTRAL.COM  (Home Depot)
# ─────────────────────────────────────────────

def scrape_pennycentral():
    print("[PennyCentral] Scanning...")
    found = []
    url   = "https://www.pennycentral.com"

    try:
        r    = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")

        page_text = soup.get_text(" ", strip=True)
        location  = classify_location(page_text)

        items = soup.find_all(["article", "div", "li"],
                               class_=re.compile(r"(item|deal|find|product|penny)", re.I))

        for item in items[:30]:
            text = item.get_text(" ", strip=True)
            loc  = classify_location(text)
            if loc == "none":
                continue

            link_tag = item.find("a", href=True)
            item_url = link_tag["href"] if link_tag else url
            found.append({
                "title":    text[:100].strip(),
                "text":     text[:400],
                "url":      item_url if item_url.startswith("http") else url + item_url,
                "store":    "Home Depot",
                "location": loc,
                "source":   "PennyCentral.com",
            })

        if not found and location != "none":
            found.append({
                "title":    "New Home Depot Penny Finds — Check PennyCentral",
                "text":     "Kansas area mentioned in today's penny list. Visit PennyCentral for details.",
                "url":      url,
                "store":    "Home Depot",
                "location": location,
                "source":   "PennyCentral.com",
            })

    except Exception as e:
        print(f"[PennyCentral] Error: {e}")

    print(f"[PennyCentral] Found {len(found)} relevant items")
    return found


# ─────────────────────────────────────────────
#  SCRAPER: THE FREEBIE GUY  (Dollar General)
# ─────────────────────────────────────────────

def scrape_thefreebieguy():
    print("[TheFreebieGuy] Scanning DG Penny List...")
    found = []
    url   = "https://thefreebieguy.com/dollar-general-penny-shopping-master-list/"

    try:
        r    = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")

        heading   = soup.find(["h1", "h2"])
        title     = heading.get_text(strip=True) if heading else "Dollar General Penny List Update"
        page_text = soup.get_text(" ", strip=True)

        penny_items = []
        for li in soup.find_all("li"):
            text = li.get_text(strip=True)
            if any(kw in text.lower() for kw in ["penny", "$.01", "$0.01"]):
                penny_items.append(text[:120])

        if penny_items:
            desc = (
                "**This week's Dollar General penny items** "
                "(valid nationwide — check your local Wichita/KS stores):\n\n"
                + "\n".join(f"• {item}" for item in penny_items[:15])
            )
            found.append({
                "title": title, "text": desc, "url": url,
                "store": "Dollar General", "location": "kansas",
                "source": "TheFreebieGuy.com",
            })
        elif "penny" in page_text.lower():
            found.append({
                "title": "Dollar General Penny List Updated",
                "text":  "Check TheFreebieGuy for this week's DG penny items.",
                "url":   url, "store": "Dollar General",
                "location": "kansas", "source": "TheFreebieGuy.com",
            })

    except Exception as e:
        print(f"[TheFreebieGuy] Error: {e}")

    print(f"[TheFreebieGuy] Found {len(found)} items")
    return found


# ─────────────────────────────────────────────
#  SCRAPER: KRAZY COUPON LADY
# ─────────────────────────────────────────────

KCL_PAGES = [
    ("https://thekrazycouponlady.com/tips/store-hacks/dollar-general-penny-list", "Dollar General"),
    ("https://thekrazycouponlady.com/tips/store-hacks/home-depot-penny-items",    "Home Depot"),
    ("https://thekrazycouponlady.com/tips/store-hacks/dollar-tree-penny-list",    "Dollar Tree"),
]

def scrape_krazycouponlady():
    print("[KrazyCouponLady] Scanning...")
    found = []

    for page_url, store in KCL_PAGES:
        try:
            r    = requests.get(page_url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")

            date_el  = soup.find(["time", "span"], class_=re.compile(r"(date|updated|time)", re.I))
            date_str = date_el.get_text(strip=True) if date_el else "recently"
            location = classify_location(soup.get_text(" ", strip=True))

            items = []
            for li in soup.find_all("li")[:60]:
                text = li.get_text(strip=True)
                if any(kw in text.lower() for kw in ["penny", "0.01", "$.01", "one cent"]):
                    items.append(text[:120])

            if items:
                desc = (
                    f"**{store} penny items** (updated {date_str}):\n\n"
                    + "\n".join(f"• {i}" for i in items[:10])
                    + f"\n\n[See full list →]({page_url})"
                )
                found.append({
                    "title":    f"{store} Penny List — KrazyCouponLady",
                    "text":     desc, "url": page_url, "store": store,
                    "location": location if location != "none" else "kansas",
                    "source":   "KrazyCouponLady.com",
                })

        except Exception as e:
            print(f"[KrazyCouponLady] Error on {store}: {e}")

    print(f"[KrazyCouponLady] Found {len(found)} items")
    return found


# ─────────────────────────────────────────────
#  SCRAPER: RETAILSHOUT.COM
# ─────────────────────────────────────────────

def scrape_retailshout():
    print("[RetailShout] Scanning...")
    found = []
    url   = "https://retailshout.com"

    try:
        r    = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")

        for article in soup.find_all(["article", "div"],
                                      class_=re.compile(r"(post|article|deal)", re.I))[:20]:
            text     = article.get_text(" ", strip=True)
            location = classify_location(text)

            if not any(kw in text.lower() for kw in ["penny", "$.01", "$0.01", "one cent"]):
                continue

            link     = article.find("a", href=True)
            href     = link["href"] if link else url
            title_el = article.find(["h2", "h3", "h4"])
            title    = title_el.get_text(strip=True) if title_el else text[:80]

            found.append({
                "title":    title, "text": text[:400],
                "url":      href if href.startswith("http") else url + href,
                "store":    detect_store(text),
                "location": location if location != "none" else "kansas",
                "source":   "RetailShout.com",
            })

    except Exception as e:
        print(f"[RetailShout] Error: {e}")

    print(f"[RetailShout] Found {len(found)} items")
    return found


# ─────────────────────────────────────────────
#  DEDUPLICATION
# ─────────────────────────────────────────────

SEEN_FILE = "seen_posts.json"

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen)[-500:], f)

def make_key(item):
    return f"{item['source']}::{item['title'][:60]}"


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def main():
    print(f"\n{'='*50}")
    print(f"Penny Hunter running at {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")

    seen      = load_seen()
    all_items = (
        scrape_reddit()
        + scrape_pennycentral()
        + scrape_thefreebieguy()
        + scrape_krazycouponlady()
        + scrape_retailshout()
    )

    print(f"\nTotal candidates: {len(all_items)}")
    wichita_sent = kansas_sent = 0

    for item in all_items:
        key = make_key(item)
        if key in seen:
            continue
        seen.add(key)

        if item["location"] == "wichita":
            send_discord(CHANNEL_WICHITA, item["title"], item["text"],
                         item["url"], item["store"], item["source"], color=0xFF6B00)
            send_discord(CHANNEL_KANSAS, f"[Wichita] {item['title']}", item["text"],
                         item["url"], item["store"], item["source"], color=0xFF6B00)
            wichita_sent += 1

        elif item["location"] == "kansas":
            send_discord(CHANNEL_KANSAS, item["title"], item["text"],
                         item["url"], item["store"], item["source"], color=0x00BFFF)
            kansas_sent += 1

    save_seen(seen)
    print(f"\n{'='*50}")
    print(f"Done. Wichita alerts: {wichita_sent} | Kansas alerts: {kansas_sent}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
