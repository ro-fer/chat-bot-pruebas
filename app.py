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
# PROCESADOR DE DOCX (FUNCIONA BIEN)
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
            texto_completo += "\n" + "="*50 + "\n"
            for row in table.rows:
                fila_texto = []
                for cell in row.cells:
                    if cell.text.strip():
                        fila_texto.append(cell.text.strip())
                if fila_texto:
                    texto_completo += " | ".join(fila_texto) + "\n"
            texto_completo += "="*50 + "\n"
        
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
            if texto:
                documentos[archivo] = texto
    return documentos

# ================================
# BÚSQUEDA FUNCIONAL - VERSIÓN SIMPLE Y EFECTIVA
# ================================
def buscar_respuesta_directa(pregunta, contenido):
    """Búsqueda directa y efectiva basada en el contenido real"""
    pregunta_limpia = pregunta.lower()
    lineas = contenido.split('\n')
    resultados = []
    
    # 1. BUSCAR EQUIPOS ESPECÍFICOS
    equipos = {
        'stock': ['stock', 'equipamiento', 'inventario'],
        'proyectos': ['proyectos', 'implementación', 'analistas'],
        'soporte': ['soporte', 'técnico', 'tic', 'instalación'],
        'imagen': ['imagen', 'cartelería'],
        'monitoreo': ['monitoreo', 'vinculación'],
        'dirección': ['dirección', 'programa']
    }
    
    for equipo, palabras_clave in equipos.items():
        if any(palabra in pregunta_limpia for palabra in palabras_clave):
            # Buscar sección del equipo
            for i, linea in enumerate(lineas):
                if equipo in linea.lower() and len(linea.strip()) > 10:
                    resultados.append(f"<strong>🏢 {equipo.upper()}</strong><br>")
                    # Capturar información del equipo
                    for j in range(i, min(i+10, len(lineas))):
                        if lineas[j].strip() and len(lineas[j].strip()) > 5:
                            resultados.append(f"• {lineas[j].strip()}<br>")
                    break
            break
    
    # 2. BUSCAR PROCEDIMIENTOS DE PUESTA EN MARCHA
    if any(p in pregunta_limpia for p in ['puesta en marcha', 'procedimiento', 'proceso']):
        # Buscar la tabla de puesta en marcha
        en_tabla = False
        for i, linea in enumerate(lineas):
            if 'servicio de puesta en marcha' in linea.lower():
                resultados.append("<strong>🚀 PROCEDIMIENTOS DE PUESTA EN MARCHA</strong><br>")
                en_tabla = True
                continue
            if en_tabla and '=' in linea and len(linea.strip()) > 10:
                en_tabla = False
                break
            if en_tabla and linea.strip():
                # Formatear líneas de la tabla
                if any(num in linea for num in ['1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.', '11.']):
                    resultados.append(f"<br>🔹 {linea.strip()}<br>")
                elif 'proyectos' in linea.lower() or 'soporte' in linea.lower() or 'stock' in linea.lower():
                    resultados.append(f"• {linea.strip()}<br>")
    
    # 3. BUSCAR PROCEDIMIENTOS DE SEGUIMIENTO
    if any(p in pregunta_limpia for p in ['seguimiento', 'soporte', 'mantenimiento']):
        en_tabla = False
        for i, linea in enumerate(lineas):
            if 'procedimientos de seguimiento' in linea.lower():
                resultados.append("<br><strong>🔧 PROCEDIMIENTOS DE SEGUIMIENTO</strong><br>")
                en_tabla = True
                continue
            if en_tabla and '=' in linea and len(linea.strip()) > 10:
                en_tabla = False
                break
            if en_tabla and linea.strip():
                if any(letra in linea for letra in ['A.', 'B.', 'C.']):
                    resultados.append(f"<br>🔸 {linea.strip()}<br>")
                elif 'soporte técnico' in linea.lower() or 'imagen' in linea.lower() or 'stock' in linea.lower():
                    resultados.append(f"• {linea.strip()}<br>")
    
    # 4. SI NO ENCONTRÓ NADA ESPECÍFICO, BUSCAR TÉRMINO GENERAL
    if not resultados:
        for i, linea in enumerate(lineas):
            if pregunta_limpia in linea.lower() and len(linea.strip()) > 10:
                resultados.append(f"<strong>🔍 RESULTADO ENCONTRADO:</strong><br>")
                # Mostrar contexto
                inicio = max(0, i-1)
                fin = min(len(lineas), i+4)
                for j in range(inicio, fin):
                    if lineas[j].strip():
                        resultados.append(f"{lineas[j].strip()}<br>")
                break
    
    return resultados

