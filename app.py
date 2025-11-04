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
# GROQ API - CON DEBUG MEJORADO
# ================================
def preguntar_groq(pregunta, contexto_documentos):
    """Usa Groq con Llama 3 para respuestas inteligentes"""
    
    # DEBUG: Ver todas las variables de entorno
    todas_variables = dict(os.environ)
    variables_railway = {k: v for k, v in todas_variables.items() if 'GROQ' in k or 'API' in k}
    
    print("🔍 Variables de entorno relacionadas con API:", variables_railway)
    
    # Buscar la API key de diferentes maneras
    api_key = os.environ.get('GROQ_API_KEY')
    
    if not api_key:
        # Intentar alternativas
        api_key = os.environ.get('GROQAPIKEY')
    
    if not api_key:
        # Verificar si hay alguna variable que contenga 'GROQ'
        for key, value in todas_variables.items():
            if 'GROQ' in key.upper():
                api_key = value
                print(f"🔍 Encontrada API key en variable: {key}")
                break
    
    print(f"🔍 API Key encontrada: {'SÍ' if api_key else 'NO'}")
    if api_key:
        print(f"🔍 Longitud API key: {len(api_key)}")
        print(f"🔍 Empieza con: {api_key[:10]}...")
    
    if not api_key:
        return f"""❌ **Error de configuración**

No se encontró la API key de Groq. Por favor:

1. Ve a Railway → Settings → Variables
2. Agrega esta variable:
   **GROQ_API_KEY = gsk_tu_clave_real_aqui**

3. Asegúrate de que la clave sea correcta
4. Haz redeploy

Variables encontradas: {list(variables_railway.keys())}"""
    
    # Preparar contexto
    contexto = ""
    for doc_nombre, contenido in contexto_documentos.items():
        # Tomar contenido relevante
        lineas = contenido.split('\n')[:50]  # Primeras 50 líneas
        contexto += f"--- DOCUMENTO: {doc_nombre} ---\n" + '\n'.join(lineas) + "\n\n"
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""Eres un asistente especializado en documentos de Puntos Digitales.

DOCUMENTOS DISPONIBLES:
{contexto}

Responde basado en la información de arriba. Si no está en los documentos, di que no lo encuentras.

PREGUNTA: {pregunta}

RESPUESTA:"""
    
    data = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", "content": "Eres un asistente técnico preciso."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 1000
    }
    
    try:
        print("🔄 Enviando solicitud a Groq...")
        response = requests.post(url, json=data, headers=headers, timeout=30)
        print(f"📡 Respuesta de Groq: {response.status_code}")
        
        if response.status_code == 200:
            resultado = response.json()
            return resultado["choices"][0]["message"]["content"]
        elif response.status_code == 401:
            return "❌ Error: API Key inválida o expirada. Verifica tu clave en Groq."
        elif response.status_code == 429:
            return "❌ Error: Límite de uso excedido. Intenta en un momento."
        else:
            return f"❌ Error de API: {response.status_code} - {response.text}"
            
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
        
        # Respuesta rápida para debug
        if pregunta.lower() == 'debug':
            return jsonify({
                'success': True,
                'response': "🔧 Modo debug activado. Revisa los logs en Railway para ver las variables de entorno."
            })
        
        # Usar Groq
        respuesta = preguntar_groq(pregunta, documentos)
        return jsonify({'success': True, 'response': respuesta})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error: {str(e)}'})

# ================================
# INICIALIZACIÓN
# ================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 ChatBot con Groq iniciado en puerto {port}")
    # Debug de variables al iniciar
    groq_key = os.environ.get('GROQ_API_KEY')
    print(f"🔍 GROQ_API_KEY al iniciar: {'✅ Configurada' if groq_key else '❌ No configurada'}")
    if groq_key:
        print(f"🔍 Longitud: {len(groq_key)} caracteres")
    app.run(host='0.0.0.0', port=port, debug=False)