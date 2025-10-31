from flask import Flask, request, jsonify, render_template
import fitz  # PyMuPDF
import os
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import requests
import json

app = Flask(__name__)

# ================================
# Configuración - Modelo liviano
# ================================
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')  # Modelo pequeño

# Variables globales para el conocimiento
document_chunks = []
index = None

# ================================
# Cargar y procesar PDF
# ================================
def cargar_y_procesar_pdf(ruta_pdf="documentacion.pdf"):
    global document_chunks, index
    
    if not os.path.exists(ruta_pdf):
        print("⚠️ No se encontró documentacion.pdf, usando respuestas predefinidas")
        # Respuestas de emergencia basadas en GDE
        document_chunks = [
            "El Sistema GDE (Gestión Documental Electrónica) permite gestionar documentos digitales",
            "Para ingresar al GDE se utiliza credencial única en el portal oficial del estado",
            "El GDE gestiona expedientes digitales, documentos electrónicos y firma digital",
            "Los trámites documentales se realizan de forma digital en la plataforma GDE",
            "El manual de usuario del GDE contiene las instrucciones para usar el sistema",
            "La firma digital en GDE tiene validez legal según la normativa vigente"
        ]
    else:
        print("📖 Cargando documentación PDF...")
        doc = fitz.open(ruta_pdf)
        document_chunks = []
        
        for pagina_num in range(len(doc)):
            pagina = doc.load_page(pagina_num)
            texto = pagina.get_text()
            
            # Dividir en chunks más pequeños
            lineas = texto.split('\n')
            chunk = ""
            for linea in lineas:
                linea = linea.strip()
                if linea:
                    chunk += linea + " "
                    if len(chunk) > 200:  # Chunks de ~200 caracteres
                        document_chunks.append(chunk)
                        chunk = ""
            if chunk:
                document_chunks.append(chunk)
        
        doc.close()
        print(f"✅ PDF procesado: {len(document_chunks)} fragmentos")

    # Crear índice de búsqueda semántica
    if document_chunks:
        embeddings = model.encode(document_chunks)
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(np.array(embeddings).astype('float32'))
        print("🔍 Índice de búsqueda creado")

# ================================
# Búsqueda en documentación
# ================================
def buscar_en_documentacion(pregunta, n_resultados=3):
    if not document_chunks or index is None:
        return ["Información no disponible en este momento."]
    
    pregunta_embedding = model.encode([pregunta])
    distancias, indices = index.search(np.array(pregunta_embedding).astype('float32'), n_resultados)
    
    resultados = []
    for idx in indices[0]:
        if idx < len(document_chunks):
            resultados.append(document_chunks[idx])
    
    return resultados if resultados else ["No se encontró información relevante en la documentación."]

# ================================
# Generar respuesta
# ================================
def generar_respuesta(pregunta):
    # Buscar en documentación
    contexto = buscar_en_documentacion(pregunta)
    contexto_texto = "\n".join(contexto)
    
    # Si no hay mucha información específica, usar respuestas predefinidas
    respuestas_predefinidas = {
        "hola": "¡Hola! Soy tu asistente del Sistema GDE. ¿En qué puedo ayudarte?",
        "que es gde": "GDE es el Sistema de Gestión Documental Electrónica que permite gestionar documentos digitales del estado.",
        "como ingresar": "Para ingresar al GDE utiliza tu credencial única en el portal oficial del estado.",
        "manual": "Consulta el manual de usuario del GDE para instrucciones detalladas.",
        "tramite": "Los trámites documentales se realizan de forma digital en la plataforma GDE.",
        "firma digital": "La firma digital en GDE tiene validez legal según la normativa vigente."
    }
    
    # Buscar respuesta predefinida
    pregunta_lower = pregunta.lower()
    for key, respuesta in respuestas_predefinidas.items():
        if key in pregunta_lower:
            return f"{respuesta}\n\n📚 Información de apoyo:\n{contexto_texto}"
    
    # Respuesta generica con contexto
    return f"""Basándome en la documentación del GDE:

{contexto_texto}

¿Te sirve esta información o necesitas más detalles sobre algún aspecto específico?"""

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
        respuesta = generar_respuesta(pregunta)
        return jsonify({"success": True, "response": respuesta})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# ================================
# Inicialización
# ================================
print("🚀 Iniciando chatbot GDE...")
cargar_y_procesar_pdf()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)