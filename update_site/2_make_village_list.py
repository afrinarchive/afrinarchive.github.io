import os
from bs4 import BeautifulSoup

def extract_village_data(folder_path):
    """Extract village name, nahiya, and filename from HTML files"""
    villages = []
    
    # Get all HTML files that don't start with "0"
    for filename in os.listdir(folder_path):
        if filename.endswith('.html') and not filename.startswith('0'):
            file_path = os.path.join(folder_path, filename)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Extract village name from title
                    title_tag = soup.find('title')
                    if title_tag and 'Archive |' in title_tag.text:
                        village_name = title_tag.text.replace('Archive |', '').strip()
                    else:
                        village_name = "Unknown"
                    
                    # Extract nahiya
                    nahiya = "Unknown"
                    # Find the h3 tag containing "Nahiya (Subdistrict)"
                    nahiya_headers = soup.find_all('h3', string=lambda text: text and 'Nahiya' in text and 'Subdistrict' in text)
                    if nahiya_headers:
                        # Get the next p tag after the h3
                        nahiya_header = nahiya_headers[0]
                        nahiya_p = nahiya_header.find_next_sibling('p')
                        if nahiya_p:
                            nahiya = nahiya_p.text.strip()
                    
                    villages.append({
                        'village_name': village_name,
                        'nahiya': nahiya,
                        'filename': filename
                    })
                    
            except Exception as e:
                print(f"Error processing {filename}: {e}")
    
    # Sort by nahiya alphabetically
    villages.sort(key=lambda x: x['nahiya'])
    
    return villages

def create_markdown_file(villages, output_path):
    """Create markdown file with village data"""
    with open(output_path, 'w', encoding='utf-8') as file:
        for village in villages:
            file.write(f"{village['village_name']}\t{village['nahiya']}\t{village['filename']}\n")

def main():
    folder_path = r"C:\Users\Zachar\Desktop\Afrin_Archive\village_sites"
    output_file = os.path.join(folder_path, "00_names_nahiyas.md")
    
    villages = extract_village_data(folder_path)
    create_markdown_file(villages, output_file)
    
    print(f"Created {output_file} with {len(villages)} villages")

if __name__ == "__main__":
    main()