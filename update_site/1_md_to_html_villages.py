#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standalone village Markdown -> HTML generator.
Updated to fix:
1. Strict conditional rendering for ALL General Info fields (including Etymology).
2. Remove redundant "Summary of..." lines.
3. specific spacing after "Source:" lines.
4. Increased global paragraph spacing.
"""
import sys
from pathlib import Path
from datetime import datetime
import re
import html
from bs4 import BeautifulSoup
import yaml

import shutil
import glob

INPUT_PATH  = r"H:\\My Drive\\Zachar\\1 - PhD\\Villages"
OUTPUT_DIR  = r"C:\\Users\\Zachar\\Desktop\\Afrin_Archive\\village_sites"
NAHIYA_MAPS_DIR = r"C:\\Users\\Zachar\\Desktop\\Afrin_Archive\\nahiyas"
MASTER_MAP_PATH = r"C:\Users\Zachar\Desktop\Afrin_Archive\nahiyas\All_Nahiyas_Clickable_Maps.html"

# --- Transcript & Subtitle Paths ---
TRANSCRIPTS_SOURCE_DIR = r"H:\\My Drive\\Zachar\\1 - PhD\\Villages_Transcripts"
SUBTITLES_SOURCE_DIR = r"C:\\Users\\Zachar\\Desktop\\programs I made\\python programs\\archive programs\\make_subtitles\\subtitle_files"
SUBTITLES_DEST_DIR = r"C:\\Users\\Zachar\\Desktop\\Afrin_Archive\\village_subtitles\\subtitles"

SOURCE_TO_SUBTITLE_MAP = {
    "Afrin 366": ("afrin366_videos", "afrin366_videos_"),
    "Ax u Walat": ("videos", "videos_"),
    "Ax û Welat": ("videos", "videos_"), # Handling both spellings
    "Afrin Flo": ("afrin_flo_videos", "afrin_flo_videos_"),
    "Halil Sino": ("khalil_sino_videos", "khalil_sino_videos_"),
    "Khalil Sino": ("khalil_sino_videos", "khalil_sino_videos_"),
    "Afrin Zeyton": ("afrinzeyton_videos", "afrinzeyton_videos_")
}

def has_meaningful_content(md_block: str) -> bool:
    if not md_block:
        return False
    for line in md_block.splitlines():
        stripped = line.strip()
        if not stripped or stripped == '---':
            continue
        if re.match(r'^#+\s*[A-Z]\.\s+Summary\s+from', stripped):
            continue
        if re.match(r'^#+\s*[A-Za-z]+TV\s*$', stripped, re.IGNORECASE):
            continue
        content_only = stripped.lstrip('#').strip().strip('*').rstrip(':').strip()
        if not content_only:
            continue
        SIMPLE_TEMPLATE_WORDS = {
            'source', 'history within time periods', 'general history',
            'oral history / stories', 'historic families/people',
            'cultural aspects', 'food', 'handiwork', 'professions',
            'dengbêj/çirok', 'dengbej/cirok'
        }
        if content_only.lower() in SIMPLE_TEMPLATE_WORDS:
            continue
        return True
    return False

def build_master_lookup(master_html_path: Path):
    if not master_html_path.is_file():
        print(f"[FATAL ERROR] Master map file not found at: {master_html_path}")
        return None
    print(f"Building lookup index from {master_html_path.name}...")
    lookup = {}
    with open(master_html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    nahiya_sections = soup.find_all('div', class_='nahiya-section')
    for section in nahiya_sections:
        nahiya_name_tag = section.find('h2')
        if not nahiya_name_tag:
            continue
        nahiya_name = nahiya_name_tag.get_text(strip=True)
        links = section.find_all('a', href=lambda href: href and href.startswith('#'))
        for link in links:
            village_text = link.get_text(strip=True)
            href = link.get('href')
            lookup[village_text.lower()] = {
                'href': href,
                'nahiya': nahiya_name
            }
    print(f"--> Index built successfully with {len(lookup)} entries.")
    return lookup

def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def parse_yaml_frontmatter(md_content: str) -> dict:
    match = re.search(r'---\s*\n(.*?)\n---', md_content, re.DOTALL)
    if match:
        yaml_str = match.group(1)
        # We deliberately do NOT catch YAMLError here.
        # It should propagate to process_one -> main loop,
        # so the file is marked as failed and the user sees the error count.
        data = yaml.safe_load(yaml_str)
        if isinstance(data, dict):
            return data
    return {}

def extract_minimap(village_name: str, maps_dir: Path, master_lookup: dict):
    village_info = master_lookup.get(village_name.lower())
    if not village_info:
        return None, None
    correct_nahiya = village_info['nahiya']
    href = village_info['href']
    highlight_class = href.lstrip('#')
    map_file = maps_dir / f"{correct_nahiya}.html"
    if not map_file.is_file():
        return None, None
    try:
        with open(map_file, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
        map_container = soup.find('div', class_='map-container')
        if not map_container:
            return None, None
        img_tag = map_container.find('img')
        if img_tag and img_tag.get('src'):
            original_image_name = img_tag['src']
            img_tag['src'] = f"../nahiyas/{original_image_name}"
        highlight_box = map_container.find('div', class_=highlight_class)
        if highlight_box:
            highlight_box['style'] = 'display: block;'
        style_tag = soup.find('style')
        css_text = style_tag.string if style_tag else ""
        map_id = f"minimap-{re.sub(r'[^a-zA-Z0-9]', '-', correct_nahiya.lower())}"
        scoped_css_lines = []
        if css_text:
            for line in css_text.splitlines():
                match = re.match(r'^\s*(\.-?[_a-zA-Z]+[_a-zA-Z0-9-]*.*\{)', line)
                if match:
                    original_selector = match.group(1)
                    scoped_line = line.replace(original_selector, f"#{map_id} {original_selector}")
                    scoped_css_lines.append(scoped_line)
                else:
                    scoped_css_lines.append(line)
        map_container['id'] = map_id
        map_container['class'] = 'map-container'
        return str(map_container), "\n".join(scoped_css_lines)
    except Exception as e:
        print(f"  [ERROR] Failed to process minimap: {e}")
        return None, None

def md_find_nahiya_in_body(md: str) -> str:
    for line in md.splitlines():
        if line.strip().lower().startswith("## nahiya"):
            m = re.search(r'\[\[(.*?)\]\]', line)
            if m:
                return m.group(1).strip() or "unknown"
            t = line.split("## Nahiya", 1)[-1].strip(" :\t")
            return t if t else "unknown"
    return "unknown"

def md_find_coords(md: str):
    lat = None
    lng = None
    for line in md.splitlines():
        ml = re.match(r'(?i)^\s*lat(itude)?\s*:\s*([+-]?\d+(?:\.\d+)?)', line.strip())
        if ml:
            try: lat = float(ml.group(2))
            except: pass
        mlon = re.match(r'(?i)^\s*(lon|long|lng|longitude)\s*:\s*([+-]?\d+(?:\.\d+)?)', line.strip())
        if mlon:
            try: lng = float(mlon.group(2))
            except: pass
    return lat, lng

def md_sections(md: str) -> dict:
    sections = {}
    cur = None
    buf = []
    for line in md.splitlines():
        m = re.match(r'^\s*##\s+(.*)\s*$', line)
        if m:
            if cur is not None:
                sections[cur] = "\n".join(buf).strip()
            cur = m.group(1).strip()
            buf = []
        else:
            if cur is None:
                continue
            buf.append(line)
    if cur is not None:
        sections[cur] = "\n".join(buf).strip()
    return sections

def md_find_photos(md: str) -> list:
    secs = md_sections(md)
    photos_block = ""
    for key in secs.keys():
        if key.strip().lower().startswith("photos"):
            photos_block = secs[key]
            break
    
    out = []
    lines = photos_block.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.search(r'!\[\[\s*([^\]\|]+?)(?:\|.*?)?\s*\]\]', line)
        if m:
            fname = m.group(1).strip()
            caption = ""
            if i + 1 < len(lines):
                next_line = lines[i+1].strip()
                if next_line and not next_line.startswith('![') and not next_line.startswith('---'):
                    caption = next_line.lstrip('*').strip()
            out.append((fname, caption))
        i += 1
    return out

def md_extract_basic_info_section(md: str) -> str:
    """Extract the entire 'Basic Information about ...' section as raw markdown."""
    secs = md_sections(md)
    for key in secs.keys():
        if "basic information" in key.lower():
            return secs[key]
    return ""

def convert_md_to_html_basic(md_text: str) -> str:
    md_text = re.sub(r'==(.+?)==', r'\1', md_text)
    # Updated regex to also capture ##### headers
    blocks = re.split(r'(^\s*#{3,5}.*\n?)', md_text, flags=re.MULTILINE)
    final_html_parts = []

    def _convert_simple_block_to_html(block_text):
        lines = block_text.strip().splitlines()
        if not lines: return ""
        html_lines = []
        in_ul = False; in_ol = False; in_blockquote = False
        def close_all_blocks():
            nonlocal in_ul, in_ol, in_blockquote
            if in_ul: html_lines.append('</ul>'); in_ul = False
            if in_ol: html_lines.append('</ol>'); in_ol = False
            if in_blockquote: html_lines.append('</blockquote>'); in_blockquote = False

        i = 0
        while i < len(lines):
            line = lines[i]
            s = line.strip()
            
            # --- SKIP "Summary of..." lines ---
            if re.match(r'^Summary\s+of', s, re.IGNORECASE):
                i += 1
                continue
            
            s_esc = html.escape(s)
            s_esc = re.sub(r'(https?://[^\s<]+)', r'<a href="\1" target="_blank" rel="noopener noreferrer" class="external-link hover:underline">\1</a>', s_esc)
            s_esc = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s_esc)
            s_esc = re.sub(r'\*(.+?)\*', r'<em>\1</em>', s_esc)
            s_esc = re.sub(r'\[\[(.+?)\]\]', r'<span class="internal-link">\1</span>', s_esc)
            
            if s == '---' or not s:
                close_all_blocks(); 
                i += 1
                continue
            
            # --- START FIX: Source Line Styling ---
            if re.match(r'^Source:', s, re.IGNORECASE):
                close_all_blocks()
                # Apply mb-6 to create the "empty space" requested
                html_lines.append(f'<p class="mb-6 font-semibold">{s_esc}</p>')
                i += 1
                continue
            # --------------------------------------

            if re.match(r'^\s*>\s+', s):
                if in_ul or in_ol: close_all_blocks()
                if not in_blockquote: html_lines.append('<blockquote>'); in_blockquote = True
                item_content = re.sub(r'^\s*>\s+', '', s, count=1)
                item_content_esc = html.escape(item_content)
                item_content_esc = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', item_content_esc)
                item_content_esc = re.sub(r'\[\[(.+?)\]\]', r'<span class="internal-link">\1</span>', item_content_esc)
                html_lines.append(f'<p>{item_content_esc}</p>')
                i += 1
                continue
            if re.match(r'^[-\*]\s+', s):
                if in_ol or in_blockquote: close_all_blocks()
                if not in_ul: html_lines.append('<ul>'); in_ul = True
                item = re.sub(r'^[-\*]\s+', '', s_esc, count=1)
                html_lines.append(f'<li>{item}</li>'); 
                i += 1
                continue
            if re.match(r'^\d+\.\s+', s):
                if in_ul or in_blockquote: close_all_blocks()
                if not in_ol: html_lines.append('<ol>'); in_ol = True
                item = re.sub(r'^\d+\.\s+', '', s_esc, count=1)
                html_lines.append(f'<li>{item}</li>'); 
                i += 1
                continue
            
            close_all_blocks()
            html_lines.append(f'<p>{s_esc}</p>')
            i += 1
            
        close_all_blocks()
        return "\n".join(html_lines)

    initial_content = blocks[0]
    if has_meaningful_content(initial_content):
        final_html_parts.append(_convert_simple_block_to_html(initial_content))
    for i in range(1, len(blocks), 2):
        heading = blocks[i].strip()
        content = blocks[i+1] if (i + 1) < len(blocks) else ""
        if has_meaningful_content(content):
            # Handle ##### headers (h5) for source sub-sections
            m_h5 = re.match(r'^\s*#####\s*(.*)', heading)
            if m_h5:
                final_html_parts.append(f'<h5 class="font-semibold text-base mt-5 mb-2 text-gray-600 dark:text-gray-400">{html.escape(m_h5.group(1).strip())}</h5>')
                final_html_parts.append(_convert_simple_block_to_html(content))
                continue
            m_h4 = re.match(r'^\s*####\s*(.*)', heading)
            if m_h4:
                final_html_parts.append(f'<h4 class="font-semibold text-lg mt-4 mb-2">{html.escape(m_h4.group(1).strip())}</h4>')
                final_html_parts.append(_convert_simple_block_to_html(content))
                continue
            m_h3 = re.match(r'^\s*###\s*(.*)', heading)
            if m_h3:
                final_html_parts.append(f'<h3 class="font-semibold text-xl mt-6 mb-3">{html.escape(m_h3.group(1).strip())}</h3>')
            final_html_parts.append(_convert_simple_block_to_html(content))
    return "\n".join(part for part in final_html_parts if part)

def build_links_html(links_md: str) -> str:
    if not links_md.strip():
        return '<div class="p-4 italic subtext">No data provided.</div>'
    blocks = re.split(r'\n\s*\n', links_md.strip())
    items = []
    for block in blocks:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines: continue
        label = lines[0].rstrip(':')
        urls = [ln for ln in lines[1:] if re.search(r'https?://', ln)]
        if not urls and re.search(r'https?://', label):
            label, urls = "Links", [label] + [ln for ln in lines[1:] if re.search(r'https?://', ln)]
        if not urls: continue
        url_html = '<br>'.join([f'<a href="{html.escape(u)}" target="_blank" rel="noopener noreferrer" class="external-link hover:underline break-all">{html.escape(u)}</a>' for u in urls])
        items.append(f'<li>{html.escape(label)}:<br>{url_html}</li>')
    if not items:
        return '<div class="p-4 italic subtext">No data provided.</div>'
    return '<ul class="list-disc list-inside space-y-2 p-4">' + "".join(items) + "</ul>"

def build_transcripts_table_html(transcripts_md: str, metadata_lookup: dict) -> str:
    """
    Parses transcripts markdown, styles matches site theme (minimalist/transparent),
    sorts rows by priority, removes IDs from display, and adds download attribute.
    """
    if not has_meaningful_content(transcripts_md):
        return ""

    # parse links
    wikilinks = re.findall(r'\[\[(.*?)\]\]', transcripts_md)
    mdlinks = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', transcripts_md)
    
    entries = []
    for w in wikilinks:
        entries.append((w, w))
    for text, link in mdlinks:
        p = Path(link)
        entries.append((text, p.stem))

    # Priority for sorting
    SORT_ORDER = ["TirejAfrin", "Ax û Welat", "Afrin 366", "Khalil Sino", "Afrin Flo", "Afrin Zeyton"]
    
    row_data = [] # Stores dict of data for sorting

    for text, stem in entries:
        meta = metadata_lookup.get(stem)
        
        video_url = "#"
        subtitle_file = None
        
        # Determine source name for display and sorting
        if meta:
            video_url = meta.get('url') or "#"
            raw_source = meta.get('source')
            t_id = meta.get('id')
            village = meta.get('village')
            
            subtitle_file = find_and_copy_subtitle(raw_source, t_id, village)
            
            # clean source name for display (remove id)
            disp_source = raw_source
            
            # If the stem has a suffix like "_2", append it to the source name
            # Pattern: .*_(\d+)$ matches end of string digits
            m_part = re.search(r'_(\d+)$', stem)
            if m_part:
                part_num = m_part.group(1)
                # Check if number exists as a distinct word to avoid matching "3" in "366"
                if not re.search(rf'\b{part_num}\b', disp_source):
                    disp_source = f"{disp_source} {part_num}"
        else:
            disp_source = text
            raw_source = text
            
        # Normalize for sorting
        sort_key = 999
        for idx, key in enumerate(SORT_ORDER):
            if key.lower() in str(disp_source).lower():
                sort_key = idx
                break
        
        row_data.append({
            "sort": sort_key,
            "source": disp_source,
            "video_url": video_url,
            "subtitle_file": subtitle_file,
            "stem": stem
        })
        
    # Sort
    # row_data.sort(key=lambda x: x["sort"])
    
    rows_html = []
    for r in row_data:
        # Video
        if r["video_url"] and r["video_url"] != "#":
            # Use external-link class to match site theme colors
            video_col = f'<a href="{r["video_url"]}" target="_blank" class="external-link hover:underline">Watch Video</a>'
        else:
            video_col = '<span class="subtext opacity-50">No Video</span>'
            
        # Subtitle
        if r["subtitle_file"]:
            sub_link = f"../village_subtitles/subtitles/{r['subtitle_file']}"
            # download attribute matching filename
            sub_col = f'<a href="{sub_link}" download="{r["subtitle_file"]}" class="inline-flex items-center px-3 py-1 bg-green-600 text-white text-sm font-medium rounded hover:bg-green-700 transition">Download SRT</a>'
        else:
            sub_col = '<span class="subtext italic opacity-50">Not Available</span>'
            
        # Transcript
        final_link = f"../village_transcripts/{r['stem']}.html"
        # Use external-link class to match video link color
        trans_col = f'<a href="{final_link}" target="_blank" class="external-link hover:underline">View Transcript</a>'
        
        # Increased font size (text-sm -> text-base or removed class for default which is typically base)
        rows_html.append(f"""
            <tr class="border-b themed-border hover:bg-gray-50 dark:hover:bg-gray-800 transition">
                <td class="px-4 py-3 text-base">{r['source']}</td>
                <td class="px-4 py-3 text-base">{video_col}</td>
                <td class="px-4 py-3 text-base">{sub_col}</td>
                <td class="px-4 py-3 text-base">{trans_col}</td>
            </tr>
        """)

    if not rows_html:
        return ""

    # Minimal table style
    html_out = f"""
    <div class="mb-4">
        <a href="../village_subtitles/how_to_use_substital.html" target="_blank" class="text-base font-medium external-link hover:underline">Need help with using this subtitles on Youtube? (Click here)</a>
    </div>
    <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
            <thead>
                <tr class="border-b-2 themed-border">
                    <th class="px-4 py-2 text-sm font-semibold uppercase tracking-wider opacity-70">Source</th>
                    <th class="px-4 py-2 text-sm font-semibold uppercase tracking-wider opacity-70">Video</th>
                    <th class="px-4 py-2 text-sm font-semibold uppercase tracking-wider opacity-70">Subtitles</th>
                    <th class="px-4 py-2 text-sm font-semibold uppercase tracking-wider opacity-70">Transcript</th>
                </tr>
            </thead>
            <tbody>
                {"".join(rows_html)}
            </tbody>
        </table>
    </div>
    """
    return html_out


def section_or_placeholder(title: str, body_md: str, open_details=True) -> str:
    if not has_meaningful_content(body_md): return ""
    content = convert_md_to_html_basic(body_md)
    open_attr = " open" if open_details else ""
    return f'<details class="group"{open_attr}><summary class="flex justify-between items-center font-semibold p-3 cursor-pointer text-lg"><span>{html.escape(title)}</span><svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 transform transition-transform group-open:rotate-180 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg></summary><div class="p-4 prose max-w-none">{content}</div></details>'

def section_or_placeholder_plain(title: str, body_md: str, open_details=True) -> str:
    if not has_meaningful_content(body_md): return ""
    content = convert_md_to_html_basic(body_md)
    open_attr = " open" if open_details else ""
    # Fixed: Added 'prose max-w-none' class so paragraph spacing CSS applies
    return f'<details class="group"{open_attr}><summary class="flex justify-between items-center font-semibold p-3 cursor-pointer text-lg"><span>{html.escape(title)}</span><svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 transform transition-transform group-open:rotate-180 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg></summary><div class="p-4 prose max-w-none">{content}</div></details>'

def build_simple_section_html(title: str, body_md: str, name: str) -> str:
    if not has_meaningful_content(body_md): return ""
    title = title.replace("__NAME__", name)
    content = convert_md_to_html_basic(body_md)
    return f"""<div class="border-b themed-border pb-3 mb-4"><h2 class="text-2xl font-semibold">{html.escape(title)}</h2></div><div class="p-4 prose max-w-none">{content}</div>"""

def photos_grid_html(name: str, photos: list) -> str:
    if not photos:
        return '<div class="italic subtext">No photos available.</div>'
    tiles = []
    for fn, caption in photos:
        src = f"../village_photos/{fn}"
        alt = f"Photo of {name}"
        placeholder = 'https://placehold.co/600x400/e2e8f0/4a5568?text=' + html.escape(fn).replace(' ', '+')
        caption_html = ""
        if caption:
            caption_html = f'<p class="mt-2 text-sm subtext">{html.escape(caption)}</p>'
        tiles.append(f'<div><img src="{html.escape(src)}" alt="{html.escape(alt)}" class="lightbox-trigger rounded-lg w-full h-auto object-cover border themed-border cursor-pointer" onerror="this.onerror=null;this.src=\'{placeholder}\';">{caption_html}</div>')
    return '<div class="grid grid-cols-1 md:grid-cols-2 gap-4">\n' + "\n".join(tiles) + '\n</div>'

def build_html_page(name, nahiya, aliases, lat, lng,
                    ordered_summaries,
                    transcripts_html,
                    links_md,
                    vi_history, vii_families, viii_culture, ix_dengbej, x_connections,
                    foundation_origin_md, name_meaning_md,
                    mountains_of_kurds_md,
                    xi_ar_tirej,
                    photos,
                    foundation_txt, size_txt, tribes_txt, families_txt,
                    basic_info_md,
                    minimap_html, minimap_css):
    today = datetime.now().strftime("%B %d, %Y")
    nahiya_disp = nahiya if nahiya else "unknown"

    # --- Build info rows conditionally with STRIP() ---
    info_rows = []
    if nahiya_disp and nahiya_disp.strip():
        info_rows.append(f'<div><h3 class="text-sm font-medium subtext">Nahiya (Subdistrict)</h3><p class="text-lg">{html.escape(nahiya_disp)}</p></div>')
    if aliases and aliases.strip():
        info_rows.append(f'<div><h3 class="text-sm font-medium subtext">Also Known As</h3><p class="text-lg">{html.escape(aliases)}</p></div>')
    if tribes_txt and tribes_txt.strip():
        info_rows.append(f'<div><h3 class="text-sm font-medium subtext">Tribes</h3><p class="text-lg">{html.escape(tribes_txt)}</p></div>')
    if families_txt and families_txt.strip():
        info_rows.append(f'<div><h3 class="text-sm font-medium subtext">Families, Clans, etc.</h3><p class="text-lg">{html.escape(families_txt)}</p></div>')
    if foundation_txt and foundation_txt.strip():
        info_rows.append(f'<div><h3 class="text-sm font-medium subtext">Foundation Date</h3><p class="text-lg">{html.escape(foundation_txt)}</p></div>')
    if size_txt and size_txt.strip():
        info_rows.append(f'<div><h3 class="text-sm font-medium subtext">Size</h3><p class="text-lg">{html.escape(size_txt)}</p></div>')
    
    # No longer adding geo_info items - they now go in the separate Basic Information card
    general_info_block = "\n".join(info_rows)
    # ------------------------------------------------

    html_template = """<!DOCTYPE html>
