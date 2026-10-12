"""Scrape 3 casino bonuses from a public comparison table, normalise the
free-text terms with Claude Opus, and write data/casinos.json.

Run:  python scrape.py
"""
import json
import os
import sys
import traceback
import urllib.parse
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path

import anthropic
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from healthcheck import ping
from render import render, write_atomic

HERE = Path(__file__).parent
OUT = HERE / "data" / "casinos.json"
MODEL = "claude-opus-5-5"
COUNT = 3
UA = "CasinoBonusDemoBot/1.0 (educational; contact: sharifndlovu@gmail.com)"

SOURCES = [
    "https://www.casino.org/bonuses/",
]

BLOCK_MARKERS = ("captcha", "access denied", "are you a robot", "verify you are human")

SCHEMA = {
    "type": "object",
    "properties": {
        "casinos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "welcome_bonus": {"type": "string"},
                    "wagering_multiplier": {"type": ["number", "null"]},
                    "min_deposit": {"type": ["string", "null"]},
                },
                "required": ["name", "welcome_bonus", "wagering_multiplier", "min_deposit"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["casinos"],
    "additionalProperties": False,
}

PROMPT = """Below are raw table cells scraped from a casino comparison page, as JSON.
For each casino return:
- name: the casino name, unchanged
- welcome_bonus: the welcome offer as a short clean string (drop emoji/medal icons, keep amounts and free spins)
- wagering_multiplier: the wagering requirement on the BONUS as a plain number (e.g. "40x bonus, 35x free spins" -> 40; "35x deposit & bonus" -> 35). null if not stated.
- min_deposit: the minimum deposit including currency symbol (e.g. "$30"). null if not stated.
Use only what the text says; never guess. Keep the same order.

{rows}"""


def allowed_by_robots(url: str) -> bool:
    parts = urllib.parse.urlsplit(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    try:
        r = requests.get(robots_url, headers={"User-Agent": UA}, timeout=15)
    except requests.RequestException:
        return False
    if r.status_code in (401, 403):
        return False  # robots.txt itself is blocked: treat as disallowed
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(r.text.splitlines() if r.ok else [])
    return rp.can_fetch(UA, url)


def fetch_rows(url: str) -> list[dict] | None:
    """Return the first COUNT rows of the bonus comparison table, or None if unusable."""
    if not allowed_by_robots(url):
        print(f"  skip: robots.txt disallows {url}")
        return None
    r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
    if r.status_code != 200:
        print(f"  skip: HTTP {r.status_code}")
        return None
    if any(m in r.text.lower() for m in BLOCK_MARKERS):
        print("  skip: page looks like a CAPTCHA / block page")
        return None

    soup = BeautifulSoup(r.text, "html.parser")
    for table in soup.find_all("table"):
        heads = [th.get_text(" ", strip=True).lower() for th in table.find_all("th")]
        if not any("wagering" in h for h in heads):
            continue
        col = lambda word: next(i for i, h in enumerate(heads) if word in h)
        bonus, deposit, wagering = col("bonus"), col("deposit"), col("wagering")
        rows = []
        for tr in table.find("tbody").find_all("tr")[:COUNT]:
            td = [c.get_text(" ", strip=True) for c in tr.find_all("td")]
            rows.append({
                "name": td[0],
                "bonus_text": td[bonus],
                "min_deposit_text": td[deposit],
                "wagering_text": td[wagering],
            })
        if len(rows) == COUNT:
            return rows
    print("  skip: comparison table not found")
    return None


def structure_with_llm(rows: list[dict]) -> list[dict]:
    resp = anthropic.Anthropic().messages.create(  # reads ANTHROPIC_API_KEY
        model=MODEL,
        max_tokens=8000,  # thinking tokens count against this, so leave headroom
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": PROMPT.format(rows=json.dumps(rows, ensure_ascii=False))}],
    )
    if resp.stop_reason != "end_turn":
        raise RuntimeError(f"LLM stopped early: {resp.stop_reason}")
    casinos = json.loads(next(b.text for b in resp.content if b.type == "text"))["casinos"]
    if len(casinos) != len(rows):
        raise RuntimeError("LLM returned a different number of casinos")
    return casinos


def run() -> None:
    """Do the whole job; raise on any failure."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is not set (put it in .env)")

    for url in SOURCES:
        print(f"Trying {url}")
        rows = fetch_rows(url)
        if rows:
            break
    else:
        raise RuntimeError("No usable source (blocked, disallowed or changed) - existing data left untouched")

    casinos = structure_with_llm(rows)
    for c in casinos:
        c["source_url"] = url
    payload = {"updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "casinos": casinos}
    write_atomic(OUT, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {len(casinos)} casinos to {OUT.relative_to(HERE)}")
    render()


def main() -> int:
    load_dotenv(HERE / ".env")
    try:
        run()
    except Exception:
        err = traceback.format_exc()
        print(err, file=sys.stderr)
        ping(False, err)
        return 1
    ping(True, "ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
