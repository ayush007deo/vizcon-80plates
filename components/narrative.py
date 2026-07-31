"""Narrative sentences and data-derived discovery insights (Req 1.4, 17.2-17.4).

NARRATIVES gives each section a complete opening sentence (not a label). insight()
computes a Discovery_Insight from the Data_Store for the storytelling sections, so
insights change with the data rather than being fixed prose.
"""
from __future__ import annotations

# One complete sentence per section (subject + verb), never just a label (Req 1.4).
NARRATIVES: dict[str, str] = {
    "home": "Food is more than nutrition; it is the story of how the world lives, celebrates, and connects.",
    "explore_map": "Every country on this map holds a plate waiting to tell its story.",
    "country_story": "Geography decides what grows, and culture decides what it becomes.",
    "journeys": "The ingredients we call our own were once travelers from far away.",
    "traditions": "Every celebration sets a table, and every monument remembers a meal.",
    "travel": "The world's kitchens are also its destinations — follow where hunger and wanderlust meet.",
    "bigpicture": "Step back, and the world's plates reveal patterns no single meal could.",
    "plate": "Look closely at a plate and you can read a whole nation's landscape.",
    "similarity": "Two distant kitchens often share more than they know.",
    "migration": "The ingredients we call our own were once travelers from far away.",
    "spice_journey": "A single spice could redraw trade routes and reshape empires.",
    "spice_map": "Centuries after the spice trade, the world still seasons its food very unevenly.",
    "happiness": "Some of the world's happiest nations also set some of its most celebrated tables.",
    "festivals": "Around the world, the calendar is seasoned with celebration.",
    "heritage": "Some travelers follow aromas; others follow monuments — and every stone remembers a tradition.",
    "health": "The healthiest plate is not always the richest one.",
    "flavor_wheel": "Cuisines cluster by taste, not by the borders drawn on maps.",
    "taste_passport": "Tell us what you crave, and the world will suggest where to wander.",
    "dish_search": "Search for a dish and discover where it feels at home.",
    "insights": "Step back, and the world's plates reveal patterns no single meal could.",
    "dinner_party": "Tonight, five strangers from five nations share one table.",
    "food_travel": "We travel on our stomachs — the world's great cuisines are also its great destinations.",
    "sources": "Every story here rests on data you can trace and trust.",
}


def narrative(section: str) -> str:
    return NARRATIVES.get(section, "This chapter of the journey is being written.")


def insight(section: str, **context) -> str | None:
    """Return a data-derived Discovery_Insight for a storytelling section, or None.

    Reads from the repository; failures degrade to None so a view never breaks.
    """
    try:
        from data import repository as repo

        if section == "migration":
            ingredients = repo.list_migration_ingredients()
            if not ingredients:
                return None
            ing = context.get("ingredient") or ingredients[0]
            steps = repo.get_migration_story(ing)
            if steps.empty:
                return None
            periods = [p for p in steps["time_period"].tolist() if p]
            return (
                f"{ing} traveled through {len(steps)} places"
                + (f", from {periods[0]} to {periods[-1]}," if len(periods) >= 2 else "")
                + " before it reached kitchens worldwide."
            )

        if section == "spice_journey":
            spices = repo.list_spices()
            spice = context.get("spice") or (spices[0] if spices else None)
            if not spice:
                return None
            steps = repo.get_spice_route(spice)
            if steps.empty:
                return None
            periods = [p for p in steps["time_period"].tolist() if p]
            span = f" spanning {periods[0]} to {periods[-1]}" if len(periods) >= 2 else ""
            return f"{spice} crossed {len(steps)} regions on a journey{span}."

        if section == "heritage":
            pts = repo.heritage_tourism_points()
            if pts.empty:
                return None
            top = pts.sort_values("heritage", ascending=False).iloc[0]
            corr = pts["heritage"].corr(pts["annual_tourists"]) if len(pts) >= 5 else None
            lead = f"{top['name']} guards {int(top['heritage'])} World Heritage sites"
            if corr is not None and corr == corr:  # not NaN
                tail = (
                    f", and across {len(pts)} countries, more heritage tends to mean more "
                    f"tourism (correlation {corr:+.2f})."
                )
            else:
                tail = "."
            return lead + tail

        if section == "insights":
            data = repo.get_insights()
            if not data or data.get("country_count", 0) == 0:
                return None
            avg = data.get("avg_life_expectancy")
            n = data.get("country_count")
            if avg is not None:
                return (
                    f"Across {n} countries with data, average life expectancy is "
                    f"{float(avg):.1f} years."
                )
            return f"This journey draws on data from {n} countries."

        if section == "spice_map":
            from data import spice_data as sp

            year = sp.latest_year()
            top = sp.top_consumers(year, limit=1)
            brk = sp.spice_breakdown(year)
            if top.empty or brk.empty:
                return None
            lead = top.iloc[0]
            named = brk[brk["item"] != "Other spices"]
            spice = named.iloc[0]["item"] if not named.empty else brk.iloc[0]["item"]
            return (
                f"In {year}, {lead['name']} consumed more spice than any other country "
                f"— and of the world's named spices, {spice.lower()} lead what we season with."
            )

        if section == "happiness":
            from data import wellbeing_data as wb

            df = wb.happiness()
            if df.empty:
                return None
            year = wb.latest_year()
            top = df.sort_values("score", ascending=False).iloc[0]
            corr = (df["life_exp"].corr(df["score"])
                    if df["life_exp"].notna().sum() >= 5 else None)
            lead = f"In {year}, {top['country']} tops the world happiness ranking ({top['score']:.2f}/10)"
            if corr is not None and corr == corr:
                return (lead + f", and across {len(df)} countries, longer healthy lives track "
                        f"with greater happiness (correlation {corr:+.2f}).")
            return lead + "."

        if section == "travel":
            from data import tourism_data as td

            c = td.covid_impact()
            crash = c.get("crash_pct")
            if crash is None:
                return None
            arr = c.get("arrivals", {})
            peak, trough = c.get("peak_year"), c.get("trough_year")
            p = arr.get(peak)
            t = arr.get(trough)

            def _b(n):
                return f"{n / 1e9:.1f} billion" if n and n >= 1e9 else f"{n / 1e6:.0f} million"

            return (
                f"In a single year, global tourist arrivals fell {abs(crash):.0f}% — from "
                f"{_b(p)} in {peak} to {_b(t)} in {trough} — the steepest collapse in the "
                "history of modern travel."
            )

        if section == "food_travel":
            cmp = repo.food_travel_comparison()
            w, wo = cmp.get("with"), cmp.get("without")
            if not w or not wo:
                return None
            aw, awo = w.get("avg_tourists"), wo.get("avg_tourists")
            if aw and awo and awo > 0:
                ratio = aw / awo
                return (
                    f"Countries whose food traditions are recognized by UNESCO draw about "
                    f"{ratio:.1f}× as many visitors on average as those without — "
                    "a living cuisine is a magnet for travelers."
                )
            rw, rwo = w.get("avg_receipts"), wo.get("avg_receipts")
            if rw and rwo and rwo > 0:
                return (
                    f"Countries with UNESCO-recognized food traditions earn about "
                    f"{rw / rwo:.1f}× more in tourism on average than those without."
                )
            return None

        if section == "dinner_party":
            countries = context.get("countries") or []
            if not countries:
                return None
            return (
                f"Tonight's table connects {len(countries)} nations — "
                "trace the shared ingredients and trade routes between their dishes."
            )
    except Exception:  # noqa: BLE001 - insights must never break a view
        return None
    return None
