import sqlite3
import pathlib
from bs4 import BeautifulSoup
import locale
import re



# --- CONFIGURATION ---
INPUT_DIR = pathlib.Path(r"C:\Users\Zachar\Desktop\Afrin_Archive\nahiyas")
DB_PATH = pathlib.Path(r"C:\Users\Zachar\Desktop\programs I made\python programs\archive programs\village names\all_only_village_names.db")
OUTPUT_DIR = pathlib.Path(r"C:\Users\Zachar\Desktop\Afrin_Archive\nahiyas")

def extract_nahiya_elements(file_path):
    """
    Parses a source HTML file to extract village links, the FIRST map container,
    and the raw text content of the style block.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')

        # --- Extract Village Data ---
        village_data = []
        links_container = soup.find('div', class_='bg-white')
        if links_container:
            for link in links_container.find_all('a', href=lambda href: href and href.startswith('#')):
                if link.get('id') != 'clear-link':
                    village_data.append({
                        'text': link.get_text(strip=True),
                        'href': link.get('href')
                    })

        # --- Extract ONLY THE FIRST Map Container ---
        map_container = soup.find('div', class_='map-container')
        map_container_html = str(map_container) if map_container else ""

        # --- Extract Raw CSS Text ---
        style_tag = soup.find('style')
        css_text = style_tag.string if style_tag else ""

        return {
            'villages': village_data,
            'map_container_html': map_container_html,
            'css_text': css_text
        }
    except Exception as e:
        print(f"  [ERROR] Could not read or parse {file_path.name}: {e}")
        return {'villages': [], 'map_container_html': "", 'css_text': ""}

def scope_css(css_text, nahiya_id):
    """
    Parses raw CSS text and prepends a section ID to each rule to make it specific.
    """
    if not css_text:
        return ""
    scoped_lines = []
    for line in css_text.splitlines():
        match = re.match(r'^\s*(\.-?[_a-zA-Z]+[_a-zA-Z0-9-]*.*\{)', line)
        if match:
            original_selector = match.group(1)
            scoped_line = line.replace(original_selector, f"#{nahiya_id} {original_selector}")
            scoped_lines.append(scoped_line)
        else:
            scoped_lines.append(line)
    scoped_css = "\n".join(scoped_lines)
    return f"/* --- COORDINATES FOR {nahiya_id.upper()} MAP --- */\n{scoped_css}\n"

def fetch_nahiya_data_from_db(db_path, nahiya_name):
    """Queries the database for a specific nahiya."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        query = "SELECT geojson_names, alt_names FROM locations WHERE nahiyah = ?"
        cursor.execute(query, (nahiya_name,))
        db_data = cursor.fetchall()
        conn.close()
        return db_data
    except Exception as e:
        print(f"  [ERROR] Could not query database for {nahiya_name}: {e}")
        return []

