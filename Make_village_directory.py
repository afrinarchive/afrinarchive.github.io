import os
import re
from collections import defaultdict

def parse_markdown_file(md_file_path):
    """Parse the markdown file and return village data organized by nahiya."""
    villages_by_nahiya = defaultdict(list)
    
    with open(md_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split('\t')
            if len(parts) >= 2:
                village_name = parts[0].strip()
                
                if len(parts) == 3:
                    # Format: Village Name \t Nahiya \t HTML file
                    nahiya = parts[1].strip()
                    html_file = parts[2].strip()
                else:
                    # Format: Village Name \t HTML file (no nahiya specified)
                    nahiya = ""
                    html_file = parts[1].strip()
                
                # Handle blank nahiya and unknown
                if not nahiya:
                    nahiya = "Uncategorized"
                elif nahiya.lower() == "unknown":
                    # Skip unknown entries entirely
                    continue
                
                villages_by_nahiya[nahiya].append({
                    'name': village_name,
                    'html_file': html_file
                })
    
    return villages_by_nahiya

def generate_nahiya_sections(villages_by_nahiya):
    """Generate HTML sections for each nahiya."""
    sections_html = ""
    nav_buttons_html = ""
    
    # Sort nahiyas alphabetically, but put "Uncategorized" last
    sorted_nahiyas = sorted(villages_by_nahiya.keys())
    if "Uncategorized" in sorted_nahiyas:
        sorted_nahiyas.remove("Uncategorized")
        sorted_nahiyas.append("Uncategorized")
    
    for nahiya in sorted_nahiyas:
        villages = villages_by_nahiya[nahiya]
        nahiya_id = nahiya.lower().replace(" ", "").replace("'", "").replace("-", "")
        
        # Generate navigation button
        nav_buttons_html += f'                    <button class="nav-btn" onclick="scrollToSection(\'{nahiya_id}\')">{nahiya}</button>\n'
        
        # Generate nahiya section
        sections_html += f'''            <div class="nahiya-section" id="{nahiya_id}">
                <h3 class="nahiya-title">{nahiya}</h3>
                <div class="villages-grid">
'''
        
        # Sort villages alphabetically within each nahiya
        villages.sort(key=lambda x: x['name'])
        
        for village in villages:
            sections_html += f'                    <a href="{village["html_file"]}" target="_blank" class="village-link">{village["name"]}</a>\n'
        
        sections_html += '''                </div>
            </div>

'''
    
    return sections_html.rstrip(), nav_buttons_html.rstrip()

def update_html_file(html_file_path, villages_by_nahiya):
    """Update the HTML file with new village data."""
    with open(html_file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Calculate statistics - exclude "Uncategorized" from nahiya count
    total_villages = sum(len(villages) for villages in villages_by_nahiya.values())
    total_nahiyas = len([k for k in villages_by_nahiya.keys() if k != "Uncategorized"])
    
    # Generate new sections
    nahiya_sections, nav_buttons = generate_nahiya_sections(villages_by_nahiya)
    
    # Update statistics
    stats_pattern = r'<div class="stats-bar">.*?</div>'
    new_stats = f'''<div class="stats-bar">
                <div class="stat-item">
                    <div class="stat-number">{total_villages}</div>
                    <div class="stat-label">Villages</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">{total_nahiyas}</div>
                    <div class="stat-label">Nahiyas</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">Archive Status</div>
                    <div class="stat-label">In Research and Development Stage</div>
                </div>
            </div>'''
    
    html_content = re.sub(stats_pattern, new_stats, html_content, flags=re.DOTALL)
    
    # Update navigation buttons
    nav_pattern = r'<div class="nav-buttons">\s*.*?</div>'
    new_nav = f'''<div class="nav-buttons">
{nav_buttons}
                </div>'''
    
    html_content = re.sub(nav_pattern, new_nav, html_content, flags=re.DOTALL)
    
    # Find the exact start and end points for replacement
    # Find where the first nahiya section starts
    start_marker = '<div class="nahiya-section"'
    start_pos = html_content.find(start_marker)
    
    # Find where the container ends (before the closing </div></div><script>)
    end_marker = '</div>\n        </div>\n\n    <script>'
    end_pos = html_content.find(end_marker)
    
    if start_pos != -1 and end_pos != -1:
        # Replace everything between start and end
        before = html_content[:start_pos]
        after = html_content[end_pos:]
        html_content = before + nahiya_sections + '\n        ' + after
    else:
        print("Warning: Could not find proper start/end markers for replacement")
    
    # Write updated HTML back to file
    with open(html_file_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

def main():
    # File paths
    base_path = r"C:\Users\Zachar\Desktop\temp_afrin_archive\village_sites"
    md_file_path = os.path.join(base_path, "00_names_nahiyas.md")
    html_file_path = os.path.join(base_path, "00_village_names.html")
    
    # Check if files exist
    if not os.path.exists(md_file_path):
        print(f"Error: Markdown file not found at {md_file_path}")
        return
    
    if not os.path.exists(html_file_path):
        print(f"Error: HTML file not found at {html_file_path}")
        return
    
    # Parse markdown file
    print("Parsing markdown file...")
    villages_by_nahiya = parse_markdown_file(md_file_path)
    
    # Print statistics
    total_villages = sum(len(villages) for villages in villages_by_nahiya.values())
    total_nahiyas = len([k for k in villages_by_nahiya.keys() if k != "Uncategorized"])
    
    print(f"Found {total_villages} villages across {len(villages_by_nahiya)} sections ({total_nahiyas} main nahiyas + uncategorized):")
    for nahiya, villages in sorted(villages_by_nahiya.items()):
        print(f"  {nahiya}: {len(villages)} villages")
    
    # Update HTML file
    print("\nUpdating HTML file...")
    update_html_file(html_file_path, villages_by_nahiya)
    
    print(f"Successfully updated {html_file_path}")
    print(f"Updated statistics: {total_villages} villages, {total_nahiyas} nahiyas (uncategorized not counted)")
    print("Note: 'Unknown' entries were excluded, blank entries moved to 'Uncategorized'")

if __name__ == "__main__":
    main()