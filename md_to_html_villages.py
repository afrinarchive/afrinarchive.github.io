import os
import re
from pathlib import Path

def markdown_to_html(text):
    """
    (Final, Corrected Version) Converts markdown to HTML, correctly handling
    paragraphs, lists (ordered and unordered), and mixed content, while
    forcing paragraph spacing and list numbering to override template styles.
    """
    if not text:
        return ""

    def process_inline_formatting(line):
        """Handles bold and internal links on a single line of text."""
        line = re.sub(r'\[\[(.*?)\]\]', r'<span class="internal-link">\1</span>', line)
        line = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', line)
        return line

    blocks = re.split(r'\n\s*\n', text.strip())
    html_output = []

    for block in blocks:
        lines = block.strip().split('\n')
        in_list_type = None
        
        for line in lines:
            stripped_line = line.strip()
            is_ul_item = stripped_line.startswith('- ')
            is_ol_item = re.match(r'^\d+\.\s', stripped_line)

            if not is_ul_item and not is_ol_item:
                if in_list_type:
                    html_output.append(f'</{in_list_type}>')
                    in_list_type = None
                formatted_line = process_inline_formatting(stripped_line)
                html_output.append(f'<p style="margin-bottom: 1em;">{formatted_line}</p>')
                continue

            if is_ul_item:
                if in_list_type == 'ol':
                    html_output.append('</ol>')
                    in_list_type = None
                if not in_list_type:
                    html_output.append('<ul>')
                    in_list_type = 'ul'
                item_content = process_inline_formatting(stripped_line[2:])
                html_output.append(f'<li>{item_content}</li>')
                continue

            if is_ol_item:
                if in_list_type == 'ul':
                    html_output.append('</ul>')
                    in_list_type = None
                if not in_list_type:
                    html_output.append('<ol style="list-style-type: decimal; margin-left: 2em;">')
                    in_list_type = 'ol'
                item_content = process_inline_formatting(re.sub(r'^\d+\.\s', '', stripped_line))
                html_output.append(f'<li>{item_content}</li>')
                continue

        if in_list_type:
            html_output.append(f'</{in_list_type}>')
            in_list_type = None

    return '\n'.join(html_output)


