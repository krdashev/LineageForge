# LineageForge MVP

**Genealogical intelligence infrastructure with claim-based provenance**

LineageForge is an open-source genealogical research platform that treats ancestry as a knowledge graph of **claims with explicit provenance**, not as a single authoritative tree. Every assertion is traceable to its source, conflicts are preserved, and identity resolution is probabilistic and auditable.

This is **research infrastructure**, not a consumer genealogy app.

---

## Core Principles

1. **Claims, not facts** – All assertions are claims that can be supported, challenged, or revised
2. **Provenance first** – Every claim links to its source, citation, and contextual metadata
3. **Conflict preservation** – Conflicting claims are stored side by side for comparative analysis
4. **Transparent inference** – Derived conclusions are traceable through evidence and reasoning
5. **Deterministic runs** – Re-running inference produces reproducible results

---

## Features (MVP)

### ✅ Implemented
- **GEDCOM Import** – Parse GEDCOM files as claims with explicit sources
- **Claim-based Storage** – PostgreSQL schema with full provenance tracking
- **Identity Resolution** – Probabilistic entity resolution with merge audit logs
- **WikiTree Expansion** – Conservative lineage expansion from WikiTree API
- **Validation Engine** – Detect temporal impossibilities, circular relationships, and conflicts
- **REST API** – Query persons, claims, relationships, and graph structures
- **Minimal GUI** – Dashboard, tree visualization (Cytoscape.js), and evidence inspection
- **Background Jobs** – RQ worker for long-running tasks (resolution, expansion, validation)
- **Report Generation** – HTML and PDF reports with source coverage and confidence metrics

### 🎯 Ontology (v0.1.0)
All data conforms to a formal ontology:
- **Entities**: `Person`, `Source`, `Place`, `Event`, `Claim`, `Relationship`
- **Predicates**: Standard genealogical relations (`has_name`, `born_on`, `parent_of`, etc.)
- **Confidence Levels**: `definite`, `high`, `moderate`, `low`, `speculative`
- **Flags**: Validation anomalies (`lifespan_invalid`, `circular_relationship`, etc.)

See: `app/ontology.py`

---

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (recommended)

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/lineageforge.git
cd lineageforge
```

### 2. Start with Docker Compose
```bash
docker-compose up -d
```

This starts:
- **PostgreSQL** (port 5432)
- **Redis** (port 6379)
- **Web service** (port 8000)
- **Worker service** (background jobs)

### 3. Run Migrations
```bash
docker-compose exec web alembic upgrade head
```

### 4. Access Application
- **Dashboard**: http://localhost:8000
- **API docs**: http://localhost:8000/docs
- **Tree view**: http://localhost:8000/tree

### 5. Import GEDCOM
Upload a GEDCOM file via the dashboard or:
```bash
curl -X POST http://localhost:8000/api/import/gedcom \
  -F "file=@your_tree.ged"
```

---

## Manual Setup (Without Docker)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables
```bash
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/lineageforge
export REDIS_URL=redis://localhost:6379/0
```

### 3. Run Migrations
```bash
alembic upgrade head
```

### 4. Start Services
```bash
# Terminal 1: Web service
uvicorn app.main:app --reload

# Terminal 2: Worker
python -m app.worker.worker
```

---

## API Reference

### Import
- `POST /api/import/gedcom` – Upload GEDCOM file

### Persons
- `GET /api/person/{id}` – Get person details
- `GET /api/person/{id}/claims` – Get all claims about a person
- `GET /api/search?q={query}` – Search persons by name

### Graph
- `GET /api/graph/lineage/{id}?depth={n}` – Get lineage subgraph
- `GET /api/graph/subgraph?person_ids={ids}` – Get subgraph for specific persons

### Jobs
- `GET /api/jobs` – List recent jobs
- `GET /api/jobs/{id}` – Get job status
- `POST /api/jobs/resolve` – Start identity resolution
- `POST /api/jobs/expand?person_id={id}` – Expand lineage from WikiTree
- `POST /api/jobs/validate` – Run validation
- `POST /api/jobs/report` – Generate report

---

## GUI Walkthrough

### Dashboard
- View summary statistics (persons, claims, flags)
- Import GEDCOM files
- See recent job runs

### Tree View
- Interactive graph visualization (Cytoscape.js)
- Click nodes to view evidence
- Explore relationships with confidence scores

### Person Detail Page
- All claims grouped by predicate
- Conflict detection (highlighted)
- Source citations with confidence levels
- Link to tree view

### Runs Page
- Job execution history
- View results and error logs

---

## Architecture

```
┌─────────────────────────────────────────────┐
│              User Interface                  │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐ │
│  │   CLI    │  │   GUI    │  │  Python   │ │
│  │          │  │ (HTMX)   │  │  Bindings │ │
│  └──────────┘  └──────────┘  └───────────┘ │
└─────────────────────────────────────────────┘
                     │
┌─────────────────────────────────────────────┐
│             FastAPI Web Service              │
│  REST API + Server-Rendered UI              │
└─────────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼────────┐       ┌────────▼────────┐
│   PostgreSQL   │       │   Redis + RQ    │
│   (Claims)     │       │   (Jobs)        │
└────────────────┘       └─────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │   Background Worker   │
                    │  • Identity Resolution│
                    │  • Lineage Expansion  │
                    │  • Validation         │
                    │  • Report Generation  │
                    └───────────────────────┘
