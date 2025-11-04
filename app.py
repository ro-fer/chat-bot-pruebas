from flask import Flask, request, jsonify, render_template, send_from_directory, Response
import os
import re
from docx import Document
import requests
import io

app = Flask(__name__)

# ================================
# CONFIGURACIÓN
# ================================
DOCUMENTS_DIR = "documents"

# ================================
# AUTENTICACIÓN PARA DOCUMENTACIÓN
# ================================
def check_auth(username, password):
    """Verifica credenciales básicas"""
    return username == os.environ.get('DOC_USER', 'admin') and password == os.environ.get('DOC_PASS', 'password123')

def authenticate():
    """Solicita autenticación básica"""
    return Response(
        'Acceso requerido', 401,
        {'WWW-Authenticate': 'Basic realm="Documentación Privada"'}
    )

@app.route('/documentos/<path:filename>')
def download_document(filename):
    """Descargar documentos con autenticación básica"""
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()
    
    return send_from_directory(DOCUMENTS_DIR, filename)

@app.route('/documentos/')
def list_documents():
    """Listar documentos disponibles"""
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()
    
    documentos = []
    for archivo in os.listdir(DOCUMENTS_DIR):
        if archivo.lower().endswith('.docx'):
            documentos.append(archivo)
    
    html = "<h1>📁 Documentos Disponibles</h1><ul>"
    for doc in documentos:
        html += f'<li><a href="/documentos/{doc}" download>{doc}</a></li>'
    html += "</ul><p><em>Usa Ctrl+Click para descargar</em></p>"
    
    return html

# ================================
# CARGA DESDE GITLAB PAGES
# ================================
def cargar_documentos_desde_gitlab():
    """Carga documentos desde GitLab Pages privado"""
    
    # URL base de tu GitLab Pages
    GITLAB_PAGES_URL = "https://documents-group1.gitlab.io/documentos-privados-chatbot"
    
    # Lista de tus documentos (usa los nombres exactos)
    documentos_nombres = [
        "Manual%20de%20Procedimientos%20de%20Punto%20Digital%20-%2000%20-%20%20%E2%80%9CGesti%C3%B3n%20de%20Puntos%20Digitales%E2%80%9D.docx",
        "Manual%20de%20Procedimientos%20de%20Punto%20Digital%20-%2001%20-%20%E2%80%9CGesti%C3%B3n%20de%20la%20demanda%20de%20Puntos%20Digitales%E2%80%9D.docx",
        "Manual%20de%20Procedimientos%20de%20Punto%20Digital%20-%2002%20-%20%20%E2%80%9CAn%C3%A1lisis%20de%20proyectos%20de%20Puntos%20Digitales%E2%80%9D.docx"
    ]
    
    documentos = {}
    
    for nombre_archivo in documentos_nombres:
        try:
            # Descargar desde GitLab Pages
            url = f"{GITLAB_PAGES_URL}/{nombre_archivo}"
            response = requests.get(url)
            
            if response.status_code == 200:
                # Procesar el DOCX desde memoria
                doc_file = io.BytesIO(response.content)
                doc = Document(doc_file)
                
                texto_completo = ""
                for paragraph in doc.paragraphs:
                    if paragraph.text.strip():
                        texto_completo += paragraph.text + "\n\n"
                
                # Usar nombre legible como clave
                nombre_legible = nombre_archivo.replace('%20', ' ').replace('%E2%80%9C', '"').replace('%E2%80%9D', '"').replace('%C3%B3n', 'ón').replace('%C3%A1lisis', 'álisis')
                documentos[nombre_legible] = texto_completo.strip()
                print(f"✅ Cargado: {nombre_legible}")
            else:
                print(f"❌ Error descargando {nombre_archivo}: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error procesando {nombre_archivo}: {str(e)}")
    
    return documentos

# ================================
# PROCESADOR DE DOCX
# ================================
def procesar_docx(ruta_archivo):
    """Extrae texto de archivos DOCX"""
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
    """Carga documentos desde GitLab Pages"""
    return cargar_documentos_desde_gitlab()