def buscar_localmente_mejorada(pregunta, documentos):
    """Búsqueda local MEJORADA y FUNCIONAL"""
    pregunta_limpia = pregunta.lower()
    
    # 1. Pregunta sobre documentos disponibles
    if any(p in pregunta_limpia for p in ['documento', 'cargado', 'archivo', 'disponible']):
        docs = list(documentos.keys())
        doc_list = "<br>".join([f"• {d}" for d in docs])
        return f"<strong>📂 Documentos cargados ({len(docs)}):</strong><br><br>{doc_list}"
    
    resultados_totales = []
    
    for doc_nombre, contenido in documentos.items():
        # Buscar respuesta directa en el contenido
        resultados = buscar_respuesta_directa(pregunta, contenido)
        
        if resultados:
            resultados_totales.append(f"<strong>📄 {doc_nombre}</strong><br><br>" + "".join(resultados))
    
    if resultados_totales:
        return "<br><br>".join(resultados_totales)
    
    # Si no encuentra nada, mostrar ayuda específica
    return f"""
    🤔 <strong>No encontré información específica sobre "{pregunta}"</strong><br><br>
    
    💡 <strong>Prueba con estos términos:</strong><br>
    • <strong>"Stock"</strong> - Información sobre equipamiento e inventario<br>
    • <strong>"Proyectos"</strong> - Gestión e implementación<br>
    • <strong>"Soporte técnico"</strong> - Instalación y mantenimiento<br>
    • <strong>"Puesta en marcha"</strong> - Procedimientos de implementación<br>
    • <strong>"Imagen"</strong> - Cartelería y señalética<br>
    • <strong>"Monitoreo"</strong> - Seguimiento y evaluación<br><br>
    
    📋 <strong>También puedes preguntar sobre:</strong><br>
    - Procedimientos específicos<br>
    - Responsabilidades de cada equipo<br>
    - Procesos de instalación<br>
    - Gestión de equipamiento
    """

# ================================
# GROQ MEJORADO
# ================================
def preguntar_groq(pregunta, documentos):
    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        respuesta = buscar_localmente_mejorada(pregunta, documentos)
        return respuesta
    
    try:
        contexto = "INFORMACIÓN DEL DOCUMENTO:\n\n"
        
        for doc_nombre, contenido in documentos.items():
            # Enviar contenido relevante según la pregunta
            lineas_relevantes = []
            lineas = contenido.split('\n')
            
            for linea in lineas:
                linea_limpia = linea.strip()
                if (pregunta.lower() in linea_limpia.lower() or 
                    any(termino in linea_limpia.lower() for termino in ['procedimiento', 'proceso', 'objetivo', 'actividad'])):
                    lineas_relevantes.append(linea_limpia)
                    if len(lineas_relevantes) >= 15:
                        break
            
            if lineas_relevantes:
                contexto += f"DOCUMENTO: {doc_nombre}\n" + "\n".join(lineas_relevantes) + "\n\n"
        
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
                        "content": "Eres un asistente especializado en Puntos Digitales. Responde de forma CLARA, CONCISA y BIEN ESTRUCTURADA. Usa HTML básico: <br> para saltos de línea y <strong> para negritas. Basate SOLO en la información proporcionada."
                    },
                    {
                        "role": "user", 
                        "content": f"{contexto}\n\nPREGUNTA: {pregunta}\n\nRESPUESTA (usa HTML, sé específico):"
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
                'response': f"¡Hola! 👋 Soy tu asistente especializado en Puntos Digitales.<br><br>Tengo {len(documentos)} documento(s) cargados.<br><br>¿En qué puedo ayudarte?"
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