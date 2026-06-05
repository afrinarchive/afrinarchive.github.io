# Afrin Archive Website Bug Tracker

This document records resolved and unresolved bugs found in the Afrin Archive repository for future reference.

---

## 1. Hardcoded Village Page Coordinate Mismatches (Unresolved)

### Issue Description
Exactly four village pages in the `village_sites/` directory have incorrect coordinates hardcoded in their HTML files. This causes their Leaflet maps and coordinate displays to show the wrong location (mapping to another nearby or similarly-named location).

### Root Cause Analysis
The original automation script that generated these HTML files likely matched names in the master `afrin_locations.json` database using substring matching (e.g., checking if the village name is a substring of a location name in the database) instead of executing an exact name match. Consequently, when searching for short names, the coordinates of longer names containing the query were mistakenly retrieved and written into the HTML files.

* `Xelîl` matched `Mile Xelîla`
* `Xidiriya` matched `Qestelê Xidiriya`
* `Şera` matched `Xirabî Şera`
* `Ĥesen` matched `Ĥec Ĥesena`

### Coordinate Mismatch Registry

| Village Page | Subdiştrict (Nahiya) | Current (Wrong) Coordinates | Displays as (Incorrect) | Expected (Correct) Coordinates |
| :--- | :--- | :--- | :--- | :--- |
| [Xelîl.html](file:///c:/Users/Zachar/Documents/Hatra/Afrin_Archive/village_sites/Xel%C3%AEl.html) | Şiyê | `36.341822, 36.639073` | **Mile Xelîla** (Cindires) | `36.579195, 36.643374` |
| [Xidiriya.html](file:///c:/Users/Zachar/Documents/Hatra/Afrin_Archive/village_sites/Xidiriya.html) | Bilbilê | `36.753726, 36.782729` | **Qestelê Xidiriya** (Bilbilê) | `36.746547, 36.794961` |
| [Şera.html](file:///c:/Users/Zachar/Documents/Hatra/Afrin_Archive/village_sites/%C5%9Eera.html) | Şera | `36.614579, 36.937103` | **Xirabî Şera** (Şera) | `36.624278, 36.93676` |
| [Ĥesen.html](file:///c:/Users/Zachar/Documents/Hatra/Afrin_Archive/village_sites/%C4%A6esen.html) | Reco | `36.484665, 36.652524` | **Ĥec Ĥesena** (Cindires) | `36.630199, 36.631634` |

---

### Verification and Actions Needed
* Modify the generator scripts to perform exact string matches when mapping names from `afrin_locations.json` to village pages.
* Correct the hardcoded coordinates in the `Coordinates: ...` paragraph and the `const villageLat` / `const villageLng` variables in each of the four affected HTML files above.

---

## 2. Integrity Sweeps & Verification (Clean)

During the second sweep, the following integrity validations were performed:

* **Image Reference Integrity**: Scanned all `village_sites/*.html` files for references to photos in `village_photos/`. All linked image files exist on disk (no broken image references).
* **Term Graph Index Integrity**: Verified all village names referenced in `js/internal-link-graph-data.js` exist as valid HTML pages under `village_sites/` (no 404 targets in navigation).
* **Internal Link Key Matching**: Verified all `.internal-link` elements on all village pages match entries in `INTERNAL_LINK_GRAPH_INDEX`. All links are fully functional (no missing keys, double-space whitespace variants are normalized on load).

