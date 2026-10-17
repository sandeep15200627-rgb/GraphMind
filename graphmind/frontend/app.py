import html
import os
import time

import pandas as pd
import requests
import streamlit as st


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

API_BASE_URL = os.getenv(
    "GRAPHMIND_API_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

REQUEST_TIMEOUT = 60

EXAMPLE_QUESTIONS = [
    "Why did we migrate payment storage to PostgreSQL?",
    "What incidents affected order-service?",
    "Which decisions were made after an outage?",
]

st.set_page_config(
    page_title="GraphMind | Engineering Memory",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)


def h(markup: str) -> str:
    """Strip indentation so Markdown never treats HTML as a code block."""
    return "\n".join(line.strip() for line in markup.splitlines())


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""))


def clip(value, limit: int) -> str:
    text = str(value or "")
    return text if len(text) <= limit else text[: limit - 1] + "…"


# ---------------------------------------------------------
# Styling
# ---------------------------------------------------------

st.markdown(
    h(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

        :root {
            --ink: #070b14;
            --panel: rgba(255, 255, 255, 0.04);
            --line: rgba(255, 255, 255, 0.09);
            --text: #e6eaf2;
            --muted: #8c96ab;
            --violet: #8b7cff;
            --cyan: #3dd9eb;
            --amber: #ffb454;
            --green: #4ade80;
            --red: #ff6b7a;
        }

        html, body, [class*="css"], .stApp {
            font-family: 'Manrope', system-ui, sans-serif;
            color: var(--text);
        }

        .stApp {
            background:
                radial-gradient(900px 500px at 12% -8%, rgba(139, 124, 255, 0.22), transparent 60%),
                radial-gradient(800px 500px at 92% 4%, rgba(61, 217, 235, 0.14), transparent 60%),
                var(--ink);
        }

        header[data-testid="stHeader"] { background: transparent; }

        .block-container {
            padding-top: 2.2rem;
            padding-bottom: 3rem;
            max-width: 1200px;
        }

        section[data-testid="stSidebar"] {
            background: rgba(10, 15, 28, 0.85);
            border-right: 1px solid var(--line);
        }

        /* ---------- hero ---------- */
        .hero {
            position: relative;
            padding: 2.2rem 2.2rem 2rem;
            border: 1px solid var(--line);
            border-radius: 22px;
            margin-bottom: 1.6rem;
            background:
                linear-gradient(135deg, rgba(139, 124, 255, 0.12), rgba(61, 217, 235, 0.05) 60%),
                var(--panel);
            overflow: hidden;
        }
        .hero::after {
            content: "";
            position: absolute;
            inset: 0;
            background-image: radial-gradient(rgba(255,255,255,0.07) 1px, transparent 1px);
            background-size: 22px 22px;
            mask-image: linear-gradient(90deg, transparent 35%, #000 100%);
            -webkit-mask-image: linear-gradient(90deg, transparent 35%, #000 100%);
            pointer-events: none;
        }
        .hero h1 {
            position: relative;
            z-index: 1;
            font-size: 2.7rem;
            font-weight: 800;
            letter-spacing: -0.035em;
            line-height: 1.1;
            margin: 0 0 0.7rem;
            padding: 0;
            background: linear-gradient(95deg, #ffffff 0%, #c9c2ff 45%, #3dd9eb 100%);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }
        .hero p {
            position: relative;
            z-index: 1;
            max-width: 620px;
            color: #b6bfd2;
            font-size: 1.05rem;
            line-height: 1.6;
            margin: 0 0 1.1rem;
        }
        .chips { position: relative; z-index: 1; display: flex; gap: 0.5rem; flex-wrap: wrap; }
        .chip {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            padding: 0.3rem 0.7rem;
            border-radius: 999px;
            border: 1px solid var(--line);
            background: rgba(255, 255, 255, 0.05);
            color: #c8d0e0;
        }
        .chip b { color: var(--cyan); font-weight: 500; }

        /* ---------- status pills ---------- */
        .pill {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.55rem 0.8rem;
            margin-bottom: 0.45rem;
            border: 1px solid var(--line);
            border-radius: 10px;
            background: var(--panel);
            font-size: 0.86rem;
        }
        .pill span.state { font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; }
        .dot {
            display: inline-block;
            width: 8px; height: 8px;
            border-radius: 50%;
            margin-right: 0.55rem;
        }
        .ok .dot { background: var(--green); box-shadow: 0 0 10px var(--green); }
        .ok .state { color: var(--green); }
        .warn .dot { background: var(--amber); box-shadow: 0 0 10px var(--amber); }
        .warn .state { color: var(--amber); }
        .bad .dot { background: var(--red); box-shadow: 0 0 10px var(--red); }
        .bad .state { color: var(--red); }

        /* ---------- evidence ---------- */
        .badge {
            display: inline-block;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.68rem;
            padding: 0.12rem 0.5rem;
            border-radius: 6px;
            margin-right: 0.5rem;
            vertical-align: middle;
        }
        .badge.decision { color: var(--violet); background: rgba(139,124,255,0.14); border: 1px solid rgba(139,124,255,0.35); }
        .badge.incident { color: var(--amber); background: rgba(255,180,84,0.12); border: 1px solid rgba(255,180,84,0.35); }
        .badge.record   { color: var(--cyan);   background: rgba(61,217,235,0.10); border: 1px solid rgba(61,217,235,0.30); }
        .ev-title { font-weight: 700; font-size: 1.02rem; }
        .ev-meta { color: var(--muted); font-size: 0.86rem; margin-top: 0.35rem; line-height: 1.55; }
        .ev-meta b { color: #c3cbdc; font-weight: 600; }

        .trail {
            border: 1px solid var(--line);
            border-radius: 16px;
            background: var(--panel);
            padding: 0.6rem 0.8rem;
            margin: 0.4rem 0 1.2rem;
        }
        .trail-title { color: var(--muted); font-size: 0.82rem; margin: 0.2rem 0 0 0.3rem; }

        /* ---------- native widgets ---------- */
        div[data-testid="stMetric"] {
            border: 1px solid var(--line);
            background: var(--panel);
            padding: 1rem 1.1rem;
            border-radius: 14px;
        }
        div[data-testid="stMetricLabel"] p { color: var(--muted); }
        div[data-testid="stMetricValue"] { font-weight: 800; letter-spacing: -0.02em; }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 14px;
            border-color: var(--line);
        }

        div[data-testid="stTabs"] button[role="tab"] {
            font-weight: 600;
            padding: 0.6rem 1rem;
        }

        div.stButton > button, div[data-testid="stFormSubmitButton"] > button {
            border-radius: 10px;
            font-weight: 700;
            border: 1px solid var(--line);
            transition: border-color 0.15s, transform 0.15s;
        }
        div.stButton > button:hover { border-color: var(--violet); }
        div.stButton > button[kind="primary"],
        div[data-testid="stFormSubmitButton"] > button[kind="primary"] {
            background: linear-gradient(95deg, #7a6bff, #3dc7e8);
            border: none;
            color: #05070d;
        }
        div.stButton > button[kind="primary"]:hover,
        div[data-testid="stFormSubmitButton"] > button[kind="primary"]:hover {
            transform: translateY(-1px);
            filter: brightness(1.08);
        }

        textarea, input[type="text"] {
            border-radius: 12px !important;
            font-family: 'Manrope', sans-serif !important;
        }

        .muted { color: var(--muted); font-size: 0.92rem; }
        .foot { color: var(--muted); font-size: 0.8rem; text-align: center; padding-top: 0.5rem; }

        @media (prefers-reduced-motion: reduce) {
            * { transition: none !important; }
        }
        @media (max-width: 700px) {
            .hero h1 { font-size: 1.9rem; }
        }
        </style>
        """
    ),
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# API helpers
# ---------------------------------------------------------

def api_get(path: str) -> dict:
    """Call a GraphMind GET endpoint."""
    response = requests.get(
        f"{API_BASE_URL}{path}",
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def api_post(path: str, payload: dict) -> dict:
    """Call a GraphMind POST endpoint."""
    response = requests.post(
        f"{API_BASE_URL}{path}",
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def show_api_error(error: Exception) -> None:
    """Display useful API error information."""
    if isinstance(error, requests.HTTPError) and error.response is not None:
        try:
            details = error.response.json()
        except ValueError:
            details = error.response.text

        st.error(f"API returned HTTP {error.response.status_code}: {details}")
    elif isinstance(error, requests.ConnectionError):
        st.error(
            "Cannot reach the GraphMind backend. "
            f"Make sure FastAPI is running at {API_BASE_URL}."
        )
    elif isinstance(error, requests.Timeout):
        st.error(
            "The request timed out. The local model may need more time, "
            "especially on a laptop with limited RAM."
        )
    else:
        st.error(f"Something went wrong: {error}")


# ---------------------------------------------------------
# UI helpers
# ---------------------------------------------------------

def status_pill(label: str, state: str, text: str) -> None:
    st.markdown(
        h(
            f"""
            <div class="pill {state}">
                <div><span class="dot"></span>{esc(label)}</div>
                <span class="state">{esc(text)}</span>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def evidence_kind(item: dict) -> str:
    if item.get("decision"):
        return "decision"
    if item.get("incident"):
        return "incident"
    return "record"


def evidence_title(item: dict, index: int) -> str:
    return (
        item.get("decision")
        or item.get("incident")
        or item.get("source_title")
        or f"Evidence record {index}"
    )


def evidence_trail_svg(question: str, evidence: list, answer_mode: str) -> str:
    """Draw the path from the question through graph evidence to the answer."""
    shown = evidence[:6]
    n = max(len(shown), 1)
    row = 58
    height = max(150, n * row + 40)
    mid = height / 2

    colors = {
        "decision": ("#8b7cff", "rgba(139,124,255,0.14)"),
        "incident": ("#ffb454", "rgba(255,180,84,0.12)"),
        "record": ("#3dd9eb", "rgba(61,217,235,0.10)"),
    }

    parts = [
        f'<svg viewBox="0 0 900 {height}" width="100%" xmlns="http://www.w3.org/2000/svg" '
        'font-family="Manrope, sans-serif">',
        "<defs>"
        '<linearGradient id="flow" x1="0" x2="1">'
        '<stop offset="0" stop-color="#8b7cff"/><stop offset="1" stop-color="#3dd9eb"/>'
        "</linearGradient></defs>",
    ]

    ys = [
        (height - (len(shown) - 1) * row) / 2 + i * row for i in range(len(shown))
    ] or [mid]

    # edges first so nodes sit on top
    for y in ys:
        parts.append(
            f'<path d="M 190 {mid} C 290 {mid}, 300 {y}, 340 {y}" '
            'stroke="url(#flow)" stroke-width="1.6" fill="none" opacity="0.7"/>'
        )
        parts.append(
            f'<path d="M 570 {y} C 610 {y}, 620 {mid}, 710 {mid}" '
            'stroke="url(#flow)" stroke-width="1.6" fill="none" opacity="0.7"/>'
        )

    # question node
    parts.append(
        f'<rect x="20" y="{mid - 26}" width="170" height="52" rx="12" '
        'fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.25)"/>'
        f'<text x="105" y="{mid - 3}" fill="#8c96ab" font-size="10" text-anchor="middle">QUESTION</text>'
        f'<text x="105" y="{mid + 14}" fill="#e6eaf2" font-size="11" text-anchor="middle">'
        f"{esc(clip(question, 22))}</text>"
    )

    # evidence nodes
    for item, y in zip(shown, ys):
        kind = evidence_kind(item)
        stroke, fill = colors[kind]
        title = clip(evidence_title(item, 0), 30)
        sub = item.get("service") or kind
        parts.append(
            f'<rect x="340" y="{y - 22}" width="230" height="44" rx="10" '
            f'fill="{fill}" stroke="{stroke}" stroke-opacity="0.6"/>'
            f'<circle cx="358" cy="{y}" r="4" fill="{stroke}"/>'
            f'<text x="372" y="{y - 3}" fill="#e6eaf2" font-size="11.5" font-weight="600">{esc(title)}</text>'
            f'<text x="372" y="{y + 12}" fill="#8c96ab" font-size="9.5">{esc(clip(sub, 34))}</text>'
        )

    if not shown:
        parts.append(
            f'<text x="455" y="{mid + 4}" fill="#8c96ab" font-size="12" text-anchor="middle">'
            "No graph evidence matched</text>"
        )

    # answer node
    parts.append(
        f'<rect x="710" y="{mid - 26}" width="170" height="52" rx="12" '
        'fill="rgba(61,217,235,0.10)" stroke="#3dd9eb" stroke-opacity="0.7"/>'
        f'<text x="795" y="{mid - 3}" fill="#3dd9eb" font-size="10" text-anchor="middle">ANSWER</text>'
        f'<text x="795" y="{mid + 14}" fill="#e6eaf2" font-size="11" text-anchor="middle">'
        f"{esc(clip(answer_mode, 22))}</text>"
    )

    parts.append("</svg>")
    return "".join(parts)


def records_to_frame(records: list) -> pd.DataFrame:
    """Turn [{label/type: name, count: n}] into a name-indexed frame."""
    rows = []
    for record in records:
        count = record.get("count", 0)
        try:
            count = int(count)
        except (TypeError, ValueError):
            count = 0
        name = next(
            (str(v) for k, v in record.items() if k != "count"),
            "unknown",
        )
        rows.append({"name": name, "count": count})
    if not rows:
        return pd.DataFrame(columns=["count"])
    return pd.DataFrame(rows).set_index("name")


def use_example(text: str) -> None:
    st.session_state["question_input"] = text


# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------

with st.sidebar:
    st.markdown("### 🧠 GraphMind")
    st.caption("Persistent engineering memory")

    st.divider()
    st.markdown("**System status**")

    if st.button("↻ Refresh status", use_container_width=True):
        st.rerun()

    try:
        health = api_get("/health")

        status_pill("FastAPI", "ok", "connected")

        if health.get("falkordb") == "ok":
            status_pill("FalkorDB", "ok", "connected")
        else:
            status_pill("FalkorDB", "warn", str(health.get("falkordb", "unknown")))

        if health.get("ollama") == "ok":
            status_pill("Ollama", "ok", "reachable")
        else:
            status_pill("Ollama", "warn", str(health.get("ollama", "unknown")))

        if health.get("ollama") == "ok":
            if health.get("configured_model_available"):
                st.caption(
                    f"Model: {health.get('ollama_model', 'configured model')}"
                )
            else:
                st.warning(
                    "The configured model was not found in Ollama's "
                    "available model list."
                )

    except requests.RequestException as exc:
        status_pill("FastAPI", "bad", "offline")
        st.caption(str(exc))

    st.divider()
    st.markdown("**How it works**")
    st.markdown(
        h(
            """
            <div class="muted">
            Your question is matched against the graph, the connected
            decisions and incidents become the evidence, and the local
            model writes an answer from that evidence only.
            </div>
            """
        ),
        unsafe_allow_html=True,
    )
    st.code(
        "Streamlit\n    ↓\nFastAPI\n    ↓\nFalkorDB + Ollama",
        language="text",
    )
    st.caption("Runs on a local model. No paid model API required.")


# ---------------------------------------------------------
# Header
# ---------------------------------------------------------

st.markdown(
    h(
        """
        <div class="hero">
            <h1>Engineering knowledge,<br>connected.</h1>
            <p>
                Ask why a decision was made, trace an incident to its fix,
                and keep the reasoning behind your engineering work
                from disappearing.
            </p>
            <div class="chips">
                <span class="chip"><b>graph</b> FalkorDB</span>
                <span class="chip"><b>api</b> FastAPI</span>
                <span class="chip"><b>llm</b> Ollama, local</span>
                <span class="chip"><b>answers</b> cited from evidence</span>
            </div>
        </div>
        """
    ),
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Main dashboard
# ---------------------------------------------------------

ask_tab, memory_tab, graph_tab = st.tabs(
    ["💬 Ask GraphMind", "📝 Add Memory", "🕸️ Graph Overview"]
)


# ---------------------------------------------------------
# Tab 1: Ask GraphMind
# ---------------------------------------------------------

with ask_tab:
    st.markdown("#### Ask your engineering memory")
    st.markdown(
        '<div class="muted">Ask about decisions, incidents, services, '
        "or the evidence behind a technical choice.</div>",
        unsafe_allow_html=True,
    )

    st.write("")
    st.caption("Try one of these")
    example_cols = st.columns(len(EXAMPLE_QUESTIONS))
    for col, example in zip(example_cols, EXAMPLE_QUESTIONS):
        with col:
            st.button(
                example,
                key=f"example_{example}",
                on_click=use_example,
                args=(example,),
                use_container_width=True,
            )

    with st.form("ask_form"):
        question = st.text_area(
            "Your question",
            key="question_input",
            placeholder="Why did we migrate payment storage to PostgreSQL?",
            height=100,
            max_chars=1000,
        )

        submitted = st.form_submit_button(
            "Ask GraphMind",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if not question.strip():
            st.warning("Enter a question first.")
        elif len(question.strip()) < 3:
            st.warning("Please enter at least 3 characters.")
        else:
            try:
                started = time.perf_counter()
                with st.status("Working on it…", expanded=True) as status:
                    st.write("Searching the graph for connected evidence")
                    st.write("Generating an answer with the local model")
                    result = api_post("/ask", {"question": question.strip()})
                    elapsed = time.perf_counter() - started
                    status.update(
                        label=f"Answered in {elapsed:.1f}s",
                        state="complete",
                        expanded=False,
                    )

                result["_question"] = question.strip()
                result["_seconds"] = elapsed
                st.session_state["last_answer"] = result

                history = st.session_state.setdefault("history", [])
                history.insert(
                    0,
                    {
                        "question": question.strip(),
                        "answer": result.get("answer", ""),
                    },
                )
                del history[8:]

            except requests.RequestException as exc:
                show_api_error(exc)

    result = st.session_state.get("last_answer")

    if result:
        evidence = result.get("evidence", []) or []

        st.divider()

        st.markdown(
            h(
                f"""
                <div class="trail">
                    {evidence_trail_svg(
                        result.get("_question", ""),
                        evidence,
                        result.get("model_used", "unknown"),
                    )}
                    <div class="trail-title">
                        Evidence trail: how the graph connects your question to this answer
                    </div>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )

        st.markdown("#### Answer")
        with st.container(border=True):
            st.markdown(result.get("answer", "No answer returned."))

        metric1, metric2, metric3 = st.columns(3)

        with metric1:
            st.metric(
                "Supporting graph records",
                result.get("evidence_count", len(evidence)),
            )

        with metric2:
            st.metric("Answer mode", result.get("model_used", "unknown"))

        with metric3:
            st.metric("Response time", f"{result.get('_seconds', 0):.1f}s")

        with st.expander(
            f"Inspect supporting evidence ({len(evidence)} records)",
            expanded=True,
        ):
            if not evidence:
                st.info(
                    "No matching graph evidence was found. "
                    "Try a different question or add a relevant memory."
                )
            else:
                for index, item in enumerate(evidence, start=1):
                    kind = evidence_kind(item)
                    title = evidence_title(item, index)

                    meta = []
                    if item.get("incident") and kind != "incident":
                        meta.append(f"<b>Incident</b> {esc(item['incident'])}")
                    if item.get("service"):
                        meta.append(f"<b>Service</b> {esc(item['service'])}")
                    if item.get("rationale"):
                        meta.append(f"<b>Rationale</b> {esc(item['rationale'])}")
                    if item.get("source_title"):
                        meta.append(f"<b>Source</b> {esc(item['source_title'])}")

                    with st.container(border=True):
                        st.markdown(
                            h(
                                f"""
                                <div>
                                    <span class="badge {kind}">{kind}</span>
                                    <span class="ev-title">{index}. {esc(title)}</span>
                                </div>
                                <div class="ev-meta">{"<br>".join(meta)}</div>
                                """
                            ),
                            unsafe_allow_html=True,
                        )

                        if item.get("source_content"):
                            st.caption(item["source_content"])

                        with st.expander("View complete record"):
                            st.json(item)

    history = st.session_state.get("history", [])
    if len(history) > 1:
        with st.expander("Recent questions"):
            for entry in history[1:]:
                st.markdown(f"**{entry['question']}**")
                st.caption(clip(entry["answer"], 220))


# ---------------------------------------------------------
# Tab 2: Add Memory
# ---------------------------------------------------------

with memory_tab:
    st.markdown("#### Preserve engineering knowledge")
    st.markdown(
        '<div class="muted">Record a decision or incident so future '
        "questions can use that information.</div>",
        unsafe_allow_html=True,
    )
    st.write("")

    memory_kind = st.radio(
        "Memory type",
        options=["decision", "incident"],
        format_func=lambda value: value.title(),
        horizontal=True,
        key="memory_kind",
    )

    with st.form("memory_form", clear_on_submit=False):
        title = st.text_input(
            "Title",
            placeholder=(
                "Enable retry logic for order-service"
                if memory_kind == "decision"
                else "Order processing failures during peak traffic"
            ),
            max_chars=200,
        )

        content = st.text_area(
            "Description / supporting evidence",
            placeholder=(
                "Describe what the team decided and the relevant "
                "technical evidence."
            ),
            height=140,
            max_chars=5000,
        )

        service = st.text_input(
            "Affected service (optional)",
            placeholder="order-service",
            max_chars=120,
        )

        rationale = None
        incident_id = None

        if memory_kind == "decision":
            rationale = st.text_area(
                "Decision rationale (optional)",
                placeholder="Explain why this decision was made.",
                height=90,
                max_chars=2000,
            )

            incident_id = st.text_input(
                "Existing incident ID (optional)",
                placeholder="INC-101",
                help=(
                    "Connect this decision to an existing incident "
                    "using its exact graph ID."
                ),
            )

        save_clicked = st.form_submit_button(
            "Save to GraphMind",
            type="primary",
            use_container_width=True,
        )

    if save_clicked:
        if len(title.strip()) < 3:
            st.warning("The title must contain at least 3 characters.")
        elif len(content.strip()) < 5:
            st.warning(
                "Provide at least 5 characters of description or evidence."
            )
        else:
            payload = {
                "kind": memory_kind,
                "title": title.strip(),
                "content": content.strip(),
                "service": service.strip() or None,
            }

            if memory_kind == "decision":
                payload["rationale"] = rationale.strip() if rationale else None
                payload["incident_id"] = (
                    incident_id.strip() if incident_id else None
                )

            try:
                with st.spinner("Saving memory to FalkorDB..."):
                    saved = api_post("/memories", payload)

                st.success("Memory saved.")
                st.toast("Saved to the graph", icon="🧠")

                with st.expander("Saved record details", expanded=True):
                    st.json(saved)

                st.info(
                    "Open Ask GraphMind and ask about this memory "
                    "to test retrieval."
                )

            except requests.RequestException as exc:
                show_api_error(exc)


# ---------------------------------------------------------
# Tab 3: Graph Overview
# ---------------------------------------------------------

with graph_tab:
    st.markdown("#### Explore the knowledge graph")
    st.markdown(
        '<div class="muted">See the node labels and relationship types '
        "currently stored in FalkorDB.</div>",
        unsafe_allow_html=True,
    )
    st.write("")

    if st.button("Load graph statistics", type="primary", key="load_graph"):
        try:
            st.session_state["graph_overview"] = api_get("/graph/overview")
        except requests.RequestException as exc:
            show_api_error(exc)

    overview = st.session_state.get("graph_overview")

    if overview:
        nodes = overview.get("nodes_by_label", [])
        relationships = overview.get("relationships_by_type", [])

        node_df = records_to_frame(nodes)
        rel_df = records_to_frame(relationships)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total nodes", int(node_df["count"].sum()))
        with col2:
            st.metric("Total relationships", int(rel_df["count"].sum()))
        with col3:
            st.metric("Node labels", len(node_df))

        left, right = st.columns(2)

        with left:
            st.markdown("##### Nodes by label")
            if len(node_df):
                st.bar_chart(node_df, color="#8b7cff", height=240)
                st.dataframe(nodes, use_container_width=True, hide_index=True)
            else:
                st.info("No labeled nodes found.")

        with right:
            st.markdown("##### Relationships by type")
            if len(rel_df):
                st.bar_chart(rel_df, color="#3dd9eb", height=240)
                st.dataframe(
                    relationships, use_container_width=True, hide_index=True
                )
            else:
                st.info("No relationships found.")

        with st.expander("Raw API response"):
            st.json(overview)

    else:
        st.info("Select 'Load graph statistics' to inspect the current graph.")


# ---------------------------------------------------------
# Footer
# ---------------------------------------------------------

st.divider()

st.markdown(
    '<div class="foot">GraphMind · Evidence-grounded engineering memory · '
    "FalkorDB + FastAPI + Ollama</div>",
    unsafe_allow_html=True,
)
