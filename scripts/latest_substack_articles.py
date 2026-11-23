#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Puts a slider of all Substack articles on the homepage, newest first.

1. Downloads the list of every post from the Substack API
   (https://afrinarchive.substack.com/api/v1/posts). Each post carries its
   language: "en", "ar" or "ku".
2. Pairs each Arabic article with the English article published closest to it
   (within 2 days). Posts with no partner in the other language, such as lecture
   announcements and the Kurdish version of the caves article, are left out.
3. Writes one slide per pair into index.html, English card on the left and Arabic
   card on the right, between the markers <!-- LATEST-ARTICLES:START --> and
   <!-- LATEST-ARTICLES:END -->. The arrows and swiping are handled by a small
   script in index.html that does not change between runs.

If Substack cannot be reached, index.html is left exactly as it was,
so the slides from the last successful run stay on the page.

GitHub runs this every day (.github/workflows/update-articles.yml) and the
desktop site updater runs it as step 9.
"""

import html
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_FILE = BASE_DIR / "index.html"
API_URL = "https://afrinarchive.substack.com/api/v1/posts?limit=50"
SITE_HOST = "afrinarchive.substack.com"
PAIR_WINDOW = timedelta(days=2)
IMAGE_WIDTH = 960  # pixels; Substack's image server resizes the cover pictures

START_MARKER = "<!-- LATEST-ARTICLES:START -->"
END_MARKER = "<!-- LATEST-ARTICLES:END -->"

ARABIC_LETTERS = re.compile(r"[\u0600-\u06FF]")

ENGLISH_MONTHS = ["January", "February", "March", "April", "May", "June", "July",
                  "August", "September", "October", "November", "December"]
# Month names as used in Syria
ARABIC_MONTHS = ["كانون الثاني", "شباط", "آذار", "نيسان", "أيار", "حزيران", "تموز",
                 "آب", "أيلول", "تشرين الأول", "تشرين الثاني", "كانون الأول"]
ARABIC_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def fetch_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def download_posts():
    """Returns every published post. Follows Substack's page cursor if there are more than 50."""
    posts, url, seen_cursors = [], API_URL, set()
    while True:
        data = fetch_json(url)
        batch = data.get("posts", []) if isinstance(data, dict) else data
        posts.extend(batch)
        cursor = data.get("nextCursor") if isinstance(data, dict) else None
        if not cursor or not batch or cursor in seen_cursors:
            return posts
        seen_cursors.add(cursor)
        url = f"{API_URL}&cursor={urllib.parse.quote(str(cursor))}"


def clean_text(value):
    text = html.unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def resized_image(url):
    if not url:
        return ""
    if url.startswith("https://substackcdn.com/image/fetch/"):
        return url
    return (f"https://substackcdn.com/image/fetch/w_{IMAGE_WIDTH},c_limit,f_auto,q_auto:good,"
            f"fl_progressive:steep/{urllib.parse.quote(url, safe='')}")


def focal_point(crop):
    """The focus point set on the cover picture in Substack's editor, as (x, y) from 0 to 1, or None."""
    if not isinstance(crop, dict):
        return None
    try:
        x, y = float(crop.get("x")), float(crop.get("y"))
    except (TypeError, ValueError):
        return None
    if 0 <= x <= 1 and 0 <= y <= 1:
        return x, y
    return None


def to_entry(post):
    title = clean_text(post.get("title"))
    link = (post.get("canonical_url") or "").strip()
    try:
        published = datetime.fromisoformat((post.get("post_date") or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    if not title or not link or not post.get("is_published", True):
        return None
    language = (post.get("language") or "").lower()
    if not language:
        language = "ar" if ARABIC_LETTERS.search(title) else "en"
    return {
        "title": title,
        "subtitle": clean_text(post.get("subtitle")),
        "link": link,
        "image": resized_image(post.get("cover_image") or ""),
        "focus": focal_point(post.get("cover_image_crop")),
        "published": published,
        "language": language,
    }


def pair_articles(entries):
    english = [entry for entry in entries if entry["language"] == "en"]
    arabic = sorted((entry for entry in entries if entry["language"] == "ar"),
                    key=lambda entry: entry["published"], reverse=True)
    used, pairs = set(), []
    for ar in arabic:
        candidates = [en for en in english
                      if id(en) not in used and abs(en["published"] - ar["published"]) <= PAIR_WINDOW]
        if not candidates:
            print(f"  [skipped, no English partner] {ar['title']}")
            continue
        en = min(candidates, key=lambda entry: abs(entry["published"] - ar["published"]))
        used.add(id(en))
        pairs.append((en, ar))
    for en in english:
        if id(en) not in used:
            print(f"  [skipped, no Arabic partner] {en['title']}")
    pairs.sort(key=lambda pair: pair[0]["published"], reverse=True)
    return pairs


def format_date(published, arabic):
    if arabic:
        return f"{published.day} {ARABIC_MONTHS[published.month - 1]} {published.year}".translate(ARABIC_DIGITS)
    return f"{published.day} {ENGLISH_MONTHS[published.month - 1]} {published.year}"


def build_card(entry, first_slide):
    arabic = entry["language"] == "ar"
    esc = lambda value: html.escape(value, quote=True)
    lang_attrs = ' lang="ar" dir="rtl"' if arabic else ' lang="en"'
    side_class = "article-card-ar" if arabic else "article-card-en"
    image_html = ""
    if entry["image"]:
        # The first slide is visible straight away; the rest load as the reader moves to them.
        # Where the picture is cropped to fit the wide frame:
        #   1. the focus point set in Substack's editor is used, if there is one;
        #   2. otherwise square and tall pictures are cropped from near the top, so heads
        #      are not cut off (Substack puts the size in the file name, e.g. _573x823.png);
        #   3. otherwise the picture is cropped around its middle.
        loading = "eager" if first_slide else "lazy"
        image_class, style = "article-card-image", ""
        if entry.get("focus"):
            x, y = entry["focus"]
            style = f' style="object-position: {x * 100:.0f}% {y * 100:.0f}%"'
        else:
            size = re.search(r"_(\d+)x(\d+)\.(?:png|jpe?g|webp|gif)", entry["image"], re.IGNORECASE)
            if size and int(size.group(2)) >= 0.9 * int(size.group(1)):
                image_class += " article-card-image-tall"
        image_html = (f'\n                    <img class="{image_class}"{style} src="{esc(entry["image"])}" alt="" '
                      f'loading="{loading}" decoding="async">')
    subtitle_html = ""
    if entry["subtitle"]:
        subtitle_html = f'\n                        <p class="article-card-subtitle">{esc(entry["subtitle"])}</p>'
    return (
        f'                <a class="article-card {side_class}" href="{esc(entry["link"])}" target="_blank" rel="noopener"{lang_attrs}>'
        f'{image_html}\n'
        f'                    <div class="article-card-body">\n'
        f'                        <div class="article-card-meta">{esc(format_date(entry["published"], arabic))}</div>\n'
        f'                        <h3 class="article-card-title">{esc(entry["title"])}</h3>'
        f'{subtitle_html}\n'
        f'                        <div class="article-card-source">{SITE_HOST}</div>\n'
        f'                    </div>\n'
        f'                </a>'
    )


def build_block(pairs):
    total = len(pairs)
    slides = []
    for number, (en, ar) in enumerate(pairs, start=1):
        first = number == 1
        slides.append(
            f'            <div class="articles-slide" role="group" aria-roledescription="slide" aria-label="{number} of {total}">\n'
            f'{build_card(en, first)}\n'
            f'{build_card(ar, first)}\n'
            f'            </div>'
        )
    return (
        f"{START_MARKER}\n"
        f'        <section class="articles" aria-roledescription="carousel" aria-label="Articles from the Afrin Archive Substack">\n'
        f'            <button class="articles-arrow" id="articles-prev" type="button" aria-label="Newer articles">\n'
        f'                <svg viewBox="0 0 40 100" aria-hidden="true"><path d="M31 8 11 50l20 42"></path></svg>\n'
        f'            </button>\n'
        f'            <div class="articles-track" id="articles-track" tabindex="0">\n'
        + "\n".join(slides)
        + "\n            </div>\n"
        f'            <button class="articles-arrow" id="articles-next" type="button" aria-label="Older articles">\n'
        f'                <svg viewBox="0 0 40 100" aria-hidden="true"><path d="M9 8l20 42-20 42"></path></svg>\n'
        f'            </button>\n'
        f"        </section>\n        {END_MARKER}"
    )


def main():
    print("Updating the Substack article slider on the homepage...")

    if not INDEX_FILE.exists():
        print(f"[ERROR] index.html not found: {INDEX_FILE}")
        return 1

    try:
        posts = download_posts()
    except Exception as error:
        print(f"[!] Could not reach Substack ({error}). The homepage articles were left unchanged.")
        return 0

    entries = [entry for entry in (to_entry(post) for post in posts) if entry]
    pairs = pair_articles(entries)
    if not pairs:
        print("[!] No English and Arabic article pairs were found. The homepage articles were left unchanged.")
        return 0

    content = INDEX_FILE.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER), re.DOTALL)
    if len(pattern.findall(content)) != 1:
        print("[ERROR] index.html must contain exactly one LATEST-ARTICLES marker pair. Nothing was changed.")
        return 1

    block = build_block(pairs)
    updated = pattern.sub(lambda _match: block, content)
    print(f"  {len(posts)} posts on Substack, {len(pairs)} English and Arabic pairs on the homepage.")
    if updated == content:
        print("[OK] The homepage already shows these articles.")
        return 0

    INDEX_FILE.write_text(updated, encoding="utf-8")
    print(f"  Newest: {pairs[0][0]['title']} / {pairs[0][1]['title']}")
    print("[SUCCESS] Updated the article slider on index.html.")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
