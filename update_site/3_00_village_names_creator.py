import os
import json
from bs4 import BeautifulSoup

# --- 1. CONFIGURATION ---

# Define the input and output paths for the website files.
INPUT_FOLDER = r"C:\Users\Zachar\Desktop\Afrin_Archive\village_sites"
OUTPUT_FOLDER = r"C:\Users\Zachar\Desktop\Afrin_Archive\village_site_files"
OUTPUT_FILENAME = "00_village_names.html"

# --- 2. STATIC DATA FOR INTERACTIVE MAPS ---

# ==============================================================================
# CRITICAL NOTE: DO NOT EVER CHANGE THIS DATA STRUCTURE.
# This dictionary is the one and only source of truth for the interactive map
# sections on the website. It MUST be hardcoded to ensure the maps and their
# associated village links never change, regardless of what is in the
# village_sites folder.
# ==============================================================================
nahiyas_map_data = {
    "Bilbilê": {
        "hasMap": True,
        "image": "ÇK Map 14.png",
        "villages": [
            {"name": "Baliya", "id": "baliya"}, {"name": "Bêkê", "id": "beke"},
            {"name": "Bêlê", "id": "bele"}, {"name": "Berkaşê", "id": "berkase"},
            {"name": "Bêxçe", "id": "bexce"}, {"name": "Bîbaka", "id": "bibaka"},
            {"name": "Bilbilê", "id": "bilbile"}, {"name": "Ebûdanê", "id": "ebudane"},
            {"name": "Elcara", "id": "elcara"}, {"name": "Eli Kera", "id": "eli-kere"},
            {"name": "Eşûnê", "id": "esune"}, {"name": "Ĥesen Dêra", "id": "hesendera"},
            {"name": "Heyama", "id": "heyama"}, {"name": "Kerê", "id": "kere"},
            {"name": "Kotana", "id": "kotana"}, {"name": "Kurdo", "id": "kurdo"},
            {"name": "Kurzêl", "id": "kurzele"}, {"name": "Qaşa", "id": "qasa"},
            {"name": "Qestelê Miqdêd", "id": "qestele-miqded"}, {"name": "Qiri Golê", "id": "qirigole"},
            {"name": "Qizilbaşa", "id": "qizilbasa"}, {"name": "Qornê", "id": "qurne"},
            {"name": "Qorta", "id": "qurta"}, {"name": "Qota", "id": "qota"},
            {"name": "Şêrqiya", "id": "serqiya"}, {"name": "Şêxorz", "id": "sexorze"},
            {"name": "Şingêl", "id": "singele"}, {"name": "Topel Meĥmûd", "id": "topeli-mehmud"},
            {"name": "Uga", "id": "uga"}, {"name": "Upila", "id": "upila"},
            {"name": "Xelîlaka", "id": "xelilaka"}, {"name": "Xidiriya", "id": "qestele-xidiriya"},
            {"name": "Xidiriya", "id": "xidiriya"}, {"name": "Xilalka", "id": "xilalka"},
            {"name": "Ze'rê", "id": "zere"}, {"name": "Zivingê", "id": "zivinge"}
        ]
    },
    "Cindires": {
        "hasMap": True,
        "image": "ÇK Map 16.png",
        "villages": [
            {"name": "Abû Ke'bê Xerbî", "id": "ebukebe"}, {"name": "Aşkê Şerqî", "id": "aske-serqi"},
            {"name": "Aşkê Xerbî", "id": "aske-xerbi"}, {"name": "Axcelê", "id": "axcele"},
            {"name": "Baflor", "id": "baflor"}, {"name": "Bircikê", "id": "bircike"},
            {"name": "Celemê", "id": "celeme"}, {"name": "Cindirês", "id": "cindires"},
            {"name": "Çobana", "id": "cobana"}, {"name": "Çolaqa (North)", "id": "colaqa-1"},
            {"name": "Çolaqa (South)", "id": "colaqa-2"}, {"name": "Dêrbelûtê", "id": "derbelute"},
            {"name": "Dêwê Jêrin", "id": "dewe-jerin"}, {"name": "Dêwê Jorin", "id": "dewe-jorin"},
            {"name": "Feqîra", "id": "feqira"}, {"name": "Firêriyê", "id": "fireriye"},
            {"name": "Gewrika", "id": "gewrika"}, {"name": "Gorda", "id": "gorda"},
            {"name": "Ĥec Ĥesna", "id": "hechesna"}, {"name": "Ĥec Îskenderê", "id": "heciskendere"},
            {"name": "Ĥecîler", "id": "hecilere"}, {"name": "Hêkiçê", "id": "hekice"},
            {"name": "Ĥemamê", "id": "hemame"}, {"name": "Ĥemêlkê", "id": "hemelke"},
            {"name": "Kefersefrê", "id": "kefersefre"}, {"name": "Kora", "id": "kora"},
            {"name": "Medaya", "id": "medaya"}, {"name": "Mehmediyê Xerbî", "id": "mehmediye"},
            {"name": "Merwanê Jerin", "id": "merwane-jerin"}, {"name": "Merwanê Jorin", "id": "merwane-jorin"},
            {"name": "Miske Jerin", "id": "miske-jerin"}, {"name": "Miskê Jorin", "id": "miske-jorin"},
            {"name": "Qîlê", "id": "qile"}, {"name": "Qujûma", "id": "qujuma"},
            {"name": "Qurbê", "id": "qurbe"}, {"name": "Remadiyê", "id": "remadiye"},
            {"name": "Remedena", "id": "remedena"}, {"name": "Şêx Ebdirehmên", "id": "sex-ebdirehmen"},
            {"name": "Sifriyê", "id": "sifiye"}, {"name": "Sindiyankê", "id": "sindiyanke"},
            {"name": "Tetera", "id": "tetera"}, {"name": "Til Ĥemo", "id": "tilhemo"},
            {"name": "Tilsilorê", "id": "tilsilore"}, {"name": "Xerza", "id": "xerza"},
            {"name": "Yalanqozê", "id": "yalanqoze"}
        ]
    },
    "Efrîn": {
        "hasMap": True,
        "image": "ÇK Map 11.png",
        "villages": [
            {"name": "Aqîbê", "id": "aqibe"}, {"name": "Astêr", "id": "aster"},
            {"name": "Bablîtê", "id": "bablite"}, {"name": "Başemrê", "id": "basemre"},
            {"name": "Basilê", "id": "basile"}, {"name": "Basûfanê", "id": "basufane"},
            {"name": "Basûtê", "id": "basute"}, {"name": "Bênê", "id": "bene"},
            {"name": "Beradê", "id": "berade"}, {"name": "Bi'îyê", "id": "biiye"},
            {"name": "Birc Ĥêderê", "id": "birc-hedar"}, {"name": "Bircê", "id": "birce"},
            {"name": "Bircilqazê", "id": "bircilqase"}, {"name": "Cidêdê", "id": "cidede"},
            {"name": "Cilbirê", "id": "cilbire"}, {"name": "Coqê", "id": "coqe"},
            {"name": "Cûmkê", "id": "cumqe"}, {"name": "Efrîn", "id": "efrin"},
            {"name": "Fafirtîn", "id": "farfirtine"}, {"name": "Gazê", "id": "gaze"},
            {"name": "Gundê Mezin - above Ma'rata", "id": "gunde-mezin"}, {"name": "Gundê Mezin - Shirawa area", "id": "gundi-mezin"},
            {"name": "Inabkê", "id": "inabke"}, {"name": "Îska", "id": "iska"},
            {"name": "Keferbetrê", "id": "kefirbetre"}, {"name": "Keferdelê Jêrîn", "id": "keferdele-jerin"},
            {"name": "Keferdelê Jorin", "id": "keferdele-jorin"}, {"name": "Kefermizê", "id": "kefermize"},
            {"name": "Kefernebo", "id": "kefer-nabo"}, {"name": "Keferşîlê", "id": "kefersile"},
            {"name": "Keferzîtê", "id": "keferzite"}, {"name": "Kersanê", "id": "kersane"},
            {"name": "Kîbêşînê", "id": "kibesine"}, {"name": "Kifêrê", "id": "kifere"},
            {"name": "Kîmarê", "id": "kimare"}, {"name": "Kokebê", "id": "kokebe"},
            {"name": "Maratê", "id": "marate"}, {"name": "Mêremînê", "id": "meremine"},
            {"name": "Me'riskê", "id": "meriske"}, {"name": "Meyasê", "id": "meyase"},
            {"name": "Pitêtê", "id": "pitete"}, {"name": "Qîbar", "id": "qibare"},
            {"name": "Şadêrê", "id": "sadere"}, {"name": "Soĝanekê", "id": "soxaneke"},
            {"name": "Tilifê", "id": "tilfe"}, {"name": "Tirtewîlê", "id": "tirtewile"},
            {"name": "Turindê", "id": "turinde"}, {"name": "Xalta", "id": "xalta"},
            {"name": "Xelnêrê", "id": "xelnare"}, {"name": "Xezîwê", "id": "xeziwe"},
            {"name": "Xurêbkê", "id": "xurebke"}, {"name": "Zaretê", "id": "zarete"}
        ]
    },
    "Mabeta": {
        "hasMap": True,
        "image": "ÇK Map 13.png",
        "villages": [
            {"name": "Avraz", "id": "avraze"}, {"name": "Birîmce", "id": "birimce"},
            {"name": "Çomazna", "id": "comezna"}, {"name": "Dargirê", "id": "dagire"},
            {"name": "Dela", "id": "dela"}, {"name": "Emara", "id": "emara"},
            {"name": "Ên' Ĥecer", "id": "enhecere"}, {"name": "Ereba", "id": "erebsexo"},
            {"name": "Ereba", "id": "ereba"}, {"name": "Gemrûkê", "id": "gemruk"},
            {"name": "Gulîka", "id": "gobeke"}, {"name": "Ĥebo", "id": "hebo"},
            {"name": "Ĥec Qasma", "id": "hecqasma"}, {"name": "Kaxrê", "id": "kaxre"},
            {"name": "Kêl Îbo", "id": "kelibo"}, {"name": "Kokanê Jorin", "id": "kokane"},
            {"name": "Kurkê Jêrin", "id": "kurke-jerin"}, {"name": "Kurkê Jorin", "id": "kurke-jorin"},
            {"name": "Mabeta", "id": "mabete"}, {"name": "Me'serkê", "id": "merserke"},
            {"name": "Mîrka", "id": "mirka"}, {"name": "Mist'eşûra", "id": "mistesura"},
            {"name": "Omo", "id": "omo"}, {"name": "Qenterê", "id": "qentere"},
            {"name": "Qitraniyê", "id": "qitraniye"}, {"name": "Reca", "id": "reca"},
            {"name": "Rûta", "id": "ruta"}, {"name": "Sariya", "id": "sariya"},
            {"name": "Selo", "id": "selo"}, {"name": "Sêmalka", "id": "semalka"},
            {"name": "Şêtana", "id": "setana"}, {"name": "Sêwiya", "id": "sewiya"},
            {"name": "Şêx Kêlê", "id": "sexkele"}, {"name": "Şêxûtka", "id": "sexutka"},
            {"name": "Şîtka", "id": "sitka"}, {"name": "Şorbe", "id": "sorbe"},
            {"name": "Xaziyanê Jorin", "id": "xazyane-jorin"}, {"name": "Xazyanê Jêrin", "id": "xazyane-jerin"}
        ]
    },
    "Reco": {
        "hasMap": True,
        "image": "ÇK Map 15.png",
        "villages": [
            {"name": "Banîkê", "id": "banika"}, {"name": "Be'dîna", "id": "bedina"},
            {"name": "Berbenê", "id": "berbene"}, {"name": "Bilêlko", "id": "bilelko"},
            {"name": "Çe'inka", "id": "ceinke"}, {"name": "Cela", "id": "cela"},
            {"name": "Çençeliya", "id": "cenceliya"}, {"name": "Çêqilme", "id": "ceqilme"},
            {"name": "Çeqmaqê Çûçik", "id": "ceqmaqe-cucik"}, {"name": "Çeqmaqê Mezin", "id": "ceqmaqe-mezin"},
            {"name": "Çerxûta", "id": "cerxuta"}, {"name": "Çiyê", "id": "ciye"},
            {"name": "Dêwrîş", "id": "deewris"}, {"name": "Dodo", "id": "dodo"},
            {"name": "Dumilya", "id": "dumiliya"}, {"name": "Edema", "id": "edema"},
            {"name": "Elbîskê", "id": "elbiske"}, {"name": "Elendara", "id": "elendara"},
            {"name": "Eltaniya", "id": "heydar"}, {"name": "Etmana", "id": "etmana"},
            {"name": "Firfirkê Jêrin", "id": "firfirke-jerin"}, {"name": "Firfirkê Jorin", "id": "firfirke-jorin"},
            {"name": "Gewenda", "id": "gewenda"}, {"name": "Goliyê Jêrin", "id": "goliye-jerin"},
            {"name": "Goliyê Jorin", "id": "goliye-jorin"}, {"name": "Ĥec Xelîl", "id": "xecxelil"},
            {"name": "Ĥêcîka Jorin", "id": "hecika"}, {"name": "Ĥesen", "id": "hesen"},
            {"name": "Holîlê", "id": "holile"}, {"name": "Hopka", "id": "hopka"},
            {"name": "Kosa", "id": "kosa"}, {"name": "Kum Reşê", "id": "kumrese"},
            {"name": "Kûra", "id": "kura"}, {"name": "Kurê", "id": "kure"},
            {"name": "Maseka", "id": "maseka"}, {"name": "Memala", "id": "memala"},
            {"name": "Me'mala", "id": "memila"}, {"name": "Meydan Ekbez", "id": "meydan-ekbez"},
            {"name": "Mûskê", "id": "muske"}, {"name": "Penêreka", "id": "peynereke"},
            {"name": "Qere Baba", "id": "qerebaba"}, {"name": "Qêsim", "id": "qesim"},
            {"name": "Qopê", "id": "hemseleke"}, {"name": "Qude", "id": "qude"},
            {"name": "Reco", "id": "reco"}, {"name": "Şediya", "id": "sediya"},
            {"name": "Sêmala", "id": "semala"}, {"name": "Şêx", "id": "sex"},
            {"name": "Şêx Bila", "id": "sexbila"}, {"name": "Şêx Mihemed", "id": "sexmihemed"},
            {"name": "Sorkê", "id": "sorka"}, {"name": "Umera", "id": "umera"},
            {"name": "Welîklî", "id": "welikli"}, {"name": "Xirabî Silûg", "id": "xerabi-silug"},
            {"name": "Zerka", "id": "zerka"}
        ]
    },
    "Şera": {
        "hasMap": True,
        "image": "ÇK Map 12.png",
        "villages": [
            {"name": "Alciya", "id": "alciya"}, {"name": "Baflûnê", "id": "baflune"},
            {"name": "Be'rava", "id": "berava"}, {"name": "Çema", "id": "cema"},
            {"name": "Cyrrhus", "id": "nebi-huri"}, {"name": "Dewrîş", "id": "dewris"},
            {"name": "Dêrsiwanê", "id": "dersiwane"}, {"name": "Dîkmedaşê", "id": "dikmedase"},
            {"name": "Diraqliya", "id": "diraqliya"}, {"name": "Ereb Wêranê", "id": "erebwerane"},
            {"name": "Gubelê", "id": "gabeleke"}, {"name": "Ĥilûbiyê Mezin", "id": "hilubiye"},
            {"name": "Îkîdamê", "id": "ikidame"}, {"name": "Keferomê", "id": "kerferome"},
            {"name": "Kortikê", "id": "kortike"}, {"name": "Mersewa", "id": "mersewa"},
            {"name": "Meşalê", "id": "mesale"}, {"name": "Metîna", "id": "metina"},
            {"name": "Meydankê", "id": "meydanke"}, {"name": "Naza", "id": "naza"},
            {"name": "Omer Simo", "id": "omer-simo"}, {"name": "Omera", "id": "omera"},
            {"name": "Pelûsankê", "id": "pelusanke"}, {"name": "Qeredepe", "id": "qeredepe"},
            {"name": "Qestela Cindo", "id": "qastele-eli-cindo"}, {"name": "Qestelê Kîşik", "id": "qestele-kistik"},
            {"name": "Qetlebiyê", "id": "qetlebiye"}, {"name": "Qetlebiyê", "id": "qerqina"},
            {"name": "Qitmê", "id": "qitme"}, {"name": "Qurtqulaqê Çûçik", "id": "qurtqulaqe-cucik"},
            {"name": "Qurtqulaqê Mezin", "id": "qurtqulaqe-mezin"}, {"name": "Şera", "id": "sera"},
            {"name": "Serê Kaniyê", "id": "sere-kaniye"}, {"name": "Şîlte'tê", "id": "siltete"},
            {"name": "Sînka", "id": "sinka"}, {"name": "Zêtûnekê", "id": "zeytuneke"}
        ]
    },
    "Şiyê": {
        "hasMap": True,
        "image": "ÇK Map 17.png",
        "villages": [
            {"name": "Alkana", "id": "alkana"}, {"name": "Anqelê", "id": "anqele"},
            {"name": "Baziya", "id": "baziya"}, {"name": "Çeqelê Jêrin", "id": "ceqele-jerin"},
            {"name": "Çeqelê Jorin", "id": "ceqele-jorin"}, {"name": "Çeqelê Ortê", "id": "ceqele-orte"},
            {"name": "Erendê", "id": "erende"}, {"name": "Ĥec Bilal", "id": "hec-bilal"},
            {"name": "Hêkiçê", "id": "hekice"}, {"name": "Kela", "id": "kela"},
            {"name": "Mistika", "id": "mistika"}, {"name": "Qermîtliq", "id": "qermitliq"},
            {"name": "Senarê", "id": "senare"}, {"name": "Şiketka", "id": "siketka"},
            {"name": "Şiyê", "id": "siye"}, {"name": "Tirmûşa", "id": "tirmisho"},
            {"name": "Xelîl", "id": "xelil"}
        ]
    }
}

