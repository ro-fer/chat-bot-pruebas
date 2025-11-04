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
# BÚSQUEDA LOCAL MEJORADA - MÁS ESTRUCTURADA
# ================================
def formatear_respuesta_legible(contenido, equipo):
    """Formatea la respuesta para que sea más legible"""
    lineas = contenido.split('\n')
    respuesta_formateada = f"**🏢 {equipo.upper()}**\n\n"
    
    seccion_actual = ""
    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue
            
        # Detectar secciones importantes
        if 'objetivos generales:' in linea.lower():
            seccion_actual = "🎯 **Objetivos Generales:**\n"
            respuesta_formateada += seccion_actual
        elif 'actividades' in linea.lower() and '/ tareas' in linea.lower():
            seccion_actual = "📋 **Actividades y Tareas:**\n"
            respuesta_formateada += "\n" + seccion_actual
        elif 'coordinación' in linea.lower() and len(linea) < 30:
            seccion_actual = "👨‍💼 **Coordinación:**\n"
            respuesta_formateada += "\n" + seccion_actual
        elif 'analistas' in linea.lower() and len(linea) < 30:
            seccion_actual = "👩‍💻 **Analistas:**\n"
            respuesta_formateada += "\n" + seccion_actual
        elif linea.startswith('•') or linea.startswith('●') or linea.startswith('-'):
            respuesta_formateada += f"  • {linea[1:].strip()}\n"
        elif len(linea) > 10 and not linea.endswith(':'):
            if seccion_actual:
                respuesta_formateada += f"  • {linea}\n"
            else:
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
            seccion.append(f"=== {linea_limpia} ===")
            continue
        
        # Buscar subsecciones dentro del equipo
        if en_seccion:
            if 'coordinación' in linea_lower and len(linea_limpia) < 25:
                seccion.append(f"\n--- {linea_limpia} ---")
                continue
            elif 'analistas' in linea_lower and len(linea_limpia) < 25:
                seccion.append(f"\n--- {linea_limpia} ---")
                continue
            elif 'objetivos generales:' in linea_lower:
                seccion.append(f"\n**Objetivos:**")
                continue
            elif 'actividades' in linea_lower and '/ tareas' in linea_lower:
                seccion.append(f"\n**Actividades:**")
                continue
        
        # Detectar fin de sección (nuevo equipo o sección principal)
        if en_seccion and len(linea_limpia) > 5:
            if any(p in linea_lower for p in ['equipo de', 'equipo ', 'proceso general', 'ciclos', 'lineamientos']):
                if equipo_buscado not in linea_lower:
                    break
            # Evitar capturar otros equipos
            otros_equipos = ['dirección', 'proyectos', 'stock', 'soporte', 'imagen', 'monitoreo']
            for otro_equipo in otros_equipos:
                if otro_equipo != equipo_buscado and otro_equipo in linea_lower and 'equipo' in linea_lower:
                    break
        
        if en_seccion and linea_limpia:
            # Formatear mejor las listas
            if linea_limpia.startswith('•') or linea_limpia.startswith('●') or linea_limpia.startswith('-'):
                seccion.append(f"  • {linea_limpia[1:].strip()}")
            elif len(linea_limpia) > 10:
                seccion.append(linea_limpia)
    
    if equipo_encontrado:
        # Limitar la longitud y formatear
        contenido_limpio = '\n'.join(seccion[:30])  # Máximo 30 líneas
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
                resultados.append(f"📄 **{doc_nombre}**\n\n{seccion}")
                break  # Solo un resultado por equipo
        
        # Búsqueda general si no se encontró equipo específico
        if not resultados and any(p in pregunta_limpia for p in ['equipo', 'rol', 'función', 'responsabilidad']):
            # Mostrar todos los equipos de forma resumida
            equipos_info = []
            for equipo in palabras_clave.keys():
                seccion = extraer_seccion_equipo_estructurada(contenido, equipo)
                if seccion:
                    # Extraer solo los objetivos principales para el resumen
                    lineas = seccion.split('\n')
                    objetivos = []
                    capturando_objetivos = False
                    for linea in lineas:
                        if 'objetivos:' in linea.lower():
                            capturando_objetivos = True
                            continue
                        elif capturando_objetivos and linea.strip() and not linea.startswith('**'):
                            if len(objetivos) < 2:  # Máximo 2 objetivos por equipo
                                objetivos.append(linea.strip())
                        elif capturando_objetivos and linea.startswith('**'):
                            break
                    
                    if objetivos:
                        equipos_info.append(f"• **{equipo.title()}:** {', '.join(objetivos)}")
            
            if equipos_info:
                resultados.append(f"📄 **{doc_nombre} - Resumen de Equipos:**\n\n" + "\n".join(equipos_info))
                break
    
    if resultados:
        return "\n\n" + "\n\n".join(resultados)
    
    return "🤔 No encontré información específica sobre ese tema. Prueba con: 'equipo de proyectos', 'soporte técnico', 'gestión de stock'"

# ================================
# GROQ - VERSIÓN MEJORADA
# ================================
def preguntar_groq(pregunta, documentos):
    """Versión mejorada de Groq con mejor manejo de errores"""
    
    api_key = os.environ.get('GROQ_API_KEY')
    
    if not api_key:
        return "⚠️ **Modo local**\n\n" + buscar_localmente_mejorada(pregunta, documentos)
    
    # CONTEXTO MEJORADO - Enviamos contenido estructurado
    contexto = "MANUAL DE PROCEDIMIENTOS - PUNTOS DIGITALES\n\n"
    for doc_nombre, contenido in documentos.items():
        contexto += f"DOCUMENTO: {doc_nombre}\n"
        contexto += "CONTENIDO RELEVANTE:\n"
        
        # Para preguntas sobre equipos, enviamos información estructurada
        if any(p in pregunta.lower() for p in ['equipo', 'rol', 'función', 'stock', 'proyectos', 'soporte']):
            equipos = ['dirección', 'proyectos', 'stock', 'soporte', 'imagen', 'monitoreo']
            for equipo in equipos:
                seccion = extraer_seccion_equipo_estructurada(contenido, equipo)
                if seccion:
                    contexto += f"\n--- {equipo.upper()} ---\n{seccion}\n"
        else:
            # Envío normal limitado
            lineas = contenido.split('\n')[:15]
            contexto += '\n'.join(lineas) + "\n"
        
        contexto += "\n" + "="*50 + "\n"
    
    try:
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
                        "content": "Eres un asistente especializado. Responde en español de forma CLARA y BIEN ESTRUCTURADA. Usa negritas para títulos y emojis para hacerlo visual. Basate SOLO en la información proporcionada."
                    },
                    {
                        "role": "user", 
                        "content": f"INFORMACIÓN DE REFERENCIA:\n{contexto}\n\nPREGUNTA DEL USUARIO: {pregunta}\n\nPOR FAVOR RESPONDE DE FORMA ORGANIZADA Y FÁCIL DE LEER:"
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 1000
            },
            timeout=25
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            error_msg = f"❌ Error en la API. Usando búsqueda local...\n"
            return error_msg + buscar_localmente_mejorada(pregunta, documentos)
            
    except requests.exceptions.Timeout:
        return "⏰ Tiempo de espera agotado. Usando búsqueda local...\n" + buscar_localmente_mejorada(pregunta, documentos)
    except Exception as e:
        return f"🔧 Error técnico. Usando búsqueda local...\n" + buscar_localmente_mejorada(pregunta, documentos)

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