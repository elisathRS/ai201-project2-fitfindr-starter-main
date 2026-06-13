import pytest

from tools import create_fit_card, search_listings, suggest_outfit


def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


def test_suggest_outfit_empty_wardrobe_returns_advice(monkeypatch):
    monkeypatch.setattr(
        "tools._call_groq_chat",
        lambda messages, temperature=0.95, max_completion_tokens=300, model="llama-3.3-70b-versatile":
        "This is a general styling suggestion for the new item."
    )

    new_item = {
        "title": "Vintage Graphic Tee",
        "category": "tops",
        "colors": ["black"],
        "style_tags": ["vintage", "graphic tee"],
        "price": 25.0,
        "platform": "Depop",
    }
    wardrobe = {"items": []}
    result = suggest_outfit(new_item, wardrobe)
    assert isinstance(result, str)
    assert result.strip() != ""
    assert "styling" in result.lower() or "outfit" in result.lower()


def test_create_fit_card_empty_outfit_returns_error():
    new_item = {
        "title": "Vintage Graphic Tee",
        "price": 25.0,
        "platform": "Depop",
    }
    result = create_fit_card("", new_item)
    assert isinstance(result, str)
    assert "need a valid outfit suggestion" in result.lower()
