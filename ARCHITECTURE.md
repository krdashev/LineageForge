# LineageForge Architecture

## System Overview

LineageForge is a genealogical intelligence platform built on claim-based provenance. Every assertion about a person, relationship, or event is stored as an explicit claim with traceable sources, confidence scores, and rationale.

---

## Design Principles

### 1. Claims, Not Facts
Every piece of information is a **claim** that can be:
- Supported by evidence
- Challenged by conflicting claims
- Revised as new evidence emerges

### 2. No Silent Merges
Identity resolution is **explicit and auditable**:
- Merge events are logged with confidence scores
- Feature scores are preserved for inspection
- Merged entities remain queryable (marked as inactive)

### 3. Conflict Preservation
When sources disagree:
- All conflicting claims are stored
- Conflicts are flagged but not resolved automatically
- Users can inspect evidence and choose interpretations

### 4. Deterministic Inference
Re-running any process produces identical results:
- Seeded random number generators
- Version-controlled configurations
- Full provenance logs

---

## Core Data Model

### Entity-Relationship Diagram

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   Person    │       │    Source   │       │    Place    │
│             │       │             │       │             │
│ person_id   │       │ source_id   │       │ place_id    │
│ is_active   │       │ source_type │       │ place_name  │
│ merged_into │       │ reliability │       │ latitude    │
└─────────────┘       └─────────────┘       └─────────────┘
       │                     │                     │
       │                     │                     │
       └─────────────┬───────┴─────────────────────┘
                     │
              ┌──────▼──────┐
              │    Claim    │
              │             │
              │ claim_id    │
              │ subject_id  │──> person_id
              │ predicate   │──> has_name, parent_of, etc.
              │ object_id   │──> person_id (for relationships)
              │ object_value│──> "John Doe" (for literals)
              │ source_id   │──> source_id
              │ confidence  │──> 0.0 to 1.0
              │ place_id    │──> place_id (optional)
              │ time_start  │──> datetime (optional)
              │ time_end    │──> datetime (optional)
              │ rationale   │──> "Imported from GEDCOM"
              └─────────────┘
```

### Claim Structure

Claims follow a **subject-predicate-object** triple pattern:

```
Person A [has_name] "John Smith" (source: GEDCOM, confidence: 0.9)
Person A [parent_of] Person B (source: WikiTree, confidence: 0.8)
Person A [born_on] "1950-01-01" (source: Birth Certificate, confidence: 0.95)
```

**Every claim must have:**
- `subject_id` – Entity being described
- `predicate` – Relationship type (from ontology)
- `object_id` OR `object_value` – Target entity or literal value
- `source_id` – Evidence source
- `confidence` – Numeric score (0.0 to 1.0)
- `confidence_level` – Categorical level (definite/high/moderate/low/speculative)

**Optional fields:**
- `place_id` – Geographic context
- `time_start`, `time_end` – Temporal bounds
- `rationale` – Human-readable explanation

---

## Module Architecture

### 1. Ontology Layer (`app/ontology.py`)
Defines the formal vocabulary:
- **Entity types**: Person, Source, Place, Event, Claim, Relationship
- **Predicates**: has_name, born_on, parent_of, married_at, etc.
- **Confidence levels**: definite, high, moderate, low, speculative
- **Flag types**: lifespan_invalid, circular_relationship, etc.

All other modules **must** conform to this ontology.

### 2. Data Layer (`app/models.py`, `app/database.py`)
SQLModel-based ORM:
- Type-safe models with Pydantic validation
- PostgreSQL as canonical store
- JSONB for flexible metadata (raw source payloads, custom fields)

### 3. Ingestion Layer (`app/ingestion/`)
Converts external data to claims:
- **GEDCOM Importer**: Parses GEDCOM → creates persons + claims
- **WikiTree Connector**: Queries WikiTree API → creates claims
- **No merging at ingestion**: Each import creates new persons

### 4. Resolution Layer (`app/resolution/`)
Probabilistic entity resolution:
1. **Candidate Generation**: Blocking on name parts
2. **Feature Scoring**: Name similarity, date overlap, place overlap, relational coherence
3. **Merge Decision**: If weighted score ≥ threshold, merge
4. **Audit Log**: Record merge event with rationale

### 5. Validation Layer (`app/validation/`)
Detects anomalies:
- **Temporal**: Lifespan invalid, events out of order
- **Generational**: Parent-child age gaps
- **Logical**: Circular relationships
- **Evidentiary**: Conflicting claims

Flags are **stored, not blocking**.

### 6. Reporting Layer (`app/reporting/`)
Generates HTML/PDF reports:
- Summary statistics
- Confidence distributions
- Source coverage
- Notable individuals (externally corroborated)

### 7. API Layer (`app/api/`)
RESTful endpoints:
- **Import**: Upload GEDCOM files
- **Query**: Get persons, claims, relationships
- **Graph**: Traverse lineage subgraphs
- **Jobs**: Queue background tasks

### 8. UI Layer (`app/ui/`)
Minimal web interface:
- **Server-rendered**: Jinja2 templates
- **Interactive**: HTMX for dynamic updates
- **Visualization**: Cytoscape.js for graph rendering

### 9. Worker Layer (`app/worker/`)
Background job processing:
- **RQ** (Redis Queue) for task management
- Long-running operations: identity resolution, expansion, validation, reporting

---

## Data Flow

### Example: GEDCOM Import

```
1. User uploads GEDCOM file
   ↓
