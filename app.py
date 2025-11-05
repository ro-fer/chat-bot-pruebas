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
# BÚSQUEDA DEBUG - VERSIÓN SIMPLIFICADA
# ================================
def debug_buscar_puesta_marcha(contenido):
    """Función DEBUG para encontrar exactamente qué hay en el documento"""
    lineas = contenido.split('\n')
    resultados_debug = []
    
    resultados_debug.append("🔍 <strong>DEBUG - BUSCANDO 'PUESTA EN MARCHA':</strong><br>")
    
    # Buscar cualquier mención de puesta en marcha
    for i, linea in enumerate(lineas):
        linea_limpia = linea.strip()
        if 'puesta' in linea_limpia.lower() or 'marcha' in linea_limpia.lower():
            resultados_debug.append(f"Línea {i}: {linea_limpia}<br>")
    
    # Buscar la tabla específica
    resultados_debug.append("<br>🔍 <strong>BUSCANDO TABLA:</strong><br>")
    for i, linea in enumerate(lineas):
        linea_limpia = linea.strip()
        if 'servicio' in linea_limpia.lower() and any(p in linea_limpia.lower() for p in ['puesta', 'marcha']):
            resultados_debug.append(f"🚨 ENCONTRADO TÍTULO en línea {i}: {linea_limpia}<br>")
            
            # Mostrar las siguientes 15 líneas
            resultados_debug.append(f"<br>📋 <strong>CONTENIDO DE LA TABLA (próximas 15 líneas):</strong><br>")
            for j in range(i+1, min(i+16, len(lineas))):
                linea_tabla = lineas[j].strip()
                if linea_tabla:
                    resultados_debug.append(f"Línea {j}: {linea_tabla}<br>")
            break
    
    return resultados_debug

def buscar_puesta_marcha_simple(contenido):
    """Búsqueda simple pero efectiva de puesta en marcha"""
    lineas = contenido.split('\n')
    resultados = []
    
    # Buscar el título de la sección
    for i, linea in enumerate(lineas):
        linea_limpia = linea.strip()
        
        # Buscar el título de la tabla (diferentes variaciones)
        if (('servicio' in linea_limpia.lower() and 'puesta' in linea_limpia.lower() and 'marcha' in linea_limpia.lower()) or
            ('servicio de puesta' in linea_limpia.lower())):
            
            resultados.append("<strong>🚀 SERVICIO DE PUESTA EN MARCHA DE UN PUNTO DIGITAL</strong><br><br>")
            
            # Capturar las líneas de la tabla (buscar líneas con números)
            for j in range(i+1, min(i+25, len(lineas))):
                linea_tabla = lineas[j].strip()
                
                # Buscar líneas que parecen ser de la tabla
                if (re.match(r'^\d+\.', linea_tabla) or 
                    re.match(r'^\d+\.\s', linea_tabla) or
                    any(palabra in linea_tabla.lower() for palabra in ['proyectos', 'stock', 'soporte', 'imagen', 'monitoreo', 'equipo', 'gestión', 'análisis', 'designación', 'preinstalación', 'instalación', 'inauguración'])):
                    
                    if len(linea_tabla) > 5:  # Filtrar líneas muy cortas
                        # Formatear según el tipo de actividad
                        if 'instalación' in linea_tabla.lower():
                            resultados.append(f"🔨 {linea_tabla}<br>")
                        elif 'inauguración' in linea_tabla.lower():
                            resultados.append(f"🎉 {linea_tabla}<br>")
                        elif 'equipamiento' in linea_tabla.lower() or 'stock' in linea_tabla.lower():
                            resultados.append(f"📦 {linea_tabla}<br>")
                        elif 'preinstalación' in linea_tabla.lower():
                            resultados.append(f"🔧 {linea_tabla}<br>")
                        elif 'proyectos' in linea_tabla.lower():
                            resultados.append(f"📋 {linea_tabla}<br>")
                        elif 'soporte' in linea_tabla.lower():
                            resultados.append(f"🛠️ {linea_tabla}<br>")
                        elif 'imagen' in linea_tabla.lower():
                            resultados.append(f"🎨 {linea_tabla}<br>")
                        elif 'monitoreo' in linea_tabla.lower():
                            resultados.append(f"📊 {linea_tabla}<br>")
                        else:
                            resultados.append(f"• {linea_tabla}<br>")
                
                # Detener si encontramos el final de la tabla
                if 'procedimientos de seguimiento' in linea_tabla.lower() or 'equipo' in linea_tabla.lower() and 'proceso' in linea_tabla.lower():
                    break
            
            break
    
    return resultados

