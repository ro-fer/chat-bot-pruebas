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
# BÚSQUEDA MEJORADA - VERSIÓN LIMPIA
# ================================
def extraer_seccion_equipo(contenido, equipo_buscado):
    """Extrae una sección específica de equipo de forma limpia"""
    lineas = contenido.split('\n')
    resultados = []
    en_seccion = False
    equipo_encontrado = False
    
    for i, linea in enumerate(lineas):
        linea_limpia = linea.strip()
        
        # Buscar inicio de la sección del equipo
        if equipo_buscado in linea_limpia.lower() and any(palabra in linea_limpia.lower() for palabra in ['equipo', 'coordinación', 'analistas']):
            if not equipo_encontrado:
                resultados.append(f"<strong>🏢 {equipo_buscado.upper()}</strong><br>")
                equipo_encontrado = True
            en_seccion = True
            continue
        
        # Si estamos en la sección correcta
        if en_seccion:
            # Detectar fin de sección (nuevo equipo)
            if i > 0 and any(otro_equipo in linea_limpia.lower() for otro_equipo in 
                            ['equipo de', 'equipo ', 'dirección del programa']):
                if equipo_buscado not in linea_limpia.lower():
                    break
            
            # Agregar contenido relevante
            if len(linea_limpia) > 5 and not linea_limpia.startswith('==='):
                if any(keyword in linea_limpia.lower() for keyword in ['objetivos', 'actividades', 'funciones']):
                    resultados.append(f"<br><strong>{linea_limpia}</strong><br>")
                else:
                    resultados.append(f"• {linea_limpia}<br>")
    
    return resultados

def buscar_termino_especifico(contenido, termino_buscado):
    """Busca un término específico en el contenido"""
    lineas = contenido.split('\n')
    resultados = []
    
    for i, linea in enumerate(lineas):
        if termino_buscado in linea.lower() and len(linea.strip()) > 10:
            # Encontrar el contexto completo
            inicio = max(0, i-2)
            fin = min(len(lineas), i+5)
            contexto = []
            
            for j in range(inicio, fin):
                if lineas[j].strip() and len(lineas[j].strip()) > 5:
                    contexto.append(lineas[j].strip())
            
            if contexto:
                resultados.append(f"<strong>🔍 INFORMACIÓN SOBRE {termino_buscado.upper()}:</strong><br>")
                for linea_ctx in contexto:
                    if termino_buscado in linea_ctx.lower():
                        resultados.append(f"<strong>• {linea_ctx}</strong><br>")
                    else:
                        resultados.append(f"• {linea_ctx}<br>")
                break
    
    return resultados

def buscar_procedimientos_tabla(contenido, tipo_procedimiento):
    """Busca procedimientos en las tablas"""
    lineas = contenido.split('\n')
    resultados = []
    en_tabla = False
    
    titulo_buscar = 'servicio de puesta en marcha' if tipo_procedimiento == 'puesta en marcha' else 'procedimientos de seguimiento'
    
    for i, linea in enumerate(lineas):
        if titulo_buscar in linea.lower():
            titulo = "🚀 PROCEDIMIENTOS DE PUESTA EN MARCHA" if tipo_procedimiento == 'puesta en marcha' else "🔧 PROCEDIMIENTOS DE SEGUIMIENTO"
            resultados.append(f"<strong>{titulo}</strong><br>")
            en_tabla = True
            continue
        
        if en_tabla and '=' in linea and len(linea.strip()) > 20:
            break
            
        if en_tabla and linea.strip():
            if tipo_procedimiento == 'puesta en marcha' and any(num in linea for num in ['1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.', '11.']):
                resultados.append(f"🔹 {linea.strip()}<br>")
            elif tipo_procedimiento == 'seguimiento' and any(letra in linea for letra in ['A.', 'B.', 'C.']):
                resultados.append(f"🔸 {linea.strip()}<br>")
    
    return resultados

