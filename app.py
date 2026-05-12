from flask import Flask, render_template, request
import requests

app = Flask(__name__)

API_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJhMjYwMmZjMmNmZmJmOTQ0ZjJiNzU0ZDZlNmQxZWE1MSIsIm5iZiI6MTc3NzQ5MDk3OS4wNTMsInN1YiI6IjY5ZjI1YzIzNzk0MGEzOGY0MDdiZWViNiIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.qr16rcpUhfh4-ZV2J1NxdNWFV-bn8vl1IWMVUsg8lsY"
BASE_URL = "https://api.themoviedb.org/3"
IMG_BASE = "https://image.tmdb.org/t/p/w500"
HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "accept": "application/json"
}

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

    # busca episódios de cada temporada (ignora temporada 0 = especiais)
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