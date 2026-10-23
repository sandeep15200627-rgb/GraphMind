# GraphMind

**Track:** Company Brain



GraphMind is a graph-backed engineering memory prototype built with FalkorDB and a local language model. It stores engineering decisions and their related context, then retrieves graph evidence to help answer questions about previous decisions.

## Problem

Engineering knowledge is often spread across discussions, incident reports, services, and documentation. When a team asks why a decision was made, finding the original reasoning and supporting evidence can be difficult.

GraphMind aims to make that context easier to retrieve by connecting decisions to the incidents that motivated them, the services they affect, and the sources that support them.

## Why a graph?

A decision can link to the incident that caused it, the service it changes, and the evidence that supports it. Following those relationships helps answer questions such as “Why did we make this decision?” rather than relying only on text matches.

FalkorDB stores these entities and relationships as a graph. GraphMind retrieves connected context from that graph and uses it to help construct an answer.

## Features

- **Engineering memory:** Store engineering decisions and related information in a graph.
- **Evidence retrieval:** Retrieve decisions and their connected incidents, services, and sources.
- **Decision trace:** Inspect a decision and its outgoing graph relationships.
- **Local language model:** Use Ollama to run a language model locally instead of requiring a paid model API.
- **Web interface:** Interact with GraphMind through a Streamlit frontend.
- **API:** Access backend functionality through FastAPI endpoints.

GraphMind is a prototype for evidence-grounded engineering memory. It is not presented as a fully autonomous engineering agent.

## Architecture

```text
             User
              |
              v
      Streamlit Frontend
              |
              v
         FastAPI Backend
              |
              v
      Evidence Retrieval
              |
              v
           FalkorDB
        (Graph Database)
              |
              v
       Retrieved Evidence
              |
              v
        Local Ollama LLM
              |
              v
        Answer to User
```

FalkorDB is the primary store for the connected engineering context. Ollama supplies the local language model used to help formulate answers from retrieved evidence.

## Technology stack

| Component | Technology |
|---|---|
| Backend API | Python, FastAPI |
| Frontend | Streamlit |
| Graph database | FalkorDB |
| Local language model runtime | Ollama |
| Example model | Qwen2.5 1.5B |
| Database access | FalkorDB Python client |
| Container runtime | Docker |

## Graph data model

The current data model uses the following node labels and properties.

| Node label | Properties |
|---|---|
| `Decision` | `id`, `title`, `rationale` |
| `Incident` | `id`, `title`, `description` |
| `Source` | `id`, `title`, `content` |
| `Service` | `id`, `name` |

The relationships used by the retrieval and decision-trace queries are:

| Relationship | Meaning |
|---|---|
| `(:Decision)-[:MOTIVATED_BY]->(:Incident)` | Connects a decision to a motivating incident |
| `(:Decision)-[:AFFECTS]->(:Service)` | Connects a decision to an affected service |
| `(:Decision)-[:SUPPORTED_BY]->(:Source)` | Connects a decision to a supporting source |

This describes the graph schema used by these queries. It does not mean every decision automatically has all three relationships.

## Cypher queries used by the product

### 1. Evidence retrieval

Used by `graph_db.retrieve_evidence()`.

```cypher
MATCH (d:Decision)
OPTIONAL MATCH (d)-[:MOTIVATED_BY]->(i:Incident)
OPTIONAL MATCH (d)-[:AFFECTS]->(s:Service)
OPTIONAL MATCH (d)-[:SUPPORTED_BY]->(src:Source)
RETURN d.id, d.title, d.rationale, i.title, s.name, src.title, src.content
```

The optional matches allow the query to return decision information even when one or more connected entities are absent.

### 2. Decision trace

Used by `graph_db.get_decision_trace()`.

```cypher
MATCH (d:Decision {id: $decision_id})
OPTIONAL MATCH (d)-[r]->(n)
RETURN properties(d), type(r), labels(n), properties(n)
```

The query finds a decision by its ID and inspects its outgoing relationships, returning the decision properties, relationship type, connected node labels, and connected node properties.

## Project structure

```text
GraphMind/
├── README.md
├── .gitignore
└── graphmind/
    ├── README.md
    ├── .env.example
    ├── requirements.txt
    ├── backend/
    │   ├── main.py
    │   ├── graph_db.py
    │   └── seed_demo.py
    ├── frontend/
    │   └── app.py
    └── tests/
```

This is a simplified overview. Other files may exist in these directories.

## Requirements

Install the following before running the application:

