import os

def find_unique_files(folder1, folder2):
    """
    Compares two folders and finds files that are unique to each.

    Args:
        folder1 (str): The path to the first folder.
        folder2 (str): The path to the second folder.

    Returns:
        tuple: A tuple containing two lists:
               - A list of files only in folder1.
               - A list of files only in folder2.
    """
    # --- 1. Validate folder paths ---
    if not os.path.isdir(folder1):
        print(f"Error: Folder not found at '{folder1}'")
        return None, None
    if not os.path.isdir(folder2):
        print(f"Error: Folder not found at '{folder2}'")
        return None, None

    # --- 2. Get the list of files from each folder ---
    # os.listdir() returns a list of all files and directories in the specified path.
    # We use a set for efficient comparison later on.
    try:
        files1 = set(os.listdir(folder1))
        files2 = set(os.listdir(folder2))
    except OSError as e:
        print(f"Error reading files from a directory: {e}")
        return None, None


    # --- 3. Find the differences using set operations ---
    # The difference() method returns a new set containing items that are only in the first set.
    unique_to_folder1 = sorted(list(files1.difference(files2)))
    unique_to_folder2 = sorted(list(files2.difference(files1)))

    return unique_to_folder1, unique_to_folder2

def main():
    """
    Main function to run the folder comparison script.
    """
    print("--- Folder Comparison Script ---")
    
    # --- Folder paths are now hardcoded as requested ---
    # Using raw strings (r"...") for Windows paths is a good practice.
    folder_path1 = r"C:\Users\Zachar\Desktop\temp_afrin_archive\village_sites"
    folder_path2 = r"C:\Users\Zachar\Desktop\Afrin_Archive\village_sites"
    
    print(f"Comparing the following folders:")
    print(f"1: {folder_path1}")
    print(f"2: {folder_path2}")
    print("-" * 30)

    # --- Find and print the unique files ---
    unique1, unique2 = find_unique_files(folder_path1, folder_path2)

    if unique1 is not None and unique2 is not None:
        print(f"Comparing '{os.path.basename(folder_path1)}' and '{os.path.basename(folder_path2)}'...\n")

        if not unique1:
            print(f"No files are unique to '{os.path.basename(folder_path1)}'.\n")
        else:
            print(f"Found {len(unique1)} file(s) only in '{os.path.basename(folder_path1)}':")
            for filename in unique1:
                print(f"  - {filename}")
            print("-" * 30)


        if not unique2:
            print(f"No files are unique to '{os.path.basename(folder_path2)}'.\n")
        else:
            print(f"Found {len(unique2)} file(s) only in '{os.path.basename(folder_path2)}':")
            for filename in unique2:
                print(f"  - {filename}")
            print("-" * 30)

if __name__ == "__main__":
    main()
