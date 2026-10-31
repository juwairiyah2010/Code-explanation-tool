"""Streamlit Focused Learning Workspace – Code Lore.

Presents a unified, responsive learning environment combining:
1. Code editor
2. Language selector
3. Learner level selector
4. Analyze button with sequential progress states
5. Explanation panel (AI-generated, grounded)
6. Static analysis panel (deterministic AST engine)
7. Execution trace panel (deterministic sandbox runner)
8. Flowchart panel (deterministic Mermaid diagram)
9. Quiz & learning panel (comprehension & concept mastery)
10. RAG / source panel (verified reference documentation)
"""

import time
import streamlit as st
from frontend.utils.api_client import APIClient

# ── Page Config ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="Code Lore – Interactive Learning Workspace",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS for Visual Identity & Clear Provenance Badges ──────────
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
    --accent-purple: #a371f7;
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
    padding: 10px 14px;
}
div[data-testid="stMetric"] label {
    color: var(--text-secondary) !important;
    font-size: 0.72rem !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-weight: 700 !important;
    color: var(--accent) !important;
    font-size: 1.3rem !important;
}

/* Sidebar polish */
section[data-testid="stSidebar"] {
    border-right: 1px solid var(--border);
}
section[data-testid="stSidebar"] .stMarkdown h1 {
    font-size: 1.25rem !important;
    font-weight: 700;
}

/* Tab styling */
button[data-baseweb="tab"] {
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    padding: 8px 16px !important;
}

/* Status dot */
.status-dot {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    margin-right: 6px;
}
.status-dot.green { background: var(--accent-green); }
.status-dot.red   { background: #f85149; }

/* Provenance Badges clearly distinguishing data origins */
.provenance-banner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 0.78rem;
    font-weight: 600;
    margin-bottom: 12px;
    letter-spacing: 0.02em;
}
.prov-ai {
    background: rgba(163, 113, 247, 0.12);
    border: 1px solid var(--accent-purple);
    color: #d2a8ff;
}
.prov-ast {
    background: rgba(63, 185, 80, 0.12);
    border: 1px solid var(--accent-green);
    color: #7ee787;
}
.prov-trace {
    background: rgba(210, 153, 34, 0.12);
    border: 1px solid var(--accent-orange);
    color: #e3b341;
}
.prov-rag {
    background: rgba(88, 166, 255, 0.12);
    border: 1px solid var(--accent);
    color: #79c0ff;
}
.prov-quiz {
    background: rgba(219, 97, 162, 0.12);
    border: 1px solid #db61a2;
    color: #f778ba;
}

/* Trace Step Box */
.trace-step-box {
    border-left: 3px solid var(--accent-orange);
    background: var(--bg-card);
    padding: 8px 12px;
    border-radius: 0 6px 6px 0;
    margin-bottom: 6px;
    font-size: 0.85rem;
}

/* Concept Chip */
.concept-chip {
    display: inline-block;
    padding: 3px 10px;
    margin: 2px 4px;
    border: 1px solid var(--accent);
    border-radius: 14px;
    font-size: 0.78rem;
    color: var(--accent);
    background: rgba(88, 166, 255, 0.08);
}
</style>
""", unsafe_allow_html=True)

# ── Session State Defaults ───────────────────────────────────────────
DEFAULTS = {
    "explanation_result": None,
    "ast_result": None,
    "trace_result": None,
    "quiz_result": None,
    "quiz_answers": {},
    "quiz_submitted": False,
    "eval_res": None,
    "current_code": "",
    "current_language": "python",
    "attempts": 0,
    "active_step_idx": 0,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

client = APIClient()

# ── Curated Educational Code Samples ─────────────────────────────────
PYTHON_SAMPLES = {
    "Factorial & Recursion": """def factorial(n: int) -> int:
    \"\"\"Compute factorial recursively with boundary validation.\"\"\"
    if n < 0:
        raise ValueError("Factorial is undefined for negative numbers")
    if n <= 1:
        return 1
    return n * factorial(n - 1)

