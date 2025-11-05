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
# BÚSQUEDA MEJORADA PARA PROCEDIMIENTOS
# ================================
def extraer_procedimientos_instalacion_completo(contenido):
    """Extrae específicamente los procedimientos de instalación de las tablas"""
    lineas = contenido.split('\n')
    procedimientos = []
    
    # Buscar la tabla de "Servicio de Puesta en Marcha"
    en_tabla_puesta_marcha = False
    pasos_encontrados = []
    
    for i, linea in enumerate(lineas):
        linea_limpia = linea.strip()
        
        # Detectar inicio de la tabla de puesta en marcha
        if 'servicio de puesta en marcha' in linea_limpia.lower():
            en_tabla_puesta_marcha = True
            procedimientos.append("<strong>🚀 SERVICIO DE PUESTA EN MARCHA DE UN PUNTO DIGITAL</strong><br>")
            continue
            
        # Capturar las líneas de la tabla
        if en_tabla_puesta_marcha:
            # Buscar líneas que parecen ser de la tabla (contienen números y equipos)
            if (re.match(r'^\d+\.', linea_limpia) or 
                any(equipo in linea_limpia.lower() for equipo in ['proyectos', 'stock', 'soporte', 'imagen', 'monitoreo']) and 
                any(proceso in linea_limpia.lower() for proceso in ['gestión', 'análisis', 'instalación', 'preinstalación', 'entrega'])):
                
                # Formatear la línea para mejor legibilidad
                if 'instalación' in linea_limpia.lower():
                    linea_formateada = f"<br>🔨 <strong>{linea_limpia}</strong>"
                else:
                    linea_formateada = f"<br>• {linea_limpia}"
                
                procedimientos.append(linea_formateada)
                pasos_encontrados.append(linea_limpia)
            
            # Detectar fin de la tabla (cuando empieza otra sección)
            if 'procedimientos de seguimiento' in linea_limpia.lower() or i > len(lineas) - 5:
                en_tabla_puesta_marcha = False
    
    # Si no se encontró la tabla específica, buscar información relevante sobre instalación
    if not pasos_encontrados:
        procedimientos.append("<strong>📋 INFORMACIÓN SOBRE INSTALACIÓN</strong><br>")
        actividades_instalacion = []
        
        for i, linea in enumerate(lineas):
            linea_limpia = linea.strip()
            if any(termino in linea_limpia.lower() for termino in [
                'instalación presencial', 'realiza las instalaciones', 'configuraciones necesarias',
                'puesta en marcha', 'equipos tecnológicos', 'soporte técnico tic'
            ]) and len(linea_limpia) > 20:
                actividades_instalacion.append(f"<br>🔧 {linea_limpia}")
                if len(actividades_instalacion) >= 8:
                    break
        
        procedimientos.extend(actividades_instalacion)
    
    return procedimientos

def extraer_procedimientos_seguimiento(contenido):
    """Extrae los procedimientos de seguimiento y soporte"""
    lineas = contenido.split('\n')
    procedimientos = []
    en_tabla_seguimiento = False
    
    for i, linea in enumerate(lineas):
        linea_limpia = linea.strip()
        
        # Detectar inicio de la tabla de seguimiento
        if 'procedimientos de seguimiento y soporte' in linea_limpia.lower():
            en_tabla_seguimiento = True
            procedimientos.append("<br><strong>🔧 PROCEDIMIENTOS DE SEGUIMIENTO Y SOPORTE</strong><br>")
            continue
            
        # Capturar líneas de la tabla de seguimiento
        if en_tabla_seguimiento:
            if any(equipo in linea_limpia.lower() for equipo in ['soporte técnico', 'imagen', 'gestión de stock']):
                if len(linea_limpia) > 10:
                    procedimientos.append(f"<br>• {linea_limpia}")
            
            # Detectar fin de la tabla
            if i > len(lineas) - 3 or 'lineamientos' in linea_limpia.lower():
                en_tabla_seguimiento = False
    
    return procedimientos

def buscar_procedimientos_especificos(pregunta, documentos):
    """Búsqueda específica para procedimientos"""
    pregunta_limpia = pregunta.lower()
    resultados = []
    
    for doc_nombre, contenido in documentos.items():
        procedimientos_completos = []
        
        # Para preguntas sobre instalación
        if any(p in pregunta_limpia for p in ['instalación', 'implementación', 'puesta en marcha']):
            procedimientos_instalacion = extraer_procedimientos_instalacion_completo(contenido)
            procedimientos_completos.extend(procedimientos_instalacion)
        
        # Para preguntas sobre seguimiento/soporte
        if any(p in pregunta_limpia for p in ['seguimiento', 'soporte', 'mantenimiento']):
            procedimientos_seguimiento = extraer_procedimientos_seguimiento(contenido)
            procedimientos_completos.extend(procedimientos_seguimiento)
        
        # Si no se especifica, mostrar ambos
        if not any(p in pregunta_limpia for p in ['instalación', 'seguimiento', 'implementación', 'soporte']):
            procedimientos_instalacion = extraer_procedimientos_instalacion_completo(contenido)
            procedimientos_seguimiento = extraer_procedimientos_seguimiento(contenido)
            procedimientos_completos.extend(procedimientos_instalacion)
            procedimientos_completos.extend(procedimientos_seguimiento)
        
        if procedimientos_completos:
            resultados.append(f"<strong>📄 {doc_nombre}</strong><br><br>" + "".join(procedimientos_completos))
    
    return resultados