def buscar_seguimiento_simple(contenido):
    """Búsqueda simple de procedimientos de seguimiento"""
    lineas = contenido.split('\n')
    resultados = []
    
    for i, linea in enumerate(lineas):
        linea_limpia = linea.strip()
        
        if 'procedimientos de seguimiento' in linea_limpia.lower():
            resultados.append("<br><strong>🔧 PROCEDIMIENTOS DE SEGUIMIENTO Y SOPORTE</strong><br><br>")
            
            # Buscar las líneas de la tabla de seguimiento
            for j in range(i+1, min(i+15, len(lineas))):
                linea_tabla = lineas[j].strip()
                
                # Buscar líneas con formato de tabla (A., B., C.)
                if (re.match(r'^[A-Z]\.', linea_tabla) or 
                    any(palabra in linea_tabla.lower() for palabra in ['soporte técnico', 'imagen', 'gestión de stock'])):
                    
                    if len(linea_tabla) > 5:
                        if 'soporte técnico' in linea_tabla.lower():
                            resultados.append(f"🛠️ {linea_tabla}<br>")
                        elif 'imagen' in linea_tabla.lower():
                            resultados.append(f"🎨 {linea_tabla}<br>")
                        elif 'stock' in linea_tabla.lower():
                            resultados.append(f"📦 {linea_tabla}<br>")
                        else:
                            resultados.append(f"• {linea_tabla}<br>")
                
                # Detener si encontramos otra sección
                if 'lineamientos' in linea_tabla.lower() or j == i+14:
                    break
            
            break
    
    return resultados

def buscar_localmente_mejorada(pregunta, documentos):
    """Búsqueda local mejorada - VERSIÓN DEBUG"""
    pregunta_limpia = pregunta.lower()
    
    # 1. Pregunta sobre documentos disponibles
    if any(p in pregunta_limpia for p in ['documento', 'cargado', 'archivo', 'disponible']):
        docs = list(documentos.keys())
        doc_list = "<br>".join([f"• {d}" for d in docs])
        return f"<strong>📂 Documentos cargados ({len(docs)}):</strong><br><br>{doc_list}"
    
    resultados = []
    
    for doc_nombre, contenido in documentos.items():
        # 2. PRIMERO: Mostrar información DEBUG para entender el problema
        if 'debug' in pregunta_limpia:
            debug_info = debug_buscar_puesta_marcha(contenido)
            return f"<strong>📄 {doc_nombre} - DEBUG</strong><br><br>" + "".join(debug_info)
        
        # 3. Búsqueda de puesta en marcha
        if any(p in pregunta_limpia for p in ['puesta en marcha', 'puesta', 'marcha']):
            puesta_marcha = buscar_puesta_marcha_simple(contenido)
            if puesta_marcha:
                resultados.append(f"<strong>📄 {doc_nombre}</strong><br><br>" + "".join(puesta_marcha))
            
            seguimiento = buscar_seguimiento_simple(contenido)
            if seguimiento:
                if resultados:
                    resultados[-1] += "".join(seguimiento)
                else:
                    resultados.append(f"<strong>📄 {doc_nombre}</strong><br><br>" + "".join(seguimiento))
        
        # Si no se encontró nada específico, mostrar información general
        if not resultados and any(p in pregunta_limpia for p in ['puesta en marcha', 'implementación']):
            # Buscar cualquier mención de puesta en marcha
            lineas = contenido.split('\n')
            info_general = []
            for linea in lineas:
                if 'puesta' in linea.lower() and 'marcha' in linea.lower() and len(linea.strip()) > 10:
                    info_general.append(linea.strip())
                    if len(info_general) >= 5:
                        break
            
            if info_general:
                contenido_general = "<br>".join([f"📋 {linea}" for linea in info_general])
                resultados.append(f"<strong>📄 {doc_nombre}</strong><br><br>{contenido_general}")
    
    if resultados:
        return "<br><br>".join(resultados)
    
    return "🤔 No encontré información específica sobre 'puesta en marcha'.<br><br>💡 <strong>Sugerencia:</strong> Escribe 'DEBUG' para ver qué contiene el documento."

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
            # Usar las funciones simples para el contexto
            puesta_marcha = buscar_puesta_marcha_simple(contenido)
            seguimiento = buscar_seguimiento_simple(contenido)
            
            if puesta_marcha or seguimiento:
                contexto += f"DOCUMENTO: {doc_nombre}\n"
                if puesta_marcha:
                    contexto += "PUESTA EN MARCHA:\n" + "\n".join([p.replace('<br>', '\n').replace('<strong>', '').replace('</strong>', '') for p in puesta_marcha]) + "\n"
                if seguimiento:
                    contexto += "SEGUIMIENTO:\n" + "\n".join([p.replace('<br>', '\n').replace('<strong>', '').replace('</strong>', '') for p in seguimiento]) + "\n"
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
                        "content": "Eres un asistente especializado en Puntos Digitales. Responde de forma CLARA y ESTRUCTURADA. Usa HTML básico: <br> para saltos de línea y <strong> para negritas. Basate SOLO en la información proporcionada."
                    },
                    {
                        "role": "user", 
                        "content": f"{contexto}\n\nPREGUNTA: {pregunta}\n\nRESPUESTA (usa HTML):"
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