# --- 3. DYNAMIC DATA SCRAPING LOGIC ---

def scrape_village_file(file_path, filename):
    """
    Parses a single village HTML file to extract key information.
    Returns a dictionary with the data or None if parsing fails.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        soup = BeautifulSoup(content, 'html.parser')
        
        village_name = soup.find('h1').get_text(strip=True)
        
        nahiya_heading = soup.find('h3', string='Nahiya (Subdistrict)')
        nahiya_name = nahiya_heading.find_next_sibling('p').get_text(strip=True) if nahiya_heading else "Unknown"

        alt_names_heading = soup.find('h3', string='Also Known As')
        alt_names = []
        if alt_names_heading and alt_names_heading.find_next_sibling('p'):
            alt_names_text = alt_names_heading.find_next_sibling('p').get_text(strip=True)
            if alt_names_text:
                alt_names = [name.strip() for name in alt_names_text.split(',')]
        
        # NEW: Check for the presence of the "Summaries" section
        summaries_heading = soup.find('h2', string='Summaries')
        has_minimal_info = summaries_heading is None

        return {
            "name": village_name,
            "nahiya": nahiya_name,
            "alt": alt_names,
            "filename": filename,
            "has_minimal_info": has_minimal_info
        }
    except Exception as e:
        print(f"  - Could not process file '{filename}': {e}")
        return None

def get_all_scraped_data(input_dir):
    """
    Loops through the input directory, scrapes each HTML file,
    and returns a list of dictionaries, one for each village.
    """
    scraped_villages = []
    if not os.path.isdir(input_dir):
        print(f"Error: Input directory not found at '{input_dir}'")
        return scraped_villages

    print(f"Scanning for HTML files in '{input_dir}'...")
    filenames = sorted([f for f in os.listdir(input_dir) if f.endswith(".html")])
    print(f"Found {len(filenames)} HTML files to process.")

    for filename in filenames:
        file_path = os.path.join(input_dir, filename)
        village_data = scrape_village_file(file_path, filename)
        if village_data:
            scraped_villages.append(village_data)
            
    return scraped_villages

# --- 4. HTML TEMPLATE ---

html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Village Directory - Archive of Afrin</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Scheherazade+New:wght@400;700&display=swap" rel="stylesheet">
    
    <style>
        :root {
            --bg-color: #f7f5f3; --text-color: #3a3a3a; --border-color: #000000; --card-bg-color: #f7f5f3; --subtext-color: #8b7355; --link-color: #2563eb; --button-hover-bg: #000000; --button-hover-text: #f7f5f3; --internal-link-color: #2563eb; --green-color: #009A3D; --brown-color: #8b7355; --white-bg: rgba(255, 255, 255, 0.8); --nav-bg: rgba(0, 154, 61, 0.1); --village-bg: rgba(139, 115, 85, 0.1); --village-border: rgba(139, 115, 85, 0.2); --alt-name-bg: rgba(139, 115, 85, 0.8); --alt-name-text: #f7f5f3;
        }
        .dark {
            --bg-color: #2d2d2d; --text-color: #f1f1f1; --border-color: #555555; --card-bg-color: #2d2d2d; --subtext-color: #999999; --link-color: #63b3ed; --button-hover-bg: #f1f1f1; --button-hover-text: #2d2d2d; --internal-link-color: #86efac; --green-color: #86efac; --brown-color: #b8a082; --white-bg: rgba(45, 45, 45, 0.8); --nav-bg: rgba(134, 239, 172, 0.1); --village-bg: rgba(184, 160, 130, 0.1); --village-border: rgba(184, 160, 130, 0.2); --alt-name-bg: rgba(184, 160, 130, 0.8); --alt-name-text: #2d2d2d;
        }
        body { font-family: 'Inter', sans-serif; background-color: var(--bg-color); background-image: url('../nahiyas/images/background2.png'); background-size: cover; background-position: center; background-repeat: no-repeat; background-attachment: fixed; margin: 0; padding: 0; color: var(--text-color); line-height: 1.6; transition: background-color 0.3s, color 0.3s; }
        .main-content { background: linear-gradient(135deg, rgba(247, 245, 243, 0.9) 0%, rgba(242, 237, 231, 0.9) 100%); padding: 40px 20px; min-height: 80vh; }
        .dark .main-content { background: linear-gradient(135deg, rgba(45, 45, 45, 0.9) 0%, rgba(60, 60, 60, 0.9) 100%); }
        .container { max-width: 1200px; margin: 0 auto; }
        .header-section { background: linear-gradient(135deg, rgba(247, 245, 243, 0.95) 0%, rgba(242, 237, 231, 0.95) 100%); padding: 40px 20px; text-align: center; border-bottom: 3px solid var(--green-color); position: relative; }
        .dark .header-section { background: linear-gradient(135deg, rgba(45, 45, 45, 0.95) 0%, rgba(60, 60, 60, 0.95) 100%); }
        .site-title-en { font-size: 48px; font-weight: 700; color: var(--text-color); margin-bottom: 0px; letter-spacing: -1.5px; line-height: 1.3; }
        .site-title-ar { font-size: 52px; font-weight: 400; color: var(--brown-color); margin-top: -10px; margin-bottom: 20px; direction: rtl; font-family: 'Scheherazade New', serif; }
        .theme-toggle-container { margin-top: 15px; }
        .toggle-button-colors { background-color: var(--text-color); color: var(--bg-color); border: 1px solid var(--border-color); }
        .search-wrapper { display: flex; gap: 15px; justify-content: center; margin-bottom: 30px; position: relative; max-width: 600px; margin-left: auto; margin-right: auto; }
        .search-input { flex: 1; padding: 16px 22px; border: 2px solid var(--village-border); border-radius: 6px; font-size: 16px; background-color: var(--white-bg); transition: all 0.3s ease; color: var(--text-color); box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
        .search-input:focus { outline: none; border-color: var(--green-color); box-shadow: 0 2px 12px rgba(0, 154, 61, 0.15); }
        .search-button { background-color: var(--green-color); color: var(--bg-color); border: none; padding: 18px 32px; border-radius: 6px; cursor: pointer; font-size: 18px; transition: all 0.3s ease; font-weight: 500; }
        .search-button:hover { background-color: var(--brown-color); }
        .stats-bar { background: var(--nav-bg); padding: 20px; border-radius: 8px; margin-bottom: 30px; display: flex; justify-content: space-around; flex-wrap: wrap; gap: 20px; }
        .stat-item { text-align: center; }
        .stat-number { font-size: 24px; font-weight: 700; color: var(--green-color); }
        .stat-label { font-size: 14px; color: var(--brown-color); text-transform: uppercase; letter-spacing: 0.5px; }
        .nahiya-nav { background: var(--nav-bg); padding: 25px; border-radius: 8px; margin-bottom: 30px; text-align: center; }
        .nav-title { font-size: 20px; font-weight: 600; color: var(--green-color); margin-bottom: 20px; }
        .nav-buttons { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; }
        .nav-btn { background-color: var(--brown-color); color: var(--bg-color); border: none; padding: 10px 16px; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.3s ease; }
        .nav-btn:hover { background-color: var(--green-color); transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0, 154, 61, 0.3); }
        .nahiya-section { background: var(--white-bg); border-radius: 12px; padding: 30px; margin-bottom: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-left: 5px solid var(--green-color); }
        .nahiya-title { font-size: 28px; font-weight: 700; color: var(--green-color); margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid var(--brown-color); }
        .nahiya-subtitle { font-size: 22px; font-weight: 600; color: var(--brown-color); margin-top: 20px; margin-bottom: 15px; padding-bottom: 5px; border-bottom: 1px solid var(--village-border); }
        .nahiya-group { margin-bottom: 30px; }
        .nahiya-group:last-child { margin-bottom: 0; }
        .village-list { display: flex; flex-direction: column; gap: 8px; margin-top: 20px; }
        .village-link { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 0; background-color: var(--village-bg); color: var(--text-color); text-decoration: none; border-radius: 6px; transition: all 0.3s ease; border: 1px solid var(--village-border); font-weight: 500; overflow: hidden; }
        .village-name-main { padding: 12px 18px; flex-grow: 1; }
        .village-name-alt-container { display: flex; flex-wrap: wrap; gap: 4px; padding: 4px; }
        .village-name-alt { padding: 4px 8px; background-color: var(--alt-name-bg); color: var(--alt-name-text); border-radius: 4px; font-size: 12px; font-weight: 400; white-space: nowrap; transition: all 0.2s ease-in-out; }
        .village-link:hover { background-color: var(--brown-color); color: white; transform: translateX(5px); box-shadow: 0 4px 12px rgba(139, 115, 85, 0.3); }
        .village-link:hover .village-name-alt { background-color: var(--bg-color); color: var(--brown-color); }
        
        /* MODIFIED AND NEW STYLES FOR MAP LAYOUT */
        .map-wrapper { padding: 20px 0; border-bottom: 1px solid var(--village-border); margin-bottom: 20px; }
        .map-layout-container { display: flex; gap: 20px; align-items: flex-start; }
        .map-village-links-multicolumn { flex: 1; column-count: 2; column-gap: 10px; }
        .map-village-links-multicolumn a { display: block; padding: 9px 12px; color: var(--internal-link-color); text-decoration: none; border: 1px solid var(--village-border); transition: background-color 0.2s; border-radius: 4px; margin-bottom: 5px; break-inside: avoid-column; }
        .map-village-links-multicolumn a:hover { background-color: var(--village-bg); }
        .map-layout-container .map-container { flex: 1; margin: 0; }
        .map-container { position: relative; width: 100%; max-width: 500px; }
        .map-container img { display: block; width: 100%; height: auto; border-radius: 5px; }
        .highlight-box { display: none; position: absolute; background-color: yellow; opacity: 0.5; border-radius: 50%; pointer-events: none; }
        
        /* ALL MAP COORDINATES COPIED DIRECTLY */
        #Bilbilê .singele { left: 12.71%; top: 6.48%; width: 8.48%; height: 8.24%; } #Bilbilê .beke { left: 21.60%; top: 13.05%; width: 8.27%; height: 8.05%; } #Bilbilê .eli-kere { left: 28.96%; top: 17.76%; width: 8.27%; height: 8.05%; } #Bilbilê .heyama { left: 30.07%; top: 21.59%; width: 8.07%; height: 7.85%; } #Bilbilê .zere { left: 38.24%; top: 21.98%; width: 8.07%; height: 7.85%; } #Bilbilê .baliya { left: 48.94%; top: 19.14%; width: 8.68%; height: 8.44%; } #Bilbilê .xilalka { left: 9.59%; top: 32.58%; width: 8.27%; height: 8.05%; } #Bilbilê .bexce { left: 22.60%; top: 29.73%; width: 8.68%; height: 8.44%; } #Bilbilê .bilbile { left: 41.37%; top: 26.40%; width: 10.09%; height: 9.81%; } #Bilbilê .qurne { left: 51.46%; top: 25.32%; width: 8.27%; height: 8.05%; } #Bilbilê .topeli-mehmud { left: 60.24%; top: 27.58%; width: 8.48%; height: 8.24%; } #Bilbilê .kurdo { left: 70.64%; top: 28.16%; width: 8.88%; height: 8.64%; } #Bilbilê .ebudane { left: 84.76%; top: 34.15%; width: 8.88%; height: 8.64%; } #Bilbilê .elcara { left: 58.63%; top: 38.96%; width: 8.88%; height: 8.64%; } #Bilbilê .uga { left: 51.66%; top: 39.16%; width: 8.88%; height: 8.64%; } #Bilbilê .qestele-xidiriya { left: 26.03%; top: 33.66%; width: 8.88%; height: 8.64%; } #Bilbilê .xidiriya { left: 32.09%; top: 36.02%; width: 8.88%; height: 8.64%; } #Bilbilê .kurzele { left: 18.37%; top: 46.42%; width: 9.28%; height: 9.03%; } #Bilbilê .berkase { left: 33.20%; top: 47.79%; width: 9.08%; height: 8.83%; } #Bilbilê .serqiya { left: 44.20%; top: 44.16%; width: 8.88%; height: 8.64%; } #Bilbilê .qestele-miqded { left: 56.81%; top: 45.24%; width: 9.69%; height: 9.42%; } #Bilbilê .sexorze { left: 64.38%; top: 45.34%; width: 9.28%; height: 9.03%; } #Bilbilê .bibaka { left: 41.07%; top: 51.52%; width: 8.48%; height: 8.24%; } #Bilbilê .qurta { left: 51.66%; top: 50.15%; width: 9.49%; height: 9.22%; } #Bilbilê .qasa { left: 48.33%; top: 52.11%; width: 8.68%; height: 8.44%; } #Bilbilê .kela { left: 18.47%; top: 55.05%; width: 8.68%; height: 8.44%; } #Bilbilê .kere { left: 24.52%; top: 57.41%; width: 8.68%; height: 8.44%; } #Bilbilê .qota { left: 33.80%; top: 53.09%; width: 8.27%; height: 8.05%; } #Bilbilê .kotana { left: 54.49%; top: 60.06%; width: 10.29%; height: 10.01%; } #Bilbilê .upila { left: 50.05%; top: 61.73%; width: 9.49%; height: 9.22%; } #Bilbilê .xelilaka { left: 33.90%; top: 62.71%; width: 9.28%; height: 9.03%; } #Bilbilê .esune { left: 26.64%; top: 60.75%; width: 8.68%; height: 8.44%; } #Bilbilê .zivinge { left: 28.76%; top: 69.28%; width: 9.28%; height: 9.03%; } #Bilbilê .qirigole { left: 45.41%; top: 64.97%; width: 9.89%; height: 9.62%; } #Bilbilê .qizilbasa { left: 61.96%; top: 65.85%; width: 9.49%; height: 9.22%; } #Bilbilê .bele { left: 58.22%; top: 69.48%; width: 10.09%; height: 9.81%; } #Bilbilê .hesendera { left: 48.23%; top: 77.13%; width: 9.69%; height: 9.42%; }
        #Cindires .remadiye { left: 36.63%; top: 3.61%; width: 8.88%; height: 8.82%; } #Cindires .hechesna { left: 34.21%; top: 10.02%; width: 8.88%; height: 8.82%; } #Cindires .xalta { left: 53.78%; top: 12.22%; width: 9.28%; height: 9.22%; } #Cindires .colaqa-1 { left: 66.50%; top: 15.63%; width: 9.69%; height: 9.62%; } #Cindires .gewrika { left: 72.45%; top: 12.53%; width: 9.28%; height: 9.22%; } #Cindires .gorda { left: 41.57%; top: 15.63%; width: 9.49%; height: 9.42%; } #Cindires .xerza { left: 63.47%; top: 16.93%; width: 10.09%; height: 10.02%; } #Cindires .tetera { left: 34.21%; top: 18.44%; width: 9.69%; height: 9.62%; } #Cindires .cobana { left: 43.99%; top: 23.65%; width: 9.89%; height: 9.82%; } #Cindires .miske-jorin { left: 47.93%; top: 22.55%; width: 9.49%; height: 9.42%; } #Cindires .miske-jerin { left: 49.45%; top: 27.56%; width: 9.89%; height: 9.82%; } #Cindires .colaqa-2 { left: 55.09%; top: 23.85%; width: 9.49%; height: 9.42%; } #Cindires .aske-serqi { left: 56.41%; top: 18.84%; width: 9.69%; height: 9.62%; } #Cindires .feqira { left: 71.24%; top: 17.94%; width: 9.08%; height: 9.02%; } #Cindires .sex-ebdirehmen { left: 73.16%; top: 32.67%; width: 9.69%; height: 9.62%; } #Cindires .qujuma { left: 63.37%; top: 30.96%; width: 10.29%; height: 10.22%; } #Cindires .bircike { left: 53.08%; top: 34.67%; width: 10.49%; height: 10.42%; } #Cindires .kora { left: 40.56%; top: 29.06%; width: 9.69%; height: 9.62%; } #Cindires .kefersefre { left: 34.91%; top: 33.87%; width: 10.29%; height: 10.22%; } #Cindires .hekice { left: 17.96%; top: 32.26%; width: 9.89%; height: 9.82%; } #Cindires .merwane-jerin { left: 11.91%; top: 35.87%; width: 9.89%; height: 9.82%; } #Cindires .merwane-jorin { left: 17.15%; top: 37.88%; width: 8.68%; height: 8.62%; } #Cindires .aske-xerbi { left: 25.23%; top: 45.19%; width: 9.89%; height: 9.82%; } #Cindires .baflor { left: 35.92%; top: 44.79%; width: 9.28%; height: 9.22%; } #Cindires .yalanqoze { left: 43.09%; top: 45.29%; width: 9.69%; height: 9.62%; } #Cindires .sindiyanke { left: 47.02%; top: 38.78%; width: 9.89%; height: 9.82%; } #Cindires .qurbe { left: 55.30%; top: 39.68%; width: 9.89%; height: 9.82%; } #Cindires .qile { left: 63.07%; top: 39.28%; width: 9.08%; height: 9.02%; } #Cindires .tilhemo { left: 73.86%; top: 40.78%; width: 9.49%; height: 9.42%; } #Cindires .hemame { left: 14.43%; top: 58.42%; width: 9.49%; height: 9.42%; } #Cindires .heciskendere { left: 25.23%; top: 55.51%; width: 9.89%; height: 9.82%; } #Cindires .axcele { left: 35.02%; top: 56.51%; width: 9.69%; height: 9.62%; } #Cindires .cindires { left: 43.79%; top: 50.40%; width: 11.50%; height: 11.42%; } #Cindires .hemelke { left: 56.41%; top: 48.00%; width: 9.49%; height: 9.42%; } #Cindires .remedena { left: 63.57%; top: 48.10%; width: 9.28%; height: 9.22%; } #Cindires .fireriye { left: 73.56%; top: 48.80%; width: 9.28%; height: 9.22%; } #Cindires .hecilere { left: 54.69%; top: 53.21%; width: 9.89%; height: 9.82%; } #Cindires .ebukebe { left: 64.18%; top: 54.21%; width: 11.10%; height: 11.02%; } #Cindires .zelaqe { left: 80.22%; top: 52.51%; width: 9.69%; height: 9.62%; } #Cindires .sifiye { left: 18.47%; top: 71.54%; width: 9.28%; height: 9.22%; } #Cindires .mila-xelila { left: 26.54%; top: 70.94%; width: 9.49%; height: 9.42%; } #Cindires .mehmediye { left: 40.36%; top: 69.04%; width: 9.69%; height: 9.62%; } #Cindires .derbelute { left: 41.17%; top: 75.15%; width: 8.68%; height: 8.62%; } #Cindires .medaya { left: 47.63%; top: 66.33%; width: 9.08%; height: 9.02%; } #Cindires .dewe-jerin { left: 54.09%; top: 65.63%; width: 9.49%; height: 9.42%; } #Cindires .dewe-jorin { left: 50.96%; top: 74.25%; width: 9.28%; height: 9.22%; } #Cindires .tilsilore { left: 56.31%; top: 62.22%; width: 9.49%; height: 9.42%; } #Cindires .celeme { left: 71.24%; top: 67.43%; width: 10.09%; height: 10.02%; }
        #Efrîn .aster { left: 34.84%; top: 6.93%; width: 11.92%; height: 9.03%; } #Efrîn .coqe { left: 16.85%; top: 13.55%; width: 8.43%; height: 6.39%; } #Efrîn .cumqe { left: 40.70%; top: 13.94%; width: 10.28%; height: 7.79%; } #Efrîn .meriske { left: 65.67%; top: 4.21%; width: 9.66%; height: 7.32%; } #Efrîn .kefermize { left: 59.92%; top: 7.16%; width: 11.31%; height: 8.57%; } #Efrîn .sewarxa { left: 66.60%; top: 8.02%; width: 9.04%; height: 6.85%; } #Efrîn .tirtewile { left: 35.25%; top: 17.60%; width: 10.48%; height: 7.94%; } #Efrîn .qibare { left: 50.87%; top: 18.46%; width: 9.66%; height: 7.32%; } #Efrîn .efrin { left: 37.82%; top: 22.04%; width: 10.69%; height: 8.10%; } #Efrîn .gaze { left: 7.50%; top: 22.82%; width: 8.43%; height: 6.39%; } #Efrîn .gunde-mezin { left: 13.16%; top: 19.00%; width: 10.28%; height: 7.79%; } #Efrîn .xelnare { left: 19.01%; top: 18.69%; width: 8.84%; height: 6.70%; } #Efrîn .kefersile { left: 23.54%; top: 22.90%; width: 9.04%; height: 6.85%; } #Efrîn .marate { left: 16.03%; top: 24.30%; width: 9.66%; height: 7.32%; } #Efrîn .keferdele-jorin { left: 5.76%; top: 24.77%; width: 8.84%; height: 6.70%; } #Efrîn .keferdele-jerin { left: 10.59%; top: 32.48%; width: 8.02%; height: 6.07%; } #Efrîn .bablite { left: 25.69%; top: 30.61%; width: 9.25%; height: 7.01%; } #Efrîn .xalta { left: 55.19%; top: 24.14%; width: 9.66%; height: 7.32%; } #Efrîn .meremine { left: 63.62%; top: 18.30%; width: 8.43%; height: 6.39%; } #Efrîn .inabke { left: 63.72%; top: 20.64%; width: 9.25%; height: 7.01%; } #Efrîn .cilbire { left: 68.86%; top: 31.00%; width: 9.25%; height: 7.01%; } #Efrîn .bene { left: 76.46%; top: 35.75%; width: 9.66%; height: 7.32%; } #Efrîn .basile { left: 63.00%; top: 37.62%; width: 9.66%; height: 7.32%; } #Efrîn .kurzele { left: 43.58%; top: 34.66%; width: 9.46%; height: 7.16%; } #Efrîn .turinde { left: 41.11%; top: 26.32%; width: 10.28%; height: 7.79%; } #Efrîn .kersane { left: 34.84%; top: 25.70%; width: 10.69%; height: 8.10%; } #Efrîn .pitete { left: 30.22%; top: 33.41%; width: 10.07%; height: 7.63%; } #Efrîn .endare { left: 36.99%; top: 34.74%; width: 10.07%; height: 7.63%; } #Efrîn .cidede { left: 34.74%; top: 28.50%; width: 10.90%; height: 8.26%; } #Efrîn .kefirbetre { left: 20.97%; top: 36.37%; width: 9.04%; height: 6.85%; } #Efrîn .kokebe { left: 26.72%; top: 38.94%; width: 9.46%; height: 7.16%; } #Efrîn .tilfe { left: 16.65%; top: 43.54%; width: 9.25%; height: 7.01%; } #Efrîn .keferzite { left: 19.22%; top: 50.08%; width: 9.66%; height: 7.32%; } #Efrîn .kifere { left: 34.12%; top: 47.98%; width: 8.84%; height: 6.70%; } #Efrîn .basute { left: 38.54%; top: 44.39%; width: 8.84%; height: 6.70%; } #Efrîn .soxaneke { left: 54.78%; top: 42.68%; width: 10.48%; height: 7.94%; } #Efrîn .aqibe { left: 68.35%; top: 43.54%; width: 9.25%; height: 7.01%; } #Efrîn .xurebke { left: 81.09%; top: 45.95%; width: 9.25%; height: 7.01%; } #Efrîn .zarete { left: 78.73%; top: 49.30%; width: 9.04%; height: 6.85%; } #Efrîn .kimare { left: 45.43%; top: 47.66%; width: 8.84%; height: 6.70%; } #Efrîn .birce { left: 36.48%; top: 51.95%; width: 9.25%; height: 7.01%; } #Efrîn .xeziwe { left: 28.57%; top: 61.37%; width: 9.25%; height: 7.01%; } #Efrîn .iska { left: 17.37%; top: 68.07%; width: 9.25%; height: 7.01%; } #Efrîn .sadere { left: 23.54%; top: 64.56%; width: 10.28%; height: 7.79%; } #Efrîn .berade { left: 45.63%; top: 58.33%; width: 10.07%; height: 7.63%; } #Efrîn .meyase { left: 61.46%; top: 56.23%; width: 9.04%; height: 6.85%; } #Efrîn .bircilqase { left: 59.30%; top: 64.72%; width: 9.25%; height: 7.01%; } #Efrîn .biiye { left: 36.28%; top: 66.98%; width: 9.04%; height: 6.85%; } #Efrîn .kefer-nabo { left: 49.54%; top: 66.51%; width: 9.04%; height: 6.85%; } #Efrîn .basufane { left: 38.34%; top: 71.96%; width: 9.25%; height: 7.01%; } #Efrîn .gundi-mezin { left: 62.90%; top: 72.35%; width: 10.07%; height: 7.63%; } #Efrîn .birc-hedar { left: 47.48%; top: 71.57%; width: 9.25%; height: 7.01%; } #Efrîn .kibesine { left: 50.77%; top: 75.16%; width: 9.46%; height: 7.16%; } #Efrîn .farfirtine { left: 47.58%; top: 77.57%; width: 9.87%; height: 7.48%; } #Efrîn .basemre { left: 66.80%; top: 80.76%; width: 9.87%; height: 7.48%; }
        #Mabeta .sorbe { left: 46.85%; top: 9.70%; width: 8.54%; height: 5.62%; } #Mabeta .gemruk { left: 56.20%; top: 13.11%; width: 8.54%; height: 5.62%; } #Mabeta .semalka { left: 42.78%; top: 14.25%; width: 9.35%; height: 6.15%; } #Mabeta .erebsexo { left: 58.33%; top: 16.45%; width: 9.35%; height: 6.15%; } #Mabeta .sexutka { left: 53.15%; top: 19.46%; width: 8.94%; height: 5.89%; } #Mabeta .emara { left: 51.83%; top: 23.95%; width: 9.15%; height: 6.02%; } #Mabeta .avraze { left: 26.22%; top: 27.96%; width: 8.74%; height: 5.75%; } #Mabeta .gobeke { left: 22.36%; top: 30.70%; width: 9.15%; height: 6.02%; } #Mabeta .sexkele { left: 27.44%; top: 32.37%; width: 9.15%; height: 6.02%; } #Mabeta .sewiya { left: 13.62%; top: 36.59%; width: 9.15%; height: 6.02%; } #Mabeta .kelibo { left: 18.50%; top: 40.94%; width: 9.15%; height: 6.02%; } #Mabeta .enhecere { left: 71.65%; top: 29.83%; width: 10.57%; height: 6.96%; } #Mabeta .omo { left: 64.94%; top: 34.38%; width: 10.57%; height: 6.96%; } #Mabeta .kokane { left: 64.53%; top: 44.35%; width: 10.37%; height: 6.82%; } #Mabeta .qitraniye { left: 39.84%; top: 45.95%; width: 10.16%; height: 6.69%; } #Mabeta .mabete { left: 43.60%; top: 51.97%; width: 10.77%; height: 7.09%; } #Mabeta .dagire { left: 61.28%; top: 51.04%; width: 10.57%; height: 6.96%; } #Mabeta .qentere { left: 41.77%; top: 54.45%; width: 9.76%; height: 6.42%; } #Mabeta .ereba { left: 29.47%; top: 55.72%; width: 9.55%; height: 6.29%; } #Mabeta .kurke-jerin { left: 13.31%; top: 54.78%; width: 9.76%; height: 6.42%; } #Mabeta .kurke-jorin { left: 10.06%; top: 55.65%; width: 9.35%; height: 6.15%; } #Mabeta .sariya { left: 10.98%; top: 58.19%; width: 10.16%; height: 6.69%; } #Mabeta .hebo { left: 11.89%; top: 62.27%; width: 10.16%; height: 6.69%; } #Mabeta .setana { left: 15.14%; top: 59.93%; width: 10.16%; height: 6.69%; } #Mabeta .selo { left: 29.37%; top: 59.46%; width: 10.16%; height: 6.69%; } #Mabeta .xazyane-jerin { left: 21.44%; top: 64.82%; width: 9.76%; height: 6.42%; } #Mabeta .xazyane-jorin { left: 21.85%; top: 64.95%; width: 9.76%; height: 6.42%; } #Mabeta .birimce { left: 39.43%; top: 64.15%; width: 9.96%; height: 6.56%; } #Mabeta .mirka { left: 48.48%; top: 64.08%; width: 9.76%; height: 6.42%; } #Mabeta .sitka { left: 50.91%; top: 67.36%; width: 9.76%; height: 6.42%; } #Mabeta .comezna { left: 33.74%; top: 68.63%; width: 10.37%; height: 6.82%; } #Mabeta .merserke { left: 27.03%; top: 71.91%; width: 10.16%; height: 6.69%; } #Mabeta .elcara { left: 32.93%; top: 71.71%; width: 10.16%; height: 6.69%; } #Mabeta .reca { left: 36.08%; top: 71.97%; width: 9.96%; height: 6.56%; } #Mabeta .kaxre { left: 53.15%; top: 73.18%; width: 9.55%; height: 6.29%; } #Mabeta .mistesura { left: 41.67%; top: 77.86%; width: 9.15%; height: 6.02%; } #Mabeta .hecqasma { left: 40.85%; top: 79.73%; width: 9.76%; height: 6.42%; } #Mabeta .dela { left: 43.40%; top: 85.35%; width: 9.96%; height: 6.56%; } #Mabeta .ruta { left: 51.32%; top: 83.01%; width: 9.55%; height: 6.29%; }
        #Reco .meydan-ekbez { left: 45.71%; top: 5.63%; width: 10.49%; height: 7.81%; } #Reco .peynereke { left: 61.65%; top: 6.23%; width: 9.69%; height: 7.21%; } #Reco .kosa { left: 62.56%; top: 9.01%; width: 9.89%; height: 7.36%; } #Reco .gaze { left: 52.37%; top: 11.79%; width: 11.30%; height: 8.41%; } #Reco .welikli { left: 59.33%; top: 15.54%; width: 10.09%; height: 7.51%; } #Reco .dodo { left: 62.26%; top: 16.37%; width: 9.69%; height: 7.21%; } #Reco .gewenda { left: 66.19%; top: 18.69%; width: 9.49%; height: 7.06%; } #Reco .sexmihemed { left: 56.51%; top: 17.57%; width: 10.69%; height: 7.96%; } #Reco .semala { left: 53.08%; top: 18.17%; width: 10.89%; height: 8.11%; } #Reco .edema { left: 39.46%; top: 22.89%; width: 11.10%; height: 8.26%; } #Reco .qerebaba { left: 25.33%; top: 30.63%; width: 11.10%; height: 8.26%; } #Reco .elbiske { left: 43.09%; top: 30.86%; width: 11.30%; height: 8.41%; } #Reco .bilelko { left: 47.83%; top: 30.01%; width: 11.10%; height: 8.26%; } #Reco .xerabi-silug { left: 40.97%; top: 34.01%; width: 11.10%; height: 8.26%; } #Reco .firfirke-jerin { left: 36.53%; top: 32.58%; width: 8.88%; height: 6.61%; } #Reco .firfirke-jorin { left: 35.12%; top: 35.89%; width: 11.10%; height: 8.26%; } #Reco .heydar { left: 38.04%; top: 39.26%; width: 10.89%; height: 8.11%; } #Reco .ceinke { left: 44.60%; top: 35.51%; width: 11.70%; height: 8.71%; } #Reco .cela { left: 56.91%; top: 33.86%; width: 11.50%; height: 8.56%; } #Reco .ceqmaqe-mezin { left: 51.06%; top: 43.24%; width: 11.10%; height: 8.26%; } #Reco .ceqmaqe-cucik { left: 59.03%; top: 45.35%; width: 9.89%; height: 7.36%; } #Reco .elendara { left: 64.98%; top: 44.00%; width: 9.49%; height: 7.06%; } #Reco .zerka { left: 68.21%; top: 47.82%; width: 10.29%; height: 7.66%; } #Reco .memala { left: 40.77%; top: 48.72%; width: 10.29%; height: 7.66%; } #Reco .cenceliya { left: 54.89%; top: 47.60%; width: 10.89%; height: 8.11%; } #Reco .cobana { left: 65.19%; top: 49.47%; width: 11.30%; height: 8.41%; } #Reco .holile { left: 49.34%; top: 51.28%; width: 11.50%; height: 8.56%; } #Reco .cerxuta { left: 58.12%; top: 53.53%; width: 9.69%; height: 7.21%; } #Reco .kura { left: 53.38%; top: 54.73%; width: 11.10%; height: 8.26%; } #Reco .qesim { left: 69.43%; top: 54.28%; width: 10.49%; height: 7.81%; } #Reco .dike { left: 79.11%; top: 54.20%; width: 10.89%; height: 8.11%; } #Reco .maseka { left: 35.32%; top: 52.25%; width: 10.09%; height: 7.51%; } #Reco .hopka { left: 29.77%; top: 58.03%; width: 10.49%; height: 7.81%; } #Reco .sorka { left: 5.85%; top: 64.64%; width: 9.89%; height: 7.36%; } #Reco .reco { left: 38.75%; top: 56.08%; width: 10.89%; height: 8.11%; } #Reco .xecxelil { left: 44.90%; top: 56.68%; width: 11.10%; height: 8.26%; } #Reco .ceqilme { left: 62.97%; top: 59.23%; width: 10.29%; height: 7.66%; } #Reco .sex { left: 71.34%; top: 61.56%; width: 10.09%; height: 7.51%; } #Reco .ciye { left: 80.12%; top: 65.54%; width: 10.09%; height: 7.51%; } #Reco .banika { left: 35.42%; top: 62.16%; width: 9.28%; height: 6.91%; } #Reco .etmana { left: 35.12%; top: 63.36%; width: 9.89%; height: 7.36%; } #Reco .sexbila { left: 59.03%; top: 63.06%; width: 10.49%; height: 7.81%; } #Reco .goliye-jerin { left: 63.47%; top: 66.07%; width: 10.49%; height: 7.81%; } #Reco .goliye-jorin { left: 58.73%; top: 67.34%; width: 10.29%; height: 7.66%; } #Reco .muske { left: 42.89%; top: 65.77%; width: 11.10%; height: 8.26%; } #Reco .kure { left: 20.79%; top: 68.70%; width: 11.30%; height: 8.41%; } #Reco .hecika { left: 31.89%; top: 66.89%; width: 10.69%; height: 7.96%; } #Reco .sediya { left: 15.24%; top: 73.72%; width: 10.29%; height: 7.66%; } #Reco .kumrese { left: 22.20%; top: 73.80%; width: 9.69%; height: 7.21%; } #Reco .qude { left: 31.18%; top: 75.75%; width: 10.89%; height: 8.11%; } #Reco .deewris { left: 39.76%; top: 71.02%; width: 10.49%; height: 7.81%; } #Reco .hemseleke { left: 49.85%; top: 72.75%; width: 11.10%; height: 8.26%; } #Reco .berbene { left: 56.61%; top: 71.40%; width: 10.69%; height: 7.96%; } #Reco .bedina { left: 47.23%; top: 76.58%; width: 10.49%; height: 7.81%; } #Reco .dumiliya { left: 42.18%; top: 79.95%; width: 10.49%; height: 7.81%; } #Reco .umera { left: 23.71%; top: 80.63%; width: 9.89%; height: 7.36%; } #Reco .memila { left: 26.44%; top: 83.71%; width: 10.29%; height: 7.66%; } #Reco .hesen { left: 25.63%; top: 72.07%; width: 9.69%; height: 7.21%; }
        #Şera .nebi-huri { left: 34.51%; top: 3.04%; width: 9.89%; height: 7.26%; } #Şera .mersewa { left: 45.41%; top: 9.34%; width: 9.89%; height: 7.26%; } #Şera .siltete { left: 59.84%; top: 11.05%; width: 9.28%; height: 6.82%; } #Şera .omer-simo { left: 38.85%; top: 14.75%; width: 8.88%; height: 6.52%; } #Şera .siiriya { left: 31.08%; top: 20.83%; width: 9.69%; height: 7.12%; } #Şera .zeytuneke { left: 42.89%; top: 21.05%; width: 9.69%; height: 7.12%; } #Şera .ikidame { left: 74.97%; top: 19.87%; width: 9.69%; height: 7.12%; } #Şera .dersiwane { left: 63.17%; top: 24.76%; width: 10.69%; height: 7.86%; } #Şera .diraqliya { left: 30.88%; top: 28.17%; width: 9.28%; height: 6.82%; } #Şera .pelusanke { left: 44.40%; top: 31.06%; width: 9.49%; height: 6.97%; } #Şera .alciya { left: 36.23%; top: 36.70%; width: 8.88%; height: 6.52%; } #Şera .qetlebiye { left: 47.73%; top: 37.73%; width: 9.28%; height: 6.82%; } #Şera .dewris { left: 28.15%; top: 38.77%; width: 8.88%; height: 6.52%; } #Şera .qerqina { left: 36.93%; top: 43.81%; width: 8.68%; height: 6.37%; } #Şera .naza { left: 21.09%; top: 41.88%; width: 9.69%; height: 7.12%; } #Şera .omera { left: 47.83%; top: 44.11%; width: 9.08%; height: 6.67%; } #Şera .erebwerane { left: 62.46%; top: 36.92%; width: 9.49%; height: 6.97%; } #Şera .dikmedase { left: 69.93%; top: 42.18%; width: 9.08%; height: 6.67%; } #Şera .yazibaxe { left: 80.93%; top: 44.85%; width: 9.69%; height: 7.12%; } #Şera .qastele-eli-cindo { left: 71.44%; top: 52.78%; width: 9.49%; height: 6.97%; } #Şera .baflune { left: 57.72%; top: 59.38%; width: 9.49%; height: 6.97%; } #Şera .ezaz { left: 79.21%; top: 67.16%; width: 9.69%; height: 7.12%; } #Şera .qitme { left: 51.16%; top: 65.68%; width: 9.28%; height: 6.82%; } #Şera .cema { left: 42.38%; top: 47.44%; width: 9.49%; height: 6.97%; } #Şera .sinka { left: 46.92%; top: 55.23%; width: 9.28%; height: 6.82%; } #Şera .berava { left: 35.72%; top: 46.55%; width: 8.48%; height: 6.23%; } #Şera .sera { left: 41.27%; top: 55.67%; width: 9.28%; height: 6.82%; } #Şera .gabeleke { left: 31.28%; top: 54.26%; width: 9.49%; height: 6.97%; } #Şera .meydanke { left: 20.99%; top: 50.04%; width: 9.49%; height: 6.97%; } #Şera .hilubiye { left: 23.11%; top: 63.53%; width: 9.69%; height: 7.12%; } #Şera .kerferome { left: 13.72%; top: 67.38%; width: 9.08%; height: 6.67%; } #Şera .qurtqulaqe-mezin { left: 22.50%; top: 70.05%; width: 9.69%; height: 7.12%; } #Şera .qurtqulaqe-cucik { left: 22.10%; top: 73.17%; width: 9.49%; height: 6.97%; } #Şera .xirabi-sera { left: 41.07%; top: 57.45%; width: 9.69%; height: 7.12%; } #Şera .metina { left: 41.37%; top: 63.90%; width: 9.49%; height: 6.97%; } #Şera .sere-kaniye { left: 46.42%; top: 67.61%; width: 9.49%; height: 6.97%; } #Şera .mesale { left: 39.15%; top: 69.46%; width: 10.09%; height: 7.41%; } #Şera .kortike { left: 30.98%; top: 73.17%; width: 9.69%; height: 7.12%; } #Şera .qeredepe { left: 26.74%; top: 78.28%; width: 10.09%; height: 7.41%; } #Şera .qestele-kistik { left: 20.38%; top: 80.73%; width: 8.88%; height: 6.52%; } #Şera .cumke { left: 20.69%; top: 84.58%; width: 8.68%; height: 6.37%; }
        #Şiyê .tirmisho { left: 66.2%; top: 37.0%; width: 9.1%; height: 6.0%; } #Şiyê .kela { left: 59.1%; top: 27.0%; width: 6.7%; height: 4.4%; } #Şiyê .alkana { left: 57.0%; top: 15.1%; width: 7.7%; height: 5.1%; } #Şiyê .xelil { left: 64.5%; top: 13.9%; width: 7.7%; height: 5.1%; } #Şiyê .ceqele-jorin { left: 45.2%; top: 18.1%; width: 9.1%; height: 6.0%; } #Şiyê .ceqele-jerin { left: 36.7%; top: 23.2%; width: 9.9%; height: 6.5%; } #Şiyê .hec-bilal { left: 54.7%; top: 18.8%; width: 8.3%; height: 5.5%; } #Şiyê .ceqele-orte { left: 44.1%; top: 22.5%; width: 9.3%; height: 6.1%; } #Şiyê .mistika { left: 44.1%; top: 27.1%; width: 9.5%; height: 6.3%; } #Şiyê .siketka { left: 70.7%; top: 34.5%; width: 8.5%; height: 5.6%; } #Şiyê .erende { left: 47.9%; top: 35.0%; width: 9.1%; height: 6.0%; } #Şiyê .qermitliq { left: 18.1%; top: 36.3%; width: 10.9%; height: 7.2%; } #Şiyê .siye { left: 28.4%; top: 44.3%; width: 17.8%; height: 11.7%; } #Şiyê .senare { left: 31.1%; top: 60.4%; width: 10.1%; height: 6.7%; } #Şiyê .anqele { left: 31.0%; top: 64.4%; width: 8.9%; height: 5.9%; } #Şiyê .baziya { left: 52.0%; top: 65.7%; width: 10.1%; height: 6.7%; } #Şiyê .hekice { left: 38.8%; top: 76.8%; width: 10.1%; height: 6.7%; }

        .footer { text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid var(--village-border); color: var(--subtext-color); font-size: 14px; }
        
        @media (max-width: 768px) {
            .header-section, .main-content { padding: 20px 15px; } .site-title-en { font-size: 36px; } .site-title-ar { font-size: 40px; } .search-wrapper, .stats-bar, .nav-buttons { flex-direction: column; align-items: stretch; gap: 15px; } .nahiya-title { font-size: 24px; } .nahiya-section { padding: 20px; }
            /* NEW RESPONSIVE RULES FOR MAP */
            .map-layout-container { flex-direction: column; }
            .map-village-links-multicolumn { column-count: 1; margin-bottom: 20px; }
        }
        @media (max-width: 480px) {
            .header-section { padding: 25px 10px; } .main-content { padding: 20px 10px; } .site-title-en { font-size: 28px; } .site-title-ar { font-size: 32px; } .village-link { flex-direction: column; align-items: stretch; } .village-name-alt-container { justify-content: flex-start; }
        }
    </style>
</head>
<body>
    <div class="header-section">
        <h1 class="site-title-en">Archive of Afrin: Village Directory</h1>
        <h2 class="site-title-ar">أرشيف عفرين: دليل القرى</h2>
        <div class="theme-toggle-container">
            <button id="theme-toggle" class="toggle-button-colors" style="padding: 8px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center;">
                <svg id="theme-toggle-dark-icon" class="hidden" style="width: 24px; height: 24px;" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"></path></svg>
                <svg id="theme-toggle-light-icon" class="hidden" style="width: 24px; height: 24px;" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M12 3v2.25m6.364.386-1.591 1.591M21 12h-2.25m-.386 6.364-1.591-1.591M12 18.75V21m-4.773-4.227-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0Z" /></svg>
            </button>
        </div>
    </div>

    <div class="main-content">
        <div class="container">
            <div class="search-wrapper">
                <input type="text" id="search-input" class="search-input" placeholder="Search villages...">
                <button class="search-button">Search</button>
            </div>
            <div class="stats-bar">
                <div class="stat-item"><div id="village-count" class="stat-number"></div><div class="stat-label">Villages</div></div>
                <div class="stat-item"><div id="nahiya-count" class="stat-number"></div><div class="stat-label">Nahiyas</div></div>
                <div class="stat-item"><div class="stat-number">Archive Status</div><div class="stat-label">In Research and Development</div></div>
            </div>
            
            <div class="nahiya-nav">
                <h4 class="nav-title">Quick Navigation to Nahiya</h4>
                <div id="nahiya-nav-buttons" class="nav-buttons"></div>
            </div>

            <div class="nahiya-section" id="alphabetical-list-section">
                <h3 class="nahiya-title">All Villages (Alphabetical)</h3>
                <div id="alphabetical-list-container" class="village-list"></div>
            </div>
    
            <div class="nahiya-section" id="by-nahiya-list-section">
                <h3 class="nahiya-title">Villages by Nahiya</h3>
                <div id="by-nahiya-list-container"></div>
            </div>

            <footer class="footer">
                <p>Last Updated: September 15, 2025</p>
            </footer>
        </div>
    </div>

    <script>
        // EXACT SCRIPT FROM All_Nahiyas_Clickable_Maps.html
        function showHighlight() {
            document.querySelectorAll('.highlight-box').forEach(box => { box.style.display = 'none'; });
            if (window.location.hash) {
                try {
                    const activeLink = document.querySelector(`a[href="${window.location.hash}"]`);
                    if (activeLink) {
                        const parentSection = activeLink.closest('.nahiya-group');
                        if (parentSection) {
                            const highlightClass = window.location.hash.substring(1);
                            const highlightBox = parentSection.querySelector('.' + highlightClass);
                            if (highlightBox) { highlightBox.style.display = 'block'; }
                        }
                    }
                } catch (e) { console.error("Could not process hash:", window.location.hash, e); }
            }
        }
        window.addEventListener('hashchange', showHighlight);
        window.addEventListener('DOMContentLoaded', showHighlight);

        // --- Page Building and Other Logic ---
        document.addEventListener('DOMContentLoaded', function() {
            const nahiyas = __NAHIYAS_DATA_JSON_PLACEHOLDER__;

            const alphabeticalContainer = document.getElementById('alphabetical-list-container');
            const byNahiyaContainer = document.getElementById('by-nahiya-list-container');
            const navButtonsContainer = document.getElementById('nahiya-nav-buttons');
            let allVillagesForAlphabeticalList = [];

            function createDetailedVillageLink(village) {
                const linkWrapper = document.createElement('a');
                linkWrapper.className = "village-link";
                // Use the actual filename for the link
                linkWrapper.href = `../village_sites/${village.filename}`;
                linkWrapper.target = "_blank";

                const mainName = document.createElement('span');
                mainName.className = "village-name-main";
                mainName.textContent = village.name;
                
                // NEW: Check the flag and apply blue color if info is minimal
                if (village.has_minimal_info) {
                    mainName.style.color = 'var(--internal-link-color)';
                }
                
                const altContainer = document.createElement('div');
                altContainer.className = 'village-name-alt-container';
                if (village.alt && village.alt.length > 0) {
                    village.alt.forEach(altText => {
                        const altName = document.createElement('span');
                        altName.className = "village-name-alt";
                        altName.textContent = altText;
                        altContainer.appendChild(altName);
                    });
                }
                
                linkWrapper.appendChild(mainName);
                linkWrapper.appendChild(altContainer);
                return linkWrapper;
            }

            // Sort nahiyas alphabetically for display
            const sortedNahiyaNames = Object.keys(nahiyas).sort((a, b) => a.localeCompare(b));

            for (const nahiyaName of sortedNahiyaNames) {
                const nahiyaData = nahiyas[nahiyaName];
                const safeId = `nahiya-${nahiyaName.replace(/[^a-zA-Z0-9]/g, '')}`;
                
                const groupDiv = document.createElement('div');
                groupDiv.className = 'nahiya-group';
                groupDiv.id = safeId;

                const subtitle = document.createElement('h4');
                subtitle.className = 'nahiya-subtitle';
                subtitle.textContent = nahiyaName;
                groupDiv.appendChild(subtitle);
                
                // This section uses the HARDCODED map data
                if (nahiyaData.hasMap) {
                    const mapWrapper = document.createElement('div');
                    mapWrapper.className = 'map-wrapper';
                    mapWrapper.id = nahiyaName;

                    const mapLayoutContainer = document.createElement('div');
                    mapLayoutContainer.className = 'map-layout-container';

                    const villageLinks = document.createElement('div');
                    villageLinks.className = 'map-village-links-multicolumn';
                    nahiyaData.villages.forEach(village => {
                        const link = document.createElement('a');
                        link.href = `#${village.id}`;
                        link.textContent = village.name;
                        villageLinks.appendChild(link);
                    });

                    const mapContainer = document.createElement('div');
                    mapContainer.className = 'map-container';
                    
                    const mapImage = document.createElement('img');
                    mapImage.alt = `Map of ${nahiyaName}`;
                    mapImage.onerror = function() { this.onerror=null; this.src=`https://placehold.co/500x331/ef4444/ffffff?text=IMAGE+NOT+FOUND`; };
                    mapImage.src = `../nahiyas/${nahiyaData.image}`;
                    mapContainer.appendChild(mapImage);

                    nahiyaData.villages.forEach(village => {
                        const highlightBox = document.createElement('div');
                        highlightBox.className = `${village.id} highlight-box`;
                        mapContainer.appendChild(highlightBox);
                    });
                    
                    mapLayoutContainer.appendChild(villageLinks);
                    mapLayoutContainer.appendChild(mapContainer);
                    mapWrapper.appendChild(mapLayoutContainer);
                    groupDiv.appendChild(mapWrapper);
                }

                // This section uses the DYNAMICALLY SCRAPED data
                const detailedVillageList = document.createElement('div');
                detailedVillageList.className = 'village-list';
                if (nahiyaData.all_villages_detailed) {
                    // Sort villages alphabetically within the nahiya
                    nahiyaData.all_villages_detailed.sort((a, b) => a.name.localeCompare(b.name));
                    nahiyaData.all_villages_detailed.forEach(village => {
                        detailedVillageList.appendChild(createDetailedVillageLink(village));
                        allVillagesForAlphabeticalList.push(village); // Collect for main alphabetical list
                    });
                }
                groupDiv.appendChild(detailedVillageList);
                
                byNahiyaContainer.appendChild(groupDiv);

                const navButton = document.createElement('button');
                navButton.className = 'nav-btn';
                navButton.textContent = nahiyaName;
                navButton.onclick = () => scrollToSection(safeId);
                navButtonsContainer.appendChild(navButton);
            }
            
            // Update counts based on the number of villages actually scraped and displayed
            document.getElementById('village-count').textContent = allVillagesForAlphabeticalList.length;
            document.getElementById('nahiya-count').textContent = sortedNahiyaNames.length;

            // Build the main alphabetical list from all collected villages
            allVillagesForAlphabeticalList.sort((a, b) => a.name.localeCompare(b.name));
            allVillagesForAlphabeticalList.forEach(village => alphabeticalContainer.appendChild(createDetailedVillageLink(village)));

            const themeToggleBtn = document.getElementById('theme-toggle');
            const setupTheme = () => {
                const isDark = localStorage.getItem('color-theme') === 'dark' || (!('color-theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches);
                document.documentElement.classList.toggle('dark', isDark);
                document.getElementById('theme-toggle-light-icon').classList.toggle('hidden', !isDark);
                document.getElementById('theme-toggle-dark-icon').classList.toggle('hidden', isDark);
            };
            setupTheme();
            themeToggleBtn.addEventListener('click', () => {
                const isDark = document.documentElement.classList.toggle('dark');
                localStorage.setItem('color-theme', isDark ? 'dark' : 'light');
                setupTheme();
            });
        });
        
        function scrollToSection(sectionId) {
            const element = document.getElementById(sectionId);
            if (element) { element.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
        }
    </script>
</body>
</html>
"""

