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
# BÚSQUEDA ESPECÍFICA MEJORADA
# ================================
def buscar_tabla_puesta_marcha_exacta(contenido):
    """Busca específicamente la tabla de puesta en marcha"""
    lineas = contenido.split('\n')
    procedimientos = []
    
    # Buscar el inicio exacto de la tabla
    for i, linea in enumerate(lineas):
        linea_limpia = linea.strip()
        
        # Buscar el título exacto de la tabla
        if 'servicio de puesta en marcha de un punto digital' in linea_limpia.lower():
            procedimientos.append("<strong>🚀 SERVICIO DE PUESTA EN MARCHA DE UN PUNTO DIGITAL</strong><br><br>")
            
            # Buscar las líneas de la tabla después del título
            for j in range(i+1, min(i+20, len(lineas))):
                linea_tabla = lineas[j].strip()
                
                # Buscar líneas que parecen ser de la tabla
                if (re.match(r'^\d+\.', linea_tabla) or 
                    re.match(r'^[A-Z]\.', linea_tabla) or
                    any(palabra in linea_tabla.lower() for palabra in ['proyectos', 'stock', 'soporte', 'imagen', 'monitoreo', 'equipo'])):
                    
                    if len(linea_tabla) > 3:  # Filtrar líneas muy cortas
                        # Formatear según el contenido
                        if 'instalación' in linea_tabla.lower():
                            procedimientos.append(f"🔨 {linea_tabla}<br>")
                        elif 'inauguración' in linea_tabla.lower():
                            procedimientos.append(f"🎉 {linea_tabla}<br>")
                        elif 'equipamiento' in linea_tabla.lower() or 'stock' in linea_tabla.lower():
                            procedimientos.append(f"📦 {linea_tabla}<br>")
                        elif 'preinstalación' in linea_tabla.lower():
                            procedimientos.append(f"🔧 {linea_tabla}<br>")
                        else:
                            procedimientos.append(f"• {linea_tabla}<br>")
                
                # Detener si encontramos el final de la tabla
                if 'procedimientos de seguimiento' in linea_tabla.lower() or j == i+19:
                    break
            
            break  # Salir después de encontrar la primera tabla
    
    return procedimientos

def buscar_tabla_seguimiento_exacta(contenido):
    """Busca específicamente la tabla de seguimiento"""
    lineas = contenido.split('\n')
    procedimientos = []
    
    for i, linea in enumerate(lineas):
        linea_limpia = linea.strip()
        
        if 'procedimientos de seguimiento y soporte a puntos digitales' in linea_limpia.lower():
            procedimientos.append("<br><strong>🔧 PROCEDIMIENTOS DE SEGUIMIENTO Y SOPORTE</strong><br><br>")
            
            # Buscar las líneas de la tabla de seguimiento
            for j in range(i+1, min(i+15, len(lineas))):
                linea_tabla = lineas[j].strip()
                
                if (re.match(r'^[A-Z]\.', linea_tabla) or 
                    any(palabra in linea_tabla.lower() for palabra in ['soporte técnico', 'imagen', 'gestión de stock', 'equipo'])):
                    
                    if len(linea_tabla) > 5:
                        if 'soporte técnico' in linea_tabla.lower():
                            procedimientos.append(f"🛠️ {linea_tabla}<br>")
                        elif 'imagen' in linea_tabla.lower():
                            procedimientos.append(f"🎨 {linea_tabla}<br>")
                        elif 'stock' in linea_tabla.lower():
                            procedimientos.append(f"📦 {linea_tabla}<br>")
                        else:
                            procedimientos.append(f"• {linea_tabla}<br>")
                
                # Detener si encontramos otra sección
                if 'lineamientos' in linea_tabla.lower() or j == i+14:
                    break
            
            break
    
    return procedimientos

def buscar_informacion_estructurada(contenido, termino_busqueda):
    """Busca información estructurada sobre un término específico"""
    lineas = contenido.split('\n')
    resultados = []
    termino = termino_busqueda.lower()
    
    for i, linea in enumerate(lineas):
        linea_limpia = linea.strip()
        linea_lower = linea_limpia.lower()
        
        if termino in linea_lower and len(linea_limpia) > 10:
            # Buscar contexto alrededor
            inicio = max(0, i-1)
            fin = min(len(lineas), i+4)
            contexto = []
            
            for j in range(inicio, fin):
                if lineas[j].strip():
                    contexto.append(lineas[j].strip())
            
            if contexto:
                resultados.extend(contexto)
                if len(resultados) >= 8:  # Límite de líneas
                    break
    
    return resultados

