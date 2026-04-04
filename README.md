# 🪙 Penny Hunter Bot

Automatically scans deal communities for penny items near **Wichita, KS** and
posts alerts to two Discord channels:

| Channel | What it receives |
|---|---|
| `#wichita-deals` | Wichita-area specific penny finds (orange embeds) |
| `#kansas-deals` | All Kansas penny finds including Wichita re-posts (blue embeds) |

Runs **every hour** for free via GitHub Actions. No server needed.

---

## Sources Monitored

- **PennyCentral.com** — Home Depot (community-reported, real-time)
- **TheFreebieGuy.com** — Dollar General penny list (updates Tuesdays)
- **KrazyCouponLady.com** — DG, Dollar Tree, Home Depot penny lists
- **RetailShout.com** — Multi-store penny finds
- **Reddit** — r/extremecouponing, r/frugal, r/pennyshopping, r/coupons

---

## Setup (one time, ~15 minutes)

### Step 1 — Create your Discord server & channels

1. Open Discord → click **+** to create a new server → name it "Penny Hunter"
2. Create two text channels:
   - `#wichita-deals`
   - `#kansas-deals`

### Step 2 — Create Discord Webhooks

For **each channel**:
1. Right-click the channel → **Edit Channel**
2. Go to **Integrations** → **Webhooks** → **New Webhook**
3. Name it "Penny Hunter Bot"
4. Click **Copy Webhook URL** — save it somewhere temporarily

### Step 3 — Fork this repo on GitHub

1. Go to [github.com](https://github.com) and sign in (free account)
2. Click **+** → **New repository**
3. Name it `penny-hunter`, set it to **Private**
4. Upload all files from this folder into it

### Step 4 — Add your webhook URLs as Secrets

1. In your GitHub repo → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret** and add:

   | Secret Name | Value |
   |---|---|
   | `DISCORD_WEBHOOK_WICHITA` | Your `#wichita-deals` webhook URL |
   | `DISCORD_WEBHOOK_KANSAS`  | Your `#kansas-deals` webhook URL |

### Step 5 — Enable Actions

1. Go to the **Actions** tab in your repo
2. Click **Enable GitHub Actions** if prompted
3. Click on **Penny Hunter Bot** → **Run workflow** to test it right now

---

## Customizing Your Cities

To add more cities to the Wichita radius or add new Kansas cities, open
`penny_hunter.py` and edit these lists near the top:

```python
# Cities considered "Wichita area" (~25 mile radius)
WICHITA_CITIES = [
    "wichita", "derby", "haysville", "andover", "goddard",
    "maize", "park city", "valley center", "mulvane",
    "augusta", "newton", "bel aire", "kechi",
    # Add more here ↓
]
```

---

## Adding More Discord Channels (e.g., a specific city you flag)

1. Create the new channel in Discord and grab its webhook URL
2. Add a new secret in GitHub (e.g., `DISCORD_WEBHOOK_LAWRENCE`)
3. In `penny_hunter.py`, add the new city to `WICHITA_CITIES` or a new list,
   and add a routing block in `main()` similar to the existing ones

---

## How the Location Filter Works

Every post/article is scanned for city and state keywords. Posts are routed:

- **Mentions Wichita / Derby / Andover / etc.** → `#wichita-deals` AND `#kansas-deals`
- **Mentions Kansas / KS / other KS cities** → `#kansas-deals` only
- **No Kansas relevance** → silently dropped

National penny lists (Dollar General, Dollar Tree) are always routed to
`#kansas-deals` since they apply to all stores including yours.

---

## Facebook Groups (Manual — Worth Doing)

Automated Facebook scraping gets accounts banned quickly. Instead, join these
groups manually and enable their notifications — you'll get real-time alerts
directly from locals in your area:

- **Home Depot Penny and Clearance Deals** (search on Facebook)
- **Dollar General Penny Shopping** (TheFreebieGuy's official group)
- **Extreme Couponing Wichita KS** (search for local groups)
- **eMoney Discord** (Home Depot penny deals — search for invite link)

---

## Run Schedule

The bot runs at **:05 past every hour** by default. To change this, edit
`.github/workflows/penny_hunt.yml` and modify the cron line:

```yaml
- cron: '5 * * * *'   # every hour
- cron: '5 */2 * * *' # every 2 hours
- cron: '5 9,12,15,18 * * *' # 9am, noon, 3pm, 6pm only
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| No alerts showing up | Run workflow manually from Actions tab; check logs |
| Duplicate alerts | The `seen_posts.json` file handles this automatically |
| Webhook not working | Double-check the secret name matches exactly |
| Rate limited by a site | Increase the sleep time in `penny_hunter.py` |
