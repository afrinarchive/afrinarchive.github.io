#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Village Transcript Markdown -> HTML generator.
Converts transcript .md files to styled HTML pages matching the village site design.
Parses ## Translation and ## Transcript sections separately.
"""
import sys
from pathlib import Path
from datetime import datetime
import re
import html
import yaml

INPUT_PATH  = r"H:\\My Drive\\Zachar\\1 - PhD\\Villages_Transcripts"
OUTPUT_DIR  = r"C:\\Users\\Zachar\\Desktop\\Afrin_Archive\\village_transcripts"

def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def parse_yaml_frontmatter(md_content: str) -> dict:
    """Extract YAML frontmatter from markdown file."""
    match = re.search(r'---\s*\n(.*?)\n---', md_content, re.DOTALL)
    if match:
        yaml_str = match.group(1)
        try:
            data = yaml.safe_load(yaml_str)
            if isinstance(data, dict):
                return data
        except yaml.YAMLError as e:
            print(f"  [YAML ERROR] Could not parse frontmatter: {e}")
    return {}

def parse_transcript_sections(md_content: str) -> tuple:
    """
    Parse the markdown to extract Translation (English) and Transcript (Kurdish) sections.
    Returns (translation_text, transcript_text)
    """
    # Remove YAML frontmatter
    content = re.sub(r'^---\s*\n.*?\n---\s*\n?', '', md_content, flags=re.DOTALL)
    # Remove the "# Transcript of..." header line if present
    content = re.sub(r'^#\s+Transcript of.*?\n', '', content, flags=re.MULTILINE)
    
    translation_text = ""
    transcript_text = ""
    
    # Look for ## Translation and ## Transcript sections
    translation_match = re.search(r'##\s*Translation\s*\n(.*?)(?=##\s*Transcript|$)', content, re.DOTALL | re.IGNORECASE)
    transcript_match = re.search(r'##\s*Transcript\s*\n(.*?)$', content, re.DOTALL | re.IGNORECASE)
    
    if translation_match:
        translation_text = translation_match.group(1).strip()
    
    if transcript_match:
        transcript_text = transcript_match.group(1).strip()
    
    # If no sections found, treat entire content as transcript (fallback)
    if not translation_text and not transcript_text:
        transcript_text = content.strip()
    
    return translation_text, transcript_text

def get_last_timestamp(text: str) -> str:
    """Extract the last timestamp from text (HH:MM:SS or MM:SS or HH:MM)."""
    if not text:
        return "N/A"
    # Matches timestamps like 00:04, 01:23:45, etc. at start of line
    matches = re.findall(r'(?:^|\n)\s*\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?', text)
    if matches:
        return matches[-1]
    # Fallback to looking anywhere if not found at start of line
    matches = re.findall(r'(\d{1,2}:\d{2}(?::\d{2})?)', text)
    if matches:
        return matches[-1]
    return "N/A"

def convert_transcript_to_html(transcript_text: str) -> str:
    """Convert timestamped transcript text to HTML paragraphs."""
    if not transcript_text.strip():
        return ''
    
    lines = transcript_text.strip().splitlines()
    html_lines = []
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        
        # Check if line starts with a timestamp (e.g., "06:33:" or "40:09:") or "[06:33]"
        timestamp_match = re.match(r'^\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?:?\s*(.*)$', stripped)
        if timestamp_match:
            timestamp = timestamp_match.group(1)
            content = timestamp_match.group(2).strip()
            content_esc = html.escape(content)
            html_lines.append(
                f'<p class="mb-2"><span class="font-mono text-sm subtext mr-2">[{html.escape(timestamp)}]</span>{content_esc}</p>'
            )
        else:
            # Regular line without timestamp
            html_lines.append(f'<p class="mb-2">{html.escape(stripped)}</p>')
    
    return '\n'.join(html_lines)

def build_html_page(village_name: str, source_name: str, video_url: str, 
                    translation_text: str, transcript_text: str,
                    duration: str) -> str:
    """Build the complete HTML page for a transcript."""
    today = datetime.now().strftime("%B %d, %Y")
    
    # Convert both sections to HTML
    translation_html = convert_transcript_to_html(translation_text)
    transcript_html = convert_transcript_to_html(transcript_text)
    
    # Build placeholder messages if empty
    if not translation_html:
        translation_html = '<p class="italic subtext">English translation not yet available.</p>'
    if not transcript_html:
        transcript_html = '<p class="italic subtext">Transkrîpt hêj tune ye.</p>'
    
    # Build video link HTML
    video_link_html = ""
    if video_url and video_url.strip():
        video_link_html = f'''<div class="mt-4">
                    <a href="{html.escape(video_url)}" target="_blank" rel="noopener noreferrer" class="external-link hover:underline flex items-center gap-2">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M19.615 3.184c-3.604-.246-11.631-.245-15.23 0-3.897.266-4.356 2.62-4.385 8.816.029 6.185.484 8.549 4.385 8.816 3.6.245 11.626.246 15.23 0 3.897-.266 4.356-2.62 4.385-8.816-.029-6.185-.484-8.549-4.385-8.816zm-10.615 12.816v-8l8 3.993-8 4.007z"/>
                        </svg>
                        Watch on YouTube
                    </a>
                </div>'''
    
    html_template = """<!DOCTYPE html>