<html lang="en" class="">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Archive | __NAME__</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
     integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
     crossorigin=""/>
    <style>
        body { font-family: 'Inter', sans-serif; }
        :root {
            --bg-color: #f0f2e6;
            --text-color: #000000;
            --border-color: #000000;
            --card-bg-color: #f0f2e6;
            --subtext-color: #4a5568;
            --link-color: #2563eb;
            --button-hover-bg: #000000;
            --button-hover-text: #f0f2e6;
            --internal-link-color: #2563eb;
            --blockquote-border-color: #16a34a;
        }
        .dark {
            --bg-color: #2d2d2d;
            --text-color: #f1f1f1;
            --border-color: #555555;
            --card-bg-color: #2d2d2d;
            --subtext-color: #999999;
            --link-color: #63b3ed;
            --button-hover-bg: #f1f1f1;
            --button-hover-text: #2d2d2d;
            --internal-link-color: #86efac;
            --blockquote-border-color: #4ade80;
        }
        body { background-color: var(--bg-color); color: var(--text-color); transition: background-color 0.3s, color 0.3s; }
        .card { background-color: var(--card-bg-color); border: 1px solid var(--border-color); transition: background-color 0.3s, border-color 0.3s; }
        h1, h2, h3, .prose { color: var(--text-color); }
        .subtext { color: var(--subtext-color); }
        .themed-border { border-color: var(--border-color); }
        .internal-link { text-decoration: none; cursor: pointer; color: var(--internal-link-color); }
        .external-link { color: var(--link-color); }
        .button-style { border: 1px solid var(--border-color); }
        .button-style:hover { background-color: var(--button-hover-bg); color: var(--button-hover-text); }
        details > summary { list-style: none; }
        details > summary::-webkit-details-marker { display: none; }
        .prose strong { font-weight: 600; }
        .prose p { margin-bottom: 1.5rem; } /* Increased Paragraph Spacing */
        .prose-compact p { margin-bottom: 0.5rem; } /* Compact spacing for Basic Info */
        .prose ol, .prose ul { margin-bottom: 1rem; }
        .prose blockquote { border-left: 3px solid var(--blockquote-border-color); padding-left: 1rem; margin-left: 0; margin-bottom: 1rem; }
        .prose blockquote p { color: var(--text-color); }
        .toggle-button-colors { background-color: var(--text-color); color: var(--bg-color); border: 1px solid var(--border-color); }
        .leaflet-popup-content-wrapper, .leaflet-control-layers { background-color: var(--card-bg-color) !important; color: var(--text-color) !important; border-radius: 8px; border: 1px solid var(--border-color); }
        .leaflet-popup-tip { background: var(--card-bg-color) !important; }
        .leaflet-popup-close-button { color: var(--text-color) !important; }
        .leaflet-popup-content b { font-weight: 600; }
        .leaflet-popup-content span { color: var(--subtext-color); text-transform: capitalize; }
        .leaflet-control-layers-toggle {
            background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23000'%3e%3cpath d='M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5'/%3e%3c/svg%3e") !important;
            background-size: 20px 20px !important;
        }
        .dark .leaflet-control-layers-toggle {
             background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23fff'%3e%3cpath d='M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5'/%3e%3c/svg%3e") !important;
        }
        .leaflet-control-scale-line { background: var(--card-bg-color); border-color: var(--text-color); color: var(--text-color); }
        .lightbox-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); display: flex; justify-content: center; align-items: center; z-index: 1000; cursor: pointer; }
        .lightbox-image { max-width: 90vw; max-height: 90vh; border: 3px solid var(--border-color); border-radius: 8px; }
        .lightbox-close { position: absolute; top: 20px; right: 30px; font-size: 3rem; color: white; cursor: pointer; line-height: 1; }
        
        /* --- START MINIMAP --- */
        __MINIMAP_CSS__
        .map-container { position: relative; width: 100%; max-width: 500px; }
        .map-container img { display: block; width: 100%; height: auto; border-radius: 5px; }
        .highlight-box { display: none; position: absolute; background-color: yellow; opacity: 0.5; border-radius: 50%; pointer-events: none; }
        /* --- END MINIMAP --- */

    </style>
