"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from tools import search_listings, suggest_outfit, create_fit_card


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def _parse_query(query: str) -> dict:
    """Extract description, size, and max_price from a user query."""
    text = query.strip()
    parsed = {
        "description": text,
        "size": None,
        "max_price": None,
    }

    size_match = re.search(r"\bsize\s*([XSML]{1,3}(?:/[XSML]{1,3})?)\b", text, flags=re.I)
    if size_match:
        parsed["size"] = size_match.group(1).upper()

    price_match = re.search(
        r"\b(?:under|below|less than|up to|maximum price of|max(?:imum)? price(?: of)?)\s*\$?(\d+(?:\.\d+)?)\b",
        text,
        flags=re.I,
    )
    if price_match:
        parsed["max_price"] = float(price_match.group(1))

    description = text
    description = re.sub(r"\bsize\s*[XSML]{1,3}(?:/[XSML]{1,3})?\b", "", description, flags=re.I)
    description = re.sub(
        r"\b(?:under|below|less than|up to|maximum price of|max(?:imum)? price(?: of)?)\s*\$?\s*\d+(?:\.\d+)?\b",
        "",
        description,
        flags=re.I,
    )
    description = re.sub(r"\b(?:i\s*am|i'm|im|looking for|searching for|find me|find|want|need)\b", "", description, flags=re.I)
    description = re.sub(r"[\.,]", "", description)
    description = " ".join(description.split()).strip()
    parsed["description"] = description or text
    return parsed


def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.
    """
    session = _new_session(query, wardrobe)

    parsed = _parse_query(query)
    session["parsed"] = parsed

    search_results = search_listings(
        parsed["description"],
        size=parsed["size"],
        max_price=parsed["max_price"],
    )
    session["search_results"] = search_results

    if not search_results:
        session["error"] = (
            "I couldn't find any listings matching that query. "
            "Try broader keywords, a higher budget, or removing the size filter."
        )
        return session

    session["selected_item"] = search_results[0]

    outfit_suggestion = suggest_outfit(session["selected_item"], wardrobe)
    session["outfit_suggestion"] = outfit_suggestion

    if not outfit_suggestion or not outfit_suggestion.strip():
        session["error"] = (
            "I couldn't generate a styling suggestion for the selected item. "
            "Please try a different search or update your wardrobe."
        )
        return session

    session["fit_card"] = create_fit_card(outfit_suggestion, session["selected_item"])
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
