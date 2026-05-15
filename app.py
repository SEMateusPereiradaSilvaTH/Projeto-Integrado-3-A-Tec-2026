from flask import Flask, render_template, request, redirect, url_for, session
import requests
import sqlite3
import hashlib
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

API_TOKEN = os.getenv("TMDB_API_TOKEN")
BASE_URL = "https://api.themoviedb.org/3"
IMG_BASE = "https://image.tmdb.org/t/p/w500"
HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "accept": "application/json"
}

# ─── Banco de dados ───────────────────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect("usuarios.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

init_db()

# ─── Login / Cadastro ─────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    erro = None
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        senha = request.form.get("senha", "").strip()

        conn = sqlite3.connect("usuarios.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE nome = ? AND senha = ?", (nome, hash_senha(senha)))
        usuario = cursor.fetchone()
        conn.close()

        if usuario:
            session["usuario"] = nome
            return redirect(url_for("index"))
        else:
            erro = "Usuário ou senha incorretos."

    return render_template("login.html", erro=erro)

@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    erro = None
    sucesso = None
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        senha = request.form.get("senha", "").strip()

        if not nome or not senha:
            erro = "Preencha todos os campos."
        else:
            try:
                conn = sqlite3.connect("usuarios.db")
                cursor = conn.cursor()
                cursor.execute("INSERT INTO usuarios (nome, senha) VALUES (?, ?)", (nome, hash_senha(senha)))
                conn.commit()
                conn.close()
                sucesso = "Conta criada! Faça login."
            except sqlite3.IntegrityError:
                erro = "Esse nome de usuário já existe."

    return render_template("cadastro.html", erro=erro, sucesso=sucesso)

@app.route("/logout")
def logout():
    session.pop("usuario", None)
    return redirect(url_for("index"))

# ─── Rotas principais ─────────────────────────────────────────────────────────

@app.route("/")
def index():
    page = request.args.get("page", 1, type=int)

    filmes_res = requests.get(f"{BASE_URL}/discover/movie", headers=HEADERS, params={
        "language": "pt-BR",
        "sort_by": "vote_average.desc",
        "vote_count.gte": 1000,
        "page": page
    })
    series_res = requests.get(f"{BASE_URL}/discover/tv", headers=HEADERS, params={
        "language": "pt-BR",
        "sort_by": "vote_average.desc",
        "vote_count.gte": 500,
        "page": page
    })

    filmes = filmes_res.json().get("results", [])
    series = series_res.json().get("results", [])

    for f in filmes:
        f["tipo"] = "filme"

    for s in series:
        s["title"] = s.get("name", "Sem título")
        s["release_date"] = s.get("first_air_date", "")
        s["tipo"] = "serie"

    resultados = [i for i in filmes + series if i.get("poster_path")]
    return render_template("index.html", filmes=resultados, img_base=IMG_BASE, page=page, base_url="/?")

@app.route("/buscar")
def buscar():
    query = request.args.get("q", "")
    page = request.args.get("page", 1, type=int)

    filmes_res = requests.get(f"{BASE_URL}/search/movie", headers=HEADERS, params={
        "query": query,
        "include_adult": False,
        "page": page
    })
    series_res = requests.get(f"{BASE_URL}/search/tv", headers=HEADERS, params={
        "query": query,
        "include_adult": False,
        "page": page
    })

    filmes = filmes_res.json().get("results", [])
    series = series_res.json().get("results", [])

    for f in filmes:
        f["tipo"] = "filme"

    for s in series:
        s["title"] = s.get("name", "Sem título")
        s["release_date"] = s.get("first_air_date", "")
        s["tipo"] = "serie"

    vistos = {}
    for item in filmes + series:
        chave = item["id"]
        if chave not in vistos:
            vistos[chave] = item
        else:
            if item.get("poster_path") and not vistos[chave].get("poster_path"):
                vistos[chave] = item

    resultados = [i for i in vistos.values() if i.get("poster_path")]
    return render_template("index.html", filmes=resultados, img_base=IMG_BASE, page=page, base_url=f"/buscar?q={query}&")

@app.route("/filme/<int:filme_id>")
def filme(filme_id):
    res = requests.get(f"{BASE_URL}/movie/{filme_id}", headers=HEADERS, params={"language": "pt-BR"})
    filme = res.json()
    filme["tipo"] = "filme"
    return render_template("filme.html", filme=filme, img_base=IMG_BASE, seasons=[])

@app.route("/serie/<int:serie_id>")
def serie(serie_id):
    res = requests.get(f"{BASE_URL}/tv/{serie_id}", headers=HEADERS, params={"language": "pt-BR"})
    serie = res.json()
    serie["title"] = serie.get("name", "Sem título")
    serie["release_date"] = serie.get("first_air_date", "")
    serie["runtime"] = serie.get("episode_run_time", [0])[0] if serie.get("episode_run_time") else None
    serie["tipo"] = "serie"

    seasons_data = []
    num_temporadas = serie.get("number_of_seasons", 0)
    for i in range(1, num_temporadas + 1):
        season_res = requests.get(f"{BASE_URL}/tv/{serie_id}/season/{i}", headers=HEADERS, params={"language": "pt-BR"})
        season = season_res.json()
        if season.get("episodes"):
            seasons_data.append(season)

    return render_template("filme.html", filme=serie, img_base=IMG_BASE, seasons=seasons_data)

@app.route("/sobre")
def sobre():
    return render_template("sobre.html")

@app.route("/genero/<int:genero_id>")
def genero(genero_id):
    page = request.args.get("page", 1, type=int)

    res = requests.get(f"{BASE_URL}/discover/movie", headers=HEADERS, params={
        "with_genres": genero_id,
        "language": "pt-BR",
        "sort_by": "popularity.desc",
        "page": page
    })
    filmes = res.json().get("results", [])
    for f in filmes:
        f["tipo"] = "filme"
    filmes = [f for f in filmes if f.get("poster_path")]
    return render_template("index.html", filmes=filmes, img_base=IMG_BASE, page=page, base_url=f"/genero/{genero_id}?")

@app.route("/ano/<int:ano>")
def por_ano(ano):
    page = request.args.get("page", 1, type=int)

    filmes_res = requests.get(f"{BASE_URL}/discover/movie", headers=HEADERS, params={
        "primary_release_year": ano,
        "language": "pt-BR",
        "sort_by": "popularity.desc",
        "page": page
    })
    series_res = requests.get(f"{BASE_URL}/discover/tv", headers=HEADERS, params={
        "first_air_date_year": ano,
        "language": "pt-BR",
        "sort_by": "popularity.desc",
        "page": page
    })

    filmes = filmes_res.json().get("results", [])
    series = series_res.json().get("results", [])

    for f in filmes:
        f["tipo"] = "filme"

    for s in series:
        s["title"] = s.get("name", "Sem título")
        s["release_date"] = s.get("first_air_date", "")
        s["tipo"] = "serie"

    resultados = [i for i in filmes + series if i.get("poster_path")]
    return render_template("index.html", filmes=resultados, img_base=IMG_BASE, page=page, base_url=f"/ano/{ano}?")

if __name__ == "__main__":
    app.run(debug=True)