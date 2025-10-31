from flask import Flask, request, jsonify, render_template
import requests
import fitz  # PyMuPDF para leer PDFs
import chromadb
from chromadb.utils import embedding_functions
import os

app = Flask(__name__)
OLLAMA_HOST = "http://localhost:11434"

# ================================
# Inicializar base de conocimiento
# ================================
chroma_client = chromadb.Client()
embedding_fn = embedding_functions.DefaultEmbeddingFunction()

# Crear o recuperar colección
try:
    collection = chroma_client.get_collection("documentacion_pdf")
except:
    collection = chroma_client.create_collection(
        name="documentacion_pdf", embedding_function=embedding_fn
    )

# ================================
# Función para leer PDF y cargarlo
# ================================
def cargar_pdf_a_chroma(ruta_pdf):
    if not os.path.exists(ruta_pdf):
        raise FileNotFoundError(f"No se encontró el PDF en {ruta_pdf}")

    doc = fitz.open(ruta_pdf)
    fragmentos = []
    for pagina in doc:
        texto = pagina.get_text("text")
        if texto.strip():
            fragmentos.append(texto.strip())
    doc.close()

    # Limpiar colección previa (si ya existía)
    try:
        ids_existentes = [doc_id for doc_id in collection.get()['ids']]
        if ids_existentes:
            collection.delete(ids_existentes)
    except Exception:
        pass

    # Agregar texto por páginas
    for i, texto in enumerate(fragmentos):
        collection.add(documents=[texto], ids=[f"pagina_{i+1}"])
    print(f"✅ PDF cargado: {len(fragmentos)} páginas indexadas.")

# Cargar el PDF automáticamente al iniciar
cargar_pdf_a_chroma("documentacion.pdf")

# ================================
# Funciones de generación de texto
# ================================
def generar_respuesta(prompt):
    payload = {
        "model": "llama3.1",
        "prompt": prompt,
        "stream": False
    }
    response = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload)
    try:
        return response.json().get("response", "")
    except Exception:
        return response.text

def consultar_documentacion(pregunta):
    resultados = collection.query(query_texts=[pregunta], n_results=3)
    documentos = resultados["documents"][0] if resultados["documents"] else []
    contexto = "\n\n".join(documentos)

    prompt = f"""
Eres un asistente experto en el uso del Sistema de Gestión Documental Digital (GDE).
Responde exclusivamente basándote en el siguiente Manual de Escritorio Único:

{contexto}

Pregunta: {pregunta}

Si la información no está en el manual, responde:
"No encontré información sobre eso en el Manual de Escritorio Único."
"""
    return generar_respuesta(prompt)

# ================================
# Rutas Flask
# ================================
@app.route('/')
def index():
    return render_template('chat.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    pregunta = data.get("prompt", "")
    if not pregunta.strip():
        return jsonify({"success": False, "error": "Prompt vacío"})

    try:
        respuesta = consultar_documentacion(pregunta)
        return jsonify({"success": True, "response": respuesta})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
