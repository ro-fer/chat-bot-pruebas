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
        return f"ERROR: {str(e)}"

def cargar_documentos_docx():
    documentos = {}
    if not os.path.exists(DOCUMENTS_DIR):
        return documentos
    
    for archivo in os.listdir(DOCUMENTS_DIR):
        if archivo.lower().endswith('.docx'):
            ruta_archivo = os.path.join(DOCUMENTS_DIR, archivo)
            texto = procesar_docx_completo(ruta_archivo)
            if texto and not texto.startswith("ERROR"):
                documentos[archivo] = texto
    return documentos

# ================================
# GROQ - ÚNICO MOTOR DE BÚSQUEDA
# ================================
def preguntar_groq(pregunta, documentos):
    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        return "❌ Error: No se configuró GROQ_API_KEY. Por favor configura tu API key en Railway."

    try:
        # Construir contexto con TODOS los documentos
        contexto = "INFORMACIÓN COMPLETA DE LOS DOCUMENTOS DE PUNTOS DIGITALES:\n\n"
        
        for doc_nombre, contenido in documentos.items():
            contexto += f"--- DOCUMENTO: {doc_nombre} ---\n{contenido}\n\n"
        
        # Limitar el contexto si es muy grande (Groq tiene límites)
        if len(contexto) > 20000:
            contexto = contexto[:20000] + "\n\n[Información truncada por límites de tamaño]"
        
        # System prompt optimizado para Puntos Digitales
        system_prompt = """
        Eres un asistente especializado en el Programa Puntos Digitales de Argentina. 
        Responde de forma CLARA, CONCISA y ESTRUCTURADA usando HTML básico.
        
        FORMATO DE RESPUESTA OBLIGATORIO:
        - Usa <br> para saltos de línea
        - Usa <strong>texto</strong> para negritas  
        - Usa • para listas con puntos
        - Sé específico y basate SOLO en la información proporcionada
        - Si la información no está en los documentos, dilo claramente
        
        ESTRUCTURA PREFERIDA:
        <strong>[EMOJI] TÍTULO DESCRIPTIVO</strong><br>
        <strong>📋 Información relevante:</strong><br>
        • Punto 1<br>
        • Punto 2<br>
        <strong>👥 Equipos involucrados:</strong><br>
        • Equipo - Función específica<br>
        <strong>🔗 Procedimientos relacionados:</strong><br>
        • Procedimiento X<br>
        """
        
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
                        "content": system_prompt
                    },
                    {
                        "role": "user", 
                        "content": f"CONTEXTO COMPLETO DE TODOS LOS DOCUMENTOS:\n{contexto}\n\nPREGUNTA DEL USUARIO: {pregunta}\n\nRESPONDE EN ESPAÑOL USANDO EXCLUSIVAMENTE EL FORMATO HTML INDICADO:"
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 1500
            },
            timeout=30
        )
        
        if response.status_code == 200:
            respuesta = response.json()["choices"][0]["message"]["content"]
            
            # Asegurar formato HTML básico
            if '<br>' not in respuesta:
                respuesta = respuesta.replace('\n', '<br>')
            
            return respuesta
        else:
            return f"❌ Error en la API de Groq: {response.status_code} - {response.text}"
            
    except requests.exceptions.Timeout:
        return "⏰ Timeout: La consulta tardó demasiado. Intenta nuevamente."
    except Exception as e:
        return f"❌ Error al conectar con Groq: {str(e)}"

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
                'response': "📂 No hay documentos cargados en la carpeta 'documents'.<br><br>Por favor carga los manuales de Puntos Digitales."
            })
        
        # Respuestas rápidas
        pregunta_lower = pregunta.lower()
        
        if any(s in pregunta_lower for s in ['hola', 'buenos días', 'buenas', 'hello', 'hi']):
            return jsonify({
                'success': True, 
                'response': f"¡Hola! 👋 Soy tu asistente especializado en Puntos Digitales.<br><br>📚 Tengo {len(documentos)} documento(s) cargados.<br><br>¿En qué puedo ayudarte?"
            })
        
        if any(s in pregunta_lower for s in ['chao', 'adiós', 'bye', 'nos vemos']):
            return jsonify({
                'success': True, 
                'response': "¡Hasta luego! 👋<br><br>Fue un gusto ayudarte."
            })
        
        if 'gracias' in pregunta_lower:
            return jsonify({
                'success': True, 
                'response': "¡De nada! 😊<br><br>¿Necesitas ayuda con algo más?"
            })
        
        # Mostrar documentos disponibles
        if any(p in pregunta_lower for p in ['documento', 'cargado', 'archivo', 'disponible', 'documentos']):
            docs = list(documentos.keys())
            doc_list = "<br>".join([f"• {d}" for d in docs])
            return jsonify({
                'success': True,
                'response': f"<strong>📂 Documentos cargados ({len(docs)}):</strong><br><br>{doc_list}"
            })
        
        # Usar Groq para todo el procesamiento
        print(f"🔍 Procesando pregunta: {pregunta}")
        respuesta = preguntar_groq(pregunta, documentos)
        return jsonify({'success': True, 'response': respuesta})
        
    except Exception as e:
        print(f"❌ Error en chat: {str(e)}")
        return jsonify({'success': False, 'error': f'Error interno: {str(e)}'})

# ================================
# INICIO DE LA APLICACIÓN
# ================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 ChatBot Punto Digital iniciado en puerto {port}")
    
    api_key = os.environ.get('GROQ_API_KEY')
    if api_key:
        print("✅ GROQ_API_KEY: CONFIGURADA - Usando IA para respuestas")
    else:
        print("❌ GROQ_API_KEY: NO CONFIGURADA - El chatbot no funcionará")
    
    documentos = cargar_documentos_docx()
    print(f"📄 Documentos cargados: {len(documentos)}")
    
    for doc in documentos.keys():
        print(f"   • {doc}")
    
    app.run(host='0.0.0.0', port=port, debug=False)