</head>
<body>
    <div class="container mx-auto p-4 sm:p-6 md:p-8 max-w-4xl">
        <header class="mb-8">
            <h1 class="text-3xl sm:text-4xl md:text-5xl font-bold">__NAME__</h1>
        </header>

        <main class="space-y-6">
            <div class="card p-6 rounded-xl">
                <div class="flex justify-between items-center border-b themed-border pb-3 mb-4">
                    <h2 class="text-2xl font-semibold">General Information</h2>
                    <button id="theme-toggle" class="toggle-button-colors p-2 rounded-full focus:outline-none focus:ring-2 focus:ring-offset-2" style="--ring-offset-color: var(--card-bg-color); --ring-color: var(--border-color);">
                        <svg id="theme-toggle-dark-icon" class="hidden h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"></path></svg>
                        <svg id="theme-toggle-light-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="hidden h-6 w-6">
                          <path stroke-linecap="round" stroke-linejoin="round" d="M12 3v2.25m6.364.386-1.591 1.591M21 12h-2.25m-.386 6.364-1.591-1.591M12 18.75V21m-4.773-4.227-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0Z" />
                        </svg>
                    </button>
                </div>
                <div class="flex flex-col md:flex-row gap-6 md:gap-8">
                    <div class="flex-1">
                        <div class="grid grid-cols-1 gap-4">
                            __GENERAL_INFO_BLOCK__
                        </div>
                    </div>
                    __MINIMAP_COLUMN__
                </div>
            </div>

            <div class="card p-6 rounded-xl">
                <h2 class="text-2xl font-semibold border-b themed-border pb-3 mb-4">Map and Location</h2>
                <div id="map" class="rounded-lg border themed-border" style="height: 450px;"></div>
                <div class="mt-4 flex flex-col sm:flex-row flex-wrap justify-between items-center gap-4">
                    <p class="text-sm">Coordinates: __LAT__, __LNG__</p>
                </div>
                 <p class="text-xs subtext mt-3">Source: <a href="https://akmckeever.substack.com/" class="hover:underline external-link">akmckeever.substack.com</a></p>
            </div>
            
            <div class="card p-6 rounded-xl">
                <h2 class="text-2xl font-semibold border-b themed-border pb-3 mb-4">Photos</h2>
                __PHOTOS__
            </div>

            __BASIC_INFO_CARD__

            __MOUNTAINS_CARD__

            __SUMMARIES_CARD__

            __TRANSCRIPTS_CARD__

            __FOUNDATION_CARD__

            __LINKS_CARD__

            __ADDITIONAL_INFO_CARD__

            __ADDITIONAL_TRANSCRIPTS_CARD__

        </main>

        <footer class="text-center mt-12 py-4 border-t themed-border">
            <p class="text-sm subtext">Page Updated on __TODAY__</p>
        </footer>
    </div>

    <div id="lightbox" class="lightbox-overlay hidden">
        <span id="lightbox-close" class="lightbox-close">&times;</span>
        <img id="lightbox-image" class="lightbox-image" src="">
    </div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
    <script>
        const themeToggleBtn = document.getElementById('theme-toggle');
        const themeToggleDarkIcon = document.getElementById('theme-toggle-dark-icon');
        const themeToggleLightIcon = document.getElementById('theme-toggle-light-icon');
        if (localStorage.getItem('color-theme') === 'dark' || (!('color-theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            document.documentElement.classList.add('dark');
            themeToggleLightIcon.classList.remove('hidden');
        } else {
            document.documentElement.classList.remove('dark');
            themeToggleDarkIcon.classList.remove('hidden');
        }
        themeToggleBtn.addEventListener('click', function() {
            themeToggleDarkIcon.classList.toggle('hidden');
            themeToggleLightIcon.classList.toggle('hidden');
            if (localStorage.getItem('color-theme')) {
                if (localStorage.getItem('color-theme') === 'light') {
                    document.documentElement.classList.add('dark');
                    localStorage.setItem('color-theme', 'dark');
                } else {
                    document.documentElement.classList.remove('dark');
                    localStorage.setItem('color-theme', 'light');
                }
            } else {
                if (document.documentElement.classList.contains('dark')) {
                    document.documentElement.classList.remove('dark');
                    localStorage.setItem('color-theme', 'light');
                } else {
                    document.documentElement.classList.add('dark');
                    localStorage.setItem('color-theme', 'dark');
                }
            }
        });

        document.addEventListener('DOMContentLoaded', function () {
            const lightbox = document.getElementById('lightbox');
            const lightboxImage = document.getElementById('lightbox-image');
            const lightboxClose = document.getElementById('lightbox-close');
            const imageTriggers = document.querySelectorAll('.lightbox-trigger');
            imageTriggers.forEach(trigger => {
                trigger.addEventListener('click', () => {
                    lightboxImage.src = trigger.src;
                    lightbox.classList.remove('hidden');
                });
            });
            function closeLightbox() { lightbox.classList.add('hidden'); }
            lightbox.addEventListener('click', closeLightbox);
            lightboxClose.addEventListener('click', closeLightbox);
            document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { closeLightbox(); }});

            const iconConfig = {
                shrine: { pinColor: '#28a745', iconColor: '#ffffff', svg: '<path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>' },
                landmark: { pinColor: '#ffc107', iconColor: '#ffffff', svg: '<path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>' },
                transport: { pinColor: '#007bff', iconColor: '#ffffff', svg: '<path d="M12 2c-4 0-8 3.5-8 8v6c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2v-6c0-4.5-4-8-8-8zm0 2c1.1 0 2 .9 2 2s-.9 2-2 2-2-.9-2-2 .9-2 2-2zm-6 8h12v4H6v-4z"/>' },
                settlement: { pinColor: '#343a40', iconColor: '#ffffff', svg: '<path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/>' },
                historical_site: { pinColor: '#6f42c1', iconColor: '#ffffff', svg: '<path d="M12 2L2 7v2h20V7L12 2zM4 10v10h2V10H4zm5 0v10h2V10H9zm5 0v10h2V10h-2zm5 0v10h2V10h-2z"/>' },
                infrastructure: { pinColor: '#6c757d', iconColor: '#ffffff', svg: '<path d="M20.5 16.5c.83 0 1.5-.67 1.5-1.5s-.67-1.5-1.5-1.5-1.5.67-1.5 1.5.67 1.5 1.5 1.5zm-17 0c.83 0 1.5-.67 1.5-1.5S4.33 13.5 3.5 13.5 2 14.17 2 15s.67 1.5 1.5 1.5zm17-13C21.33 3.5 22 4.17 22 5s-.67 1.5-1.5 1.5S19 5.83 19 5s.67-1.5 1.5-1.5zM3.5 5c.83 0 1.5-.67 1.5-1.5S4.33 2 3.5 2 2 2.67 2 3.5 2.67 5 3.5 5zm9.45 2.55L5.71 11.29c-.39.39-.39 1.02 0 1.41l8.49 8.49c.39.39 1.02.39 1.41 0l7.24-7.24c.39-.39.39-1.02 0-1.41L14.37 5.29c-.39-.39-1.03-.39-1.42 0z"/>' },
                military: { pinColor: '#dc3545', iconColor: '#ffffff', svg: '<path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>' },
                default: { pinColor: '#343a40', iconColor: '#ffffff', svg: '<path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>' }
            };
            function createCustomIcon(type, isMain) {
                const config = iconConfig[type] || iconConfig.default;
                const iconSize = isMain ? [36, 36] : [30, 30];
                const iconAnchor = isMain ? [18, 36] : [15, 30];
                const popupAnchor = [0, -iconSize[1] + 4];
                const iconInnerSize = isMain ? 20 : 16;
                const topPadding = (iconSize[1] - iconInnerSize) / 2 - (isMain ? 2 : 2);
                const html = `
                    <div style="position: relative; width: ${iconSize[0]}px; height: ${iconSize[1]}px; display: flex; justify-content: center; align-items: flex-start; padding-top: ${topPadding}px;">
                        <svg viewBox="0 0 24 24" width="${iconSize[0]}" height="${iconSize[1]}" style="position: absolute; left: 0; top: 0; filter: drop-shadow(0 2px 2px rgba(0,0,0,0.5));">
                            <path fill="${config.pinColor}" d="M12,2C8.1,2,5,5.1,5,9c0,5.2,7,13,7,13s7-7.8,7-13C19,5.1,15.9,2,12,2z"></path>
                        </svg>
                        <svg viewBox="0 0 24 24" width="${iconInnerSize}" height="${iconInnerSize}" style="position: relative; fill: ${config.iconColor};">
                            ${config.svg}
                        </svg>
                    </div>`;
                return L.divIcon({ html, className: '', iconSize, iconAnchor, popupAnchor });
            }
            const mainVillageName = "__NAME__";
            const villageLat = __LAT_JS__;
            const villageLng = __LNG_JS__;
            const initialZoom = 14;
            const map = L.map('map').setView([villageLat, villageLng], initialZoom);
            const esriImagery = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', { attribution: 'Tiles &copy; Esri' });
            const osmStreet = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' });
            const thunderforestTerrain = L.tileLayer('https://{s}.tile.thunderforest.com/outdoors/{z}/{x}/{y}{r}.png?apikey={apikey}', {
                attribution: '&copy; <a href="http://www.thunderforest.com/">Thunderforest</a>, &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
                apikey: 'e030b1cd0c1041a69a5ca2b0ca2ebe36',
                maxZoom: 22
            });
            const baseMaps = { "Satellite": esriImagery, "Street": osmStreet, "Terrain": thunderforestTerrain };
            L.control.layers(baseMaps).addTo(map);
            esriImagery.addTo(map);
            L.control.scale({ imperial: false }).addTo(map);
            fetch('afrin_locations.json')
                .then(r => { if (!r.ok) throw new Error('Network response was not ok'); return r.json(); })
                .then(locations => {
                    locations.forEach(location => {
                        const isMainVillage = location.name === mainVillageName;
                        const customIcon = createCustomIcon(location.type, isMainVillage);
                        const marker = L.marker([location.lat, location.lng], { icon: customIcon, zIndexOffset: isMainVillage ? 1000 : 0 }).addTo(map);
                        marker.bindPopup(`<b>${location.name}</b><br><span>${location.type.replace(/_/g, ' ')}</span>`);
                        if (isMainVillage) { marker.openPopup(); }
                    });
                })
                .catch(err => {
                    console.error('Error loading location data:', err);
                    document.getElementById('map').innerHTML = '<div style="text-align:center; padding: 20px; color: var(--subtext-color);">Could not load map data.<br>Please ensure <strong>afrin_locations.json</strong> is in the same folder as this HTML file.</div>';
                });
        });
    </script>