2. FastAPI endpoint receives file
   ↓
3. Create Run record (status: RUNNING)
   ↓
4. GedcomImporter parses file
   ↓
5. For each GEDCOM individual:
   - Create Person entity
   - Create Source record (GEDCOM file)
   - Extract assertions → Create Claim records
   ↓
6. Update Run record (status: COMPLETED)
   ↓
7. Return summary (persons_created, claims_created)
```

**Key Point**: No identity resolution happens during import. Each GEDCOM individual becomes a separate Person.

### Example: Identity Resolution

```
1. User triggers resolution job
   ↓
2. Create Run record (status: QUEUED)
   ↓
3. Enqueue task to RQ worker
   ↓
4. Worker starts, updates Run (status: RUNNING)
   ↓
5. IdentityResolver processes all active persons:
   - Find candidates (blocking on names)
   - Score candidates (name, dates, places, relationships)
   - If score ≥ threshold: Merge persons
   - Create MergeEvent audit record
   ↓
6. Update Run (status: COMPLETED, result_summary)
   ↓
7. User inspects merge_events table for audit trail
```

### Example: Tree Visualization

```
1. User navigates to /tree?person_id={id}
   ↓
2. Browser loads tree.html template
   ↓
3. JavaScript calls /api/graph/lineage/{id}?depth=2
   ↓
4. API traverses relationship claims (BFS)
   ↓
5. Returns { nodes: [...], edges: [...] }
   ↓
6. Cytoscape.js renders graph
   ↓
7. User clicks node → JavaScript calls /api/person/{id}/claims
   ↓
8. Display claims with sources and confidence
```

---

## Identity Resolution Algorithm

### Blocking Strategy
Generate candidates using **name token overlap**:
```python
if len(name_parts_1 ∩ name_parts_2) >= 2:
    add to candidates
```

### Feature Scoring
Weighted features:
- **Name similarity** (40%): Token-based Jaccard similarity
- **Date overlap** (30%): Birth/death date alignment
- **Place similarity** (20%): Shared geographic locations
- **Relational coherence** (10%): Shared parents/spouses/children

### Merge Decision
```python
if weighted_score >= threshold (default 0.75):
    merge(source_person → target_person)
    log_merge_event(scores, rationale)
```

### Merge Operation
1. Mark source person as `is_active = False`
2. Set source person's `merged_into = target_person_id`
3. Transfer all claims: `UPDATE claims SET subject_id = target WHERE subject_id = source`
4. Create MergeEvent with full audit trail

---

## Validation Rules

### Lifespan Validation
```python
if death_date < birth_date:
    flag(LIFESPAN_INVALID, severity=ERROR)
elif lifespan > 120 years:
    flag(LIFESPAN_INVALID, severity=WARNING)
```

### Generational Spacing
```python
parent_child_age_gap = child_birth - parent_birth
if age_gap < 10 years:
    flag(GENERATIONAL_SPACING_INVALID, severity=ERROR)
