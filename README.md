# DealShield

Enterprise M&A due diligence platform that uses a Neo4j knowledge graph and Google Gemini AI to detect hidden conflict-of-interest rings, change-of-control clause landmines, antitrust exposures, and exclusivity traps — before a deal closes.

---

## What It Does

M&A deals fail or incur massive post-close penalties because critical risks are buried inside legal agreements and undisclosed relationships between insiders and vendors. DealShield automates the discovery of those risks by traversing a multi-hop knowledge graph across directors, related parties, suppliers, holding companies, contracts, and regulatory filings.

It surfaces four categories of material risk:

| Category | Examples |
|---|---|
| **Conflict of Interest** | Director's spouse owns the sole-source vendor via an offshore shell company; Non-Executive Director holds an undisclosed stake in a tier-2 supplier; Board attestation falsely certifies no conflicts |
| **Change of Control** | Poison-pill termination fees; mandatory post-close purchase commitments; equity-transfer thresholds that trigger automatic penalties |
| **Antitrust / Regulatory** | DoD contract auto-revocation on competitor overlap; common-parent market share cap breach |
| **Non-Compete / Exclusivity** | 84-month sole-source ASIC lock-in; SLA auto-renewal with an expired notice window; toolchain IP migration restrictions |

Each finding is scored 0–100 and classified as **CRITICAL / HIGH / MEDIUM / LOW** based on financial exposure, related-party involvement, and holding-chain depth.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Knowledge Graph | Neo4j Aura (cloud) |
| AI Pipeline | Google Gemini (via ADK `SequentialAgent`) |
| Backend | FastAPI + Python 3.12 |
| Frontend | Vanilla JS + HTML + CSS (zero build step) |
| Graph Traversal | Cypher (multi-hop, 1–4 hops) |
| Dependency Management | uv |

---

## Project Structure

```
dealshield_adk_workflow.py   # Three GraphRAG tools + ADK agent pipeline
dealshield_api.py            # FastAPI REST backend + risk scoring engine
static/
  index.html                 # Dashboard shell
  style.css                  # Styles
  app.js                     # Dashboard logic (Vanilla JS)
dealshield_generator.py      # Synthetic dataset loader (Neo4j seed)
dealshield_golden_v2.py      # Golden ground-truth dataset loader (Neo4j seed)
ground_truth.json            # Ground truth for synthetic dataset
golden_ground_truth.json     # Ground truth for golden dataset
pyproject.toml               # Python project config
.env                         # Secrets and configuration (not committed)
```

---

## Setup

### 1. Prerequisites

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) package manager
- A Neo4j Aura instance (free tier works)
- A Google AI Studio API key

### 2. Install dependencies

```bash
uv sync
source .venv/bin/activate
```

### 3. Configure environment

Create a `.env` file in the project root:

```env
NEO4J_URI=neo4j+s://<your-instance-id>.databases.neo4j.io
NEO4J_USERNAME=<your-username>
NEO4J_PASSWORD=<your-password>
NEO4J_DATABASE=<your-database-name>

GOOGLE_API_KEY=<your-google-ai-studio-api-key>

# Optional: change the Gemini model
GEMINI_MODEL=gemini-2.0-flash
```

### 4. Seed the database

Run the dataset loaders once to populate Neo4j:

```bash
python3 dealshield_generator.py
python3 dealshield_golden_v2.py
```

### 5. Start the server

```bash
uvicorn dealshield_api:app --host 0.0.0.0 --port 8000 --reload
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## Usage

1. Select a target company from the dropdown.
2. Click **Run Analysis**.
3. Review the scored risk cards on the **Risk Analysis** tab.
4. Switch to the **Knowledge Graph** tab to visually explore the relationship network.
5. Switch to the **Contracts** tab to browse underlying contract data.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/targets` | List available target companies |
| `POST` | `/api/analyze/full` | Run the full 3-stage risk pipeline |
| `GET` | `/api/graph/visualize` | Fetch graph nodes and edges for a target |
| `GET` | `/api/contracts` | List contracts for a target |
| `GET` | `/api/graph/stats` | Graph database statistics |
| `GET` | `/api/health` | Health check |

---

## Risk Scoring Model

Each risk is scored on a 0–100 scale:

```
score = base_exposure_score
      + related_party_bonus  (if insider/family member involved)
      + holding_hops_bonus   (deeper shell structures = higher score)
      + regulatory_bonus     (for high-exposure regulatory revocations)
```

| Score Range | Severity |
|---|---|
| 80 – 100 | CRITICAL |
| 60 – 79 | HIGH |
| 40 – 59 | MEDIUM |
| 0 – 39 | LOW |
