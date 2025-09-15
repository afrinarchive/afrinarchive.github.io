import os
import json
import shutil
from bs4 import BeautifulSoup # <--- THIS LINE WAS MISSING

def create_split_graph_data(directory):
    """
    Scans HTML files and creates a directory of individual JSON files,
    one for each node, for progressive loading.
    """
    # --- Step 1: Discover all nodes and their direct connections ---
    nodes_data = {} # Will store data for each node: { "node_label": { "type": "file", "edges": [...] } }
    file_node_labels = set()

    if not os.path.isdir(directory):
        print(f"Error: Directory not found at {directory}")
        return

    print(f"Scanning directory: {os.path.abspath(directory)}")

    # First, identify all file nodes
    for filename in os.listdir(directory):
        if filename.endswith(".html") and not filename.startswith("00"):
            file_label = os.path.splitext(filename)[0]
            file_node_labels.add(file_label)

    # Now, build the full connection map in memory
    for filename in os.listdir(directory):
        if filename.endswith(".html") and not filename.startswith("00"):
            source_label = os.path.splitext(filename)[0]
            
            # Ensure the source file node exists in our map
            if source_label not in nodes_data:
                nodes_data[source_label] = {"type": "file", "edges": []}

            filepath = os.path.join(directory, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    soup = BeautifulSoup(f.read(), 'html.parser')
                    for span_tag in soup.find_all('span', class_='internal-link'):
                        target_label = span_tag.get_text(strip=True)
                        
                        # Add the edge to the source node
                        nodes_data[source_label]["edges"].append(target_label)

                        # Ensure the target concept node also exists in our map
                        if target_label not in nodes_data:
                            # Determine if the target is a file or a concept
                            node_type = "file" if target_label in file_node_labels else "concept"
                            nodes_data[target_label] = {"type": node_type, "edges": []}
            except Exception as e:
                print(f"Warning: Could not process {filename}: {e}")

    print(f"Discovered {len(nodes_data)} total unique nodes.")
    
    # --- Step 2: Create the output directory and write individual files ---
    output_dir = "graph_data_split"
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir) # Clean out old data
    os.makedirs(output_dir)

    print(f"Creating individual JSON files in '{output_dir}' directory...")

    for label, data in nodes_data.items():
        # Sanitize the label to create a valid filename
        # This replaces invalid characters with an underscore
        safe_filename = "".join(c if c.isalnum() else '_' for c in label) + ".json"
        filepath = os.path.join(output_dir, safe_filename)
        
        # The JSON for each file contains its own info and its direct connections
        file_content = {
            "id": label,
            "type": data["type"],
            "connections": list(set(data["edges"])) # Use set to store unique connections
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(file_content, f, ensure_ascii=False)

    print(f"\nSuccessfully created {len(nodes_data)} node files in '{output_dir}'.")
    print("Move this entire folder into your 'landing' directory.")

# --- Run the script ---
if __name__ == "__main__":
    html_files_directory = r"C:\Users\Zachar\Desktop\Afrin_Archive\village_sites"
    create_split_graph_data(html_files_directory)
