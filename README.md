# FitFindr

An AI-powered thrift shopping assistant that takes a natural language query, searches a dataset of secondhand listings, and generates an outfit suggestion plus a shareable fit-card caption — all in a single interaction.

---

## Setup

```bash
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

Run the Gradio app:
```bash
python app.py
```

Run the CLI demo (shows both happy path and failure path):
```bash
python agent.py
```

Run tests:
```bash
pytest tests/
```

---

## Tool Inventory

FitFindr uses three tools called in sequence. Each tool is a standalone function in [tools.py](tools.py).

### Tool 1 — `search_listings`

**Purpose:** Searches the mock secondhand listings dataset for items matching a description, filtered by optional size and price ceiling, and ranked by keyword relevance.

**Inputs:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `description` | `str` | Yes | Keywords describing the item (e.g. `"vintage graphic tee"`) |
| `size` | `str \| None` | No | Size filter; case-insensitive, supports partial match (`"M"` matches `"S/M"`). Default: `None` |
| `max_price` | `float \| None` | No | Maximum price ceiling, inclusive. Default: `None` |

**Returns:** A `list[dict]` of matching listings sorted by relevance score (highest first). Each dict contains: `id`, `title`, `description`, `category`, `style_tags` (list of str), `size`, `condition`, `price` (float), `colors` (list of str), `brand`, `platform`. Returns `[]` if nothing matches.

---

### Tool 2 — `suggest_outfit`

**Purpose:** Uses an LLM to generate 1–2 complete outfit suggestions pairing the thrifted item with pieces from the user's existing wardrobe.

**Inputs:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `new_item` | `dict` | Yes | A listing dict returned by `search_listings` |
| `wardrobe` | `dict` | Yes | Dict with an `'items'` key mapping to a list of wardrobe item dicts (may be empty) |

**Returns:** A non-empty `str` with 1–2 outfit suggestions. If `wardrobe['items']` is empty, returns general styling advice and pairing ideas instead of wardrobe-specific recommendations. Never returns an empty string or raises an exception.

---

### Tool 3 — `create_fit_card`

**Purpose:** Generates a 2–4 sentence social-media-style OOTD caption for the thrifted find.

**Inputs:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `outfit` | `str` | Yes | The outfit suggestion returned by `suggest_outfit` |
| `new_item` | `dict` | Yes | The listing dict for the thrifted item |

**Returns:** A `str` caption that mentions the item name, price, and platform exactly once each, in a casual voice. If `outfit` is empty or whitespace, returns a descriptive error message string (e.g. `"I need a valid outfit suggestion..."`) without calling the LLM. Never raises an exception.

---

## Planning Loop

The agent in [agent.py](agent.py) uses a sequential, guard-clause-driven loop — not a free-form reactive loop. Each step checks the previous result before proceeding.

**Step-by-step conditional logic:**

1. **Parse query** — `_parse_query()` extracts `description`, `size`, and `max_price` from the raw user string using regex. These become `session["parsed"]`.

2. **Search** — calls `search_listings(description, size, max_price)`. Stores the result list in `session["search_results"]`.
   - **If the list is empty:** sets `session["error"]` to a specific message ("Try broader keywords, a higher budget, or removing the size filter") and **returns immediately**. `suggest_outfit` and `create_fit_card` are never called.
   - **If the list is non-empty:** sets `session["selected_item"] = results[0]` and continues.

3. **Outfit** — calls `suggest_outfit(selected_item, wardrobe)`. Stores the result in `session["outfit_suggestion"]`.
   - **If the result is empty or whitespace:** sets `session["error"]` and **returns immediately**. `create_fit_card` is never called.
   - **If the result is a non-empty string:** continues.

4. **Fit card** — calls `create_fit_card(outfit_suggestion, selected_item)`. Stores the result in `session["fit_card"]` and returns the full session.

The agent never calls all three tools unconditionally. The `search_listings` empty-result path and the `suggest_outfit` empty-string path each cause early termination without calling the downstream tools.

---

## State Management

All intermediate values live in a single `session` dict initialized by `_new_session()` in [agent.py](agent.py). No data is re-entered by the user between tool calls.

| Session key | Set after | Passed into |
|-------------|-----------|-------------|
| `session["parsed"]` | `_parse_query()` | Arguments to `search_listings` |
| `session["search_results"]` | `search_listings` returns | Guards next step; source of `selected_item` |
| `session["selected_item"]` | `results[0]` selected | `suggest_outfit` (arg 1) and `create_fit_card` (arg 2) |
| `session["outfit_suggestion"]` | `suggest_outfit` returns | Guards next step; passed to `create_fit_card` (arg 1) |
| `session["fit_card"]` | `create_fit_card` returns | Returned to the UI |
| `session["error"]` | On any early exit | Signals failure; UI shows this instead of tool outputs |

`selected_item` is set once from `search_results[0]` and reused in both downstream tools without the user re-entering it. `outfit_suggestion` passes directly into `create_fit_card` the same way.

---

## Error Handling

| Tool | Failure mode | What the agent does |
|------|-------------|---------------------|
| `search_listings` | Returns `[]` — no listings match the description, size, or price | Sets `session["error"]`: *"I couldn't find any listings matching that query. Try broader keywords, a higher budget, or removing the size filter."* Returns immediately; `suggest_outfit` and `create_fit_card` are never called. |
| `suggest_outfit` | LLM returns an empty string (API failure or token issue) | Sets `session["error"]`: *"I couldn't generate a styling suggestion for the selected item. Please try a different search or update your wardrobe."* Returns immediately; `create_fit_card` is never called. |
| `create_fit_card` | `outfit` argument is empty or whitespace (upstream failure reached this point) | Guard clause fires before the LLM call; returns the string *"I need a valid outfit suggestion to create a fit card. Please try again with a completed styling recommendation."* Never raises an exception. |

**Concrete examples from testing:**

- `test_search_empty_results` passes `search_listings("designer ballgown", size="XXS", max_price=5)` and asserts the return is `[]`. Running `python agent.py` also deliberately calls `run_agent("designer ballgown size XXS under $5", ...)` and prints the error message.
- `test_create_fit_card_empty_outfit_returns_error` passes `create_fit_card("", new_item)` directly and asserts the guard-clause error string is returned. This is a real failure trigger — not a happy-path edge case.

---

## Spec Reflection

**One way the spec helped:** Writing the error handling table in planning.md before any code was written forced an explicit decision about what each failure mode should do and in what order. For `search_listings`, the spec said "stop and return immediately" — this became the `if not search_results: session["error"] = ...; return session` guard in `run_agent()`. Without the spec, that early exit could easily have been left implicit or handled only in the UI layer.

**One divergence:** The planning.md listed `suggest_outfit`'s failure mode as "wardrobe is empty." In practice, an empty wardrobe is not actually a failure — the tool handles it gracefully by switching to general styling advice. The real failure mode is when the LLM itself returns an empty string (API issue). The code ends up handling both, but the spec conflated "edge case" with "failure," which required refining the distinction during implementation. The guard in the agent loop (`if not outfit_suggestion or not outfit_suggestion.strip()`) targets the true failure (empty LLM response), not the wardrobe edge case.

---

## AI Usage Transparency

### Instance 1 — Implementing `search_listings`

I gave Claude the Tool 1 spec from planning.md (inputs with types, return value description, and the failure behavior) and asked it to implement the function using `load_listings()` from `utils/data_loader.py`, with keyword scoring and relevance sorting.

The generated code scored all keyword matches equally (each hit = 1 point). I revised the scoring weights after testing showed that a listing with "vintage" buried in a long description ranked the same as one with "vintage" in the title. I changed the weights to title=3, description=2, category=2, brand=2, style_tags=2, colors=1. I also added a secondary sort by price (`results.sort(key=lambda pair: (-pair[0], pair[1].get("price", float("inf"))))`) to break ties predictably — the AI-generated version only sorted by score and had non-deterministic ordering among equal-score results.

### Instance 2 — Implementing the planning loop in `agent.py`

I gave Claude the Planning Loop, State Management, and Architecture sections from planning.md and asked it to implement `run_agent()` with the session dict and sequential guard-clause structure shown in the Mermaid diagram.

The generated code had the session dict and sequential tool calls but was missing the empty-string check on `outfit_suggestion` — it called `create_fit_card` regardless of whether the LLM had returned anything. I added the guard (`if not outfit_suggestion or not outfit_suggestion.strip(): session["error"] = ...; return session`) after a test run where `suggest_outfit` returned an empty string (Groq API timeout) and `create_fit_card` was silently called with `""`, returning its own error string. The agent had no way to distinguish "create_fit_card failed" from "suggest_outfit failed" without the upstream guard. I also moved `wardrobe` into the session dict via `_new_session()` rather than passing it as a bare local, to keep the state management consistent with the spec.

---

## Project Structure

```
fitfindr/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # load_listings(), get_example_wardrobe(), get_empty_wardrobe()
├── tools.py                   # search_listings, suggest_outfit, create_fit_card
├── agent.py                   # run_agent() — planning loop and state management
├── app.py                     # Gradio UI
├── tests/
│   └── test_tools.py          # Unit tests for all three tools
└── planning.md                # Spec, architecture diagram, AI tool plan
```
