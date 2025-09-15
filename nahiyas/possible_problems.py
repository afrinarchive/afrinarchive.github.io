import os
from bs4 import BeautifulSoup
import locale

# --- CONFIGURATION ---
# Define the directory and filenames for the HTML files.
HTML_DIR_PATH = r"C:\Users\Zachar\Desktop\Afrin_Archive\nahiyas"
HTML_FILENAMES = [
    "Şiyê.html",
    "Bilbilê.html", # Corrected filename
    "Cindires.html",
    "Efrîn.html",
    "Mabeta.html",
    "Reco.html",
    "Şera.html",
]
# Create a list of full paths for the HTML files
HTML_FILE_PATHS = [os.path.join(HTML_DIR_PATH, f) for f in HTML_FILENAMES]


def extract_village_names(html_paths):
    """
    Parses multiple HTML files to extract village names from the specific
    anchor tags and returns a single, sorted list.

    Args:
        html_paths (list): A list of full paths to the HTML files.

    Returns:
        A list of unique, alphabetized village names.
    """
    all_village_names = set()  # Using a set prevents duplicate entries

    for path in html_paths:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f, 'html.parser')

            # Find all <a> tags with an href attribute that starts with '#'
            links = soup.find_all('a', href=lambda href: href and href.startswith('#'))

            for link in links:
                # Exclude the specific "Clear Highlights" link
                if link.get('id') == 'clear-link':
                    continue
                # This correctly gets the visible text, e.g., "Tirmûşa"
                name = link.get_text(strip=True)
                if name:
                    all_village_names.add(name)
        except FileNotFoundError:
            print(f"Warning: File not found at '{path}', skipping.")
        except Exception as e:
            print(f"An error occurred while processing file '{path}': {e}")

    # Set the locale to handle sorting of special characters correctly.
    # 'tr_TR.UTF-8' is a good choice for Turkish characters like 'Ş' and 'î'.
    try:
        locale.setlocale(locale.LC_ALL, 'tr_TR.UTF-8')
    except locale.Error:
        print("Warning: 'tr_TR.UTF-8' locale not supported. Using default system sort.")
        # Fallback to default sort if the locale is not available
        return sorted(list(all_village_names))

    return sorted(list(all_village_names), key=locale.strxfrm)


def main():
    """
    Main function to run the extraction process and print the results.
    """
    print("--- Extracting Village Names from All HTML Files ---")
    village_list = extract_village_names(HTML_FILE_PATHS)

    if village_list:
        print(f"\nFound {len(village_list)} unique village names. Alphabetical list:")
        for name in village_list:
            print(f"- {name}")
    else:
        print("\nNo village names could be extracted.")

    print("\n--- End of List ---")


if __name__ == "__main__":
    main()

