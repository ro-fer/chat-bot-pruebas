from flask import Flask, request, jsonify, render_template, send_from_directory, Response
import os
from docx import Document
import requests
import logging
import time

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
DOCUMENTS_DIR = "documents"

# ================================
# CONFIGURACIÓN BÁSICA
# ================================
def check_auth(username, password):
    return username == os.environ.get('DOC_USER', 'admin') and password == os.environ.get('DOC_PASS', 'password123')

def authenticate():
    return Response('Acceso requerido', 401, {'WWW-Authenticate': 'Basic realm="Documentación Privada"'})

@app.route('/documentos/<path:filename>')
def download_document(filename):
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()
    return send_from_directory(DOCUMENTS_DIR, filename)

@app.route('/documentos/')
def list_documents():
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()
    
    documentos = [archivo for archivo in os.listdir(DOCUMENTS_DIR) if archivo.lower().endswith('.docx')]
    html = "<h1>📁 Documentos Disponibles</h1><ul>"
    for doc in documentos:
        html += f'<li><a href="/documentos/{doc}" download>{doc}</a></li>'
    html += "</ul><p><em>Usa Ctrl+Click para descargar</em></p>"
    return html

# ================================
# PROCESADOR DE DOCX
# ================================
def procesar_docx_completo(ruta_archivo):
    """Procesa TODO el contenido del DOCX incluyendo tablas"""
    try:
        doc = Document(ruta_archivo)
        texto_completo = ""
        
        # Procesar párrafos
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                texto_completo += paragraph.text + "\n"
        
        # Procesar tablas
        for table in doc.tables:
            for row in table.rows:
                fila_texto = []
                for cell in row.cells:
                    if cell.text.strip():
                        fila_texto.append(cell.text.strip())
                if fila_texto:
                    texto_completo += " | ".join(fila_texto) + "\n"
        
        return texto_completo.strip()
    except Exception as e:
        logger.error(f"Error procesando DOCX {ruta_archivo}: {str(e)}")
        return f"ERROR: {str(e)}"

def cargar_documentos_docx():
    documentos = {}
    if not os.path.exists(DOCUMENTS_DIR):
        logger.warning(f"Directorio {DOCUMENTS_DIR} no existe")
        return documentos
    
    archivos = os.listdir(DOCUMENTS_DIR)
    logger.info(f"Archivos en directorio: {archivos}")
    
    for archivo in archivos:
        if archivo.lower().endswith('.docx'):
            ruta_archivo = os.path.join(DOCUMENTS_DIR, archivo)
            texto = procesar_docx_completo(ruta_archivo)
            if texto and not texto.startswith("ERROR"):
                documentos[archivo] = texto
                logger.info(f"✅ Documento {archivo} cargado")
    
    return documentos

# ================================
# GROQ - OPTIMIZADO
# ================================
def preguntar_groq(pregunta, documentos):
    api_key = os.environ.get('GROQ_API_KEY')
    
    if not api_key:
        return "❌ Error de configuración del servicio."

    try:
        # Contexto más eficiente
        contexto = "DOCUMENTOS PUNTOS DIGITALES:\n\n"
        
        for doc_nombre, contenido in documentos.items():
            # Tomar solo partes relevantes del documento
            lineas = contenido.split('\n')[:30]  # Máximo 30 líneas
            contexto += f"--- {doc_nombre} ---\n" + "\n".join(lineas) + "\n\n"
            if len(contexto) > 10000:  # Límite total
                break
        
        # System prompt conciso
        system_prompt = "Asistente de Puntos Digitales. Responde en español con HTML: <br> <strong>texto</strong> • listas. Sé conciso."
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{contexto}\n\nPregunta: {pregunta}\nRespuesta HTML:"}
            ],
            "temperature": 0.1,
            "max_tokens": 600
        }
        
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            respuesta = data["choices"][0]["message"]["content"]
            
            # Formato HTML
            if '<br>' not in respuesta:
                respuesta = respuesta.replace('\n', '<br>')
                
            return respuesta
            
        elif response.status_code == 429:
            return "⏳ <strong>Servicio ocupado</strong><br>Espera unos segundos y vuelve a intentar."
            
        else:
            return "🔧 <strong>Servicio temporalmente no disponible</strong><br>Intenta nuevamente en un momento."
            
    except Exception as e:
        logger.error(f"Error Groq: {str(e)}")
        return "❌ Error temporal del servicio."

# ================================
# RUTAS PRINCIPALES
# ================================
@app.route('/')
def home():
    return render_template('chat.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        pregunta = data.get('prompt', '').strip()
        
        if not pregunta:
            return jsonify({'success': False, 'error': 'Escribe una pregunta'})
        
        # Cargar documentos
        documentos = cargar_documentos_docx()
        
        if not documentos:
            return jsonify({
                'success': True, 
                'response': "📂 No hay documentos en la carpeta 'documents'."
            })
        
        # Respuestas rápidas
        pregunta_lower = pregunta.lower()
        
        if any(s in pregunta_lower for s in ['hola', 'buenos días', 'buenas']):
            return jsonify({
                'success': True, 
                'response': f"¡Hola! 👋 Asistente de Puntos Digitales<br><br>📚 Documentos: {len(documentos)}<br>¿En qué puedo ayudarte?"
            })
        
        if any(s in pregunta_lower for s in ['chao', 'adiós', 'bye']):
            return jsonify({'success': True, 'response': "¡Hasta luego! 👋"})
        
        # Mostrar documentos
        if any(p in pregunta_lower for p in ['documento', 'archivo', 'disponible']):
            docs = list(documentos.keys())
            doc_list = "<br>".join([f"• {d}" for d in docs])
            return jsonify({
                'success': True,
                'response': f"<strong>📂 Documentos ({len(docs)}):</strong><br>{doc_list}"
            })
        
        # Usar Groq
        respuesta = preguntar_groq(pregunta, documentos)
        return jsonify({'success': True, 'response': respuesta})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error: {str(e)}'})

# ================================
# INICIO
# ================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    documentos = cargar_documentos_docx()
    print(f"🚀 ChatBot Puntos Digitales - {len(documentos)} documentos")
    app.run(host='0.0.0.0', port=port, debug=False)