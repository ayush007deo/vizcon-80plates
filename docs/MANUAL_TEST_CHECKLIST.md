# Manual Interaction Checklist

Automated tests (Streamlit AppTest) cover rendering, navigation, empty states,
placeholders, citations, and insights. A few interactions depend on the live browser
(hover, click-on-map, animation playback) and are verified by hand using this list.

Run the app:

```bash
brew services start postgresql@16   # if not already running
python -m pipeline.run_pipeline      # ensure the database is populated
streamlit run app.py
```

## Checklist (mapped to requirements)

### Home — animated globe (Req 2)
- [ ] Hero title and "Food is more than nutrition" intro are visible.
- [ ] Press "Spin the globe" — the globe rotates. (Req 2.6)
- [ ] Hover a country — it highlights; move away — it returns to normal. (Req 2.7, 2.8)
- [ ] "Start Exploring" navigates to the Explore Map. (Req 2.4)

### Explore Map — click to select (Req 3)
- [ ] Countries with a story are colored; others are greyed. (Req 3.1)
- [ ] Click a highlighted country — it opens that Country Story. (Req 3.2)
- [ ] Click a greyed region — an inline "no story" message appears; map stays. (Req 3.3)
- [ ] Hover a country — tooltip lists its region and bordering countries. (Req 3.4)

### Country Story → Plate (Req 4, 5)
- [ ] Cards show staples, dishes, festivals, heritage, life expectancy, nutrition, tourists.
- [ ] Missing fields show "Not available". (Req 4.3)
- [ ] "See What's on the Plate" opens the plate; segments are labeled with %. (Req 5.2)

### Migration & Spice — animated routes (Req 7, 8)
- [ ] Choose an ingredient/spice, press "Trace the journey" — the traveler hops the route. (Req 7.2, 8.2)
- [ ] The step-by-step trail lists stops with time periods. (Req 7.4, 8.3)
- [ ] A "Did you know?" insight appears and changes with the selection. (Req 17.2)

### Festivals (Req 9)
- [ ] Move the month slider — the highlighted bar and country list update. (Req 9.2)
- [ ] A month with no festivals shows the empty-state message. (Req 9.5)

### Health bubble (Req 10)
- [ ] Bubbles are sized by population and colored by region with a legend. (Req 10.2, 10.3)
- [ ] Hover shows country, region, vegetable supply, life expectancy, population. (Req 10.4)

### Flavor Wheel — circle packing (Req 11)
- [ ] Cluster circles enclose one labeled circle per country. (Req 11.2)
- [ ] Hover a country circle shows its cluster name. (Req 11.5)

### Taste Passport, Dish Search, Insights, Dinner Party (Req 12-15, 17)
- [ ] Select tastes — up to 10 ranked countries under "Your Culinary Passport". (Req 12)
- [ ] Search a dish (e.g., "sushi") — matching dishes and countries appear. (Req 13)
- [ ] Insights shows a data-derived "Did you know?" and aggregate cards. (Req 14, 17.2)
- [ ] "Set a new table" reshuffles the dinner; each course is a different country. (Req 15)

### Cross-cutting (Req 18, 19, 20)
- [ ] Each data section shows a "Sources:" line; Sources & Credits lists all sources. (Req 19)
- [ ] Colors, fonts, and spacing are consistent; text is readable (contrast). (Req 18.1, 20.1)
- [ ] Region colors are consistent across Health, Globe, and Explore Map. (Req 20.3)
