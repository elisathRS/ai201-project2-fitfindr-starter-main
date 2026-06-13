# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**


**Input parameters:**
- `description` (str): 
- `max_price` (float): 

**What it returns:**


**What happens if it fails or returns nothing:**


---

### Tool 2: suggest_outfit

**What it does:**


**Input parameters:**
- `new_item` (dict): 
- `wardrobe` (dict): 

**What it returns:**


**What happens if it fails or returns nothing:**


---

### Tool 3: create_fit_card

**What it does:**


**Input parameters:**
- `outfit` (str or dict): 
- `new_item` (dict): 

**What it returns:**


**What happens if it fails or returns nothing:**


---

### Additional Tools (if any)

No additional tools are required for Milestone 1.

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->

---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | |
| suggest_outfit | Wardrobe is empty | |
| create_fit_card | Outfit input is missing or incomplete | |

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**

**Milestone 4 — Planning loop and state management:**

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
The agent calls `search_listings(description="vintage graphic tee", size="M", max_price=30.0)` to find matching listings in `data/listings.json`.

**Step 2:**
`search_listings` returns a ranked list of matches such as a black tour-style graphic tee, a Y2K butterfly tee, and a faded band tee. The agent selects the top result and passes it to `suggest_outfit` along with the user's wardrobe loaded from `get_example_wardrobe()`.

**Step 3:**
`suggest_outfit(new_item=<selected listing>, wardrobe=<user wardrobe>)` returns a styling recommendation like pairing the tee with baggy dark wash jeans and chunky white sneakers, plus notes on how to wear the look.

**Step 4:**
The agent calls `create_fit_card(outfit=<styling suggestion>, new_item=<selected listing>)` to generate a concise fit-card caption summarizing the new item and the outfit mood.

**Final output to user:**
The user receives a complete response: the matched listing headline and price, the outfit suggestion using their wardrobe, and a fit-card style caption. If no listings match, the agent instead tells the user to broaden the search or raise the budget and stops without suggesting an outfit.