# --- 5. MAIN EXECUTION LOGIC ---

def main():
    """
    Main function to orchestrate the scraping, data merging, and file generation.
    """
    print("Starting website generation...")
    
    # Step 1: Scrape all village data from the input folder
    scraped_villages = get_all_scraped_data(INPUT_FOLDER)
    if not scraped_villages:
        print("Fatal Error: No village files were found or processed. Aborting.")
        return

    # Step 2: Group scraped villages by nahiya for easy lookup
    all_nahiyas_detailed = {}
    for village in scraped_villages:
        nahiya = village['nahiya']
        if nahiya not in all_nahiyas_detailed:
            all_nahiyas_detailed[nahiya] = []
        all_nahiyas_detailed[nahiya].append(village)

    # Step 3: Assemble the final data structure
    # Start with a deep copy of the static map data to ensure it's never modified
    final_data = json.loads(json.dumps(nahiyas_map_data))

    # Add the dynamically scraped lists to the existing nahiyas
    for nahiya_name in final_data:
        if nahiya_name in all_nahiyas_detailed:
            final_data[nahiya_name]['all_villages_detailed'] = all_nahiyas_detailed[nahiya_name]
        else:
            final_data[nahiya_name]['all_villages_detailed'] = []
            print(f"Warning: No villages found for map-defined nahiya '{nahiya_name}'.")

    # Add new nahiyas found during scraping that don't have maps (e.g., Azaz)
    for nahiya_name, villages in all_nahiyas_detailed.items():
        if nahiya_name not in final_data:
            print(f"Found new nahiya without a map: '{nahiya_name}'")
            final_data[nahiya_name] = {
                "hasMap": False,
                "villages": [], # Must have this key, even if empty
                "all_villages_detailed": villages
            }

    # Step 4: Convert the final Python dictionary to a JSON string
    final_json_string = json.dumps(final_data, indent=4, ensure_ascii=False)

    # Step 5: Inject the JSON data into the HTML template
    final_html_content = html_template.replace(
        "__NAHIYAS_DATA_JSON_PLACEHOLDER__", final_json_string
    )

    # Step 6: Write the final HTML to the specified output file
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    output_path = os.path.join(OUTPUT_FOLDER, OUTPUT_FILENAME)

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(final_html_content)
        print(f"\nSuccess! Website generated at: {output_path}")
        print(f"Total villages processed: {len(scraped_villages)}")
        print(f"Total nahiyas created: {len(final_data)}")
    except IOError as e:
        print(f"\nError: Could not write to file '{output_path}'. Reason: {e}")

if __name__ == "__main__":
    main()