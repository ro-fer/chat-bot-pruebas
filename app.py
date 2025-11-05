from flask import Flask, request, jsonify, render_template, send_from_directory, Response
import os
from docx import Document
import requests
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
# PROCESADOR DE DOCX MEJORADO
# ================================
def procesar_docx_completo(ruta_archivo):
    """Procesa TODO el contenido del DOCX de forma más completa"""
    try:
        doc = Document(ruta_archivo)
        texto_completo = ""
        
        # Procesar párrafos con mejor estructura
        for paragraph in doc.paragraphs:
            texto = paragraph.text.strip()
            if texto:
                # Identificar títulos importantes
                if any(keyword in texto.lower() for keyword in 
                      ['equipo de', 'dirección', 'coordinación', 'analistas', 'objetivos', 'actividades']):
                    texto_completo += f"\n\n{texto}\n"
                else:
                    texto_completo += f"{texto}\n"
        
        # Procesar tablas de forma más inteligente
        for table in doc.tables:
            texto_completo += "\n" + "="*50 + "\n"
            for i, row in enumerate(table.rows):
                fila_texto = []
                for cell in row.cells:
                    if cell.text.strip():
                        fila_texto.append(cell.text.strip())
                if fila_texto:
                    # Mejor formato para tablas
                    if i == 0:  # Encabezado de tabla
                        texto_completo += " | ".join(fila_texto) + "\n"
                        texto_completo += "-" * 30 + "\n"
                    else:
                        texto_completo += " | ".join(fila_texto) + "\n"
            texto_completo += "="*50 + "\n\n"
        
        return texto_completo.strip()
        
    except Exception as e:
        logger.error(f"Error procesando DOCX {ruta_archivo}: {str(e)}")
        return f"ERROR: {str(e)}"

def extraer_secciones_especificas(contenido):
    """Extrae y enfatiza secciones específicas que sabemos que existen"""
    secciones_importantes = []
    
    # Buscar específicamente el Equipo de Imagen
    lineas = contenido.split('\n')
    en_equipo_imagen = False
    equipo_imagen_content = []
    
    for i, linea in enumerate(lineas):
        linea_limpia = linea.strip()
        
        # Detectar inicio del Equipo de Imagen
        if 'equipo de imagen' in linea_limpia.lower():
            en_equipo_imagen = True
            equipo_imagen_content.append(f"\n🎨 **EQUIPO DE IMAGEN - INFORMACIÓN COMPLETA**\n")
            continue
        
        # Si estamos en la sección de imagen, capturar contenido
        if en_equipo_imagen:
            # Detectar fin de sección (nuevo equipo)
            if i > 0 and any(otro_equipo in linea_limpia.lower() for otro_equipo in 
                            ['equipo de', 'equipo de monitoreo', 'equipo de proyectos']):
                if 'imagen' not in linea_limpia.lower():
                    break
            
            # Agregar contenido relevante
            if len(linea_limpia) > 5:
                equipo_imagen_content.append(linea_limpia)
    
    # Si encontramos información del equipo de imagen, agregarla al inicio
    if equipo_imagen_content:
        secciones_importantes.append("\n".join(equipo_imagen_content))
    
    return secciones_importantes

def cargar_documentos_docx():
    documentos = {}
    if not os.path.exists(DOCUMENTS_DIR):
        logger.warning(f"Directorio {DOCUMENTS_DIR} no existe")
        return documentos
    
    archivos = os.listdir(DOCUMENTS_DIR)
    logger.info(f"Archivos en directorio: {archivos}")
    
    for archivo in archivos:
        if archivo.lower().endswith('.docx'):
            ruta_archivo = os.path.join(DOCUMENTS_DIR, archivo)
            texto_base = procesar_docx_completo(ruta_archivo)
            
            if texto_base and not texto_base.startswith("ERROR"):
                # Mejorar el contenido con secciones específicas
                secciones_especiales = extraer_secciones_especificas(texto_base)
                
                # Combinar contenido base con secciones especiales
                contenido_mejorado = texto_base
                if secciones_especiales:
                    contenido_mejorado = "\n\n".join(secciones_especiales) + "\n\n" + contenido_mejorado
                    logger.info(f"✅ Secciones especiales agregadas a {archivo}")
                
                documentos[archivo] = contenido_mejorado
                logger.info(f"✅ Documento {archivo} cargado y mejorado")
            else:
                logger.error(f"❌ Error cargando {archivo}: {texto_base}")
    
    return documentos