def generate_final_page(output_path, all_data):
    """
    Generates the final HTML file, replicating the exact structure,
    scoped CSS, and JavaScript of the working example file.
    """
    try:
        locale.setlocale(locale.LC_ALL, 'ku_TR.UTF-8')
    except locale.Error:
        print("[Warning] Kurmanji locale 'ku_TR.UTF-8' not found. Using default string sorting.")

    all_data.sort(key=lambda x: x['nahiya_name'])
    final_css = ""
    for data in all_data:
        final_css += data['scoped_css']

    html_content = f"""<!DOCTYPE html>
<html lang="ku">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nexşeyên Hemû Nahiyeyan - All Nahiyas Clickable Maps</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; margin: 0; background-color: #f4f4f9; color: #333; }}
        h1 {{ text-align: center; color: #2c3e50; padding: 20px 0; }}
        .nahiya-section {{ border-top: 5px solid #3498db; margin: 20px; background: #fff; box-shadow: 0 4px 8px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden; }}
        .nahiya-section h2 {{ background-color: #2c3e50; color: white; padding: 15px 20px; margin: 0; font-size: 1.5em; }}
        .content-wrapper {{ display: flex; flex-wrap: wrap; gap: 20px; padding: 20px; }}
        .village-list-column {{ flex: 1; min-width: 280px; }}
        .village-list-column a {{ display: block; padding: 9px 12px; color: #2980b9; text-decoration: none; border-bottom: 1px solid #f0f0f0; transition: background-color 0.2s, padding-left 0.2s; border-radius: 4px; }}
        .village-list-column a:hover {{ background-color: #ecf0f1; padding-left: 20px; }}
        a.clear-link {{ color: #c0392b; font-weight: bold; margin-top: 10px; }}
        a.clear-link:hover {{ background-color: #e74c3c; color: white; }}
        .maps-column {{ flex: 2; min-width: 300px; display: flex; justify-content: center; align-items: flex-start; }}
        .map-container {{ position: relative; width:100%; max-width: 500px; }}
        .map-container img {{ display: block; width: 100%; height: auto; border-radius: 5px; }}
        .highlight-box {{ display: none; position: absolute; background-color: yellow; opacity: 0.5; border-radius: 50%; pointer-events: none; }}
        
        {final_css}
    </style>
</head>
<body>
    <h1>Nexşeyên Hemû Nahiyeyan</h1>
"""
    for data in all_data:
        html_content += f'    <div class="nahiya-section" id="{data["nahiya_name"]}">\n'
        html_content += f'        <h2>{data["nahiya_name"]}</h2>\n'
        html_content += '        <div class="content-wrapper">\n'
        html_content += '            <div class="village-list-column">\n'
        
        try:
            sorted_matches = sorted(data['matches'], key=lambda m: locale.strxfrm(m['geojson_name']))
        except NameError:
            sorted_matches = sorted(data['matches'], key=lambda m: m['geojson_name'])

        for match in sorted_matches:
            html_content += f'                <a href="{match["href"]}">{match["geojson_name"]}</a>\n'
        
        html_content += '                <a href="#" class="clear-link">Vala Bike (Clear Highlight)</a>\n'
        html_content += '            </div>\n'
        html_content += '            <div class="maps-column">\n'
        if data['map_container_html']:
            html_content += f'                {data["map_container_html"]}\n'
        else:
            html_content += '                <p>Nexşe nehate dîtin (Map not found).</p>\n'
        html_content += '            </div>\n'
        html_content += '        </div>\n'
        html_content += '    </div>\n'
        
    html_content += """
    <script>
    function showHighlight() {
        document.querySelectorAll('.highlight-box').forEach(box => {
            box.style.display = 'none';
        });

        if (window.location.hash) {
            try {
                const activeLink = document.querySelector(`a[href="${window.location.hash}"]`);
                if (activeLink) {
                    const parentSection = activeLink.closest('.nahiya-section');
                    if (parentSection) {
                        const highlightClass = window.location.hash.substring(1);
                        const highlightBox = parentSection.querySelector('.' + highlightClass);
                        if (highlightBox) {
                            highlightBox.style.display = 'block';
                        }
                    }
                }
            } catch (e) {
                console.error("Could not process hash:", window.location.hash, e);
            }
        }
    }

    function clearHighlights(event) {
        event.preventDefault();
        history.pushState("", document.title, window.location.pathname + window.location.search);
        showHighlight();
    }

    window.addEventListener('hashchange', showHighlight);
    window.addEventListener('DOMContentLoaded', showHighlight);
    
    document.querySelectorAll('.clear-link').forEach(link => {
        link.addEventListener('click', clearHighlights);
    });
    </script>
</body>
</html>
"""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"\n\033[1m\033[92mSuccessfully created the final, working map file:\033[0m {output_path}")
    except Exception as e:
        print(f"\n[ERROR] An error occurred while writing the final HTML file: {e}")

