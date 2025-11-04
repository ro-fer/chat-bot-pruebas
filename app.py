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
# BÚSQUEDA LOCAL MEJORADA - FORMATEO MÁS LEGIBLE
# ================================
def formatear_respuesta_legible(contenido, equipo):
    """Formatea la respuesta para que sea más legible y estructurada"""
    lineas = contenido.split('\n')
    respuesta_formateada = f"**🏢 {equipo.upper()}**\n\n"
    
    seccion_actual = ""
    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue
            
        # Limpiar líneas de marcadores
        if linea.startswith('===') or linea.startswith('---'):
            continue
            
        # Detectar secciones importantes
        if 'coordinación' in linea.lower() and len(linea) < 25:
            seccion_actual = "coordinacion"
            respuesta_formateada += "👨‍💼 **Coordinación**\n\n"
            continue
        elif 'analistas' in linea.lower() and len(linea) < 25:
            seccion_actual = "analistas"
            respuesta_formateada += "\n👩‍💻 **Analistas de Stock**\n\n"
            continue
        elif 'objetivos generales:' in linea.lower() or 'objetivos:' in linea.lower():
            respuesta_formateada += "🎯 **Objetivos:**\n"
            continue
        elif 'actividades' in linea.lower() and '/ tareas' in linea.lower():
            respuesta_formateada += "\n📋 **Actividades:**\n"
            continue
        
        # Formatear el contenido según el tipo
        if len(linea) > 10:
            if linea.startswith('•') or linea.startswith('●') or linea.startswith('-'):
                texto_limpio = linea[1:].strip()
                respuesta_formateada += f"  • {texto_limpio}\n"
            else:
                # Si es un párrafo normal, agregarlo como tal
                respuesta_formateada += f"{linea}\n"
    
    return respuesta_formateada

def extraer_seccion_equipo_estructurada(contenido, equipo_buscado):
    """Extrae la sección específica de un equipo de forma estructurada"""
    lineas = contenido.split('\n')
    en_seccion = False
    seccion = []
    equipo_encontrado = False
    
    for i, linea in enumerate(lineas):
        linea_limpia = linea.strip()
        if not linea_limpia:
            continue
            
        linea_lower = linea_limpia.lower()
        
        # Buscar el inicio de la sección del equipo
        if equipo_buscado in linea_lower and any(palabra in linea_lower for palabra in ['equipo', 'rol', 'función']):
            en_seccion = True
            equipo_encontrado = True
            seccion.append(f"🔹 {linea_limpia}")
            continue
        
        # Detectar subsecciones dentro del equipo
        if en_seccion:
            if 'coordinación' in linea_lower and len(linea_limpia) < 25:
                seccion.append(f"\n👨‍💼 {linea_limpia}")
                continue
            elif 'analistas' in linea_lower and len(linea_limpia) < 25:
                seccion.append(f"\n👩‍💻 {linea_limpia}")
                continue
            elif 'objetivos generales:' in linea_lower:
                seccion.append(f"\n🎯 Objetivos Generales:")
                continue
            elif 'actividades' in linea_lower and '/ tareas' in linea_lower:
                seccion.append(f"\n📋 Actividades/Tareas:")
                continue
        
        # Detectar fin de sección
        if en_seccion and len(linea_limpia) > 5:
            if any(p in linea_lower for p in ['equipo de', 'equipo ', 'proceso general', 'ciclos', 'lineamientos']):
                if equipo_buscado not in linea_lower:
                    break
        
        if en_seccion and linea_limpia:
            # Solo agregar contenido relevante (evitar títulos repetidos)
            if not any(palabra in linea_lower for palabra in ['equipo de', 'manual de', 'proceso general']):
                seccion.append(linea_limpia)
    
    if equipo_encontrado:
        contenido_limpio = '\n'.join(seccion[:25])  # Máximo 25 líneas
        return formatear_respuesta_legible(contenido_limpio, equipo_buscado)
    
    return None