# ================================
# GROQ - MEJOR CONTEXTO
# ================================
def preguntar_groq(pregunta, documentos):
    api_key = os.environ.get('GROQ_API_KEY')
    
    if not api_key:
        return "❌ Error de configuración del servicio."

    try:
        # Construir contexto enfatizando equipos específicos
        contexto = "MANUAL COMPLETO DE PUNTOS DIGITALES - INFORMACIÓN DETALLADA:\n\n"
        
        # Enfatizar equipos específicos en el contexto
        equipos_especiales = [
            "EQUIPO DE IMAGEN", "EQUIPO DE PROYECTOS", "EQUIPO DE GESTIÓN DE STOCK",
            "EQUIPO DE SOPORTE TÉCNICO TIC", "EQUIPO DE MONITOREO Y VINCULACIÓN"
        ]
        
        for doc_nombre, contenido in documentos.items():
            contexto += f"=== DOCUMENTO: {doc_nombre} ===\n"
            
            # Resaltar equipos importantes
            for equipo in equipos_especiales:
                if equipo.lower() in contenido.lower():
                    contexto += f"\n🔍 **{equipo} - INFORMACIÓN DISPONIBLE**\n"
            
            # Tomar contenido completo pero limitar tamaño
            lineas = contenido.split('\n')
            lineas_importantes = []
            
            for linea in lineas:
                if any(keyword in linea.lower() for keyword in 
                      ['equipo', 'coordinación', 'analistas', 'objetivos', 'actividades', 'imagen']):
                    lineas_importantes.append(linea)
                elif len(lineas_importantes) < 100:  # Límite razonable
                    lineas_importantes.append(linea)
            
            contexto += "\n".join(lineas_importantes[:80]) + "\n\n"
            
            if len(contexto) > 12000:
                contexto += "[... contenido adicional disponible ...]\n\n"
                break
        
        # System prompt más específico
        system_prompt = """Eres un experto en el Programa Puntos Digitales. 
Responde en español con HTML: <br> para saltos, <strong>para negritas</strong>, • para listas.

INFORMACIÓN CLAVE DISPONIBLE:
- Equipo de Imagen: cartelería, señalética, instalaciones presenciales
- Equipo de Proyectos: implementación, gestión, inauguraciones  
- Equipo de Stock: equipamiento, inventario, reequipamiento
- Equipo de Soporte Técnico: instalaciones TIC, mantenimiento
- Equipo de Monitoreo: evaluación, capacitación, vinculación

Basate SOLO en la información proporcionada."""

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{contexto}\n\nPREGUNTA: {pregunta}\n\nRESPUESTA (HTML básico, sé específico):"}
            ],
            "temperature": 0.1,
            "max_tokens": 800
        }
        
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=20
        )
        
        if response.status_code == 200:
            data = response.json()
            respuesta = data["choices"][0]["message"]["content"]
            
            # Mejorar formato HTML
            if '<br>' not in respuesta:
                respuesta = respuesta.replace('\n', '<br>')
            if '•' in respuesta and '<strong>' not in respuesta:
                # Mejorar formato de listas
                lineas = respuesta.split('<br>')
                respuesta_mejorada = []
                for linea in lineas:
                    if linea.strip().startswith('•'):
                        respuesta_mejorada.append(f"<strong>{linea.strip()}</strong>")
                    else:
                        respuesta_mejorada.append(linea)
                respuesta = '<br>'.join(respuesta_mejorada)
                
            return respuesta
            
        elif response.status_code == 429:
            return "⏳ <strong>Servicio ocupado</strong><br>Por favor, espera 5 segundos y vuelve a intentar."
            
        else:
            return "🔧 <strong>Servicio temporalmente no disponible</strong><br>Intenta nuevamente en un momento."
            
    except Exception as e:
        logger.error(f"Error Groq: {str(e)}")
        return "❌ Error temporal del servicio. Intenta nuevamente."

# ================================
# RUTAS PRINCIPALES (igual que antes)
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
            return jsonify({'success': False, 'error': 'Escribe una pregunta'})
        
        documentos = cargar_documentos_docx()
        
        if not documentos:
            return jsonify({
                'success': True, 
                'response': "📂 No hay documentos en la carpeta 'documents'."
            })
        
        # Respuestas rápidas
        pregunta_lower = pregunta.lower()
        
        if any(s in pregunta_lower for s in ['hola', 'buenos días', 'buenas']):
            return jsonify({
                'success': True, 
                'response': f"¡Hola! 👋 Asistente especializado en Puntos Digitales<br><br>📚 Documentos cargados: {len(documentos)}<br>¿En qué puedo ayudarte?"
            })
        
        if any(s in pregunta_lower for s in ['chao', 'adiós', 'bye']):
            return jsonify({'success': True, 'response': "¡Hasta luego! 👋"})
        
        if any(p in pregunta_lower for p in ['documento', 'archivo', 'disponible']):
            docs = list(documentos.keys())
            doc_list = "<br>".join([f"• {d}" for d in docs])
            return jsonify({
                'success': True,
                'response': f"<strong>📂 Documentos ({len(docs)}):</strong><br>{doc_list}"
            })
        
        respuesta = preguntar_groq(pregunta, documentos)
        return jsonify({'success': True, 'response': respuesta})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error: {str(e)}'})

# ================================
# INICIO
# ================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    documentos = cargar_documentos_docx()
    print(f"🚀 ChatBot Puntos Digitales - {len(documentos)} documentos")
    print("✅ Procesador mejorado - Captura completa de Equipo de Imagen")
    app.run(host='0.0.0.0', port=port, debug=False)