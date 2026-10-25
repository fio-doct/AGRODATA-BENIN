Oui, mais attention : ne modifie pas directement les fichiers de ton site actuel sans sauvegarde. Nous allons préparer Pilo Étudiant sur GitHub, puis le déployer sur Render.

Étape 1 — Ouvre ton dépôt GitHub

Clique ici :

Ton dépôt AGRODATA-BENIN sur GitHub

Tu arriveras sur la page qui contient les fichiers de ton application.

Étape 2 — Prépare une sauvegarde

Avant de remplacer quoi que ce soit :

Sur GitHub, ouvre le fichier app.py.
Vérifie que tu es bien sur la branche main.
Télécharge une copie de l'ancien fichier pour pouvoir le récupérer si nécessaire.

Tu peux aussi conserver une copie complète du dépôt sur ton ordinateur.

Étape 3 — Remplacer les fichiers

J'ai préparé les fichiers de la nouvelle application :

Télécharger le projet complet Pilo Étudiant
Code Python app.py
Dépendances requirements.txt
Guide du projet

Cependant, ne remplace pas encore le fichier de production : la nouvelle version doit être testée avant sa publication.

Étape 4 — Dis-moi ce que tu vois

Une fois sur GitHub, regarde les boutons situés au-dessus de la liste des fichiers.

Est-ce que tu vois un bouton vert Code, un bouton Add file et le fichier app.py ?

Réponds simplement oui ou envoie une capture d'écran de la page.

Je te guiderai à partir de ton écran pour mettre les fichiers en place sans casser ton site actuel.

app.py
Code
requirements.txt
Document
README_PILO.md
Document

AGRODATA-BENIN

Public

fio-doct (image)fio-doct

Update print statement from 'Hello' to 'Goodbye'

f148457 · 8 hours ago

Name		
.gitignore	Add .gitignore for Python project files	10 hours ago
README.md	Initial commit	10 hours ago
app.py	Update print statement from 'Hello' to 'Goodbye'	8 hours ago
requirements.txt	Add files via upload	9 hours ago CES MON GITHUB SA

D’accord, c’est bien ton dépôt GitHub. Je vois les fichiers app.py, requirements.txt, README.md et .gitignore.

Attention : il y a un détail important. Le dernier commit s’intitule « Update print statement from 'Hello' to 'Goodbye' ». Cela ne correspond pas au projet agricole que nous avions examiné auparavant. Il faut donc vérifier le contenu actuel de app.py avant de remplacer quoi que ce soit.

Voici ce que nous allons faire

1. Sauvegarder le projet actuel.

Ne supprime aucun fichier pour le moment.

2. Télécharger le nouveau code Pilo Étudiant.

📦 Télécharger Pilo Étudiant — fichiers du projet

3. Vérifier le code avant de le publier.

Le code préparé précédemment n'a pas encore passé de tests fonctionnels complets. Je ne veux donc pas te faire remplacer ton application par une version qui pourrait échouer au démarrage.

Maintenant, fais ceci

Sur ta page GitHub :

Clique sur le fichier app.py.
Copie le code affiché, ou télécharge le fichier.
Envoie-moi le fichier app.py actuel ici.

Je pourrai alors comparer précisément le projet actuel avec la version Pilo, corriger le nouveau code et vérifier les points essentiels avant de te donner une version prête à déployer.

Nous éviterons ainsi de perdre ton travail ou de publier un site défectueux.

from flask import Flask, request, redirect, url_for, render_template_string, flash
import sqlite3
from pathlib import Path
from datetime import date

app = Flask(__name__)
app.secret_key = "agrodata-benin-cle-locale"

DOSSIER = Path(__file__).resolve().parent
DB = DOSSIER / "agrodata.db"

# ---------------- BASE DE DONNEES ----------------