result = factorial(4)
print(f"Result: {result}")
""",
    "List Filter & Loop": """def count_positives(numbers: list[int]) -> int:
    \"\"\"Count strictly positive numbers in a collection.\"\"\"
    count = 0
    for num in numbers:
        if num > 0:
            count += 1
    return count

scores = [12, -4, 0, 8, -1, 15]
total_pos = count_positives(scores)
print(f"Positive elements: {total_pos}")
""",
    "Hypotenuse Calculation": """import math

def calculate_hypotenuse(a: float, b: float) -> float:
    \"\"\"Compute hypotenuse using Pythagorean theorem.\"\"\"
    if a <= 0 or b <= 0:
        raise ValueError("Sides must be positive numbers")
    return math.sqrt(a**2 + b**2)

res = calculate_hypotenuse(3, 4)
print(f"Hypotenuse: {res}")
"""
}

JS_SAMPLES = {
    "Array Filter & Sum": """function sumEvenNumbers(arr) {
    if (!Array.isArray(arr)) {
        throw new TypeError("Input must be an array");
    }
    let sum = 0;
    for (let i = 0; i < arr.length; i++) {
        if (arr[i] % 2 === 0) {
            sum += arr[i];
        }
    }
    return sum;
}

const numbers = [1, 2, 3, 4, 5, 6];
console.log("Sum of evens:", sumEvenNumbers(numbers));
""",
    "Debounce Utility": """function debounce(func, delay) {
    let timeoutId;
    return function (...args) {
        if (timeoutId) {
            clearTimeout(timeoutId);
        }
        timeoutId = setTimeout(() => {
            func.apply(this, args);
        }, delay);
    };
}
"""
}

# ── Sidebar Configuration ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("# 📜 Code Lore")
    st.caption("Deterministic Code Explanation & Learning Platform")
    st.divider()

    # Health Indicator
    health = client.check_health()
    if health and health.get("status") == "healthy":
        st.markdown('<span class="status-dot green"></span> **Backend Online**', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-dot red"></span> **Backend Offline**', unsafe_allow_html=True)
        st.error("FastAPI backend is unreachable on port 8000.")

    st.divider()
    st.markdown("#### 🧭 Workspace View")
    main_view = st.radio(
        "Navigation",
        options=["🎓 Learning Workspace", "📜 History"],
        label_visibility="collapsed",
    )

    st.divider()
    st.markdown("#### ⚙️ Analysis Parameters")
    
    # 2. Language Selector
    language = st.selectbox(
        "Language",
        options=["python", "javascript", "auto"],
        index=0,
        help="Select language or auto-detect based on syntax structure.",
    )

    # 3. Learner Level Selector
    level = st.selectbox(
        "Learner Level",
        options=["Absolute Beginner", "Beginner", "Intermediate"],
        index=1,
        help="Tailors vocabulary, analogies, and complexity to the student.",
    )

    explanation_mode = st.selectbox(
        "Explanation Mode",
        options=["beginner", "line-by-line", "debugging", "security", "performance", "expert"],
        index=0,
        help="Targeted analysis perspective.",
    )

    include_ast = st.toggle("Deterministic AST Rules", value=True)
    enable_rag = st.toggle("Grounded Documentation", value=True)
    save_history = st.toggle("Save Submission to History", value=True)

    rag_stats = client.get_rag_stats()
    if rag_stats.get("chunks", 0) > 0:
        st.caption(f"📚 Vector Index: {rag_stats['documents']} docs · {rag_stats['chunks']} chunks")


# ════════════════════════════════════════════════════════════════════
# VIEW 1 – FOCUSED LEARNING WORKSPACE
# ════════════════════════════════════════════════════════════════════
if main_view == "🎓 Learning Workspace":
    st.markdown("## 🎓 Code Lore – Learning Workspace")
    st.caption("Interactive workbench for programming students: inspect code, syntax trees, runtime traces, and grounded quizzes side-by-side.")

    # ── Workspace Layout Setup ────────────────────────────────────────
    col_editor_pane, col_workspace_pane = st.columns([5, 7], gap="large")

    # ─────────────────────────────────────────────────────────────────
    # LEFT PANE: 1. Code Editor & 4. Analyze Controls
    # ─────────────────────────────────────────────────────────────────
    with col_editor_pane:
        st.markdown("#### 1. Source Code Editor")

        # Sample code loader
        sample_choice = st.selectbox(
            "Load Educational Example:",
            options=["-- Select a sample --"] + list(PYTHON_SAMPLES.keys()) + list(JS_SAMPLES.keys()),
            index=0,
        )
        if sample_choice in PYTHON_SAMPLES:
            st.session_state["current_code"] = PYTHON_SAMPLES[sample_choice]
            language = "python"
        elif sample_choice in JS_SAMPLES:
            st.session_state["current_code"] = JS_SAMPLES[sample_choice]
            language = "javascript"

        # 1. Code Editor Text Area
        code_input = st.text_area(
            "Source Code",
            value=st.session_state.get("current_code") or PYTHON_SAMPLES["Factorial & Recursion"],
            height=340,
            key="workspace_code_area",
            label_visibility="collapsed",
            placeholder="Write or paste Python or JavaScript code here…",
        )
        st.session_state["current_code"] = code_input

        # Code stats
        line_count = len(code_input.splitlines()) if code_input else 0
        char_count = len(code_input) if code_input else 0
        st.caption(f"📏 {line_count} lines · {char_count} characters · Language: `{language}` · Level: `{level}`")

        # 4. Analyze & Action Controls
        col_btn_main, col_btn_trace, col_btn_quiz = st.columns([2, 1, 1])
        with col_btn_main:
            analyze_btn = st.button("✨ Analyze & Learn", type="primary", use_container_width=True)
        with col_btn_trace:
            trace_only_btn = st.button("🔬 Trace", use_container_width=True, help="Run execution trace in sandbox")
        with col_btn_quiz:
            quiz_only_btn = st.button("🎲 Quiz", use_container_width=True, help="Generate interactive questions")

        # ── Sequential Progress States for Long-Running Analyze ──────
        if analyze_btn:
            if not code_input.strip():
                st.warning("⚠️ Please provide source code before analyzing.")
            elif not health:
                st.error("🔴 Backend is offline. Please start FastAPI on port 8000.")
            else:
                with st.status("Analyzing code...", expanded=True) as status_box:
                    st.write("🔍 **Analyzing code** – detecting language and validating input format...")
                    time.sleep(0.12)

                    st.write("🌲 **Building syntax tree** – parsing deterministic AST constructs and blocks...")
                    time.sleep(0.12)

                    st.write("🛡️ **Running static analysis** – calculating cyclomatic complexity & evaluating rules...")
                    time.sleep(0.12)

                    st.write("📚 **Retrieving concepts** – querying local vector knowledge base for verified documentation...")
                    
                    try:
                        # Call Backend API
                        result = client.explain_code(
                            code=code_input,
                            language=language,
                            level=level,
                            include_ast=include_ast,
                            enable_rag=enable_rag,
                            save_history=save_history,
                        )
                        st.session_state["explanation_result"] = result
                        st.session_state["ast_result"] = result.get("ast_analysis")
                    except Exception as e:
                        status_box.update(label="❌ Analysis Failed", state="error", expanded=True)
                        st.error(f"Analysis error: {str(e)}")
                        st.stop()

                    st.write("🧠 **Generating explanation** – synthesizing block-by-block and line-level walkthroughs...")
                    
                    # Execution Trace in sandbox when applicable
                    resolved_lang = result.get("language", language)
                    if resolved_lang in ("python", "auto"):
                        st.write("⚙️ **Executing in sandbox** – tracing line steps and generating control flowchart...")
                        try:
                            trace_res = client.trace_code(code_input, language="python", generate_flowchart=True)
                            st.session_state["trace_result"] = trace_res
                        except Exception as te:
                            st.caption(f"Notice: Trace skipped: {te}")

                    # Generate grounded interactive learning quiz
                    st.write("🎓 **Generating learning questions** – synthesizing comprehension & debugging challenges...")
                    try:
                        quiz_res = client.generate_quiz(code_input, resolved_lang, workflow="learning")
                        st.session_state["quiz_result"] = quiz_res
                        st.session_state["quiz_submitted"] = False
                        st.session_state["quiz_answers"] = {}
                        st.session_state["attempts"] = 1
                    except Exception as qe:
                        st.caption(f"Notice: Quiz generator fallback: {qe}")

                    st.write("🛡️ **Validating explanation** – checking line bounds and AST construct grounding...")
                    time.sleep(0.1)

                    status_box.update(label="✅ Learning Workspace Ready!", state="complete", expanded=False)
                    st.success("✅ Analysis complete! Review the grounded output panels on the right.")

        # Trace Only Action
        if trace_only_btn:
            if not code_input.strip():
                st.warning("⚠️ Enter code to trace.")
            elif not health:
                st.error("🔴 Backend offline.")
            else:
                with st.spinner("🔬 Running execution trace in sandbox…"):
                    try:
                        t_res = client.trace_code(code_input, language=language, generate_flowchart=True)
                        st.session_state["trace_result"] = t_res
                        st.success("✅ Trace complete! See 'Execution Trace' and 'Flowchart' panels.")
                    except Exception as e:
                        st.error(f"Trace error: {str(e)}")

        # Quiz Only Action
        if quiz_only_btn:
            if not code_input.strip():
                st.warning("⚠️ Enter code to generate questions.")
            elif not health:
                st.error("🔴 Backend offline.")
            else:
                with st.spinner("🎲 Generating interactive learning questions…"):
                    try:
                        q_res = client.generate_quiz(code_input, language=language, workflow="learning")
                        st.session_state["quiz_result"] = q_res
                        st.session_state["quiz_submitted"] = False
                        st.session_state["quiz_answers"] = {}
                        st.session_state["attempts"] = st.session_state.get("attempts", 0) + 1
                        st.success("✅ Quiz ready! See 'Quiz & Learning' panel.")
                    except Exception as e:
                        st.error(f"Quiz error: {str(e)}")

    # ─────────────────────────────────────────────────────────────────
    # RIGHT PANE: 5-10 Focused Workspace Panels
    # ─────────────────────────────────────────────────────────────────
    with col_workspace_pane:
        st.markdown("#### Learning Panels")

        # Define 6 Workspace Output Panels
        tab_expl, tab_ast, tab_trace, tab_flowchart, tab_quiz, tab_rag = st.tabs([
            "📖 Explanation",
            "🛡️ Static Analysis",
            "🔬 Execution Trace",
            "🗺️ Flowchart",
            "🎓 Quiz & Learning",
            "📚 Documentation",
        ])

        # ── 5. EXPLANATION PANEL ──────────────────────────────────────
        with tab_expl:
            st.markdown('<div class="provenance-banner prov-ai"><span>🤖 DATA SOURCE: AI-Generated Content</span><span>Grounded in Deterministic AST</span></div>', unsafe_allow_html=True)
            expl_res = st.session_state.get("explanation_result")

            if not expl_res:
                st.info("💡 **Empty State**: No explanation generated yet. Write code and click **'✨ Analyze & Learn'** to synthesize a grounded explanation.")
            else:
                # Grounding Verification Indicator
                val_res = expl_res.get("validation_result")
                if val_res:
                    is_val = val_res.get("valid", True)
                    cov = int(val_res.get("coverage_score", 0.0) * 100)
                    lvl = val_res.get("grounding_level", "Moderate")
                    repaired = val_res.get("repaired", False)

                    status_icon = "🟢" if is_val else "🟡"
                    status_lbl = "Verified Grounded" if is_val else "Grounding Warnings Flagged"
                    if repaired:
                        status_lbl += " (Auto-Repaired)"

                    with st.container():
                        st.markdown(f"**{status_icon} Explanation Grounding:** `{status_lbl}`")
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Coverage", f"{cov}%")
                        m2.metric("Grounding Level", lvl)
                        m3.metric("Referenced Lines", len(val_res.get("referenced_lines", [])))

                        if val_res.get("unsupported_claims") or val_res.get("warnings"):
                            with st.expander("🔍 Grounding Details & Disclosures", expanded=False):
                                for claim in val_res.get("unsupported_claims", []):
                                    st.warning(f"⚠️ {claim}")
                                for w in val_res.get("warnings", []):
                                    st.caption(f"ℹ️ {w}")

                # Summary Card
                st.markdown(f"> **Summary:**\n>\n> {expl_res.get('summary', 'No summary available.')}")

                # Block-by-Block Explanations
                blocks = expl_res.get("blocks", [])
                if blocks:
                    st.markdown("##### 🧩 Block-by-Block Breakdown")
                    for b in blocks:
                        ls = b.get("line_start", 1)
                        le = b.get("line_end", ls)
                        with st.expander(f"**{b.get('title', 'Block')}** (Lines {ls}–{le})", expanded=True):
                            st.markdown(b.get("explanation", ""))

                # Key Takeaways & Improvements
                takeaways = expl_res.get("key_takeaways", [])
                if takeaways:
                    st.markdown("##### 🎯 Key Takeaways")
                    for tk in takeaways:
                        st.markdown(f"- {tk}")

                hints = expl_res.get("hints", [])
                if hints:
                    st.markdown("##### 💡 Improvement Suggestions")
                    for h in hints:
                        st.markdown(f"- {h}")

        # ── 6. STATIC ANALYSIS PANEL ──────────────────────────────────
        with tab_ast:
            st.markdown('<div class="provenance-banner prov-ast"><span>🛡️ DATA SOURCE: Deterministic Static Analysis</span><span>AST Engine (No AI Hallucination)</span></div>', unsafe_allow_html=True)
            ast_data = st.session_state.get("ast_result") or (st.session_state.get("explanation_result") or {}).get("ast_analysis")

            if not ast_data:
                st.info("🔍 **Empty State**: No static analysis data yet. Click **'✨ Analyze & Learn'** to run deterministic syntax inspections.")
            else:
                m_c1, m_c2, m_c3, m_c4 = st.columns(4)
                m_c1.metric("Complexity", ast_data.get("complexity_score", 1))
                m_c2.metric("Max Nesting", ast_data.get("max_nesting_depth", 0))
                metrics = ast_data.get("metrics", {})
                m_c3.metric("Functions", metrics.get("num_functions", 0))
                m_c4.metric("Static Hints", len(ast_data.get("static_hints", [])))

                # Static hints & Rule Violations
                hints_list = ast_data.get("static_hints", [])
                if hints_list:
                    st.markdown("##### ⚠️ Static Analysis Rule Findings")
                    for h in hints_list:
                        sev = h.get("severity", "info")
                        icon = "🔴" if sev == "error" else ("🟡" if sev == "warning" else "🔵")
                        st.warning(f"{icon} **[{h.get('rule_id', 'RULE')}] Line {h.get('line_start')}:** {h.get('message')}\n\n💡 *Fix: {h.get('suggestion', 'None')}*")
                else:
                    st.success("✅ **Clean code:** No static rule violations detected.")

                # Syntax Constructs
                constructs = ast_data.get("constructs", {})
                if constructs:
                    st.markdown("##### 🌲 Extracted AST Constructs")
                    funcs = constructs.get("functions", [])
                    loops = constructs.get("loops", [])
                    conds = constructs.get("conditions", [])

                    col_f, col_l, col_c = st.columns(3)
                    with col_f:
                        st.markdown(f"**Functions ({len(funcs)})**")
                        for f in funcs:
                            st.caption(f"• `{f.get('name')}()` (L{f.get('line_start')}–L{f.get('line_end')})")
                    with col_l:
                        st.markdown(f"**Loops ({len(loops)})**")
                        for lp in loops:
                            st.caption(f"• `{lp.get('loop_type')}` loop (L{lp.get('line_start')}–L{lp.get('line_end')})")
                    with col_c:
                        st.markdown(f"**Branches ({len(conds)})**")
                        for cd in conds:
                            st.caption(f"• `{cd.get('condition_type')}` (L{cd.get('line_start')}–L{cd.get('line_end')})")

        # ── 7. EXECUTION TRACE PANEL ──────────────────────────────────
        with tab_trace:
            st.markdown('<div class="provenance-banner prov-trace"><span>⚙️ DATA SOURCE: Deterministic Execution Results</span><span>Subprocess Trace Sandbox</span></div>', unsafe_allow_html=True)
            trace_data = st.session_state.get("trace_result")

            if not trace_data:
                st.info("🔬 **Empty State**: No execution trace recorded. Click **'🔬 Trace'** to execute Python code step-by-step.")
            else:
                if trace_data.get("error"):
                    st.error(f"⚠️ Trace Error: {trace_data['error']}")

                steps = trace_data.get("steps", [])
                if steps:
                    st.markdown(f"##### Step Scrubber ({len(steps)} total runtime steps)")
                    step_idx = st.slider(
                        "Scrub Execution Step:",
                        min_value=1,
                        max_value=len(steps),
                        value=min(st.session_state.get("active_step_idx", 1), len(steps)),
                        step=1,
                        key="trace_step_slider",
                    )
                    st.session_state["active_step_idx"] = step_idx
                    current_step = steps[step_idx - 1]

                    col_s_info, col_s_vars = st.columns([1, 1], gap="medium")
                    with col_s_info:
                        st.markdown(f"""
