"""Curated 'Did You Know?' stories and journey summaries for the Food Voyage.

Common-knowledge culinary history (not fabricated statistics), keyed by subject and
stop name. Missing entries fall back to the era label, so any route still renders.
"""
from __future__ import annotations

# subject (lower) -> stop location_name -> a short, memorable story line.
STOP_FACTS: dict[str, dict[str, str]] = {
    "potato": {
        "Andes (Peru)": "Domesticated in the Andes over 7,000 years ago — Inca farmers grew thousands of varieties.",
        "Spain": "Spanish ships carried the potato to Europe in the 1500s, where people first thought it was poisonous.",
        "Ireland": "It became Ireland's staple — until the 1840s blight caused the Great Famine.",
        "India": "Today India is one of the world's largest potato producers.",
        "Global": "Now grown on every inhabited continent and eaten in 160+ countries.",
    },
    "tomato": {
        "Andes (Peru)": "The wild tomato began as a tiny berry in the Andes.",
        "Mexico": "Aztecs cultivated it and gave us the word 'tomatl'.",
        "Spain": "Conquistadors brought it to Europe in the 1540s.",
        "Italy": "Italians were slow to trust it, but it became the soul of their cuisine.",
        "India": "Now a backbone of curries and chutneys across South Asia.",
        "Global": "Today the world grows over 180 million tonnes of tomatoes a year.",
    },
    "chili pepper": {
        "Bolivia": "Chili peppers were first tamed in the Bolivia–Peru highlands.",
        "Mexico": "Central America made chili the heart of its cooking millennia ago.",
        "Portugal": "Portuguese traders spread it along their sea routes in the 1500s.",
        "India": "Within decades it redefined Indian cuisine — there was no 'spicy' curry before it.",
        "Thailand": "It became inseparable from Thai food in barely a century.",
        "China (Sichuan)": "Sichuan cooking embraced the chili so fully it now defines the region.",
    },
    "coffee": {
        "Ethiopia": "Legend says an Ethiopian goatherd noticed his goats dancing after eating the berries.",
        "Yemen": "Sufi monks in Yemen brewed the first cups to stay awake for prayer.",
        "Yemen (Mocha)": "The port of Mocha gave its name to the coffee we still drink.",
        "Turkey": "Ottoman coffee houses became 'schools of the wise'.",
        "Ottoman Empire": "Ottoman coffee houses became lively centers of conversation.",
        "Italy": "Venice opened Europe's first coffee houses in the 1600s.",
        "Vienna": "Vienna's café culture was born after the 1683 siege left sacks of coffee behind.",
        "Brazil": "Brazil now grows about a third of the world's coffee.",
    },
    "tea": {
        "Yunnan (China)": "Tea was first drunk in China's Yunnan hills thousands of years ago.",
        "Japan": "Zen monks carried it to Japan, where it became a meditative ceremony.",
        "Netherlands": "Dutch traders shipped the first tea to Europe in the 1600s.",
        "Britain": "Tea reshaped British daily life — and sparked the Boston Tea Party.",
        "Assam (India)": "The British planted vast estates in Assam, now a tea heartland.",
    },
    "black pepper": {
        "Kerala (India)": "India's Malabar Coast was the original home of 'black gold'.",
        "Arabia": "Arab merchants guarded the routes and the secret of its source.",
        "Alexandria": "Alexandria's spice markets funneled pepper into the Mediterranean.",
        "Rome": "Romans prized pepper so highly it was used to pay ransoms.",
        "Venice": "Venice grew rich as Europe's medieval pepper gateway.",
    },
    "chocolate": {
        "Mesoamerica": "The Maya and Aztecs drank cacao as a bitter, sacred beverage — and used beans as money.",
        "Spain": "Spain added sugar and kept sweet chocolate a court secret for a century.",
        "France": "It swept the French royal court as a luxury drink.",
        "Switzerland": "The Swiss invented milk chocolate and the conching that made it smooth.",
    },
    "cardamom": {
        "Western Ghats (India)": "Cardamom grew wild in India's Western Ghats — the 'queen of spices'.",
        "Persia": "Persia wove it into rice, sweets, and coffee.",
        "Scandinavia": "Vikings brought it north; it still flavors Nordic baking today.",
    },
    "sugar": {
        "New Guinea": "Sugarcane was first chewed and cultivated in New Guinea thousands of years ago.",
        "India": "India learned to crystallize cane juice — the Sanskrit 'sharkara' gives us 'sugar'.",
        "Persia": "Persian refineries turned it into a prized luxury.",
        "Egypt": "Arab and Egyptian traders spread cane and refining across the Mediterranean.",
        "Caribbean": "Colonial sugar plantations drove the transatlantic slave trade — a bitter history behind the sweetness.",
    },
    "maize": {
        "Mexico": "Maize was bred from wild teosinte by Mesoamerican farmers ~9,000 years ago.",
        "Spain": "Columbus carried it back to Spain in the 1490s.",
        "West Africa": "It quickly became a staple across West Africa.",
        "Italy": "Northern Italy turned it into polenta.",
        "China": "China is now one of the world's largest maize growers.",
    },
    "banana": {
        "Malaysia": "Bananas were first domesticated in Southeast Asia.",
        "India": "Early travelers found orchards of them across India.",
        "East Africa": "They became a African highland staple (think matoke).",
        "Caribbean": "Colonial plantations spread them through the Americas.",
        "Central America": "The 'banana republics' were named for this fruit's economic power.",
    },
    "rice": {
        "Yangtze (China)": "Rice was domesticated along China's Yangtze over 9,000 years ago.",
        "India": "India developed thousands of its own rice varieties.",
        "Persia": "It reached Persia and became the base of pilaf.",
        "Spain": "Moorish farmers planted it in Spain — the root of paella.",
        "Americas": "Enslaved West Africans' expertise built the Carolina rice economy.",
    },
    "vanilla": {
        "Mexico": "Vanilla comes from a Mexican orchid the Totonac people first cultivated.",
        "Spain": "Spain paired it with chocolate and kept it exclusive for centuries.",
        "Madagascar": "A boy's hand-pollination trick let Madagascar become the world's vanilla capital.",
    },
    "cinnamon": {
        "Sri Lanka": "True cinnamon comes from Sri Lankan tree bark — its source was kept secret for ages.",
        "Arabia": "Arab traders spun tall tales to hide where it grew and guard their monopoly.",
        "Alexandria": "It flowed through Alexandria into the Roman world as a costly luxury.",
        "Venice": "Venice's cinnamon trade helped fund its golden age.",
    },
    "nutmeg": {
        "Banda Islands": "Nutmeg grew only on Indonesia's tiny Banda Islands — worth its weight in gold.",
        "Arabia": "Arab merchants carried it west without revealing its origin.",
        "Venice": "Venice grew rich as Europe's nutmeg gateway.",
        "Netherlands": "The Dutch fought wars for a monopoly on these few islands.",
    },
}

