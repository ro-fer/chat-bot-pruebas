from flask import Flask, request, jsonify, render_template, send_from_directory, Response
import os
from docx import Document
import requests

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
def procesar_docx(ruta_archivo):
    try:
        doc = Document(ruta_archivo)
        texto_completo = ""
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                texto_completo += paragraph.text + "\n"
        return texto_completo.strip()
    except Exception as e:
        return ""

def cargar_documentos_docx():
    documentos = {}
    if not os.path.exists(DOCUMENTS_DIR):
        return documentos
    
    for archivo in os.listdir(DOCUMENTS_DIR):
        if archivo.lower().endswith('.docx'):
            ruta_archivo = os.path.join(DOCUMENTS_DIR, archivo)
            texto = procesar_docx(ruta_archivo)
            if texto:
                documentos[archivo] = texto
    return documentos

# ================================
# GROQ - VERSIÓN ESTABLE
# ================================
def preguntar_groq(pregunta, documentos):
    """Versión estable de Groq - Contexto controlado"""
    
    api_key = os.environ.get('GROQ_API_KEY')
    
    if not api_key:
        return "⚠️ **Modo local** - Usando búsqueda básica\n\n" + buscar_localmente(pregunta, documentos)
    
    # CONTEXTO MUY CONTROLADO
    contexto = "INFORMACIÓN DE DOCUMENTOS:\n"
    for doc_nombre, contenido in documentos.items():
        # Solo las primeras 15 líneas de cada documento
        lineas = contenido.split('\n')[:15]
        contexto += f"\n--- {doc_nombre} ---\n" + '\n'.join(lineas) + "\n"
    
    print(f"🔍 Enviando a Groq... Contexto: {len(contexto)} chars")
    
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
                        "content": "Eres un asistente especializado. Responde en español de forma clara y concisa basándote solo en los documentos proporcionados."
                    },
                    {
                        "role": "user", 
                        "content": f"{contexto}\n\nPREGUNTA: {pregunta}\n\nRESPUESTA:"
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 800
            },
            timeout=20
        )
        
        print(f"📡 Respuesta Groq: {response.status_code}")
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"❌ Error Groq {response.status_code}\n\n" + buscar_localmente(pregunta, documentos)
            
    except requests.exceptions.Timeout:
        return "⏰ Timeout - Groq no respondió\n\n" + buscar_localmente(pregunta, documentos)
    except Exception as e:
        return f"❌ Error: {str(e)}\n\n" + buscar_localmente(pregunta, documentos)

def buscar_localmente(pregunta, documentos):
    """Búsqueda local de respaldo"""
    pregunta_limpia = pregunta.lower()
    
    # Pregunta sobre documentos
    if any(p in pregunta_limpia for p in ['documento', 'cargado', 'archivo']):
        docs = list(documentos.keys())
        return f"📂 **Documentos cargados ({len(docs)}):**\n" + "\n".join([f"• {d}" for d in docs])
    
    # Buscar contenido específico
    for doc_nombre, contenido in documentos.items():
        contenido_lower = contenido.lower()
        
        if 'equipo' in pregunta_limpia or 'rol' in pregunta_limpia:
            if 'equipo' in contenido_lower or 'rol' in contenido_lower:
                lineas = contenido.split('\n')
                resultado = f"📄 **{doc_nombre} - Equipos/Roles:**\n\n"
                for linea in lineas:
                    if any(palabra in linea.lower() for palabra in ['equipo', 'rol', 'dirección', 'proyectos', 'stock', 'soporte']):
                        resultado += f"{linea}\n"
                return resultado
    
    return "🤔 No encontré información específica. Prueba con: 'documentos', 'equipos', 'roles'"

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
        
        documentos = cargar_documentos_docx()
        
        if not documentos:
            return jsonify({'success': True, 'response': "📂 No hay documentos cargados."})
        
        # Respuesta rápida para saludo
        if any(s in pregunta.lower() for s in ['hola', 'buenos días', 'buenas']):
            return jsonify({
                'success': True, 
                'response': f"¡Hola! 👋 Soy tu asistente con IA. Tengo {len(documentos)} documento(s) cargados. ¿En qué puedo ayudarte?"
            })
        
        # Usar Groq
        respuesta = preguntar_groq(pregunta, documentos)
        return jsonify({'success': True, 'response': respuesta})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error: {str(e)}'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 ChatBot con Groq iniciado en puerto {port}")
    api_key = os.environ.get('GROQ_API_KEY')
    print(f"🔍 GROQ_API_KEY: {'✅ CONFIGURADA' if api_key else '❌ FALTANTE'}")
    app.run(host='0.0.0.0', port=port, debug=False)