def buscar_localmente_mejorada(pregunta, documentos):
    """Búsqueda local mejorada con respuestas estructuradas"""
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
    
    # Pregunta sobre documentos disponibles
    if any(p in pregunta_limpia for p in ['documento', 'cargado', 'archivo', 'disponible']):
        docs = list(documentos.keys())
        return f"📂 **Documentos cargados ({len(docs)}):**\n" + "\n".join([f"• {d}" for d in docs])
    
    # Buscar equipo específico
    equipo_encontrado = None
    for equipo, keywords in palabras_clave.items():
        if any(palabra in pregunta_limpia for palabra in keywords):
            equipo_encontrado = equipo
            break
    
    resultados = []
    for doc_nombre, contenido in documentos.items():
        if equipo_encontrado:
            seccion = extraer_seccion_equipo_estructurada(contenido, equipo_encontrado)
            if seccion:
                # Acortar el nombre del documento si es muy largo
                doc_nombre_corto = doc_nombre[:50] + "..." if len(doc_nombre) > 50 else doc_nombre
                resultados.append(f"**📄 {doc_nombre_corto}**\n\n{seccion}")
                break
    
    if resultados:
        return "\n" + "\n\n".join(resultados)
    
    # Si no se encontró equipo específico, buscar información general
    for doc_nombre, contenido in documentos.items():
        if any(p in pregunta_limpia for p in ['equipo', 'rol', 'función', 'responsabilidad']):
            # Buscar cualquier mención a equipos
            equipos_encontrados = []
            for equipo in palabras_clave.keys():
                if equipo in contenido.lower():
                    equipos_encontrados.append(equipo.title())
            
            if equipos_encontrados:
                return f"**📄 {doc_nombre}**\n\n🔍 **Equipos mencionados:** {', '.join(equipos_encontrados)}\n\n💡 *Pregunta por un equipo específico como 'stock' o 'proyectos' para más detalles*"
    
    return "🤔 No encontré información específica sobre ese tema. Prueba con: 'equipo de proyectos', 'soporte técnico', 'gestión de stock' o 'documentos cargados'"

# ================================
# GROQ - VERSIÓN MEJORADA
# ================================
def preguntar_groq(pregunta, documentos):
    """Versión mejorada de Groq con mejor manejo de errores"""
    
    api_key = os.environ.get('GROQ_API_KEY')
    
    if not api_key:
        return "⚠️ **Modo local**\n\n" + buscar_localmente_mejorada(pregunta, documentos)
    
    try:
        # CONTEXTO MÁS SELECTIVO
        contexto = "INFORMACIÓN SOBRE PUNTOS DIGITALES:\n\n"
        
        for doc_nombre, contenido in documentos.items():
            # Para preguntas específicas, buscar contenido relevante
            if any(p in pregunta.lower() for p in ['stock', 'equipamiento', 'inventario']):
                # Extraer solo secciones relacionadas con stock
                seccion_stock = extraer_seccion_equipo_estructurada(contenido, 'stock')
                if seccion_stock:
                    contexto += f"DOCUMENTO: {doc_nombre}\n{seccion_stock}\n\n"
            else:
                # Envío general limitado
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
                        "content": "Eres un asistente especializado en Puntos Digitales. Responde de forma CLARA, ESTRUCTURADA y CONCISA. Usa emojis y formato para hacerlo visual. Basate SOLO en la información proporcionada."
                    },
                    {
                        "role": "user", 
                        "content": f"{contexto}\n\nPREGUNTA: {pregunta}\n\nRESPUESTA:"
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 800
            },
            timeout=20
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return "🔧 **Usando búsqueda local...**\n" + buscar_localmente_mejorada(pregunta, documentos)
            
    except Exception as e:
        return "🔧 **Usando búsqueda local...**\n" + buscar_localmente_mejorada(pregunta, documentos)

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
                'response': f"¡Hola! 👋 Soy tu asistente especializado en Puntos Digitales. Tengo {len(documentos)} documento(s) cargados. ¿En qué puedo ayudarte?"
            })
        
        # Usar Groq con fallback mejorado
        respuesta = preguntar_groq(pregunta, documentos)
        return jsonify({'success': True, 'response': respuesta})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error: {str(e)}'})

# ================================
# INICIO DE LA APLICACIÓN
# ================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 ChatBot Puntos Digitales iniciado en puerto {port}")
    api_key = os.environ.get('GROQ_API_KEY')
    print(f"🔍 GROQ_API_KEY: {'✅ CONFIGURADA' if api_key else '❌ FALTANTE - Usando modo local'}")
    
    documentos = cargar_documentos_docx()
    print(f"📄 Documentos cargados: {len(documentos)}")
    
    app.run(host='0.0.0.0', port=port, debug=False)