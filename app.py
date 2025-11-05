from flask import Flask, request, jsonify, render_template, send_from_directory, Response
import os
from docx import Document
import requests
import re

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
# BÚSQUEDA MEJORADA - ESPECÍFICA PARA PROCEDIMIENTOS
# ================================
def extraer_procedimientos_instalacion(contenido):
    """Extrae específicamente los procedimientos de instalación"""
    lineas = contenido.split('\n')
    en_seccion_procedimientos = False
    procedimientos = []
    
    for i, linea in enumerate(lineas):
        linea_limpia = linea.strip()
        
        # Buscar la sección de procedimientos de instalación
        if 'instalación' in linea_limpia.lower() and any(p in linea_limpia.lower() for p in ['procedimiento', 'proceso', 'servicio']):
            en_seccion_procedimientos = True
            procedimientos.append(f"<strong>🔧 {linea_limpia}</strong>")
            continue
            
        # Buscar la tabla de procedimientos
        if 'servicio de puesta en marcha' in linea_limpia.lower():
            en_seccion_procedimientos = True
            procedimientos.append("<strong>🚀 SERVICIO DE PUESTA EN MARCHA DE UN PUNTO DIGITAL</strong>")
            continue
            
        # Capturar los pasos de instalación de la tabla
        if en_seccion_procedimientos:
            # Buscar líneas que contengan números (pasos del proceso)
            if re.match(r'^\d+\.', linea_limpia) or any(palabra in linea_limpia.lower() for palabra in ['instalación', 'soporte técnico', 'equipamiento']):
                if len(linea_limpia) > 5:
                    procedimientos.append(f"<br>• {linea_limpia}")
            
            # Capturar las actividades de instalación del equipo de soporte
            elif 'realiza las instalaciones' in linea_limpia.lower() or 'ejecuta la instalación' in linea_limpia.lower():
                procedimientos.append(f"<br>🔨 <strong>Actividad de instalación:</strong> {linea_limpia}")
    
    return procedimientos

def buscar_procedimientos_especificos(pregunta, documentos):
    """Búsqueda específica para procedimientos"""
    pregunta_limpia = pregunta.lower()
    resultados = []
    
    for doc_nombre, contenido in documentos.items():
        # Para preguntas sobre instalación
        if any(p in pregunta_limpia for p in ['instalación', 'procedimiento', 'proceso', 'implementación']):
            procedimientos = extraer_procedimientos_instalacion(contenido)
            if procedimientos:
                resultados.append(f"<strong>📄 {doc_nombre}</strong><br><br>" + "<br>".join(procedimientos[:15]))
        
        # Buscar información específica sobre pasos de instalación
        elif 'puesta en marcha' in pregunta_limpia or 'implementación' in pregunta_limpia:
            # Buscar la tabla de puesta en marcha
            lineas = contenido.split('\n')
            en_tabla = False
            pasos = []
            
            for i, linea in enumerate(lineas):
                if 'servicio de puesta en marcha' in linea.lower():
                    en_tabla = True
                    pasos.append("<strong>📋 PROCEDIMIENTOS DE INSTALACIÓN - PUESTA EN MARCHA</strong>")
                    continue
                    
                if en_tabla:
                    if re.match(r'^\d+\.', linea.strip()):
                        pasos.append(f"<br>🔹 {linea.strip()}")
                    elif 'proyectos' in linea.lower() or 'soporte técnico' in linea.lower():
                        if len(linea.strip()) > 10:
                            pasos.append(f"<br>• {linea.strip()}")
            
            if pasos:
                resultados.append(f"<strong>📄 {doc_nombre}</strong><br><br>" + "<br>".join(pasos[:12]))
    
    return resultados

def buscar_localmente_mejorada(pregunta, documentos):
    """Búsqueda local mejorada con respuestas en HTML"""
    pregunta_limpia = pregunta.lower()
    
    # Diccionario de palabras clave por equipo
    palabras_clave = {
        'dirección': ['dirección', 'director', 'estrategia', 'dirección del programa'],
        'proyectos': ['proyectos', 'analistas', 'implementación', 'inauguración', 'equipo de proyectos'],
        'stock': ['stock', 'equipamiento', 'inventario', 'configuración', 'gestión de stock'],
        'soporte': ['soporte', 'técnico', 'tic', 'instalación', 'ingeniería', 'soporte técnico'],
        'imagen': ['imagen', 'cartelería', 'señalética', 'equipo de imagen'],
        'monitoreo': ['monitoreo', 'vinculación', 'capacitación', 'evaluación', 'monitoreo y vinculación']
    }
    
    # 1. Pregunta sobre documentos disponibles
    if any(p in pregunta_limpia for p in ['documento', 'cargado', 'archivo', 'disponible']):
        docs = list(documentos.keys())
        doc_list = "<br>".join([f"• {d}" for d in docs])
        return f"<strong>📂 Documentos cargados ({len(docs)}):</strong><br><br>{doc_list}"
    
    # 2. 🔥 NUEVO: Búsqueda específica de procedimientos
    if any(p in pregunta_limpia for p in ['procedimiento', 'instalación', 'proceso', 'implementación', 'puesta en marcha']):
        resultados_procedimientos = buscar_procedimientos_especificos(pregunta, documentos)
        if resultados_procedimientos:
            return "<br><br>".join(resultados_procedimientos)
    
    # 3. Buscar equipo específico (código existente)
    equipo_encontrado = None
    for equipo, keywords in palabras_clave.items():
        if any(palabra in pregunta_limpia for palabra in keywords):
            equipo_encontrado = equipo
            break
    
    resultados = []
    for doc_nombre, contenido in documentos.items():
        if equipo_encontrado:
            # (Aquí iría tu función extraer_seccion_equipo_estructurada)
            # Por simplicidad, uso una búsqueda básica
            if equipo_encontrado in contenido.lower():
                lineas_relevantes = []
                lineas = contenido.split('\n')
                for linea in lineas:
                    if equipo_encontrado in linea.lower() and len(linea) > 10:
                        lineas_relevantes.append(linea)
                        if len(lineas_relevantes) >= 5:
                            break
                
                if lineas_relevantes:
                    contenido_relevante = "<br>".join(lineas_relevantes[:5])
                    resultados.append(f"<strong>📄 {doc_nombre}</strong><br><br>{contenido_relevante}")
                    break
    
    if resultados:
        return "<br><br>".join(resultados)
    
    # 4. Búsqueda general
    for doc_nombre, contenido in documentos.items():
        if pregunta_limpia in contenido.lower():
            # Encontrar contexto alrededor
            lineas = contenido.split('\n')
            for i, linea in enumerate(lineas):
                if pregunta_limpia in linea.lower():
                    inicio = max(0, i-1)
                    fin = min(len(lineas), i+3)
                    contexto = "<br>".join(lineas[inicio:fin])
                    return f"<strong>📄 {doc_nombre}</strong><br><br>{contexto}"
    
    return "🤔 No encontré información específica sobre ese tema.<br><br>Puedes preguntar sobre:<br>• Procedimientos de instalación<br>• Equipos específicos<br>• Procesos de implementación<br>• Documentos disponibles"

