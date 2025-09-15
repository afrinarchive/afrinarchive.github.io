import os
import json
from bs4 import BeautifulSoup

def create_full_graph_data(directory):
    """
    Scans HTML files to create a complete graph. Every unique internal link
    becomes a node, and files are a special type of node.
    """
    all_node_labels = set()
    file_node_labels = set()
    edges = []

    if not os.path.isdir(directory):
        print(f"Error: Directory not found at {directory}")
        return

    print(f"Scanning directory: {os.path.abspath(directory)}")

    # --- Pass 1: Discover all possible nodes (both files and concepts) ---
    for filename in os.listdir(directory):
        if filename.endswith(".html") and not filename.startswith("00"):
            # Add the file itself as a node
            file_label = os.path.splitext(filename)[0]
            all_node_labels.add(file_label)
            file_node_labels.add(file_label)
            
            filepath = os.path.join(directory, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    soup = BeautifulSoup(f.read(), 'html.parser')
                    # Find all span tags and add their text as nodes
                    for span_tag in soup.find_all('span', class_='internal-link'):
                        concept_label = span_tag.get_text(strip=True)
                        all_node_labels.add(concept_label)
            except Exception as e:
                print(f"Warning: Could not process {filename}: {e}")

    print(f"Found {len(all_node_labels)} total unique nodes (files + concepts).")

    # --- Pass 2: Create the edges ---
    for filename in os.listdir(directory):
        if filename.endswith(".html") and not filename.startswith("00"):
            source_label = os.path.splitext(filename)[0]
            filepath = os.path.join(directory, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    soup = BeautifulSoup(f.read(), 'html.parser')
                    # Find links and create an edge from the file to the concept
                    for span_tag in soup.find_all('span', class_='internal-link'):
                        target_label = span_tag.get_text(strip=True)
                        edge = {"from": source_label, "to": target_label}
                        if edge not in edges:
                            edges.append(edge)
            except Exception as e:
                # This error was already reported in pass 1
                pass

    print(f"Found {len(edges)} unique connections.")

    # --- Final Step: Format the node list for vis.js ---
    # We add a 'type' to distinguish files from concepts for styling
    final_nodes = []
    for label in sorted(list(all_node_labels)):
        node_type = "file" if label in file_node_labels else "concept"
        final_nodes.append({
            "id": label,
            "label": label,
            "type": node_type
        })

    graph_data = {"nodes": final_nodes, "edges": edges}

    output_filename = "graph-data.json"
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(graph_data, f, indent=2, ensure_ascii=False)

    print(f"\nSuccessfully created '{output_filename}'!")
    print("This file now contains ALL nodes and connections.")

# --- Run the script ---
if __name__ == "__main__":
    html_files_directory = r"C:\Users\Zachar\Desktop\Afrin_Archive\village_sites"
    create_full_graph_data(html_files_directory)
