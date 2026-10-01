"""Streamlit multipage frontend – Code Lore."""

import streamlit as st

# ── Page Config (must be first Streamlit call) ───────────────────────
st.set_page_config(
    page_title="Code Lore – Understand Any Code",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --bg-primary: #0e1117;
    --bg-card: #161b22;
    --border: #30363d;
    --accent: #58a6ff;
    --accent-green: #3fb950;
    --accent-orange: #d29922;
    --accent-red: #f85149;
    --text-primary: #e6edf3;
    --text-secondary: #8b949e;
}

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}
code, pre, .stCodeBlock {
    font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
}

/* Card styling */
div[data-testid="stExpander"] {
    border: 1px solid var(--border);
    border-radius: 8px;
    margin-bottom: 0.5rem;
}

/* Metric cards */
div[data-testid="stMetric"] {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px 16px;
}
div[data-testid="stMetric"] label {
    color: var(--text-secondary) !important;
    font-size: 0.75rem !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-weight: 700 !important;
    color: var(--accent) !important;
}

/* Sidebar polish */
section[data-testid="stSidebar"] {
    border-right: 1px solid var(--border);
}
section[data-testid="stSidebar"] .stMarkdown h1 {
    font-size: 1.3rem !important;
    font-weight: 700;
    letter-spacing: -0.01em;
}

/* Tab styling */
button[data-baseweb="tab"] {
    font-weight: 600 !important;
    font-size: 0.85rem !important;
}

/* Quiz option buttons */
.quiz-option {
    padding: 10px 16px;
    border: 1px solid var(--border);
    border-radius: 6px;
    margin: 4px 0;
    cursor: pointer;
    transition: border-color 0.2s;
}
.quiz-option:hover { border-color: var(--accent); }

/* Block card */
.block-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 12px;
}
.block-card h4 {
    margin: 0 0 8px 0;
    color: var(--accent);
    font-size: 0.95rem;
}
.block-card .line-ref {
    font-size: 0.75rem;
    color: var(--text-secondary);
    font-family: 'JetBrains Mono', monospace;
}

/* Trace step */
.trace-step {
    border-left: 3px solid var(--accent);
    padding-left: 12px;
    margin-bottom: 8px;
}

/* Concept chip */
.concept-chip {
    display: inline-block;
    padding: 4px 10px;
    margin: 2px 4px;
    border: 1px solid var(--accent);
    border-radius: 16px;
    font-size: 0.8rem;
    color: var(--accent);
}

