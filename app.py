import os, secrets, sqlite3, hashlib, hmac, math
from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path
from flask import Flask, request, redirect, url_for, render_template_string, flash, session, g, abort

BASE_DIR = Path(__file__).resolve().parent
# On Render, set DB_PATH to a path on a persistent disk (for example /var/data/pilo.db).
DB_PATH = Path(os.environ.get('DB_PATH', str(BASE_DIR / 'pilo.db')))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY') or secrets.token_hex(32),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SECURE', '0') == '1',
    PERMANENT_SESSION_LIFETIME=timedelta(days=14),
    MAX_CONTENT_LENGTH=1 * 1024 * 1024,
)

CATEGORIES = ['Alimentation', 'Logement', 'Transport / carburant', 'Téléphone / Internet', 'Études', 'Santé', 'Hygiène', 'Entretien moto / équipement', 'Loisirs', 'Autre']
FREQUENCIES = {'once': 'Une seule fois', 'weekly': 'Chaque semaine', 'monthly': 'Chaque mois'}

# ---------- Database ----------
def db_conn():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH, timeout=15)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
        g.db.execute('PRAGMA journal_mode = WAL')
    return g.db

@app.teardown_appcontext
def close_db(_error=None):
    conn = g.pop('db', None)
    if conn is not None:
        conn.close()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA foreign_keys = ON')
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT NOT NULL,
      email TEXT NOT NULL COLLATE NOCASE UNIQUE, institution TEXT DEFAULT '',
      field_of_study TEXT DEFAULT '', password_hash TEXT NOT NULL,
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS budgets (
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      title TEXT NOT NULL DEFAULT 'Mon budget', period_type TEXT NOT NULL DEFAULT 'monthly',
      start_date TEXT NOT NULL, end_date TEXT NOT NULL, initial_amount INTEGER NOT NULL DEFAULT 0,
      savings_target INTEGER NOT NULL DEFAULT 0, savings_current INTEGER NOT NULL DEFAULT 0,
      savings_deadline TEXT DEFAULT '', emergency_reserve INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS expenses (
      id INTEGER PRIMARY KEY AUTOINCREMENT, budget_id INTEGER NOT NULL REFERENCES budgets(id) ON DELETE CASCADE,
      user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      label TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'Autre', quantity REAL NOT NULL DEFAULT 1,
      unit_price INTEGER NOT NULL DEFAULT 0, frequency TEXT NOT NULL DEFAULT 'once',
      priority TEXT NOT NULL DEFAULT 'normal', due_date TEXT DEFAULT '', is_saving INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS transactions (
      id INTEGER PRIMARY KEY AUTOINCREMENT, budget_id INTEGER NOT NULL REFERENCES budgets(id) ON DELETE CASCADE,
      user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, label TEXT NOT NULL,
      category TEXT NOT NULL DEFAULT 'Autre', amount INTEGER NOT NULL CHECK(amount > 0),
      transaction_date TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'expense', notes TEXT DEFAULT '',
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_budgets_user ON budgets(user_id);
    CREATE INDEX IF NOT EXISTS idx_expenses_budget ON expenses(budget_id, user_id);
    CREATE INDEX IF NOT EXISTS idx_transactions_budget ON transactions(budget_id, user_id);
    ''')
    conn.commit(); conn.close()

init_db()

# ---------- Security and helpers ----------
def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 310000)
    return salt.hex() + '$' + digest.hex()

def check_password(password, stored):
    try:
        salt_hex, digest_hex = stored.split('$', 1)
        actual = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt_hex), 310000).hex()
        return hmac.compare_digest(actual, digest_hex)
    except (ValueError, TypeError):
        return False

def csrf_token():
    if '_csrf' not in session:
        session['_csrf'] = secrets.token_urlsafe(32)
    return session['_csrf']
app.jinja_env.globals['csrf_token'] = csrf_token

@app.before_request
def csrf_protect():
    if request.method == 'POST':
        sent = request.form.get('_csrf', '')
        expected = session.get('_csrf', '')
        if not sent or not expected or not hmac.compare_digest(sent, expected):
            abort(400, description='Formulaire expiré ou invalide. Rechargez la page puis réessayez.')

@app.before_request
def load_user():
    uid = session.get('user_id')
    g.user = None
    if uid:
        g.user = db_conn().execute('SELECT id, full_name, email, institution, field_of_study FROM users WHERE id=?', (uid,)).fetchone()
        if g.user is None:
            session.clear()

@app.context_processor
def inject_globals():
    return {'current_user': getattr(g, 'user', None), 'today': date.today().isoformat(), 'categories': CATEGORIES, 'frequencies': FREQUENCIES}

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not getattr(g, 'user', None):
            flash('Connectez-vous pour accéder à votre espace.', 'info')
            return redirect(url_for('login', next=request.path))
        return fn(*args, **kwargs)
    return wrapped

def money(value):
    return f"{int(round(value or 0)):,}".replace(',', ' ')
app.jinja_env.filters['fcfa'] = money

def as_int(value, default=0):
    try:
        n = int(float(value))
        return max(0, n)
    except (ValueError, TypeError): return default

def valid_date(value, fallback=None):
    try: return date.fromisoformat(value).isoformat()
    except (ValueError, TypeError): return (fallback or date.today()).isoformat()

def get_budget(budget_id=None):
    if not g.user: return None
    conn = db_conn()
    if budget_id:
        row = conn.execute('SELECT * FROM budgets WHERE id=? AND user_id=?', (budget_id, g.user['id'])).fetchone()
        if not row: abort(404)
        return row
    return conn.execute('SELECT * FROM budgets WHERE user_id=? ORDER BY id DESC LIMIT 1', (g.user['id'],)).fetchone()

def create_default_budget(user_id):
    start = date.today().replace(day=1)
    next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    end = next_month - timedelta(days=1)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('INSERT INTO budgets(user_id,title,period_type,start_date,end_date) VALUES(?,?,?,?,?)',
                     (user_id, 'Mon budget', 'monthly', start.isoformat(), end.isoformat()))

def frequency_cost(row, period_type):
    base = float(row['quantity'] or 1) * int(row['unit_price'] or 0)
    freq = row['frequency']
    if freq == 'weekly': return base * (52/12 if period_type == 'monthly' else 1)
    if freq == 'monthly': return base if period_type == 'monthly' else base * (12/52)
    return base

def budget_summary(budget):
    conn = db_conn(); bid = budget['id']; uid = g.user['id']
    expenses = conn.execute('SELECT * FROM expenses WHERE budget_id=? AND user_id=? ORDER BY is_saving DESC, priority DESC, id DESC', (bid, uid)).fetchall()
    transactions = conn.execute('SELECT * FROM transactions WHERE budget_id=? AND user_id=? ORDER BY transaction_date DESC,id DESC', (bid, uid)).fetchall()
    planned = sum(frequency_cost(e, budget['period_type']) for e in expenses if not e['is_saving'])
    planned_savings = sum(frequency_cost(e, budget['period_type']) for e in expenses if e['is_saving'])
    actual_out = sum(t['amount'] for t in transactions if t['kind'] == 'expense')
    actual_in = sum(t['amount'] for t in transactions if t['kind'] == 'income')
    income = int(budget['initial_amount']) + actual_in
    savings = int(budget['savings_current']) + planned_savings
    remaining_forecast = income - planned - planned_savings - int(budget['emergency_reserve'])
    real_balance = int(budget['initial_amount']) + actual_in - actual_out - int(budget['savings_current'])
    essential = sum(frequency_cost(e, budget['period_type']) for e in expenses if not e['is_saving'] and e['priority'] == 'essential')
    discretionary = sum(frequency_cost(e, budget['period_type']) for e in expenses if not e['is_saving'] and e['priority'] == 'optional')
    # Margin thresholds are transparent examples, not financial advice or universal rules.
    if remaining_forecast < 0: status, status_text = 'red', f'Déficit prévisionnel de {money(-remaining_forecast)} FCFA.'
    elif remaining_forecast < max(3000, income * .05): status, status_text = 'orange', 'Marge faible : vérifiez les imprévus et vos priorités.'
    else: status, status_text = 'green', 'Budget prévisionnel compatible avec une marge.'
    cats = {}
    for e in expenses:
        if not e['is_saving']:
            cats[e['category']] = cats.get(e['category'], 0) + frequency_cost(e, budget['period_type'])
    actual_by_cat = {}
    for t in transactions:
        if t['kind'] == 'expense': actual_by_cat[t['category']] = actual_by_cat.get(t['category'], 0) + t['amount']
    days = max(1, (date.fromisoformat(budget['end_date']) - max(date.today(), date.fromisoformat(budget['start_date']))).days + 1)
    weekly_cap = max(0, remaining_forecast) / days * 7
    target = int(budget['savings_target']); current_saved = int(budget['savings_current'])
    goal_pct = min(100, round(current_saved * 100 / target)) if target else 0
    return dict(expenses=expenses, transactions=transactions, planned=round(planned), planned_savings=round(planned_savings), actual_out=actual_out, actual_in=actual_in, income=income, savings=savings, remaining_forecast=round(remaining_forecast), real_balance=real_balance, essential=round(essential), discretionary=round(discretionary), status=status, status_text=status_text, categories=cats, actual_by_cat=actual_by_cat, weekly_cap=round(weekly_cap), goal_pct=goal_pct)

# ---------- UI ----------
STYLE = '''
:root{--ink:#14251f;--muted:#68766f;--green:#13795b;--lime:#c9f36b;--paper:#f5f8f4;--line:#e2e9e1;--white:#fff;--red:#b42318;--orange:#a15c00}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.5 Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif}a{color:inherit;text-decoration:none}.top{background:#102a22;color:white;padding:16px max(20px,calc((100% - 1160px)/2));display:flex;align-items:center;justify-content:space-between;gap:18px}.brand{font-size:23px;font-weight:850;letter-spacing:-1px}.brand span{color:var(--lime)}.nav{display:flex;align-items:center;gap:15px;flex-wrap:wrap;font-size:14px}.container{max-width:1160px;margin:28px auto;padding:0 20px}.hero{background:#102a22;color:white;border-radius:26px;padding:38px;display:grid;grid-template-columns:1.4fr 1fr;gap:22px;align-items:center}.hero h1{font-size:clamp(32px,5vw,52px);line-height:1.03;letter-spacing:-2px;margin:10px 0 18px}.hero p{color:#d1dfd7;max-width:560px}.eyebrow{text-transform:uppercase;letter-spacing:1.8px;font-size:11px;font-weight:800;color:var(--green)}.hero .eyebrow{color:var(--lime)}.hero-card{background:#1b3c30;border:1px solid #315447;border-radius:20px;padding:22px}.hero-card strong{font-size:31px;display:block}.btn{border:0;border-radius:12px;background:var(--green);color:white;padding:11px 16px;display:inline-flex;align-items:center;justify-content:center;font-weight:750;cursor:pointer;font:inherit;font-weight:750}.btn.light{background:var(--lime);color:#183025}.btn.secondary{background:#e8f0e9;color:#174b39}.btn.danger{background:#fff0ef;color:#9f241b}.btn.small{padding:7px 10px;font-size:13px}.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:16px;margin:18px 0}.card{background:white;border:1px solid var(--line);border-radius:18px;padding:20px;box-shadow:0 5px 22px #1a39200a}.span-3{grid-column:span 3}.span-4{grid-column:span 4}.span-5{grid-column:span 5}.span-6{grid-column:span 6}.span-7{grid-column:span 7}.span-8{grid-column:span 8}.span-12{grid-column:span 12}.metric-label{font-size:13px;color:var(--muted)}.metric{font-size:clamp(23px,3vw,31px);font-weight:850;letter-spacing:-1px;margin:6px 0}.sub{font-size:12px;color:var(--muted)}h1,h2,h3{letter-spacing:-.5px}h2{font-size:23px;margin:0 0 5px}h3{font-size:17px;margin:0 0 12px}.section-head{display:flex;align-items:end;justify-content:space-between;gap:14px;flex-wrap:wrap;margin:26px 0 12px}.form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.field{display:flex;flex-direction:column;gap:6px}.field.full{grid-column:1/-1}label{font-size:13px;font-weight:750}input,select,textarea{width:100%;border:1px solid #d6e0d7;background:white;border-radius:10px;padding:11px 12px;color:var(--ink);font:inherit;min-width:0}input:focus,select:focus,textarea:focus{outline:2px solid #9bd8bb;border-color:var(--green)}.hint{font-size:12px;color:var(--muted)}.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;min-width:620px}th,td{text-align:left;padding:12px 10px;border-bottom:1px solid var(--line);font-size:13px}th{color:var(--muted);font-weight:700}.pill{display:inline-block;padding:5px 9px;border-radius:100px;font-size:12px;font-weight:800;background:#edf2ed}.green{background:#e4f8e9;color:#17633d}.orange{background:#fff0d6;color:#8a4b00}.red{background:#ffe6e4;color:#a32018}.bar{height:9px;background:#edf1ed;border-radius:20px;overflow:hidden;margin:10px 0}.bar span{display:block;height:100%;background:var(--green);border-radius:20px}.flash{padding:12px 15px;border-radius:12px;margin:10px 0;background:#e5f5e9;color:#165c39}.flash.error{background:#ffebe9;color:#9c2219}.flash.warning{background:#fff2d9;color:#8a4b00}.muted{color:var(--muted)}.auth{max-width:520px;margin:35px auto}.auth .card{padding:28px}.empty{text-align:center;padding:30px;color:var(--muted)}.footer{max-width:1160px;margin:40px auto 20px;padding:0 20px;color:var(--muted);font-size:12px}.split{display:flex;justify-content:space-between;gap:12px;align-items:center}.smalltext{font-size:12px}.inline-form{display:inline}.checkrow{display:flex;align-items:center;gap:8px}.checkrow input{width:auto}.danger-text{color:var(--red)}@media(max-width:800px){.hero{grid-template-columns:1fr;padding:25px}.span-3,.span-4,.span-5,.span-6,.span-7,.span-8{grid-column:span 12}.container{margin-top:18px}.top{align-items:flex-start;flex-direction:column}.form-grid{grid-template-columns:1fr}.field.full{grid-column:auto}.metric{font-size:27px}}@media(min-width:801px){.span-3{grid-column:span 3}}
'''
BASE = '''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#102a22"><title>{{ title }} · Pilo Étudiant</title><style>''' + STYLE + '''</style></head><body><header class="top"><a class="brand" href="{{ url_for('home') }}">pilo<span>.</span></a><nav class="nav">{% if current_user %}<a href="{{ url_for('dashboard') }}">Mon budget</a><a href="{{ url_for('budget_settings') }}">Paramètres</a><span>{{ current_user['full_name'] }}</span><form class="inline-form" method="post" action="{{ url_for('logout') }}"><input type="hidden" name="_csrf" value="{{ csrf_token() }}"><button class="btn small secondary" type="submit">Déconnexion</button></form>{% else %}<a href="{{ url_for('login') }}">Connexion</a><a class="btn small light" href="{{ url_for('register') }}">Créer un compte</a>{% endif %}</nav></header><main class="container">{% with messages=get_flashed_messages(with_categories=true) %}{% for category,message in messages %}<div class="flash {{ category }}">{{ message }}</div>{% endfor %}{% endwith %}{{ body|safe }}</main><footer class="footer">Pilo Étudiant · Gérez votre argent avec clarté. Les prévisions sont des estimations : adaptez-les à votre situation.</footer></body></html>'''
def page(title, template, **context):
    body = render_template_string(template, **context)
    return render_template_string(BASE, title=title, body=body)

HOME = '''<section class="hero"><div><div class="eyebrow">Le budget étudiant, sans prise de tête</div><h1>Ton argent.<br>Ton rythme.<br><span style="color:var(--lime)">Tes choix.</span></h1><p>Pilo t’aide à comprendre où va ton argent, à prévoir tes dépenses et à avancer vers tes objectifs, sans décider à ta place.</p><div class="actions"><a class="btn light" href="{{ url_for('register') }}">Créer mon espace gratuit →</a><a class="btn secondary" href="{{ url_for('login') }}">J’ai déjà un compte</a></div><p class="smalltext">FCFA · Budget personnalisable · Suivi des dépenses réelles</p></div><div class="hero-card"><div class="eyebrow">Un budget plus lisible</div><p>Disponible</p><strong>25 000 FCFA</strong><div class="bar"><span style="width:68%"></span></div><div class="split"><span class="sub">Dépenses prévues</span><b>68 %</b></div><hr style="border:0;border-top:1px solid #315447;margin:18px 0"><div class="split"><span>🎯 Épargne</span><b>Objectif personnel</b></div><div class="split" style="margin-top:12px"><span>🔔 Alertes</span><b>Avant le dépassement</b></div><p class="sub">Exemple illustratif, pas une promesse de résultat.</p></div></section><div class="grid"><article class="card span-4"><div class="eyebrow">01 · Comprendre</div><h3>Vois ton budget d’un coup d’œil</h3><p class="muted">Revenus, dépenses prévues, dépenses réelles et argent restant, séparés clairement.</p></article><article class="card span-4"><div class="eyebrow">02 · Décider</div><h3>Garde la main</h3><p class="muted">Modifie tes catégories, tes priorités, tes prix et tes objectifs à tout moment.</p></article><article class="card span-4"><div class="eyebrow">03 · Progresser</div><h3>Épargne à ton rythme</h3><p class="muted">Teste plusieurs scénarios sans couper automatiquement les dépenses essentielles.</p></article></div>'''

REGISTER = '''<section class="auth"><div class="card"><div class="eyebrow">Ton espace personnel</div><h1>Créer mon compte</h1><p class="muted">Tes données budgétaires seront rattachées à ton compte.</p><form method="post" class="form-grid"><input type="hidden" name="_csrf" value="{{ csrf_token() }}"><div class="field full"><label>Nom et prénom *</label><input name="full_name" required maxlength="100" autocomplete="name" value="{{ request.form.get('full_name','') }}"></div><div class="field full"><label>Adresse e-mail *</label><input name="email" type="email" required maxlength="254" autocomplete="email" value="{{ request.form.get('email','') }}"></div><div class="field"><label>Établissement (facultatif)</label><input name="institution" maxlength="120"></div><div class="field"><label>Filière (facultatif)</label><input name="field_of_study" maxlength="120"></div><div class="field"><label>Mot de passe *</label><input type="password" name="password" minlength="10" required autocomplete="new-password"><span class="hint">Au moins 10 caractères.</span></div><div class="field"><label>Confirmer le mot de passe *</label><input type="password" name="confirm_password" minlength="10" required autocomplete="new-password"></div><div class="field full"><button class="btn" type="submit">Créer mon espace →</button></div></form><p class="muted">Déjà inscrit ? <a href="{{ url_for('login') }}"><b>Se connecter</b></a></p></div></section>'''
LOGIN = '''<section class="auth"><div class="card"><div class="eyebrow">Content de te revoir</div><h1>Connexion</h1><p class="muted">Connecte-toi pour retrouver ton budget.</p><form method="post" class="form-grid"><input type="hidden" name="_csrf" value="{{ csrf_token() }}"><div class="field full"><label>Adresse e-mail</label><input name="email" type="email" required autocomplete="email" value="{{ request.form.get('email','') }}"></div><div class="field full"><label>Mot de passe</label><input name="password" type="password" required autocomplete="current-password"></div><div class="field full"><button class="btn" type="submit">Me connecter →</button></div></form><p class="muted">Pas encore de compte ? <a href="{{ url_for('register') }}"><b>Créer un compte</b></a></p><p class="hint">Mot de passe oublié ? Pour cette première version, la récupération automatique par e-mail n'est pas activée. Contacte l'administrateur du service plutôt que de créer un autre compte.</p></div></section>'''

DASHBOARD = '''{% if not budget %}<section class="card"><h1>Bienvenue sur Pilo, {{ current_user['full_name'].split(' ')[0] }} !</h1><p>Configure ton premier budget pour commencer.</p><a class="btn" href="{{ url_for('budget_settings') }}">Configurer mon budget →</a></section>{% else %}<div class="section-head"><div><div class="eyebrow">Ton espace personnel</div><h1>Bonjour {{ current_user['full_name'].split(' ')[0] }} 👋</h1><p class="muted">{{ budget['title'] }} · {{ budget['start_date'] }} au {{ budget['end_date'] }}</p></div><div class="actions"><a class="btn secondary" href="{{ url_for('budget_settings') }}">Modifier le budget</a><a class="btn" href="{{ url_for('expense_add') }}">+ Dépense prévue</a></div></div><div class="grid"><article class="card span-3"><div class="metric-label">Argent prévu disponible</div><div class="metric">{{ s.remaining_forecast|fcfa }} <small>FCFA</small></div><span class="pill {{ s.status }}">Prévision</span></article><article class="card span-3"><div class="metric-label">Solde réel estimé</div><div class="metric">{{ s.real_balance|fcfa }} <small>FCFA</small></div><span class="sub">Après dépenses enregistrées</span></article><article class="card span-3"><div class="metric-label">Dépenses prévues</div><div class="metric">{{ s.planned|fcfa }} <small>FCFA</small></div><span class="sub">Hors épargne et réserve</span></article><article class="card span-3"><div class="metric-label">Dépenses réelles</div><div class="metric">{{ s.actual_out|fcfa }} <small>FCFA</small></div><span class="sub">{{ s.actual_in|fcfa }} FCFA de revenus ajoutés</span></article><article class="card span-8"><div class="split"><div><h2>État de ton budget</h2><p class="muted">{{ s.status_text }}</p></div><span class="pill {{ s.status }}">{% if s.status=='green' %}Marge correcte{% elif s.status=='orange' %}Attention{% else %}Déficit{% endif %}</span></div><div class="grid"><div class="span-6"><div class="metric-label">Revenus et argent initial</div><div class="metric">{{ s.income|fcfa }} FCFA</div></div><div class="span-6"><div class="metric-label">Réserve d’urgence prévue</div><div class="metric">{{ budget['emergency_reserve']|fcfa }} FCFA</div></div></div><div class="bar"><span style="width:{{ [100, (s.planned+s.planned_savings+budget['emergency_reserve'])*100/s.income if s.income else 0]|min }}%"></span></div><p class="hint">Repère d’alerte : une marge inférieure au plus élevé de 3 000 FCFA ou 5 % du montant disponible est signalée comme faible. Ce seuil est indicatif et doit être adapté à ta situation.</p><div class="actions"><a class="btn" href="{{ url_for('transaction_add') }}">+ Enregistrer une dépense réelle</a><a class="btn secondary" href="{{ url_for('expense_add') }}">Ajouter une prévision</a></div></article><article class="card span-4"><h3>🎯 Mon objectif d’épargne</h3>{% if budget['savings_target'] %}<div class="metric">{{ budget['savings_current']|fcfa }} <small>FCFA</small></div><p class="muted">sur {{ budget['savings_target']|fcfa }} FCFA</p><div class="bar"><span style="width:{{ s.goal_pct }}%"></span></div><b>{{ s.goal_pct }} % atteint</b>{% if budget['savings_deadline'] %}<p class="hint">Échéance : {{ budget['savings_deadline'] }}</p>{% endif %}{% else %}<p class="muted">Tu n’as pas encore défini d’objectif. Choisis un montant réaliste selon tes dépenses essentielles.</p>{% endif %}<a class="btn secondary" href="{{ url_for('budget_settings') }}">Gérer mon objectif</a></article></div><div class="section-head"><div><h2>Répartition par catégorie</h2><p class="muted">Prévisions comparées aux dépenses enregistrées.</p></div></div><div class="grid"><article class="card span-6">{% if s.categories %}{% for cat,amount in s.categories.items() %}<div class="split"><span>{{ cat }}</span><b>{{ amount|fcfa }} FCFA</b></div><div class="bar"><span style="width:{{ [100, amount*100/(s.income or 1)]|min }}%"></span></div><div class="sub">Dépenses réelles : {{ s.actual_by_cat.get(cat,0)|fcfa }} FCFA</div>{% endfor %}{% else %}<div class="empty">Ajoute tes dépenses prévues pour voir la répartition.</div>{% endif %}</article><article class="card span-6"><h3>📆 Repères pratiques</h3><div class="split"><span>Plafond hebdomadaire indicatif</span><b>{{ s.weekly_cap|fcfa }} FCFA</b></div><p class="hint">Calculé à partir du solde prévisionnel et des jours restants. Ce n’est pas une limite imposée.</p><hr style="border:0;border-top:1px solid var(--line);margin:16px 0"><div class="split"><span>Épargne prévue dans ce budget</span><b>{{ s.planned_savings|fcfa }} FCFA</b></div><div class="split"><span>Réserve d’urgence</span><b>{{ budget['emergency_reserve']|fcfa }} FCFA</b></div><div class="split"><span>Montant essentiel identifié</span><b>{{ s.essential|fcfa }} FCFA</b></div><div class="split"><span>Dépenses facultatives</span><b>{{ s.discretionary|fcfa }} FCFA</b></div></article></div><div class="section-head"><div><h2>Mes dépenses prévues</h2><p class="muted">Modifie-les librement selon tes besoins.</p></div><a class="btn small" href="{{ url_for('expense_add') }}">+ Ajouter</a></div><div class="card table-wrap">{% if s.expenses %}<table><thead><tr><th>Libellé</th><th>Catégorie</th><th>Quantité × prix</th><th>Fréquence</th><th>Montant estimé</th><th>Actions</th></tr></thead><tbody>{% for e in s.expenses %}<tr><td><b>{{ e['label'] }}</b>{% if e['is_saving'] %}<div class="sub">Épargne</div>{% endif %}</td><td>{{ e['category'] }}</td><td>{{ e['quantity'] }} × {{ e['unit_price']|fcfa }}</td><td>{{ frequencies.get(e['frequency'],e['frequency']) }}</td><td><b>{{ (e['quantity']*e['unit_price'])|fcfa }} FCFA</b></td><td><a class="btn small secondary" href="{{ url_for('expense_add', expense_id=e['id']) }}">Modifier</a> <form class="inline-form" method="post" action="{{ url_for('expense_delete',expense_id=e['id']) }}" onsubmit="return confirm('Supprimer cette prévision ?')"><input type="hidden" name="_csrf" value="{{ csrf_token() }}"><button class="btn small danger">Supprimer</button></form></td></tr>{% endfor %}</tbody></table>{% else %}<div class="empty">Aucune dépense prévue. Commence par ajouter le loyer, l’alimentation, le transport ou les dépenses d’études qui te concernent.</div>{% endif %}</div><div class="section-head"><div><h2>Derniers mouvements réels</h2><p class="muted">Enregistre ce qui est réellement dépensé ou reçu.</p></div><a class="btn small" href="{{ url_for('transaction_add') }}">+ Mouvement</a></div><div class="card table-wrap">{% if s.transactions %}<table><thead><tr><th>Date</th><th>Libellé</th><th>Catégorie</th><th>Type</th><th>Montant</th><th>Action</th></tr></thead><tbody>{% for t in s.transactions[:10] %}<tr><td>{{ t['transaction_date'] }}</td><td>{{ t['label'] }}</td><td>{{ t['category'] }}</td><td><span class="pill {{ 'green' if t['kind']=='income' else 'orange' }}">{{ 'Entrée' if t['kind']=='income' else 'Dépense' }}</span></td><td>{{ t['amount']|fcfa }} FCFA</td><td><form method="post" action="{{ url_for('transaction_delete',transaction_id=t['id']) }}" onsubmit="return confirm('Supprimer ce mouvement ?')"><input type="hidden" name="_csrf" value="{{ csrf_token() }}"><button class="btn small danger">Supprimer</button></form></td></tr>{% endfor %}</tbody></table>{% else %}<div class="empty">Pas encore de mouvement réel enregistré.</div>{% endif %}</div>{% endif %}'''

BUDGET_FORM = '''<div class="section-head"><div><div class="eyebrow">Personnalisation</div><h1>Paramètres du budget</h1><p class="muted">Renseigne des montants réels, sans appliquer de pourcentage universel.</p></div></div><div class="card"><form method="post" class="form-grid"><input type="hidden" name="_csrf" value="{{ csrf_token() }}"><div class="field full"><label>Nom du budget</label><input name="title" required maxlength="100" value="{{ budget['title'] if budget else 'Mon budget' }}"></div><div class="field"><label>Période de référence</label><select name="period_type"><option value="monthly" {{ 'selected' if not budget or budget['period_type']=='monthly' }}>Mensuelle</option><option value="weekly" {{ 'selected' if budget and budget['period_type']=='weekly' }}>Hebdomadaire</option></select></div><div class="field"><label>Argent disponible au départ (FCFA)</label><input name="initial_amount" type="number" min="0" step="1" required value="{{ budget['initial_amount'] if budget else 0 }}"><span class="hint">Pour des revenus irréguliers, ajoute les sommes reçues comme entrées réelles plutôt que de les supposer garanties.</span></div><div class="field"><label>Début de période</label><input name="start_date" type="date" required value="{{ budget['start_date'] if budget else today }}"></div><div class="field"><label>Fin de période</label><input name="end_date" type="date" required value="{{ budget['end_date'] if budget else today }}"></div><div class="field"><label>Objectif total d’épargne (FCFA)</label><input name="savings_target" type="number" min="0" value="{{ budget['savings_target'] if budget else 0 }}"></div><div class="field"><label>Épargne déjà mise de côté (FCFA)</label><input name="savings_current" type="number" min="0" value="{{ budget['savings_current'] if budget else 0 }}"></div><div class="field"><label>Date cible d’épargne (facultatif)</label><input name="savings_deadline" type="date" value="{{ budget['savings_deadline'] if budget else '' }}"></div><div class="field"><label>Réserve d’urgence séparée (FCFA)</label><input name="emergency_reserve" type="number" min="0" value="{{ budget['emergency_reserve'] if budget else 0 }}"><span class="hint">Cette réserve est distincte de l’objectif d’épargne.</span></div><div class="field full"><button class="btn" type="submit">Enregistrer mon budget →</button></div></form></div><div class="card" style="margin-top:16px"><h3>Mon profil</h3><p>{{ current_user['full_name'] }} · {{ current_user['email'] }}</p><p class="muted">{{ current_user['institution'] or 'Établissement non renseigné' }} · {{ current_user['field_of_study'] or 'Filière non renseignée' }}</p><a class="btn secondary" href="{{ url_for('profile') }}">Modifier mon profil</a></div>'''

EXPENSE_FORM = '''<div class="auth" style="max-width:760px"><div class="card"><div class="eyebrow">Prévision budgétaire</div><h1>{{ 'Modifier une dépense' if expense else 'Ajouter une dépense prévue' }}</h1><p class="muted">Pour un coût mesurable, indique la quantité et le prix unitaire. Le prix n’est jamais imposé par l’application.</p><form method="post" class="form-grid"><input type="hidden" name="_csrf" value="{{ csrf_token() }}"><div class="field full"><label>Libellé *</label><input name="label" maxlength="120" required value="{{ expense['label'] if expense else '' }}" placeholder="Ex. : carburant, photocopies, repas"></div><div class="field"><label>Catégorie</label><select name="category">{% for c in categories %}<option {{ 'selected' if expense and expense['category']==c }}>{{ c }}</option>{% endfor %}</select></div><div class="field"><label>Fréquence</label><select name="frequency">{% for k,v in frequencies.items() %}<option value="{{ k }}" {{ 'selected' if expense and expense['frequency']==k }}>{{ v }}</option>{% endfor %}</select></div><div class="field"><label>Quantité</label><input name="quantity" type="number" min="0.01" step="0.01" required value="{{ expense['quantity'] if expense else 1 }}"></div><div class="field"><label>Prix unitaire (FCFA)</label><input name="unit_price" type="number" min="0" step="1" required value="{{ expense['unit_price'] if expense else 0 }}"></div><div class="field"><label>Priorité</label><select name="priority"><option value="essential" {{ 'selected' if expense and expense['priority']=='essential' }}>Essentielle</option><option value="normal" {{ 'selected' if not expense or expense['priority']=='normal' }}>Prévue / importante</option><option value="optional" {{ 'selected' if expense and expense['priority']=='optional' }}>Facultative</option></select></div><div class="field"><label>Date (facultatif)</label><input name="due_date" type="date" value="{{ expense['due_date'] if expense else '' }}"></div><div class="field full checkrow"><input type="checkbox" id="is_saving" name="is_saving" value="1" {{ 'checked' if expense and expense['is_saving'] }}><label for="is_saving">Il s’agit d’une somme d’épargne planifiée</label></div><div class="field full"><button class="btn">Enregistrer</button><a class="btn secondary" href="{{ url_for('dashboard') }}">Annuler</a></div></form></div></div>'''

TRANSACTION_FORM = '''<div class="auth" style="max-width:720px"><div class="card"><div class="eyebrow">Suivi réel</div><h1>Enregistrer un mouvement</h1><p class="muted">Note les dépenses effectivement faites ou l’argent réellement reçu. Cela mettra à jour ton solde réel estimé.</p><form method="post" class="form-grid"><input type="hidden" name="_csrf" value="{{ csrf_token() }}"><div class="field full"><label>Libellé *</label><input name="label" required maxlength="120" placeholder="Ex. : achat de cahiers"></div><div class="field"><label>Type</label><select name="kind"><option value="expense">Dépense</option><option value="income">Argent reçu</option></select></div><div class="field"><label>Montant (FCFA) *</label><input name="amount" type="number" min="1" required></div><div class="field"><label>Catégorie</label><select name="category">{% for c in categories %}<option>{{ c }}</option>{% endfor %}</select></div><div class="field"><label>Date</label><input name="transaction_date" type="date" value="{{ today }}" required></div><div class="field full"><label>Note (facultatif)</label><input name="notes" maxlength="250" placeholder="Détail utile"></div><div class="field full"><button class="btn">Enregistrer le mouvement</button><a class="btn secondary" href="{{ url_for('dashboard') }}">Annuler</a></div></form></div></div>'''

PROFILE_FORM = '''<div class="auth"><div class="card"><h1>Mon profil</h1><form method="post" class="form-grid"><input type="hidden" name="_csrf" value="{{ csrf_token() }}"><div class="field full"><label>Nom et prénom</label><input name="full_name" required maxlength="100" value="{{ current_user['full_name'] }}"></div><div class="field full"><label>Établissement</label><input name="institution" maxlength="120" value="{{ current_user['institution'] }}"></div><div class="field full"><label>Filière</label><input name="field_of_study" maxlength="120" value="{{ current_user['field_of_study'] }}"></div><div class="field full"><label>Mot de passe actuel (obligatoire pour le changer)</label><input type="password" name="old_password" autocomplete="current-password"></div><div class="field"><label>Nouveau mot de passe</label><input type="password" name="new_password" minlength="10" autocomplete="new-password"></div><div class="field"><label>Confirmer le nouveau mot de passe</label><input type="password" name="confirm_password" minlength="10" autocomplete="new-password"></div><div class="field full"><button class="btn">Enregistrer les modifications</button></div></form></div></div>'''

# ---------- Routes ----------
@app.route('/')
def home():
    if g.user: return redirect(url_for('dashboard'))
    return page('Accueil', HOME)

@app.route('/inscription', methods=['GET','POST'])
def register():
    if g.user: return redirect(url_for('dashboard'))
    if request.method == 'POST':
        name = request.form.get('full_name','').strip()
        email = request.form.get('email','').strip().lower()
        institution = request.form.get('institution','').strip()
        field = request.form.get('field_of_study','').strip()
        password = request.form.get('password','')
        if len(name) < 2 or len(email) < 5 or '@' not in email:
            flash('Renseigne un nom et une adresse e-mail valides.', 'error')
        elif len(password) < 10:
            flash('Le mot de passe doit contenir au moins 10 caractères.', 'error')
        elif password != request.form.get('confirm_password',''):
            flash('Les deux mots de passe ne correspondent pas.', 'error')
        else:
            try:
                cur = db_conn().execute('INSERT INTO users(full_name,email,institution,field_of_study,password_hash) VALUES(?,?,?,?,?)', (name,email,institution,field,hash_password(password)))
                db_conn().commit(); uid = cur.lastrowid
                create_default_budget(uid)
                session.clear(); session['user_id'] = uid; session.permanent = True
                flash('Compte créé. Bienvenue sur Pilo !', 'success')
                return redirect(url_for('dashboard'))
            except sqlite3.IntegrityError:
                flash('Cette adresse e-mail possède déjà un compte. Essaie de te connecter.', 'error')
    return page('Créer un compte', REGISTER)

@app.route('/connexion', methods=['GET','POST'])
def login():
    if g.user: return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email','').strip().lower(); password = request.form.get('password','')
        user = db_conn().execute('SELECT id,password_hash FROM users WHERE email=?', (email,)).fetchone()
        if user and check_password(password, user['password_hash']):
            session.clear(); session['user_id'] = user['id']; session.permanent = True
            return redirect(url_for('dashboard'))
        flash('Adresse e-mail ou mot de passe incorrect.', 'error')
    return page('Connexion', LOGIN)

@app.route('/deconnexion', methods=['POST'])
@login_required
def logout():
    session.clear(); flash('Tu es déconnecté.', 'info'); return redirect(url_for('home'))

@app.route('/budget')
@login_required
def dashboard():
    budget = get_budget()
    s = budget_summary(budget) if budget else None
    return page('Mon budget', DASHBOARD, budget=budget, s=s)

@app.route('/budget/parametres', methods=['GET','POST'])
@login_required
def budget_settings():
    budget = get_budget()
    if request.method == 'POST':
        title = request.form.get('title','Mon budget').strip()[:100] or 'Mon budget'
        period = request.form.get('period_type','monthly')
        start = valid_date(request.form.get('start_date')); end = valid_date(request.form.get('end_date'))
        if period not in ('weekly','monthly'): period = 'monthly'
        if end < start:
            flash('La date de fin doit être égale ou postérieure à la date de début.', 'error')
        else:
            vals = (title,period,start,end,as_int(request.form.get('initial_amount')),as_int(request.form.get('savings_target')),as_int(request.form.get('savings_current')),request.form.get('savings_deadline',''),as_int(request.form.get('emergency_reserve')))
            conn = db_conn()
            if budget:
                conn.execute('UPDATE budgets SET title=?,period_type=?,start_date=?,end_date=?,initial_amount=?,savings_target=?,savings_current=?,savings_deadline=?,emergency_reserve=? WHERE id=? AND user_id=?', vals+(budget['id'],g.user['id']))
            else:
                conn.execute('INSERT INTO budgets(title,period_type,start_date,end_date,initial_amount,savings_target,savings_current,savings_deadline,emergency_reserve,user_id) VALUES(?,?,?,?,?,?,?,?,?,?)', vals+(g.user['id'],))
            conn.commit(); flash('Ton budget a été enregistré.', 'success'); return redirect(url_for('dashboard'))
    return page('Paramètres du budget', BUDGET_FORM, budget=budget)

@app.route('/depenses/ajouter', methods=['GET','POST'])
@app.route('/depenses/<int:expense_id>/modifier', methods=['GET','POST'])
@login_required
def expense_add(expense_id=None):
    budget = get_budget()
    if not budget: flash('Configure d’abord ton budget.', 'warning'); return redirect(url_for('budget_settings'))
    expense = None
    if expense_id:
        expense = db_conn().execute('SELECT * FROM expenses WHERE id=? AND budget_id=? AND user_id=?', (expense_id,budget['id'],g.user['id'])).fetchone()
        if not expense: abort(404)
    if request.method == 'POST':
        label = request.form.get('label','').strip()[:120]; category = request.form.get('category','Autre')
        frequency = request.form.get('frequency','once'); priority = request.form.get('priority','normal')
        quantity = request.form.get('quantity','1')
        try: quantity = float(quantity)
        except ValueError: quantity = 0
        unit_price = as_int(request.form.get('unit_price'))
        if not label or quantity <= 0:
            flash('Indique un libellé et une quantité supérieure à zéro.', 'error')
        elif category not in CATEGORIES or frequency not in FREQUENCIES or priority not in ('essential','normal','optional'):
            flash('Valeur de formulaire invalide.', 'error')
        else:
            vals = (label,category,quantity,unit_price,frequency,priority,request.form.get('due_date',''),1 if request.form.get('is_saving')=='1' else 0)
            conn = db_conn()
            if expense_id:
                conn.execute('UPDATE expenses SET label=?,category=?,quantity=?,unit_price=?,frequency=?,priority=?,due_date=?,is_saving=? WHERE id=? AND budget_id=? AND user_id=?', vals+(expense_id,budget['id'],g.user['id']))
            else:
                conn.execute('INSERT INTO expenses(label,category,quantity,unit_price,frequency,priority,due_date,is_saving,budget_id,user_id) VALUES(?,?,?,?,?,?,?,?,?,?)', vals+(budget['id'],g.user['id']))
            conn.commit(); flash('Dépense prévue enregistrée.', 'success'); return redirect(url_for('dashboard'))
    return page('Dépense prévue', EXPENSE_FORM, expense=expense)

@app.route('/depenses/<int:expense_id>/supprimer', methods=['POST'])
@login_required
def expense_delete(expense_id):
    budget = get_budget()
    if budget:
        db_conn().execute('DELETE FROM expenses WHERE id=? AND budget_id=? AND user_id=?', (expense_id,budget['id'],g.user['id'])); db_conn().commit()
    flash('Prévision supprimée si elle t’appartenait.', 'info'); return redirect(url_for('dashboard'))

@app.route('/mouvements/ajouter', methods=['GET','POST'])
@login_required
def transaction_add():
    budget = get_budget()
    if not budget: flash('Configure d’abord ton budget.', 'warning'); return redirect(url_for('budget_settings'))
    if request.method == 'POST':
        label = request.form.get('label','').strip()[:120]; amount = as_int(request.form.get('amount'))
        kind = request.form.get('kind','expense'); category = request.form.get('category','Autre')
        tdate = valid_date(request.form.get('transaction_date')); notes = request.form.get('notes','').strip()[:250]
        if not label or amount < 1 or kind not in ('expense','income') or category not in CATEGORIES:
            flash('Vérifie le libellé, le montant et les champs choisis.', 'error')
        else:
            db_conn().execute('INSERT INTO transactions(budget_id,user_id,label,category,amount,transaction_date,kind,notes) VALUES(?,?,?,?,?,?,?,?)', (budget['id'],g.user['id'],label,category,amount,tdate,kind,notes))
            db_conn().commit(); flash('Mouvement enregistré.', 'success'); return redirect(url_for('dashboard'))
    return page('Enregistrer un mouvement', TRANSACTION_FORM)

@app.route('/mouvements/<int:transaction_id>/supprimer', methods=['POST'])
@login_required
def transaction_delete(transaction_id):
    budget = get_budget()
    if budget:
        db_conn().execute('DELETE FROM transactions WHERE id=? AND budget_id=? AND user_id=?', (transaction_id,budget['id'],g.user['id'])); db_conn().commit()
    flash('Mouvement supprimé si celui-ci t’appartenait.', 'info'); return redirect(url_for('dashboard'))

@app.route('/profil', methods=['GET','POST'])
@login_required
def profile():
    if request.method == 'POST':
        name = request.form.get('full_name','').strip()[:100]
        institution = request.form.get('institution','').strip()[:120]; field = request.form.get('field_of_study','').strip()[:120]
        oldp = request.form.get('old_password',''); newp = request.form.get('new_password',''); conf = request.form.get('confirm_password','')
        conn = db_conn()
        if len(name) < 2:
            flash('Le nom doit contenir au moins deux caractères.', 'error')
        else:
            user = conn.execute('SELECT password_hash FROM users WHERE id=?', (g.user['id'],)).fetchone()
            if newp:
                if not check_password(oldp,user['password_hash']): flash('Mot de passe actuel incorrect.', 'error')
                elif len(newp) < 10: flash('Le nouveau mot de passe doit contenir au moins 10 caractères.', 'error')
                elif newp != conf: flash('Les nouveaux mots de passe ne correspondent pas.', 'error')
                else:
                    conn.execute('UPDATE users SET full_name=?,institution=?,field_of_study=?,password_hash=? WHERE id=?', (name,institution,field,hash_password(newp),g.user['id']))
                    conn.commit(); flash('Profil et mot de passe mis à jour.', 'success'); return redirect(url_for('profile'))
            else:
                conn.execute('UPDATE users SET full_name=?,institution=?,field_of_study=? WHERE id=?', (name,institution,field,g.user['id']))
                conn.commit(); flash('Profil mis à jour.', 'success'); return redirect(url_for('profile'))
    return page('Mon profil', PROFILE_FORM)

@app.errorhandler(400)
def bad_request(error):
    return page('Formulaire à recharger', '<section class="card"><h1>Formulaire expiré</h1><p>{{ error.description }}</p><a class="btn" href="{{ url_for("home") }}">Retour</a></section>', error=error), 400
@app.errorhandler(404)
def not_found(error):
    return page('Page introuvable', '<section class="card"><h1>Page introuvable</h1><p>Cette page ou cet élément n’existe pas, ou ne t’appartient pas.</p><a class="btn" href="{{ url_for("dashboard") if current_user else url_for("home") }}">Retour</a></section>'), 404

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.environ.get('PORT', '5000')), debug=False)