```

### Key Modules
- `app/models.py` – Database schema (SQLModel)
- `app/ontology.py` – Formal ontology definitions
- `app/ingestion/` – GEDCOM and WikiTree importers
- `app/resolution/` – Identity resolution engine
- `app/validation/` – Validation rules
- `app/reporting/` – Report generation
- `app/api/` – REST API endpoints
- `app/ui/` – GUI views (Jinja2 + HTMX)
- `app/worker/` – Background tasks (RQ)

---

## Database Schema

### Core Tables
- `persons` – Person entities
- `sources` – Evidence sources
- `places` – Geographic locations
- `claims` – All assertions (subject-predicate-object)
- `flags` – Validation anomalies
- `merge_events` – Identity resolution audit log
- `runs` – Job execution tracking
- `external_refs` – WikiTree IDs, etc.

### Claim Structure
Every claim must include:
```python
{
  "subject_id": UUID,        # Usually person_id
  "predicate": str,          # e.g., "has_name", "parent_of"
  "object_id": UUID | None,  # For relationships
  "object_value": str | None,# For literal values
  "source_id": UUID,         # Required provenance
  "confidence": float,       # 0.0 to 1.0
  "confidence_level": str,   # definite/high/moderate/low/speculative
  "rationale": str | None,   # Why this claim exists
  "time_start": datetime,    # Optional temporal bounds
  "time_end": datetime,
  "place_id": UUID | None    # Optional spatial context
}
```

---

## Identity Resolution

### How It Works
1. **Blocking**: Find candidates using name overlap
2. **Scoring**: Weighted features (name, dates, places, relationships)
3. **Merge**: If score ≥ threshold (default 0.75), merge entities
4. **Audit**: Log merge event with rationale and feature scores

### Claims Are Preserved
Merging transfers all claims to the target person. No data is lost.

### Inspecting Merges
```sql
SELECT * FROM merge_events WHERE confidence_score >= 0.75;
```

---

## Validation Rules

The validator detects:
- **Lifespan invalid**: Death before birth, age > 120 years
- **Generational spacing invalid**: Parent-child age gap < 10 or > 60 years
- **Temporal impossibility**: Events in wrong order (marriage before birth, etc.)
- **Circular relationships**: Cycles in parent-child graph
- **Conflicting claims**: Multiple values for same predicate

### Flags Are Non-Blocking
Validation flags are stored but **do not block execution**. Inspect flags via:
```bash
GET /api/person/{id}/claims
```

---

## Testing

### Run Tests
```bash
pytest
```

### Test Coverage
- API endpoints (persons, claims, search, graph)
- Identity resolution (merge, candidate scoring)
- Validation (lifespan, generational spacing, conflicts)

---

## Deployment (Railway)

See `DEPLOYMENT.md` for full instructions.

### Quick Deploy
1. Connect GitHub repo to Railway
2. Add Postgres and Redis plugins
3. Set environment variables (DATABASE_URL, REDIS_URL)
4. Deploy web service: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Deploy worker service: `python -m app.worker.worker`
6. Run migrations: `alembic upgrade head`

---

## Configuration

All settings via environment variables (see `app/config.py`):

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/lineageforge

# Redis
REDIS_URL=redis://localhost:6379/0

# Identity Resolution
IDENTITY_MERGE_THRESHOLD=0.75
IDENTITY_MAX_CANDIDATES=100

# Expansion
EXPANSION_MAX_DEPTH=3
EXPANSION_MAX_NODES=1000

# WikiTree
WIKITREE_API_BASE=https://api.wikitree.com/api.php
WIKITREE_RATE_LIMIT=0.5  # seconds between requests

# Worker
WORKER_TIMEOUT=3600
```

---

## Roadmap

### Phase 1 (MVP) ✅
- Claim-based storage
- GEDCOM import
- Identity resolution
- WikiTree expansion
- Validation
- Basic GUI

### Phase 2 (Planned)
- Multi-source conflict resolution UI
- Advanced graph queries (SPARQL-like)
- Export to RDF/JSON-LD
- Python API client library
- Performance optimizations (caching, indexing)

### Phase 3 (Future)
- Multi-user collaboration
- Source digitization integration
- Machine learning for claim confidence
- Integration with archives (FamilySearch, Ancestry, etc.)

---

## Contributing

Contributions welcome! Please follow these principles:
- **Correctness over convenience**: No silent merges, no hidden heuristics
- **Auditability**: Every decision must be inspectable
- **Determinism**: Re-running inference must produce same results
- **Preserve conflicts**: Don't collapse conflicting claims

See `CONTRIBUTING.md` for code style and PR guidelines.

---

## License

AGPL-3.0 – See `LICENSE` file.

---

## Philosophy

LineageForge is built for **researchers, not consumers**. We prioritize:
- **Epistemic rigor** over user-friendly simplifications
- **Transparency** over algorithmic magic
- **Long-term preservation** over short-term convenience

If you need a genealogy toy, this is not it. If you need genealogical intelligence infrastructure, welcome.

---

## Contact

- **Issues**: https://github.com/yourusername/lineageforge/issues
- **Discussions**: https://github.com/yourusername/lineageforge/discussions
- **Documentation**: See `docs/` directory

---

**Execute.**