/* Status dot */
.status-dot {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    margin-right: 6px;
}
.status-dot.green { background: var(--accent-green); }
.status-dot.red   { background: var(--accent-red); }
.status-dot.orange { background: var(--accent-orange); }
</style>
""", unsafe_allow_html=True)

# ── Imports ──────────────────────────────────────────────────────────
from frontend.utils.api_client import APIClient

# ── Session State Defaults ───────────────────────────────────────────
DEFAULTS = {
    "explanation_result": None,
    "ast_result": None,
    "trace_result": None,
    "quiz_result": None,
    "quiz_answers": {},
    "quiz_submitted": False,
    "current_code": "",
    "current_language": "python",
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── API Client & Health ──────────────────────────────────────────────
client = APIClient()

# ── Code Examples ────────────────────────────────────────────────────
PYTHON_EXAMPLE = '''import math

def calculate_hypotenuse(a: float, b: float) -> float:
    """Compute hypotenuse using Pythagorean theorem."""
    if a <= 0 or b <= 0:
        raise ValueError("Sides must be positive")
    return math.sqrt(a**2 + b**2)

result = calculate_hypotenuse(3, 4)
print(f"Hypotenuse: {result}")
'''

JS_EXAMPLE = '''function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
'''

# ── Sidebar ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("# 📜 Code Lore")
    st.caption("Understand any code, deeply.")
    st.divider()

    # Health indicator
    health = client.check_health()
    if health and health.get("status") == "healthy":
        st.markdown('<span class="status-dot green"></span> **Backend Online**', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-dot red"></span> **Backend Offline**', unsafe_allow_html=True)
        st.error("The FastAPI backend is unreachable. Start it with:\n```\nuvicorn backend.main:app --port 8000\n```")

    st.divider()
    st.markdown("#### ⚙️ Settings")

    language = st.selectbox(
        "Language",
        options=["python", "javascript", "auto"],
        index=0,
        help="Select the language of your code snippet",
    )

    level = st.selectbox(
        "Explanation Level",
        options=["Absolute Beginner", "Beginner", "Intermediate"],
        index=1,
    )

    include_ast = st.toggle("Include AST Analysis", value=True)
    save_history = st.toggle("Save to History", value=True)

    st.divider()
    st.markdown("#### 🧭 Navigation")
    page = st.radio(
        "Go to",
        options=[
            "📝 Code Input",
            "📖 Explanation",
            "📚 Concepts",
            "🔬 Trace & Flowchart",
            "🧩 Quiz",
            "📜 History",
        ],
        label_visibility="collapsed",
    )

# ════════════════════════════════════════════════════════════════════
# PAGE 1 – CODE INPUT
# ════════════════════════════════════════════════════════════════════
if page == "📝 Code Input":
    st.markdown("## 📝 Code Input")
    st.markdown("Paste your code below, choose a language and explanation level, then click **Analyze**.")

    col_editor, col_preview = st.columns([3, 2], gap="medium")

    with col_editor:
        default_code = PYTHON_EXAMPLE if language in ("python", "auto") else JS_EXAMPLE
        code_input = st.text_area(
            "Code Editor",
            value=st.session_state.get("current_code") or default_code,
            height=380,
            key="code_editor_main",
            label_visibility="collapsed",
            placeholder="Paste your Python or JavaScript code here…",
        )

        col_b1, col_b2, col_b3 = st.columns(3)
        with col_b1:
            analyze_btn = st.button("✨ Analyze & Explain", type="primary", use_container_width=True)
        with col_b2:
            ast_btn = st.button("🔍 AST Only", use_container_width=True)
        with col_b3:
            trace_btn = st.button("🔬 Trace Code", use_container_width=True)

    with col_preview:
        st.markdown("##### Preview")
        if code_input.strip():
            lang_preview = language if language != "auto" else "python"
            st.code(code_input, language=lang_preview, line_numbers=True)
            line_count = len(code_input.splitlines())
            st.caption(f"{line_count} lines · {len(code_input)} characters · {language}")
        else:
            st.info("Enter code on the left to see a preview.")

    # ── Analyze button handler ───────────────────────────────────────
    if analyze_btn:
        if not code_input.strip():
            st.warning("⚠️ Please enter some code to analyze.")
        elif not health:
            st.error("🔴 Cannot reach the backend. Please start it first.")
        else:
            st.session_state["current_code"] = code_input
            st.session_state["current_language"] = language
            with st.spinner("🧠 Analyzing code structure and generating explanation…"):
                try:
                    result = client.explain_code(
                        code=code_input,
                        language=language,
                        level=level,
                        include_ast=include_ast,
                        save_history=save_history,
                    )
                    st.session_state["explanation_result"] = result
                    st.success("✅ Analysis complete! Navigate to **📖 Explanation** to see results.")
                except Exception as e:
                    st.error(f"❌ Explanation failed: {str(e)}")

    if ast_btn:
        if not code_input.strip():
            st.warning("⚠️ Please enter some code to analyze.")
        elif not health:
            st.error("🔴 Cannot reach the backend.")
        else:
            st.session_state["current_code"] = code_input
            with st.spinner("🔍 Running AST analysis…"):
                try:
                    ast_result = client.analyze_ast(code_input, language)
                    st.session_state["ast_result"] = ast_result
                    st.success("✅ AST analysis complete!")
                    with st.expander("📋 Raw AST Output", expanded=False):
                        st.json(ast_result)
                except Exception as e:
                    st.error(f"❌ AST analysis failed: {str(e)}")

    if trace_btn:
        if not code_input.strip():
            st.warning("⚠️ Please enter some code to trace.")
        elif not health:
            st.error("🔴 Cannot reach the backend.")
        else:
            st.session_state["current_code"] = code_input
            with st.spinner("🔬 Tracing execution…"):
                try:
                    trace_result = client.trace_code(
                        code=code_input,
                        language=language,
                        generate_flowchart=True,
                    )
                    st.session_state["trace_result"] = trace_result
                    st.success("✅ Trace complete! Navigate to **🔬 Trace & Flowchart**.")
                except Exception as e:
                    st.error(f"❌ Trace failed: {str(e)}")


# ════════════════════════════════════════════════════════════════════
# PAGE 2 – EXPLANATION VIEW
# ════════════════════════════════════════════════════════════════════
elif page == "📖 Explanation":
    st.markdown("## 📖 Code Explanation")

    result = st.session_state.get("explanation_result")
    if not result:
        st.info("No explanation yet. Go to **📝 Code Input** and click **Analyze & Explain**.")
    else:
        code = st.session_state.get("current_code", "")
        code_lines = code.splitlines()
        lang = result.get("language", "python")

        # ── Summary Card ─────────────────────────────────────────
        st.markdown(f"""