# ================================
# DETECCIÓN FLEXIBLE DE PREGUNTAS META
# ================================
def es_pregunta_meta(pregunta):
    """Detecta preguntas sobre el chatbot de forma flexible"""
    pregunta_limpia = pregunta.lower().strip()
    
    # Patrones flexibles para cada tipo de pregunta
    patrones = {
        'quien_eres': [
            r'quien eres', r'qué eres', r'que eres', r'quien sos', r'que sos',
            r'presentate', r'dime quien eres', r'explicate', r'identificate'
        ],
        'que_puedes': [
            r'qué puedes', r'que puedes', r'qué sabes', r'que sabes', 
            r'qué haces', r'que haces', r'para qué sirves', r'para que sirves',
            r'funciones', r'capacidades', r'qué ofreces', r'que ofreces'
        ],
        'que_preguntar': [
            r'qué preguntar', r'que preguntar', r'qué puedo preguntar', 
            r'que puedo preguntar', r'preguntas posibles', r'ejemplos de preguntas',
            r'qué preguntas', r'que preguntas', r'ayuda con preguntas'
        ],
        'documentos': [
            r'cuántos documentos', r'que documentos', r'qué documentos',
            r'documentos cargados', r'archivos tienes', r'qué archivos',
            r'listar documentos', r'mostrar archivos'
        ]
    }
    
    # Verificar cada categoría
    for categoria, patrones_lista in patrones.items():
        for patron in patrones_lista:
            if re.search(patron, pregunta_limpia):
                return categoria
    
    return None

def responder_pregunta_meta(tipo_pregunta, pregunta_original, documentos):
    """Responde preguntas sobre el chatbot"""
    documentos_lista = list(documentos.keys())
    
    if tipo_pregunta == 'quien_eres':
        return "🤖 **¡Hola! Soy tu asistente inteligente**\n\nPuedo leer y buscar información en tus documentos DOCX. Estoy aquí para ayudarte a encontrar rápidamente la información que necesitas en tus manuales y documentos."
    
    elif tipo_pregunta == 'que_puedes':
        return f"""🔍 **Puedo ayudarte a:**

• 🔎 **Buscar información** en tus documentos
• 📋 **Encontrar procedimientos** específicos  
• 💼 **Localizar datos técnicos** y normativas
• 🎯 **Explicar conceptos** del manual
• 📂 **Navegar por múltiples** documentos

📚 **Documentos cargados:** {len(documentos_lista)}
💡 **Tip:** Haz preguntas completas para mejores resultados

**Ejemplo:** En lugar de "licencia" pregunta "¿Cómo gestiono una licencia?"""
    
    elif tipo_pregunta == 'que_preguntar':
        ejemplos = [
            "¿Cómo ingreso al sistema?",
            "¿Qué es la firma digital y cómo funciona?",
            "¿Cómo gestiono una licencia en el sistema?",
            "¿Dónde encuentro soporte técnico?",
            "¿Qué son los datos personales y cómo se configuran?",
            "¿Cómo funciona el buzón grupal?",
            "¿Qué trámites puedo realizar?"
        ]
        ejemplos_texto = "\n".join([f"• {ej}" for ej in ejemplos])
        return f"""❓ **Puedes preguntarme sobre cualquier tema de tus documentos:**

{ejemplos_texto}

💡 **Consejos:**
• Preguntas completas → mejores respuestas
• Específico → más preciso
• Contexto → más relevante

📄 **Documento actual:** {documentos_lista[0] if documentos_lista else 'Ninguno'}"""
    
    elif tipo_pregunta == 'documentos':
        docs_texto = "\n".join([f"• {doc}" for doc in documentos_lista])
        return f"""📂 **Documentos cargados ({len(documentos_lista)}):**

{docs_texto}

🔍 **Puedo buscar en todos ellos simultáneamente.**"""
    
    else:
        return "🤖 Soy tu asistente para buscar información en documentos. ¿En qué puedo ayudarte?"

