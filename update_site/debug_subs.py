import os

SUBTITLES_DIR = r"C:\Users\Zachar\Desktop\programs I made\python programs\archive programs\make_subtitles\subtitle_files"

print(f"Listing {SUBTITLES_DIR}...")
try:
    items = os.listdir(SUBTITLES_DIR)
    for item in items:
        print(f" - {item}")
        if "khalil" in item.lower() or "halil" in item.lower():
            full_path = os.path.join(SUBTITLES_DIR, item)
            if os.path.isdir(full_path):
                print(f"   [DIR MATCH] Contents of {item}:")
                subfiles = os.listdir(full_path)
                for s in subfiles[:5]:
                    print(f"     - {s}")
except Exception as e:
    print(f"Error: {e}")
