from flask import Flask, render_template, jsonify
import requests
from bs4 import BeautifulSoup
import random
import time
import threading
from urllib.parse import urljoin, urlparse

app = Flask(__name__)

keywords = ['accidente', 'incendio', 'lluvias', 'huayco', 'sequía', 'sismo', 
            'caída de bus', 'muertos', 'bloqueo', 'huaico', 'quebradas', 
            'desborde', 'deslizamiento', 'derrumbe', 'inundación']

user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"
]

session = requests.Session()
titulos_vistos = set()
noticias_extraidas = []
sitios_web = []
sitios_procesados = 0
stop_event = threading.Event()  # Evento para detener el hilo

def cargar_sitios_web(archivo):
    """Carga la lista de sitios desde un archivo."""
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
    """Extrae titulares de una página y los almacena si cumplen con los criterios."""
    global noticias_extraidas, sitios_procesados
    if stop_event.is_set():
        return  

    try:
        headers = {"User-Agent": random.choice(user_agents)}
        response = session.get(base_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        links = soup.find_all('a')
        parsed_url = urlparse(base_url)
        clean_base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        for link in links:
            if stop_event.is_set():
                return  

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
                time.sleep(0.5)

        sitios_procesados += 1  

    except requests.RequestException as e:
        print(f'❌ Error al acceder a {base_url}: {e}')
        
@app.route('/reiniciar', methods=['POST'])
def reiniciar_extraccion():
    global noticias_extraidas, titulos_vistos, sitios_procesados, stop_event

    # Reiniciar variables
    noticias_extraidas = []
    titulos_vistos = set()
    sitios_procesados = 0

    # Detener cualquier proceso anterior si está en ejecución
    stop_event.set()
    time.sleep(1)  # Pequeña espera para asegurar que el hilo anterior se detenga completamente

    # Iniciar un nuevo proceso de extracción
    stop_event.clear()
    thread = threading.Thread(target=iniciar_extraccion, daemon=True)
    thread.start()

    return jsonify({"mensaje": "Extracción reiniciada desde 0"}), 200


def iniciar_extraccion():
    global sitios_web, sitios_procesados
    sitios_web = cargar_sitios_web('sitios.txt')
    sitios_procesados = 0  
    stop_event.clear()  

    for sitio in sitios_web:
        if stop_event.is_set():
            break  
        extract_headlines(sitio)

    sitios_procesados = len(sitios_web)  # Asegurar que llega al total
    print("✅ Extracción completada. El proceso ha finalizado.")
    stop_event.set()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/noticias')
def get_noticias():
    return jsonify(noticias_extraidas)

@app.route('/progreso')
def progreso():
    return jsonify({
        "procesados": sitios_procesados,
        "total": len(sitios_web)
    })

if __name__ == '__main__':
    # Iniciar el hilo de extracción antes de arrancar Flask
    thread = threading.Thread(target=iniciar_extraccion, daemon=True)
    thread.start()

    # Iniciar el servidor Flask
    app.run(debug=True)
