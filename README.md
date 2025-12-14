# LineageForge
LineageForge is an open-source genealogical intelligence framework that models ancestry as a verifiable, evidence-weighted knowledge graph. Instead of presenting a single authoritative family tree, LineageForge captures claims about people, relationships, and events, along with the sources, reasoning, and uncertainty behind them. The goal is to support rigorous genealogical research, reproducibility, and long-term knowledge preservation.

## Core Principles
- **Claims, not facts**  
  All assertions are treated as claims that can be supported, challenged, or revised as new evidence emerges.
- **Provenance first**  
  Every claim is explicitly linked to its sources, citations, and contextual metadata.
- **Conflict preservation**  
  Conflicting claims are stored side by side rather than collapsed or hidden, allowing researchers to compare interpretations.
- **Transparent inference**  
  Derived conclusions are traceable back through the evidence and inference rules that produced them.

## What This Is
- **A data model** for representing people, events, relationships, sources, and claims in a structured, queryable graph
- **An inference engine** for evaluating evidence, propagating confidence, and generating derived relationships
- **A research platform** for historians, genealogists, and developers who need auditable, extensible genealogical analysis

## What This Is Not
- **A consumer genealogy website** with charts, hints, or social features
- **A DNA database** or genetic matching service
- **A closed system** with proprietary formats or opaque decision-making

## Key Use Cases
- Comparative analysis of conflicting genealogical hypotheses
- Long-term preservation of research notes, sources, and reasoning
- Programmatic querying of complex family relationships
- Integration with external archives, datasets, and digital humanities tools

## High-Level Architecture
LineageForge is designed around a modular architecture, typically including:
- A graph-based storage layer for entities, claims, and sources
- An inference and scoring layer for evaluating evidence
- APIs for data ingestion, querying, and analysis
- Optional tooling for visualization, validation, and export

## Data Model Overview
At a minimum, the model represents:
- **Entities** (people, places, organizations)
- **Events** (births, deaths, marriages, migrations)
- **Claims** linking entities and events
- **Sources** providing evidence and context
- **Assertions and inferences** with confidence and rationale

## Project Status
Early-stage architecture and specification. The core concepts and data structures are under active design, and APIs and tooling are expected to evolve.

## Roadmap
Planned areas of development include:
- Formal schema definitions and versioning
- Reference implementations of the inference engine
- Import/export pipelines for common genealogical formats
- Documentation and example datasets

## Getting Started
See docs/architecture.md for an overview of the system design, data model, and planned components.

## Contributing
Contributions are welcome in the form of design feedback, documentation, prototypes, and code. See CONTRIBUTING.md for guidelines once available.
