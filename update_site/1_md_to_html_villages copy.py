#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standalone village Markdown -> HTML generator.

It recreates the exact layout, colors, and scripts of your sample (00_sample.html)
without loading that file. The entire HTML/CSS/JS is embedded and filled from
the .md content.

Usage:
  python md_to_html_standalone.py "H:\\My Drive\\Zachar\\1 - PhD\\Villages" "C:\\Users\\Zachar\\Desktop\\Afrin_Archive\\village_sites"
or:
  python md_to_html_standalone.py "H:\\My Drive\\Zachar\\1 - PhD\\Villages\\Abu Keb.md" "C:\\Users\\Zachar\\Desktop\\Afrin_Archive\\village_sites"
"""
import sys
from pathlib import Path
from datetime import datetime
import re
import html
from bs4 import BeautifulSoup

INPUT_PATH  = r"H:\\My Drive\\Zachar\\1 - PhD\\Villages"
OUTPUT_DIR  = r"C:\\Users\\Zachar\\Desktop\\Afrin_Archive\\village_sites"
NAHIYA_MAPS_DIR = r"C:\\Users\\Zachar\\Desktop\\Afrin_Archive\\nahiyas"
MASTER_MAP_PATH = r"C:\Users\Zachar\Desktop\Afrin_Archive\nahiyas\All_Nahiyas_Clickable_Maps.html"

def has_meaningful_content(md_block: str) -> bool:
    """
    Checks if a markdown block has content beyond any known template placeholders.
    This version correctly identifies both simple and complex (dynamic) templates.
    """
    if not md_block:
        return False

    for line in md_block.splitlines():
        stripped = line.strip()

        # Rule 1: Ignore empty lines and dividers.
        if not stripped or stripped == '---':
            continue

        # Rule 2: Check for complex, dynamic template patterns first.
        # These are patterns that change based on the village name.
        
        # This pattern matches headings like "### A. Summary from... Transcript of..."
        if re.match(r'^#+\s*[A-Z]\.\s+Summary\s+from', stripped):
            continue
        
        # This pattern matches channel headings like "#### HalabTodayTV"
        if re.match(r'^#+\s*[A-Za-z]+TV\s*$', stripped, re.IGNORECASE):
            continue

        # Rule 3: Check for simple, static template patterns.
        # This requires cleaning the line of markdown characters first.
        content_only = stripped.lstrip('#').strip().strip('*').rstrip(':').strip()
        
        # If after cleaning, the line is empty, it's not content.
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

        # If a line survives all of the template checks, it's real content.
        return True

    # If every single line was identified as a template or empty, the block has no content.
    return False

def build_master_lookup(master_html_path: Path):
    """
    Parses the master HTML file to create a lookup dictionary.
    KEY: lowercase village name (link text)
    VALUE: {'href': '#dot-1', 'nahiya': 'Reco'}
    """
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
            # The official name from the link is the key
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

def md_find_yaml_aliases(md: str) -> list:
    aliases = []
    m = re.search(r'(?s)^---\s*(.*?)\s*---', md)
    if not m:
        return aliases
    fm = m.group(1)
    m2 = re.search(r'(?mi)^\s*aliases\s*:\s*(.+)?$', fm)
    if not m2:
        return aliases
    rest = m2.group(1) or ""
    inline = re.search(r'\[(.*?)\]', rest)
    if inline:
        items = [x.strip() for x in inline.group(1).split(",")]
        return [x for x in items if x]
    lines = fm.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.match(r'^\s*aliases\s*:', line):
            start = i + 1
            break
    if start is None:
        return aliases
    for j in range(start, len(lines)):
        line = lines[j]
        if re.match(r'^\s*[A-Za-z_]+\s*:', line):
            break
        mli = re.match(r'^\s*-\s*(.+)$', line)
        if mli:
            aliases.append(mli.group(1).strip())
    return aliases



def extract_minimap(village_name: str, maps_dir: Path, master_lookup: dict):
    """
    Finds and extracts a village's minimap using the pre-built master lookup index.
    """
    # Step 1: Look up the village in our master index.
    village_info = master_lookup.get(village_name.lower())
    
    if not village_info:
        # This village doesn't exist in the master map file.
        return None, None

    correct_nahiya = village_info['nahiya']
    href = village_info['href']
    highlight_class = href.lstrip('#')

    # Step 2: Open the correct individual nahiya map file.
    map_file = maps_dir / f"{correct_nahiya}.html"
    if not map_file.is_file():
        print(f"  [MAP_ERROR] Index points to '{correct_nahiya}.html', but file not found.")
        return None, None

    try:
        with open(map_file, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')

        # Step 3: Extract the map container and activate the highlight.
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
        print(f"  [ERROR] Failed to process minimap for {village_name} from {correct_nahiya}.html: {e}")
        return None, None

def md_find_nahiya(md: str) -> str:
    # Try finding it in the YAML frontmatter first
    m_fm = re.search(r'(?s)^---\s*(.*?)\s*---', md)
    if m_fm:
        fm = m_fm.group(1)
        # Regex to find 'nahiyah:' followed by a list item '- value'
        m_nahiya = re.search(r'(?mi)^\s*nahiyah\s*:\s*\n\s*-\s*(.+)$', fm)
        if m_nahiya:
            return m_nahiya.group(1).strip()

    # Fallback to the old method (searching for ## Nahiya)
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
    for m in re.finditer(r'!\[\[\s*([^\]\|]+?)(?:\|.*?)?\s*\]\]', photos_block):
        out.append(m.group(1).strip())
    return out

def convert_md_to_html_basic(md_text: str) -> str:
    # This new version processes content in blocks to hide empty headings.

    # First, strip the unwanted '==' highlight markers from the raw text
    md_text = re.sub(r'==(.+?)==', r'\1', md_text)

    # Split the entire text into chunks based on ### or #### headings.
    # The regex keeps the headings as part of the list.
    blocks = re.split(r'(^\s*####?.*\n?)', md_text, flags=re.MULTILINE)
    
    final_html_parts = []

    # Helper function to convert a simple block of text (no headings) to HTML
    def _convert_simple_block_to_html(block_text):
        lines = block_text.strip().splitlines()
        if not lines:
            return ""

        html_lines = []
        in_ul = False
        in_ol = False
        def close_lists():
            nonlocal in_ul, in_ol
            if in_ul: html_lines.append('</ul>'); in_ul = False
            if in_ol: html_lines.append('</ol>'); in_ol = False

        for line in lines:
            s = line.strip()
            s_esc = html.escape(s)
            s_esc = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s_esc)
            s_esc = re.sub(r'\[\[(.+?)\]\]', r'<span class="internal-link">\1</span>', s_esc)
            
            if s == '---' or not s:
                close_lists()
                continue
            if re.match(r'^[-\*]\s+', s):
                if in_ol: close_lists()
                if not in_ul: html_lines.append('<ul>'); in_ul = True
                item_content = re.sub(r'^[-\*]\s+', '', s_esc, count=1)
                html_lines.append(f'<li>{item_content}</li>')
                continue
            if re.match(r'^\d+\.\s+', s):
                if in_ul: close_lists()
                if not in_ol: html_lines.append('<ol>'); in_ol = True
                item_content = re.sub(r'^\d+\.\s+', '', s_esc, count=1)
                html_lines.append(f'<li>{item_content}</li>')
                continue
            
            close_lists()
            html_lines.append(f'<p>{s_esc}</p>')

        close_lists()
        return "\n".join(html_lines)

    # Process any text that came before the first heading
    initial_content = blocks[0]
    if has_meaningful_content(initial_content):
        final_html_parts.append(_convert_simple_block_to_html(initial_content))

    # Process the remaining blocks in pairs of (heading, content)
    for i in range(1, len(blocks), 2):
        heading_line = blocks[i].strip()
        content_block = blocks[i+1] if (i + 1) < len(blocks) else ""

        # The critical check: only proceed if the content block is not empty.
        if has_meaningful_content(content_block):
            # Add the heading's HTML
            m_h4 = re.match(r'^\s*####\s*(.*)', heading_line)
            if m_h4:
                final_html_parts.append(f'<h4 class="font-semibold text-lg mt-4 mb-2">{html.escape(m_h4.group(1).strip())}</h4>')
            else:
                m_h3 = re.match(r'^\s*###\s*(.*)', heading_line)
                if m_h3:
                    final_html_parts.append(f'<h3 class="font-semibold text-xl mt-6 mb-3">{html.escape(m_h3.group(1).strip())}</h3>')
            
            # Add the content's HTML
            final_html_parts.append(_convert_simple_block_to_html(content_block))
            
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

def section_or_placeholder(title: str, body_md: str, open_details=True) -> str:
    if not has_meaningful_content(body_md):
        return ""
    
    content = convert_md_to_html_basic(body_md)
    open_attr = " open" if open_details else ""
    return f'<details class="group"{open_attr}><summary class="flex justify-between items-center font-semibold p-3 cursor-pointer text-lg"><span>{html.escape(title)}</span><svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 transform transition-transform group-open:rotate-180 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg></summary><div class="p-4 prose max-w-none">{content}</div></details>'

def section_or_placeholder_plain(title: str, body_md: str, open_details=True) -> str:
    if not has_meaningful_content(body_md):
        return ""
        
    content = convert_md_to_html_basic(body_md)
    open_attr = " open" if open_details else ""
    return f'<details class="group"{open_attr}><summary class="flex justify-between items-center font-semibold p-3 cursor-pointer text-lg"><span>{html.escape(title)}</span><svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 transform transition-transform group-open:rotate-180 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg></summary><div class="p-4">{content}</div></details>'

def photos_grid_html(name: str, photos: list) -> str:
    if not photos:
        return '<div class="italic subtext">No photos available.</div>'
    tiles = []
    for fn in photos:
        src = f"../village_photos/{fn}"
        alt = f"Photo of {name}"
        placeholder = 'https://placehold.co/600x400/e2e8f0/4a5568?text=' + html.escape(fn).replace(' ', '+')
        tiles.append(f'<img src="{html.escape(src)}" alt="{html.escape(alt)}" class="lightbox-trigger rounded-lg w-full h-auto object-cover border themed-border cursor-pointer" onerror="this.onerror=null;this.src=\'{placeholder}\';">')
    return '<div class="grid grid-cols-1 md:grid-cols-2 gap-4">\n' + "\n".join(tiles) + '\n</div>'

def build_html_page(name, nahiya, aliases, lat, lng,
                    summaries_I, summaries_II, summaries_III, summaries_IV,
                    links_md,
                    vi_history, vii_families, viii_culture, ix_dengbej, x_connections,
                    xi_ar_tirej, xii_axw_en, xiii_halil_en, xiv_flo_en, xv_afr366_en, xvi_zeyton_en, xvii_other_en,
                    xviii_axw_ku, xix_halil_ku, xx_flo_ku, xxi_afr366_ku, xxii_zeyton_ku, xxiii_other_ku,
                    photos,
                    foundation_txt, size_txt, tribes_txt, families_txt,
                    minimap_html, minimap_css):
    today = datetime.now().strftime("%B %d, %Y")
    aliases_txt = ", ".join([a for a in aliases if a]) if aliases else ""
    nahiya_disp = nahiya if nahiya else "unknown"

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
        .prose p { margin-bottom: 1rem; }
        .prose ol, .prose ul { margin-bottom: 1rem; }
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
                            <div>
                                <h3 class="text-sm font-medium subtext">Nahiya (Subdistrict)</h3>
                                <p class="text-lg">__NAHIYA__</p>
                            </div>
                            <div>
                                <h3 class="text-sm font-medium subtext">Also Known As</h3>
                                <p class="text-lg">__ALIASES__</p>
                            </div>
                            <div>
                                <h3 class="text-sm font-medium subtext">Tribes</h3>
                                <p class="text-lg">__TRIBES__</p>
                            </div>
                            <div>
                                <h3 class="text-sm font-medium subtext">Families, Clans, etc.</h3>
                                <p class="text-lg">__FAMILIES__</p>
                            </div>
                            <div>
                                <h3 class="text-sm font-medium subtext">Foundation Date</h3>
                                <p class="text-lg">__FOUNDATION__</p>
                            </div>
                            <div>
                                <h3 class="text-sm font-medium subtext">Size</h3>
                                <p class="text-lg">__SIZE__</p>
                            </div>
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

            __SUMMARIES_CARD__

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

    # Summaries Card
    sum_i   = section_or_placeholder(f"I. Summary from TirejAfrin Site of {name} (English)", summaries_I, open_details=True)
    sum_ii  = section_or_placeholder_plain(f"II. Summary from Ax û Walat Transcript of {name}", summaries_II)
    sum_iii = section_or_placeholder_plain(f"III. Summary from other Channels' Transcripts of {name}", summaries_III) if has_meaningful_content(summaries_III) else ""
    sum_iv  = section_or_placeholder_plain(f"IV. Summary from other Sources of {name}", summaries_IV)
    summaries_content = [sum_i, sum_ii, sum_iii, sum_iv]
    summaries_card_html = ""
    if any(summaries_content):
        summaries_card_html = f'''<div class="card p-6 rounded-xl">
                <h2 class="text-2xl font-semibold border-b themed-border pb-3 mb-4">Summaries</h2>
                <div class="space-y-4">{"<hr class=\"themed-border\">".join(s for s in summaries_content if s)}</div>
            </div>'''

    # Links Card
    links_html = build_links_html(links_md)
    links_card_html = ""
    if links_md.strip(): # Links has its own check
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
            
    # Additional Summaries and Transcripts Card
    xi  = section_or_placeholder_plain("XI. Summary from TirejAfrin Site (Arabic)", xi_ar_tirej)
    xii = section_or_placeholder_plain("XII. Ax û Walat Transcript (English)", xii_axw_en)
    xiii= section_or_placeholder_plain("XIII. Halil Sino Transcript (English)", xiii_halil_en)
    xiv = section_or_placeholder_plain("XIV. Afrin Flo Transcript (English)", xiv_flo_en)
    xv  = section_or_placeholder_plain("XV. Afrin 366 Transcript (English)", xv_afr366_en)
    xvi = section_or_placeholder_plain("XVI. Afrin Zeyton Transcript (English)", xvi_zeyton_en)
    xvii= section_or_placeholder_plain("XVII. Other Transcripts (English)", xvii_other_en)
    xviii=section_or_placeholder_plain("XVIII. Ax û Walat Transcript (Kumancî)", xviii_axw_ku)
    xix = section_or_placeholder_plain("XIX. Halil Sino Transcript (Kumancî)", xix_halil_ku)
    xx  = section_or_placeholder_plain("XX. Afrin Flo Transcript (Kumancî)", xx_flo_ku)
    xxi = section_or_placeholder_plain("XXI. Afrin 366 Transcript (Kumancî)", xxi_afr366_ku)
    xxii= section_or_placeholder_plain("XXII. Afrin Zeyton Transcript (Kumancî)", xxii_zeyton_ku)
    xxiii=section_or_placeholder_plain("XXIII. Other Transcripts (Kumancî)", xxiii_other_ku)
    add_transcripts_content = [xi, xii, xiii, xiv, xv, xvi, xvii, xviii, xix, xx, xxi, xxii, xxiii]
    add_transcripts_card_html = ""
    if any(add_transcripts_content):
        add_transcripts_card_html = f'''<div class="card p-6 rounded-xl">
                <h2 class="text-2xl font-semibold border-b themed-border pb-3 mb-4">Additional Summaries and Transcripts</h2>
                <div class="space-y-4">{"<hr class=\"themed-border\">".join(s for s in add_transcripts_content if s)}</div>
            </div>'''

    photos_html = photos_grid_html(name, photos)

    out = (html_template
           .replace("__NAME__", html.escape(name))
           .replace("__NAHIYA__", html.escape(nahiya_disp))
           .replace("__ALIASES__", html.escape(aliases_txt))
           .replace("__TRIBES__", html.escape(tribes_txt))
           .replace("__FAMILIES__", html.escape(families_txt))
           .replace("__FOUNDATION__", html.escape(foundation_txt or ""))
           .replace("__SIZE__", html.escape(size_txt or ""))
           .replace("__LAT__", "" if lat is None else str(lat))
           .replace("__LNG__", "" if lng is None else str(lng))
           .replace("__LAT_JS__", "null" if lat is None else str(lat))
           .replace("__LNG_JS__", "null" if lng is None else str(lng))
           .replace("__PHOTOS__", photos_html)
           .replace("__SUMMARIES_CARD__", summaries_card_html)
           .replace("__LINKS_CARD__", links_card_html)
           .replace("__ADDITIONAL_INFO_CARD__", add_info_card_html)
           .replace("__ADDITIONAL_TRANSCRIPTS_CARD__", add_transcripts_card_html)
           .replace("__TODAY__", html.escape(today))
           .replace("__MINIMAP_CSS__", minimap_css or "")
           .replace("__MINIMAP_COLUMN__", minimap_column_html)
          )
    return out

def parse_foundation_and_size(md: str):
    foundation = ""
    size = ""
    for line in md.splitlines():
        m1 = re.match(r'(?i)^\s*Foundation\s*Date\s*:\s*(.+)$', line.strip())
        if m1: foundation = m1.group(1).strip()
        m2 = re.match(r'(?i)^\s*Size\s*:\s*(.+)$', line.strip())
        if m2: size = m2.group(1).strip()
    return foundation, size

def normalize_section_title(t: str) -> str:
    return re.sub(r'\s+', ' ', t.strip().lower())

def extract_expected_sections(md: str) -> dict:
    secs_raw = md_sections(md)
    lookup = {normalize_section_title(k): v for k, v in secs_raw.items()}
    def find_by_prefix(num_roman, keyword):
        for k_norm, v in lookup.items():
            if k_norm.startswith(f"{num_roman.lower()}.") and keyword in k_norm:
                return v
        return ""
    out = {}
    out["I"]   = find_by_prefix("I","tirej") or lookup.get("i. summary from tirejafrin site (english)", "")
    out["II"]  = find_by_prefix("II","ax")   or lookup.get("ii. summary from ax û walat transcript", "")
    out["III"] = find_by_prefix("III","other") or lookup.get("iii. summary from other channels' transcripts", "")
    out["IV"]  = find_by_prefix("IV","source") or lookup.get("iv. summary from other sources", "")
    out["V_links"] = lookup.get("v. links", "")
    out["VI"]  = lookup.get("vi. history", "")
    out["VII"] = lookup.get("vii. families, clans, etc.", "")
    out["VIII"]= lookup.get("viii. cultural aspects", "")
    out["IX"]  = lookup.get("ix. dengbêj/çirok", "") or lookup.get("ix. dengbej/cirok", "")
    out["X"]   = lookup.get("x. connections with other villages", "")
    out["XI"]  = lookup.get("xi. summary from tirejafrin site (arabic)", "")
    out["XII"] = lookup.get("xii. ax û walat transcript (english)", "")
    out["XIII"]= lookup.get("xiii. halil sino transcript (english)", "")
    out["XIV"] = lookup.get("xiv. afrin flo transcript (english)", "")
    out["XV"]  = lookup.get("xv. afrin 366 transcript (english)", "")
    out["XVI"] = lookup.get("xvi. afrin zeyton transcript (english)", "")
    out["XVII"]= lookup.get("xvii. other transcripts (english)", "")
    out["XVIII"]= lookup.get("xviii. ax û walat transcript (kumancî)", "") or lookup.get("xviii. ax û walat transcript (kurmancî)", "")
    out["XIX"] = lookup.get("xix. halil sino transcript (kumancî)", "") or lookup.get("xix. halil sino transcript (kurmancî)", "")
    out["XX"]  = lookup.get("xx. afrin flo transcript (kumancî)", "") or lookup.get("xx. afrin flo transcript (kurmancî)", "")
    out["XXI"] = lookup.get("xxi. afrin 366 transcript (kumancî)", "") or lookup.get("xxi. afrin 366 transcript (kurmancî)", "")
    out["XXII"]= lookup.get("xxii. afrin zeyton transcript (kumancî)", "") or lookup.get("xxii. afrin zeyton transcript (kurmancî)", "")
    out["XXIII"]= lookup.get("xxiii. other transcripts (kumancî)", "") or lookup.get("xxiii. other transcripts (kurmancî)", "")
    return out

def md_find_yaml_list(md: str, key: str) -> list:
    items = []
    m = re.search(r'(?s)^---\s*(.*?)\s*---', md)
    if not m:
        return items
    fm = m.group(1)

    # Regex to find the key and capture the subsequent list items
    pattern = re.compile(rf'^\s*{re.escape(key)}\s*:\s*\n((?:\s*-\s*.+\n?)+)', re.MULTILINE | re.IGNORECASE)
    match = pattern.search(fm)

    if match:
        list_block = match.group(1)
        items = [item.strip() for item in re.findall(r'^\s*-\s*(.+)$', list_block, re.MULTILINE)]
    
    return items

def process_one(md_path: Path, out_dir: Path, master_lookup: dict):
    md = read_text(md_path)
    name = md_path.stem
    aliases = md_find_yaml_aliases(md)
    nahiya = md_find_nahiya(md) or "unknown"
    lat, lng = md_find_coords(md)
    photos = md_find_photos(md)
    foundation, size = parse_foundation_and_size(md)

    # Use the new, simple map extraction method
    minimap_html, minimap_css = extract_minimap(name, Path(NAHIYA_MAPS_DIR), master_lookup)

    # Extract families/tribes from YAML
    tribes_list = md_find_yaml_list(md, "tribes")
    families_list = md_find_yaml_list(md, "families, clans, etc")
    
    # Convert lists to simple text, just like aliases
    tribes_txt = ", ".join(tribes_list)
    families_txt = ", ".join(families_list)

    sec = extract_expected_sections(md)
    vii_data = sec["VII"]

    html_text = build_html_page(
        name=name, nahiya=nahiya, aliases=aliases, lat=lat, lng=lng,
        summaries_I=sec["I"], summaries_II=sec["II"], summaries_III=sec["III"], summaries_IV=sec["IV"],
        links_md=sec["V_links"],
        vi_history=sec["VI"], vii_families=vii_data, viii_culture=sec["VIII"], ix_dengbej=sec["IX"], x_connections=sec["X"],
        xi_ar_tirej=sec["XI"], xii_axw_en=sec["XII"], xiii_halil_en=sec["XIII"], xiv_flo_en=sec["XIV"], xv_afr366_en=sec["XV"], xvi_zeyton_en=sec["XVI"], xvii_other_en=sec["XVII"],
        xviii_axw_ku=sec["XVIII"], xix_halil_ku=sec["XIX"], xx_flo_ku=sec["XX"], xxi_afr366_ku=sec["XXI"], xxii_zeyton_ku=sec["XXII"], xxiii_other_ku=sec["XXIII"],
        photos=photos, foundation_txt=foundation, size_txt=size,
        tribes_txt=tribes_txt, families_txt=families_txt,
        minimap_html=minimap_html, minimap_css=minimap_css
    )
    ensure_dir(out_dir)
    out_file = out_dir / f"{name}.html"
    out_file.write_text(html_text, encoding="utf-8")
    print(f"✓ Wrote: {out_file}")

def main():
    in_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(INPUT_PATH)
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(OUTPUT_DIR)
    
    # Build the master lookup index from the HTML file at the very beginning.
    master_lookup = build_master_lookup(Path(MASTER_MAP_PATH))
    if not master_lookup:
        print("Could not build master lookup. Exiting.")
        return

    if in_path.is_file():
        if in_path.suffix.lower() != ".md":
            print(f"Skipping non-md file: {in_path}")
            return
        process_one(in_path, out_dir, master_lookup)
    else:
        md_files = sorted([p for p in in_path.glob("*.md") if p.is_file()])
        if not md_files:
            print("No .md files found.")
            return

        batch_size = 15
        first_batch = md_files[:batch_size]
        rest_batch = md_files[batch_size:]

        print(f"--- Processing first batch of {len(first_batch)} files ---")
        for p in first_batch:
            process_one(p, out_dir, master_lookup)

        if rest_batch:
            print("---")
            try:
                choice = input(f"Continue with the remaining {len(rest_batch)} files? (y/N): ").lower()
                if choice == 'y':
                    print(f"--- Processing remaining {len(rest_batch)} files ---")
                    for p in rest_batch:
                        process_one(p, out_dir, master_lookup)
                else:
                    print("Processing stopped by user.")
            except (KeyboardInterrupt, EOFError):
                print("\nProcessing stopped by user.")

if __name__ == "__main__":
    main()