<html lang="en" class="">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Transcript | __VILLAGE_NAME__ - __SOURCE_NAME__</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
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
        .prose strong { font-weight: 600; }
        .prose p { margin-bottom: 1rem; }
        .prose ol, .prose ul { margin-bottom: 1rem; }
        .prose blockquote { border-left: 3px solid var(--blockquote-border-color); padding-left: 1rem; margin-left: 0; margin-bottom: 1rem; }
        .prose blockquote p { color: var(--text-color); }
        .toggle-button-colors { background-color: var(--text-color); color: var(--bg-color); border: 1px solid var(--border-color); }
        .jump-btn { padding: 0.5rem 1rem; border: 1px solid var(--border-color); border-radius: 0.5rem; font-size: 0.875rem; transition: all 0.2s; }
        .jump-btn:hover { background-color: var(--button-hover-bg); color: var(--button-hover-text); }
        .copy-btn { padding: 0.25rem 0.75rem; border: 1px solid var(--border-color); border-radius: 0.375rem; font-size: 0.75rem; transition: all 0.2s; display: inline-flex; align-items: center; gap: 0.25rem; }
        .copy-btn:hover { background-color: var(--button-hover-bg); color: var(--button-hover-text); }
        .copy-btn svg { width: 14px; height: 14px; }
    </style>
</head>
<body>
    <div class="container mx-auto p-4 sm:p-6 md:p-8 max-w-4xl">
        <header class="mb-8">
            <h1 class="text-3xl sm:text-4xl md:text-5xl font-bold">__VILLAGE_NAME__</h1>
            <p class="text-xl subtext mt-2">Transcript from __SOURCE_NAME__</p>
        </header>

        <main class="space-y-6">
            <!-- General Info Card -->
            <div class="card p-6 rounded-xl">
                <div class="flex justify-between items-center border-b themed-border pb-3 mb-4">
                    <h2 class="text-2xl font-semibold">Transcript Information</h2>
                    <button id="theme-toggle" class="toggle-button-colors p-2 rounded-full focus:outline-none focus:ring-2 focus:ring-offset-2" style="--ring-offset-color: var(--card-bg-color); --ring-color: var(--border-color);">
                        <svg id="theme-toggle-dark-icon" class="hidden h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"></path></svg>
                        <svg id="theme-toggle-light-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="hidden h-6 w-6">
                          <path stroke-linecap="round" stroke-linejoin="round" d="M12 3v2.25m6.364.386-1.591 1.591M21 12h-2.25m-.386 6.364-1.591-1.591M12 18.75V21m-4.773-4.227-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0Z" />
                        </svg>
                    </button>
                </div>
                <div class="grid grid-cols-1 gap-4">
                    <div>
                        <h3 class="text-sm font-medium subtext">Village</h3>
                        <p class="text-lg">__VILLAGE_NAME__</p>
                    </div>
                    <div>
                        <h3 class="text-sm font-medium subtext">Source Channel</h3>
                        <p class="text-lg">__SOURCE_NAME__</p>
                    </div>
                    <div>
                        <h3 class="text-sm font-medium subtext">Length</h3>
                        <p class="text-lg">__DURATION__</p>
                    </div>
                    __VIDEO_LINK__
                </div>
                <!-- Jump Buttons -->
                <div class="flex flex-wrap gap-3 mt-6 pt-4 border-t themed-border">
                    <a href="#english" class="jump-btn">Go to Translation</a>
                    <a href="#kurdish" class="jump-btn">Biçe Transkrîptê</a>
                </div>
            </div>

            <!-- English Translation Card -->
            <div id="english" class="card p-6 rounded-xl">
                <div class="flex justify-between items-center border-b themed-border pb-3 mb-4">
                    <h2 class="text-2xl font-semibold">English Translation</h2>
                    <button class="copy-btn" onclick="copySection('translation-content')">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                        Copy
                    </button>
                </div>
                <div id="translation-content" class="prose max-w-none">
                    __TRANSLATION_CONTENT__
                </div>
            </div>

            <!-- Kurdish Transcript Card -->
            <div id="kurdish" class="card p-6 rounded-xl">
                <div class="flex justify-between items-center border-b themed-border pb-3 mb-4">
                    <h2 class="text-2xl font-semibold">Transkrîpta bi Kurmancî</h2>
                    <button class="copy-btn" onclick="copySection('transcript-content')">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                        Kopî bike
                    </button>
                </div>
                <div id="transcript-content" class="prose max-w-none">
                    __TRANSCRIPT_CONTENT__
                </div>
            </div>

        </main>

        <footer class="text-center mt-12 py-4 border-t themed-border">
            <p class="text-sm subtext">Page Updated on __TODAY__</p>
        </footer>
    </div>

    <script>
        // Theme toggle
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

        // Copy to clipboard function
        function copySection(elementId) {
            const element = document.getElementById(elementId);
            const text = element.innerText;
            navigator.clipboard.writeText(text).then(() => {
                // Find the button that was clicked and update its text
                const btn = event.target.closest('.copy-btn');
                const originalText = btn.innerHTML;
                btn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width:14px;height:14px"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg> ✓';
                setTimeout(() => { btn.innerHTML = originalText; }, 2000);
            }).catch(err => {
                console.error('Failed to copy: ', err);
            });
        }
    </script>
