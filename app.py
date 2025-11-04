from flask import Flask, request, jsonify, render_template, send_from_directory, Response
import os
import re
from docx import Document

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
# BÚSQUEDA MEJORADA
# ================================
def buscar_seccion_especifica(concepto, documentos):
    """Busca secciones específicas del documento"""
    for doc_nombre, contenido in documentos.items():
        lineas = contenido.split('\n')
        
        for i, linea in enumerate(lineas):
            linea_lower = linea.lower()
            
            if concepto == 'objetivo' and ('objetivo' in linea_lower or 'propósito' in linea_lower):
                # Tomar las siguientes 3-5 líneas después del título "Objetivo"
                contenido_objetivo = ""
                for j in range(i, min(i+6, len(lineas))):
                    if lineas[j].strip() and len(lineas[j].strip()) > 10:
                        contenido_objetivo += lineas[j] + "\n"
                if contenido_objetivo:
                    return f"📄 **{doc_nombre} - Objetivo:**\n{contenido_objetivo.strip()}"
            
            elif concepto == 'alcance' and 'alcance' in linea_lower:
                contenido_alcance = ""
                for j in range(i, min(i+6, len(lineas))):
                    if lineas[j].strip() and len(lineas[j].strip()) > 10:
                        contenido_alcance += lineas[j] + "\n"
                if contenido_alcance:
                    return f"📄 **{doc_nombre} - Alcance:**\n{contenido_alcance.strip()}"
            
            elif concepto == 'proceso' and ('proceso' in linea_lower or 'procedimiento' in linea_lower):
                contenido_proceso = ""
                for j in range(i, min(i+8, len(lineas))):
                    if lineas[j].strip() and len(lineas[j].strip()) > 10:
                        contenido_proceso += lineas[j] + "\n"
                if contenido_proceso:
                    return f"📄 **{doc_nombre} - Proceso:**\n{contenido_proceso.strip()}"
        
        # Si no encontró sección específica, buscar cualquier mención
        if concepto in contenido.lower():
            # Encontrar párrafo que contenga el concepto
            parrafos = contenido.split('\n\n')
            for parrafo in parrafos:
                if concepto in parrafo.lower() and len(parrafo) > 50:
                    if len(parrafo) > 300:
                        parrafo = parrafo[:300] + "..."
                    return f"📄 **{doc_nombre}:**\n{parrafo.strip()}"
    
    return f"🤔 No encontré información específica sobre {concepto} en los documentos."

def buscar_en_documentos(pregunta, documentos):
    """Busca en documentos de forma más inteligente y precisa"""
    pregunta_limpia = pregunta.lower().strip()
    
    # Detectar preguntas específicas sobre conceptos clave
    conceptos_especificos = {
        'objetivo': ['objetivo', 'propósito', 'finalidad', 'meta'],
        'alcance': ['alcance', 'aplicación', 'ámbito', 'cubre'],
        'proceso': ['proceso', 'procedimiento', 'etapas', 'flujo'],
        'roles': ['roles', 'funciones', 'responsabilidades', 'equipo'],
        'glosario': ['glosario', 'definiciones', 'términos', 'conceptos']
    }
    
    # Verificar si es pregunta sobre concepto específico
    for concepto, palabras_clave in conceptos_especificos.items():
        for palabra in palabras_clave:
            if palabra in pregunta_limpia:
                # Buscar secciones específicas
                return buscar_seccion_especifica(concepto, documentos)
    
    # Búsqueda general mejorada
    palabras_clave = set(re.findall(r'\b[a-záéíóúñ]{4,}\b', pregunta_limpia))
    
    palabras_filtro = {
        'sobre', 'como', 'que', 'donde', 'puedo', 'preguntar', 'para', 'por', 
        'con', 'cual', 'cuáles', 'cuando', 'cómo', 'porque', 'tiene', 'tienen'
    }
    palabras_clave = {p for p in palabras_clave if p not in palabras_filtro}
    
    if not palabras_clave:
        return "🤔 ¿Podrías ser más específico? Por ejemplo: '¿Cuál es el objetivo del manual?' o '¿Qué roles existen?'"
    
    resultados = []
    
    for doc_nombre, contenido in documentos.items():
        # Buscar en secciones específicas primero
        secciones = contenido.split('\n\n')
        
        for i, seccion in enumerate(secciones):
            if len(seccion.strip()) < 30:
                continue
                
            seccion_lower = seccion.lower()
            
            # Calcular relevancia
            relevancia = 0
            for palabra in palabras_clave:
                if palabra in seccion_lower:
                    # Más peso si la palabra está en título o inicio
                    if seccion_lower.startswith(palabra) or any(titulo in seccion_lower for titulo in ['objetivo', 'alcance', 'proceso', 'roles']):
                        relevancia += 3
                    else:
                        relevancia += 1
            
            if relevancia > 0:
                # Encontrar la línea más relevante
                lineas = seccion.split('\n')
                for linea in lineas:
                    if any(palabra in linea.lower() for palabra in palabras_clave):
                        contenido_resumen = linea.strip()
                        break
                else:
                    contenido_resumen = seccion.strip()
                
                if len(contenido_resumen) > 300:
                    contenido_resumen = contenido_resumen[:300] + "..."
                
                resultados.append({
                    'documento': doc_nombre,
                    'contenido': contenido_resumen,
                    'relevancia': relevancia
                })
                break  # Solo un resultado por documento
    
    # Ordenar y mostrar resultados
    resultados.sort(key=lambda x: x['relevancia'], reverse=True)
    
    if resultados:
        respuesta = f"🔍 **Encontré esto sobre '{pregunta}':**\n\n"
        for resultado in resultados[:2]:  # Máximo 2 resultados
            respuesta += f"📄 **{resultado['documento']}:**\n{resultado['contenido']}\n\n"
        return respuesta
    else:
        return f"🤔 No encontré información específica sobre '{pregunta}'.\n\n💡 **Sugerencia:** Intenta con términos más específicos como 'objetivo', 'alcance', 'roles' o 'procesos'."

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
            "¿Cuál es el objetivo del manual?",
            "¿Qué alcance tiene el documento?",
            "¿Qué procesos se describen?",
            "¿Qué roles existen en el equipo?",
            "¿Cómo funciona el soporte técnico?",
            "¿Qué es un Punto Digital?",
            "¿Quiénes son los responsables del programa?"
        ]
        ejemplos_texto = "\n".join([f"• {ej}" for ej in ejemplos])
        return f"""❓ **Puedes preguntarme sobre cualquier tema de tus documentos:**

{ejemplos_texto}

💡 **Consejos:**
• Preguntas específicas → mejores respuestas
• Usa términos como 'objetivo', 'alcance', 'proceso', 'roles'
• Contexto → más relevante

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
    print(f"🚀 ChatBot con búsqueda mejorada iniciado en puerto {port}")
    print(f"📁 Ruta documentos: http://localhost:{port}/documentos/")
    app.run(host='0.0.0.0', port=port, debug=False)