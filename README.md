# Casino Welcome Bonuses

A small scraper that pulls 3 casino welcome bonuses from a public comparison
site, uses Claude Opus to turn the free-text terms into structured fields,
saves them to JSON, and builds a simple Bootstrap 5 web page from that JSON.

**Live on Cloudflare:** https://casino.devbridge.co.za (also
https://casino-bonus-scrapper.sharifndlovu.workers.dev). See [Live site](#live-site).

## What it collects

For each of 3 casinos:

| Field | Example |
|---|---|
| Welcome bonus | `250% up to $9,000 + 250 FS` |
| Wagering requirement (multiplier) | `40` (shown as `40x`) |
| Minimum deposit | `$20` |
| Source URL | `https://www.casino.org/bonuses/` |

Times on the page are shown in SAST (South Africa Standard Time); `data/casinos.json` stores UTC.
Anything missing is stored as `null` and shown as "n/a" on the page. Before the
first scrape the page shows three rows of "n/a".

## Live site

The page is hosted on Cloudflare (Workers static assets) at:

- https://casino.devbridge.co.za
- https://casino-bonus-scrapper.sharifndlovu.workers.dev

Deploying publishes the contents of `public/` only:

```bash
npx wrangler deploy
```

Note: the nightly cron job refreshes the files on this machine. The live site
only shows new data after the next `npx wrangler deploy`.

## Setup

You need Python 3.10+ and an Anthropic API key.

```bash
# 1. Create a virtual environment and install dependencies
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Add your API key to a .env file in this folder
echo 'ANTHROPIC_API_KEY=your-key-here' > .env
```

`.env` and `.venv/` are listed in `.gitignore`, so your key is not committed.

## Run it

One command updates the data and the page:

```bash
.venv/bin/python scrape.py
```

Then view the page. It is plain HTML with no JavaScript (`public/index.html`), so you
can open it directly, or serve it locally with Wrangler (Cloudflare's dev server,
needs Node):

```bash
npx wrangler dev          # http://localhost:8787
```

Wrangler serves only the `public/` folder (see `wrangler.jsonc`), so `.env` and the
source files are never exposed.

To rebuild the page from the existing JSON without scraping or calling the API:

```bash
.venv/bin/python render.py
```

## Nightly refresh

**The data refreshes automatically every night at 02:00 SAST (the machine's local time).** A cron
job runs `scrape.py`, which re-scrapes the source, re-runs the Opus extraction,
rewrites `data/casinos.json` and rebuilds `public/index.html`. Reload the page in the
morning to see the new data. The "Last updated" line shows when it last ran.

A static page can't run Python by itself, and there is no server, so the
refresh is a normal cron job that runs from this folder. It is managed with
`schedule.py`:

```bash
.venv/bin/python schedule.py install     # every night at 02:00 SAST
.venv/bin/python schedule.py status
.venv/bin/python schedule.py uninstall
```

- Output is appended to `data/cron.log`.
- The job only runs while the computer is on at 02:00. A missed run is not
  caught up later; run `python scrape.py` by hand if needed.
- To change the time, edit `TIME` at the top of `schedule.py` and run `install` again.
- If a night's scrape fails (blocked, no network), the previous data stays in place.

## Failure alerts (healthchecks.io)

Each run reports to [healthchecks.io](https://healthchecks.io) (free), which
emails you when something is wrong:

1. Create a check there, set its period to 1 day with a grace time of a few hours,
   and add your email (or Slack etc.) as the alert channel.
2. Put its ping URL in `.env`:

   ```text
   HEALTHCHECK_URL=https://hc-ping.com/your-uuid
   ```

- **Success:** `scrape.py` pings the URL after the data is saved and the page is rendered.
- **Error:** any failure (blocked source, Opus error, render crash) pings
  `<url>/fail` with the traceback, and you get an email straight away.
- **Never ran:** if the computer was off or cron is broken, no ping arrives and
  healthchecks.io alerts you once the grace time passes.
- If `HEALTHCHECK_URL` is not set, alerts are simply off. The scrape still works.

## How it works

```
scrape.py  ->  fetch + parse  ->  Claude Opus  ->  data/casinos.json  ->  render.py  ->  public/index.html
```

1. **Fetch:** `scrape.py` reads the comparison table on `casino.org/bonuses/`
   and takes the first 3 rows.
2. **Extract:** the raw cell text (for example `35x deposit & bonus, 40x free spins`)
   is sent to `claude-opus-5-5`, which returns structured JSON that is forced
   to match a schema.
3. **Save:** the result is written to `data/casinos.json`. The file is written
   to a temp file first and then swapped in, so a failed run never leaves a
   half-written file.
4. **Render:** `render.py` turns the JSON into a static `public/index.html`.

## Scraping rules

- Checks `robots.txt` before fetching and sends an honest User-Agent.
- Never tries to get around logins, CAPTCHAs or blocks. If a source disallows
  us, returns a non-200 status, or serves a block page, it is skipped and the
  next source in `SOURCES` (top of `scrape.py`) is tried.
- If no source works, the run stops and the existing data is left untouched.
- `SOURCES` currently holds one site. To add a fallback, append another
  comparison page with a similar table (the parser looks for a table with a
  "Wagering" column).

## Files

| File | Purpose |
|---|---|
| `scrape.py` | Entry point: scrape, extract with Opus, write JSON, render page |
| `schedule.py` | Installs/removes the nightly cron job |
| `healthcheck.py` | Sends success/failure pings to healthchecks.io |
| `render.py` | Builds `public/index.html` from `data/casinos.json` |
| `wrangler.jsonc` | Wrangler config: serves `public/` locally |
| `data/casinos.json` | Latest scraped data |
| `public/index.html` | Generated page. Don't edit by hand, it is overwritten on each run |
| `requirements.txt` | Python dependencies |
| `.env` | Your API key (not committed) |

## Notes

- The 3 casinos are simply the top 3 rows of the source table, so they change
  when the site reorders its list.
- The wagering number is the requirement on the bonus only. A row like
  `40x bonus, 35x free spins` gives `40`.
- Each run makes one small Opus request (a few cents at most).
