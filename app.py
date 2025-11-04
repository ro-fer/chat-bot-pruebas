from flask import Flask, request, jsonify, render_template, send_from_directory, Response
import os
import re
from docx import Document

app = Flask(__name__)

# ================================
# CONFIGURACIÓN
# ================================
DOCUMENTS_DIR = "documents"

# Variable para mantener contexto de conversación
ultima_busqueda = None

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
    """Carga todos los archivos DOCX de la carpeta local"""
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
# BÚSQUEDA INTELIGENTE MEJORADA
# ================================
def buscar_contenido_extendido(termino, documentos, lineas_extra=10):
    """Busca contenido más extenso alrededor de un término"""
    global ultima_busqueda
    
    for doc_nombre, contenido in documentos.items():
        lineas = contenido.split('\n')
        
        for i, linea in enumerate(lineas):
            if termino.lower() in linea.lower():
                # Tomar líneas antes y después para contexto
                inicio = max(0, i - 2)
                fin = min(len(lineas), i + lineas_extra)
                
                contenido_extendido = ""
                for j in range(inicio, fin):
                    if lineas[j].strip() and len(lineas[j].strip()) > 5:
                        contenido_extendido += lineas[j] + "\n"
                
                if contenido_extendido:
                    ultima_busqueda = termino
                    return f"📄 **{doc_nombre} - Información sobre {termino.title()}:**\n\n{contenido_extendido.strip()}"
    
    return None

def buscar_seccion_completa(concepto, documentos):
    """Busca secciones completas del documento"""
    global ultima_busqueda
    
    # Mapeo de sinónimos mejorado
    sinonimos = {
        'equipos': ['equipos', 'roles', 'equipo', 'funciones', 'responsabilidades', 'áreas'],
        'objetivo': ['objetivo', 'propósito', 'finalidad', 'meta'],
        'alcance': ['alcance', 'aplicación', 'ámbito', 'cubre'],
        'proceso': ['proceso', 'procedimiento', 'etapas', 'flujo', 'trabajo'],
        'stock': ['stock', 'inventario', 'equipamiento', 'materiales'],
        'soporte': ['soporte', 'técnico', 'tic', 'asistencia'],
        'imagen': ['imagen', 'cartelería', 'identidad'],
        'monitoreo': ['monitoreo', 'vinculación', 'seguimiento']
    }
    
    for doc_nombre, contenido in documentos.items():
        lineas = contenido.split('\n')
        
        # Buscar por título de sección
        for i, linea in enumerate(lineas):
            linea_limpia = linea.lower().strip()
            
            # Verificar todos los sinónimos para este concepto
            palabras_buscar = sinonimos.get(concepto, [concepto])
            
            for palabra in palabras_buscar:
                if palabra in linea_limpia and len(linea_limpia) < 100:  # Probablemente es un título
                    # Tomar contenido completo de la sección
                    contenido_seccion = ""
                    j = i + 1
                    while j < len(lineas) and (not lineas[j].strip() or 
                          (len(lineas[j].strip()) > 10 and not any(s in lineas[j].lower() for s in ['equipo', 'objetivo', 'alcance', 'proceso', 'roles', 'glosario']))):
                        if lineas[j].strip():
                            contenido_seccion += lineas[j] + "\n"
                        j += 1
                    
                    if contenido_seccion:
                        ultima_busqueda = concepto
                        return f"📄 **{doc_nombre} - {linea.strip()}:**\n\n{contenido_seccion.strip()}"
        
        # Búsqueda por contenido si no encontró título
        for palabra in sinonimos.get(concepto, [concepto]):
            if palabra in contenido.lower():
                # Buscar párrafos que contengan el término
                parrafos = contenido.split('\n\n')
                for parrafo in parrafos:
                    if palabra in parrafo.lower() and len(parrafo) > 30:
                        if len(parrafo) > 500:
                            parrafo = parrafo[:500] + "..."
                        ultima_busqueda = concepto
                        return f"📄 **{doc_nombre}:**\n{parrafo.strip()}"
    
    return None

