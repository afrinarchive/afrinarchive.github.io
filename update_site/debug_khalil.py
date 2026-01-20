import os
from pathlib import Path

TRANSCRIPTS_SOURCE_DIR = r"H:\My Drive\Zachar\1 - PhD\Villages_Transcripts"
SUBTITLES_SOURCE_DIR = r"C:\Users\Zachar\Desktop\programs I made\python programs\archive programs\make_subtitles\subtitle_files"

def list_dir(path):
    print(f"--- Listing {path} ---")
    try:
        p = Path(path)
        if not p.exists():
            print("Path does not exist!")
            return
        
        items = list(p.iterdir())
        print(f"Found {len(items)} items.")
        for item in items[:10]:
            print(f"  {item.name}")
            
        # Check specifically for Khalil/Halil folders
        for item in items:
            if "khalil" in item.name.lower() or "halil" in item.name.lower():
                print(f"  -> FOUND MATCH: {item.name}")
                if item.is_dir():
                     subitems = list(item.iterdir())
                     print(f"     First 5 files in {item.name}:")
                     for s in subitems[:5]:
                         print(f"       {s.name}")

    except Exception as e:
        print(f"Error: {e}")

print("Checking Directories...")
list_dir(SUBTITLES_SOURCE_DIR)

print("\nChecking Transcript content for 'Khalil'...")
# Scan a few transcript files to see the 'source' metadata
try:
    t_dir = Path(TRANSCRIPTS_SOURCE_DIR)
    count = 0
    for f in t_dir.glob("*.md"):
        txt = f.read_text(encoding="utf-8", errors="ignore")
        if "Khalil" in txt or "Halil" in txt:
            print(f"Match in {f.name}:")
            for line in txt.splitlines():
                if "source:" in line.lower():
                    print(f"  {line.strip()}")
            count += 1
            if count >= 5: break
except Exception as e:
    print(f"Error scanning transcripts: {e}")