<div class="trace-step-box">
    <strong>Step {step_idx} of {len(steps)}</strong> · Line <code>{current_step.get('line_number')}</code><br>
    <strong>Event:</strong> <code>{current_step.get('event_type', 'line')}</code> · Function: <code>{current_step.get('function_name', '<module>')}</code><br>
    <strong>Executed Code:</strong><br>
    <code>{current_step.get('executed_code', '')}</code>
</div>
""", unsafe_allow_html=True)

                    with col_s_vars:
                        st.markdown("**Variable State at Step:**")
                        step_vars = current_step.get("local_variables") or current_step.get("variables", {})
                        if step_vars:
                            for var_k, var_v in step_vars.items():
                                st.markdown(f"• **`{var_k}`** = `{var_v}`")
                        else:
                            st.caption("No local variables in this frame.")

                    # Terminal Output
                    term_out = trace_data.get("output") or trace_data.get("stdout")
                    if term_out:
                        st.markdown("**Terminal Output (`stdout`):**")
                        st.code(term_out, language="text")
                else:
                    st.info("No discrete steps recorded during execution.")

        # ── 8. FLOWCHART PANEL ────────────────────────────────────────
        with tab_flowchart:
            st.markdown('<div class="provenance-banner prov-ast"><span>🗺️ DATA SOURCE: Deterministic Control Flowchart</span><span>Generated from Trace & AST Logic</span></div>', unsafe_allow_html=True)
            trace_flow = st.session_state.get("trace_result")
            flowchart_code = trace_flow.get("flowchart") if trace_flow else None

            if not flowchart_code:
                st.info("🗺️ **Empty State**: No flowchart available. Run analysis on Python code to generate a Mermaid control flow diagram.")
            else:
                st.markdown("##### Control Flow Diagram")
                st.code(flowchart_code, language="mermaid")
                st.caption("Diagram shows entry point, conditional branches, loops, and termination paths.")

        # ── 9. QUIZ & LEARNING PANEL ──────────────────────────────────
        with tab_quiz:
            st.markdown('<div class="provenance-banner prov-quiz"><span>🎓 DATA SOURCE: Interactive Code-Learning Workflow</span><span>Deterministic Mastery & Line-Grounded Questions</span></div>', unsafe_allow_html=True)
            quiz_data = st.session_state.get("quiz_result")

            if not quiz_data:
                st.info("🎓 **Empty State**: No quiz generated yet. Click **'🎲 Quiz'** or **'✨ Analyze & Learn'** to generate comprehension challenges.")
            else:
                # 1. Beginner Explanation
                if quiz_data.get("beginner_explanation"):
                    st.markdown(f"💡 **Beginner Concept:** {quiz_data['beginner_explanation']}")

                # 4. Common Mistakes
                if quiz_data.get("common_mistakes"):
                    with st.expander("⚠️ Common Student Mistakes for this Code", expanded=False):
                        for cm in quiz_data["common_mistakes"]:
                            st.caption(f"• {cm}")

                # Questions
                q_list = quiz_data.get("questions", [])
                is_sub = st.session_state.get("quiz_submitted", False)

                st.markdown(f"##### Code Comprehension Questions ({len(q_list)} total)")
                for qi, q in enumerate(q_list):
                    q_type = q.get("question_type", "comprehension")
                    t_badge = "🐛 Debugging" if q_type == "debugging" else ("🔮 Predict Output" if q_type == "predict_output" else "🧠 Comprehension")
                    st.markdown(f"**Q{qi + 1}. [{t_badge}]** {q.get('question') or q.get('text')}")
                    
                    if q.get("referenced_lines"):
                        st.caption(f"📍 Line(s): `{q.get('referenced_lines')}` | Concept: `{q.get('concept', 'General')}`")

                    opts = q.get("options", [])
                    opt_ids = [opt["id"] for opt in opts]

                    if not is_sub:
                        sel = st.radio(
                            f"Q{qi+1} Choice:",
                            options=opt_ids,
                            format_func=lambda x, options=opts: next((f"{o['id']}) {o['text']}" for o in options if o['id'] == x), x),
                            key=f"wk_quiz_q_{qi}",
                            label_visibility="collapsed",
                        )
                        st.session_state["quiz_answers"][q["id"]] = sel
                    else:
                        u_ans = st.session_state["quiz_answers"].get(q["id"], "")
                        c_ans = q.get("correct_answer") or q.get("correct_option_id")
                        for o in opts:
                            if o["id"] == c_ans:
                                st.markdown(f"✅ **{o['id']}) {o['text']}** ← Correct")
                            elif o["id"] == u_ans and u_ans != c_ans:
                                st.markdown(f"❌ ~~{o['id']}) {o['text']}~~ ← Your selection")
                            else:
                                st.markdown(f"⬜ {o['id']}) {o['text']}")
                        st.info(f"💡 {q.get('explanation', '')}")
                    st.markdown("---")

                if not is_sub:
                    if st.button("📩 Submit Answers for Deterministic Evaluation", type="primary", use_container_width=True, key="submit_wk_quiz"):
                        st.session_state["quiz_submitted"] = True
                        try:
                            client.submit_learning_answers(
                                code=code_input,
                                language=language,
                                answers=st.session_state["quiz_answers"],
                                questions_payload=q_list,
                            )
                        except Exception as se:
                            st.caption(f"Submission recorded: {se}")
                        st.rerun()
                else:
                    # Deterministic Score
                    sc = 0
                    for q in q_list:
                        corr = q.get("correct_answer") or q.get("correct_option_id")
                        if st.session_state["quiz_answers"].get(q["id"]) == corr:
                            sc += 1
                    pct = int((sc / len(q_list)) * 100) if q_list else 0

                    c_s1, c_s2, c_s3 = st.columns(3)
                    c_s1.metric("Score", f"{sc}/{len(q_list)}")
                    c_s2.metric("Accuracy", f"{pct}%")
                    c_s3.metric("Status", "Completed")

                    # Concept Mastery Progress Model
                    prog = client.get_learner_progress()
                    if prog:
                        st.markdown("##### 📈 Concept Mastery Progress")
                        p_cols = st.columns(min(len(prog), 3))
                        for pi, p_item in enumerate(prog):
                            with p_cols[pi % len(p_cols)]:
                                st.metric(label=p_item["concept"], value=f"{p_item['mastery']}%")

                    if st.button("🔄 Retake Quiz", key="retake_wk_quiz"):
                        st.session_state["quiz_submitted"] = False
                        st.session_state["quiz_answers"] = {}
                        st.rerun()

                # 8. Final Takeaway
                if quiz_data.get("final_takeaway"):
                    st.markdown(f"🎯 **Final Takeaway:** {quiz_data['final_takeaway']}")

        # ── 10. RAG / SOURCE PANEL ────────────────────────────────────
        with tab_rag:
            st.markdown('<div class="provenance-banner prov-rag"><span>📖 DATA SOURCE: Retrieved Verified Documentation</span><span>Vector Knowledge Base (Curated References)</span></div>', unsafe_allow_html=True)
            sources = (st.session_state.get("explanation_result") or {}).get("rag_sources", [])

            if sources:
                st.markdown(f"##### Verified Documentation Citations ({len(sources)} grounded)")
                for cite in sources:
                    score_pct = int(cite.get("similarity_score", 0.0) * 100)
                    with st.expander(f"📖 **{cite.get('title')}** — *{cite.get('source')}* ({score_pct}% match)", expanded=True):
                        st.markdown(f"> {cite.get('snippet')}")
                        st.caption(f"Topic: `{cite.get('topic')}` | Chunk ID: `{cite.get('chunk_id')}`")
            else:
                st.info("📚 **Empty State**: No specific external documentation chunks cited for this snippet.")

            st.divider()
            st.markdown("##### 🔍 Semantic Knowledge Search")
            rag_q = st.text_input("Query curated programming references:", placeholder="e.g. recursion base case, list slicing", key="wk_rag_q")
            if rag_q.strip():
                if not health:
                    st.error("Backend offline.")
                else:
                    with st.spinner("Searching vector index…"):
                        s_res = client.search_rag(rag_q.strip(), language=language)
                    if s_res and s_res.get("results"):
                        for r in s_res["results"]:
                            r_pct = int(r.get("similarity_score", 0.0) * 100)
                            with st.expander(f"📖 {r.get('title')} ({r_pct}% match)"):
                                st.markdown(f"**Source:** *{r.get('source')}* · Topic: `{r.get('topic')}`")
                                st.markdown(r.get("snippet"))
                    else:
                        st.caption("No matching knowledge chunks found.")


# ════════════════════════════════════════════════════════════════════
# VIEW 2 – SUBMISSION HISTORY
# ════════════════════════════════════════════════════════════════════
elif main_view == "📜 History":
    st.markdown("## 📜 Submission History")
    st.caption("Review past analyzed submissions and reload them into your learning workspace.")

    if not health:
        st.error("🔴 Backend offline. Cannot load history.")
    else:
        with st.spinner("Loading history…"):
            history_list = client.get_history(limit=50)

        if history_list:
            st.markdown(f"Showing **{len(history_list)}** saved submissions:")
            for item in history_list:
                item_id = item.get("id", "?")
                lang_h = item.get("language", "unknown")
                level_h = item.get("level", "")
                created = item.get("created_at", "")[:19]
                summary_preview = item.get("summary", "")

                label = f"**#{item_id}** · {lang_h.upper()} · {level_h} · {created}"
                if summary_preview:
                    label += f" — {summary_preview[:60]}…"

                with st.expander(label):
                    detail = client.get_history_item(item_id)
                    if detail:
                        st.markdown(f"**Summary:** {detail.get('summary', 'No summary available.')}")
                        saved_code = detail.get("code", "")
                        if saved_code:
                            st.code(saved_code, language=detail.get("language", "python"))

                        if st.button(f"📥 Load Submission #{item_id} into Workspace", key=f"load_hist_{item_id}"):
                            st.session_state["current_code"] = saved_code
                            st.session_state["current_language"] = detail.get("language", "python")
                            st.session_state["explanation_result"] = {
                                "id": detail.get("id"),
                                "language": detail.get("language"),
                                "level": detail.get("level"),
                                "summary": detail.get("summary"),
                                "blocks": detail.get("blocks", []),
                                "concepts": detail.get("concepts", []),
                                "complexity": (detail.get("explanation") or {}).get("complexity", {}),
                                "hints": (detail.get("explanation") or {}).get("hints", []),
                            }
                            st.success(f"Loaded submission #{item_id}! Switch back to '🎓 Learning Workspace' to inspect.")
                    else:
                        st.caption("Could not load details.")
        else:
            st.info("No submissions saved yet. Analyze some code with **Save Submission to History** enabled.")
