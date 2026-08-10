"""Author dinner symbolism for the remaining dishes so the Global Dinner Party can
draw from the whole menu while still teaching something on every card.

Appends the curated rows to pipeline/curated/dinner_symbolism.csv (pipe-joined lists,
matching the existing format) AND inserts them into the live SQLite plates.db (arrays
as JSON strings, matching how the app reads them). Idempotent: a dish already carrying
symbolism is skipped.

Run:  python -m scripts.add_symbolism
"""
from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = PROJECT_ROOT / "pipeline" / "curated" / "dinner_symbolism.csv"
DB_PATH = PROJECT_ROOT / "data" / "plates.db"

# dish -> (symbolism, [connecting_ingredients], [trade_routes], [cultural_values])
ENTRIES: list[tuple[str, str, list[str], list[str], list[str]]] = [
    ("Asado", "The weekend fire that gathers the whole family", ["beef", "salt", "fire"], ["Pampas cattle culture"], ["community", "celebration"]),
    ("Dulce de Leche", "Caramel sweetness poured over childhood", ["milk", "sugar"], ["colonial dairy exchange"], ["comfort", "nostalgia"]),
    ("Empanadas", "Hand-folded parcels shared at every gathering", ["wheat", "beef"], ["Spanish colonial exchange"], ["family", "hospitality"]),
    ("Milanesa", "A breaded comfort carried by Italian immigrants", ["beef", "breadcrumb", "egg"], ["Italian migration"], ["comfort", "heritage"]),
    ("Hilsa Curry", "The prized river fish at the heart of Bengali feasts", ["hilsa", "mustard", "rice"], ["Bay of Bengal trade"], ["pride", "festivity"]),
    ("Panta Bhat", "Fermented rice that welcomes the Bengali new year", ["rice", "water"], ["ancient rice culture"], ["renewal", "simplicity"]),
    ("Roshogolla", "Spongy syrup-soaked sweets of celebration", ["milk", "sugar"], ["Bengal sweet tradition"], ["joy", "togetherness"]),
    ("Ajiaco", "A hearty highland soup that warms Bogota", ["potato", "chicken", "corn"], ["Andean origin"], ["comfort", "home"]),
    ("Arepas", "The daily corn cake of the northern Andes", ["maize"], ["Mesoamerican origin"], ["sustenance", "sharing"]),
    ("Bandeja Paisa", "A mountain feast piled high with abundance", ["beans", "pork", "rice"], ["Antioquian tradition"], ["abundance", "labor"]),
    ("Basbousa", "Semolina sweetness soaked in fragrant syrup", ["semolina", "honey"], ["Ottoman exchange"], ["celebration", "hospitality"]),
    ("Ful Medames", "The ancient bean breakfast of the Nile", ["fava beans", "olive oil"], ["Nile Valley origin"], ["sustenance", "tradition"]),
    ("Koshari", "A street-food melting pot in a single bowl", ["rice", "lentils", "pasta"], ["Mediterranean & Indian exchange"], ["fusion", "thrift"]),
    ("Molokhia", "A green jute-leaf stew from pharaonic times", ["jute leaf", "garlic"], ["Nile Valley origin"], ["heritage", "comfort"]),
    ("Black Forest Cake", "Cherry and cream layered into indulgence", ["cherry", "chocolate", "cream"], ["European baking exchange"], ["celebration", "indulgence"]),
    ("Bratwurst", "The grilled sausage of fairs and festivals", ["pork", "spices"], ["Germanic sausage craft"], ["conviviality", "tradition"]),
    ("Pretzel", "A knotted emblem of the baker's guilds", ["wheat", "salt"], ["monastic baking"], ["craft", "good fortune"]),
    ("Sauerbraten", "A slow-marinated Sunday roast", ["beef", "vinegar", "spices"], ["medieval preservation"], ["patience", "tradition"]),
    ("Gado-Gado", "A vegetable medley united by peanut sauce", ["vegetables", "peanut", "egg"], ["Spice Islands trade"], ["harmony", "balance"]),
    ("Nasi Goreng", "Fragrant fried rice that wastes nothing", ["rice", "soy", "chili"], ["Chinese-Indonesian exchange"], ["thrift", "comfort"]),
    ("Rendang", "Slow-simmered spice mastery of the Minangkabau", ["beef", "coconut", "chili"], ["Spice Route"], ["patience", "prestige"]),
    ("Satay", "Skewered street smoke with peanut sauce", ["meat", "peanut", "turmeric"], ["maritime spice trade"], ["conviviality", "street life"]),
    ("Chelo Kabab", "The national plate of rice and grilled meat", ["rice", "lamb", "saffron"], ["Silk Road"], ["hospitality", "pride"]),
    ("Fesenjan", "A regal stew of pomegranate and walnut", ["pomegranate", "walnut", "chicken"], ["Persian court cuisine"], ["richness", "celebration"]),
    ("Ghormeh Sabzi", "The beloved herb stew of Persian homes", ["herbs", "beans", "lamb"], ["Persian origin"], ["home", "tradition"]),
    ("Tahdig", "The prized crispy rice everyone reaches for", ["rice", "saffron", "oil"], ["Persian rice culture"], ["delight", "sharing"]),
    ("Nyama Choma", "Roasted meat that brings friends together", ["meat", "salt"], ["East African pastoral culture"], ["community", "celebration"]),
    ("Sukuma Wiki", "Greens that stretch the week", ["collard greens", "onion"], ["colonial-era staple"], ["thrift", "sustenance"]),
    ("Ugali", "The maize staple that anchors every meal", ["maize"], ["Columbian exchange (maize)"], ["sustenance", "unity"]),
    ("Hummus", "A creamy chickpea dip of shared tables", ["chickpea", "tahini", "lemon"], ["Levantine origin"], ["sharing", "hospitality"]),
    ("Shawarma", "Spit-roasted street food that circled the world", ["meat", "spices", "bread"], ["Ottoman origin"], ["street life", "fusion"]),
    ("Tabbouleh", "A herb-bright salad of the Levant", ["parsley", "bulgur", "lemon"], ["Levantine origin"], ["freshness", "health"]),
    ("Laksa", "A spicy noodle soup of cultural crossroads", ["rice noodles", "coconut", "chili"], ["Straits Chinese fusion"], ["fusion", "vibrancy"]),
    ("Nasi Lemak", "Coconut rice hailed as the national dish", ["rice", "coconut", "chili"], ["Malay origin"], ["identity", "comfort"]),
    ("Roti Canai", "Flaky flatbread of Indian-Malay mornings", ["wheat", "ghee"], ["Indian migration"], ["fusion", "street life"]),
    ("Bitterballen", "Crispy bites shared over friendly drinks", ["beef", "breadcrumb"], ["Dutch tavern tradition"], ["conviviality", "comfort"]),
    ("Haring", "Raw herring, a taste of the sea's bounty", ["herring", "onion"], ["North Sea fishing"], ["heritage", "simplicity"]),
    ("Stroopwafel", "A caramel-filled waffle born in Gouda", ["wheat", "caramel"], ["Dutch baking"], ["comfort", "craft"]),
    ("Egusi Soup", "A melon-seed stew at the center of feasts", ["melon seed", "leafy greens"], ["West African origin"], ["community", "abundance"]),
    ("Jollof Rice", "The one-pot rice at the heart of friendly rivalry", ["rice", "tomato", "pepper"], ["trans-Atlantic exchange"], ["pride", "festivity"]),
    ("Puff Puff", "Sweet fried dough of celebrations", ["wheat", "sugar"], ["West African street food"], ["joy", "sharing"]),
    ("Suya", "Spiced grilled skewers of the northern streets", ["beef", "peanut", "spices"], ["Hausa trade routes"], ["street life", "conviviality"]),
    ("Haleem", "A slow-cooked wheat-and-meat stew of patience", ["wheat", "lentils", "meat"], ["Persian-Mughal exchange"], ["patience", "community"]),
    ("Nihari", "A slow morning stew once fit for royalty", ["beef", "spices"], ["Mughal cuisine"], ["indulgence", "heritage"]),
    ("Seekh Kebab", "Spiced minced-meat skewers off the grill", ["meat", "spices"], ["Central Asian-Mughal exchange"], ["conviviality", "craft"]),
    ("Aji de Gallina", "A creamy chili chicken of Lima comfort", ["chicken", "aji", "walnut"], ["colonial-Andean fusion"], ["comfort", "fusion"]),
    ("Ceviche", "Citrus-cured fish, a gift of the Pacific", ["fish", "lime", "chili"], ["Pacific coastal origin"], ["freshness", "pride"]),
    ("Lomo Saltado", "A stir-fry born of Chinese-Peruvian kitchens", ["beef", "soy", "potato"], ["Chinese migration (chifa)"], ["fusion", "ingenuity"]),
    ("Adobo", "The tangy national dish of every household", ["pork", "vinegar", "soy"], ["Austronesian-Spanish fusion"], ["home", "identity"]),
    ("Halo-Halo", "A colorful shaved-ice medley of mix-mix", ["shaved ice", "beans", "milk"], ["American-era dessert"], ["joy", "abundance"]),
    ("Lumpia", "Crisp spring rolls shared at gatherings", ["wheat", "vegetables", "pork"], ["Chinese migration"], ["sharing", "festivity"]),
    ("Sinigang", "A sour tamarind soup that comforts", ["tamarind", "pork", "vegetables"], ["Austronesian origin"], ["comfort", "home"]),
    ("Bigos", "The hunter's stew that improves with age", ["cabbage", "meat"], ["Polish forest tradition"], ["patience", "heartiness"]),
    ("Kielbasa", "The smoky sausage of celebration and craft", ["pork", "garlic"], ["Central European curing"], ["tradition", "conviviality"]),
    ("Pierogi", "Filled dumplings folded for every occasion", ["wheat", "potato", "cheese"], ["Central & Eastern European exchange"], ["family", "comfort"]),
    ("Bacalhau", "Salt cod, faithful friend of a seafaring nation", ["cod", "olive oil"], ["Atlantic cod trade"], ["heritage", "resourcefulness"]),
    ("Caldo Verde", "A humble kale-and-potato soup of the north", ["kale", "potato", "sausage"], ["rural Portuguese origin"], ["comfort", "simplicity"]),
    ("Pastel de Nata", "The custard tart born in a Lisbon monastery", ["egg", "cream", "pastry"], ["monastic baking"], ["indulgence", "craft"]),
    ("Beef Stroganoff", "Aristocratic beef in a creamy sauce", ["beef", "cream", "mushroom"], ["19th-century Russian court"], ["comfort", "prestige"]),
    ("Blini", "Thin pancakes marking the turn of the seasons", ["wheat", "egg"], ["Slavic sun ritual"], ["celebration", "renewal"]),
    ("Borscht", "The ruby beet soup of Slavic tables", ["beet", "cabbage"], ["Eastern European origin"], ["home", "comfort"]),
    ("Pelmeni", "Siberian dumplings frozen for the long winter", ["wheat", "meat"], ["Ural & Siberian origin"], ["resourcefulness", "family"]),
    ("Falafel", "Crisp chickpea fritters of the shared table", ["chickpea", "herbs"], ["Levantine origin"], ["sharing", "hospitality"]),
    ("Kabsa", "The fragrant spiced rice of gatherings", ["rice", "meat", "spices"], ["Arabian spice trade"], ["hospitality", "generosity"]),
    ("Biltong", "Air-dried spiced meat of the trekking life", ["beef", "vinegar", "spices"], ["Voortrekker preservation"], ["resourcefulness", "heritage"]),
    ("Bobotie", "A spiced baked mince of Cape Malay heritage", ["beef", "curry", "egg"], ["Cape Malay-Dutch fusion"], ["fusion", "comfort"]),
    ("Bunny Chow", "A hollowed loaf filled with curry, born in Durban", ["bread", "curry"], ["Indian migration"], ["ingenuity", "street life"]),
    ("Bibimbap", "A harmonious bowl of colorful balance", ["rice", "vegetables", "egg"], ["Korean royal & folk cuisine"], ["harmony", "balance"]),
    ("Bulgogi", "Marinated grilled beef shared at the table", ["beef", "soy", "pear"], ["Korean barbecue tradition"], ["conviviality", "celebration"]),
    ("Kimchi", "Fermented vegetables at the soul of every meal", ["cabbage", "chili", "garlic"], ["Columbian exchange (chili)"], ["patience", "identity"]),
    ("Tteokbokki", "Chewy rice cakes in a fiery street sauce", ["rice cake", "gochujang"], ["Korean street food"], ["comfort", "street life"]),
    ("Gazpacho", "A chilled tomato soup of Andalusian summers", ["tomato", "pepper", "olive oil"], ["Columbian exchange (tomato)"], ["freshness", "thrift"]),
    ("Paella", "The saffron rice that gathers a crowd", ["rice", "saffron", "seafood"], ["Moorish rice & spice"], ["conviviality", "celebration"]),
    ("Tapas", "Small plates that turn eating into socializing", ["olive oil", "bread"], ["Spanish tavern culture"], ["conviviality", "sharing"]),
    ("Cinnamon Bun", "The spiral pastry at the heart of fika", ["wheat", "cinnamon", "cardamom"], ["spice trade"], ["comfort", "ritual"]),
    ("Gravlax", "Cured salmon, a Nordic art of preservation", ["salmon", "dill", "salt"], ["Nordic preservation"], ["craft", "heritage"]),
    ("Swedish Meatballs", "Cozy meatballs of the family table", ["beef", "cream", "lingonberry"], ["18th-century Ottoman influence"], ["comfort", "home"]),
    ("Kebab", "Grilled-meat mastery spanning an empire", ["meat", "spices"], ["Ottoman & Silk Road"], ["conviviality", "craft"]),
    ("Meze", "A spread of small plates made for lingering", ["olive oil", "bread"], ["Ottoman-Levantine"], ["sharing", "hospitality"]),
    ("Turkish Coffee", "Thick coffee poured with fortune and friendship", ["coffee"], ["Ottoman coffeehouse culture"], ["ritual", "hospitality"]),
    ("Fish and Chips", "The seaside comfort of a nation", ["cod", "potato"], ["North Sea fishing & Columbian (potato)"], ["comfort", "nostalgia"]),
    ("Roast Beef", "The Sunday roast at the family table", ["beef", "potato"], ["British agrarian tradition"], ["family", "tradition"]),
    ("Scones", "Teatime crumbs of the afternoon ritual", ["wheat", "cream", "jam"], ["British tea culture"], ["ritual", "comfort"]),
    ("Shepherd's Pie", "Humble minced lamb under mashed potato", ["lamb", "potato"], ["British-Irish origin"], ["thrift", "comfort"]),
]