def buscar_en_documentos(pregunta, documentos):
    """Busca en documentos de forma inteligente con contexto"""
    global ultima_busqueda
    
    pregunta_limpia = pregunta.lower().strip()
    
    # Detectar preguntas de seguimiento
    if any(palabra in pregunta_limpia for palabra in ['más', 'cuéntame más', 'amplía', 'detalla']):
        if ultima_busqueda:
            resultado = buscar_contenido_extendido(ultima_busqueda, documentos, 15)
            if resultado:
                return resultado
        return "🤔 No tengo contexto previo. ¿Sobre qué tema específico quieres que amplíe información?"
    
    # Mapeo de preguntas comunes a conceptos
    mapeo_preguntas = {
        'equipos': ['equipos', 'equipo', 'quienes trabajan', 'áreas', 'departamentos'],
        'roles': ['roles', 'funciones', 'responsabilidades', 'cargos'],
        'proceso': ['proceso', 'cómo funciona', 'etapas', 'flujo'],
        'stock': ['stock', 'inventario', 'equipamiento', 'materiales'],
        'soporte': ['soporte', 'técnico', 'tic', 'asistencia'],
        'objetivo': ['objetivo', 'para qué sirve', 'finalidad'],
        'alcance': ['alcance', 'a qué aplica', 'ámbito']
    }
    
    # Buscar coincidencia en preguntas comunes
    for concepto, preguntas in mapeo_preguntas.items():
        for pregunta_clave in preguntas:
            if pregunta_clave in pregunta_limpia:
                resultado = buscar_seccion_completa(concepto, documentos)
                if resultado:
                    return resultado
    
    # Búsqueda por palabras clave general
    palabras_clave = set(re.findall(r'\b[a-záéíóúñ]{3,}\b', pregunta_limpia))
    
    palabras_filtro = {
        'sobre', 'como', 'que', 'donde', 'puedo', 'preguntar', 'para', 'por', 
        'con', 'cual', 'cuáles', 'cuando', 'cómo', 'porque', 'tiene', 'tienen',
        'mas', 'más', 'información', 'cuéntame', 'amplia'
    }
    palabras_clave = {p for p in palabras_clave if p not in palabras_filtro}
    
    if palabras_clave:
        for palabra in palabras_clave:
            resultado = buscar_seccion_completa(palabra, documentos)
            if resultado:
                return resultado
    
    # Si no encuentra nada específico
    sugerencias = [
        "Pregunta sobre: 'equipos', 'roles', 'procesos', 'stock', 'soporte'",
        "Usa términos como: 'objetivo', 'alcance', 'funciones'", 
        "Ejemplos: '¿Qué equipos existen?', '¿Cómo funciona el proceso?'",
        "Pide más información: 'cuéntame más sobre stock'"
    ]
    sugerencias_texto = "\n".join([f"• {sug}" for sug in sugerencias])
    
    return f"🤔 No encontré información específica sobre '{pregunta}'.\n\n💡 **Sugerencias:**\n{sugerencias_texto}"

# ================================
# DETECCIÓN FLEXIBLE DE PREGUNTAS META
# ================================
def es_pregunta_meta(pregunta):
    """Detecta preguntas sobre el chatbot de forma flexible"""
    pregunta_limpia = pregunta.lower().strip()
    
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
            "¿Qué equipos o roles existen?",
            "¿Cuál es el objetivo del manual?",
            "¿Qué alcance tiene el documento?",
            "¿Cómo funciona el proceso de instalación?",
            "¿Qué hace el equipo de stock?",
            "¿Cómo funciona el soporte técnico?",
            "¿Qué es un Punto Digital?"
        ]
        ejemplos_texto = "\n".join([f"• {ej}" for ej in ejemplos])
        return f"""❓ **Puedes preguntarme sobre:**

{ejemplos_texto}

💡 **Consejos:**
• Pregunta por 'equipos', 'roles', 'procesos', 'stock'
• Usa 'cuéntame más' para ampliar información
• Sé específico para mejores resultados

📄 **Documentos disponibles:** {len(documentos_lista)}"""
    
    elif tipo_pregunta == 'documentos':
        docs_texto = "\n".join([f"• {doc}" for doc in documentos_lista])
        return f"""📂 **Documentos cargados ({len(documentos_lista)}):**

{docs_texto}

🔍 **Puedo buscar en todos ellos simultáneamente.**"""
    
    else:
        return "🤖 Soy tu asistente para buscar información en documentos. ¿En qué puedo ayudarte?"

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
        
        # Cargar documentos locales
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
    print(f"🚀 ChatBot con búsqueda inteligente iniciado en puerto {port}")
    print(f"📁 Ruta documentos: http://localhost:{port}/documentos/")
    app.run(host='0.0.0.0', port=port, debug=False)