> **Summary**
>
> {result.get('summary', 'No summary available.')}
""")

        # ── Metrics Row ──────────────────────────────────────────
        ast_data = result.get("ast_analysis")
        if ast_data:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Complexity", ast_data.get("complexity_score", 1))
            m2.metric("Max Nesting", ast_data.get("max_nesting_depth", 0))
            metrics = ast_data.get("metrics", {})
            m3.metric("Functions", metrics.get("num_functions", 0))
            m4.metric("Static Hints", len(ast_data.get("static_hints", [])))

            # Static hints
            hints = ast_data.get("static_hints", [])
            if hints:
                st.markdown("#### ⚠️ Static Analysis Hints")
                for h in hints:
                    icon = "🟡" if h["severity"] == "warning" else "🔵"
                    st.warning(f"{icon} **[{h['rule_id']}]** Line {h['line_start']}: {h['message']}\n\n💡 *{h.get('suggestion', '')}*")

        st.divider()

        # ── Block-by-Block Explanations ──────────────────────────
        st.markdown("### 🧩 Block-by-Block Explanations")
        blocks = result.get("blocks", [])
        if blocks:
            for block in blocks:
                ls = block.get("line_start", 1)
                le = block.get("line_end", ls)
                with st.expander(f"**{block['title']}** — Lines {ls}–{le}", expanded=True):
                    col_code, col_expl = st.columns([1, 1], gap="medium")
                    with col_code:
                        # Show just the relevant source lines
                        snippet_lines = code_lines[max(0, ls - 1):le]
                        numbered = "\n".join(
                            f"{i + ls}: {line}" for i, line in enumerate(snippet_lines)
                        )
                        st.code(numbered, language=lang)
                    with col_expl:
                        st.markdown(block.get("explanation", ""))
        else:
            st.info("No block explanations available.")

        st.divider()

        # ── Concept Tags ─────────────────────────────────────────
        concepts = result.get("concepts", [])
        if concepts:
            st.markdown("### 🏷️ Concept Tags")
            for c in concepts:
                st.markdown(f'<span class="concept-chip">{c["concept"]}</span>', unsafe_allow_html=True)
            st.markdown("")
            for c in concepts:
                st.markdown(f"**{c['concept']}** — {c['definition']}")

        # ── Algorithm Steps ──────────────────────────────────────
        algo_steps = result.get("algorithm_steps", [])
        if algo_steps:
            st.markdown("### 📐 Algorithm Steps")
            for i, step in enumerate(algo_steps, 1):
                st.markdown(f"{i}. {step}")

        # ── Complexity ───────────────────────────────────────────
        complexity = result.get("complexity")
        if complexity:
            st.markdown("### ⚡ Complexity")
            c1, c2 = st.columns(2)
            c1.metric("Time", complexity.get("time_complexity", "–"))
            c2.metric("Space", complexity.get("space_complexity", "–"))
            st.caption(complexity.get("explanation", ""))

        # ── Hints ────────────────────────────────────────────────
        improvement_hints = result.get("hints", [])
        if improvement_hints:
            st.markdown("### 💡 Improvement Hints")
            for h in improvement_hints:
                st.markdown(f"- {h}")


# ════════════════════════════════════════════════════════════════════
# PAGE 3 – CONCEPTS GLOSSARY
# ════════════════════════════════════════════════════════════════════
elif page == "📚 Concepts":
    st.markdown("## 📚 Concepts Glossary")

    # Show concepts from the latest explanation
    result = st.session_state.get("explanation_result")
    concepts = result.get("concepts", []) if result else []

    search = st.text_input("🔍 Search concepts…", placeholder="e.g. Variables, Loops, Functions")

    if concepts:
        filtered = concepts
        if search.strip():
            term = search.strip().lower()
            filtered = [c for c in concepts if term in c["concept"].lower() or term in c["definition"].lower()]

        if filtered:
            for c in filtered:
                with st.expander(f"**{c['concept']}**", expanded=False):
                    st.markdown(c["definition"])
        else:
            st.warning(f'No concepts match "{search}".')
    else:
        st.info("No concepts loaded yet. Run an explanation first from **📝 Code Input**.")

    st.divider()
    st.markdown("#### 🌐 Search saved concepts from database")
    db_search = st.text_input("Concept name to look up:", key="db_concept_search")
    if db_search.strip():
        if not health:
            st.error("🔴 Backend offline.")
        else:
            with st.spinner("Searching…"):
                db_concepts = client.get_concepts(db_search.strip())
            if isinstance(db_concepts, list) and db_concepts:
                for item in db_concepts:
                    st.markdown(f"- **{item.get('name', '')}** (Submission #{item.get('submission_id', '?')}): {item.get('definition', '')}")
            elif isinstance(db_concepts, dict):
                items = db_concepts.get("items", [])
                if items:
                    for item in items:
                        st.markdown(f"- **{item.get('name', '')}** (Submission #{item.get('submission_id', '?')}): {item.get('definition', '')}")
                else:
                    st.info(f'No saved concepts named "{db_search}" found.')
            else:
                st.info(f'No saved concepts named "{db_search}" found.')


# ════════════════════════════════════════════════════════════════════
# PAGE 4 – TRACE & FLOWCHART
# ════════════════════════════════════════════════════════════════════
elif page == "🔬 Trace & Flowchart":
    st.markdown("## 🔬 Execution Trace & Flowchart")

    trace_result = st.session_state.get("trace_result")

    # Allow re-tracing from this page
    code = st.session_state.get("current_code", "")
    with st.expander("⚙️ Trace Settings", expanded=not bool(trace_result)):
        trace_code_input = st.text_area("Code to trace:", value=code, height=200, key="trace_code_area")
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            trace_input = st.text_input("stdin input (optional):", placeholder="e.g. 42")
        with col_t2:
            gen_flowchart = st.toggle("Generate Mermaid flowchart", value=True)

        if st.button("▶️ Run Trace", type="primary", use_container_width=True):
            if not trace_code_input.strip():
                st.warning("Enter code to trace.")
            elif not health:
                st.error("🔴 Backend offline.")
            else:
                with st.spinner("🔬 Tracing step-by-step…"):
                    try:
                        trace_result = client.trace_code(
                            code=trace_code_input,
                            language=language,
                            input_data=trace_input if trace_input.strip() else None,
                            generate_flowchart=gen_flowchart,
                        )
                        st.session_state["trace_result"] = trace_result
                    except Exception as e:
                        st.error(f"❌ Trace failed: {str(e)}")

    if trace_result:
        if trace_result.get("error"):
            st.error(f"⚠️ Trace error: {trace_result['error']}")

        steps = trace_result.get("steps", [])
        if steps:
            st.markdown(f"### Execution Steps ({len(steps)} total)")

            # Steps table
            col_steps, col_vars = st.columns([2, 1], gap="medium")
            with col_steps:
                for i, step in enumerate(steps):
                    line_no = step.get("line_number", "?")
                    exec_code = step.get("executed_code", "")
                    output = step.get("output", "")

                    step_html = f"""