# ================================
# GROQ 
# ================================
def preguntar_groq(pregunta, documentos):
    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        respuesta = buscar_localmente_mejorada(pregunta, documentos)
        return respuesta
    
    try:
        contexto = "INFORMACIÓN SOBRE PUNTO DIGITAL:\n\n"
        
        for doc_nombre, contenido in documentos.items():
            # Para preguntas sobre procedimientos, enviar información específica
            if any(p in pregunta.lower() for p in ['procedimiento', 'instalación', 'proceso']):
                # Extraer secciones relevantes
                lineas = contenido.split('\n')
                secciones_relevantes = []
                for i, linea in enumerate(lineas):
                    if any(term in linea.lower() for term in ['instalación', 'procedimiento', 'proceso', 'puesta en marcha']):
                        inicio = max(0, i-1)
                        fin = min(len(lineas), i+5)
                        secciones_relevantes.extend(lineas[inicio:fin])
                
                if secciones_relevantes:
                    contexto += f"DOCUMENTO: {doc_nombre}\n" + '\n'.join(secciones_relevantes[:20]) + "\n\n"
            else:
                lineas = contenido.split('\n')[:10]
                contexto += f"DOCUMENTO: {doc_nombre}\n" + '\n'.join(lineas) + "\n\n"
        
        if len(contexto) > 3000:
            contexto = contexto[:3000] + "..."
        
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
                        "content": "Eres un asistente especializado en Puntos Digitales. Responde de forma CLARA y CONCISA. Enfócate en la información específica solicitada. Usa HTML básico: <br> para saltos de línea y <strong> para negritas. Basate SOLO en la información proporcionada."
                    },
                    {
                        "role": "user", 
                        "content": f"{contexto}\n\nPREGUNTA: {pregunta}\n\nRESPUESTA (usa HTML, sé específico y conciso):"
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 600
            },
            timeout=15
        )
        
        if response.status_code == 200:
            respuesta = response.json()["choices"][0]["message"]["content"]
            if '<br>' not in respuesta and '</strong>' not in respuesta:
                respuesta = respuesta.replace('\n', '<br>')
            return respuesta
        else:
            return buscar_localmente_mejorada(pregunta, documentos)
            
    except Exception as e:
        return buscar_localmente_mejorada(pregunta, documentos)

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
            return jsonify({'success': True, 'response': "📂 No hay documentos cargados en la carpeta 'documents'."})
        
        # Respuestas rápidas con HTML
        if any(s in pregunta.lower() for s in ['hola', 'buenos días', 'buenas', 'hello', 'hi']):
            return jsonify({
                'success': True, 
                'response': f"¡Hola! 👋 Soy tu asistente especializado en Punto Digital.<br><br>Tengo {len(documentos)} documento(s) cargados.<br><br>¿En qué puedo ayudarte?"
            })
        
        if any(s in pregunta.lower() for s in ['chao', 'adiós', 'bye', 'nos vemos', 'gracias']):
            return jsonify({
                'success': True, 
                'response': "¡Hasta luego! 👋<br><br>Fue un gusto ayudarte."
            })
        
        # Usar Groq con fallback transparente
        respuesta = preguntar_groq(pregunta, documentos)
        return jsonify({'success': True, 'response': respuesta})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error: {str(e)}'})

# ================================
# INICIO DE LA APLICACIÓN
# ================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 ChatBot Punto Digital iniciado en puerto {port}")
    api_key = os.environ.get('GROQ_API_KEY')
    print(f"🔍 GROQ_API_KEY: {'✅ CONFIGURADA' if api_key else '❌ FALTANTE - Usando modo local'}")
    
    documentos = cargar_documentos_docx()
    print(f"📄 Documentos cargados: {len(documentos)}")
    
    app.run(host='0.0.0.0', port=port, debug=False)