elif age_gap > 60 years:
    flag(GENERATIONAL_SPACING_INVALID, severity=WARNING)
```

### Circular Relationships
Detect cycles in parent-child graph using DFS:
```python
def has_cycle(node, visited, rec_stack):
    if node in rec_stack:
        return True  # Cycle detected
    ...
```

### Conflicting Claims
```python
for predicate, claims in grouped_by_predicate:
    unique_values = set(claim.object_value for claim in claims)
    if len(unique_values) > 1:
        flag(CONFLICTING_CLAIMS, severity=WARNING)
```

---

## Scalability Considerations

### Current Limits (MVP)
- Persons: ~1M (depends on Postgres configuration)
- Claims: ~10M (indexed by subject_id, predicate)
- Concurrent users: ~100 (single web instance)

### Optimization Paths
1. **Indexing**: Add B-tree indexes on frequently queried fields
2. **Caching**: Redis cache for hot paths (frequent person queries)
3. **Partitioning**: Partition claims table by predicate or date range
4. **Read Replicas**: Separate read/write database instances
5. **Graph Database**: Migrate to Neo4j for complex graph traversals

### Worker Scaling
Add more worker instances for parallel job processing:
```bash
# Railway: Deploy multiple worker services
railway up --service worker-1
railway up --service worker-2
```

---

## Security & Privacy

### Current Status (MVP)
- **No authentication**: Single-user deployment
- **No encryption**: Database connections should use SSL in production
- **No PII controls**: Assumes public genealogical data

### Production Hardening
1. Add authentication (JWT or session-based)
2. Implement RBAC (researcher, contributor, admin)
3. Enable database encryption at rest
4. Add audit logs for all mutations
5. Implement data retention policies

---

## Testing Strategy

### Unit Tests
- Model validation (Pydantic)
- Claim construction
- Confidence score calculations

### Integration Tests
- API endpoints (persons, claims, graph)
- GEDCOM import workflow
- Identity resolution logic
- Validation rules

### End-to-End Tests
- User imports GEDCOM
- System resolves identities
- User inspects merge audit logs
- User generates report

### Performance Tests
- Benchmark identity resolution at scale
- Measure graph traversal latency
- Profile database query performance

---

## Observability

### Logging
Structured logs via Python `logging`:
- Request/response logs (FastAPI middleware)
- Job execution logs (RQ worker)
- Error tracking with stack traces

### Metrics
Track via Railway dashboard:
- Request latency (p50, p95, p99)
- Database connection pool utilization
- Worker queue depth
- Error rates

### Debugging
- Inspect Run records for job history
- Query MergeEvent table for resolution audit
- Check Flag table for validation issues

---

## Deployment Architecture (Railway)

```
┌──────────────────────────────────────────────┐
│              Railway Platform                 │
│                                              │
│  ┌──────────────┐      ┌──────────────┐    │
│  │  Web Service │      │ Worker Svc   │    │
│  │  (FastAPI)   │      │ (RQ Worker)  │    │
│  └──────┬───────┘      └──────┬───────┘    │
│         │                     │              │
│  ┌──────▼──────────────────────▼─────┐     │
│  │      PostgreSQL Plugin              │     │
│  │      (Managed Database)             │     │
│  └─────────────────────────────────────┘     │
│                                              │
│  ┌─────────────────────────────────────┐     │
│  │      Redis Plugin                    │     │
│  │      (Managed Cache/Queue)           │     │
│  └─────────────────────────────────────┘     │
└──────────────────────────────────────────────┘
```

### Service Configuration
- **Web**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Worker**: `python -m app.worker.worker`
- **Auto-scaling**: Railway handles based on traffic
- **Health checks**: `GET /health` endpoint

---

## Future Enhancements

### Phase 2: Advanced Querying
- SPARQL-like graph queries
- Relationship path finding
- Probabilistic reasoning over uncertain claims

### Phase 3: Collaboration
- Multi-user editing
- Claim versioning
- Comment threads on conflicts

### Phase 4: ML Integration
- Confidence prediction from text
- Record linkage with learned embeddings
- Anomaly detection via unsupervised learning

---

**This architecture prioritizes correctness, auditability, and long-term maintainability over convenience.**
