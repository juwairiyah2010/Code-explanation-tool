from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from frontend.utils.api_client import APIClient
import json
from functools import wraps

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_code_lore'
client = APIClient()

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

@app.context_processor
def inject_health():
    health = client.check_health()
    return dict(health=health, rag_stats=client.get_rag_stats(), current_user=session.get('username'))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/app', methods=['GET', 'POST'])
@login_required
def app_view():
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        language = request.form.get('language', 'auto')
        level = request.form.get('level', 'Beginner')
        action = request.form.get('action')

        if not code:
            flash('Please enter some code.', 'warning')
            return redirect(url_for('app_view'))

        if action == 'analyze':
            try:
                result = client.explain_code(
                    code=code,
                    language=language,
                    level=level,
                    include_ast=True,
                    enable_rag=True,
                    save_history=True
                )
                session['explanation_result'] = result
                session['current_code'] = code
                session['current_language'] = language
                return redirect(url_for('explanation'))
            except Exception as e:
                flash(f'Analysis failed: {str(e)}', 'danger')

        elif action == 'ast':
            try:
                ast_result = client.analyze_ast(code, language)
                session['ast_result'] = ast_result
                session['current_code'] = code
                session['current_language'] = language
                return redirect(url_for('ast_view'))
            except Exception as e:
                flash(f'AST analysis failed: {str(e)}', 'danger')

        elif action == 'trace':
            try:
                trace_result = client.trace_code(
                    code=code,
                    language=language,
                    generate_flowchart=True
                )
                session['trace_result'] = trace_result
                session['current_code'] = code
                session['current_language'] = language
                return redirect(url_for('trace_view'))
            except Exception as e:
                flash(f'Trace failed: {str(e)}', 'danger')

    code_val = session.get('current_code', PYTHON_EXAMPLE)
    lang_val = session.get('current_language', 'python')
    return render_template('index.html', code=code_val, language=lang_val, py_ex=PYTHON_EXAMPLE, js_ex=JS_EXAMPLE)

@app.route('/explanation')
@login_required
def explanation():
    result = session.get('explanation_result')
    code = session.get('current_code', '')
    if not result:
        flash('No explanation available. Please analyze code first.', 'info')
        return redirect(url_for('app_view'))
    return render_template('explanation.html', result=result, code=code)

@app.route('/ast_view')
@login_required
def ast_view():
    ast_result = session.get('ast_result')
    code = session.get('current_code', '')
    if not ast_result:
        flash('No AST available.', 'info')
        return redirect(url_for('app_view'))
    return render_template('ast_view.html', ast_result=ast_result, code=code)

@app.route('/trace_view')
@login_required
def trace_view():
    trace_result = session.get('trace_result')
    code = session.get('current_code', '')
    if not trace_result:
        flash('No trace available.', 'info')
        return redirect(url_for('app_view'))
    return render_template('trace_view.html', trace_result=trace_result, code=code)

@app.route('/concepts', methods=['GET', 'POST'])
@login_required
def concepts():
    search = request.form.get('search', '').lower() if request.method == 'POST' else ''
    rag_query = request.form.get('rag_query', '')
    
    result = session.get('explanation_result', {})
    concepts = result.get('concepts', [])
    filtered_concepts = [c for c in concepts if search in c['concept'].lower() or search in c['definition'].lower()] if search else concepts
    
    search_res = None
    if rag_query:
        try:
            search_res = client.search_rag(rag_query)
        except Exception as e:
            flash(f"Search failed: {e}", "danger")
            
    return render_template('concepts.html', concepts=filtered_concepts, search=search, search_res=search_res, rag_query=rag_query)

@app.route('/quiz', methods=['GET', 'POST'])
@login_required
def quiz():
    code = session.get('current_code', '')
    language = session.get('current_language', 'python')
    
    if not code:
        flash('No code loaded to generate quiz.', 'info')
        return redirect(url_for('app_view'))

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'generate':
            try:
                quiz_result = client.generate_quiz(code, language)
                session['quiz_result'] = quiz_result
            except Exception as e:
                flash(f'Quiz generation failed: {str(e)}', 'danger')
        elif action == 'submit':
            answers = {}
            for key, val in request.form.items():
                if key.startswith('q_'):
                    answers[key[2:]] = val
            session['quiz_answers'] = answers
            session['quiz_submitted'] = True

    quiz_result = session.get('quiz_result')
    answers = session.get('quiz_answers', {})
    submitted = session.get('quiz_submitted', False)
    
    return render_template('quiz.html', quiz_result=quiz_result, answers=answers, submitted=submitted, code=code)

@app.route('/history')
@login_required
def history():
    hist = client.get_history(limit=50)
    return render_template('history.html', history=hist)

@app.route('/history/<int:item_id>')
@login_required
def load_history(item_id):
    detail = client.get_history_item(item_id)
    if detail:
        session['current_code'] = detail.get('code', '')
        session['current_language'] = detail.get('language', 'python')
        session['explanation_result'] = {
            "id": detail.get("id"),
            "language": detail.get("language"),
            "level": detail.get("level"),
            "summary": detail.get("summary"),
            "blocks": detail.get("blocks", []),
            "concepts": detail.get("concepts", []),
            "algorithm_steps": (detail.get("explanation") or {}).get("algorithm_steps", []),
            "complexity": (detail.get("explanation") or {}).get("complexity", {}),
            "hints": (detail.get("explanation") or {}).get("hints", []),
        }
        flash(f"Loaded submission #{item_id}", "success")
        return redirect(url_for('explanation'))
    flash("Could not load details.", "danger")
    return redirect(url_for('history'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        try:
            res = client.login(username, password)
            session['user_id'] = res['id']
            session['username'] = res['username']
            flash('Logged in successfully!', 'success')
            return redirect(url_for('app_view'))
        except Exception as e:
            flash('Login failed. Please check your credentials.', 'danger')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        try:
            res = client.signup(username, password)
            session['user_id'] = res['id']
            session['username'] = res['username']
            flash('Signed up and logged in successfully!', 'success')
            return redirect(url_for('app_view'))
        except Exception as e:
            flash(f'Signup failed: {str(e)}', 'danger')
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out.', 'info')
    return redirect(url_for('landing'))

@app.route('/profile')
@login_required
def profile():
    hist = client.get_history(limit=50) # In a real app we'd filter by user_id
    return render_template('profile.html', user=session.get('username'), history=hist)

if __name__ == '__main__':
    app.run(port=5001, debug=True)
