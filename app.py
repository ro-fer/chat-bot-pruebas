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
def buscar_contenido_extendido(termino, documentos, lineas_extra=15):
    """Busca contenido más extenso alrededor de un término"""
    global ultima_busqueda
    
    for doc_nombre, contenido in documentos.items():
        lineas = contenido.split('\n')
        
        for i, linea in enumerate(lineas):
            if termino.lower() in linea.lower():
                # Tomar líneas antes y después para contexto
                inicio = max(0, i - 3)
                fin = min(len(lineas), i + lineas_extra)
                
                contenido_extendido = ""
                for j in range(inicio, fin):
                    if lineas[j].strip() and len(lineas[j].strip()) > 3:
                        contenido_extendido += lineas[j] + "\n"
                
                if contenido_extendido:
                    ultima_busqueda = termino
                    if len(contenido_extendido) > 2500:
                        contenido_extendido = contenido_extendido[:2500] + "\n\n... (contenido recortado)"
                    return f"📄 **{doc_nombre} - Información extendida sobre {termino.title()}:**\n\n{contenido_extendido.strip()}"
    
    return None

def buscar_seccion_completa(concepto, documentos):
    """Busca secciones completas del documento con TODO el contenido"""
    global ultima_busqueda
    
    # Mapeo de sinónimos mejorado
    sinonimos = {
        'equipos': ['equipos', 'roles', 'equipo', 'funciones', 'responsabilidades', 'áreas', 'departamentos'],
        'objetivo': ['objetivo', 'propósito', 'finalidad', 'meta'],
        'alcance': ['alcance', 'aplicación', 'ámbito', 'cubre'],
        'proceso': ['proceso', 'procedimiento', 'etapas', 'flujo', 'trabajo'],
        'stock': ['stock', 'inventario', 'equipamiento', 'materiales'],
        'soporte': ['soporte', 'técnico', 'tic', 'asistencia'],
        'imagen': ['imagen', 'cartelería', 'identidad'],
        'monitoreo': ['monitoreo', 'vinculación', 'seguimiento'],
        'roles': ['roles', 'funciones', 'responsabilidades', 'cargos', 'equipos', 'equipo']
    }
    
    for doc_nombre, contenido in documentos.items():
        lineas = contenido.split('\n')
        
        # BUSQUEDA ESPECÍFICA PARA ROLES - MOSTRAR TODO EL CONTENIDO
        if concepto in ['roles', 'equipos']:
            contenido_completo = f"📄 **{doc_nombre} - Todos los Roles y Equipos:**\n\n"
            contenido_encontrado = False
            
            # Buscar la sección "Roles / Funciones"
            for i, linea in enumerate(lineas):
                if 'roles / funciones' in linea.lower():
                    contenido_completo += f"**{linea.strip()}**\n\n"
                    j = i + 1
                    
                    # Tomar TODO el contenido hasta la próxima sección importante
                    while j < len(lineas):
                        linea_actual = lineas[j].strip()
                        
                        # Detener si encontramos nueva sección importante
                        if (linea_actual and 
                            any(seccion in linea_actual.lower() for seccion in 
                                ['objetivo', 'alcance', 'proceso', 'glosario', 'lineamientos', 'ciclos']) and
                            len(linea_actual) < 100):
                            break
                            
                        if linea_actual:
                            contenido_completo += linea_actual + "\n\n"
                        j += 1
                    
                    contenido_encontrado = True
                    break
            
            # Si no encontró "Roles / Funciones", buscar todos los equipos individualmente
            if not contenido_encontrado:
                equipos = [
                    'Dirección del Programa',
                    'Equipo de Proyectos',
                    'Equipo de Gestión de Stock', 
                    'Equipo de Soporte Técnico TIC',
                    'Equipo de Imagen',
                    'Equipo de Monitoreo y Vinculación'
                ]
                
                for equipo in equipos:
                    for i, linea in enumerate(lineas):
                        if equipo.lower() in linea.lower():
                            contenido_completo += f"**{linea.strip()}**\n\n"
                            # Tomar descripción del equipo
                            j = i + 1
                            lineas_tomadas = 0
                            while j < len(lineas) and lineas_tomadas < 10:
                                if lineas[j].strip() and len(lineas[j].strip()) > 10:
                                    contenido_completo += lineas[j] + "\n"
                                    lineas_tomadas += 1
                                j += 1
                            contenido_completo += "\n" + "═" * 60 + "\n\n"
                            contenido_encontrado = True
            
            if contenido_encontrado:
                ultima_busqueda = 'roles'
                if len(contenido_completo) > 4000:
                    contenido_completo = contenido_completo[:4000] + "\n\n... (contenido recortado - usa 'cuéntame más' para ver el resto)"
                return contenido_completo.strip()
        
        # Búsqueda normal para otros conceptos
        for i, linea in enumerate(lineas):
            linea_limpia = linea.lower().strip()
            
            # Verificar todos los sinónimos para este concepto
            palabras_buscar = sinonimos.get(concepto, [concepto])
            
            for palabra in palabras_buscar:
                if palabra in linea_limpia and len(linea_limpia) < 100:
                    # Tomar contenido COMPLETO de la sección
                    contenido_seccion = f"**{linea.strip()}**\n\n"
                    j = i + 1
                    
                    while j < len(lineas):
                        linea_actual = lineas[j].strip()
                        
                        # Detener si encontramos nueva sección
                        if (linea_actual and 
                            any(titulo in linea_actual.lower() for titulo in 
                                ['equipo', 'objetivo', 'alcance', 'proceso', 'roles', 'glosario', 'lineamientos', 'ciclos']) and
                            len(linea_actual) < 100 and j > i + 2):
                            break
                        
                        if linea_actual:
                            contenido_seccion += linea_actual + "\n\n"
                        j += 1
                    
                    if len(contenido_seccion.strip()) > len(linea.strip()):
                        ultima_busqueda = concepto
                        if len(contenido_seccion) > 3000:
                            contenido_seccion = contenido_seccion[:3000] + "\n\n... (contenido recortado)"
                        return f"📄 **{doc_nombre}:**\n\n{contenido_seccion.strip()}"
    
    return None
