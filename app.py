from flask import Flask, request, jsonify, render_template, send_from_directory, Response
import os
from docx import Document
import requests
import logging

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
            logger.info(f"Procesando: {archivo}")
            texto = procesar_docx_completo(ruta_archivo)
            if texto and not texto.startswith("ERROR"):
                documentos[archivo] = texto
                logger.info(f"✅ Documento {archivo} cargado exitosamente")
            else:
                logger.error(f"❌ Error cargando {archivo}: {texto}")
    
    return documentos

# ================================
# GROQ - CORREGIDO (sin timeout en el JSON)
# ================================
def preguntar_groq(pregunta, documentos):
    api_key = os.environ.get('GROQ_API_KEY')
    
    # DEBUG: Verificar si la API key está presente
    logger.info(f"🔑 GROQ_API_KEY presente: {bool(api_key)}")
    if api_key:
        logger.info(f"🔑 Longitud de API key: {len(api_key)} caracteres")
        logger.info(f"🔑 API key comienza con: {api_key[:10]}...")
    
    if not api_key:
        error_msg = "❌ GROQ_API_KEY no encontrada en variables de entorno"
        logger.error(error_msg)
        return error_msg

    try:
        # Construir contexto
        contexto = "INFORMACIÓN DE PUNTOS DIGITALES:\n\n"
        total_caracteres = 0
        
        for doc_nombre, contenido in documentos.items():
            doc_contexto = f"--- DOCUMENTO: {doc_nombre} ---\n{contenido}\n\n"
            if total_caracteres + len(doc_contexto) > 15000:
                contexto += "[... Documento truncado por límites ...]\n\n"
                break
            contexto += doc_contexto
            total_caracteres += len(doc_contexto)
        
        logger.info(f"📚 Contexto preparado: {total_caracteres} caracteres")
        
        # System prompt mejorado
        system_prompt = """Eres un asistente especializado en Puntos Digitales. Responde en español usando HTML básico:
        - <br> para saltos de línea
        - <strong>texto</strong> para negritas
        - • para listas
        Base tus respuestas SOLO en la información proporcionada."""
        
        # Preparar request - CORREGIDO: sin 'timeout' en el JSON
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama3-8b-8192",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Contexto:\n{contexto}\n\nPregunta: {pregunta}\n\nRespuesta (usar HTML básico):"}
            ],
            "temperature": 0.1,
            "max_tokens": 1000
            # ⚠️ REMOVIDO: "timeout": 30 - Groq no soporta este parámetro
        }
        
        logger.info("🔄 Enviando solicitud a Groq API...")
        
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30  # ✅ Timeout solo aquí, en la llamada a requests
        )
        
        logger.info(f"📡 Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            respuesta = data["choices"][0]["message"]["content"]
            logger.info("✅ Respuesta recibida de Groq")
            
            # Asegurar formato HTML
            if '<br>' not in respuesta:
                respuesta = respuesta.replace('\n', '<br>')
                
            return respuesta
            
        else:
            error_msg = f"❌ Error Groq API: {response.status_code} - {response.text}"
            logger.error(error_msg)
            return error_msg
            
    except requests.exceptions.Timeout:
        error_msg = "⏰ Timeout: Groq no respondió en 30 segundos"
        logger.error(error_msg)
        return error_msg
        
    except requests.exceptions.ConnectionError:
        error_msg = "🔌 Error de conexión: No se pudo conectar con Groq"
        logger.error(error_msg)
        return error_msg
        
    except Exception as e:
        error_msg = f"❌ Error inesperado: {str(e)}"
        logger.error(error_msg)
        return error_msg

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
            return jsonify({'success': False, 'error': 'Por favor escribe una pregunta'})
        
        logger.info(f"💬 Pregunta recibida: {pregunta}")
        
        # Cargar documentos
        documentos = cargar_documentos_docx()
        logger.info(f"📄 Documentos cargados: {len(documentos)}")
        
        if not documentos:
            return jsonify({
                'success': True, 
                'response': "📂 No hay documentos DOCX en la carpeta 'documents'."
            })
        
        # Respuestas rápidas
        pregunta_lower = pregunta.lower()
        
        if any(s in pregunta_lower for s in ['hola', 'buenos días', 'buenas']):
            return jsonify({
                'success': True, 
                'response': f"¡Hola! 👋 Soy tu asistente de Puntos Digitales.<br><br>📚 Tengo {len(documentos)} documento(s) cargados.<br><br>¿En qué puedo ayudarte?"
            })
        
        if any(s in pregunta_lower for s in ['chao', 'adiós', 'bye']):
            return jsonify({
                'success': True, 
                'response': "¡Hasta luego! 👋"
            })
        
        # Mostrar documentos disponibles
        if any(p in pregunta_lower for p in ['documento', 'cargado', 'archivo', 'disponible', 'documentos']):
            docs = list(documentos.keys())
            doc_list = "<br>".join([f"• {d}" for d in docs])
            return jsonify({
                'success': True,
                'response': f"<strong>📂 Documentos cargados ({len(docs)}):</strong><br><br>{doc_list}"
            })
        
        # Usar Groq
        logger.info("🚀 Enviando pregunta a Groq...")
        respuesta = preguntar_groq(pregunta, documentos)
        
        return jsonify({'success': True, 'response': respuesta})
        
    except Exception as e:
        logger.error(f"💥 Error en endpoint /api/chat: {str(e)}")
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'})

# ================================
# INICIO
# ================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    # Verificar configuración crítica
    api_key = os.environ.get('GROQ_API_KEY')
    logger.info(f"🔑 GROQ_API_KEY configurada: {'✅ SÍ' if api_key else '❌ NO'}")
    
    documentos = cargar_documentos_docx()
    logger.info(f"📄 Documentos cargados: {len(documentos)}")
    
    for doc in documentos.keys():
        logger.info(f"   📝 {doc}")
    
    logger.info(f"🚀 Iniciando servidor en puerto {port}")
    app.run(host='0.0.0.0', port=port, debug=False)