- Python 3.11 or another version supported by the project dependencies
- Docker Desktop
- Ollama, if you want to use the local language model
- Git

The project was developed and tested in a local Windows environment. Dependency compatibility may vary by Python version.

## Run GraphMind locally

### Step 1: Clone the repository

```powershell
git clone https://github.com/sandeep15200627-rgb/GraphMind.git
cd GraphMind
```

### Step 2: Create and activate a virtual environment

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution, follow the appropriate PowerShell guidance for activating a virtual environment on your machine.

### Step 3: Install Python dependencies

```powershell
cd .\graphmind
python -m pip install -r requirements.txt
```

### Step 4: Start FalkorDB

Ensure Docker Desktop is running. Start FalkorDB with:

```powershell
docker run -p 6379:6379 -p 3000:3000 -it --rm falkordb/falkordb:latest
```

Keep this terminal open while using GraphMind.

The ports are used for the FalkorDB service and its web interface. The web interface is available at `http://localhost:3000` when the container starts successfully.

**Data persistence:** The `--rm` option removes the container when it stops. Do not rely on this command to preserve your graph data between runs. Reseed the demo graph after a fresh start. For persistent data, configure an appropriate Docker volume according to FalkorDB's documentation.

### Step 5: Seed the demo graph

Open a second PowerShell terminal and activate the virtual environment from the repository root:

```powershell
cd "$HOME\Downloads\GraphMind"
.\.venv\Scripts\Activate.ps1
cd .\graphmind
python -m backend.seed_demo
```

If you cloned the repository somewhere else, replace the example path with your actual repository location.

Run the seed command against a running FalkorDB instance. If the graph is empty, this command populates the demo data used to explore the application.

### Step 6: Configure Ollama

Install and start Ollama if it is not already running. Pull the model used by the example configuration:

```powershell
ollama pull qwen2.5:1.5b
```

The model runs locally, but it still consumes system memory. On a machine with limited RAM, close unnecessary applications before running it.

### Step 7: Start the FastAPI backend

In a terminal with the virtual environment activated:

```powershell
cd .\graphmind
python -m uvicorn backend.main:app --reload
```

The backend should be available at:

- API base URL: `http://127.0.0.1:8000`
- Interactive API documentation: `http://127.0.0.1:8000/docs`

Keep this terminal open.

### Step 8: Start the Streamlit frontend

Open another PowerShell terminal:

```powershell
cd "$HOME\Downloads\GraphMind"
.\.venv\Scripts\Activate.ps1
cd .\graphmind
python -m streamlit run frontend/app.py
```

Open the local URL printed by Streamlit, typically `http://localhost:8501`.

You should now be able to interact with the GraphMind interface.

## API overview

The following table describes the intended API surface. Confirm the actual routes and methods in `backend/main.py` and the running `/docs` page before relying on every entry.

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | Basic service information |
| `GET` | `/health` | Health-check endpoint |
| `POST` | `/ask` | Ask a question using graph evidence |
| `POST` | `/memories` | Submit a memory to the backend |
| `GET` | `/memories` | Retrieve memories, if exposed by the current implementation |
| `GET` | `/graph/overview` | View a summary of the graph |
| `GET` | `/decisions/{decision_id}/trace` | Inspect a decision and its outgoing relationships |

For exact request fields, response formats, and route availability, use the interactive API documentation at `http://127.0.0.1:8000/docs` while the backend is running.

## Testing

From the project directory containing the test configuration, activate the virtual environment and run:

```powershell
python -m pytest -q
```

A passing test suite provides a basic check of the current implementation. It does not by itself guarantee that every end-to-end workflow works on a fresh machine.

## Current limitations

- Evidence retrieval depends on the graph data and the relationships that exist.
- A decision without relevant connected evidence may not provide enough context to answer a question.
- Language-model answers depend on the quality of retrieved evidence and may still be incorrect.
- Local inference consumes RAM and other system resources.
- This is a hackathon prototype, not a production-ready engineering knowledge platform.
- Authentication, access control, deployment hardening, and production-scale evaluation are outside the scope of this prototype.

## Future improvements

- Improve evidence ranking and query understanding.
- Expand automated tests for memory creation, retrieval, and decision tracing.
- Add stronger validation and error handling for graph operations.
- Improve graph visualization and exploration in the frontend.
- Add persistent deployment configuration and appropriate security controls.

## License

Add the license selected for this repository here. Until a license is added, do not assume that the project is available for unrestricted reuse.

---

**Repository:**(https://github.com/sandeep15200627-rgb/GraphMind)