def buscar_en_documentos(pregunta, documentos):
    """Busca en documentos de forma inteligente con contexto"""
    global ultima_busqueda
    
    pregunta_limpia = pregunta.lower().strip()
    
    # Detectar preguntas de seguimiento
    if any(palabra in pregunta_limpia for palabra in ['más', 'cuéntame más', 'amplía', 'detalla', 'más información']):
        if ultima_busqueda:
            resultado = buscar_contenido_extendido(ultima_busqueda, documentos, 20)
            if resultado:
                return resultado
            else:
                return f"🤔 No tengo más información extensa sobre '{ultima_busqueda}'. ¿Quieres que busque algo específico?"
        return "🤔 No tengo contexto previo. ¿Sobre qué tema específico quieres que amplíe información?"
    
    # Mapeo de preguntas comunes a conceptos
    mapeo_preguntas = {
        'equipos': ['equipos', 'equipo', 'quienes trabajan', 'áreas', 'departamentos', 'quienes son'],
        'roles': ['roles', 'funciones', 'responsabilidades', 'cargos', 'que hace'],
        'proceso': ['proceso', 'cómo funciona', 'etapas', 'flujo', 'procedimiento'],
        'stock': ['stock', 'inventario', 'equipamiento', 'materiales'],
        'soporte': ['soporte', 'técnico', 'tic', 'asistencia', 'help desk'],
        'objetivo': ['objetivo', 'para qué sirve', 'finalidad', 'meta'],
        'alcance': ['alcance', 'a qué aplica', 'ámbito', 'cubre']
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
        'mas', 'más', 'información', 'cuéntame', 'amplia', 'dime', 'hablame'
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
        "Pide más información: 'cuéntame más sobre stock' después de una búsqueda"
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

def responder_pregunta_meta(tipo_meta, pregunta_original, documentos):
    """Responde preguntas sobre el chatbot"""
    documentos_lista = list(documentos.keys())
    
    if tipo_meta == 'quien_eres':
        return "🤖 **¡Hola! Soy tu asistente inteligente**\n\nPuedo leer y buscar información en tus documentos DOCX. Estoy aquí para ayudarte a encontrar rápidamente la información que necesitas en tus manuales y documentos."
    
    elif tipo_meta == 'que_puedes':
        return f"""🔍 **Puedo ayudarte a:**

• 🔎 **Buscar información** en tus documentos
• 📋 **Encontrar procedimientos** específicos  
• 💼 **Localizar datos técnicos** y normativas
• 🎯 **Explicar conceptos** del manual
• 📂 **Navegar por múltiples** documentos
• 💬 **Mantener contexto** de conversación

📚 **Documentos cargados:** {len(documentos_lista)}
💡 **Tip:** Usa 'cuéntame más' después de una búsqueda para ampliar información"""

    elif tipo_meta == 'que_preguntar':
        ejemplos = [
            "¿Qué equipos o roles existen?",
            "¿Cuál es el objetivo del manual?",
            "¿Qué alcance tiene el documento?",
            "¿Cómo funciona el proceso de instalación?",
            "¿Qué hace el equipo de stock?",
            "¿Cómo funciona el soporte técnico?",
            "Luego pregunta: 'cuéntame más' para ampliar"
        ]
        ejemplos_texto = "\n".join([f"• {ej}" for ej in ejemplos])
        return f"""❓ **Puedes preguntarme sobre:**

{ejemplos_texto}

💡 **Consejos:**
• Pregunta por 'equipos', 'roles', 'procesos', 'stock'
• Usa 'cuéntame más' para ampliar información
• Sé específico para mejores resultados

📄 **Documentos disponibles:** {len(documentos_lista)}"""
    
    elif tipo_meta == 'documentos':
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
    print(f"🚀 ChatBot con búsqueda mejorada iniciado en puerto {port}")
    print(f"📁 Ruta documentos: http://localhost:{port}/documentos/")
    app.run(host='0.0.0.0', port=port, debug=False)