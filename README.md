# Sentinel Sync

A predictive command center for managing high-stakes job application pipelines:
priority ranking, collision-free interview scheduling, and AI-generated follow-up
assets — all in one dark-themed Streamlit dashboard.

## Setup

```bash
pip install -r requirements.txt
```

## Enabling live AI generation (optional)

Sentinel Sync runs fully functional out of the box using a deterministic offline
fallback engine, so you can explore every feature with zero configuration.

To enable live LLM-powered parsing and message generation, set an API key before
launching:

```bash
export OPENAI_API_KEY="sk-..."
```

To point at a Gemini (or any other OpenAI-compatible) endpoint instead, also set:

```bash
export SENTINEL_LLM_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"
export SENTINEL_LLM_MODEL="gemini-2.0-flash"
```

## Run

```bash
streamlit run app.py
```

The app opens with 8 pre-loaded sample applications so the dashboard is
immediately populated and visually complete.

## Project structure

| File              | Purpose                                                          |
|-------------------|--------------------------------------------------------------------|
| `app.py`          | Streamlit UI — Pipeline Dashboard, Ingestion Hub, Schedule Engine |
| `models.py`       | `Application` data schema, pipeline stage enum, badge colors     |
| `priority.py`     | Dynamic Priority Score sorting and portfolio metrics             |
| `scheduler.py`    | 2-hour collision detection and next-available-slot suggestion    |
| `llm_engine.py`   | LLM prompt templates + offline deterministic fallback            |
| `currency.py`     | Multi-currency normalization, FX conversion, and display formatting |
| `sample_data.py`  | Pre-loaded mock pipeline for first launch                        |

## Core mechanics

- **Multi-currency support**: each application stores its own native currency
  (USD, INR, EUR, GBP, AED, SGD, AUD, CAD). Ingestion (both the live LLM parser
  and the offline fallback) detects the currency directly from the pasted text
  — a posting quoting "16 LPA" or "₹18,00,000" stays in INR; it is never
  silently converted to USD. Use the **"Display package as"** dropdown in the
  sidebar to view every figure in a different unit (native currency, USD,
  INR, INR/LPA, EUR, or GBP) without altering the underlying stored data.
  Ranking math (Dynamic Priority Score, average package) always normalizes to
  a USD-equivalent value first so offers in different currencies compare
  fairly — this is a nominal compensation comparison, not cost-of-living
  adjusted. You can correct an application's detected currency or amount any
  time from its "Manage & take action" panel.
- **Dynamic Priority Score** = USD-equivalent Package Value × Approval
  Probability. The dashboard force-sorts on this value, so high-value,
  high-probability roles bubble to the top regardless of currency.
- **Scheduling Collision Detection**: any two interviews scheduled within a
  2-hour window trigger a warning banner with a suggested next-available
  business-hours slot.
- **Last-Mile Execution Engine** triggers contextually:
  - `Technical Interview` stage → 30-Minute Blitz Prep Sheet
  - Ghosted / >5 days cold → platform-tuned follow-up message (LinkedIn / WhatsApp / Gmail)
  - Mid-stage application while another has an `Offer` → counter-offer leverage email
- All generated text renders in a code block with Streamlit's built-in copy-to-clipboard icon.
- Each company's card has a stable, distinct background tint and accent
  border (hashed from the company name) so entries are easy to tell apart at
  a glance, beyond just the divider line.
- Navigation is a centered, evenly-spaced tab bar at the top of the page
  rather than a sidebar radio list.
- Use the **Save / Load** buttons in the sidebar to persist your pipeline to
  `sentinel_data.json` between sessions.