def append_to_csv() -> None:
    existing = set()
    with CSV_PATH.open() as f:
        for row in csv.DictReader(f):
            existing.add(row["dish"])
    new = [e for e in ENTRIES if e[0] not in existing]
    if not new:
        print("CSV already up to date.")
        return
    with CSV_PATH.open("a", newline="") as f:
        w = csv.writer(f)
        for dish, sym, ing, routes, vals in new:
            w.writerow([dish, sym, "|".join(ing), "|".join(routes), "|".join(vals)])
    print(f"Appended {len(new)} rows to {CSV_PATH.name}.")


def insert_into_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    name_to_ids: dict[str, list[int]] = {}
    for did, name in cur.execute("SELECT dish_id, name FROM dish").fetchall():
        name_to_ids.setdefault(name, []).append(did)
    have = {r[0] for r in cur.execute("SELECT dish_id FROM dinner_symbolism").fetchall()}

    inserted = 0
    for dish, sym, ing, routes, vals in ENTRIES:
        for did in name_to_ids.get(dish, []):
            if did in have:
                continue
            cur.execute(
                "INSERT INTO dinner_symbolism (dish_id, symbolism, connecting_ingredients, "
                "trade_routes, cultural_values) VALUES (?,?,?,?,?)",
                (did, sym, json.dumps(ing), json.dumps(routes), json.dumps(vals)),
            )
            have.add(did)
            inserted += 1
    conn.commit()
    total = cur.execute("SELECT COUNT(*) FROM dinner_symbolism").fetchone()[0]
    conn.close()
    print(f"Inserted {inserted} symbolism rows into plates.db (total now {total}).")


if __name__ == "__main__":
    append_to_csv()
    insert_into_db()
