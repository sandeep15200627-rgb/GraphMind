# GraphMind

GraphMind is a local-first engineering-memory assistant. It retrieves connected engineering records from FalkorDB, then uses Ollama (Qwen by default) to explain the evidence in natural language.

## Architecture

- **FalkorDB:** primary store for decisions, incidents, services, sources, and their relationships.
- **Python + `falkordb`:** executes Cypher and transforms query results into records.
- **FastAPI:** exposes `/ask`, `/memories`, `/health`, and `/graph/overview`.
- **Ollama:** optional local model for answer generation. If unavailable, GraphMind returns a transparent evidence summary.
- **Streamlit:** chat UI and memory-entry form.

## Graph data model

Node labels:
- `Decision`: `id`, `title`, `rationale`
- `Incident`: `id`, `title`, `description`
- `Service`: `name`, `database`, `description`
- `Source`: `id`, `title`, `content`

Relationships:
- `(Incident)-[:AFFECTED]->(Service)`
- `(Decision)-[:AFFECTS]->(Service)`
- `(Decision)-[:MOTIVATED_BY]->(Incident)`
- `(Decision)-[:SUPPORTED_BY]->(Source)`
- `(Incident)-[:SUPPORTED_BY]->(Source)`

## Requirements

- Python 3.10+
- Docker Desktop and a running FalkorDB container exposing port `6379`
- Optional: Ollama with `qwen2.5:1.5b` pulled locally

## Windows / PowerShell setup

Open this folder in VS Code, then run these commands in the integrated terminal:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, use Command Prompt terminal and run `.venv\Scripts\activate.bat`, or ask for help before changing execution policy.

Make sure the existing FalkorDB container is running. Do not remove other containers. If your existing container is named `falkordb-learning`, start it with:

```powershell
docker start falkordb-learning
```

Seed sample data (repeatable; uses `MERGE`):

```powershell
python -m backend.seed_demo
```

Start the API in terminal 1:

```powershell
python -m uvicorn backend.main:app --reload
```

Open interactive API documentation at http://127.0.0.1:8000/docs.

Start the UI in terminal 2:

```powershell
python -m streamlit run frontend/app.py
```

Streamlit prints the local URL, usually http://localhost:8501.

## Verify

- `GET /health` reports API, FalkorDB, and Ollama status.
- `GET /graph/overview` reports node and relationship counts.
- `POST /ask` with `{"question":"Why did we migrate payment storage to PostgreSQL?"}` should retrieve connected evidence.
- `POST /memories` can add a decision or incident. Check the response for the generated IDs.
- Ask about the new memory to confirm persistence.

Example ask request:

```json
{
  "question": "Why did we migrate payment storage to PostgreSQL?"
}
```

Example memory request:

```json
{
  "kind": "decision",
  "title": "Use retries for transient notification failures",
  "content": "The team agreed to retry transient delivery errors with a bounded retry policy.",
  "service": "notification-service",
  "rationale": "Improve delivery reliability"
}
```

## Tests

```powershell
python -m pytest -q
```

The unit tests use a fake database for retrieval ranking and do not require a running FalkorDB instance.

## Essential Cypher pattern

```cypher
MATCH (d:Decision)-[:SUPPORTED_BY]->(src:Source),
      (d)-[:MOTIVATED_BY]->(i:Incident),
      (d)-[:AFFECTS]->(s:Service)
RETURN d.title AS decision,
       i.title AS incident,
       s.name AS service,
       src.title AS evidence
```

The graph relationships are central to retrieval: GraphMind traces a decision to the incident that motivated it, the service it affects, and the source supporting it.

## Current MVP limitations

- Retrieval uses graph-connected records plus transparent keyword overlap ranking, not embeddings.
- Sample data is synthetic; replace or extend it with permitted, properly sourced engineering records.
- The LLM is instructed to use retrieved evidence, but prompt instructions do not guarantee factuality. Inspect the returned evidence and test unsupported questions.
- Authentication and multi-user access controls are not included. Keep the demo local unless you add appropriate security before deployment.
