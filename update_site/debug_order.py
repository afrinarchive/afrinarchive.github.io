
from bs4 import BeautifulSoup
import re

html_path = r"C:\Users\Zachar\Desktop\Afrin_Archive\village_sites\Be'dîna.html"

with open(html_path, "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

# Check Summaries
print("--- SUMMARIES ORDER ---")
# Summaries are in <div class="card ..."> <h2>Summaries</h2> ... <h3...>Title</h3>
summary_card = None
for card in soup.find_all("div", class_="card"):
    h2 = card.find("h2")
    if h2 and "Summaries" in h2.text:
        summary_card = card
        break

if summary_card:
    # Titles are in <details><summary><span>TITLE</span>
    titles = [s.get_text(strip=True) for s in summary_card.find_all("summary")]
    for t in titles:
        print(f" - {t}")
else:
    print("NO SUMMARIES CARD FOUND")

# Check Table Order
print("\n--- TABLE SOURCE ORDER ---")
rows = soup.find_all("tr")
for r in rows:
    cols = r.find_all("td")
    if cols:
        print(f" - {cols[0].text.strip()}")
