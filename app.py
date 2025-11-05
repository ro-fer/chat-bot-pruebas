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
# BÚSQUEDA ESPECÍFICA PARA PROCEDIMIENTOS
# ================================
def extraer_tabla_procedimientos(contenido):
    """Extrae específicamente las tablas de procedimientos"""
    lineas = contenido.split('\n')
    procedimientos = []
    en_tabla_puesta_marcha = False
    en_tabla_seguimiento = False
    
    for i, linea in enumerate(lineas):
        linea_limpia = linea.strip()
        
        # Detectar inicio de tabla de puesta en marcha
        if 'servicio de puesta en marcha' in linea_limpia.lower():
            en_tabla_puesta_marcha = True
            procedimientos.append("<strong>🚀 SERVICIO DE PUESTA EN MARCHA - PROCEDIMIENTOS</strong><br>")
            continue
            
        # Detectar inicio de tabla de seguimiento
        if 'procedimientos de seguimiento y soporte' in linea_limpia.lower():
            en_tabla_seguimiento = True
            procedimientos.append("<br><strong>🔧 PROCEDIMIENTOS DE SEGUIMIENTO Y SOPORTE</strong><br>")
            continue
            
        # Capturar líneas de la tabla de puesta en marcha
        if en_tabla_puesta_marcha:
            # Buscar líneas con formato de tabla (números, equipos, procesos)
            if re.match(r'^\d+\.', linea_limpia) or any(equipo in linea_limpia.lower() for equipo in ['proyectos', 'stock', 'soporte', 'imagen', 'monitoreo']):
                if len(linea_limpia) > 5:
                    # Formatear mejor la línea
                    if 'instalación' in linea_limpia.lower():
                        procedimientos.append(f"<br>🔨 <strong>{linea_limpia}</strong>")
                    else:
                        procedimientos.append(f"<br>• {linea_limpia}")
            
            # Detectar fin de la tabla
            if 'procedimientos de seguimiento' in linea_limpia.lower() or i > len(lineas) - 10:
                en_tabla_puesta_marcha = False
                
        # Capturar líneas de la tabla de seguimiento
        if en_tabla_seguimiento:
            if any(equipo in linea_limpia.lower() for equipo in ['soporte técnico', 'imagen', 'gestión de stock']):
                if len(linea_limpia) > 5:
                    procedimientos.append(f"<br>• {linea_limpia}")
    
    return procedimientos

def extraer_procedimientos_especificos(contenido, tipo_procedimiento):
    """Extrae procedimientos específicos según el tipo solicitado"""
    lineas = contenido.split('\n')
    procedimientos = []
    
    for i, linea in enumerate(lineas):
        linea_limpia = linea.strip()
        
        # Para instalación - buscar actividades específicas
        if tipo_procedimiento == 'instalación':
            if any(termino in linea_limpia.lower() for termino in [
                'ejecuta la instalación', 'realiza las instalaciones', 
                'instalación presencial', 'configuraciones necesarias',
                'puesta en marcha', 'preinstalación'
            ]):
                procedimientos.append(f"<br>🔨 {linea_limpia}")
        
        # Para cartelería
        elif tipo_procedimiento == 'cartelería':
            if any(termino in linea_limpia.lower() for termino in [
                'cartelería', 'señalética', 'imagen', 'instalaciones presenciales',
                'envíos e instalaciones', 'disposición y tipo de cartelería'
            ]):
                procedimientos.append(f"<br>📋 {linea_limpia}")
        
        # Para equipamiento/stock
        elif tipo_procedimiento == 'equipamiento':
            if any(termino in linea_limpia.lower() for termino in [
                'equipamiento', 'stock', 'configurar equipos', 'envío y entrega',
                'movimientos de stock', 'inventario'
            ]):
                procedimientos.append(f"<br>💻 {linea_limpia}")
    
    return procedimientos

