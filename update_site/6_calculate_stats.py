#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to calculate statistics and update index.html.
1. Calculates total duration of transcripts.
2. Counts total number of transcript files.
3. Counts total number of villages from 00_village_names.html.
4. Updates index.html with these stats in bold.
"""

import os
import re
import math
from pathlib import Path
from datetime import timedelta

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
TRANSCRIPTS_DIR = BASE_DIR / "village_transcripts"
VILLAGE_NAMES_FILE = BASE_DIR / "village_site_files" / "00_village_names.html"
INDEX_FILE = BASE_DIR / "index.html"

def parse_time_string(time_str):
    """Parses a time string (MM:SS or HH:MM:SS) into a timedelta object."""
    try:
        parts = list(map(int, time_str.split(':')))
        if len(parts) == 2:
            return timedelta(minutes=parts[0], seconds=parts[1])
        elif len(parts) == 3:
            return timedelta(hours=parts[0], minutes=parts[1], seconds=parts[2])
        else:
            return timedelta(0)
    except ValueError:
        return timedelta(0)

def count_villages():
    """Counts unique villages from 00_village_names.html."""
    if not VILLAGE_NAMES_FILE.exists():
        print(f"[!] Village names file not found: {VILLAGE_NAMES_FILE}")
        return 366 # Fallback to existing number
    
    try:
        content = VILLAGE_NAMES_FILE.read_text(encoding="utf-8")
        # Count occurrences of "filename" which indicates a village entry in the detailed list
        # We search globally because "filename" property only appears in the all_villages_detailed list
        count = len(re.findall(r'"filename":', content))
        return count
    except Exception as e:
        print(f"[!] Error reading village names: {e}")
        return 366

def main():
    print("Starting Stats Calculation...")
    
    # 1. Calculate Transcript Stats
    html_files = list(TRANSCRIPTS_DIR.glob("*.html"))
    total_duration = timedelta()
    files_processed = 0
    files_with_duration = 0

    length_pattern = re.compile(r'Length\s*</h3>\s*<p[^>]*>\s*([\d:]+)\s*</p>', re.IGNORECASE)

    for file_path in html_files:
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            match = length_pattern.search(content)
            
            if match:
                time_str = match.group(1)
                duration = parse_time_string(time_str)
                total_duration += duration
                files_with_duration += 1
            files_processed += 1
        except Exception as e:
            print(f"  [!] Error processing {file_path.name}: {e}")

    total_seconds = int(total_duration.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    # Round up to the next minute if there are seconds
    if seconds > 0:
        minutes += 1
        
    if minutes == 60:
        hours += 1
        minutes = 0
    
    transcript_count = len(html_files)
    village_count = count_villages()

    print(f"Stats Calculated:")
    print(f"  - Duration: {hours} Hours, {minutes} Minutes")
    print(f"  - Transcripts: {transcript_count}")
    print(f"  - Villages: {village_count}")

    # 2. Update index.html
    if not INDEX_FILE.exists():
        print(f"[ERROR] index.html not found: {INDEX_FILE}")
        return

    try:
        index_content = INDEX_FILE.read_text(encoding="utf-8")
        
        # Regex replacement patterns
        # We need to match the list items we added earlier
        # Pattern: <li>... Hours of Transcripts</li>
        # or <li><b>... Hours of Transcripts</b></li>
        
        # 1. Hours (Handling both previous "X Hours" and potential "X Hours, Y Minutes" patterns)
        # We look for "<li><b>... Transcripts</b></li>" to be safe and replace the whole inner part
        index_content = re.sub(
            r'<li><b>.*?Hours.*?Transcripts</b></li>', 
            f'<li><b>{hours} Hours, {minutes} Minutes of Transcripts</b></li>', 
            index_content, 
            flags=re.IGNORECASE
        )
        
        # 2. Transcribed Videos
        index_content = re.sub(
            r'<li>.*?Interview Videos Transcribed.*?</li>', 
            f'<li><b>{transcript_count} Interview Videos Transcribed</b></li>', 
            index_content, 
            flags=re.IGNORECASE
        )
        
        # 3. Villages Recorded
        index_content = re.sub(
            r'<li>.*?Villages Recorded.*?</li>', 
            f'<li><b>{village_count} Villages Recorded</b></li>', 
            index_content, 
            flags=re.IGNORECASE
        )

        INDEX_FILE.write_text(index_content, encoding="utf-8")
        print(f"[SUCCESS] Updated index.html with new stats.")

    except Exception as e:
        print(f"[ERROR] Failed to update index.html: {e}")

if __name__ == "__main__":
    main()