def parse_markdown_file(file_path):
    """Parse a markdown file and extract structured content"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    village_name = Path(file_path).stem
    
    yaml_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    aliases = []
    if yaml_match:
        yaml_content = yaml_match.group(1)
        aliases_match = re.search(r'aliases:\s*\[(.*?)\]', yaml_content)
        if aliases_match:
            aliases_str = aliases_match.group(1)
            aliases = [alias.strip().strip('"').strip("'") for alias in aliases_str.split(',')]
    
    nahiya_match = re.search(r'## Nahiya\s*\n\s*\[\[(.*?)\]\]', content)
    nahiya = nahiya_match.group(1) if nahiya_match else ""
    
    coord_match = re.search(r'lat:\s*([\d.-]+)\s*\nlong:\s*([\d.-]+)', content)
    lat = coord_match.group(1) if coord_match else ""
    lng = coord_match.group(2) if coord_match else ""
    
    photos = []
    photos_section = re.search(r'## Photos\s*\n(.*?)(?=\n##|\n---|\Z)', content, re.DOTALL)
    if photos_section:
        photo_matches = re.findall(r'!\[\[(.*?)\]\]', photos_section.group(1))
        photos = photo_matches
    
    sections = {}
    section_pattern = r'## (.*?)\n(.*?)(?=\n##|\n---|\Z)'
    section_matches = re.findall(section_pattern, content, re.DOTALL)
    
    for title, section_content in section_matches:
        if title in ['Alternative names/spellings', 'Nahiya', 'Map and Location', 'Photos']:
            continue
            
        content_to_check = section_content
        boilerplate_patterns = [
            r'### .*', r'\*\*Source:\*\*', r'---',
        ]
        for pattern in boilerplate_patterns:
            content_to_check = re.sub(pattern, '', content_to_check)
            
        if len(content_to_check.strip()) < 10:
            continue
            
        sections[title] = section_content.strip()
    
    return {
        'village_name': village_name,
        'aliases': aliases,
        'nahiya': nahiya,
        'lat': lat,
        'lng': lng,
        'photos': photos,
        'sections': sections
    }

def generate_html(village_data, template_path, output_path):
    """Generate HTML file from village data and template"""
    with open(template_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # FIX 1: Make all collapsible sections open by default.
    # This replaces any <details> tag that is closed with an open one.
    html_content = html_content.replace('<details class="group">', '<details class="group" open>')

    html_content = html_content.replace('Abû Ke\'bê Şerqî', village_data['village_name'])
    html_content = html_content.replace('Jindires', village_data['nahiya'])
    
    aliases_text = ', '.join(village_data['aliases']) if village_data['aliases'] else village_data['village_name']
    html_content = html_content.replace('Abu Ka\'b Eastern, Abû ke\'bê Şerqî, Ebû Ke\'ibê, أبو كعب شرقي', aliases_text)
    
    if village_data['lat'] and village_data['lng']:
        html_content = html_content.replace('36.387605', village_data['lat'])
        html_content = html_content.replace('36.752234', village_data['lng'])
        coord_text = f"Coordinates: {village_data['lat']}, {village_data['lng']}"
        html_content = html_content.replace('Coordinates: 36.387605, 36.752234', coord_text)
    
    if village_data['photos']:
        photos_html = '<div class="grid grid-cols-1 md:grid-cols-2 gap-4">'
        for photo in village_data['photos']:
            photo_name = photo.replace(' ', '+')
            photos_html += f'''<img src="../village_photos/{photo}" alt="Photo of {photo.replace('.jpg', '').replace('.png', '')}" class="lightbox-trigger rounded-lg w-full h-auto object-cover border themed-border cursor-pointer" onerror="this.onerror=null;this.src='https://placehold.co/600x400/e2e8f0/4a5568?text={photo_name}';">'''
        photos_html += '</div>'
        old_photos = re.search(r'<div class="grid grid-cols-1 md:grid-cols-2 gap-4">.*?</div>', html_content, re.DOTALL)
        if old_photos:
            html_content = html_content.replace(old_photos.group(0), photos_html)
    else:
        photos_card_pattern = r'<div class="card p-6 rounded-xl">\s*<h2 class="text-2xl font-semibold border-b themed-border pb-3 mb-4">Photos</h2>.*?</div>\s*</div>'
        html_content = re.sub(photos_card_pattern, '', html_content, flags=re.DOTALL)
    
    summaries_html = ''
    summary_section_titles = ['I. Summary from TirejAfrin Site', 'II. Summary from Ax û Walat Transcript', 'III. Summary from Halil Sino Transcript', 'IV. Summary from Afrin Flo Transcript']
    found_summary_sections = {title: village_data['sections'][key] for title in summary_section_titles for key in village_data['sections'] if title.split('.')[1].strip() in key}
    
    if found_summary_sections:
        for title in summary_section_titles:
            if title in found_summary_sections:
                content_html = markdown_to_html(found_summary_sections[title])
                # FIX 1: Always add the 'open' attribute to make sections expanded by default.
                open_attr = 'open'
                summaries_html += f'''<details class="group" {open_attr}><summary class="flex justify-between items-center font-semibold p-3 cursor-pointer text-lg"><span>{title}</span><svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 transform transition-transform group-open:rotate-180 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg></summary><div class="p-4 prose max-w-none">{content_html}</div></details>'''
                if title != summary_section_titles[-1]: summaries_html += '<hr class="themed-border">'
        old_summaries = re.search(r'<div class="space-y-4">\s*<details class="group" open>.*?</div>\s*</div>', html_content, re.DOTALL)
        if old_summaries:
            html_content = html_content.replace(old_summaries.group(0), f'<div class="space-y-4">{summaries_html}</div>')
    else:
        summaries_card_pattern = r'<div class="card p-6 rounded-xl">\s*<h2 class="text-2xl font-semibold border-b themed-border pb-3 mb-4">Summaries</h2>.*?</div>\s*</div>\s*</div>'
        html_content = re.sub(summaries_card_pattern, '', html_content, flags=re.DOTALL)
    
    # FIX 2: Reworked the logic to correctly handle links where one label has multiple URLs.
    links_section_key = next((k for k in village_data['sections'] if 'V. Links' in k), None)
    if links_section_key:
        links_content = village_data['sections'][links_section_key]
        links_html = ''
        link_blocks = re.split(r'\n\s*\n', links_content.strip())
        
        for block in link_blocks:
            lines = [line.strip() for line in block.strip().split('\n') if line.strip()]
            if not lines:
                continue

            # The first line is the label, the rest are URLs
            label = lines[0]
            urls = lines[1:]

            # If there are no URLs, the label itself might be a link
            if not urls:
                if "http" in label:
                    links_html += f'<li><a href="{label}" target="_blank" rel="noopener noreferrer" class="external-link hover:underline break-all">{label}</a></li>'
                else:
                    links_html += f'<li>{label}</li>'
                continue
            
            # Start the list item with the label
            item_html = f'<li>{label.strip().rstrip(":")}'
            
            # Create an anchor tag for each subsequent URL line
            url_tags = []
            for url in urls:
                if "http" in url:
                    url_tags.append(f'<a href="{url}" target="_blank" rel="noopener noreferrer" class="external-link hover:underline break-all">{url}</a>')
            
            # Join the generated <a> tags with a line break
            if url_tags:
                item_html += '<br>' + '<br>'.join(url_tags)
            
            item_html += '</li>'
            links_html += item_html

        if links_html:
            placeholder_ul_pattern = r'<ul class="list-disc list-inside space-y-2 p-4">.*?</ul>'
            html_content = re.sub(placeholder_ul_pattern, f'<ul class="list-disc list-inside space-y-2 p-4">{links_html}</ul>', html_content, flags=re.DOTALL)
    else:
        links_pattern = r'<div class="card p-6 rounded-xl">\s*<h2 class="text-2xl font-semibold border-b themed-border pb-3 mb-4">V\. Links</h2>.*?</div>\s*</div>'
        html_content = re.sub(links_pattern, '', html_content, flags=re.DOTALL)

    # --- DEBUGGING AND FIX FOR HIDING EMPTY CARDS ---
    print("\n--- Analyzing Cards for Hiding ---")
    
    # Additional Info Card (VI-X)
    info_section_titles = ['VI. History', 'VII. Historic Families/People', 'VIII. Cultural Aspects', 'IX. Dengbêj/Çirok', 'X. Connections with other Villages']
    # FIX: Correctly check if any of the keys exist in the parsed sections
    found_info_keys = [key for key in village_data['sections'] if any(title.split('.')[1].strip() in key for title in info_section_titles)]
    has_additional_info = bool(found_info_keys)
    print(f"  [DEBUG] Additional Info Card (VI-X):")
    print(f"    - Keys Found: {found_info_keys}")
    print(f"    - Decision: {'KEEPING' if has_additional_info else 'HIDING'}")
    if not has_additional_info:
        additional_info_pattern = r'<div class="card p-6 rounded-xl">\s*<h2 class="text-2xl font-semibold border-b themed-border pb-3 mb-4">Additional Information</h2>.*?</div>\s*</div>'
        html_content = re.sub(additional_info_pattern, '', html_content, flags=re.DOTALL)
    
    # Additional Summaries Card (XI-XVII)
    transcript_section_titles = ['XI. Summary from TirejAfrin Site (Arabic)', 'XII. Ax û Walat Transcript (English)', 'XIII. Ax û Walat Transcript (Kumancî)', 'XIV. Halil Sino Transcript (English)', 'XV. Halil Sino Transcript (Kumancî)', 'XVI. Afrin Flo Transcript (Kumancî)', 'XVII. Afrin Flo Transcript (Kumancî)']
    found_transcript_keys = [key for key in village_data['sections'] if any(title.split('.')[1].strip() in key for title in transcript_section_titles)]
    has_additional_summaries = bool(found_transcript_keys)
    print(f"  [DEBUG] Additional Summaries/Transcripts Card (XI-XVII):")
    print(f"    - Keys Found: {found_transcript_keys}")
    print(f"    - Decision: {'KEEPING' if has_additional_summaries else 'HIDING'}")
    if not has_additional_summaries:
        additional_summaries_pattern = r'<div class="card p-6 rounded-xl">\s*<h2 class="text-2xl font-semibold border-b themed-border pb-3 mb-4">Additional Summaries and Transcripts</h2>.*?</div>\s*</div>'
        html_content = re.sub(additional_summaries_pattern, '', html_content, flags=re.DOTALL)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

def main():
    md_folder = r"C:\Users\Zachar\Desktop\local_afrin_project_vault\local_afrin_project\final_md_files"
    template_file = r"C:\Users\Zachar\Desktop\Afrin_Archive\village_sites\00_sample.html"
    output_folder = r"C:\Users\Zachar\Desktop\Afrin_Archive\village_sites"
    
    os.makedirs(output_folder, exist_ok=True)
    
    md_files = [f for f in Path(md_folder).glob("*.md") if not f.name.startswith('0')]
    
    if not md_files:
        print("No markdown files found to process.")
        return
    
    first_file = md_files[0]
    print(f"Processing first file: {first_file.name}...")
    
    try:
        village_data = parse_markdown_file(first_file)
        output_filename = first_file.stem + ".html"
        output_path = Path(output_folder) / output_filename
        generate_html(village_data, template_file, output_path)
        
        print(f"\nGenerated {output_filename}")
        print(f"Check the file at: {output_path}")
        
    except Exception as e:
        print(f"Error processing {first_file.name}: {e}")
        return
    
    response = input(f"\nFirst file created successfully. Continue with remaining {len(md_files)-1} files? (y/n): ")
    
    if response.lower() != 'y':
        print("Stopped after first file.")
        return
    
    print(f"\nProcessing remaining {len(md_files)-1} files...")
    
    for file_path in md_files[1:]:
        print(f"Processing {file_path.name}...")
        
        try:
            village_data = parse_markdown_file(file_path)
            output_filename = file_path.stem + ".html"
            output_path = Path(output_folder) / output_filename
            generate_html(village_data, template_file, output_path)
            
            print(f"Generated {output_filename}")
            
        except Exception as e:
            print(f"Error processing {file_path.name}: {e}")
    
    print("Done!")

if __name__ == "__main__":
    main()
