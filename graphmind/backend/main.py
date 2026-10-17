from contextlib import asynccontextmanager
from typing import Literal

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from backend.agent import answer_question
from backend.config import APP_NAME, OLLAMA_BASE_URL, OLLAMA_MODEL
from backend.graph_db import get_database


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


class MemoryCreate(BaseModel):
    kind: Literal["decision", "incident"]
    title: str = Field(min_length=3, max_length=200)
    content: str = Field(min_length=5, max_length=5000)
    service: str | None = Field(default=None, max_length=120)
    rationale: str | None = Field(default=None, max_length=2000)
    incident_id: str | None = Field(
        default=None,
        description="Optional existing incident ID that motivated a decision.",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Do not seed or mutate data automatically at server startup.
    yield


app = FastAPI(
    title=APP_NAME,
    description="Evidence-grounded engineering memory backed by FalkorDB and Ollama.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/")
def root():
    return {
        "name": APP_NAME,
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health():
    result = {
        "api": "ok",
        "falkordb": "unknown",
        "ollama": "unknown",
        "ollama_model": OLLAMA_MODEL,
    }

    try:
        result["falkordb"] = "ok" if get_database().ping() else "error"
    except Exception as exc:
        result["falkordb"] = "unavailable"
        result["falkordb_detail"] = str(exc)

    try:
        response = requests.get(
            f"{OLLAMA_BASE_URL.rstrip('/')}/api/tags", timeout=3
        )
        response.raise_for_status()
        models = [
            item.get("name", "")
            for item in response.json().get("models", [])
        ]
        result["ollama"] = "ok"
        result["configured_model_available"] = (
            OLLAMA_MODEL in models
            or any(name.startswith(OLLAMA_MODEL.split(":")[0] + ":") for name in models)
        )
        result["available_models"] = models
    except (requests.RequestException, ValueError):
        result["ollama"] = "unavailable"
        result["configured_model_available"] = False

    return result


@app.post("/ask")
def ask(request: AskRequest):
    try:
        return answer_question(request.question, get_database())
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "GraphMind could not query FalkorDB. Check that the container is "
                "running, port 6379 is reachable, and the graph name is correct. "
                f"Technical detail: {exc}"
            ),
        ) from exc


@app.post("/memories", status_code=201)
def create_memory(memory: MemoryCreate):
    try:
        saved = get_database().save_memory(
            kind=memory.kind,
            title=memory.title,
            content=memory.content,
            service=memory.service,
            rationale=memory.rationale,
            incident_id=memory.incident_id,
        )
        return {"status": "saved", **saved}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Could not save memory to FalkorDB: {exc}",
        ) from exc
    
@app.get("/decisions/{decision_id}/trace")
def decision_trace(decision_id: str):
    """Return the real FalkorDB connections for a decision."""
    try:
        trace = get_database().get_decision_trace(decision_id)

        if not trace["found"]:
            raise HTTPException(
                status_code=404,
                detail=f"No decision found with ID '{decision_id}'.",
            )

        return trace

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Could not retrieve decision trace from FalkorDB: {exc}",
        ) from exc

@app.get("/graph/overview")
def graph_overview():
    try:
        database = get_database()
        nodes = database.query(
            "MATCH (n) UNWIND labels(n) AS label RETURN label, count(*) AS count"
        )
        relationships = database.query(
            "MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS count"
        )
        return {"nodes_by_label": nodes, "relationships_by_type": relationships}
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"Could not inspect graph: {exc}"
        ) from exc
