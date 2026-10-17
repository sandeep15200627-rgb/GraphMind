
from functools import lru_cache
from uuid import uuid4

from falkordb import FalkorDB

from backend.config import (
    FALKORDB_GRAPH,
    FALKORDB_HOST,
    FALKORDB_PORT,
)


class GraphDatabase:
    """Adapter that connects GraphMind to FalkorDB."""

    def __init__(self):
        client = FalkorDB(
            host=FALKORDB_HOST,
            port=FALKORDB_PORT,
        )
        self.graph = client.select_graph(FALKORDB_GRAPH)

    def query(
        self,
        cypher: str,
        params: dict | None = None,
    ) -> list[dict]:
        """Execute one Cypher query and return rows as dictionaries."""
        result = self.graph.query(cypher, params=params or {})

        headers = []
        for column in result.header:
            # Some FalkorDB client versions return headers like
            # [1, "label"] instead of simply "label".
            if isinstance(column, (list, tuple)) and len(column) >= 2:
                headers.append(str(column[1]))
            else:
                headers.append(str(column))

        return [
            dict(zip(headers, row))
            for row in result.result_set
        ]

    def ping(self) -> bool:
        """Check that the graph database responds to a simple query."""
        self.query("RETURN 1 AS ok")
        return True

    def seed_demo_data(self) -> None:
        """Insert the GraphMind demonstration memories without duplicates."""

        # Incident 1
        self.query(
            """
            MERGE (i:Incident {id: $id})
            SET i.title = $title,
                i.description = $description
            """,
            {
                "id": "INC-101",
                "title": "Payment failures during peak traffic",
                "description": (
                    "Payment requests failed during peak traffic, "
                    "highlighting transaction reliability and recovery concerns."
                ),
            },
        )

        # Source 1
        self.query(
            """
            MERGE (src:Source {id: $id})
            SET src.title = $title,
                src.content = $content
            """,
            {
                "id": "DOC-301",
                "title": "Payment migration review",
                "content": (
                    "The team selected PostgreSQL after reviewing "
                    "transaction consistency and recovery requirements."
                ),
            },
        )

        # Decision 1 and its graph relationships
        self.query(
            """
            MERGE (d:Decision {id: $decision_id})
            SET d.title = $title,
                d.rationale = $rationale
            WITH d
            MATCH (i:Incident {id: $incident_id})
            MATCH (src:Source {id: $source_id})
            MERGE (d)-[:MOTIVATED_BY]->(i)
            MERGE (d)-[:SUPPORTED_BY]->(src)
            MERGE (d)-[:AFFECTS]->(:Service {
                name: $service,
                id: $service_id
            })
            """,
            {
                "decision_id": "DEC-201",
                "title": "Migrate payment storage to PostgreSQL",
                "rationale": (
                    "Improve transaction reliability and recovery."
                ),
                "incident_id": "INC-101",
                "source_id": "DOC-301",
                "service": "payment-service",
                "service_id": "SVC-101",
            },
        )

        # Incident 2
        self.query(
            """
            MERGE (i:Incident {id: $id})
            SET i.title = $title,
                i.description = $description
            """,
            {
                "id": "INC-102",
                "title": "Notification delays after queue buildup",
                "description": (
                    "Notifications were delayed when the processing "
                    "queue accumulated work."
                ),
            },
        )

        # Source 2
        self.query(
            """
            MERGE (src:Source {id: $id})
            SET src.title = $title,
                src.content = $content
            """,
            {
                "id": "DOC-302",
                "title": "Notification reliability review",
                "content": (
                    "The team reviewed queue buildup and identified "
                    "monitoring as a reliability improvement."
                ),
            },
        )

        # Decision 2 and its graph relationships
        self.query(
            """
            MERGE (d:Decision {id: $decision_id})
            SET d.title = $title,
                d.rationale = $rationale
            WITH d
            MATCH (i:Incident {id: $incident_id})
            MATCH (src:Source {id: $source_id})
            MERGE (d)-[:MOTIVATED_BY]->(i)
            MERGE (d)-[:SUPPORTED_BY]->(src)
            MERGE (d)-[:AFFECTS]->(:Service {
                name: $service,
                id: $service_id
            })
            """,
            {
                "decision_id": "DEC-202",
                "title": "Add queue monitoring to notification-service",
                "rationale": (
                    "Detect queue buildup earlier and improve "
                    "notification reliability."
                ),
                "incident_id": "INC-102",
                "source_id": "DOC-302",
                "service": "notification-service",
                "service_id": "SVC-102",
            },
        )

    def retrieve_evidence(self) -> list[dict]:
        """Retrieve decisions together with connected incidents,
        services, and supporting source documents.
        """
        return self.query(
            """
            MATCH (d:Decision)
            OPTIONAL MATCH (d)-[:MOTIVATED_BY]->(i:Incident)
            OPTIONAL MATCH (d)-[:AFFECTS]->(s:Service)
            OPTIONAL MATCH (d)-[:SUPPORTED_BY]->(src:Source)
            RETURN
                d.id AS decision_id,
                d.title AS decision,
                d.rationale AS rationale,
                i.id AS incident_id,
                i.title AS incident,
                i.description AS incident_description,
                s.name AS service,
                src.id AS source_id,
                src.title AS source_title,
                src.content AS source_content,
                'decision' AS record_type
            """
        )
    
    def get_decision_trace(self, decision_id: str) -> dict:
        """Return a decision and its directly connected graph evidence."""

        rows = self.query(
            """
            MATCH (d:Decision {id: $decision_id})
            OPTIONAL MATCH (d)-[r]->(n)
            RETURN
                properties(d) AS decision,
                type(r) AS relationship,
                labels(n) AS target_labels,
                properties(n) AS target
            """,
            {"decision_id": decision_id},
        )

        if not rows:
            return {
                "found": False,
                "decision": None,
                "nodes": [],
                "edges": [],
            }

        decision = rows[0]["decision"]
        nodes = [
            {
                "id": decision.get("id"),
                "label": "Decision",
                "title": decision.get("title", ""),
                "properties": decision,
            }
        ]
        edges = []
        seen_nodes = {decision.get("id")}

        for row in rows:
            target = row.get("target")
            relationship = row.get("relationship")

            if not target or not relationship:
                continue

            target_id = target.get("id") or target.get("name")

            if target_id is None:
                continue

            target_id = str(target_id)

            if target_id not in seen_nodes:
                labels = row.get("target_labels") or []
                label = labels[0] if labels else "Node"

                nodes.append(
                    {
                        "id": target_id,
                        "label": label,
                        "title": (
                            target.get("title")
                            or target.get("name")
                            or target_id
                        ),
                        "properties": target,
                    }
                )
                seen_nodes.add(target_id)

            edges.append(
                {
                    "source": decision.get("id"),
                    "target": target_id,
                    "relationship": relationship,
                }
            )

        return {
            "found": True,
            "decision": decision,
            "nodes": nodes,
            "edges": edges,
        }

    def save_memory(
        self,
        kind: str,
        title: str,
        content: str,
        service: str | None = None,
        rationale: str | None = None,
        incident_id: str | None = None,
    ) -> dict:
        """Save a new incident or decision and connect related graph nodes."""

        memory_id = f"{kind.upper()}-{uuid4().hex[:12]}"

        if kind == "incident":
            self.query(
                """
                CREATE (i:Incident {
                    id: $id,
                    title: $title,
                    description: $content
                })
                """,
                {
                    "id": memory_id,
                    "title": title,
                    "content": content,
                },
            )

            return {
                "id": memory_id,
                "kind": "incident",
                "title": title,
            }

        if kind != "decision":
            raise ValueError("kind must be 'decision' or 'incident'")

        # A decision should always have a supporting source record.
        source_id = f"SOURCE-{uuid4().hex[:12]}"

        self.query(
            """
            CREATE (src:Source {
                id: $source_id,
                title: $title,
                content: $content
            })
            """,
            {
                "source_id": source_id,
                "title": f"Evidence for: {title}",
                "content": content,
            },
        )

        self.query(
            """
            CREATE (d:Decision {
                id: $id,
                title: $title,
                rationale: $rationale
            })
            """,
            {
                "id": memory_id,
                "title": title,
                "rationale": rationale or "",
            },
        )

        self.query(
            """
            MATCH (d:Decision {id: $decision_id})
            MATCH (src:Source {id: $source_id})
            MERGE (d)-[:SUPPORTED_BY]->(src)
            """,
            {
                "decision_id": memory_id,
                "source_id": source_id,
            },
        )

        if service:
            service_id = f"SVC-{service}"
            self.query(
                """
                MERGE (s:Service {id: $service_id})
                SET s.name = $service
                WITH s
                MATCH (d:Decision {id: $decision_id})
                MERGE (d)-[:AFFECTS]->(s)
                """,
                {
                    "service_id": service_id,
                    "service": service,
                    "decision_id": memory_id,
                },
            )

        if incident_id:
            existing = self.query(
                """
                MATCH (i:Incident {id: $incident_id})
                RETURN i.id AS id
                """,
                {"incident_id": incident_id},
            )

            if not existing:
                raise ValueError(
                    f"No incident found with ID '{incident_id}'."
                )

            self.query(
                """
                MATCH (d:Decision {id: $decision_id})
                MATCH (i:Incident {id: $incident_id})
                MERGE (d)-[:MOTIVATED_BY]->(i)
                """,
                {
                    "decision_id": memory_id,
                    "incident_id": incident_id,
                },
            )

        return {
            "id": memory_id,
            "kind": "decision",
            "title": title,
            "source_id": source_id,
            "service": service,
            "incident_id": incident_id,
        }


@lru_cache(maxsize=1)
def get_database() -> GraphDatabase:
    """Reuse one graph adapter during this Python process."""
    return GraphDatabase()
