from flask import Flask, request, jsonify, render_template, send_from_directory, Response
import os
import re
from docx import Document
import requests

app = Flask(__name__)
DOCUMENTS_DIR = "documents"
#Prueba
# ================================
# CONFIGURACIÓN BÁSICA
# ================================
def check_auth(username, password):
    return username == os.environ.get('DOC_USER', 'admin') and password == os.environ.get('DOC_PASS', 'password123')

def authenticate():
    return Response('Acceso requerido', 401, {'WWW-Authenticate': 'Basic realm="Documentación Privada"'})

@app.route('/documentos/<path:filename>')
def download_document(filename):
    auth = request.authorizationfrom flask import Flask, request, jsonify, render_template, send_from_directory, Response
import os
import re
from docx import Document
import requests

app = Flask(__name__)
DOCUMENTS_DIR = "documents"
#Prueba
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
def procesar_docx(ruta_archivo):
    try:
        doc = Document(ruta_archivo)
        texto_completo = ""
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                texto_completo += paragraph.text + "\n\n"
        return texto_completo.strip()
    except Exception as e:
        return f"❌ Error: {str(e)}"

def cargar_documentos_docx():
    documentos = {}
    if not os.path.exists(DOCUMENTS_DIR):
        return documentos
    
    for archivo in os.listdir(DOCUMENTS_DIR):
        if archivo.lower().endswith('.docx'):
            ruta_archivo = os.path.join(DOCUMENTS_DIR, archivo)
            texto = procesar_docx(ruta_archivo)
            if texto and not texto.startswith("❌"):
                documentos[archivo] = texto
    return documentos

# ================================
# GROQ SIMPLIFICADO - SOLO LO ESENCIAL
# ================================
def usar_groq_simple(pregunta, documentos):
    """Versión SUPER simple de Groq"""
    
    api_key = os.environ.get('GROQ_API_KEY')
    print(f"🔍 API Key: {api_key[:10] if api_key else 'NO HAY'}...")
    
    if not api_key:
        return "⚠️ **Sistema en modo local** - Configura GROQ_API_KEY para respuestas con IA\n\n" + buscar_localmente(pregunta, documentos)
    
    # Preparar contexto simple
    contexto = ""
    for doc_nombre, contenido in documentos.items():
        contexto += f"Documento: {doc_nombre}\nContenido: {contenido[:1500]}\n\n"
    
    # Llamada SIMPLE a Groq
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama3-8b-8192",
                "messages": [
                    {"role": "system", "content": "Responde basado en los documentos. Sé conciso."},
                    {"role": "user", "content": f"Documentos:\n{contexto}\n\nPregunta: {pregunta}"}
                ],
                "temperature": 0.1,
                "max_tokens": 800
            },
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"❌ Error Groq: {response.status_code}\n\n" + buscar_localmente(pregunta, documentos)
            
    except Exception as e:
        return f"❌ Error conexión\n\n" + buscar_localmente(pregunta, documentos)

def buscar_localmente(pregunta, documentos):
    """Búsqueda local de emergencia"""
    pregunta_limpia = pregunta.lower()
    
    # Pregunta sobre documentos
    if any(p in pregunta_limpia for p in ['documento', 'cargado', 'archivo']):
        docs = list(documentos.keys())
        return f"📂 **Documentos ({len(docs)}):**\n" + "\n".join([f"• {d}" for d in docs])
    
    # Buscar en contenido
    for doc_nombre, contenido in documentos.items():
        if pregunta_limpia in contenido.lower():
            lineas = contenido.split('\n')
            for i, linea in enumerate(lineas):
                if pregunta_limpia in linea.lower():
                    return f"📄 **{doc_nombre}:**\n{linea}"
    
    return "🤔 No encontré información específica. Prueba con: 'documentos', 'equipos', 'objetivo'"

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
        
        documentos = cargar_documentos_docx()
        
        if not documentos:
            return jsonify({'success': True, 'response': "📂 No hay documentos cargados."})
        
        # Respuesta rápida
        if any(s in pregunta.lower() for s in ['hola', 'buenos días', 'buenas']):
            return jsonify({
                'success': True, 
                'response': f"¡Hola! 👋 Tengo {len(documentos)} documento(s). ¿En qué puedo ayudarte?"
            })
        
        # Usar Groq simple
        respuesta = usar_groq_simple(pregunta, documentos)
        return jsonify({'success': True, 'response': respuesta})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error: {str(e)}'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 ChatBot iniciado en puerto {port}")
    # Debug de API key
    api_key = os.environ.get('GROQ_API_KEY')
    print(f"🔍 GROQ_API_KEY: {'✅ CONFIGURADA' if api_key else '❌ FALTANTE'}")
    app.run(host='0.0.0.0', port=port, debug=False)
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
        return f"❌ Error: {str(e)}"