def buscar_en_documentos(pregunta, documentos):
    """Busca en documentos solo si NO es pregunta meta"""
    pregunta_limpia = pregunta.lower().strip()
    
    # 🚨 Una sola palabra = Sugerencia
    if len(pregunta_limpia.split()) <= 1:
        return f"❌ '{pregunta}' es muy general.\n\n💡 **Intenta con:** '¿Cómo funciona {pregunta}?' o '¿Qué es {pregunta}?'"
    
    palabras_clave = set(re.findall(r'\b[a-záéíóúñ]{3,}\b', pregunta_limpia))
    palabras_filtro = {
        'sobre', 'como', 'que', 'donde', 'puedo', 'preguntar', 'para', 'por', 'con',
        'sobre el', 'sobre la', 'sobre los', 'sobre las', 'acerca', 'acerca de'
    }
    palabras_clave = {p for p in palabras_clave if p not in palabras_filtro}
    
    if not palabras_clave:
        return "🤔 ¿Podrías ser más específico? Por ejemplo: '¿Cómo ingreso al sistema?' o '¿Qué son los datos personales?'"
    
    resultados = []
    
    for doc_nombre, contenido in documentos.items():
        parrafos = contenido.split('\n\n')
        
        for parrafo in parrafos:
            if len(parrafo.strip()) < 30:
                continue
                
            parrafo_lower = parrafo.lower()
            coincidencias = sum(1 for palabra in palabras_clave if palabra in parrafo_lower)
            
            if coincidencias > 0:
                if len(parrafo) > 400:
                    parrafo = parrafo[:400] + "..."
                
                resultados.append({
                    'documento': doc_nombre,
                    'contenido': parrafo.strip(),
                    'relevancia': coincidencias
                })
                break
    
    resultados.sort(key=lambda x: x['relevancia'], reverse=True)
    
    if resultados:
        respuesta = f"🔍 **Encontré esto sobre '{pregunta}':**\n\n"
        for i, resultado in enumerate(resultados[:2]):
            respuesta += f"📄 **{resultado['documento']}:**\n{resultado['contenido']}\n\n"
            if i < len(resultados) - 1:
                respuesta += "---\n\n"
        return respuesta
    else:
        sugerencias = [
            "Revisa la ortografía",
            "Intenta con sinónimos", 
            "Haz la pregunta más específica",
            "Pregunta de otra forma"
        ]
        sugerencias_texto = "\n".join([f"• {sug}" for sug in sugerencias])
        return f"🤔 No encontré información sobre '{pregunta}'.\n\n💡 **Sugerencias:**\n{sugerencias_texto}"

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
        
        # Cargar documentos desde GitLab
        documentos = cargar_documentos_docx()
        
        if not documentos:
            return jsonify({
                'success': True,
                'response': "📂 No se pudieron cargar los documentos desde GitLab."
            })
        
        # Respuestas rápidas
        pregunta_lower = pregunta.lower()
        
        if any(saludo in pregunta_lower for saludo in ['hola', 'buenos días', 'buenas tardes', 'buenas']):
            return jsonify({
                'success': True,
                'response': f"¡Hola! 👋 Soy tu asistente. Tengo {len(documentos)} documento(s) cargados. ¿En qué puedo ayudarte?"
            })
        
        if 'cómo estás' in pregunta_lower or 'que tal' in pregunta_lower:
            return jsonify({
                'success': True, 
                'response': "¡Perfecto! 😊 Listo para ayudarte a encontrar información en tus documentos."
            })
        
        if 'gracias' in pregunta_lower:
            return jsonify({
                'success': True,
                'response': "¡De nada! 😊 ¿Necesitas algo más?"
            })
        
        # 🎯 DETECCIÓN FLEXIBLE de preguntas meta
        tipo_meta = es_pregunta_meta(pregunta)
        if tipo_meta:
            respuesta = responder_pregunta_meta(tipo_meta, pregunta, documentos)
            return jsonify({'success': True, 'response': respuesta})
        
        # Si NO es pregunta meta, buscar en documentos
        respuesta = buscar_en_documentos(pregunta, documentos)
        return jsonify({'success': True, 'response': respuesta})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error: {str(e)}'})

# ================================
# INICIALIZACIÓN
# ================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 ChatBot con GitLab Pages iniciado en puerto {port}")
    print(f"📁 Documentos cargados desde: https://documents-group1.gitlab.io/documentos-privados-chatbot/")
    app.run(host='0.0.0.0', port=port, debug=False)