<div class="trace-step">
    <strong>Step {i + 1}</strong> · Line {line_no}<br>
    <code>{exec_code}</code>
"""
                    if output:
                        step_html += f'<br><span style="color: var(--accent-green);">📤 {output.strip()}</span>'
                    step_html += "</div>"
                    st.markdown(step_html, unsafe_allow_html=True)

            with col_vars:
                st.markdown("#### Variable States")
                # Show variables from the last step
                if steps:
                    last_vars = steps[-1].get("variables", {})
                    if last_vars:
                        for var_name, var_val in last_vars.items():
                            st.markdown(f"**`{var_name}`** = `{var_val}`")
                    else:
                        st.caption("No variables captured.")
        else:
            st.info("No execution steps recorded.")

        # Flowchart
        flowchart = trace_result.get("flowchart")
        if flowchart:
            st.divider()
            st.markdown("### 📊 Control Flow Diagram")
            st.code(flowchart, language="mermaid")
    elif not trace_result:
        st.info("No trace yet. Enter code above and click **Run Trace**, or trace from **📝 Code Input**.")


# ════════════════════════════════════════════════════════════════════
# PAGE 5 – QUIZ
# ════════════════════════════════════════════════════════════════════
elif page == "🧩 Quiz":
    st.markdown("## 🧩 Code Quiz")

    code = st.session_state.get("current_code", "")
    quiz_result = st.session_state.get("quiz_result")

    if not code.strip():
        st.info("No code loaded. Go to **📝 Code Input** first and analyze some code.")
    else:
        st.markdown("##### Code being quizzed:")
        lang_q = st.session_state.get("current_language", "python")
        st.code(code, language=lang_q if lang_q != "auto" else "python", line_numbers=True)

        col_gen, col_lang = st.columns([2, 1])
        with col_gen:
            gen_quiz_btn = st.button("🎲 Generate Quiz", type="primary", use_container_width=True)
        with col_lang:
            quiz_locale = st.selectbox("Language", ["en", "hi"], format_func=lambda x: "English" if x == "en" else "हिन्दी")

        if gen_quiz_btn:
            if not health:
                st.error("🔴 Backend offline.")
            else:
                with st.spinner("🧩 Generating quiz questions…"):
                    try:
                        quiz_result = client.generate_quiz(code, lang_q, locale=quiz_locale)
                        st.session_state["quiz_result"] = quiz_result
                        st.session_state["quiz_answers"] = {}
                        st.session_state["quiz_submitted"] = False
                    except Exception as e:
                        st.error(f"❌ Quiz generation failed: {str(e)}")

        if quiz_result:
            questions = quiz_result.get("questions", [])
            submitted = st.session_state.get("quiz_submitted", False)

            st.divider()
            st.markdown(f"### 📝 {len(questions)} Questions")

            for qi, q in enumerate(questions):
                st.markdown(f"**Q{qi + 1}.** {q['text']}")
                if q.get("line_reference"):
                    st.caption(f"📍 Refers to line(s): {q['line_reference']}")

                options = q.get("options", [])
                option_labels = [f"{opt['id'].upper()}) {opt['text']}" for opt in options]
                option_ids = [opt["id"] for opt in options]

                if not submitted:
                    selected = st.radio(
                        f"Your answer for Q{qi + 1}:",
                        options=option_ids,
                        format_func=lambda x, opts=options: next(
                            (f"{o['id'].upper()}) {o['text']}" for o in opts if o['id'] == x), x
                        ),
                        key=f"quiz_q_{qi}",
                        label_visibility="collapsed",
                    )
                    st.session_state["quiz_answers"][q["id"]] = selected
                else:
                    # Show results
                    user_answer = st.session_state["quiz_answers"].get(q["id"], "")
                    correct_id = q.get("correct_option_id", "")
                    for opt in options:
                        if opt["id"] == correct_id:
                            st.markdown(f"✅ **{opt['id'].upper()}) {opt['text']}** ← Correct")
                        elif opt["id"] == user_answer and user_answer != correct_id:
                            st.markdown(f"❌ ~~{opt['id'].upper()}) {opt['text']}~~ ← Your answer")
                        else:
                            st.markdown(f"⬜ {opt['id'].upper()}) {opt['text']}")
                    st.info(f"💡 {q.get('explanation', '')}")

                st.markdown("---")

            if not submitted:
                if st.button("📩 Submit Answers", type="primary", use_container_width=True):
                    st.session_state["quiz_submitted"] = True
                    st.rerun()
            else:
                # Score calculation
                score = 0
                total = len(questions)
                for q in questions:
                    if st.session_state["quiz_answers"].get(q["id"]) == q.get("correct_option_id"):
                        score += 1

                pct = int((score / total) * 100) if total else 0
                s1, s2, s3 = st.columns(3)
                s1.metric("Score", f"{score}/{total}")
                s2.metric("Percentage", f"{pct}%")
                s3.metric("Grade", "⭐ Perfect!" if pct == 100 else "👍 Good" if pct >= 66 else "📖 Keep learning")

                if st.button("🔄 Retake Quiz"):
                    st.session_state["quiz_submitted"] = False
                    st.session_state["quiz_answers"] = {}
                    st.rerun()

            # Glossary & Mistakes
            glossary = quiz_result.get("glossary", [])
            mistakes = quiz_result.get("common_mistakes", [])
            improvement = quiz_result.get("improvement")

            if glossary or mistakes or improvement:
                st.divider()

            if glossary:
                st.markdown("### 📖 Glossary")
                for g in glossary:
                    st.markdown(f"- **{g['term']}**: {g['definition']}")

            if mistakes:
                st.markdown("### ⚠️ Common Mistakes")
                for m in mistakes:
                    st.markdown(f"- {m}")

            if improvement:
                st.markdown("### ✨ Improved Code Suggestion")
                st.code(improvement.get("improved_code", ""), language=lang_q if lang_q != "auto" else "python")
                st.caption(improvement.get("explanation", ""))


# ════════════════════════════════════════════════════════════════════
# PAGE 6 – HISTORY
# ════════════════════════════════════════════════════════════════════
elif page == "📜 History":
    st.markdown("## 📜 Submission History")

    if not health:
        st.error("🔴 Backend offline. Cannot load history.")
    else:
        with st.spinner("Loading history…"):
            history = client.get_history(limit=50)

        if history:
            st.markdown(f"Showing **{len(history)}** saved submissions.")
            for item in history:
                item_id = item.get("id", "?")
                lang_h = item.get("language", "unknown")
                level_h = item.get("level", "")
                created = item.get("created_at", "")

                with st.expander(f"**#{item_id}** · {lang_h.upper()} · {level_h} · {created[:19]}"):
                    detail = client.get_history_item(item_id)
                    if detail:
                        st.markdown(f"**Language:** {detail.get('language', '')}")
                        st.markdown(f"**Level:** {detail.get('level', '')}")
                        st.markdown(f"**Created:** {detail.get('created_at', '')}")
                    else:
                        st.caption("Could not load details.")
        else:
            st.info("No submissions saved yet. Analyze some code with **Save to History** enabled.")