def buscar_respuesta_directa(pregunta, contenido):
    """Búsqueda directa y limpia"""
    pregunta_limpia = pregunta.lower()
    resultados = []
    
    # 1. BUSCAR EQUIPOS ESPECÍFICOS
    equipos = {
        'stock': ['equipo de gestión de stock', 'stock'],
        'proyectos': ['equipo de proyectos', 'proyectos', 'analistas de proyectos'],
        'soporte': ['equipo de soporte técnico tic', 'soporte técnico'],
        'imagen': ['equipo de imagen', 'imagen'],
        'monitoreo': ['equipo de monitoreo y vinculación', 'monitoreo'],
        'dirección': ['dirección del programa', 'dirección']
    }
    
    for equipo, palabras_clave in equipos.items():
        if any(palabra in pregunta_limpia for palabra in palabras_clave):
            seccion_equipo = extraer_seccion_equipo(contenido, equipo)
            if seccion_equipo:
                resultados.extend(seccion_equipo)
            break
    
    # 2. BUSCAR TÉRMINOS ESPECÍFICOS
    if not resultados:
        terminos_especificos = {
            'reequipamiento': ['reequipamiento', 'recambio de equipamiento'],
            'instalación': ['instalación', 'instalaciones técnicas'],
            'cartelería': ['cartelería', 'señalética'],
            'inauguración': ['inauguración']
        }
        
        for termino, palabras_clave in terminos_especificos.items():
            if any(palabra in pregunta_limpia for palabra in palabras_clave):
                info_termino = buscar_termino_especifico(contenido, termino)
                if info_termino:
                    resultados.extend(info_termino)
                break
    
    # 3. BUSCAR PROCEDIMIENTOS
    if not resultados:
        if any(p in pregunta_limpia for p in ['puesta en marcha', 'procedimiento']):
            procedimientos = buscar_procedimientos_tabla(contenido, 'puesta en marcha')
            if procedimientos:
                resultados.extend(procedimientos)
        
        elif any(p in pregunta_limpia for p in ['seguimiento', 'soporte']):
            procedimientos = buscar_procedimientos_tabla(contenido, 'seguimiento')
            if procedimientos:
                resultados.extend(procedimientos)
    
    # 4. BÚSQUEDA GENERAL (solo si no encontró nada específico)
    if not resultados:
        lineas = contenido.split('\n')
        for i, linea in enumerate(lineas):
            if pregunta_limpia in linea.lower() and len(linea.strip()) > 10:
                resultados.append(f"<strong>🔍 INFORMACIÓN RELACIONADA:</strong><br>")
                inicio = max(0, i-1)
                fin = min(len(lineas), i+4)
                for j in range(inicio, fin):
                    if lineas[j].strip():
                        resultados.append(f"• {lineas[j].strip()}<br>")
                break
    
    return resultados

def buscar_localmente_mejorada(pregunta, documentos):
    """Búsqueda local - VERSIÓN LIMPIA"""
    pregunta_limpia = pregunta.lower()
    
    # Pregunta sobre documentos disponibles
    if any(p in pregunta_limpia for p in ['documento', 'cargado', 'archivo', 'disponible']):
        docs = list(documentos.keys())
        doc_list = "<br>".join([f"• {d}" for d in docs])
        return f"<strong>📂 Documentos cargados ({len(docs)}):</strong><br><br>{doc_list}"
    
    resultados_totales = []
    
    for doc_nombre, contenido in documentos.items():
        resultados = buscar_respuesta_directa(pregunta, contenido)
        
        if resultados:
            resultados_totales.append(f"<strong>📄 {doc_nombre}</strong><br><br>" + "".join(resultados))
    
    if resultados_totales:
        return "<br><br>".join(resultados_totales)
    
    # Ayuda específica
    return f"""
    🤔 <strong>No encontré información específica sobre "{pregunta}"</strong><br><br>
    
    💡 <strong>Sugerencias:</strong><br>
    • <strong>"Stock"</strong> - Gestión de equipamiento e inventario<br>
    • <strong>"Proyectos"</strong> - Implementación y gestión<br>
    • <strong>"Soporte técnico"</strong> - Instalación y mantenimiento<br>
    • <strong>"Instalación"</strong> - Procesos técnicos<br>
    • <strong>"Reequipamiento"</strong> - Cambio de equipamiento<br>
    • <strong>"Puesta en marcha"</strong> - Procedimientos completos<br>
    """

# ================================
# GROQ 
# ================================
def preguntar_groq(pregunta, documentos):
    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        respuesta = buscar_localmente_mejorada(pregunta, documentos)
        return respuesta
    
    try:
        contexto = "INFORMACIÓN DEL DOCUMENTO:\n\n"
        
        for doc_nombre, contenido in documentos.items():
            lineas_relevantes = []
            lineas = contenido.split('\n')
            
            for linea in lineas:
                if (pregunta.lower() in linea.lower() or 
                    any(termino in linea.lower() for termino in ['objetivo', 'actividad', 'función', 'procedimiento'])):
                    lineas_relevantes.append(linea.strip())
                    if len(lineas_relevantes) >= 12:
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
                        "content": "Eres un asistente especializado en Puntos Digitales. Responde de forma CLARA y CONCISA. Usa HTML básico: <br> para saltos de línea y <strong> para negritas. Basate SOLO en la información proporcionada."
                    },
                    {
                        "role": "user", 
                        "content": f"{contexto}\n\nPREGUNTA: {pregunta}\n\nRESPUESTA (usa HTML):"
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