def connexion():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def initialiser_db():
    with connexion() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS plantations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                projet TEXT NOT NULL,
                village TEXT NOT NULL,
                commune TEXT NOT NULL,
                espece TEXT NOT NULL,
                date_plantation TEXT NOT NULL,
                plants_plantes INTEGER NOT NULL,
                plants_vivants INTEGER NOT NULL,
                observations TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS projets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL,
                zone TEXT NOT NULL,
                responsable TEXT DEFAULT '',
                budget REAL DEFAULT 0,
                date_debut TEXT NOT NULL,
                date_fin TEXT DEFAULT '',
                statut TEXT DEFAULT 'En cours'
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS beneficiaires (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL,
                sexe TEXT DEFAULT '',
                village TEXT DEFAULT '',
                commune TEXT DEFAULT '',
                telephone TEXT DEFAULT '',
                projet TEXT DEFAULT ''
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS activites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL,
                projet TEXT DEFAULT '',
                zone TEXT DEFAULT '',
                date_activite TEXT NOT NULL,
                responsable TEXT DEFAULT '',
                statut TEXT DEFAULT 'Planifiée',
                observations TEXT DEFAULT ''
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS productions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                projet TEXT DEFAULT '',
                culture TEXT NOT NULL,
                village TEXT DEFAULT '',
                superficie REAL DEFAULT 0,
                rendement REAL DEFAULT 0,
                campagne TEXT DEFAULT '',
                observations TEXT DEFAULT ''
            )
        """)


# ---------------- INTERFACE ----------------

STYLE = """
<style>
:root {
 --vert:#176b45; --vert2:#21865a; --fond:#f3f6f4;
 --texte:#24332b; --gris:#6b7c72; --blanc:#fff;
 --bord:#e1e9e3; --orange:#e8a23a;
}
*{box-sizing:border-box}
body{margin:0;background:var(--fond);font-family:Arial,sans-serif;color:var(--texte)}
.layout{display:flex;min-height:100vh}
.sidebar{width:245px;background:#123d2b;color:white;padding:25px 16px;flex-shrink:0}
.logo{font-size:23px;font-weight:bold;line-height:1.4;margin:0 10px 4px}
.slogan{font-size:12px;color:#b9d9c7;margin:0 10px 30px}
.menu-title{font-size:11px;text-transform:uppercase;color:#9cc6ad;margin:20px 10px 9px}
.sidebar a{display:block;color:#d8e9df;text-decoration:none;padding:12px 13px;
border-radius:8px;margin:4px 0;font-size:14px}
.sidebar a:hover,.sidebar a.active{background:#24764f;color:white}
.main{flex:1;min-width:0}
.topbar{background:white;padding:20px 30px;border-bottom:1px solid var(--bord);
display:flex;justify-content:space-between;align-items:center;gap:15px}
.topbar h2{margin:0;font-size:20px}
.topbar small{color:var(--gris)}
.content{padding:28px;max-width:1400px;margin:auto}
.hero{background:linear-gradient(120deg,#176b45,#2e9b68);color:white;
border-radius:16px;padding:30px;margin-bottom:25px}
.hero h1{margin:0 0 10px;font-size:28px}
.hero p{margin:0;line-height:1.7;max-width:750px;color:#e4f5e9}
.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;margin:20px 0}
.card,.panel{background:white;border:1px solid var(--bord);border-radius:12px;padding:20px}
.card .label{font-size:13px;color:var(--gris)}
.card .number{font-size:30px;font-weight:bold;margin:12px 0 5px;color:var(--vert)}
.card .note{font-size:12px;color:var(--gris)}
.panel{margin-bottom:22px;overflow-x:auto}
.panel h3{margin:0 0 18px;font-size:17px}
.section-head{display:flex;justify-content:space-between;align-items:center;
gap:12px;flex-wrap:wrap;margin-bottom:20px}
.section-head h1{margin:0;font-size:25px}
.btn{display:inline-block;border:0;background:var(--vert);color:white;padding:11px 16px;
border-radius:7px;text-decoration:none;font-size:13px;cursor:pointer}
.btn:hover{background:var(--vert2)}
.btn-light{background:#e6f2e9;color:var(--vert)}
form.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
.field{display:flex;flex-direction:column;gap:7px}
.field.full{grid-column:1/-1}
label{font-size:13px;font-weight:bold}
input,select,textarea{width:100%;padding:11px;border:1px solid #d3dfd7;
border-radius:7px;font:14px Arial;background:white}
textarea{min-height:85px;resize:vertical}
table{width:100%;border-collapse:collapse;font-size:13px;white-space:nowrap}
th,td{text-align:left;padding:13px 12px;border-bottom:1px solid var(--bord)}
th{color:var(--gris);font-weight:bold;background:#f8faf8}
.badge{display:inline-block;background:#e2f3e7;color:#176b45;padding:5px 8px;
border-radius:20px;font-size:11px;font-weight:bold}
.badge.orange{background:#fff1d9;color:#95600c}
.progress{height:7px;background:#e5eee8;border-radius:8px;overflow:hidden;min-width:70px}
.progress div{height:100%;background:#27925d}
.flash{padding:13px 16px;border-radius:8px;margin-bottom:15px;background:#e1f3e7;color:#176b45}
.flash.error{background:#ffeded;color:#a12626}
.empty{padding:25px;text-align:center;color:var(--gris)}
.footer{text-align:center;color:var(--gris);font-size:12px;padding:25px}
.actions{display:flex;gap:8px;align-items:center}
.delete{background:#ffeded;color:#a12626;border:0;padding:7px 9px;border-radius:6px;cursor:pointer}
@media(max-width:1000px){.cards{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:700px){
 .layout{display:block}.sidebar{width:100%;padding:15px}
 .sidebar .menu-title{display:none}.sidebar a{display:inline-block;padding:9px}
 .slogan{margin-bottom:10px}.topbar{padding:16px}.content{padding:15px}
 .hero{padding:22px}.hero h1{font-size:23px}
 form.grid{grid-template-columns:1fr}.field.full{grid-column:auto}
 .cards{gap:10px}.card{padding:14px}.card .number{font-size:24px}
}
</style>
"""

TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ titre }} | AGRODATA BÉNIN</title>
""" + STYLE + """
</head>
<body>
<div class="layout">
<aside class="sidebar">
  <div class="logo">🌱 AGRODATA<br>BÉNIN</div>
  <div class="slogan">Données agricoles & développement durable</div>
  <div class="menu-title">Général</div>
  <a href="/" class="{{ 'active' if page=='dashboard' else '' }}">▦ Tableau de bord</a>
  <div class="menu-title">Gestion des données</div>
  <a href="/projets" class="{{ 'active' if page=='projets' else '' }}">◈ Projets</a>
  <a href="/plantations" class="{{ 'active' if page=='plantations' else '' }}">♧ Plantations</a>
  <a href="/productions" class="{{ 'active' if page=='productions' else '' }}">▤ Productions</a>
  <a href="/beneficiaires" class="{{ 'active' if page=='beneficiaires' else '' }}">♙ Bénéficiaires</a>
  <a href="/activites" class="{{ 'active' if page=='activites' else '' }}">✓ Activités</a>
  <div class="menu-title">Pilotage</div>
  <a href="/rapports" class="{{ 'active' if page=='rapports' else '' }}">▥ Rapports</a>
</aside>
<main class="main">
<header class="topbar">
  <div><h2>{{ titre }}</h2><small>Suivi-évaluation · Agriculture · Foresterie</small></div>
  <div><span class="badge">{{ aujourd_hui }}</span></div>
</header>
<section class="content">
{% with messages = get_flashed_messages(with_categories=true) %}
{% for categorie, message in messages %}
<div class="flash {{ 'error' if categorie=='error' else '' }}">{{ message }}</div>
{% endfor %}
{% endwith %}
{{ contenu|safe }}
</section>
<div class="footer">AGRODATA BÉNIN · Plateforme de suivi des projets agricoles et environnementaux</div>
</main>
</div>
</body></html>
"""


def page(titre, contenu, page_name):
    return render_template_string(
        TEMPLATE, titre=titre, contenu=contenu, page=page_name,
        aujourd_hui=date.today().strftime("%d/%m/%Y")
    )


def compter(table):
    with connexion() as db:
        return db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


# ---------------- TABLEAU DE BORD ----------------

@app.route("/")
def accueil():
    with connexion() as db:
        nb_plantations = db.execute(
            "SELECT COUNT(*) FROM plantations"
        ).fetchone()[0]
        nb_projets = db.execute("SELECT COUNT(*) FROM projets").fetchone()[0]
        nb_benef = db.execute("SELECT COUNT(*) FROM beneficiaires").fetchone()[0]
        nb_activites = db.execute("SELECT COUNT(*) FROM activites").fetchone()[0]
        total_plantes = db.execute(
            "SELECT COALESCE(SUM(plants_plantes),0) FROM plantations"
        ).fetchone()[0]
        total_vivants = db.execute(
            "SELECT COALESCE(SUM(plants_vivants),0) FROM plantations"
        ).fetchone()[0]
        recentes = db.execute(
            "SELECT * FROM plantations ORDER BY id DESC LIMIT 5"
        ).fetchall()

    taux = round(100 * total_vivants / total_plantes, 1) if total_plantes else 0

    lignes = ""
    for p in recentes:
        lignes += f"""
        <tr><td>{p['projet']}</td><td>{p['village']}</td>
        <td>{p['espece']}</td><td>{p['plants_plantes']:,}</td>
        <td>{p['plants_vivants']:,}</td>
        <td><span class="badge">{round(100*p['plants_vivants']/p['plants_plantes'],1)}%</span></td></tr>
        """

    if not lignes:
        lignes = '<tr><td colspan="6" class="empty">Aucune plantation enregistrée. Commence par ajouter ta première plantation.</td></tr>'

    contenu = f"""
    <div class="hero">
      <h1>Bienvenue sur AGRODATA BÉNIN</h1>
      <p>Une plateforme de collecte, de gestion et d'analyse des données agricoles,
      forestières et environnementales pour faciliter le suivi-évaluation des projets.</p>
      <p style="margin-top:18px"><a class="btn" style="background:white;color:#176b45"
      href="/plantations/ajouter">+ Enregistrer une plantation</a></p>
    </div>
    <div class="cards">
      <div class="card"><div class="label">Projets enregistrés</div><div class="number">{nb_projets}</div><div class="note">Base de données projets</div></div>
      <div class="card"><div class="label">Sites de plantation</div><div class="number">{nb_plantations}</div><div class="note">Enregistrements réalisés</div></div>
      <div class="card"><div class="label">Bénéficiaires</div><div class="number">{nb_benef}</div><div class="note">Personnes recensées</div></div>
      <div class="card"><div class="label">Activités</div><div class="number">{nb_activites}</div><div class="note">Activités planifiées ou suivies</div></div>
    </div>
    <div class="cards">
      <div class="card"><div class="label">Plants mis en terre</div><div class="number">{total_plantes:,}</div><div class="note">Cumul des plantations</div></div>
      <div class="card"><div class="label">Plants vivants</div><div class="number">{total_vivants:,}</div><div class="note">Dernier cumul enregistré</div></div>
      <div class="card"><div class="label">Taux global de survie</div><div class="number">{taux}%</div><div class="progress"><div style="width:{taux}%"></div></div></div>
      <div class="card"><div class="label">Base de données</div><div class="number" style="font-size:21px">SQLite</div><div class="note">Stockage local persistant</div></div>
    </div>
    <div class="panel"><h3>Plantations récemment enregistrées</h3>
    <table><thead><tr><th>Projet</th><th>Village</th><th>Espèce</th><th>Plants plantés</th><th>Plants vivants</th><th>Survie</th></tr></thead>
    <tbody>{lignes}</tbody></table></div>
    """
    return page("Tableau de bord", contenu, "dashboard")


# ---------------- PLANTATIONS ----------------

@app.route("/plantations")
def plantations():
    with connexion() as db:
        lignes_db = db.execute(
            "SELECT * FROM plantations ORDER BY id DESC"
        ).fetchall()

    lignes = ""
    for p in lignes_db:
        taux = round(100*p["plants_vivants"]/p["plants_plantes"], 1)
        lignes += f"""
        <tr>
        <td>{p['projet']}</td><td>{p['village']}</td><td>{p['commune']}</td>
        <td>{p['espece']}</td><td>{p['date_plantation']}</td>
        <td>{p['plants_plantes']:,}</td><td>{p['plants_vivants']:,}</td>
        <td><span class="badge {'orange' if taux < 70 else ''}">{taux}%</span></td>
        <td><form method="post" action="/plantations/supprimer/{p['id']}"
        onsubmit="return confirm('Supprimer cet enregistrement ?')">
        <button class="delete" type="submit">Supprimer</button></form></td>
        </tr>
        """

    if not lignes:
        lignes = '<tr><td colspan="9" class="empty">Aucune donnée. Clique sur « Ajouter une plantation » pour commencer.</td></tr>'

    contenu = f"""
    <div class="section-head"><div><h1>Suivi des plantations</h1>
    <p style="color:#6b7c72">Enregistre les plantations et suis leur taux de survie.</p></div>
    <a class="btn" href="/plantations/ajouter">+ Ajouter une plantation</a></div>
    <div class="panel"><h3>Registre des plantations ({len(lignes_db)})</h3>
    <table><thead><tr><th>Projet</th><th>Village</th><th>Commune</th><th>Espèce</th>
    <th>Date</th><th>Plants plantés</th><th>Plants vivants</th><th>Survie</th><th>Action</th></tr></thead>
    <tbody>{lignes}</tbody></table></div>
    """
    return page("Plantations", contenu, "plantations")


@app.route("/plantations/ajouter", methods=["GET", "POST"])
def ajouter_plantation():
    if request.method == "POST":
        projet = request.form.get("projet", "").strip()
        village = request.form.get("village", "").strip()
        commune = request.form.get("commune", "").strip()
        espece = request.form.get("espece", "").strip()
        date_p = request.form.get("date_plantation", "").strip()
        observations = request.form.get("observations", "").strip()

        try:
            plantes = int(request.form.get("plants_plantes", ""))
            vivants = int(request.form.get("plants_vivants", ""))
            if not all([projet, village, commune, espece, date_p]):
                raise ValueError("Remplis tous les champs obligatoires.")
            if plantes < 1 or vivants < 0 or vivants > plantes:
                raise ValueError("Vérifie le nombre de plants : les plants vivants doivent être compris entre 0 et les plants plantés.")
        except ValueError as e:
            flash(str(e) if str(e) else "Saisis des nombres entiers valides.", "error")
            return redirect(url_for("ajouter_plantation"))

        with connexion() as db:
            db.execute("""
                INSERT INTO plantations
                (projet, village, commune, espece, date_plantation,
                 plants_plantes, plants_vivants, observations)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (projet, village, commune, espece, date_p,
                  plantes, vivants, observations))

        flash("Plantation enregistrée avec succès !")
        return redirect(url_for("plantations"))

    contenu = """
    <div class="section-head"><div><h1>Nouvelle plantation</h1>
    <p style="color:#6b7c72">Les champs marqués * sont obligatoires.</p></div>
    <a class="btn btn-light" href="/plantations">← Retour</a></div>
    <div class="panel">
    <form method="post" class="grid">
      <div class="field"><label>Nom du projet *</label><input name="projet" required placeholder="Ex. Reboisement communautaire"></div>
      <div class="field"><label>Espèce plantée *</label><input name="espece" required placeholder="Ex. Gmelina arborea"></div>
      <div class="field"><label>Village *</label><input name="village" required placeholder="Nom du village"></div>
      <div class="field"><label>Commune *</label><input name="commune" required placeholder="Ex. N'Dali"></div>
      <div class="field"><label>Date de plantation *</label><input type="date" name="date_plantation" required value="{{ date_du_jour }}"></div>
      <div class="field"><label>Nombre de plants mis en terre *</label><input type="number" name="plants_plantes" required min="1" step="1" placeholder="Ex. 1000"></div>
      <div class="field"><label>Nombre de plants vivants *</label><input type="number" name="plants_vivants" required min="0" step="1" placeholder="Ex. 850"></div>
      <div class="field full"><label>Observations</label><textarea name="observations" placeholder="État des plants, difficultés, remarques..."></textarea></div>
      <div class="field full"><button class="btn" type="submit">Enregistrer la plantation</button></div>
    </form></div>
    """
    contenu = render_template_string(contenu, date_du_jour=date.today().isoformat())
    return page("Ajouter une plantation", contenu, "plantations")


@app.route("/plantations/supprimer/<int:identifiant>", methods=["POST"])
def supprimer_plantation(identifiant):
    with connexion() as db:
        db.execute("DELETE FROM plantations WHERE id = ?", (identifiant,))
    flash("Enregistrement supprimé.")
    return redirect(url_for("plantations"))


# ---------------- AUTRES MODULES ----------------

@app.route("/projets", methods=["GET", "POST"])
def projets():
    if request.method == "POST":
        nom = request.form.get("nom", "").strip()
        zone = request.form.get("zone", "").strip()
        responsable = request.form.get("responsable", "").strip()
        debut = request.form.get("date_debut", "").strip()
        fin = request.form.get("date_fin", "").strip()
        statut = request.form.get("statut", "En cours")
        try:
            budget = float(request.form.get("budget", "0") or 0)
            if not nom or not zone or not debut or budget < 0:
                raise ValueError
        except ValueError:
            flash("Vérifie les champs obligatoires et le budget.", "error")
            return redirect(url_for("projets"))
        with connexion() as db:
            db.execute("""INSERT INTO projets
                (nom, zone, responsable, budget, date_debut, date_fin, statut)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (nom, zone, responsable, budget, debut, fin, statut))
        flash("Projet enregistré.")
        return redirect(url_for("projets"))

    with connexion() as db:
        donnees = db.execute("SELECT * FROM projets ORDER BY id DESC").fetchall()
    lignes = "".join(
        f"<tr><td>{p['nom']}</td><td>{p['zone']}</td><td>{p['responsable']}</td>"
        f"<td>{p['budget']:,.0f} FCFA</td><td>{p['date_debut']}</td>"
        f"<td><span class='badge'>{p['statut']}</span></td></tr>" for p in donnees
    ) or "<tr><td colspan='6' class='empty'>Aucun projet enregistré.</td></tr>"
    contenu = f"""
    <div class="section-head"><h1>Gestion des projets</h1></div>
    <div class="panel"><h3>Ajouter un projet</h3>
    <form method="post" class="grid">
    <div class="field"><label>Nom du projet *</label><input name="nom" required></div>
    <div class="field"><label>Zone d'intervention *</label><input name="zone" required></div>
    <div class="field"><label>Responsable</label><input name="responsable"></div>
    <div class="field"><label>Budget (FCFA)</label><input name="budget" type="number" min="0" step="1" value="0"></div>
    <div class="field"><label>Date de début *</label><input name="date_debut" type="date" required></div>
    <div class="field"><label>Date de fin</label><input name="date_fin" type="date"></div>
    <div class="field"><label>Statut</label><select name="statut"><option>En cours</option><option>Planifié</option><option>Terminé</option><option>Suspendu</option></select></div>
    <div class="field full"><button class="btn">Enregistrer le projet</button></div>
    </form></div>
    <div class="panel"><h3>Projets enregistrés ({len(donnees)})</h3>
    <table><thead><tr><th>Projet</th><th>Zone</th><th>Responsable</th><th>Budget</th><th>Début</th><th>Statut</th></tr></thead><tbody>{lignes}</tbody></table></div>
    """
    return page("Projets", contenu, "projets")


@app.route("/beneficiaires", methods=["GET", "POST"])
def beneficiaires():
    if request.method == "POST":
        nom = request.form.get("nom", "").strip()
        if not nom:
            flash("Le nom du bénéficiaire est obligatoire.", "error")
            return redirect(url_for("beneficiaires"))
        with connexion() as db:
            db.execute("""INSERT INTO beneficiaires
                (nom, sexe, village, commune, telephone, projet)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (nom, request.form.get("sexe", ""),
                 request.form.get("village", ""), request.form.get("commune", ""),
                 request.form.get("telephone", ""), request.form.get("projet", "")))
        flash("Bénéficiaire enregistré.")
        return redirect(url_for("beneficiaires"))

    with connexion() as db:
        donnees = db.execute("SELECT * FROM beneficiaires ORDER BY id DESC").fetchall()
    lignes = "".join(
        f"<tr><td>{b['nom']}</td><td>{b['sexe']}</td><td>{b['village']}</td>"
        f"<td>{b['commune']}</td><td>{b['telephone']}</td><td>{b['projet']}</td></tr>"
        for b in donnees
    ) or "<tr><td colspan='6' class='empty'>Aucun bénéficiaire enregistré.</td></tr>"
    contenu = f"""
    <div class="section-head"><h1>Gestion des bénéficiaires</h1></div>
    <div class="panel"><h3>Ajouter un bénéficiaire</h3><form method="post" class="grid">
    <div class="field"><label>Nom complet *</label><input name="nom" required></div>
    <div class="field"><label>Sexe</label><select name="sexe"><option value="">Non précisé</option><option>Femme</option><option>Homme</option><option>Autre / non précisé</option></select></div>
    <div class="field"><label>Village</label><input name="village"></div>
    <div class="field"><label>Commune</label><input name="commune"></div>
    <div class="field"><label>Téléphone</label><input name="telephone" type="tel"></div>
    <div class="field"><label>Projet</label><input name="projet"></div>
    <div class="field full"><button class="btn">Enregistrer le bénéficiaire</button></div>
    </form></div>
    <div class="panel"><h3>Liste des bénéficiaires ({len(donnees)})</h3>
    <table><thead><tr><th>Nom</th><th>Sexe</th><th>Village</th><th>Commune</th><th>Téléphone</th><th>Projet</th></tr></thead><tbody>{lignes}</tbody></table></div>
    """
    return page("Bénéficiaires", contenu, "beneficiaires")


@app.route("/activites", methods=["GET", "POST"])
def activites():
    if request.method == "POST":
        nom = request.form.get("nom", "").strip()
        dt = request.form.get("date_activite", "").strip()
        if not nom or not dt:
            flash("Le nom et la date de l'activité sont obligatoires.", "error")
            return redirect(url_for("activites"))
        with connexion() as db:
            db.execute("""INSERT INTO activites
                (nom, projet, zone, date_activite, responsable, statut, observations)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (nom, request.form.get("projet", ""), request.form.get("zone", ""),
                 dt, request.form.get("responsable", ""),
                 request.form.get("statut", "Planifiée"),
                 request.form.get("observations", "")))
        flash("Activité enregistrée.")
        return redirect(url_for("activites"))

    with connexion() as db:
        donnees = db.execute("SELECT * FROM activites ORDER BY id DESC").fetchall()
    lignes = "".join(
        f"<tr><td>{a['nom']}</td><td>{a['projet']}</td><td>{a['zone']}</td>"
        f"<td>{a['date_activite']}</td><td>{a['responsable']}</td>"
        f"<td><span class='badge'>{a['statut']}</span></td></tr>" for a in donnees
    ) or "<tr><td colspan='6' class='empty'>Aucune activité enregistrée.</td></tr>"
    contenu = f"""
    <div class="section-head"><h1>Suivi des activités</h1></div>
    <div class="panel"><h3>Planifier une activité</h3><form method="post" class="grid">
    <div class="field"><label>Nom de l'activité *</label><input name="nom" required></div>
    <div class="field"><label>Projet</label><input name="projet"></div>
    <div class="field"><label>Zone</label><input name="zone"></div>
    <div class="field"><label>Date *</label><input name="date_activite" type="date" required></div>
    <div class="field"><label>Responsable</label><input name="responsable"></div>
    <div class="field"><label>Statut</label><select name="statut"><option>Planifiée</option><option>En cours</option><option>Réalisée</option><option>Annulée</option></select></div>
    <div class="field full"><label>Observations</label><textarea name="observations"></textarea></div>
    <div class="field full"><button class="btn">Enregistrer l'activité</button></div>
    </form></div>
    <div class="panel"><h3>Activités ({len(donnees)})</h3>
    <table><thead><tr><th>Activité</th><th>Projet</th><th>Zone</th><th>Date</th><th>Responsable</th><th>Statut</th></tr></thead><tbody>{lignes}</tbody></table></div>
    """
    return page("Activités", contenu, "activites")


@app.route("/productions", methods=["GET", "POST"])
def productions():
    if request.method == "POST":
        culture = request.form.get("culture", "").strip()
        if not culture:
            flash("Le nom de la culture est obligatoire.", "error")
            return redirect(url_for("productions"))
        try:
            superficie = float(request.form.get("superficie", "0") or 0)
            rendement = float(request.form.get("rendement", "0") or 0)
            if superficie < 0 or rendement < 0:
                raise ValueError
        except ValueError:
            flash("La superficie et le rendement doivent être des nombres positifs.", "error")
            return redirect(url_for("productions"))
        with connexion() as db:
            db.execute("""INSERT INTO productions
                (projet, culture, village, superficie, rendement, campagne, observations)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (request.form.get("projet", ""), culture,
                 request.form.get("village", ""), superficie, rendement,
                 request.form.get("campagne", ""), request.form.get("observations", "")))
        flash("Donnée de production enregistrée.")
        return redirect(url_for("productions"))

    with connexion() as db:
        donnees = db.execute("SELECT * FROM productions ORDER BY id DESC").fetchall()
    lignes = "".join(
        f"<tr><td>{p['projet']}</td><td>{p['culture']}</td><td>{p['village']}</td>"
        f"<td>{p['superficie']:,.2f}</td><td>{p['rendement']:,.2f}</td>"
        f"<td>{p['campagne']}</td></tr>" for p in donnees
    ) or "<tr><td colspan='6' class='empty'>Aucune production enregistrée.</td></tr>"
    contenu = f"""
    <div class="section-head"><h1>Suivi des productions</h1></div>
    <div class="panel"><h3>Enregistrer une production</h3><form method="post" class="grid">
    <div class="field"><label>Culture *</label><input name="culture" required placeholder="Ex. Maïs"></div>
    <div class="field"><label>Projet</label><input name="projet"></div>
    <div class="field"><label>Village</label><input name="village"></div>
    <div class="field"><label>Campagne agricole</label><input name="campagne" placeholder="Ex. 2026-2027"></div>
    <div class="field"><label>Superficie (ha)</label><input type="number" min="0" step="0.01" name="superficie" value="0"></div>
    <div class="field"><label>Rendement (kg/ha)</label><input type="number" min="0" step="0.01" name="rendement" value="0"></div>
    <div class="field full"><label>Observations</label><textarea name="observations"></textarea></div>
    <div class="field full"><button class="btn">Enregistrer la production</button></div>
    </form></div>
    <div class="panel"><h3>Productions ({len(donnees)})</h3>
    <table><thead><tr><th>Projet</th><th>Culture</th><th>Village</th><th>Superficie (ha)</th><th>Rendement (kg/ha)</th><th>Campagne</th></tr></thead><tbody>{lignes}</tbody></table></div>
    """
    return page("Productions", contenu, "productions")


@app.route("/rapports")
def rapports():
    with connexion() as db:
        nbp = db.execute("SELECT COUNT(*) FROM plantations").fetchone()[0]
        tot = db.execute("SELECT COALESCE(SUM(plants_plantes),0) FROM plantations").fetchone()[0]
        viv = db.execute("SELECT COALESCE(SUM(plants_vivants),0) FROM plantations").fetchone()[0]
        projet = db.execute("SELECT COUNT(*) FROM projets").fetchone()[0]
        benef = db.execute("SELECT COUNT(*) FROM beneficiaires").fetchone()[0]
        act = db.execute("SELECT COUNT(*) FROM activites").fetchone()[0]
    survie = round(100*viv/tot, 1) if tot else 0
    contenu = f"""
    <div class="section-head"><h1>Rapport synthétique</h1>
    <button class="btn" onclick="window.print()">Imprimer / PDF</button></div>
    <div class="hero"><h1>État synthétique des données</h1>
    <p>Rapport généré le {date.today().strftime('%d/%m/%Y')} à partir des données actuellement enregistrées dans AGRODATA BÉNIN.</p></div>
    <div class="panel"><h3>Indicateurs clés</h3><table>
    <thead><tr><th>Indicateur</th><th>Valeur</th></tr></thead><tbody>
    <tr><td>Projets enregistrés</td><td>{projet}</td></tr>
    <tr><td>Sites de plantation enregistrés</td><td>{nbp}</td></tr>
    <tr><td>Plants mis en terre</td><td>{tot:,}</td></tr>
    <tr><td>Plants vivants</td><td>{viv:,}</td></tr>
    <tr><td>Taux global de survie</td><td>{survie}%</td></tr>
    <tr><td>Bénéficiaires enregistrés</td><td>{benef}</td></tr>
    <tr><td>Activités enregistrées</td><td>{act}</td></tr>
    </tbody></table></div>
    <p style="color:#6b7c72">Remarque : ces indicateurs dépendent des informations saisies. Vérifie les données avant toute utilisation officielle.</p>
    """
    return page("Rapports", contenu, "rapports")


# ---------------- LANCEMENT ----------------

initialiser_db()

if __name__ == "__main__":
    # Accessible sur ce PC uniquement pour le moment.
    # Ne pas publier directement ce serveur de développement sur Internet.
    app.run(host="127.0.0.1", port=5000, debug=False)

Parfait. J’ai maintenant le contenu de ton véritable app.py. Je peux donc comparer le projet actuel avec celui que nous voulons construire, au lieu de travailler sur des suppositions.

1. Ce que révèle ton code actuel

Ton application AGRODATA-BENIN possède déjà une base intéressante :

Python et Flask pour le fonctionnement du site ;
SQLite pour stocker les données ;
une interface responsive ;
des tableaux de bord, des formulaires et plusieurs modules de gestion.

Cependant, il manque les éléments fondamentaux de Pilo Étudiant :

Élément	Code actuel
Inscription des étudiants	Absente
Connexion individuelle	Absente
Protection des comptes	Absente
Budget personnel	Absent
Gestion des dépenses étudiantes	Absente
Objectifs d'épargne	Absents
Suivi des dépenses réelles	Absent
Séparation des données par étudiant	Absente

Le principal problème est que les données agricoles sont actuellement partagées dans les mêmes tables, sans compte utilisateur. Nous devons donc transformer l'application, et non simplement changer son nom.

2. J'ai préparé une nouvelle version

J'ai déjà produit un premier code Pilo Étudiant qui comprend notamment :

la création d'un compte et la connexion ;
des mots de passe hachés ;
un espace personnel pour chaque étudiant ;
les budgets et les dépenses prévisionnelles ;
les dépenses réellement effectuées et les entrées d'argent ;
les objectifs d'épargne et les réserves d'urgence ;
le calcul des soldes et les alertes ;
la modification du profil et du mot de passe.
Téléchargements

Projet complet :

📦 Télécharger Pilo Étudiant — archive ZIP

Fichiers individuels :

Code principal app.py
Dépendances requirements.txt
Guide d'installation README_PILO.md

Le code a passé une vérification de syntaxe Python. En revanche, les tests fonctionnels complets n'ont pas encore été exécutés : je ne peux donc pas garantir que toutes les fonctionnalités fonctionnent sans défaut.

3. Ce que je te recommande maintenant

Ne modifie pas encore le fichier app.py de ton dépôt public.

La prochaine étape est de vérifier et de tester le nouveau code, puis de préparer son déploiement sur Render. Il faudra notamment configurer une clé secrète et un stockage persistant pour éviter que les comptes et les budgets disparaissent lors d'un redéploiement.

Notre objectif reste une application complète, fiable et utilisable par plusieurs étudiants. Nous devons valider le fonctionnement réel avant de publier la nouvelle version.

app.py
Code
requirements.txt
Document
README_PILO.md
Document

app.py
999
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
35
36
37
38
39
40
41
42
43
44
45
46
47
48
49
50
51
52
53
54
55
56
57
58
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