</body>
</html>"""
    
    out = (html_template
           .replace("__VILLAGE_NAME__", html.escape(village_name))
           .replace("__SOURCE_NAME__", html.escape(source_name))
           .replace("__DURATION__", html.escape(duration))
           .replace("__VIDEO_LINK__", video_link_html)
           .replace("__TRANSLATION_CONTENT__", translation_html)
           .replace("__TRANSCRIPT_CONTENT__", transcript_html)
           .replace("__TODAY__", html.escape(today))
          )
    return out

def process_one(md_path: Path, out_dir: Path):
    """Process a single transcript markdown file."""
    filename = md_path.stem
    out_file = out_dir / f"{filename}.html"

    # Check if HTML is newer than MD (skip if so)
    if out_file.exists():
        md_mtime = md_path.stat().st_mtime
        html_mtime = out_file.stat().st_mtime
        if md_mtime <= html_mtime:
            return

    md = read_text(md_path)
    fm_data = parse_yaml_frontmatter(md)

    # Extract frontmatter fields
    village_name = fm_data.get('transcript village', filename.split('_')[0] if '_' in filename else filename)
    source_name = fm_data.get('transcript source', '')
    video_url = fm_data.get('transcript url', '')
    
    # If source name not in frontmatter, try to extract from filename
    if not source_name and '_' in filename:
        parts = filename.rsplit('_', 1)
        if len(parts) >= 2:
            source_name = parts[0].split('_', 1)[-1] if '_' in parts[0] else ''

    # Parse translation and transcript sections
    translation_text, transcript_text = parse_transcript_sections(md)
    
    # Get last timestamp from English translation section
    duration = get_last_timestamp(translation_text)

    # Build HTML
    html_text = build_html_page(
        village_name=village_name,
        source_name=source_name,
        video_url=video_url,
        translation_text=translation_text,
        transcript_text=transcript_text,
        duration=duration
    )
    
    ensure_dir(out_dir)
    out_file.write_text(html_text, encoding="utf-8")
    print(f"✓ Generated: {out_file}")

def main():
    in_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(INPUT_PATH)
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(OUTPUT_DIR)
    
    failed_files = []

    if in_path.is_file():
        if in_path.suffix.lower() != ".md":
            print(f"Skipping non-md file: {in_path}")
            return
        try:
            process_one(in_path, out_dir)
        except Exception as e:
            print(f"✗ ERROR processing {in_path.name}: {e}")
            failed_files.append((in_path.name, e))
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
            try:
                process_one(p, out_dir)
            except Exception as e:
                print(f"✗ ERROR processing {p.name}: {e}")
                failed_files.append((p.name, e))

        if rest_batch:
            print("---")
            try:
                choice = input(f"Continue with the remaining {len(rest_batch)} files? (y/N): ").lower()
                if choice == 'y':
                    print(f"--- Processing remaining {len(rest_batch)} files ---")
                    for p in rest_batch:
                        try:
                            process_one(p, out_dir)
                        except Exception as e:
                            print(f"✗ ERROR processing {p.name}: {e}")
                            failed_files.append((p.name, e))
                else:
                    print("Processing stopped by user.")
            except (KeyboardInterrupt, EOFError):
                print("\nProcessing stopped by user.")

    if failed_files:
        print("\n" + "="*20 + " SUMMARY OF FAILURES " + "="*20)
        print(f"Completed with {len(failed_files)} error(s).")
        for name, error in failed_files:
            print(f"  - File: {name}\n    Reason: {error}")
    else:
        print("\nProcessing completed successfully with no errors.")

if __name__ == "__main__":
    main()
