from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import requests
from bs4 import BeautifulSoup
import random
import time
import re
from urllib.parse import urljoin, urlparse

app = Flask(__name__)
socketio = SocketIO(app)  # Habilitar WebSockets

keywords = ['accidente', 'incendio', 'lluvias', 'huayco', 'sequía', 'sismo', 'caída de bus', 'muertos', 'bloqueo']
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"
]

session = requests.Session()
titulos_vistos = set()
noticias_extraidas = []
PAGINACION_LIMIT = 10  # Número de noticias por página
noticias_globales = []

def cargar_sitios_web(archivo):
    sitios = []
    try:
        with open(archivo, 'r') as file:
            for line in file:
                url = line.strip()
                if url:
                    sitios.append(url)
    except FileNotFoundError:
        print(f"❌ El archivo {archivo} no fue encontrado.")
    return sitios

def extract_headlines(base_url):
    global noticias_extraidas
    try:
        headers = {"User-Agent": random.choice(user_agents)}
        response = session.get(base_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        links = soup.find_all('a')
        parsed_url = urlparse(base_url)
        clean_base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        for link in links:
            title = link.get_text().strip()
            href = link.get('href')

            if not title or title in titulos_vistos:
                continue

            if href:
                href = urljoin(clean_base_url, href.lstrip('/'))

            if any(keyword in title.lower() for keyword in keywords):
                noticia = {"titulo": title, "enlace": href}
                noticias_extraidas.append(noticia)
                titulos_vistos.add(title)
                socketio.emit('nueva_noticia', noticia)
                time.sleep(0.5)

    except requests.RequestException as e:
        print(f'❌ Error al acceder a {base_url}: {e}')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/noticias')
def get_noticias():
    page = int(request.args.get('page', 1))
    start = (page - 1) * PAGINACION_LIMIT
    end = start + PAGINACION_LIMIT
    return jsonify(noticias_extraidas[start:end])

@socketio.on('buscar_noticias')
def buscar_noticias(_):
    global titulos_vistos, noticias_globales
    titulos_vistos.clear()
    noticias_globales.clear()
    sitios = cargar_sitios_web('sitios.txt')

    total_sitios = len(sitios)  # ✅ Definir el total de sitios

    for index, sitio in enumerate(sitios):
        extract_headlines(sitio)
        progress = (index + 1) / total_sitios * 100
        socketio.emit('progreso', {"progreso": progress, "procesados": index + 1, "total": total_sitios})  # ✅ Enviar datos completos


if __name__ == '__main__':
    socketio.run(app, debug=True)
