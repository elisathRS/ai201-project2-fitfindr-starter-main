"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import re

from dotenv import load_dotenv
from groq import Groq
from groq.types.chat import ChatCompletion

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.
    """

    def _normalize(text: str) -> str:
        return (text or "").strip().lower()

    def _tokens(text: str) -> list[str]:
        return [token for token in re.split(r"\W+", _normalize(text)) if token]

    def _size_matches(listing_size: str, desired_size: str) -> bool:
        listing_text = _normalize(listing_size)
        desired_text = _normalize(desired_size)
        if not listing_text or not desired_text:
            return False
        if desired_text in listing_text:
            return True
        if listing_text in desired_text:
            return True
        return False

    keywords = _tokens(description)
    if not keywords:
        return []

    results: list[tuple[int, dict]] = []
    for listing in load_listings():
        if max_price is not None and listing.get("price", float("inf")) > max_price:
            continue

        if size and not _size_matches(listing.get("size", ""), size):
            continue

        title = _normalize(listing.get("title", ""))
        desc = _normalize(listing.get("description", ""))
        category = _normalize(listing.get("category", ""))
        brand = _normalize(listing.get("brand", ""))
        style_tags = [tag.lower() for tag in listing.get("style_tags", []) if isinstance(tag, str)]
        colors = [color.lower() for color in listing.get("colors", []) if isinstance(color, str)]

        score = 0
        for keyword in keywords:
            if keyword in title:
                score += 3
            if keyword in desc:
                score += 2
            if keyword in category:
                score += 2
            if keyword in brand:
                score += 2
            if any(keyword in tag for tag in style_tags):
                score += 2
            if any(keyword in color for color in colors):
                score += 1

        if score <= 0:
            continue

        results.append((score, listing))

    results.sort(key=lambda pair: (-pair[0], pair[1].get("price", float("inf"))))
    return [listing for _, listing in results]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def _call_groq_chat(
    messages: list[dict[str, str]],
    temperature: float = 0.9,
    max_completion_tokens: int = 350,
    model: str = "llama-3.3-70b-versatile",
) -> str:
    client = _get_groq_client()
    response = client.chat.completions.create(
        messages=messages,
        model=model,
        temperature=temperature,
        top_p=0.95,
        max_completion_tokens=max_completion_tokens,
    )
    if not response.choices:
        return ""
    choice = response.choices[0]
    if choice.message.content:
        return choice.message.content.strip()
    if choice.message.tool_calls:
        arguments = [call.arguments for call in choice.message.tool_calls if call.arguments]
        return "\n".join(arguments).strip()
    return ""


def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.
    """
    wardrobe_items = wardrobe.get("items") if isinstance(wardrobe, dict) else None
    has_wardrobe = bool(wardrobe_items)

    title = new_item.get("title", "this item")
    category = new_item.get("category", "item")
    colors = ", ".join(new_item.get("colors", []))
    style_tags = ", ".join(new_item.get("style_tags", []))
    price = new_item.get("price")
    platform = new_item.get("platform", "a resale platform")

    item_description = (
        f"{title}, a {category} from {platform}"
        f" priced at ${price:.2f}" if isinstance(price, (int, float)) else f"{title} from {platform}"
    )
    item_description += f" with colors {colors}" if colors else ""
    item_description += f" and style tags {style_tags}" if style_tags else ""

    if not has_wardrobe:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful, fashion-forward styling assistant. "
                    "Offer friendly, practical advice for outfit ideas and styling vibes."
                ),
            },
            {
                "role": "user",
                "content": (
                    "The user's wardrobe is empty. "
                    f"Give general styling advice for a new thrifted item: {item_description}. "
                    "Recommend 1-2 directions the user could try, including type of bottoms, shoes, or layers. "
                    "Keep the answer casual, specific, and easy to imagine."
                ),
            },
        ]
    else:
        wardrobe_lines = []
        for item in wardrobe_items:
            name = item.get("name", "Unnamed piece")
            category = item.get("category", "unknown")
            colors = ", ".join(item.get("colors", []))
            tags = ", ".join(item.get("style_tags", []))
            wardrobe_lines.append(
                f"- {name} ({category}; colors: {colors or 'unknown'}; tags: {tags or 'none'})"
            )
        wardrobe_text = "\n".join(wardrobe_lines)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a thoughtful styling assistant who can match a new thrifted item "
                    "to a user's existing wardrobe. Suggest real looks using named pieces."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Suggest 1-2 complete outfit ideas that pair the new item with the user's wardrobe. "
                    f"The new item is {item_description}. "
                    "The user's wardrobe contains these pieces:\n"
                    f"{wardrobe_text}\n"
                    "Recommend specific pairings, mention the named wardrobe items, and describe how to style them together. "
                    "Keep the tone casual and inspiring."
                ),
            },
        ]

    return _call_groq_chat(messages, temperature=0.95, max_completion_tokens=300)


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.
    """
    if not outfit or not outfit.strip():
        return (
            "I need a valid outfit suggestion to create a fit card. "
            "Please try again with a completed styling recommendation."
        )

    title = new_item.get("title", "this item")
    price = new_item.get("price")
    platform = new_item.get("platform", "a resale platform")

    item_line = f"{title} from {platform}"
    if isinstance(price, (int, float)):
        item_line += f" for ${price:.2f}"

    messages = [
        {
            "role": "system",
            "content": (
                "You are a creative, relatable fashion caption writer. "
                "Write short, authentic social captions that sound like a real OOTD post."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Write a 2-to-4 sentence caption for a thrifted find. "
                f"The item is {item_line}. "
                "The outfit suggestion is: "
                f"{outfit}\n"
                "Mention the item name, price, and platform once each, and capture the look's vibe. "
                "Use a casual, slightly playful voice."
            ),
        },
    ]

    caption = _call_groq_chat(
        messages,
        temperature=1.2,
        max_completion_tokens=200,
        model="llama-3.3-70b-versatile",
    )
    return caption or (
        "I couldn't create a fit card from that outfit. "
        "Please try again with a different outfit suggestion."
    )