def buscar_localmente_mejorada(pregunta, documentos):
    """Búsqueda local mejorada"""
    pregunta_limpia = pregunta.lower()
    
    # 1. Pregunta sobre documentos disponibles
    if any(p in pregunta_limpia for p in ['documento', 'cargado', 'archivo', 'disponible']):
        docs = list(documentos.keys())
        doc_list = "<br>".join([f"• {d}" for d in docs])
        return f"<strong>📂 Documentos cargados ({len(docs)}):</strong><br><br>{doc_list}"
    
    # 2. Búsqueda específica de procedimientos
    if any(p in pregunta_limpia for p in ['procedimiento', 'instalación', 'proceso', 'implementación', 'puesta en marcha', 'seguimiento', 'soporte']):
        resultados_procedimientos = buscar_procedimientos_especificos(pregunta, documentos)
        if resultados_procedimientos:
            return "<br><br>".join(resultados_procedimientos)
    
    # 3. Búsqueda por equipos
    equipos = {
        'dirección': '👨‍💼 Dirección',
        'proyectos': '📋 Proyectos', 
        'stock': '📦 Stock',
        'soporte': '🔧 Soporte Técnico',
        'imagen': '🎨 Imagen',
        'monitoreo': '📊 Monitoreo'
    }
    
    for equipo, emoji in equipos.items():
        if equipo in pregunta_limpia:
            for doc_nombre, contenido in documentos.items():
                if equipo in contenido.lower():
                    # Buscar sección específica del equipo
                    lineas = contenido.split('\n')
                    info_equipo = []
                    for i, linea in enumerate(lineas):
                        if (equipo in linea.lower() or emoji.lower() in linea.lower()) and len(linea) > 15:
                            info_equipo.append(f"<br>{linea}")
                            if len(info_equipo) >= 4:
                                break
                    
                    if info_equipo:
                        return f"<strong>📄 {doc_nombre}</strong><br><br><strong>{emoji} {equipo.upper()}</strong>" + "".join(info_equipo)
    
    # 4. Búsqueda general
    for doc_nombre, contenido in documentos.items():
        if pregunta_limpia in contenido.lower():
            lineas = contenido.split('\n')
            for i, linea in enumerate(lineas):
                if pregunta_limpia in linea.lower():
                    inicio = max(0, i-1)
                    fin = min(len(lineas), i+4)
                    contexto = "<br>".join(lineas[inicio:fin])
                    return f"<strong>📄 {doc_nombre}</strong><br><br>{contexto}"
    
    return "🤔 No encontré información específica sobre ese tema.<br><br>Puedes preguntar sobre:<br>• Procedimientos de instalación<br>• Procedimientos de seguimiento<br>• Equipos específicos<br>• Documentos disponibles"

# ================================
# GROQ 
# ================================
def preguntar_groq(pregunta, documentos):
    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        respuesta = buscar_localmente_mejorada(pregunta, documentos)
        return respuesta
    
    try:
        contexto = "INFORMACIÓN SOBRE PROCEDIMIENTOS DE PUNTO DIGITAL:\n\n"
        
        for doc_nombre, contenido in documentos.items():
            # Extraer información relevante según la pregunta
            if any(p in pregunta.lower() for p in ['procedimiento', 'instalación', 'proceso']):
                # Extraer tablas de procedimientos
                procedimientos = extraer_procedimientos_instalacion_completo(contenido)
                procedimientos_seguimiento = extraer_procedimientos_seguimiento(contenido)
                
                if procedimientos or procedimientos_seguimiento:
                    contexto += f"DOCUMENTO: {doc_nombre}\n"
                    if procedimientos:
                        contexto += "PROCEDIMIENTOS INSTALACIÓN:\n" + "\n".join([p.replace('<br>', '\n').replace('<strong>', '').replace('</strong>', '') for p in procedimientos]) + "\n"
                    if procedimientos_seguimiento:
                        contexto += "PROCEDIMIENTOS SEGUIMIENTO:\n" + "\n".join([p.replace('<br>', '\n').replace('<strong>', '').replace('</strong>', '') for p in procedimientos_seguimiento]) + "\n"
                    contexto += "\n"
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
                        "content": "Eres un asistente especializado en Puntos Digitales. Responde de forma CLARA y ESTRUCTURADA. Cuando hablas de procedimientos, ORGANIZA la información en pasos claros. Usa HTML básico: <br> para saltos de línea y <strong> para negritas. Basate SOLO en la información proporcionada."
                    },
                    {
                        "role": "user", 
                        "content": f"{contexto}\n\nPREGUNTA: {pregunta}\n\nRESPUESTA (usa HTML, organiza en pasos si es sobre procedimientos):"
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 800
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
        
        # Respuestas rápidas
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