</body>
</html>"""

    # -- Build cards dynamically --
    minimap_column_html = ""
    if minimap_html:
        minimap_column_html = f'<div class="flex-1 min-w-0">{minimap_html}</div>'

    # Basic Information Card (preserves Source sub-sections)
    basic_info_card_html = ""
    if has_meaningful_content(basic_info_md):
        basic_info_content = convert_md_to_html_basic(basic_info_md)
        basic_info_card_html = f'''<div class="card p-6 rounded-xl">
                <h2 class="text-2xl font-semibold border-b themed-border pb-3 mb-4">Basic Information about {html.escape(name)}</h2>
                <div class="p-4 prose-compact max-w-none">{basic_info_content}</div>
            </div>'''

    # Foundation and Meaning Card
    foundation_html = build_simple_section_html("Foundation/Origin Information of __NAME__", foundation_origin_md, name)
    meaning_html = build_simple_section_html("Possible Village Name Meaning of __NAME__", name_meaning_md, name)
    foundation_card_html = ""
    if foundation_html or meaning_html:
        foundation_card_html = f'''<div class="card p-6 rounded-xl space-y-6">
                {foundation_html}
                {meaning_html}
            </div>'''
            
    # Mountains of the Kurds Card
    mountains_card_html = ""
    if has_meaningful_content(mountains_of_kurds_md):
        content = convert_md_to_html_basic(mountains_of_kurds_md)
        mountains_card_html = f'''<div class="card p-6 rounded-xl">
                <h2 class="text-2xl font-semibold border-b themed-border pb-3 mb-4">From "The Mountains of the Kurds (Afrin Region): a Comprehensive Geographical Study"</h2>
                <div class="p-4 prose max-w-none">{content}</div>
            </div>'''

    # Summaries Card
    # Summaries Card (Dynamic Order)
    summaries_card_html = ""
    if ordered_summaries:
        summary_blocks = []
        for title, content in ordered_summaries:
             # Use the title from the MD file, but maybe clean it up?
             # Actually, simpler to just pass it as title.
             # section_or_placeholder expects a title string and content string.
             # We want to display the title as well.
             # Actually section_or_placeholder adds the <h3>Title</h3> inside.
             # So we just pass the title from MD.
             
             # Special case for "I. Summary..." to check if we want open_details logic?
             # The user said "exact order of md file".
             # Let's assume standard behavior.
             block = section_or_placeholder_plain(title, content)
             if block:
                 summary_blocks.append(block)

        if summary_blocks:
            summaries_card_html = f'''<div class="card p-6 rounded-xl">
                    <h2 class="text-2xl font-semibold border-b themed-border pb-3 mb-4">Summaries</h2>
                    <div class="space-y-4">{"<hr class=\"themed-border\">".join(summary_blocks)}</div>
                </div>'''

    # Transcripts Card (New)
    transcripts_card_html = ""
    if transcripts_html:
         transcripts_card_html = f'''<div class="card p-6 rounded-xl">
            <h2 class="text-2xl font-semibold border-b themed-border pb-3 mb-4">Transcriptions and Subtitles</h2>
            <div class="p-4 prose-compact max-w-none">{transcripts_html}</div>
        </div>'''

    # Links Card
    links_html = build_links_html(links_md)
    links_card_html = ""
    if links_md.strip(): 
         links_card_html = f'''<div class="card p-6 rounded-xl">
                <h2 class="text-2xl font-semibold border-b themed-border pb-3 mb-4">V. Links</h2>
                {links_html}
            </div>'''

    # Additional Information Card
    vi  = section_or_placeholder_plain("VI. History", vi_history)
    vii = section_or_placeholder_plain("VII. Families, Clans, etc.", vii_families)
    viii= section_or_placeholder_plain("VIII. Cultural Aspects", viii_culture)
    ix  = section_or_placeholder_plain("IX. Dengbêj/Çirok", ix_dengbej)
    x   = section_or_placeholder_plain("X. Connections with other Villages", x_connections)
    add_info_content = [vi, vii, viii, ix, x]
    add_info_card_html = ""
    if any(add_info_content):
        add_info_card_html = f'''<div class="card p-6 rounded-xl">
                <h2 class="text-2xl font-semibold border-b themed-border pb-3 mb-4">Additional Information</h2>
                <div class="space-y-4">{"<hr class=\"themed-border\">".join(s for s in add_info_content if s)}</div>
            </div>'''
            
    photos_html = photos_grid_html(name, photos)

    out = (html_template
           .replace("__NAME__", html.escape(name))
           .replace("__GENERAL_INFO_BLOCK__", general_info_block)
           .replace("__LAT__", "" if lat is None else str(lat))
           .replace("__LNG__", "" if lng is None else str(lng))
           .replace("__LAT_JS__", "null" if lat is None else str(lat))
           .replace("__LNG_JS__", "null" if lng is None else str(lng))
           .replace("__PHOTOS__", photos_html)
           .replace("__BASIC_INFO_CARD__", basic_info_card_html)
           .replace("__FOUNDATION_CARD__", foundation_card_html)
           .replace("__MOUNTAINS_CARD__", mountains_card_html)
           .replace("__SUMMARIES_CARD__", summaries_card_html)
           .replace("__TRANSCRIPTS_CARD__", transcripts_card_html) 
           .replace("__LINKS_CARD__", links_card_html)
           .replace("__ADDITIONAL_INFO_CARD__", add_info_card_html)
           .replace("__ADDITIONAL_TRANSCRIPTS_CARD__", "")
           .replace("__TODAY__", html.escape(today))
           .replace("__MINIMAP_CSS__", minimap_css or "")
           .replace("__MINIMAP_COLUMN__", minimap_column_html)
          )
    return out

def normalize_section_title(t: str) -> str:
    return re.sub(r'\s+', ' ', t.strip().lower())

def extract_expected_sections(md: str) -> dict:
    secs_raw = md_sections(md)
    # Lookup for structural sections (normalization needed to match keys)
    lookup = {normalize_section_title(k): v for k, v in secs_raw.items()}
    
    # Helper to find by fuzzy keyword
    def find_by_keyword(keyword):
        for k_norm, v in lookup.items():
            if keyword in k_norm:
                return v
        return ""
        
    out = {}
    
    # Known Structural Sections (to exclude from Summaries)
    # These are handled explicitly or by specific dedicated functions
    excluded_keywords = [
        "basic information",
        "map and location",
        "photos",
        "foundation", # Foundation/Origin
        "possible village name meaning",
        "transcripts",
        "links", 
        "mountains of the kurds",
        "history",
        "families",
        "cultural aspects",
        "dengbej",
        "connections",
        "tirejafrin site (arabic)", # Specifically exclude Arabic summary if treated as extra info
         # Add other structural sections if they appear in MD
         "xi. summary from tirejafrin site (arabic)" # Ensuring explicit match
    ]
    
    # Structural Extractions
    out["transcripts_list"] = find_by_keyword("iii. transcripts") or find_by_keyword("transcripts")
    out["V_links"] = lookup.get("v. links", "")
    out["VI"]  = lookup.get("vi. history", "")
    out["VII"] = lookup.get("vii. families, clans, etc.", "")
    out["VIII"]= lookup.get("viii. cultural aspects", "")
    out["IX"]  = lookup.get("ix. dengbêj/çirok", "") or lookup.get("ix. dengbej/cirok", "")
    out["X"]   = lookup.get("x. connections with other villages", "")
    out["XI"]  = lookup.get("xi. summary from tirejafrin site (arabic)", "")
    
    # Also extract Foundation/Meaning/Mountains to ensure we key them if they exist in secs_raw
    out["foundation_origin"] = find_by_keyword("foundation/origin information")
    out["name_meaning"] = find_by_keyword("possible village name meaning")
    
    mountains_sections = []
    for title, content in secs_raw.items():
        if "mountains of the kurds" in title.lower():
            mountains_sections.append(content)
    out["mountains_of_kurds"] = "\n\n---\n\n".join(mountains_sections)

    # Dynamic Ordered Summaries Extraction
    # Iterate through original secs_raw to preserve order
    ordered_summaries = []
    
    # We need to map the excluded keywords to the normalized keys found in secs_raw
    # actually, just check if the normalized key contains any excluded keyword.
    
    for title, content in secs_raw.items():
        t_norm = normalize_section_title(title)
        
        # Check if this section is one of the excluded structural ones
        is_structural = False
        for kw in excluded_keywords:
            if kw in t_norm:
                is_structural = True
                break
        
        if not is_structural:
            # It's likely a summary.
            # Double check it has "summary" or is a Roman Numeral section we want
            # Actually, "I. Summary...", "II. Summary..." 
            # We can just include it if it's not structural.
            # But let's be safe and check if it LOOKS like a summary or generic section
            
            # Use title as header in the card? No, build_html_page handles that.
            # We will pass a list of (title, content) tuples so build_html_page can decide.
            ordered_summaries.append((title, content))
            
    out["ordered_summaries"] = ordered_summaries

    return out

def format_yaml_value(value):
    if value is None: return ""
    if isinstance(value, list): return ", ".join(str(v) for v in value)
    return str(value)

def scan_transcripts_metadata(transcripts_dir: str) -> dict:
    """"
    Scans all .md files in the transcripts directory and extracts metadata.
    Returns a dictionary keyed by the transcript filename (stem) containing:
    {
       'url': ...,
       'source': ...,
       'id': ...,
       'village': ...
    }
    """
    meta_map = {}
    path_obj = Path(transcripts_dir)
    if not path_obj.exists():
        return meta_map

    for p in path_obj.glob("*.md"):
        try:
            txt = read_text(p)
            fm = parse_yaml_frontmatter(txt)
            # Normalize keys to be safe
            fm_norm = {k.lower(): v for k, v in fm.items()}
            
            source = fm_norm.get('transcript source')
            t_id = fm_norm.get('transcript id')
            village = fm_norm.get('transcript village')
            url = fm_norm.get('transcript url')

            meta_map[p.stem] = {
                "source": source,
                "id": t_id,
                "village": village,
                "url": url,
                "filename": p.name
            }
        except Exception as e:
            print(f"Warning: could not parse metadata for {p.name}: {e}")
    return meta_map

def find_and_copy_subtitle(source, transcript_id, village_name):
    """
    Finds a subtitle file based on source and ID, copies it to the destination,
    and returns the relative path (filename) for linking.
    """
    if not source or not transcript_id:
        return None
    
    mapping = SOURCE_TO_SUBTITLE_MAP.get(source)
    if not mapping:
        return None
    
    folder_name, file_prefix = mapping
    search_dir = Path(SUBTITLES_SOURCE_DIR) / folder_name
    
    if not search_dir.exists():
        return None

    # Search pattern: prefix + id + "_" + *.srt
    # Note: transcript_id might be int or str
    pattern = f"{file_prefix}{transcript_id}_*.srt"
    matches = list(search_dir.glob(pattern))
    
    if not matches:
        return None
    
    # Take the first match
    src_file = matches[0]
    dest_dir = Path(SUBTITLES_DEST_DIR)
    ensure_dir(dest_dir)
    dest_file = dest_dir / src_file.name
    
    # Copy if not exists or size differs (simple check)
    if not dest_file.exists() or dest_file.stat().st_size != src_file.stat().st_size:
        try:
            shutil.copy2(src_file, dest_file)
            print(f"   -> Copied subtitle: {dest_file.name}")
        except Exception as e:
            print(f"   -> Error copying subtitle {src_file.name}: {e}")
            return None
            
    return src_file.name

def process_one(md_path: Path, out_dir: Path, master_lookup: dict, transcripts_lookup: dict):
    name = md_path.stem
    out_file = out_dir / f"{name}.html"

    if out_file.exists():
        md_mtime = md_path.stat().st_mtime
        html_mtime = out_file.stat().st_mtime
        # Force regeneration for subtitle integration
        # if md_mtime <= html_mtime:
        #    return

    md = read_text(md_path)
    fm_data = parse_yaml_frontmatter(md)

    aliases = format_yaml_value(fm_data.get('aliases'))
    tribes_txt = format_yaml_value(fm_data.get('tribes'))
    families_txt = format_yaml_value(fm_data.get('families, clans, etc'))
    foundation_txt = format_yaml_value(fm_data.get('foundation'))
    size_txt = format_yaml_value(fm_data.get('size'))

    nahiya_val = fm_data.get('nahiyah')
    if isinstance(nahiya_val, list) and nahiya_val:
        nahiya = str(nahiya_val[0])
    elif nahiya_val:
        nahiya = str(nahiya_val)
    else:
        nahiya = md_find_nahiya_in_body(md)

    lat, lng = md_find_coords(md)
    photos = md_find_photos(md)
    
    # Extract basic info section as raw markdown (preserves Source sub-sections)
    basic_info_md = md_extract_basic_info_section(md)

    minimap_html, minimap_css = extract_minimap(name, Path(NAHIYA_MAPS_DIR), master_lookup)
    sec = extract_expected_sections(md)
    vii_data = sec["VII"]

    # Generate Transcripts Table HTML
    transcripts_html = build_transcripts_table_html(sec["transcripts_list"], transcripts_lookup)

    html_text = build_html_page(
        name=name, nahiya=nahiya, aliases=aliases, lat=lat, lng=lng,
        ordered_summaries=sec["ordered_summaries"],
        transcripts_html=transcripts_html, # Pass the generated HTML, not the MD
        links_md=sec["V_links"],
        vi_history=sec["VI"], vii_families=vii_data, viii_culture=sec["VIII"], ix_dengbej=sec["IX"], x_connections=sec["X"],
        foundation_origin_md=sec["foundation_origin"],
        name_meaning_md=sec["name_meaning"],
        mountains_of_kurds_md=sec["mountains_of_kurds"],
        xi_ar_tirej=sec["XI"],
        photos=photos,
        foundation_txt=foundation_txt, size_txt=size_txt,
        tribes_txt=tribes_txt, families_txt=families_txt,
        basic_info_md=basic_info_md,
        minimap_html=minimap_html, minimap_css=minimap_css
    )
    ensure_dir(out_dir)
    out_file.write_text(html_text, encoding="utf-8")
    print(f"✓ Generated: {out_file}")

def main():
    in_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(INPUT_PATH)
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(OUTPUT_DIR)
    
    failed_files = []
    master_lookup = build_master_lookup(Path(MASTER_MAP_PATH))
    if not master_lookup:
        print("Could not build master lookup. Exiting.")
        return

    print("Scanning transcript metadata...")
    transcripts_lookup = scan_transcripts_metadata(TRANSCRIPTS_SOURCE_DIR)

    if in_path.is_file():
        if in_path.suffix.lower() != ".md":
            print(f"Skipping non-md file: {in_path}")
            return
        try:
            process_one(in_path, out_dir, master_lookup, transcripts_lookup)
        except Exception as e:
            print(f"✗ ERROR processing {in_path.name}: {e}")
            import traceback
            traceback.print_exc()
            failed_files.append((in_path.name, e))
    else:
        md_files = sorted([p for p in in_path.glob("*.md") if p.is_file()])
        if not md_files:
            print("No .md files found.")
            return

        print(f"--- Processing {len(md_files)} files ---")
        for p in md_files:
            try:
                process_one(p, out_dir, master_lookup, transcripts_lookup)
            except Exception as e:
                print(f"✗ ERROR processing {p.name}: {e}")
                failed_files.append((p.name, e))

    if failed_files:
        print("\n" + "="*20 + " SUMMARY OF FAILURES " + "="*20)
        print(f"Completed with {len(failed_files)} error(s).")
        for name, error in failed_files:
            print(f"  - File: {name}\n    Reason: {error}")
    else:
        print("\nProcessing completed successfully with no errors.")

if __name__ == "__main__":
    main()