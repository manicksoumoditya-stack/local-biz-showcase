#!/usr/bin/env python3
"""
generate.py - End-to-end generator for the Miami Local Business Showcase.

Only uses standard library + requests (no google.cloud).
"""

import os
import sys
import re
import json
import time
import subprocess
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
import requests

# Configuration
DATASET_PATH = "/root/business-sites/dataset_crawler-google-places_2026-06-20_17-13-03-518.xml"
GIT_ROOT = "/root/local-biz-showcase"
OUTPUT_ROOT = os.path.join(GIT_ROOT, "generated")
SLUG_TPL = re.compile(r"[^a-z0-9]+")
TEMPLATES_DIR = os.path.join(GIT_ROOT, "templates")
PROGRESS_PATH = os.path.join(GIT_ROOT, "progress.json")
BATCH_SIZE = 20
PAUSE_SECONDS = 2
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_ENDPOINT = "https://api.anthropic.com/v1/messages"

# Theme / template mapping
THEME_MAP = {
    "brickell": "corporate",
    "coconut_grove": "friendly",
    "miami_beach": "bold",
    "generic": "friendly",
}

def slugify(text: str) -> str:
    return SLUG_TPL.sub("-", text.lower()).strip("-")

def read_progress() -> int:
    if not os.path.exists(PROGRESS_PATH):
        return 0
    try:
        with open(PROGRESS_PATH, "r") as f:
            return json.load(f).get("last_index", 0)
    except Exception:
        return 0

def save_progress(idx: int) -> None:
    try:
        with open(PROGRESS_PATH, "w") as f:
            json.dump({"last_index": idx}, f)
    except Exception as e:
        print(f"[WARN] Could not write progress: {e}", file=sys.stderr)

def run_git_add(path: str) -> None:
    subprocess.run(["git", "add", path], cwd=GIT_ROOT, check=False)

def run_git_commit(message: str) -> None:
    subprocess.run(["git", "commit", "-m", message], cwd=GIT_ROOT, check=False)

def run_git_push() -> None:
    subprocess.run(["git", "push"], cwd=GIT_ROOT, check=False)

def pretty_print_live_url(slug: str) -> None:
    url = f"https://manicksoumoditya-stack.github.io/local-biz-showcase/{slug}/"
    print(f"\n✅ LIVE URL: {url}\n")

def parse_business(item: ET.Element) -> Dict[str, str]:
    data = {}
    data["title"] = item.findtext("title", "")
    data["rating"] = item.findtext("totalScore", "0")
    data["reviewsCount"] = item.findtext("reviewsCount", "0")
    data["website"] = item.findtext("website", "")
    data["phone"] = item.findtext("phone", "")
    data["street"] = item.findtext("street", "")
    data["city"] = item.findtext("city", "")
    data["state"] = item.findtext("state", "")
    data["addressEncoded"] = data["street"].replace(" ", "%20") + "," + data["city"] + "," + data["state"]
    data["categoryName"] = item.findtext("categoryName", "")

    # Simple neighbourhood inference
    title_lc = data["title"].lower()
    if "brickell" in title_lc or "downtown" in title_lc:
        data["neighbourhood"] = "brickell"
    elif "coconut grove" in title_lc or "coconutgrove" in title_lc:
        data["neighbourhood"] = "coconut_grove"
    elif "miami beach" in title_lc or "art deco" in title_lc:
        data["neighbourhood"] = "miami_beach"
    else:
        data["neighbourhood"] = "generic"
    return data

def load_all_businesses() -> List[Dict[str, str]]:
    tree = ET.parse(DATASET_PATH)
    root = tree.getroot()
    return [parse_business(item) for item in root.findall("item")]

