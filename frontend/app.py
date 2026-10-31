"""Streamlit Focused Learning Workspace – Code Lore.

Presents a clean, streamlined learning workspace focused strictly on:
1. Enter/paste code (with curated samples)
2. Select language
3. Choose explanation level
4. Analyze/explain code (single primary action)
5. Understand code block-by-block with verified grounding
6. See execution & control flow when useful
7. Inspect static analysis & complexity
8. Test understanding with interactive quiz
9. View useful submission history
"""

import streamlit as st
from frontend.utils.api_client import APIClient

# ── Page Configuration ────────────────────────────────────────────────
st.set_page_config(
    page_title="Code Lore – Interactive Learning Workspace",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sleek, Focused Styling ────────────────────────────────────────────
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
    font-size: 1.25rem !important;
}

/* Sidebar polish */
section[data-testid="stSidebar"] {
    border-right: 1px solid var(--border);
}

/* Clean Provenance Badges */
.prov-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 0.74rem;
    font-weight: 500;
    margin-bottom: 12px;
}
.prov-badge.ai { background: rgba(163, 113, 247, 0.12); color: #d2a8ff; border: 1px solid rgba(163, 113, 247, 0.3); }
.prov-badge.ast { background: rgba(63, 185, 80, 0.12); color: #7ee787; border: 1px solid rgba(63, 185, 80, 0.3); }
.prov-badge.trace { background: rgba(210, 153, 34, 0.12); color: #e3b341; border: 1px solid rgba(210, 153, 34, 0.3); }
.prov-badge.quiz { background: rgba(219, 97, 162, 0.12); color: #f778ba; border: 1px solid rgba(219, 97, 162, 0.3); }
.prov-badge.rag { background: rgba(88, 166, 255, 0.12); color: #79c0ff; border: 1px solid rgba(88, 166, 255, 0.3); }

/* Trace Step Box */
.trace-step-box {
    border-left: 3px solid var(--accent-orange);
    background: var(--bg-card);
    padding: 8px 12px;
    border-radius: 0 6px 6px 0;
    margin-bottom: 8px;
    font-size: 0.85rem;
}

/* Welcome Card */
.welcome-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 24px;
    margin-top: 10px;
}
.welcome-card h3 {
    margin-top: 0;
    color: var(--accent);
}

/* Layer Titles */
.layer-title {
    font-size: 1.02rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-top: 1.2rem;
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* Quick Understanding Card */
.quick-card {
    background: linear-gradient(135deg, rgba(88, 166, 255, 0.08) 0%, rgba(163, 113, 247, 0.08) 100%);
    border: 1px solid rgba(88, 166, 255, 0.25);
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 0.8rem;
    font-size: 0.95rem;
    line-height: 1.55;
    color: var(--text-primary);
}

/* Interactive Step Card */
.step-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: 6px;
    padding: 12px 16px;
    margin-bottom: 10px;
}
.step-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
}
.line-badge {
    background: rgba(88, 166, 255, 0.15);
    color: var(--accent);
    border-radius: 4px;
    padding: 2px 7px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.74rem;
    font-weight: 600;
}

/* Issue Cards */
.issue-box {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-left: 4px solid var(--accent-orange);
    border-radius: 6px;
    padding: 12px 16px;
    margin-bottom: 10px;
}
.issue-box.error {
    border-left-color: #f85149;
    background: rgba(248, 81, 73, 0.06);
}
.issue-box.warning {
    border-left-color: var(--accent-orange);
    background: rgba(210, 153, 34, 0.06);
}
.issue-box.complexity {
    border-left-color: var(--accent);
    background: rgba(88, 166, 255, 0.06);
}

.clean-banner {
    background: rgba(63, 185, 80, 0.1);
    border: 1px solid rgba(63, 185, 80, 0.3);
    border-radius: 6px;
    padding: 10px 14px;
    color: #7ee787;
    font-size: 0.85rem;
    font-weight: 500;
    margin-bottom: 1rem;
}

/* Highlighted Line Box */
.highlight-line-box {
    background: rgba(88, 166, 255, 0.09);
    border: 1px solid var(--accent);
    border-radius: 6px;
    padding: 10px 14px;
    margin-bottom: 12px;
}

/* Status dot */
.status-dot {
    display: inline-block;
    width: 7px; height: 7px;
    border-radius: 50%;
    margin-right: 5px;
}
.status-dot.green { background: var(--accent-green); }
.status-dot.red   { background: #f85149; }
</style>
""", unsafe_allow_html=True)

# ── Educational Code Samples ──────────────────────────────────────────
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
""",
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
""",
}

# ── Session State Defaults ────────────────────────────────────────────
DEFAULT_CODE = PYTHON_SAMPLES["Factorial & Recursion"]
if "current_code" not in st.session_state:
    st.session_state["current_code"] = DEFAULT_CODE
if "workspace_code_area" not in st.session_state:
    st.session_state["workspace_code_area"] = DEFAULT_CODE
if "explanation_result" not in st.session_state:
    st.session_state["explanation_result"] = None
if "ast_result" not in st.session_state:
    st.session_state["ast_result"] = None
if "trace_result" not in st.session_state:
    st.session_state["trace_result"] = None
if "quiz_result" not in st.session_state:
    st.session_state["quiz_result"] = None
if "quiz_answers" not in st.session_state:
    st.session_state["quiz_answers"] = {}
if "quiz_submitted" not in st.session_state:
    st.session_state["quiz_submitted"] = False
if "active_step_idx" not in st.session_state:
    st.session_state["active_step_idx"] = 1
if "nav_view" not in st.session_state:
    st.session_state["nav_view"] = "🎓 Workspace"
if "selected_language" not in st.session_state:
    st.session_state["selected_language"] = "python"
if "selected_level" not in st.session_state:
    st.session_state["selected_level"] = "Beginner"

client = APIClient()

# ── Sample Selection Callback ─────────────────────────────────────────
def on_sample_select():
    selected = st.session_state.get("sample_selector")
    if selected in PYTHON_SAMPLES:
        st.session_state["workspace_code_area"] = PYTHON_SAMPLES[selected]
        st.session_state["selected_language"] = "python"
    elif selected in JS_SAMPLES:
        st.session_state["workspace_code_area"] = JS_SAMPLES[selected]
        st.session_state["selected_language"] = "javascript"


# ── Sidebar Navigation & Parameters ───────────────────────────────────
with st.sidebar:
    st.markdown("### 📜 Code Lore")
    st.caption("Deterministic Code Explanation & Interactive Learning")
    st.divider()

    # Simple, clear navigation
    nav_choice = st.radio(
        "Navigation",
        options=["🎓 Workspace", "📜 History"],
        index=0 if st.session_state.get("nav_view") == "🎓 Workspace" else 1,
        label_visibility="collapsed",
        key="nav_radio",
    )
    st.session_state["nav_view"] = nav_choice

    if nav_choice == "🎓 Workspace":
        st.divider()
        st.markdown("##### ⚙️ Settings")

        # 2. Language Selector
        lang_options = ["python", "javascript", "auto"]
        current_lang_idx = lang_options.index(st.session_state["selected_language"]) if st.session_state["selected_language"] in lang_options else 0
        language = st.selectbox(
            "Language",
            options=lang_options,
            index=current_lang_idx,
            key="sb_language",
            help="Select programming language or auto-detect syntax.",
        )
        st.session_state["selected_language"] = language

        # 3. Learner Level Selector
        level_options = ["Absolute Beginner", "Beginner", "Intermediate"]
        current_lvl_idx = level_options.index(st.session_state["selected_level"]) if st.session_state["selected_level"] in level_options else 1
        level = st.selectbox(
            "Explanation Level",
            options=level_options,
            index=current_lvl_idx,
            key="sb_level",
            help="Tailors explanation depth, analogies, and technical vocabulary.",
        )
        st.session_state["selected_level"] = level

    st.divider()
    # Compact Health Indicator
    health = client.check_health()
    if health and health.get("status") in ("healthy", "degraded"):
        st.markdown('<small><span class="status-dot green"></span>Backend Online</small>', unsafe_allow_html=True)
    else:
        st.markdown('<small><span class="status-dot red"></span>Backend Offline</small>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════
# VIEW 1 – FOCUSED LEARNING WORKSPACE
# ════════════════════════════════════════════════════════════════════
if st.session_state["nav_view"] == "🎓 Workspace":
    col_editor, col_results = st.columns([5, 7], gap="large")

    # ─────────────────────────────────────────────────────────────────
    # LEFT PANE: 1. Code Editor & 4. Primary Analyze Action
    # ─────────────────────────────────────────────────────────────────
    with col_editor:
        st.markdown("#### 1. Code Editor")

        # Sample code loader
        st.selectbox(
            "Load Example Code:",
            options=["-- Custom Code --"] + list(PYTHON_SAMPLES.keys()) + list(JS_SAMPLES.keys()),
            index=0,
            key="sample_selector",
            on_change=on_sample_select,
        )

        # 1. Code Editor Text Area
        code_input = st.text_area(
            "Source Code",
            height=360,
            key="workspace_code_area",
            label_visibility="collapsed",
            placeholder="Paste or write Python or JavaScript code here…",
        )
        st.session_state["current_code"] = code_input

        # 4. Single Primary Analyze Button
        analyze_btn = st.button("✨ Analyze Code", type="primary", use_container_width=True)

        if analyze_btn:
            if not code_input.strip():
                st.warning("⚠️ Please provide source code before analyzing.")
            elif not health:
                st.error("🔴 Backend is offline. Please check that the server is running.")
            else:
                with st.status("Analyzing code...", expanded=True) as status_box:
                    st.write("🔍 Parsing syntax and detecting language structure...")
                    st.write("🌲 Building deterministic AST and calculating complexity...")
                    st.write("📚 Retrieving verified concepts from knowledge base...")

                    try:
                        # Call Backend API
                        result = client.explain_code(
                            code=code_input,
                            language=st.session_state["selected_language"],
                            level=st.session_state["selected_level"],
                            include_ast=True,
                            enable_rag=True,
                            save_history=True,
                        )
                        st.session_state["explanation_result"] = result
                        st.session_state["ast_result"] = result.get("ast_analysis")
                    except Exception as e:
                        status_box.update(label="❌ Analysis Failed", state="error", expanded=True)
                        st.error(f"Analysis error: {str(e)}")
                        st.stop()

                    st.write("🧠 Synthesizing block-by-block explanation...")

                    # Sandbox Execution Trace for Python
                    resolved_lang = result.get("language", st.session_state["selected_language"])
                    if resolved_lang in ("python", "auto"):
                        st.write("⚙️ Executing in sandbox and generating control flowchart...")
                        try:
                            trace_res = client.trace_code(code_input, language="python", generate_flowchart=True)
                            st.session_state["trace_result"] = trace_res
                        except Exception:
                            st.session_state["trace_result"] = None

                    # Interactive Quiz Generation
                    st.write("🎓 Generating grounded comprehension questions...")
                    try:
                        quiz_res = client.generate_quiz(code_input, resolved_lang, workflow="learning")
                        st.session_state["quiz_result"] = quiz_res
                        st.session_state["quiz_submitted"] = False
                        st.session_state["quiz_answers"] = {}
                    except Exception:
                        st.session_state["quiz_result"] = None

                    status_box.update(label="✅ Analysis Complete!", state="complete", expanded=False)

    # ─────────────────────────────────────────────────────────────────
    # RIGHT PANE: Output Panels
    # ─────────────────────────────────────────────────────────────────
    with col_results:
        expl_res = st.session_state.get("explanation_result")

        # If no code has been analyzed yet, show clean welcoming guide
        if not expl_res:
            st.markdown("""
<div class="welcome-card">
    <h3>🚀 Welcome to Code Lore</h3>
    <p style="color: var(--text-secondary); margin-bottom: 16px;">
        Paste your code or select an example on the left, then click <strong>✨ Analyze Code</strong> to inspect:
    </p>
    <ul style="color: var(--text-secondary); line-height: 1.8;">
        <li><strong>📖 Explanation:</strong> Understand code block-by-block with verified grounding.</li>
        <li><strong>⚡ Execution & Flow:</strong> Step through runtime states and view the control flowchart.</li>
        <li><strong>🛡️ Static Analysis:</strong> Inspect cyclomatic complexity and deterministic AST rules.</li>
        <li><strong>🎓 Quiz & Practice:</strong> Test comprehension with grounded questions and track mastery.</li>
        <li><strong>📚 Reference Docs:</strong> Explore verified documentation citations for this code.</li>
    </ul>
</div>
""", unsafe_allow_html=True)
        else:
            tab_expl, tab_trace, tab_ast, tab_quiz, tab_docs = st.tabs([
                "📖 Explanation",
                "⚡ Execution & Flow",
                "🛡️ Static Analysis",
                "🎓 Quiz & Practice",
                "📚 Reference Docs",
            ])

            # ── 5. EXPLANATION PANEL (Interactive Layered Design) ─────
            with tab_expl:
                st.markdown('<span class="prov-badge ai">🤖 AI-Generated · Verified Grounded</span>', unsafe_allow_html=True)

                code_lines = (code_input or "").splitlines()

                # Visual Code Reference & Line Connector
                selectable_lines = [
                    f"Line {i+1}: {l.strip()[:40]}"
                    for i, l in enumerate(code_lines)
                    if l.strip()
                ]
                line_filter_options = ["🔍 All Logic Steps"] + selectable_lines
                selected_line_filter = st.selectbox(
                    "🎯 Highlight & Connect Code Line:",
                    options=line_filter_options,
                    index=0,
                    key="expl_line_filter_sel",
                    help="Select any code line to immediately inspect its focused explanation and detected constructs.",
                )

                # If a specific line is selected, show focused line inspector
                if selected_line_filter != "🔍 All Logic Steps":
                    try:
                        line_num = int(selected_line_filter.split(":")[0].replace("Line", "").strip())
                    except Exception:
                        line_num = 1

                    code_content = code_lines[line_num - 1] if 0 <= line_num - 1 < len(code_lines) else ""
                    st.markdown(f"""
<div class="highlight-line-box">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
        <span class="line-badge">Line {line_num}</span>
        <small style="color: var(--text-secondary);">Direct Line Connection</small>
    </div>
    <code style="font-size: 0.9rem;">{code_content}</code>
</div>
""", unsafe_allow_html=True)

                    # Look up line explanation
                    line_items = expl_res.get("line_explanations", [])
                    matched_line = next((item for item in line_items if item.get("line_number") == line_num), None)

                    if matched_line:
                        st.markdown(f"**Explanation:** {matched_line.get('explanation', '')}")
                        if matched_line.get("ast_node"):
                            st.caption(f"🌲 Syntax Construct: `{matched_line.get('ast_node')}`")
                        if matched_line.get("uncertainty_note"):
                            st.caption(f"ℹ️ {matched_line.get('uncertainty_note')}")
                    else:
                        # Fallback to enclosing block
                        matched_block = next((b for b in expl_res.get("blocks", []) if b.get("line_start", 1) <= line_num <= b.get("line_end", b.get("line_start", 1))), None)
                        if matched_block:
                            st.markdown(f"**Belongs to:** **{matched_block.get('title', 'Block')}** (Lines {matched_block.get('line_start')}–{matched_block.get('line_end')})")
                            st.markdown(f"{matched_block.get('explanation', '')}")
                        else:
                            st.caption("No specific line explanation was generated for this line.")

                    # Line-specific findings
                    line_issues = [
                        iss for iss in expl_res.get("issues", [])
                        if iss.get("line_number") == line_num
                    ]
                    line_hints = [
                        h for h in (expl_res.get("ast_analysis") or {}).get("static_hints", [])
                        if h.get("line_start") == line_num or h.get("line_number") == line_num
                    ]
                    if line_issues or line_hints:
                        st.markdown("##### ⚠️ Findings on this Line:")
                        for iss in line_issues:
                            st.warning(f"**{iss.get('category', 'Issue').title()}:** {iss.get('description', '')}\n\n💡 *Fix: {iss.get('suggested_fix', 'None')}*")
                        for h in line_hints:
                            st.info(f"**[{h.get('rule_id', 'RULE')}]:** {h.get('message', '')}\n\n💡 *Fix: {h.get('suggestion', 'None')}*")

                    st.markdown("---")

                # ── Layer 1: Quick Understanding ──────────────────────
                st.markdown('<div class="layer-title">💡 Quick Understanding</div>', unsafe_allow_html=True)
                summary_text = expl_res.get("summary", "No summary available.")
                st.markdown(f'<div class="quick-card">{summary_text}</div>', unsafe_allow_html=True)

                # ── Layer 2: How It Works ─────────────────────────────
                st.markdown('<div class="layer-title">🚶 How It Works</div>', unsafe_allow_html=True)

                blocks = expl_res.get("blocks", [])
                line_explanations = expl_res.get("line_explanations", [])

                if blocks:
                    for i, b in enumerate(blocks):
                        ls = b.get("line_start", 1)
                        le = b.get("line_end", ls)
                        block_lines = code_lines[ls - 1:le] if code_lines else []
                        code_preview = "\n".join(block_lines[:3]) if block_lines else ""
                        if len(block_lines) > 3:
                            code_preview += f"\n... ({len(block_lines) - 3} more lines)"

                        full_text = b.get("explanation", "").strip()
                        # Progressive disclosure: simple explanation first (first 2 sentences)
                        sentences = full_text.split(". ")
                        lead_explanation = ". ".join(sentences[:2])
                        if not lead_explanation.endswith(".") and sentences:
                            lead_explanation += "."
                        extra_detail = ". ".join(sentences[2:]) if len(sentences) > 2 else ""

                        line_label = f"Line {ls}" if ls == le else f"Lines {ls}–{le}"
                        st.markdown(f"""
<div class="step-card">
    <div class="step-header">
        <strong style="color: var(--text-primary); font-size: 0.92rem;">Step {i + 1}: {b.get('title', 'Logic Block')}</strong>
        <span class="line-badge">{line_label}</span>
    </div>
    <div style="color: var(--text-secondary); font-size: 0.88rem; margin-bottom: 6px;">
        {lead_explanation}
    </div>
</div>
""", unsafe_allow_html=True)

                        if code_preview.strip():
                            st.code(code_preview, language=st.session_state["selected_language"])

                        if extra_detail.strip():
                            with st.expander(f"More detail on Step {i + 1}", expanded=False):
                                st.markdown(extra_detail)

                elif line_explanations:
                    for item in line_explanations[:8]:
                        st.markdown(f"- **Line {item.get('line_number')}** (`{item.get('code', '')}`): {item.get('explanation')}")

                # ── Layer 3: Code Concepts ────────────────────────────
                st.markdown('<div class="layer-title">🧩 Code Concepts</div>', unsafe_allow_html=True)
                raw_concepts = expl_res.get("concepts", [])

                concepts_list = []
                for c in raw_concepts:
                    if isinstance(c, dict):
                        name = c.get("concept") or c.get("name")
                        desc = c.get("definition") or c.get("explanation")
                        ref = c.get("reference_source")
                        if name and desc:
                            concepts_list.append((name, desc, ref))

                if not concepts_list:
                    constructs = (expl_res.get("ast_analysis") or {}).get("constructs", {})
                    if constructs.get("loops"):
                        concepts_list.append(("Loops & Iteration", "Repeats a block of code across a collection or while a condition is satisfied.", None))
                    if constructs.get("functions"):
                        concepts_list.append(("Function Encapsulation", "Packages reusable logic into callable routines with defined parameters and return values.", None))
                    if constructs.get("conditions"):
                        concepts_list.append(("Conditional Branching", "Controls program execution flow based on boolean expressions and guard clauses.", None))
                    if "def factorial" in code_input or "return n *" in code_input:
                        concepts_list.append(("Recursion", "A technique where a function solves a problem by calling smaller instances of itself until reaching a base case.", None))

                if concepts_list:
                    col_c1, col_c2 = st.columns(2)
                    for idx, (c_name, c_desc, c_ref) in enumerate(concepts_list):
                        col_target = col_c1 if idx % 2 == 0 else col_c2
                        with col_target:
                            with st.expander(f"💡 **{c_name}**", expanded=False):
                                st.markdown(c_desc)
                                if c_ref:
                                    st.caption(f"📖 Reference: {c_ref}")
                else:
                    st.caption("No specialized concepts identified for this snippet.")

                # ── Layer 4: Potential Issues (Only when they actually exist!) ──
                st.markdown('<div class="layer-title">⚠️ Potential Issues</div>', unsafe_allow_html=True)

                raw_issues = expl_res.get("issues", [])
                raw_hints = (expl_res.get("ast_analysis") or {}).get("static_hints", [])
                complexity_score = (expl_res.get("ast_analysis") or {}).get("complexity_score", 1)

                collected_issues = []
                seen_msgs = set()

                for iss in raw_issues:
                    msg = iss.get("description", "")
                    if msg and msg not in seen_msgs:
                        seen_msgs.add(msg)
                        collected_issues.append({
                            "line": iss.get("line_number"),
                            "severity": iss.get("severity", "warning").lower(),
                            "title": iss.get("category", "Code Quality").title(),
                            "description": msg,
                            "fix": iss.get("suggested_fix"),
                        })

                for h in raw_hints:
                    msg = h.get("message", "")
                    if msg and msg not in seen_msgs:
                        seen_msgs.add(msg)
                        collected_issues.append({
                            "line": h.get("line_start") or h.get("line_number"),
                            "severity": h.get("severity", "warning").lower(),
                            "title": h.get("rule_id", "Static Rule").replace("_", " ").title(),
                            "description": msg,
                            "fix": h.get("suggestion"),
                        })

                if complexity_score > 10 and "High Cyclomatic Complexity" not in seen_msgs:
                    collected_issues.append({
                        "line": None,
                        "severity": "complexity",
                        "title": "High Cyclomatic Complexity",
                        "description": f"Complexity score is {complexity_score}. High complexity indicates nested branches or loops that can make code harder to debug and test.",
                        "fix": "Refactor deeply nested logic into smaller helper functions.",
                    })

                if collected_issues:
                    for iss in collected_issues:
                        sev = iss["severity"]
                        css_class = "error" if sev == "error" else ("complexity" if sev == "complexity" else "warning")
                        icon = "🔴" if sev == "error" else ("🔵" if sev == "complexity" else "🟡")
                        line_str = f"Line {iss['line']}" if iss['line'] else "General"

                        st.markdown(f"""
<div class="issue-box {css_class}">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
        <strong>{icon} {iss['title']}</strong>
        <span class="line-badge">{line_str}</span>
    </div>
    <div style="font-size: 0.88rem; color: var(--text-primary); margin-bottom: 6px;">
        {iss['description']}
    </div>
</div>
""", unsafe_allow_html=True)
                        if iss.get("fix"):
                            st.caption(f"💡 **Suggested Fix:** {iss['fix']}")
                else:
                    st.markdown('<div class="clean-banner">✨ Clean Code: No bugs, code smells, or complexity concerns detected.</div>', unsafe_allow_html=True)

                # ── Layer 5: Deep Dive (Progressive Disclosure) ────────
                st.markdown('<div class="layer-title">🔬 Deep Dive</div>', unsafe_allow_html=True)
                with st.expander("Explore Complexity, Best Practices & Verification", expanded=False):
                    comp = expl_res.get("complexity") or {}
                    t_comp = comp.get("time_complexity") or comp.get("time") or "O(1)"
                    s_comp = comp.get("space_complexity") or comp.get("space") or "O(1)"

                    c_d1, c_d2 = st.columns(2)
                    c_d1.metric("Estimated Time Complexity", t_comp)
                    c_d2.metric("Estimated Space Complexity", s_comp)

                    if comp.get("explanation"):
                        st.markdown(f"**Complexity Rationale:** {comp.get('explanation')}")

                    improvements = expl_res.get("suggested_improvements") or expl_res.get("hints", [])
                    if improvements:
                        st.markdown("##### 💡 Best Practices & Optimization Ideas")
                        for imp in improvements:
                            st.markdown(f"- {imp}")

                    val_res = expl_res.get("validation_result")
                    if val_res:
                        st.markdown("##### 🛡️ Grounding & Verification Details")
                        st.caption(f"Confidence: **{val_res.get('grounding_level', 'High')}** · Coverage: **{int(val_res.get('coverage_score', 0.0)*100)}%** · Referenced Lines: `{val_res.get('referenced_lines', [])}`")
                        if val_res.get("unsupported_claims"):
                            for uc in val_res.get("unsupported_claims", []):
                                st.warning(f"⚠️ {uc}")

            # ── 6. EXECUTION & FLOW PANEL ─────────────────────────────
            with tab_trace:
                st.markdown('<span class="prov-badge trace">⚙️ Deterministic Execution Sandbox</span>', unsafe_allow_html=True)
                trace_data = st.session_state.get("trace_result")

                if not trace_data:
                    st.info("ℹ️ Interactive runtime execution is supported for Python. For JavaScript, review the Static Analysis panel.")
                else:
                    if trace_data.get("error"):
                        st.error(f"⚠️ Trace Error: {trace_data['error']}")

                    steps = trace_data.get("steps", [])
                    if steps:
                        st.markdown(f"##### Step Scrubber ({len(steps)} runtime steps)")
                        step_idx = st.slider(
                            "Scrub Execution Step:",
                            min_value=1,
                            max_value=len(steps),
                            value=min(st.session_state.get("active_step_idx", 1), len(steps)),
                            step=1,
                            key="trace_scrubber",
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
                            st.markdown("**Variables in Frame:**")
                            step_vars = current_step.get("local_variables") or current_step.get("variables", {})
                            if step_vars:
                                for var_k, var_v in step_vars.items():
                                    st.markdown(f"• **`{var_k}`** = `{var_v}`")
                            else:
                                st.caption("No local variables in this frame.")

                        # Terminal Output
                        term_out = trace_data.get("output") or trace_data.get("stdout")
                        if term_out:
                            st.markdown("**Program Output (`stdout`):**")
                            st.code(term_out, language="text")

                    # Control Flowchart
                    flowchart_code = trace_data.get("flowchart")
                    if flowchart_code:
                        st.markdown("##### Control Flow Diagram")
                        st.code(flowchart_code, language="mermaid")

            # ── 7. STATIC ANALYSIS PANEL ──────────────────────────────
            with tab_ast:
                st.markdown('<span class="prov-badge ast">🛡️ Deterministic AST Engine</span>', unsafe_allow_html=True)
                ast_data = st.session_state.get("ast_result") or (expl_res.get("ast_analysis") or {})

                if ast_data:
                    m_c1, m_c2, m_c3, m_c4 = st.columns(4)
                    m_c1.metric("Complexity", ast_data.get("complexity_score", 1))
                    m_c2.metric("Max Nesting", ast_data.get("max_nesting_depth", 0))
                    metrics = ast_data.get("metrics", {})
                    m_c3.metric("Functions", metrics.get("num_functions", 0))
                    m_c4.metric("Static Hints", len(ast_data.get("static_hints", [])))

                    # Static hints & Rule Findings
                    hints_list = ast_data.get("static_hints", [])
                    if hints_list:
                        st.markdown("##### ⚠️ Rule Findings")
                        for h in hints_list:
                            sev = h.get("severity", "info")
                            icon = "🔴" if sev == "error" else ("🟡" if sev == "warning" else "🔵")
                            st.warning(f"{icon} **[{h.get('rule_id', 'RULE')}] Line {h.get('line_start')}:** {h.get('message')}\n\n💡 *Fix: {h.get('suggestion', 'None')}*")
                    else:
                        st.success("✅ **Clean code:** No static rule violations detected.")

                    # Extracted AST Constructs
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
                                st.caption(f"• `{lp.get('loop_type')}` (L{lp.get('line_start')}–L{lp.get('line_end')})")
                        with col_c:
                            st.markdown(f"**Branches ({len(conds)})**")
                            for cd in conds:
                                st.caption(f"• `{cd.get('condition_type')}` (L{cd.get('line_start')}–L{cd.get('line_end')})")

            # ── 8. QUIZ & PRACTICE PANEL ──────────────────────────────
            with tab_quiz:
                st.markdown('<span class="prov-badge quiz">🎓 Interactive Code-Learning</span>', unsafe_allow_html=True)
                quiz_data = st.session_state.get("quiz_result")

                if not quiz_data:
                    st.info("ℹ️ Interactive quiz is being synthesized or not available for this snippet.")
                else:
                    if quiz_data.get("beginner_explanation"):
                        st.markdown(f"💡 **Key Concept:** {quiz_data['beginner_explanation']}")

                    if quiz_data.get("common_mistakes"):
                        with st.expander("⚠️ Common Mistakes for this Pattern", expanded=False):
                            for cm in quiz_data["common_mistakes"]:
                                st.caption(f"• {cm}")

                    q_list = quiz_data.get("questions", [])
                    is_sub = st.session_state.get("quiz_submitted", False)

                    st.markdown(f"##### Questions ({len(q_list)} total)")
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
                                key=f"quiz_opt_{qi}",
                                label_visibility="collapsed",
                            )
                            st.session_state["quiz_answers"][q["id"]] = sel
                        else:
                            u_ans = st.session_state["quiz_answers"].get(q["id"], "")
                            c_ans = q.get("correct_answer") or q.get("correct_option_id")
                            for o in opts:
                                if o["id"] == c_ans:
                                    st.markdown(f"✅ **{o['id']}) {o['text']}** *(Correct)*")
                                elif o["id"] == u_ans and u_ans != c_ans:
                                    st.markdown(f"❌ ~~{o['id']}) {o['text']}~~ *(Your answer)*")
                                else:
                                    st.markdown(f"⬜ {o['id']}) {o['text']}")
                            st.info(f"💡 {q.get('explanation', '')}")
                        st.markdown("---")

                    if not is_sub:
                        if st.button("📩 Submit Answers", type="primary", use_container_width=True, key="submit_quiz_btn"):
                            st.session_state["quiz_submitted"] = True
                            try:
                                client.submit_learning_answers(
                                    code=code_input,
                                    language=st.session_state["selected_language"],
                                    answers=st.session_state["quiz_answers"],
                                    questions_payload=q_list,
                                )
                            except Exception:
                                pass
                            st.rerun()
                    else:
                        # Deterministic Score
                        sc = sum(1 for q in q_list if st.session_state["quiz_answers"].get(q["id"]) == (q.get("correct_answer") or q.get("correct_option_id")))
                        pct = int((sc / len(q_list)) * 100) if q_list else 0

                        c1, c2 = st.columns(2)
                        c1.metric("Score", f"{sc}/{len(q_list)}")
                        c2.metric("Accuracy", f"{pct}%")

                        # Concept Mastery
                        prog = client.get_learner_progress()
                        if prog:
                            st.markdown("##### 📈 Concept Mastery")
                            p_cols = st.columns(min(len(prog), 3))
                            for pi, p_item in enumerate(prog):
                                with p_cols[pi % len(p_cols)]:
                                    st.metric(label=p_item["concept"], value=f"{p_item['mastery']}%")

                        if st.button("🔄 Retake Quiz", key="retake_quiz_btn"):
                            st.session_state["quiz_submitted"] = False
                            st.session_state["quiz_answers"] = {}
                            st.rerun()

                    if quiz_data.get("final_takeaway"):
                        st.markdown(f"🎯 **Final Takeaway:** {quiz_data['final_takeaway']}")

            # ── 9. REFERENCE DOCS PANEL ───────────────────────────────
            with tab_docs:
                st.markdown('<span class="prov-badge rag">📚 Verified Knowledge Base</span>', unsafe_allow_html=True)
                sources = expl_res.get("rag_sources", [])

                if sources:
                    st.markdown(f"##### Grounded Documentation Citations ({len(sources)})")
                    for cite in sources:
                        score_pct = int(cite.get("similarity_score", 0.0) * 100)
                        with st.expander(f"📖 **{cite.get('title')}** — *{cite.get('source')}* ({score_pct}% match)", expanded=True):
                            st.markdown(f"> {cite.get('snippet')}")
                            st.caption(f"Topic: `{cite.get('topic')}` | Chunk ID: `{cite.get('chunk_id')}`")
                else:
                    st.info("ℹ️ No external reference citations required for this self-contained snippet.")

                st.divider()
                st.markdown("##### 🔍 Search Reference Documentation")
                rag_q = st.text_input("Query programming concepts:", placeholder="e.g. recursion, list slicing, error handling", key="rag_search_input")
                if rag_q.strip():
                    with st.spinner("Searching references…"):
                        s_res = client.search_rag(rag_q.strip(), language=st.session_state["selected_language"])
                    if s_res and s_res.get("results"):
                        for r in s_res["results"]:
                            r_pct = int(r.get("similarity_score", 0.0) * 100)
                            with st.expander(f"📖 {r.get('title')} ({r_pct}% match)"):
                                st.markdown(f"**Source:** *{r.get('source')}* · Topic: `{r.get('topic')}`")
                                st.markdown(r.get("snippet"))
                    else:
                        st.caption("No matching documentation found.")


# ════════════════════════════════════════════════════════════════════
# VIEW 2 – SUBMISSION HISTORY
# ════════════════════════════════════════════════════════════════════
elif st.session_state["nav_view"] == "📜 History":
    st.markdown("## 📜 Submission History")
    st.caption("Review past analyzed submissions and reload them into the learning workspace with one click.")

    if not health:
        st.error("🔴 Backend offline. Cannot load history.")
    else:
        with st.spinner("Loading history…"):
            history_list = client.get_history(limit=50)

        if history_list:
            st.markdown(f"**{len(history_list)}** saved submissions:")
            for item in history_list:
                item_id = item.get("id", "?")
                lang_h = item.get("language", "unknown").upper()
                level_h = item.get("level", "")
                created = item.get("created_at", "")[:19]
                summary_preview = item.get("summary", "")

                label = f"#{item_id} · {lang_h} · {level_h} · {created}"
                if summary_preview:
                    label += f" — {summary_preview[:60]}…"

                with st.expander(label):
                    detail = client.get_history_item(item_id)
                    if detail:
                        st.markdown(f"**Summary:** {detail.get('summary', 'No summary available.')}")
                        saved_code = detail.get("code", "")
                        if saved_code:
                            st.code(saved_code, language=detail.get("language", "python"))

                        if st.button(f"📥 Load #{item_id} into Workspace", key=f"load_h_{item_id}"):
                            st.session_state["workspace_code_area"] = saved_code
                            st.session_state["current_code"] = saved_code
                            st.session_state["selected_language"] = detail.get("language", "python")
                            st.session_state["selected_level"] = detail.get("level", "Beginner")
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
                            st.session_state["nav_view"] = "🎓 Workspace"
                            st.success(f"Loaded submission #{item_id}! Redirecting to Workspace…")
                            st.rerun()
                    else:
                        st.caption("Could not load details.")
        else:
            st.info("No submissions saved yet. Analyze code in the Workspace to build your history.")