def cargar_documentos_docx():
    documentos = {}
    if not os.path.exists(DOCUMENTS_DIR):
        return documentos
    
    for archivo in os.listdir(DOCUMENTS_DIR):
        if archivo.lower().endswith('.docx'):
            ruta_archivo = os.path.join(DOCUMENTS_DIR, archivo)
            texto = procesar_docx(ruta_archivo)
            if texto and not texto.startswith("❌"):
                documentos[archivo] = texto
    return documentos

# ================================
# GROQ SIMPLIFICADO - SOLO LO ESENCIAL
# ================================
def usar_groq_simple(pregunta, documentos):
    """Versión MEJORADA de Groq - Contexto más pequeño"""
    
    api_key = os.environ.get('GROQ_API_KEY')
    
    if not api_key:
        return buscar_localmente(pregunta, documentos)
    
    # CONTEXTO MUCHO MÁS PEQUEÑO
    contexto = ""
    for doc_nombre, contenido in documentos.items():
        # Solo las primeras 20 líneas de cada documento
        lineas = contenido.split('\n')
        lineas_relevantes = []
        
        # Buscar líneas con información importante
        for linea in lineas[:30]:  # Solo primeras 30 líneas
            linea_limpia = linea.lower().strip()
            if any(keyword in linea_limpia for keyword in 
                  ['equipo', 'rol', 'objetivo', 'proceso', 'función', 'responsabilidad']):
                lineas_relevantes.append(linea)
        
        if lineas_relevantes:
            contexto += f"--- {doc_nombre} ---\n" + '\n'.join(lineas_relevantes[:10]) + "\n\n"
        else:
            # Si no encuentra keywords, tomar primeras líneas
            contexto += f"--- {doc_nombre} ---\n" + '\n'.join(lineas[:5]) + "\n\n"
    
    print(f"🔍 Contexto tamaño: {len(contexto)} caracteres")
    
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama3-8b-8192",
                "messages": [
                    {
                        "role": "system", 
                        "content": "Eres un asistente que responde SOBRE documentos técnicos. Responde en español de forma clara y concisa."
                    },
                    {
                        "role": "user", 
                        "content": f"INFORMACIÓN DE DOCUMENTOS:\n{contexto}\n\nPREGUNTA: {pregunta}\n\nRESPUESTA (solo basada en los documentos):"
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 500,
                "top_p": 0.9
            },
            timeout=15
        )
        
        print(f"📡 Status Groq: {response.status_code}")
        
        if response.status_code == 200:
            resultado = response.json()
            return resultado["choices"][0]["message"]["content"]
        else:
            error_msg = f"❌ Error Groq {response.status_code}"
            if response.status_code == 400:
                error_msg += " - Solicitud muy grande"
            elif response.status_code == 429:
                error_msg += " - Límite excedido"
            return error_msg + "\n\n" + buscar_localmente(pregunta, documentos)
            
    except Exception as e:
        return f"❌ Error: {str(e)}\n\n" + buscar_localmente(pregunta, documentos)

def buscar_localmente(pregunta, documentos):
    """Búsqueda local de emergencia"""
    pregunta_limpia = pregunta.lower()
    
    # Pregunta sobre documentos
    if any(p in pregunta_limpia for p in ['documento', 'cargado', 'archivo']):
        docs = list(documentos.keys())
        return f"📂 **Documentos ({len(docs)}):**\n" + "\n".join([f"• {d}" for d in docs])
    
    # Buscar en contenido
    for doc_nombre, contenido in documentos.items():
        if pregunta_limpia in contenido.lower():
            lineas = contenido.split('\n')
            for i, linea in enumerate(lineas):
                if pregunta_limpia in linea.lower():
                    return f"📄 **{doc_nombre}:**\n{linea}"
    
    return "🤔 No encontré información específica. Prueba con: 'documentos', 'equipos', 'objetivo'"

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
        
        documentos = cargar_documentos_docx()
        
        if not documentos:
            return jsonify({'success': True, 'response': "📂 No hay documentos cargados."})
        
        # Respuesta rápida
        if any(s in pregunta.lower() for s in ['hola', 'buenos días', 'buenas']):
            return jsonify({
                'success': True, 
                'response': f"¡Hola! 👋 Tengo {len(documentos)} documento(s). ¿En qué puedo ayudarte?"
            })
        
        # Usar Groq simple
        respuesta = usar_groq_simple(pregunta, documentos)
        return jsonify({'success': True, 'response': respuesta})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error: {str(e)}'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 ChatBot iniciado en puerto {port}")
    # Debug de API key
    api_key = os.environ.get('GROQ_API_KEY')
    print(f"🔍 GROQ_API_KEY: {'✅ CONFIGURADA' if api_key else '❌ FALTANTE'}")
    app.run(host='0.0.0.0', port=port, debug=False)