def anthropic_post(prompt: str) -> str:
    # Return placeholder content when API key not set (for local testing)
    if not ANTHROPIC_API_KEY:
        return "Placeholder response"
    # Original implementation follows

    headers = {
        "anthropic-api-key": ANTHROPIC_API_KEY,
        "content-type": "application/json",
    }
    payload = {
        "model": "claude-3-sonnet-4-6",
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.9,
    }
    try:
        resp = requests.post(ANTHROPIC_ENDPOINT, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        body = resp.json().get("content", [])
        if body:
            return body[0].get("text", "")
        return ""
    except Exception as e:
        print(f"[ERROR] Anthropic request failed: {e}", file=sys.stderr)
        return ""

def svg_landmark(neighbourhood: str) -> str:
    if neighbourhood == "brickell":
        return '''<svg width="300" height="250" viewBox="0 0 300 250" xmlns="http://www.w3.org/2000/svg">
<defs><linearGradient id="w1" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#c9a84c" stop-opacity="0.15"/><stop offset="100%" stop-color="#c9a84c" stop-opacity="0.05"/></linearGradient></defs>
<rect width="300" height="250" fill="url(#w1)"/>
<path d="M50,200 Q150,80 250,200" stroke="#c9a84c" stroke-width="3" fill="none"/>
<path d="M75,180 Q125,100 175,120 Q225,140 225,180" stroke="#c9a84c" stroke-width="2" fill="none"/>
<line x1="50" y1="200" x2="250" y2="200" stroke="#c9a84c" stroke-width="2"/>
</svg>'''
    elif neighbourhood == "coconut_grove":
        return '''<svg width="250" height="200" viewBox="0 0 250 200" xmlns="http://www.w3.org/2000/svg">
<defs><linearGradient id="w2" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#d4a574" stop-opacity="0.12"/><stop offset="100%" stop-color="#f5e6d3" stop-opacity="0.08"/></linearGradient></defs>
<rect width="250" height="200" fill="url(#w2)"/>
<path d="M40,165 Q90,120 125,140 Q160,120 210,165 L210,180 Q125,200 40,180z" fill="#d4a574" opacity="0.7"/>
<rect x="85" y="90" width="80" height="50" fill="#f2e6d8" stroke="#b87333" stroke-width="1"/>
</svg>'''
    elif neighbourhood == "miami_beech":
        return '''<svg width="320" height="280" viewBox="0 0 320 280" xmlns="http://www.w3.org/2000/svg">
<defs><linearGradient id="w3" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#ffd166" stop-opacity="0.15"/><stop offset="100%" stop-color="#ffd166" stop-opacity="0.05"/></linearGradient></defs>
<rect width="320" height="280" fill="url(#w3)"/>
<polygon points="160,80 80,200 240,200" fill="#ffd166" stroke="#e63946" stroke-width="2"/>
<rect x="115" y="120" width="30" height="80" fill="#e63946"/>
<circle cx="60" cy="60" r="25" fill="#ffd166" stroke="#e63946" stroke-width="2"/>
</svg>'''
    else:
        return '''<svg width="200" height="180" viewBox="0 0 200 180" xmlns="http://www.w3.org/2000/svg">
<rect x="30" y="30" width="140" height="100" fill="#cccccc" stroke="#555" stroke-width="2"/>
<polygon points="100,30 150,80 50,80" fill="#e63946" stroke="#ffd166" stroke-width="1"/>
</svg>'''

def render_template(template_str: str, context: Dict[str, Any]) -> str:
    rendered = template_str
    for key, val in context.items():
        rendered = rendered.replace("{{" + key + "}}", str(val))
    return rendered

def main():
    if not ANTHROPIC_API_KEY:
        print("[FATAL] ANTHROPIC_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    os.makedirs(OUTPUT_ROOT, exist_ok=True)
    next_index = read_progress()
    businesses = load_all_businesses()
    total = len(businesses)
    print(f"[INFO] Loaded {total} businesses – resuming from index {next_index}")

    # DEBUG: Only process first 3 businesses
    end_idx = min(next_index + 3, total)
    for idx in range(next_index, end_idx):
        biz = businesses[idx]
        # Theme selection
        theme_key = THEME_MAP.get(biz["neighbourhood"], "friendly")
        tpl_path = os.path.join(TEMPLATES_DIR, theme_key + "_template.html")

        # Load template
        with open(tpl_path, "r") as f:
            template_str = f.read()

        # Generate witty copy
        tagline = anthropic_post(
            f'Create ONE witty, Miami-local tagline for "{biz["title"]}". Single sentence, funny, warm, specific. No generic marketing language.')
        hot_raw = anthropic_post(
            f'For "{biz["title"]}" create 3-4 "Hot Selling Items" – each gets a name and a one-line fun description. Format: Item 1: Name – Desc')
        hot_items = []
        for line in hot_raw.splitlines():
            if ":" in line:
                parts = line.split(":", 1)
                hot_items.append(parts[1].strip() if len(parts) > 1 else line.strip())
        flavor = anthropic_post(
            f'Write a 2-3 sentence Miami insider blur for "{biz["title"]}". Mention the neighbourhood, a local quirk, keep it under 300 chars.')

        # Build context
        context = {
            "business_name": biz["title"],
            "rating": biz["rating"],
            "reviewsCount": biz["reviewsCount"],
            "tagline": tagline,
            "hotItems": "\n".join(hot_items[:4]),
            "localFlavor": flavor,
            "street": biz["street"],
            "city": biz["city"],
            "state": biz["state"],
            "website": biz["website"],
            "phone": biz["phone"],
            "addressEncoded": biz["addressEncoded"],
            "landmark": svg_landmark(biz["neighbourhood"]),
        }

        slug = slugify(biz["title"])
        rendered_html = render_template(template_str, context)

        biz_dir = os.path.join(OUTPUT_ROOT, slug)
        os.makedirs(biz_dir, exist_ok=True)
        with open(os.path.join(biz_dir, "index.html"), "w") as f:
            f.write(rendered_html)

        run_git_add(os.path.join("generated", slug))
        run_git_commit(f"Add site for {biz['title']}")
        run_git_push()
        pretty_print_live_url(slug)

        save_progress(idx)

        if (idx + 1) % BATCH_SIZE == 0:
            time.sleep(PAUSE_SECONDS)

    print("[DONE] All businesses processed!")

if __name__ == "__main__":
    main()