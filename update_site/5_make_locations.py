import json
import re
import os

# --- Configuration ---
# Define the input and output file paths.
# Using raw strings (r'...') is a good practice for Windows paths to avoid issues with backslashes.
INPUT_MD_FILE = r"H:\My Drive\Zachar\Files\for leaflet\000 Afrin Villages and Landmarks Master List 000.md"
OUTPUT_JSON_FILE = r"C:\Users\Zachar\Desktop\Afrin_Archive\village_sites\afrin_locations.json"

# A robust regular expression to capture the four required components from each line.
# Groups: 1=type, 2=lat, 3=lng, 4=name
MARKER_PATTERN = re.compile(r'-\s*\[(\w+),\s*\[([\d.-]+),\s*([\d.-]+)\],\s*"(.*?)"\s*\]')

# --- Main Script Logic ---

def create_json_from_markdown():
    """
    Reads a markdown file, parses a specific 'mapmarkers' section,
    and writes the data into a JSON file with a predefined structure.
    """
    print("--- Starting Location Parser ---")
    print(f"Reading from: {INPUT_MD_FILE}")

    locations_data = []
    parsing_enabled = False

    try:
        with open(INPUT_MD_FILE, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Enable parsing when the 'mapmarkers:' line is found
                if 'mapmarkers:' in line:
                    print("Found 'mapmarkers' section. Beginning data extraction.")
                    parsing_enabled = True
                    continue  # Move to the next line to start reading data

                if parsing_enabled:
                    # **FIX:** Check for definitive end-of-block markers first.
                    if line.startswith('---') or line.startswith('```'):
                        print("Reached end of 'mapmarkers' section.")
                        break
                    
                    # **FIX:** If the line is now empty, it's just whitespace. Skip it.
                    if not line:
                        continue

                    # Attempt to match the data pattern on the current line
                    match = MARKER_PATTERN.match(line)
                    if match:
                        # Extract data from the captured regex groups
                        loc_type, lat_str, lng_str, name = match.groups()

                        # Create the dictionary object with correct data types
                        location_dict = {
                            "type": loc_type,
                            "lat": float(lat_str),
                            "lng": float(lng_str),
                            "name": name
                        }
                        locations_data.append(location_dict)
                    else:
                        # This helps identify any malformed lines in the source file
                        print(f"Warning: Line {line_num} did not match format and was skipped: '{line}'")

    except FileNotFoundError:
        print(f"\n[ERROR] The input file was not found at the specified path.")
        print(f"Please ensure this path is correct: '{INPUT_MD_FILE}'")
        return
    except Exception as e:
        print(f"\n[ERROR] An unexpected error occurred while reading the file: {e}")
        return

    if not locations_data:
        print("\n[ERROR] No location data was parsed. Please check the input file format.")
        return

    print(f"Successfully parsed {len(locations_data)} location records.")

    # --- Write the data to the JSON file ---
    try:
        # Ensure the output directory exists before trying to write the file
        output_dir = os.path.dirname(OUTPUT_JSON_FILE)
        if output_dir:
             os.makedirs(output_dir, exist_ok=True)

        print(f"Writing JSON to: {OUTPUT_JSON_FILE}")

        with open(OUTPUT_JSON_FILE, 'w', encoding='utf-8') as f_out:
            # Dump the data into the file using the exact format required:
            # - indent=2: Creates the pretty-printed, indented structure.
            # - ensure_ascii=False: Preserves special characters (û, ê, ş, etc.) correctly.
            json.dump(locations_data, f_out, indent=2, ensure_ascii=False)

        print("\n--- Script finished successfully ---")
        print(f"The file '{os.path.basename(OUTPUT_JSON_FILE)}' has been created/updated.")

    except Exception as e:
        print(f"\n[ERROR] An error occurred while writing the JSON file: {e}")


# --- Run the script ---
if __name__ == "__main__":
    create_json_from_markdown()