def buscar_procedimientos_especificos(pregunta, documentos):
    """Búsqueda específica para procedimientos"""
    pregunta_limpia = pregunta.lower()
    resultados = []
    
    # Determinar el tipo de procedimiento buscado
    tipo_procedimiento = None
    if any(p in pregunta_limpia for p in ['instalación', 'instalar', 'implementación']):
        tipo_procedimiento = 'instalación'
    elif any(p in pregunta_limpia for p in ['cartelería', 'cartel', 'imagen', 'señalética']):
        tipo_procedimiento = 'cartelería'
    elif any(p in pregunta_limpia for p in ['equipamiento', 'stock', 'inventario', 'configuración']):
        tipo_procedimiento = 'equipamiento'
    
    for doc_nombre, contenido in documentos.items():
        # Extraer tablas de procedimientos
        tabla_procedimientos = extraer_tabla_procedimientos(contenido)
        if tabla_procedimientos:
            resultados.append(f"<strong>📄 {doc_nombre}</strong><br><br>" + "".join(tabla_procedimientos))
        
        # Extraer procedimientos específicos según el tipo
        if tipo_procedimiento:
            procedimientos_especificos = extraer_procedimientos_especificos(contenido, tipo_procedimiento)
            if procedimientos_especificos:
                resultados.append(f"<strong>📄 {doc_nombre} - {tipo_procedimiento.upper()}</strong><br><br>" + "".join(procedimientos_especificos[:10]))
    
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
    if any(p in pregunta_limpia for p in ['procedimiento', 'instalación', 'proceso', 'implementación', 'puesta en marcha', 'cartelería', 'equipamiento']):
        resultados_procedimientos = buscar_procedimientos_especificos(pregunta, documentos)
        if resultados_procedimientos:
            return "<br><br>".join(resultados_procedimientos)
    
    # 3. Búsqueda por equipos (simplificada)
    equipos = ['dirección', 'proyectos', 'stock', 'soporte', 'imagen', 'monitoreo']
    for equipo in equipos:
        if equipo in pregunta_limpia:
            for doc_nombre, contenido in documentos.items():
                if equipo in contenido.lower():
                    # Encontrar sección del equipo
                    lineas = contenido.split('\n')
                    seccion_equipo = []
                    for i, linea in enumerate(lineas):
                        if equipo in linea.lower() and len(linea) > 10:
                            seccion_equipo.append(linea)
                            if len(seccion_equipo) >= 3:
                                break
                    
                    if seccion_equipo:
                        contenido_equipo = "<br>".join(seccion_equipo)
                        return f"<strong>📄 {doc_nombre}</strong><br><br>{contenido_equipo}"
    
    # 4. Búsqueda general
    for doc_nombre, contenido in documentos.items():
        if pregunta_limpia in contenido.lower():
            lineas = contenido.split('\n')
            for i, linea in enumerate(lineas):
                if pregunta_limpia in linea.lower():
                    inicio = max(0, i-1)
                    fin = min(len(lineas), i+3)
                    contexto = "<br>".join(lineas[inicio:fin])
                    return f"<strong>📄 {doc_nombre}</strong><br><br>{contexto}"
    
    return "🤔 No encontré información específica sobre ese tema.<br><br>Puedes preguntar sobre:<br>• Procedimientos de instalación<br>• Cartelería e imagen<br>• Gestión de equipamiento<br>• Equipos específicos<br>• Documentos disponibles"

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
            # Enviar información específica según la pregunta
            if any(p in pregunta.lower() for p in ['procedimiento', 'instalación', 'proceso']):
                # Extraer tablas de procedimientos
                tabla_procedimientos = extraer_tabla_procedimientos(contenido)
                if tabla_procedimientos:
                    contexto += f"DOCUMENTO: {doc_nombre}\n" + "\n".join([linea.replace('<br>', '\n').replace('<strong>', '').replace('</strong>', '') for linea in tabla_procedimientos]) + "\n\n"
            else:
                lineas = contenido.split('\n')[:8]
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
                        "content": "Eres un asistente especializado en Puntos Digitales. Responde de forma CLARA y CONCISA. Enfócate en los PROCEDIMIENTOS y PASOS específicos cuando se pregunte sobre procesos. Usa HTML básico: <br> para saltos de línea y <strong> para negritas. Basate SOLO en la información proporcionada."
                    },
                    {
                        "role": "user", 
                        "content": f"{contexto}\n\nPREGUNTA: {pregunta}\n\nRESPUESTA (usa HTML, sé específico con procedimientos):"
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