def main():
    """Main function to process all files and generate the final output."""
    html_files = sorted(list(INPUT_DIR.glob('*.html')))
    if not html_files:
        print(f"No HTML files found in directory: {INPUT_DIR}")
        return

    print(f"Found {len(html_files)} HTML files. Processing all nahiyas...\n")
    
    # --- MODIFICATION: Fetch all DB data once for efficient diagnostics ---
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Fetch all relevant columns needed for matching logic
        cursor.execute("SELECT nahiyah, geojson_names, alt_names FROM locations")
        all_db_data = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(f"  [FATAL ERROR] Could not read the entire database for diagnostics: {e}")
        return
    # --- END MODIFICATION ---

    all_nahiyas_data = []

    for file_path in html_files:
        if "All_Nahiyas_Clickable_Maps" in file_path.name:
            continue
            
        nahiya_name = file_path.stem
        
        elements = extract_nahiya_elements(file_path)
        # This function fetches only the data for the current nahiya for the actual matching process
        db_village_data = fetch_nahiya_data_from_db(DB_PATH, nahiya_name)
        
        matches = []
        unmatched_html_names = [] # This remains a simple list for the matching logic
        if elements['villages'] and db_village_data:
            for village in elements['villages']:
                html_name = village['text']
                found_match = False
                for geojson_name, alt_names in db_village_data:
                    alt_names_list = [name.strip().lower() for name in alt_names.split(',')] if alt_names else []
                    if (html_name.lower() == geojson_name.lower()) or (html_name.lower() in alt_names_list):
                        matches.append({'html_name': html_name, 'geojson_name': geojson_name, 'href': village['href']})
                        found_match = True
                        break # Original logic is preserved: stop after the first match
                if not found_match:
                    unmatched_html_names.append(html_name)

        scoped_css = scope_css(elements['css_text'], nahiya_name)
        
        # We store raw elements and unmatched names to use in the new, separate diagnostic report
        all_nahiyas_data.append({
            "nahiya_name": nahiya_name,
            "matches": matches,
            "unmatched": unmatched_html_names, 
            "map_container_html": elements['map_container_html'],
            "scoped_css": scoped_css,
            "html_villages_for_report": elements['villages'], # Store for diagnostics
            "db_villages_for_report": db_village_data # Store for diagnostics
        })

    # --- NEW: Enhanced, more detailed Match Report ---
    print("--- Match Report & Diagnostics For All Nahiyas ---")
    for data in sorted(all_nahiyas_data, key=lambda x: x['nahiya_name']):
        print(f"\n--- {data['nahiya_name']} ---")
        if data['matches']:
            print("[SUCCESSFUL MATCHES]")
            for match in data['matches']:
                print(f"  - HTML Name: '{match['html_name']}'  =>  DB GeoJSON Name: '{match['geojson_name']}'")
        else:
            print("No successful matches were found for this nahiya.")

        if data['unmatched']:
            print("\n[ANALYSIS OF UNMATCHED HTML NAMES]")
            for name in data['unmatched']:
                # Diagnostic check: Search for this name across the entire database
                locations_found = set()
                name_lower = name.lower()
                for db_nahiyah, db_geojson_name, db_alt_names in all_db_data:
                    db_alt_names_list = [n.strip().lower() for n in db_alt_names.split(',')] if db_alt_names else []
                    if (name_lower == db_geojson_name.lower()) or (name_lower in db_alt_names_list):
                        locations_found.add(db_nahiyah)
                
                if locations_found:
                    print(f"  - '{name}': FOUND in DB, but under different nahiya(s): {', '.join(sorted(list(locations_found)))}")
                else:
                    print(f"  - '{name}': NOT FOUND anywhere in the database.")
        
        # Diagnostic check for potential duplicate matches for ANY name in the HTML
        print("\n[ANALYSIS OF POTENTIAL DUPLICATE MATCHES IN DB]")
        any_duplicates_found = False
        for village in data['html_villages_for_report']:
            html_name = village['text']
            matches_found = []
            for geojson_name, alt_names in data['db_villages_for_report']:
                alt_names_list = [name.strip().lower() for name in alt_names.split(',')] if alt_names else []
                if (html_name.lower() == geojson_name.lower()) or (html_name.lower() in alt_names_list):
                    matches_found.append(geojson_name)
            
            if len(matches_found) > 1:
                print(f"  - HTML name '{html_name}' has {len(matches_found)} potential matches in this nahiya's DB data: {', '.join(matches_found)}")
                any_duplicates_found = True
        
        if not any_duplicates_found:
            print("  - No names from this HTML file have multiple matches in the corresponding nahiya data.")

    print("\n---------------------------------------------------\n")

    if not any(data['matches'] for data in all_nahiyas_data):
        print("No matches found across all files. No file will be generated.")
        return

    user_input = input(f"Proceed with generating the single combined HTML file? (y/n): ").lower()
    
    if user_input == 'y':
        output_filename = "All_Nahiyas_Clickable_Maps.html"
        output_path = OUTPUT_DIR / output_filename
        generate_final_page(output_path, all_nahiyas_data)
    else:
        print("Operation cancelled by user.")

if __name__ == "__main__":
    main()