def buscar_localmente_mejorada(pregunta, documentos):
    """Búsqueda local mejorada"""
    pregunta_limpia = pregunta.lower()
    
    # 1. Pregunta sobre documentos disponibles
    if any(p in pregunta_limpia for p in ['documento', 'cargado', 'archivo', 'disponible']):
        docs = list(documentos.keys())
        doc_list = "<br>".join([f"• {d}" for d in docs])
        return f"<strong>📂 Documentos cargados ({len(docs)}):</strong><br><br>{doc_list}"
    
    resultados = []
    
    for doc_nombre, contenido in documentos.items():
        # 2. Búsqueda de tablas específicas para "puesta en marcha"
        if any(p in pregunta_limpia for p in ['puesta en marcha', 'procedimiento', 'instalación']):
            tabla_puesta_marcha = buscar_tabla_puesta_marcha_exacta(contenido)
            if tabla_puesta_marcha:
                resultados.append(f"<strong>📄 {doc_nombre}</strong><br><br>" + "".join(tabla_puesta_marcha))
            
            tabla_seguimiento = buscar_tabla_seguimiento_exacta(contenido)
            if tabla_seguimiento:
                if resultados:
                    resultados[-1] += "".join(tabla_seguimiento)
                else:
                    resultados.append(f"<strong>📄 {doc_nombre}</strong><br><br>" + "".join(tabla_seguimiento))
        
        # 3. Si no se encontraron tablas, buscar información general
        if not resultados and any(p in pregunta_limpia for p in ['puesta en marcha', 'implementación']):
            info_estructurada = buscar_informacion_estructurada(contenido, 'puesta en marcha')
            if info_estructurada:
                contenido_formateado = "<br>".join([f"📋 {linea}" for linea in info_estructurada])
                resultados.append(f"<strong>📄 {doc_nombre}</strong><br><br>{contenido_formateado}")
    
    if resultados:
        return "<br><br>".join(resultados)
    
    # 4. Búsqueda por equipos
    equipos = {
        'dirección': '👨‍💼',
        'proyectos': '📋', 
        'stock': '📦',
        'soporte': '🔧',
        'imagen': '🎨',
        'monitoreo': '📊'
    }
    
    for equipo, emoji in equipos.items():
        if equipo in pregunta_limpia:
            for doc_nombre, contenido in documentos.items():
                if equipo in contenido.lower():
                    info_equipo = buscar_informacion_estructurada(contenido, equipo)
                    if info_equipo:
                        contenido_equipo = "<br>".join([f"{emoji} {linea}" for linea in info_equipo[:6]])
                        return f"<strong>📄 {doc_nombre}</strong><br><br><strong>{emoji} {equipo.upper()}</strong><br><br>{contenido_equipo}"
    
    # 5. Búsqueda general
    for doc_nombre, contenido in documentos.items():
        if pregunta_limpia in contenido.lower():
            info_general = buscar_informacion_estructurada(contenido, pregunta_limpia)
            if info_general:
                contenido_general = "<br>".join([f"• {linea}" for linea in info_general[:5]])
                return f"<strong>📄 {doc_nombre}</strong><br><br>{contenido_general}"
    
    return "🤔 No encontré información específica sobre 'puesta en marcha'.<br><br>Puedes preguntar sobre:<br>• Procedimientos específicos<br>• Equipos (proyectos, stock, soporte)<br>• Documentos disponibles"

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
            # Para "puesta en marcha", enviar información específica de tablas
            if any(p in pregunta.lower() for p in ['puesta en marcha', 'procedimiento']):
                tabla_puesta = buscar_tabla_puesta_marcha_exacta(contenido)
                tabla_seguimiento = buscar_tabla_seguimiento_exacta(contenido)
                
                if tabla_puesta or tabla_seguimiento:
                    contexto += f"DOCUMENTO: {doc_nombre}\n"
                    if tabla_puesta:
                        contexto += "TABLA PUESTA EN MARCHA:\n" + "\n".join([p.replace('<br>', '\n').replace('<strong>', '').replace('</strong>', '') for p in tabla_puesta]) + "\n"
                    if tabla_seguimiento:
                        contexto += "TABLA SEGUIMIENTO:\n" + "\n".join([p.replace('<br>', '\n').replace('<strong>', '').replace('</strong>', '') for p in tabla_seguimiento]) + "\n"
                    contexto += "\n"
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
                        "content": "Eres un asistente especializado en Puntos Digitales. Cuando te pregunten sobre 'puesta en marcha', enfócate en los PROCEDIMIENTOS y PASOS específicos de las tablas. Responde de forma CLARA y ESTRUCTURADA. Usa HTML básico: <br> para saltos de línea y <strong> para negritas. Basate SOLO en la información proporcionada."
                    },
                    {
                        "role": "user", 
                        "content": f"{contexto}\n\nPREGUNTA: {pregunta}\n\nRESPUESTA (usa HTML, organiza en pasos):"
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