# subject (lower) -> summary for the journey stat cards.
SUMMARY: dict[str, dict[str, str]] = {
    "potato": {"origin": "Peru", "travel": "Ocean trade", "today": "160+ countries"},
    "tomato": {"origin": "Peru", "travel": "Colonial ships", "today": "Worldwide"},
    "chili pepper": {"origin": "Bolivia", "travel": "Portuguese routes", "today": "Every cuisine"},
    "coffee": {"origin": "Ethiopia", "travel": "Red Sea & cafés", "today": "2 billion cups/day"},
    "tea": {"origin": "China", "travel": "Silk Road & sea", "today": "Most-drunk brew"},
    "black pepper": {"origin": "India", "travel": "Spice Route", "today": "The 'king of spices'"},
    "chocolate": {"origin": "Mexico", "travel": "Colonial ships", "today": "Global treat"},
    "cardamom": {"origin": "India", "travel": "Caravan & sea", "today": "Global baking & chai"},
    "sugar": {"origin": "New Guinea", "travel": "Cane & colonial trade", "today": "Everywhere"},
    "maize": {"origin": "Mexico", "travel": "Colonial ships", "today": "A world staple"},
    "banana": {"origin": "SE Asia", "travel": "Sea & plantation trade", "today": "Most-eaten fruit"},
    "rice": {"origin": "China", "travel": "Rivers, road & sea", "today": "Half the world's plates"},
    "vanilla": {"origin": "Mexico", "travel": "Colonial ships", "today": "World's favorite flavor"},
    "cinnamon": {"origin": "Sri Lanka", "travel": "Spice Route", "today": "Global pantry staple"},
    "nutmeg": {"origin": "Banda Islands", "travel": "Spice Route", "today": "Global baking spice"},
}


def stop_fact(subject: str, place: str) -> str | None:
    return STOP_FACTS.get(subject.strip().lower(), {}).get(place)


def summary(subject: str) -> dict[str, str]:
    return SUMMARY.get(subject.strip().lower(), {})
