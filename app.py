from flask import Flask, request, jsonify, render_template, send_from_directory, Response
import os
import re
from docx import Document
import requests

app = Flask(__name__)

# ================================
# CONFIGURACIÓN
# ================================
DOCUMENTS_DIR = "documents"

# ================================
# AUTENTICACIÓN PARA DOCUMENTACIÓN
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
def procesar_docx(ruta_archivo):
    try:
        doc = Document(ruta_archivo)
        texto_completo = ""
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                texto_completo += paragraph.text + "\n\n"
        return texto_completo.strip()
    except Exception as e:
        return f"❌ Error procesando DOCX: {str(e)}"

def cargar_documentos_docx():
    documentos = {}
    if not os.path.exists(DOCUMENTS_DIR):
        os.makedirs(DOCUMENTS_DIR)
        return documentos
    
    for archivo in os.listdir(DOCUMENTS_DIR):
        if archivo.lower().endswith('.docx'):
            ruta_archivo = os.path.join(DOCUMENTS_DIR, archivo)
            texto = procesar_docx(ruta_archivo)
            if texto and not texto.startswith("❌ Error"):
                documentos[archivo] = texto
    return documentos

# ================================
# GROQ API - LLaMA 3 (MEJORADO)
# ================================
def preguntar_groq(pregunta, contexto_documentos):
    """Usa Groq con Llama 3 para respuestas inteligentes"""
    
    api_key = os.environ.get('GROQ_API_KEY')
    
    if not api_key:
        return "❌ Error: No hay API key configurada. Por favor configura GROQ_API_KEY en Railway."
    
    # Preparar contexto de documentos (más inteligente)
    contexto = ""
    total_docs = len(contexto_documentos)
    
    for doc_nombre, contenido in contexto_documentos.items():
        # Tomar las partes más relevantes del documento
        lineas = contenido.split('\n')
        lineas_relevantes = []
        
        # Buscar secciones importantes
        for i, linea in enumerate(lineas):
            linea_limpia = linea.lower().strip()
            if any(keyword in linea_limpia for keyword in 
                  ['objetivo', 'alcance', 'proceso', 'roles', 'equipo', 'funciones', 'responsabilidad']):
                # Tomar esta línea y las siguientes 3
                for j in range(i, min(i+4, len(lineas))):
                    if lineas[j].strip():
                        lineas_relevantes.append(lineas[j])
        
        # Si no encontró secciones, tomar primeras líneas
        if not lineas_relevantes:
            lineas_relevantes = lineas[:20]
        
        contenido_breve = '\n'.join(lineas_relevantes[:30])  # Máximo 30 líneas
        contexto += f"--- DOCUMENTO: {doc_nombre} ---\n{contenido_breve}\n\n"
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""Eres un asistente especializado en documentos técnicos sobre procedimientos  de Puntos Digitales, programa que pertenece a la subsecretaria de Tecnologias de la informacion y las comunicaciones de Argentina.

INFORMACIÓN DE LOS DOCUMENTOS ({total_docs} documentos cargados):
{contexto}

INSTRUCCIONES IMPORTANTES:
1. Responde ÚNICAMENTE con información que esté en los documentos proporcionados
2. Si no encuentras la información, di claramente "No encuentro esta información específica en los documentos"
3. Para preguntas sobre los documentos mismos, responde basado en lo que sabes de ellos
4. Sé preciso, conciso y útil

PREGUNTA DEL USUARIO: {pregunta}

RESPUESTA:"""
    
    data = {
        "model": "llama3-8b-8192",
        "messages": [
            {
                "role": "system", 
                "content": "Eres un asistente técnico especializado en documentación de Puntos Digitales. Eres preciso, conciso y solo usas información verificada de los documentos."
            },
            {
                "role": "user", 
                "content": prompt
            }
        ],
        "temperature": 0.1,
        "max_tokens": 1500,
        "top_p": 0.9
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        if response.status_code == 200:
            resultado = response.json()
            return resultado["choices"][0]["message"]["content"]
        else:
            return f"❌ Error en Groq API: {response.status_code} - {response.text}"
    except Exception as e:
        return f"❌ Error de conexión: {str(e)}"

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
        
        # Cargar documentos
        documentos = cargar_documentos_docx()
        
        if not documentos:
            return jsonify({
                'success': True,
                'response': "📂 No hay archivos DOCX en la carpeta 'documents/'."
            })
        
        # Respuestas rápidas
        pregunta_lower = pregunta.lower()
        
        if any(saludo in pregunta_lower for saludo in ['hola', 'buenos días', 'buenas tardes', 'buenas']):
            return jsonify({
                'success': True,
                'response': f"¡Hola! 👋 Soy tu asistente con IA avanzada. Tengo {len(documentos)} documento(s) cargados. ¿En qué puedo ayudarte?"
            })
        
        # Usar Groq para procesar la pregunta
        respuesta = preguntar_groq(pregunta, documentos)
        return jsonify({'success': True, 'response': respuesta})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error: {str(e)}'})

# ================================
# INICIALIZACIÓN
# ================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 ChatBot con Groq + Llama 3 iniciado en puerto {port}")
    app.run(host='0.0.0.0', port=port, debug=False)