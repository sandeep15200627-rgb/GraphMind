from backend.agent import build_fallback_answer, retrieve_relevant_evidence, tokenize


def test_tokenize_removes_common_stop_words():
    assert "postgresql" in tokenize("Why did we choose PostgreSQL?")
    assert "why" not in tokenize("Why did we choose PostgreSQL?")


def test_retrieval_ranks_matching_graph_evidence():
    class FakeDatabase:
        def retrieve_evidence(self):
            return [
                {
                    "record_type": "decision_path",
                    "decision": "Migrate payment storage to PostgreSQL",
                    "rationale": "Improve transaction reliability",
                    "incident": "Payment failures during peak traffic",
                    "service": "payment-service",
                    "source_title": "Payment migration review",
                    "source_content": "Transaction consistency and recovery requirements",
                },
                {
                    "record_type": "decision_path",
                    "decision": "Add queue monitoring",
                    "rationale": "Detect queue buildup",
                    "incident": "Notification delays",
                    "service": "notification-service",
                    "source_title": "Notification review",
                    "source_content": "Queue depth alerts",
                },
            ]

    results = retrieve_relevant_evidence(
        "Why did payment storage migrate to PostgreSQL?", FakeDatabase()
    )
    assert results
    assert results[0]["service"] == "payment-service"


def test_fallback_explains_missing_evidence():
    answer = build_fallback_answer([])
    assert "couldn't find matching evidence" in answer.lower()
